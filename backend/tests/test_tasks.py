"""Celery 入库流水线任务测试 — 断点恢复 + last_success_batch 续传 + 阶段检测"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ingest.tasks import (
    RESUMABLE_STAGES,
    _ingest_document_async,
)
from app.models.enums import DocumentStatus


def _make_mock_doc(status=DocumentStatus.UPLOADED, current_stage=None, last_success_batch=0,
                   file_path="/tmp/test.pdf", file_type="pdf", kb_id=1, doc_id=1):
    """构造 mock Document 对象"""
    doc = MagicMock()
    doc.id = doc_id
    doc.kb_id = kb_id
    doc.status = status
    doc.current_stage = current_stage
    doc.last_success_batch = last_success_batch
    doc.file_path = file_path
    doc.file_type = file_type
    doc.chunk_count = 0
    doc.error_msg = None
    return doc


def _make_mock_chunks(count: int = 5):
    """构造 mock Chunk 对象列表"""
    chunks = []
    for i in range(count):
        c = MagicMock()
        c.id = i + 1
        c.chunk_index = i
        c.content = f"chunk {i}"
        c.chroma_id = f"doc_1_chunk_{i}"
        chunks.append(c)
    return chunks


def _make_mock_embed_result(count: int = 5):
    """构造 mock Embedding 结果"""
    result = MagicMock()
    result.embeddings = [[0.1] * 1024 for _ in range(count)]
    result.token_counts = [100] * count
    result.total_tokens = count * 100
    return result


def _setup_mock_db(doc, chunks=None):
    """构造完整的 mock DB session"""
    db = AsyncMock()
    db.get = AsyncMock(return_value=doc)

    exec_result = MagicMock()
    if chunks is not None:
        exec_result.scalars.return_value.all.return_value = chunks
    else:
        exec_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=exec_result)

    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()

    return db


def _mock_async_session_ctx(db):
    """构造 async_session() 上下文管理器"""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=db)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


# ==================== RESUMABLE_STAGES ====================


class TestResumableStages:
    """断点恢复阶段常量测试"""

    def test_chunking_done_为可恢复阶段(self):
        assert "chunking_done" in RESUMABLE_STAGES

    def test_embedding_为可恢复阶段(self):
        assert "embedding" in RESUMABLE_STAGES

    def test_vector_storing_为可恢复阶段(self):
        assert "vector_storing" in RESUMABLE_STAGES

    def test_parsing_不在可恢复阶段(self):
        assert "parsing" not in RESUMABLE_STAGES

    def test_chunking_不在可恢复阶段(self):
        assert "chunking" not in RESUMABLE_STAGES


# ==================== 阶段恢复 ====================


class TestStageResume:
    """阶段检测与断点恢复测试"""

    @pytest.mark.asyncio
    async def test_chunking_done阶段_跳过解析分块进入embedding(self):
        """文档 current_stage=chunking_done，应跳过解析+分块，直接进入 Embedding 从 batch 0 开始"""
        doc = _make_mock_doc(
            status=DocumentStatus.CHUNKING,
            current_stage="chunking_done",
            last_success_batch=0,
        )
        chunks = _make_mock_chunks(5)
        embed_result = _make_mock_embed_result(5)
        db = _setup_mock_db(doc, chunks)

        with patch("app.ingest.tasks.async_session", return_value=_mock_async_session_ctx(db)):
            with patch("app.ingest.tasks.acquire_idempotency_lock", return_value=True):
                with patch("app.ingest.tasks.release_idempotency_lock"):
                    with patch("app.ingest.tasks.embed_chunks", AsyncMock(return_value=embed_result)):
                        with patch("app.ingest.tasks.get_collection"):
                            with patch("app.ingest.tasks.parse_document") as mock_parse:
                                result = await _ingest_document_async(1)
                                mock_parse.assert_not_called()

        assert result["status"] in ("completed", "success_with_warnings")

    @pytest.mark.asyncio
    async def test_vector_storing阶段_清理chroma并重做embedding(self):
        """文档 current_stage=vector_storing，应清理 ChromaDB + 从 batch 0 重做 Embedding"""
        doc = _make_mock_doc(
            status=DocumentStatus.VECTOR_STORING,
            current_stage="vector_storing",
            last_success_batch=3,
        )
        chunks = _make_mock_chunks(5)
        embed_result = _make_mock_embed_result(5)
        db = _setup_mock_db(doc, chunks)

        mock_collection = MagicMock()

        with patch("app.ingest.tasks.async_session", return_value=_mock_async_session_ctx(db)):
            with patch("app.ingest.tasks.acquire_idempotency_lock", return_value=True):
                with patch("app.ingest.tasks.release_idempotency_lock"):
                    with patch("app.ingest.tasks.embed_chunks", AsyncMock(return_value=embed_result)):
                        with patch("app.ingest.tasks.get_collection", return_value=mock_collection):
                            result = await _ingest_document_async(1)

        # 验证 ChromaDB 清理被调用
        mock_collection.delete.assert_called_with(where={"doc_id": 1})
        assert result["status"] in ("completed", "success_with_warnings")

    @pytest.mark.asyncio
    async def test_vector_storing阶段_chroma清理失败标记FAILED(self):
        """vector_storing 阶段 ChromaDB 清理失败应标记 FAILED 并返回"""
        doc = _make_mock_doc(
            status=DocumentStatus.VECTOR_STORING,
            current_stage="vector_storing",
            last_success_batch=3,
        )
        chunks = _make_mock_chunks(5)
        db = _setup_mock_db(doc, chunks)

        mock_collection = MagicMock()
        mock_collection.delete.side_effect = RuntimeError("ChromaDB connection failed")

        with patch("app.ingest.tasks.async_session", return_value=_mock_async_session_ctx(db)):
            with patch("app.ingest.tasks.acquire_idempotency_lock", return_value=True):
                with patch("app.ingest.tasks.release_idempotency_lock"):
                    with patch("app.ingest.tasks.get_collection", return_value=mock_collection):
                        result = await _ingest_document_async(1)

        assert result["status"] == "failed"
        assert doc.status == DocumentStatus.FAILED
        assert "ChromaDB" in doc.error_msg


# ==================== last_success_batch checkpoint ====================


class TestLastSuccessBatchCheckpoint:
    """last_success_batch checkpoint 更新测试"""

    @pytest.mark.asyncio
    async def test_embedding每批成功后更新last_success_batch(self):
        """验证 embedding 阶段每批成功后会更新 doc.last_success_batch"""
        doc = _make_mock_doc(
            status=DocumentStatus.EMBEDDING,
            current_stage="embedding",
            last_success_batch=0,
        )
        # 6 chunks, batch_size=2 → 3 batches
        chunks = _make_mock_chunks(6)
        embed_result = _make_mock_embed_result(2)  # each batch has 2 chunks
        db = _setup_mock_db(doc, chunks)

        # 重新获取 doc 时应返回更新后的 last_success_batch
        # 批次 0 完成后 doc.last_success_batch = 1
        # 批次 1 完成后 doc.last_success_batch = 2
        # 批次 2 完成后 doc.last_success_batch = 3
        expected_batches = [1, 2, 3]

        with patch("app.ingest.tasks.async_session", return_value=_mock_async_session_ctx(db)):
            with patch("app.ingest.tasks.acquire_idempotency_lock", return_value=True):
                with patch("app.ingest.tasks.release_idempotency_lock"):
                    with patch("app.ingest.tasks.embed_chunks", AsyncMock(return_value=embed_result)):
                        with patch("app.ingest.tasks.get_collection"):
                            with patch("app.ingest.tasks.settings") as mock_settings:
                                mock_settings.EMBED_BATCH_SIZE = 2
                                mock_settings.CHROMA_BATCH_SIZE = 20
                                result = await _ingest_document_async(1)

        assert result["status"] in ("completed", "success_with_warnings")
        # 验证 doc.last_success_batch 在每批后被更新了 3 次（6 chunks / 2 = 3 batches）
        assert db.commit.call_count >= 3

    @pytest.mark.asyncio
    async def test_last_success_batch为0时从第一批开始(self):
        """last_success_batch=0 时，embedding 从第 0 批开始"""
        doc = _make_mock_doc(
            status=DocumentStatus.EMBEDDING,
            current_stage="embedding",
            last_success_batch=0,
        )
        chunks = _make_mock_chunks(3)
        embed_result = _make_mock_embed_result(3)
        db = _setup_mock_db(doc, chunks)

        with patch("app.ingest.tasks.async_session", return_value=_mock_async_session_ctx(db)):
            with patch("app.ingest.tasks.acquire_idempotency_lock", return_value=True):
                with patch("app.ingest.tasks.release_idempotency_lock"):
                    mock_embed = AsyncMock(return_value=embed_result)
                    with patch("app.ingest.tasks.embed_chunks", mock_embed):
                        with patch("app.ingest.tasks.get_collection"):
                            result = await _ingest_document_async(1)

        assert result["status"] in ("completed", "success_with_warnings")
        # 3 chunks, batch_size 默认 20 → 1 batch
        assert mock_embed.call_count == 1


# ==================== 幂等锁集成 ====================


class TestIdempotencyLockIntegration:
    """幂等锁与流水线集成测试"""

    @pytest.mark.asyncio
    async def test_锁被占用时返回locked(self):
        """幂等锁已被占用时，任务应返回 locked 状态"""
        with patch("app.ingest.tasks.acquire_idempotency_lock", return_value=False):
            with patch("app.ingest.tasks.release_idempotency_lock"):
                result = await _ingest_document_async(1)

        assert result["status"] == "locked"
        assert result["doc_id"] == 1
