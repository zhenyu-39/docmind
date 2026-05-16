# FRONTEND — 前端交互文档

| 属性 | 值 |
|:---|:---|
| 文档版本 | v0.3 |
| 最后更新 | 2026-05-16 |
| 作者 | yuz |
| 状态 | 草稿 |

---

## 1. 全局交互架构

### 1.1 技术栈

| 层面 | 技术 | 用途 |
|:---|:---|:---|
| 框架 | Vue 3 | Composition API + `<script setup>` |
| 构建工具 | Vite | 开发服务器（端口 5173）|
| UI 组件库 | Element Plus | 表单、表格、弹窗、消息提示等 |
| 状态管理 | Pinia | 认证、聊天、知识库三个 store |
| 路由 | Vue Router | 三级路由守卫（公开/需登录/需管理员）|
| HTTP 客户端 | Axios | 请求/响应拦截器，自动处理 Token 和 401 |
| 图标 | Font Awesome 6 Free | 全站统一图标方案 |
| Markdown 渲染 | markdown-it | 答案内容解析 |

### 1.2 状态管理总览

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  auth.js    │  │  chat.js    │  │knowledge.js │
│  认证状态    │  │  聊天状态    │  │ 知识库状态   │
├─────────────┤  ├─────────────┤  ├─────────────┤
│ • user      │  │ • messages  │  │ • kbList    │
│ • token     │  │ • loading   │  │ • currentKb │
│ • isAdmin   │  │ • streaming │  │ • docList   │
│ • login()   │  │ • send()    │  │ • upload()  │
│ • logout()  │  │ • abort()   │  │ • create()  │
└─────────────┘  └─────────────┘  └─────────────┘
```

**规则**：组件内不直接调用 axios，所有请求走 `api/` 目录封装；状态提升到 Pinia，不用 props 透传超过两层。

### 1.3 全局错误处理

| 场景 | 前端行为 |
|:---|:---|
| HTTP 401 | 响应拦截器自动清除 token，跳转 `/login`（已在登录页则不动）|
| HTTP 403 | Element Plus `ElMessage.error('无权限执行此操作')` |
| HTTP 422 | 提取后端返回的字段级错误，聚焦到对应表单项 |
| HTTP 500/503 | `ElMessage.error('服务暂不可用，请稍后重试')` |
| 网络中断 | 请求超时 30s，提示 `网络异常，请检查连接` |

---

## 2. 路由与页面结构

### 2.1 路由表

| 路径 | 页面 | 权限 | 说明 |
|:---|:---|:---|:---|
| `/` | → `/chat` | 公开 | 根路径重定向到问答页 |
| `/login` | LoginPage | 公开 | 已登录者访问自动重定向到 `/chat` |
| `/chat` | ChatPage | 需登录 | 核心问答页，默认首页 |
| `/admin/knowledge` | KnowledgeList | 需管理员 | 知识库管理 |
| `/admin/documents` | DocumentList | 需管理员 | 文档管理（跨库）|
| `/admin/conversations` | ConversationList | 需管理员 | 会话管理 |
| `*` | → `/chat` | - | 兜底重定向 |

### 2.2 路由守卫逻辑

```
用户访问某个路径
    ↓
已登录且访问 /login → 重定向 /chat
    ↓
未登录且访问需认证页 → 重定向 /login
    ↓
非 admin 访问 admin/* → 重定向 /chat
    ↓
正常放行
```

---

## 3. 登录/注册页（LoginPage）

### 3.1 页面布局

| 区域 | 交互说明 |
|:---|:---|
| 品牌区 | 渐变背景 + Logo + 标题「DocMind」+ 副标题 |
| Tab 切换 | 登录/注册 两段式切换，带动画高亮 |
| 表单区 | 用户名 + 密码输入框，带图标前缀 |
| 错误提示 | 校验失败或 API 错误时，红色提示条出现 |
| 提交按钮 | loading 时禁用并显示旋转图标 |
| 底部链接 | 「还没有账号？立即注册」互转 |

### 3.2 交互流程

**登录流程**：
```
用户输入用户名、密码
    ↓
点击「登录」→ 前端校验（用户名非空、密码≥6位）
    ↓
调用 authStore.login() → POST /api/auth/login
    ↓
成功：ElMessage.success('登录成功') → 存储 token + 解析 JWT 用户信息 → 跳转 /chat
失败：显示后端错误消息（如「用户名或密码错误」）
```

**注册流程**：
```
用户输入用户名、密码
    ↓
点击「注册」→ 前端校验
    ↓
调用 authStore.register() → POST /api/auth/register
    ↓
成功：自动切换回登录模式，清空密码框，用户需手动登录
失败：显示错误（如「用户名已存在」）
```

### 3.3 表单校验规则

| 字段 | 规则 | 错误提示 |
|:---|:---|:---|
| 用户名 | 非空，长度 ≥ 2 | 请输入用户名 / 用户名至少 2 个字符 |
| 密码 | 长度 ≥ 6 | 密码至少 6 个字符 |

---

## 4. 聊天页（ChatPage）— 核心交互

### 4.1 页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar (280px)              │  Main Content               │
│  ─────────────────────────────┤  ─────────────────────────  │
│  Logo + 新建对话               │  Top: 知识库选择器            │
│  ─────────────────────────────┤  ─────────────────────────  │
│  历史会话列表                  │  MessageList               │
│  • 鼠标悬停显示重命名/删除      │  • WelcomeScreen（空态）     │
│  • 点击切换会话                │  • User Bubble              │
│  • 右键菜单（可选）             │  • Assistant Bubble         │
│  ─────────────────────────────┤    - thinking box           │
│  用户头像 + 退出按钮             │    - markdown content       │
│  • 点击头像→个人资料（预留）     │                             │
│  • 点击退出→提示+跳转登录页      │                             │
│                               │    - sources box            │
│                               │  ─────────────────────────  │
│                               │  ChatInput                   │
│                               │  • 输入框 + 发送按钮          │
│                               │  • 深度思考开关               │
│                               │  • 快捷键：Enter 发送          │
└───────────────────────────────┴─────────────────────────────┘
```

### 4.2 核心问答交互流程

```
用户选择知识库（下拉选择器，默认最近使用的知识库）
    ↓
用户在输入框输入问题，按 Enter 或点击发送
    ↓
前端立即在消息列表插入「用户消息」+「助手占位」（typing 动画）
    ↓
调用 chatStore.sendMessage() → POST /api/chat（SSE）
    ↓
接收 SSE 事件流：
  event: meta      → 记录 conversation_id、task_id
  event: thinking  → 展开思考过程框，实时追加内容
  event: message   → 逐字追加到助手消息内容区（Markdown 实时渲染）
  event: sources   → 在消息底部渲染引用来源卡片
  event: finish    → 关闭 typing，更新消息 ID，保存标题
  event: error     → 替换为错误提示，关闭 typing
    ↓
用户可点击「停止生成」中断 SSE 连接
```

### 4.3 输入框行为（ChatInput）

| 操作 | 行为 |
|:---|:---|
| 输入文字 | 实时显示字数统计（≤ 2000 字符）|
| Enter | 直接发送 |
| Shift + Enter | 换行 |
| 发送中 | 输入框禁用，按钮变为「停止生成」|
| 空内容发送 | 输入框轻微抖动，不触发请求 |
| 深度思考开关 | 切换 `deep_thinking` 参数，默认关闭 |

### 4.4 消息列表行为（MessageList）

| 场景 | 行为 |
|:---|:---|
| 新消息到达 | 自动滚动到底部；若用户已手动上滚，显示「新消息」浮动按钮 |
| 代码块 | 支持一键复制，hover 显示复制按钮 |
| 引用来源 | 点击文档名可预览该分块内容（弹窗或展开）|
| 重新生成 | 每条助手消息 hover 显示「重新生成」按钮，重新发送上一条问题 |
| 长消息 | 默认展开，无截断 |

### 4.5 会话侧边栏行为（Sidebar）

| 操作 | 行为 |
|:---|:---|
| 点击「新建对话」| 清空当前消息列表，conversation_id 设为 null，标题自动在首轮生成 |
| 点击历史会话 | 加载该会话的消息历史，切换 conversation_id |
| 悬停会话项 | 显示重命名和删除图标按钮 |
| 重命名 | 点击后标题变为可编辑输入框，Enter 保存，Esc 取消 |
| 删除 | 确认弹窗 `ElMessageBox.confirm`，确认后删除并清空当前会话（如果是当前打开的）|
| 会话分组 | 按时间分组：今天 / 昨天 / 近 7 天 / 更早 |

### 4.5.1 用户栏行为

| 操作 | 行为 |
|:---|:---|
| 点击头像/用户名 | 跳转个人资料页（Phase 1 预留，当前无操作） |
| 点击退出图标 | `ElMessage.success('已退出登录')` → 清除 token → 跳转 `/login` |

### 4.6 空状态（WelcomeScreen）

当消息列表为空时显示：
- 大 Logo + 欢迎语「我是 DocMind，你的企业知识助手」
- 快捷问题卡片（如「报销流程是怎样的？」「入职需要准备什么？」）
- 点击快捷问题直接填入输入框并发送

---

## 5. 知识库管理页（KnowledgeList）

### 5.1 页面布局

网格布局展示知识库卡片 + 顶部操作栏：
- 搜索框：按名称过滤知识库
- 新建按钮：弹窗创建知识库

### 5.2 知识库卡片交互

| 元素 | 交互 |
|:---|:---|
| 卡片整体 | hover 边框高亮 + 阴影上浮，点击进入知识库详情 |
| 图标 | 根据名称关键词自动匹配部门色（HR 红 / IT 蓝 / 行政绿等）|
| 文档数/分块数 | 实时显示 |
| 操作菜单 | 编辑名称描述 / 删除（确认弹窗）|

### 5.3 新建知识库弹窗

```
点击「新建知识库」
    ↓
弹窗：名称（必填）+ 描述（选填）
    ↓
确认 → POST /api/knowledge-bases
    ↓
成功：弹窗关闭，卡片列表 prepend 新项
失败：表单错误提示
```

---

## 6. 文档管理页（DocumentList）

### 6.1 页面布局

Element Plus 表格展示所有文档，支持：
- 按知识库筛选
- 按状态筛选（多选，默认仅显示非终态 + 最近终态）
- 按文件名模糊搜索
- 按 `created_at` 排序（默认倒序）

### 6.2 上传交互

```
用户进入知识库详情页
    ↓
拖拽文件到上传区 或 点击选择文件
    ↓
前端校验：
  - 格式（pdf/docx/md/txt），拒绝 .doc（提示「请先转换为 .docx」）
  - 大小（≤ 50MB）
    ↓
通过 multipart/form-data 上传
  - axios onUploadProgress 显示实时进度（百分比 + 速度 + 剩余时间）
    ↓
立即在文档列表新增一行，status = uploaded
    ↓
开始轮询 GET /documents/{id}（非终态 2s 间隔，终态停止，5 分钟超时）
    ↓
status 变为终态（completed / success_with_warnings / partial_failed / failed）
→ 停止轮询，更新列表行
```

### 6.3 同名文件冲突处理

| 场景 | 用户操作 | 前端提示 |
|:---|:---|:---|
| 无冲突 | 正常上传 | 无提示 |
| 同名且终态 | 弹出确认框：「文档 `xxx.pdf` 已存在，是否覆盖？」 | 用户确认后 `force=true` 重新上传 |
| 同名且处理中 | 拒绝 | `ElMessage.warning('文档正在处理中，请稍后再试')` |
| 同名 + force + 旧文档处理中 | 拒绝 | `ElMessage.error('旧文档仍在处理中，无法覆盖')` |

### 6.4 文档状态轮询

```js
// 轮询策略
const POLL_INTERVAL = 2000       // 非终态 2s
const POLL_TIMEOUT = 5 * 60 * 1000  // 5 分钟超时

function startPolling(docId) {
  const timer = setInterval(async () => {
    const { data } = await getDocumentDetail(docId)
    if (isTerminal(data.status)) {
      clearInterval(timer)  // 终态停止
    }
  }, POLL_INTERVAL)

  // 超时保护
  setTimeout(() => clearInterval(timer), POLL_TIMEOUT)
}
```

**终态判定**（前端共享 `TERMINAL_STATUSES` 常量）：
```js
const TERMINAL_STATUSES = [
  'completed', 'success_with_warnings', 'partial_failed', 'failed'
]
```

### 6.5 文档状态标签映射

| 状态 | 标签样式 | 图标 | 用户可见行为 |
|:---|:---|:---|:---|
| `uploaded` | 灰色 / 信息色（`--dm-info`） | `fa-upload` | 等待处理 |
| `parsing` | 蓝色 / 信息色 | `fa-spinner fa-spin` | 解析中 |
| `chunking` | 蓝色 / 信息色 | `fa-spinner fa-spin` | 分块中 |
| `embedding` | 蓝色 / 信息色 | `fa-spinner fa-spin` | 向量化中 |
| `vector_storing` | 蓝色 / 信息色 | `fa-spinner fa-spin` | 写入向量库 |
| `completed` | 绿色 / 成功色（`--dm-success`） | `fa-check-circle` | 可查看分块，不可重处理 |
| `success_with_warnings` | 浅绿色 | `fa-check-circle` + warning 角标 | 部分警告但可用，不可重处理 |
| `partial_failed` | 橙色 / 警告色（`--dm-warning`） | `fa-exclamation-triangle` | 显示失败比例，**可 reprocess** |
| `failed` | 红色 / 危险色（`--dm-danger`） | `fa-times-circle` | 显示错误原因，**可 reprocess** |
| `deleting` | 灰色 | `fa-spinner fa-spin` | 清理中（完成后物理删除行） |

### 6.6 上传进度反馈

```js
// axios onUploadProgress
const { data } = await api.post('/documents', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  onUploadProgress: (progressEvent) => {
    const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
    const speed = (progressEvent.loaded / (Date.now() - startTime) * 1000 / 1024).toFixed(0) // KB/s
    // 显示：百分比 + 上传速度 + 预估剩余时间
    uploadState.value = { percent, speed, eta: computeEta(progressEvent) }
  }
})
```

**上传状态阶段**：
```
选择文件 → 上传中（百分比 + 速度） → 已上传（等待处理） → 处理中（轮询状态） → 完成/失败
```

### 6.7 空状态

知识库无文档时显示：
- 图标 + 「暂无文档」
- 「上传第一个文档」引导按钮，跳转到上传区域

### 6.8 分块预览

文档详情页底部展示分块列表（分页，20条/页）：
- 默认返回 `preview`（截断 200 字符）
- 点击展开可查看完整 `content`
- 显示 chunk_index + token_count + 页码等 metadata

---

## 7. 管理后台交互

### 7.1 管理员导航

Sidebar 底部增加「管理后台」入口，仅 `role === 'admin'` 可见：
- 知识库管理
- 文档管理
- 会话管理
- 系统概览（统计卡片）

### 7.2 系统概览页

顶部四张统计卡片：用户总数、知识库数、文档总数、总问答数。点击卡片可下钻到对应管理页。

---

## 8. 组件交互规范

### 8.1 按钮状态

| 状态 | 视觉 | 交互 |
|:---|:---|:---|
| 默认 | 主色背景 | 可点击 |
| hover | 背景加深 + 阴影 | 手型光标 |
| loading | 禁用 + 旋转图标 | 不可点击，不重复提交 |
| disabled | 透明度 0.4-0.6 | 不可点击 |

### 8.2 表单反馈

| 场景 | 反馈方式 |
|:---|:---|
| 前端校验失败 | 表单项红色边框 + 下方文字提示 |
| 提交成功 | `ElMessage.success('操作成功')` |
| 提交失败 | `ElMessage.error(msg)` 或表单内错误提示 |
| 异步操作 | 按钮 loading，操作完成后 toast 提示 |
| 退出登录 | `ElMessage.success('已退出登录')` → 清除 token → 跳转登录页 |
| 登录成功 | `ElMessage.success('登录成功')` → 跳转 /chat |

### 8.3 加载状态

| 场景 | 加载方式 |
|:---|:---|
| 页面初始化 | 骨架屏或 spinning 全屏遮罩 |
| 表格数据 | 表格内 spinning |
| 发送消息 | 输入框禁用 + typing 动画 |
| 上传文件 | 进度条或圆形进度 |

### 8.4 确认操作

删除类操作统一使用 `ElMessageBox.confirm`：
```
标题：确认删除？
内容：删除后不可恢复，是否继续？
确认按钮：危险色（红色）
取消按钮：默认
```

---

## 9. SSE 流式输出交互细节

### 9.1 连接管理

```js
// 使用 EventSource 或 fetch + ReadableStream
const eventSource = new EventSource('/api/chat')

// 支持手动中断
function abort() {
  eventSource.close()
  chatStore.streaming = false
}
```

### 9.2 事件处理状态机

```
[idle] --发送请求--> [streaming]
[streaming] --收到 finish --> [idle]
[streaming] --收到 error --> [error]
[streaming] --用户点击停止 --> [idle]
```

### 9.3 内容渲染策略

| 事件类型 | 渲染方式 |
|:---|:---|
| thinking | 黄色边框卡片，内容逐字追加，支持展开/折叠 |
| message | Markdown 实时渲染，代码块高亮，支持复制 |
| sources | 折叠面板，默认展开，显示文档名 + 相关度分数 + 页码 |

---

## 10. 响应式设计边界

当前版本为桌面端优先，最小适配宽度 **1280px**。以下布局在不同宽度下的行为：

| 宽度 | 行为 |
|:---|:---|
| ≥ 1280px | 完整三栏/双栏布局 |
| < 1280px | Sidebar 可收起为图标栏（可选实现）|
| < 768px | 当前版本不做适配，提示「请使用桌面端访问」|

---

## 11. 已知 TODO

| 模块 | 当前状态 | Phase 2 实现 | 后续 Phase |
|:---|:---|:---|:---|
| ChatPage | 占位页面 | — | Phase 3：完整问答 SSE、消息列表、来源引用 |
| Sidebar | 空会话列表 | — | Phase 4：历史会话列表、新建对话、重命名、删除 |
| KnowledgeList | 占位页面 | 知识库卡片网格、新建/编辑弹窗、删除确认 | — |
| DocumentList | 占位页面 | 文档表格 + 筛选 + 上传（拖拽 + force 覆盖）+ 状态轮询 + 分块预览 | — |
| Admin Stats | 占位页面 | — | Phase 5：统计卡片、数据下钻 |
| 状态轮询 | 无 | 2s 间隔轮询非终态，终态停止，5 分钟超时 | Phase 5：可选升级 WebSocket |

---

## 12. 相关文档

- [产品需求文档](../docs/PRD.md)
- [架构设计文档](../docs/ARCHITECTURE.md)
- [接口文档](../backend/docs/API.md)
- [数据库设计文档](../backend/docs/DATABASE.md)
- [开发指南](../docs/DEVELOPMENT.md)
- [开发排期](../docs/ROADMAP.md)
- [测试策略](../docs/TESTING.md)
- [UI 设计规范](UIDESIGN.md)
