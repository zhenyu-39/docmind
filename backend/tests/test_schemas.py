"""Pydantic Schema 校验测试"""
import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse


class TestRegisterRequest:
    def test_valid_input(self):
        req = RegisterRequest(username="test", password="123456")
        assert req.username == "test"
        assert req.password == "123456"

    def test_username_too_short(self):
        with pytest.raises(ValidationError) as exc:
            RegisterRequest(username="a", password="123456")
        errors = exc.value.errors()
        assert any("string_too_short" == e.get("type", "") for e in errors)

    def test_password_too_short(self):
        with pytest.raises(ValidationError) as exc:
            RegisterRequest(username="test", password="123")
        errors = exc.value.errors()
        assert any("string_too_short" == e.get("type", "") for e in errors)

    def test_username_too_long(self):
        with pytest.raises(ValidationError) as exc:
            RegisterRequest(username="x" * 65, password="123456")
        errors = exc.value.errors()
        assert any("string_too_long" == e.get("type", "") for e in errors)

    def test_missing_username(self):
        with pytest.raises(ValidationError):
            RegisterRequest(password="123456")

    def test_missing_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(username="test")


class TestLoginRequest:
    def test_valid_input(self):
        req = LoginRequest(username="test", password="123456")
        assert req.username == "test"

    def test_empty_username_rejected(self):
        """LoginRequest username 设 min_length=2，空字符串应被拒绝"""
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="123456")

    def test_missing_username(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="123456")


class TestTokenResponse:
    def test_default_token_type(self):
        resp = TokenResponse(access_token="abc", expires_in=86400)
        assert resp.token_type == "bearer"

    def test_model_dump(self):
        resp = TokenResponse(access_token="abc", expires_in=3600)
        data = resp.model_dump()
        assert "access_token" in data
        assert "token_type" in data
        assert data["expires_in"] == 3600

    def test_custom_token_type(self):
        resp = TokenResponse(access_token="abc", token_type="jwt", expires_in=60)
        assert resp.token_type == "jwt"


class TestDocumentStatusEnum:
    """DocumentStatus 枚举与状态机单元测试"""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from app.models.enums import DocumentStatus, TERMINAL_STATUSES, is_terminal
        self.DocumentStatus = DocumentStatus
        self.TERMINAL_STATUSES = TERMINAL_STATUSES
        self.is_terminal = is_terminal

    def test_ten_statuses(self):
        assert len(list(self.DocumentStatus)) == 10

    def test_str_subclass(self):
        assert issubclass(self.DocumentStatus, str)
        assert self.DocumentStatus.COMPLETED == "completed"
        assert self.DocumentStatus.UPLOADED == "uploaded"

    def test_all_values_match_doc(self):
        expected = {
            "uploaded", "parsing", "chunking", "embedding", "vector_storing",
            "completed", "success_with_warnings", "partial_failed", "failed", "deleting",
        }
        actual = {m.value for m in self.DocumentStatus}
        assert actual == expected

    def test_terminal_statuses_count(self):
        assert len(self.TERMINAL_STATUSES) == 4
        assert "completed" in self.TERMINAL_STATUSES
        assert "success_with_warnings" in self.TERMINAL_STATUSES
        assert "partial_failed" in self.TERMINAL_STATUSES
        assert "failed" in self.TERMINAL_STATUSES

    def test_terminal_statuses_is_frozenset(self):
        assert isinstance(self.TERMINAL_STATUSES, frozenset)

    @pytest.mark.parametrize("status", ["completed", "success_with_warnings", "partial_failed", "failed"])
    def test_is_terminal_true(self, status):
        assert self.is_terminal(status) is True

    @pytest.mark.parametrize("status", ["uploaded", "parsing", "chunking", "embedding", "vector_storing", "deleting"])
    def test_is_terminal_false(self, status):
        assert self.is_terminal(status) is False

    def test_is_terminal_accepts_plain_string(self):
        assert self.is_terminal("completed") is True
        assert self.is_terminal("uploaded") is False
        assert self.is_terminal("nonexistent") is False


class TestDocumentResponse:
    """DocumentResponse Pydantic Schema 校验"""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from app.schemas.document import DocumentResponse
        self.DocumentResponse = DocumentResponse

    def test_accepts_enum_value(self):
        from app.models.enums import DocumentStatus
        resp = self.DocumentResponse(
            id=1, kb_id=1, filename="test.pdf", file_type="pdf",
            status=DocumentStatus.UPLOADED, created_at="2026-05-17T00:00:00",
        )
        assert resp.status == DocumentStatus.UPLOADED

    def test_accepts_string_and_converts(self):
        resp = self.DocumentResponse(
            id=1, kb_id=1, filename="test.pdf", file_type="pdf",
            status="completed", created_at="2026-05-17T00:00:00",
        )
        from app.models.enums import DocumentStatus
        assert resp.status == DocumentStatus.COMPLETED

    def test_rejects_invalid_status(self):
        with pytest.raises(ValidationError):
            self.DocumentResponse(
                id=1, kb_id=1, filename="test.pdf", file_type="pdf",
                status="invalid_status", created_at="2026-05-17T00:00:00",
            )

    def test_model_dump_returns_string(self):
        resp = self.DocumentResponse(
            id=1, kb_id=1, filename="test.pdf", file_type="pdf",
            status="completed", created_at="2026-05-17T00:00:00",
        )
        data = resp.model_dump()
        assert data["status"] == "completed"
        assert isinstance(data["status"], str)
