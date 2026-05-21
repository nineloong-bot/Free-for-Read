# Route B 路线图：从后端 API 到 Tauri 桌面阅读应用

## 背景
路线：
- 把 FastAPI 打包成 Tauri 的 sidecar 进程（用 PyInstaller 打包成二进制）
- 前端用 React + foliate-js 做阅读 UI
- 桌面端通过 Tauri Rust 层访问本地文件系统（拖拽导入、文件关联打开）
- 后续可把部分解析逻辑逐步迁移到 Rust 以提升性能和减少包体积

Phase 1（无状态解析 API）已完成。Phase 2（电子书库：EPUB/FB2/FBZ 导入、SQLite 持久化、阅读进度、书签）已完成。长期目标是构建一个 Tauri 桌面阅读应用，将 Python 后端作为 sidecar 进程嵌入。

Phase 1 规范中列出的"未来扩展点"（文件上传、OCR、异步任务、RAG 分块、AI 问答、向量索引）是为云 API 服务设计的。对于新路线而言，其中多项并不适用——本地桌面应用不需要后台任务队列、用户系统或分布式部署。因此需要围绕本地优先的阅读体验重新规划路线。

## 核心决策：Phase 2 之后调整方向

不应按原始扩展点列表的顺序继续推进，而是在 Phase 2 完成后转向**客户端就绪化**：

| 决策 | 条目 | 原因 |
|------|------|------|
| **保留** | `/v1/parse/file`、RAG 分块、AI 问答 | AI 阅读应用的核心功能 |
| **搁置** | OCR | 复杂度高，MVP 阶段影响小 |
| **跳过** | 异步任务队列、用户系统、分布式部署 | 本地桌面应用不需要 |

## 架构

```
Tauri 桌面应用（Rust 进程）
│
├── 主窗口（React + TypeScript webview）
│   ├── 书库视图 — 浏览已导入书籍
│   ├── 阅读视图 — foliate-js 渲染 + 进度同步
│   ├── 解析视图 — URL / 本地文件 → Markdown 预览
│   └── AI 面板 — 当前书籍对话、语义搜索
│
├── Sidecar：Python 后端（FastAPI 绑定 localhost:PORT）
│   ├── /v1/parse          — URL → Markdown（Phase 1）
│   ├── /v1/parse/file     — 本地文件 → Markdown（Phase 3）
│   ├── /v1/books/*         — 电子书库 + 进度 + 书签（Phase 2）
│   ├── /v1/books/*/chunks  — RAG 分块（Phase 5）
│   └── /v1/books/*/chat    — AI 问答（Phase 5）
│
└── Sidecar：Ollama（可选，用于离线 AI）
```

Python 后端完全不知道 Tauri 的存在——它只是在临时端口上绑定 `127.0.0.1` 的标准 FastAPI 进程。Tauri 的 Rust 层负责：启动 sidecar、读取端口号、路由前端请求、管理生命周期。

## 各阶段详情

### Phase 2：电子书库

EPUB、FB2、FBZ 导入与章节提取，SQLite 持久化，阅读进度与书签 API。

### Phase 3：可嵌入后端与本地文件支持

**目标**：让后端能作为独立 sidecar 运行。增加本地文件解析。

1. **PyInstaller 打包** — 每平台一个独立二进制文件。启动 uvicorn 到临时端口，将端口号输出到 stdout 供 Tauri 读取。

2. **`POST /v1/parse/file`** — 接受 multipart 上传或本地文件路径。完全复用现有的 检测→解析→渲染 流水线，无需改动。

3. **生命周期管理** — `GET /health` 已存在（Phase 1）。增加 `POST /shutdown` 用于优雅退出。

**需创建/修改的文件：**
- `free_for_read/api/routes.py` — 新增本地文件路由
- `free_for_read/cli.py` — CLI 入口，端口选择
- `pyproject.toml` — PyInstaller 配置

### Phase 4：Tauri 外壳与阅读界面

**目标**：可运行的桌面应用，包含书库浏览、EPUB 阅读、文档解析。

1. **Tauri 项目搭建** — sidecar 进程管理（启动 Python 二进制、读取端口、健康检查、退出时终止）。

2. **React 前端** — 三个视图：
   - **书库视图**：网格/列表、上传、删除、阅读进度标识
   - **阅读视图**：foliate-js EPUB 渲染、自动保存进度、书签切换、章节导航
   - **解析视图**：URL 输入或文件拖放 → 渲染 Markdown

3. **平台集成** — 系统托盘、文件关联、原生文件对话框、拖放导入。

4. **API 客户端** — 类型安全的 TypeScript 客户端，匹配 `ParseError` 错误格式。

**需创建的文件：**
- `tauri/` — 完整 Tauri 项目
- `frontend/` — React 应用

### Phase 5：AI 阅读功能

**目标**：与书籍对话、语义搜索、RAG 问答。

1. **分块引擎** — 标题感知的章节切分。`free_for_read/ai/chunking.py`。

2. **嵌入生成** — 本地（sentence-transformers 或 Transformers.js）或 API。嵌入向量存储在 SQLite 旁。

3. **`POST /v1/books/{id}/chat`** — 用户问题 + 上下文 → 回答 + 来源引用。委托给配置的 LLM。

4. **`GET /v1/books/{id}/search`** — 混合搜索（BM25 + 向量相似度）→ 排序后的章节摘录。

5. **前端 AI 面板** — 阅读器中嵌入对话侧栏，书库中嵌入搜索栏。

**需创建的文件：**
- `free_for_read/ai/`
- `free_for_read/api/ai_routes.py`

### Phase 6：打磨与分发

**目标**：可发布的桌面应用。

1. **CI 构建** — GitHub Actions 构建 `.dmg`、`.msi`、`.AppImage`。
2. **自动更新** — Tauri updater 指向 GitHub Releases。
3. **离线模式** — 所有功能无需网络（Ollama 驱动 AI，本地解析器处理文档）。
4. **设置界面** — AI 提供商配置、阅读偏好（字体、字号、主题）。

## 时间线总览

| 阶段 | 内容 | 
|---|---|
| Phase 2 | 电子书库 | 
| Phase 3 | 打包 + 本地文件 | 
| Phase 4 | Tauri 外壳 + 阅读界面 | 
| Phase 5 | AI 阅读功能 | 
| Phase 6 | 打磨与分发 | 

Phase 4 是关键路径——项目从 API 变成真正应用的转折点。在此之前是准备阶段，在此之后是差异化阶段。

## 各阶段验证

**Phase 3**：PyInstaller 二进制能启动并响应 `/health`；`POST /v1/parse/file` 返回与 `POST /v1/parse` 相同结构的响应。

**Phase 4**：Tauri 应用启动，导入 EPUB，foliate-js 正确渲染，重启后进度保留。

**Phase 5**：「这一章的核心主题是什么？」返回有来源引用的答案。

**Phase 6**：全新安装能打开 `.epub` 文件，离线运行，通过 Tauri updater 自动更新。
