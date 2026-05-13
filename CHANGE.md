# DocMind 变更日志

## 2026-05-10 — Phase 1: 项目初始化（目录脚手架）

### 操作概述

严格按照 `DESIGN.md` §6 项目结构定义，创建完整的目录脚手架和空占位文件。**所有文件均为空占位文件，未写入任何实现代码。**

### 后端目录 (`backend/`)

**目录创建：**
- `backend/app/` — FastAPI 应用根目录
- `backend/app/api/` — API 路由层（7 个占位文件）
- `backend/app/models/` — SQLAlchemy 数据模型（7 个占位文件）
- `backend/app/schemas/` — Pydantic 请求/响应模型（6 个占位文件）
- `backend/app/services/` — 业务逻辑层（6 个占位文件）
- `backend/app/rag/` — RAG 核心模块（8 个占位文件）
- `backend/app/ingest/` — 文档入库任务模块（3 个占位文件）
- `backend/app/core/` — 基础设施层（7 个占位文件）
- `backend/app/middleware/` — 中间件（2 个占位文件）
- `backend/knowledge_samples/` — 示例知识库文档目录（空）
- `backend/alembic/` — 数据库迁移目录（空）

**根级文件：**
- `backend/requirements.txt` — 依赖清单（空）
- `backend/alembic.ini` — Alembic 配置（空）

### 前端目录 (`frontend/`)

**目录创建：**
- `frontend/src/views/` — 页面组件（3 个占位文件）
- `frontend/src/views/admin/` — 管理后台页面（3 个占位文件）
- `frontend/src/components/chat/` — 聊天相关组件（4 个占位文件）
- `frontend/src/components/layout/` — 布局组件（2 个占位文件）
- `frontend/src/stores/` — Pinia 状态管理（3 个占位文件）
- `frontend/src/api/` — HTTP 请求封装（5 个占位文件）
- `frontend/src/router/` — 路由配置（1 个占位文件）
- `frontend/src/utils/` — 工具函数（2 个占位文件）

**根级文件：**
- `frontend/index.html` — 入口 HTML（空）
- `frontend/package.json` — 依赖清单（空）
- `frontend/vite.config.ts` — Vite 配置（空）

### 项目根目录

- `.gitignore` — Git 忽略规则（已配置 Python / Node / IDE / 环境变量等规则）

### 统计

| 类别 | 数量 |
|:---|:---|
| 后端目录 | 10 |
| 后端占位文件 | 50 |
| 前端目录 | 9 |
| 前端占位文件 | 26 |
| 根目录文件 | 1 (.gitignore) |
| **总计新增** | **96 项** |

### 后续步骤（按 DESIGN.md Phase 1）

- [ ] MySQL 表建好（SQLAlchemy models）
- [ ] ChromaDB 连接 & collection 管理
- [ ] JWT 认证（注册/登录）
- [ ] 前端登录页 + 路由骨架

---

## 2026-05-10 — Phase 1: 前端环境搭建

### 操作概述

根据用户确认的技术选型补充 DESIGN.md 前端章节，随后搭建前端运行环境并验证。

### DESIGN.md 更新

**§2 技术选型** — 前端行拆分为明细条目：
- 前端框架 → Vue 3 + Vite
- UI 组件库 → Element Plus
- 状态管理 → Pinia
- 路由 → Vue Router 4
- HTTP 客户端 → Axios
- Markdown 渲染 → markdown-it
- 包管理器 → npm
- 前端语言 → JavaScript（非 TypeScript）

**§6 项目结构** — 所有 `.ts` 扩展名改为 `.js`

**§10.1** — 新增前端 npm 依赖清单

### 文件变更

**重命名（12 个）：**
- `src/api/*.ts` → `src/api/*.js`（5 个文件）
- `src/stores/*.ts` → `src/stores/*.js`（3 个文件）
- `src/router/index.ts` → `src/router/index.js`
- `src/utils/*.ts` → `src/utils/*.js`（2 个文件）
- `vite.config.ts` → `vite.config.js`

**新创建（3 个）：**
- `package.json` — npm 依赖声明（vue 3.5, element-plus 2.9, pinia 2.3, vue-router 4.5, axios 1.7, markdown-it 14.1, vite 6, @vitejs/plugin-vue 5.2）
- `vite.config.js` — Vite 配置（Vue 插件 + `/api` 代理到 localhost:8000）
- `index.html` — 入口 HTML（zh-CN, 挂载 #app）

**新增 bootstrap 文件（2 个，环境必需）：**
- `src/main.js` — Vue 应用入口（createApp + Pinia + Router + ElementPlus）
- `src/App.vue` — 根组件（仅 `<router-view />`）

### npm 依赖安装

```
npm install → 89 packages added
```

已安装核心包：vue, vue-router, pinia, element-plus, axios, markdown-it, @vitejs/plugin-vue, vite

### 验证

- Vite 开发服务器正常启动（端口 5173）
- HTTP 200 响应正常

### 统计

| 操作 | 数量 |
|:---|:---|
| DESIGN.md 更新 | 3 处（§2, §6, §10.1） |
| 文件重命名 | 12 |
| 新创建文件 | 5 |
| npm 包安装 | 89 |

### 后续步骤（按 DESIGN.md Phase 1）

- [ ] MySQL 表建好（SQLAlchemy models）
- [ ] ChromaDB 连接 & collection 管理
- [ ] JWT 认证（注册/登录）
- [ ] 前端登录页 + 路由骨架

---

## 2026-05-10 — Phase 1: Git 版本控制初始化

### 操作概述

建立 Git 仓库并推送至 GitHub 远程仓库。

### 操作记录

```
echo "# docmind" > README.md        # 创建项目 README
git init                            # 初始化 Git 仓库
git add README.md                   # 暂存 README
git commit -m "first commit"        # 首次提交（仅 README.md）
git branch -M main                  # 默认分支 master → main
git remote add origin \
  https://github.com/zhenyu-39/docmind.git
git push -u origin main             # 推送至远程
```

### .gitignore 补充

在 Git 初始化前，根据前端环境（Vite + Vue）补充了 `.gitignore` 规则：
- `*.local` — Vite 本地环境变量文件
- `.vite/` — Vite 开发服务器缓存
- `frontend/dist/` — 生产构建产物

### 当前状态

- 远程仓库: `https://github.com/zhenyu-39/docmind.git`
- 默认分支: `main`
- 首次提交: `568de74` (仅 README.md)
- 待提交: `.gitignore`, `DESIGN.md`, `CHANGE.md`, `backend/`, `frontend/`（脚手架文件）

---

## 2026-05-13 — Phase 1: 前端登录页 + 路由 + 全局样式

### 新增

| 文件 | 说明 |
|:---|:---|
| `frontend/src/styles/global.css` | 全局 CSS 变量（Design Token）+ 重置样式 + 组件基础样式，严格对齐 UIDESIGN.md §1-2 |
| `frontend/src/views/LoginPage.vue` | 登录/注册页，含渐变背景、Logo、Tab 切换、表单验证、错误提示，样式对齐 UIDESIGN.md |
| `frontend/src/router/index.js` | Vue Router 配置，含路由守卫（公开/认证/管理员三级权限），懒加载页面 |
| `frontend/src/stores/auth.js` | Pinia 认证状态管理（login/register/logout），JWT 解析 + localStorage 持久化 |
| `frontend/src/api/index.js` | Axios 实例 + 请求拦截器（Bearer Token）+ 响应拦截器（401 跳转登录页） |
| `frontend/src/api/auth.js` | 认证 API 封装（register/login） |

### 修改

| 文件 | 说明 |
|:---|:---|
| `frontend/index.html` | 添加 Font Awesome 6.5.1 CDN 链接 |
| `frontend/src/main.js` | 导入 `global.css` |
| `frontend/vite.config.js` | 添加 `@` 路径别名（→ `./src`） |
| `frontend/src/views/admin/*.vue` | 填充占位 `<template>`，修复空文件导致构建失败 |
| `frontend/src/views/ChatPage.vue` | 同上，填充占位内容 |

### 路由设计

| 路径 | 页面 | 权限 |
|:---|:---|:---|
| `/login` | LoginPage | 公开（已登录自动跳转 `/chat`） |
| `/chat` | ChatPage | 需登录 |
| `/admin/documents` | DocumentList | 需管理员 |
| `/admin/conversations` | ConversationList | 需管理员 |
| `/admin/knowledge` | KnowledgeList | 需管理员 |
| `/` | — | 重定向 `/chat` |

### 数据流

```
LoginPage → authStore.login() → api/auth.js POST /api/auth/login
           → 解析 JWT payload → localStorage 持久化 → router.push('/chat')

LoginPage → authStore.register() → api/auth.js POST /api/auth/register
           → 注册成功 → 切换至登录模式
```
