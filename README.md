# 🧠 心灵港湾 — 智能心理咨询服务平台

## 项目介绍

**心灵港湾**是一个基于大语言模型的智能心理健康服务平台，面向有心理健康需求的普通用户，提供 AI 心理咨询对话、心理健康数据追踪、心理知识科普和社区文章分享等核心功能。用户可通过实时流式 AI 对话获得情绪疏导，系统会智能识别心理状态变化并自动引导用户完成情绪自评，形成长期心理健康数据看板。

> 项目定位：一站式心理健康自服务工具，降低专业心理咨询的获取门槛。

---

## 技术栈

### 前端

| 技术 | 用途 |
|------|------|
| **Vue 3** | 核心框架（Composition API + `<script setup>`） |
| **Vite** | 构建工具（HMR、CDN 外部化、代码分割） |
| **Pinia** | 状态管理（用户态、文章数据、收藏） |
| **Vue Router** | 路由管理（导航守卫、页面级懒加载） |
| **Element Plus** | UI 组件库（中文语言包） |
| **ECharts** | 数据可视化（情绪趋势图、分布饼图） |
| **Axios** | HTTP 客户端（统一拦截、Token 注入、错误处理） |

### 后端

| 技术 | 用途 |
|------|------|
| **Python / FastAPI** | Web 框架（异步、自动 OpenAPI 文档） |
| **SQLAlchemy** | ORM（SQLite，6 张业务表） |
| **LangChain** | LLM 编排（工具调用、上下文管理、流式输出） |
| **DeepSeek API** | 大语言模型（OpenAI 兼容接口） |
| **PubMed MCP** | 学术文献检索（Model Context Protocol） |
| **PyJWT + bcrypt** | JWT 认证 + 密码哈希 |

### 工程化

| 工具 | 用途 |
|------|------|
| **ESLint + Oxlint** | 代码质量检查（Rust 引擎，50-100x 速度提升） |
| **Prettier** | 代码格式化 |
| **Vitest** | 单元测试（jsdom 环境） |

---

## 项目亮点

### 1. SSE 流式 AI 对话 + 多事件协议

LLM 响应通过 Server-Sent Events 实时推送到前端，定义了 `content`、`correction`（去重修正）、`done`、`form_trigger`、`error` 五种事件类型。前端使用 `requestAnimationFrame` 节流滚动，保证流式输出时 60fps 不丢帧。

```
用户发送消息 → SSE 连接 → 逐字 content 事件 → 流式渲染
→ 检测情绪改善 → form_trigger 事件 → 嵌入自评卡片
```

### 2. 智能心理健康自评卡片（A2UI）

AI 在对话中识别到用户情绪变化关键词时，自动触发 `form_trigger` 事件，在聊天界面嵌入心理健康自评表单——无需弹窗，不打断对话节奏。提交后的数据持久化到数据库，刷新页面表单状态不丢失，同时在心理健康数据页面生成趋势图表。

### 3. PubMed 学术文献实时检索

集成 MCP（Model Context Protocol）协议，当用户提及焦虑、抑郁等心理关键词时，自动查询 PubMed 数据库，将最新学术文献摘要注入 LLM 上下文，让 AI 回复具备循证依据。检索结果以结构化引用格式呈现（标题、作者、期刊、年份、PubMed 链接）。

### 4. LLM 上下文压缩 + 工具调用编排

对话历史超过 12 条时，旧消息被自动压缩为一句摘要，保证上下文窗口不溢出。采用"首轮非流式工具检测 → 执行工具 → 回传结果 → 流式输出最终回复"的策略，确保工具调用成功后再让用户看到回复，避免中途修正的割裂感。

### 5. CDN 外部化构建优化

生产构建时，Vue、Pinia、ElementPlus、ECharts 等 6 个核心库不打包进 dist，改为从 jsdelivr CDN 加载。Rollup `external` + 自定义 `cdnPlugin` 注入 script 标签，最终构建产物体积控制在几十 KB。

### 6. Token 缓存 + 按账号隔离的数据持久化

- `request.js` 模块级 `cachedToken` 变量避免每次 HTTP 请求同步读取 `localStorage`
- 文章收藏 key 按用户 ID 隔离：`article_favorites_{uid}`，不同用户数据互不干扰
- `shallowRef` 优化静态数据，避免深度响应式代理的性能开销

### 7. ECharts 图表复用 + 懒初始化

心理健康数据看板的 ECharts 实例在首次渲染时懒初始化，后续数据更新使用 `setOption(opt, {notMerge: true})` 原地更新，而非销毁重建。窗口 resize 事件用 150ms debounce 处理，避免频繁重绘。

### 8. 全局统一错误处理

Axios 响应拦截器覆盖 401/403/404/500 全部 HTTP 错误码，401 自动清除登录态并跳转登录页。业务层错误通过 `code` 字段区分（兼容 200/1/0 三种成功码）。`useConfirm` 组合式函数提供全局 Promise 式确认弹窗，防止 Promise 悬挂导致内存泄漏。

### 9. 安全加固

- 请求体 XSS 过滤：纯 ASGI 中间件递归剥离所有 JSON 字段中的 HTML 标签
- 密码 bcrypt 哈希存储，JWT 72 小时过期
- 安全响应头：`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`

---

## 项目结构

```
vue-project/
├── index.html                   # HTML 入口
├── vite.config.js               # Vite 构建配置（别名、代理、CDN外部化）
├── vitest.config.js             # 单元测试配置（继承 vite 配置）
├── eslint.config.js             # ESLint 规则调度中心
├── .oxlintrc.json               # Oxlint 检查规则（Rust 引擎）
├── .prettierrc.json             # Prettier 格式化配置
├── .editorconfig                # 编辑器约定配置
├── .gitattributes               # Git 换行符统一
├── package.json                 # 依赖 & 脚本
├── public/                      # 静态资源（favicon 等）
├── backend/                     # Python FastAPI 后端
│   ├── main.py                  # 应用入口（CORS、中间件、注册路由）
│   ├── database.py              # SQLAlchemy + SQLite 配置
│   ├── models.py                # 6 张数据表模型
│   ├── auth.py                  # JWT 认证
│   ├── schemas.py               # Pydantic 请求/响应模型
│   ├── llm_service.py           # LLM 对话核心（LangChain + DeepSeek + MCP）
│   ├── mcp_server.py            # MCP 协议服务器（PubMed 检索）
│   ├── llm_tools.py             # LLM 工具实现（呼吸练习、情绪追踪、文献检索）
│   ├── sanitize.py              # XSS 过滤 ASGI 中间件
│   ├── routers/
│   │   ├── users.py             # 用户注册/登录/信息修改
│   │   ├── chat.py              # AI 对话会话 & 消息（SSE流式）
│   │   ├── mental_health.py     # 心理健康记录 & 统计
│   │   ├── sleep.py             # 睡眠追踪
│   │   └── articles.py          # 社区文章 CRUD & 收藏
│   └── requirements.txt
└── src/                         # Vue 3 前端
    ├── main.js                  # 应用入口（注册插件、挂载）
    ├── App.vue                  # 根组件
    ├── router/index.js          # 路由配置（6 个页面路由）
    ├── layouts/
    │   └── FrontLayout.vue      # 主布局（导航、页脚、响应式）
    ├── views/front/
    │   ├── Home.vue             # 首页（轮播图、科普卡片、滚动动画）
    │   ├── Login.vue            # 登录/注册
    │   ├── Articles.vue         # 心理知识文章（分类、搜索、收藏）
    │   ├── ArticleShare.vue     # 社区文章管理（发布、编辑、收藏）
    │   ├── Counselors.vue       # AI 心理咨询对话（SSE流式、自评卡片）
    │   └── MentalHealth.vue     # 心理健康数据看板（ECharts图表）
    ├── components/common/
    │   ├── BaseDialog.vue       # 通用弹窗封装
    │   ├── ConfirmDialog.vue    # 确认弹窗（Promise式）
    │   ├── LoginGate.vue        # 登录门禁组件
    │   └── LazySection.vue      # 可视区域懒加载
    ├── composables/
    │   └── useConfirm.js        # 全局确认弹窗 composable
    ├── stores/
    │   ├── user.js              # 用户状态（登录、Token、用户信息）
    │   └── articles.js          # 文章数据（12篇内建 + 收藏 + 搜索过滤）
    ├── api/
    │   ├── user.js              # 用户相关 API 封装
    │   ├── chat.js              # 对话相关 API 封装（含 SSE）
    │   └── articles.js          # 文章相关 API 封装
    └── utils/
        └── request.js           # Axios 实例（拦截器、Token注入、错误处理）
```

---

## 快速开始

### 环境要求

- Node.js `^20.19.0 || >=22.12.0`
- Python 3.10+
- DeepSeek API Key

### 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env          # 编辑 .env 填入 DeepSeek API Key
python main.py                # 启动在 http://localhost:8000
```

### 前端

```bash
npm install
npm run dev                   # 启动在 http://localhost:5173
```

### 运行测试

```bash
npm run test:unit             # Vitest 单元测试
npm run lint                  # ESLint + Oxlint 代码检查
npm run format                # Prettier 格式化

http://123.57.59.63/
```
