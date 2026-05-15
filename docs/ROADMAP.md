# ROADMAP — 开发排期

| 属性 | 值 |
|:---|:---|
| 文档版本 | v0.3 |
| 最后更新 | 2026-05-14 |
| 作者 | yuz |
| 状态 | 进行中 |

---

## 1. 总体时间线

**预计总工期**：3-4 周（80-120 小时）

```
Phase 1          Phase 2          Phase 3          Phase 4        Phase 5
骨架搭建         文档入库          核心问答          会话 & 记忆     打磨上线
3-4天            3-4天            3-4天            2-3天          2-3天
  ├────────────────┼────────────────┼────────────────┼──────────────┤
Week 1            Week 2           Week 2-3         Week 3         Week 3-4
```

---

## 2. Phase 1：骨架搭建（3-4 天）

**目标**：可运行的全栈骨架，前后端联通，数据库表就绪。

| 状态 | 任务 | 说明 |
|:---|:---|:---|
| ✅ | 项目初始化 | FastAPI + Vue3 脚手架 |
| ✅ | 前端环境搭建 | npm 依赖与 Vite 配置 |
| ✅ | Git 初始化 | .gitignore + 分支策略 |
| ✅ | MySQL 表建好 | 6 张表 SQLAlchemy 模型 + Alembic 迁移 |
| ✅ | ChromaDB 连接 | collection 创建与管理 |
| ✅ | JWT 认证 | 注册/登录接口 + 中间件 |
| ✅ | 前端登录页 | LoginPage.vue + 路由骨架 |
| ✅ | 前端布局框架 | AppLayout + Sidebar 空壳 |

---

## 3. Phase 2：文档入库（3-4 天）

**目标**：用户可以创建知识库、上传文档，系统异步完成解析 → 分块 → 向量化 → 入库。

### 3.1 后端：知识库 CRUD + 文档管理

| 状态 | 任务 | 说明 | 依赖决策 |
|:---|:---|:---|:---|
| ⬜ | 知识库 CRUD 接口 | POST/GET/PUT/DELETE `/api/knowledge-bases`，DELETE 异步（标记 deleting → Celery → 物理删除，FK CASCADE 级联子记录） | KB 级异步批量清理 |
| ⬜ | 文档状态枚举 | `DocumentStatus(str, Enum)` — 10 状态 + `TERMINAL_STATUSES` + `is_terminal()`，ORM/Schema/API 统一使用 | 约束一 |
| ⬜ | 文档上传 API | POST `/documents`（multipart + force 参数），唯一性检查 `(kb_id, filename)` | 约束二、约束四 |
| ⬜ | 批量上传 API | POST `/documents/batch-upload`（多文件，部分成功返回） | 决策 #13 |
| ⬜ | 重新处理 API | POST `/documents/{id}/reprocess`（仅 `partial_failed`/`failed` 允许） | 决策 #12 |
| ⬜ | 文档列表/详情 API | GET 文档支持 status/filename 筛选 + sort_by/order，分块接口分页（仅 owner/admin） | 决策 #14、#18、#19 |
| ⬜ | 文档删除 API | DELETE 异步清理（标记 deleting → Celery 清理向量+文件 → 物理 DELETE，FK CASCADE 清 chunks） | 决策 #10、#11 |
| ⬜ | 文件存储 | `uploads/{kb_id}/{doc_id}/{uuid}_{sanitized_filename}` 目录结构 | 决策 #5 |

### 3.2 后端：Celery 异步入库流水线

| 状态 | 任务 | 说明 | 依赖决策 |
|:---|:---|:---|:---|
| ⬜ | Celery 幂等锁 | Redis `SET idempotency_key:{doc_id}:{task_type} EX 600 NX`，处理中拒绝重复入队 | 约束二 |
| ⬜ | 文档解析 | Unstructured + PyPDF2 + python-docx，部分容错（<20% warning / 20-50% partial / >50% failed） | 决策 #8 |
| ⬜ | 智能分块 | `RecursiveCharacterTextSplitter`（800-1200 chars，分隔符优先级 `\n\n`→`\n`→`。！？`），字符估算 token | 决策 #1、#2 |
| ⬜ | Embedding 向量化 | DashScope text-embedding-v3，batch_size=20，max_retries=5 指数退避，批次级 checkpoint | 决策 #7 |
| ⬜ | ChromaDB 批量写入 | batch_size=100，禁止单条循环；失败时全清 + 回滚 | 决策 #3 |
| ⬜ | chunk_count 事务更新 | 全部 batch 成功后一次性事务更新 `documents.chunk_count` + `kb.chunk_count` | 决策 #4 |
| ⬜ | 阶段化状态机 | 每阶段更新 `current_stage` + `last_success_batch`，Worker crash 后可断点恢复 | 决策 #9 |

### 3.3 前端

| 状态 | 任务 | 说明 | 依赖决策 |
|:---|:---|:---|:---|
| ⬜ | 知识库管理页 | 网格布局 + 新建/编辑弹窗 + 删除确认 | UIDESIGN.md §4 |
| ⬜ | 文档管理页 | 表格 + 筛选（status/filename）+ 分页 + 上传（拖拽 + force 覆盖选项） | 决策 #15、#19、#20 |
| ⬜ | 文档状态轮询 | 非终态 2s 间隔轮询，终态停止，5 分钟超时 | 决策 #16 |
| ⬜ | 上传进度反馈 | axios `onUploadProgress`（百分比 + 速度 + 剩余时间） | 决策 #15 |
| ⬜ | 状态标签样式 | 10 种状态对应不同颜色/图标（详见 UIDESIGN.md §4） | 约束一 |

### 3.4 本阶段不做的

| 推迟项 | 排期 | 原因 |
|:---|:---|:---|
| 结构感知分块（Markdown 标题层级） | Phase 3 | Phase 2 先跑通固定大小，后续优化 |
| `.doc` 格式支持 | 不做 | 维护成本极高，前端提示「请先转换为 .docx」 |
| WebSocket 实时状态推送 | Phase 5 | 轮询已满足需求 |
| Resumable 分片上传 | Phase 5+ | 50MB 以内 multipart 足够 |
| 内容去重 | Phase 5+ | Phase 2 仅做文件名唯一性检查 |

---

## 4. Phase 3：核心问答（3-4 天）

**目标**：单轮问答全链路跑通，SSE 流式输出，前端展示答案及引用来源。

| 状态 | 任务 | 说明 |
|:---|:---|:---|
| ⬜ | 向量检索 | ChromaDB 语义检索 |
| ⬜ | BM25 关键词检索 | jieba 分词 + 自定义 BM25 |
| ⬜ | RRF 多路融合 | k=60 合并两路结果 |
| ⬜ | NoopReranker | 占位实现，截取 top_k |
| ⬜ | Prompt 组装 | 拼接检索结果 + 用户问题 |
| ⬜ | LLM 调用 | DeepSeek API，含 thinking_content |
| ⬜ | SSE 流式输出 | sse-starlette，event 类型 meta/thinking/message/sources/finish/error |
| ⬜ | 前端问答界面 | ChatPage + MessageList + ChatInput + SSE 解析 |
| ⬜ | 来源引用展示 | 答案末尾展示引用文档名 |

---

## 5. Phase 4：会话 & 记忆（2-3 天）

**目标**：多轮对话能力，会话管理，滑动窗口记忆。

| 状态 | 任务 | 说明 |
|:---|:---|:---|
| ⬜ | 会话 CRUD | 创建/列表/详情/重命名/删除 |
| ⬜ | 多轮对话上下文 | service 层获取历史消息注入 context |
| ⬜ | 滑动窗口记忆 | 保留最近 10 轮，超出 LLM 摘要压缩 |
| ⬜ | 问题重写 | LLM 结合对话历史补全指代和上下文 |
| ⬜ | 前端会话列表 | Sidebar 展示会话列表 + 切换 |

---

## 6. Phase 5：打磨上线（2-3 天）

**目标**：体验完善，管理后台，错误处理，部署就绪。

| 状态 | 任务 | 说明 |
|:---|:---|:---|
| ⬜ | 意图识别 | LLM 分类：知识查询 / 闲聊，闲聊直接回复不检索 |
| ⬜ | 管理后台统计 | 概览统计（用户数/KB数/文档数/问答数） |
| ⬜ | 错误处理 | 全局异常处理 + 统一错误码 |
| ⬜ | Refresh Token 机制 | access_token（15-30min）+ refresh_token（7天，存 MySQL/Redis），支持 Rotation（刷新后旧 token 失效）、主动吊销（改密/强制下线） |
| ⬜ | 限流 | 简单 IP/用户级频率限制 |
| ⬜ | 日志 | 结构化日志 + 关键节点埋点 |
| ⬜ | README + 部署文档 | 项目说明 + Docker Compose 部署方案 |
| ⬜ | 简历描述文案 | 项目亮点提炼，技术选型理由 |

---

## 7. 依赖关系

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5
                              └────────────┘
                              可部分并行
```

- Phase 3 和 Phase 4 可部分并行：核心问答的单轮链路可与会话 CRUD 同时开发
- Phase 4 的问题重写依赖 Phase 3 的 LLM 调用能力
- Phase 5 在所有功能就绪后进行

---

## 8. 相关文档

- [产品需求文档](PRD.md)
- [架构设计文档](ARCHITECTURE.md)
- [开发指南](DEVELOPMENT.md)
- [测试策略](TESTING.md)
- [UI 设计规范](../frontend/docs/UIDESIGN.md)
