# 个人简历

## 技能概览

- **前端**：Vue 3 (Composition API)、Vite、Vue Router、Pinia、JavaScript (ES6+)、HTML5、SCSS/CSS3、Element Plus、ECharts
- **后端**：Python FastAPI、SQLAlchemy ORM、JWT 鉴权、RESTful API、SSE 流式响应
- **工程化**：Docker、Nginx 反向代理、Git、Vite 构建优化、代码分割与懒加载
- **安全**：XSS 防御 (DOMPurify + ASGI 输入消毒)、CSRF 免疫设计 (JWT Bearer)、安全响应头
- **性能优化**：Element Plus 按需导入 (bundle -62%)、路由懒加载、虚拟列表、静态资源哈希缓存

---

## 项目经历

### 心灵港湾 —— AI 心理健康咨询平台

**2024.07 - 至今** | 独立全栈开发

一个面向公众的 AI 心理健康咨询 Web 应用，集成 DeepSeek 大语言模型提供实时对话咨询服务，支持心理健康自评追踪与可视化、社区文章分享等功能。

**在线地址**：_[部署后填写]_

#### 核心成果

**1. 全栈架构设计与 Docker 容器化部署**

- 采用 **Vue 3 + Vite SPA** 前端 + **FastAPI** 后端 + **SQLite** 数据库的前后端分离架构
- 编写 **Dockerfile × 2 + docker-compose.yml** 实现一键部署，前端 Nginx + 后端 Uvicorn 独立容器
- 配置 **Nginx 反向代理**：`/api/` 代理至后端、SSE 流式响应 `proxy_buffering off`、静态资源 1 年强缓存、SPA `try_files` History 模式兜底
- Nginx 对 `index.html` 禁用缓存 + `version.json` 禁止缓存，前端路由守卫轮询实现**版本自动检测与新版本无缝刷新**

**2. JWT 双 Token 鉴权与 401 自动无感刷新**

- 设计 **access_token (15min) + refresh_token (14d)** 双令牌鉴权方案，token 直接操作 localStorage，减少 Pinia 中间状态同步问题
- Axios 请求拦截器自动携带 Bearer token，响应拦截器拦截 401 后自动调用刷新接口，**并发请求排队等待**避免重复刷新
- **SSE 流式原始 fetch** 脱离 axios 拦截器，专门在 fetch 回调中处理 401 → 刷新 token → 带新 token 重连，解决流式对话自动断连问题

**3. SSE 流式对话 —— 幂等性与断线重连**

- 聊天采用 **SSE (Server-Sent Events)** 流式传输，AI 回复逐字推送到前端，支持**随时中断生成**
- **Last-Event-ID 断线重连机制**：客户端跟踪最后收到的事件 ID，断线后重连时服务端跳过重复创建用户消息，续接未完成的 AI 回复
- **幂等性设计**：每次发送消息生成 UUID 幂等键，服务端以 `idempotency_key UNIQUE` 约束去重，前端失败重试不产生重复消息
- 切换对话后原对话继续**后台生成**，侧边栏显示加载动画指示器，返回后自动同步已生成内容

**4. XSS 与 CSRF 安全防御**

- **XSS 多层防御**：后端 ASGI 中间件递归剥离请求体中 HTML 标签；前端 AI 对话输出经 **DOMPurify** 白名单清洗 + `escapeHtml` 转义后渲染
- **CSRF 天然免疫**：全站采用 JWT Bearer token 置于 `Authorization` 请求头，不依赖 Cookie 传递身份凭证，不存在 CSRF 攻击面
- 后端设置 `X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`Referrer-Policy`、`Permissions-Policy` 等安全响应头

**5. 性能优化（Lighthouse 99/100）**

| 优化项 | 优化前 | 优化后 | 效果 |
|--------|--------|--------|------|
| Element Plus 全局引入 → 按需导入 | 969 KB (raw) | 354 KB (raw) | **-63%** |
| Element Plus gzip 传输 | 361 KB | 137 KB | **-62%** |
| 路由懒加载 | 首屏全量加载 | 按路由拆分 6 个 chunk | 首屏 JS < 160 KB |
| 静态资源 hash 命名 + CDN | — | 长效缓存命中 | — |
| **Lighthouse 生产环境** | — | FCP 0.5s / LCP 0.9s | **99/100** |

- 使用 `unplugin-vue-components` + `ElementPlusResolver` 实现 Element Plus 组件级按需导入，消除全局 CSS 全量引入
- 所有页面路由 `() => import(...)` 异步加载，Vite 自动 code-split 为独立 chunk
- 首页轮播图使用 **WebP** 格式（5 张共 532 KB），构建产物 hash 命名配合 Nginx `expires 1y`
- **ECharts**（1.1 MB）仅 MentalHealth 统计页引用，路由级隔离不阻塞首页加载

**6. 组件化架构与工程化实践**

- 将原 1500+ 行单文件 `Counselors.vue` 拆分为 **4 个子组件 + 2 个 Composition API 逻辑层 + 1 个工具模块**，每个文件不超过 700 行
- 提取 `useChatConversations`（对话 CRUD + 状态缓存）和 `useChatStream`（SSE 流式 + 草稿持久化 + 滚动控制）两个 composable 实现**关注点分离**
- 全局 SCSS 基础设施：`_variables.scss`（颜色/字号/间距/圆角/阴影变量）+ `_mixins.scss`（flex-center/text-ellipsis/scrollable 等混入），通过 Vite `additionalData` 自动注入所有组件
- MentalHealth 统计页实现 **Grid 自适应列数 + 固定行高的虚拟列表**，可视区外仅保留上下各 4 行缓冲，大数据量下流畅滚动

**7. AI 对话业务功能**

- 集成 **DeepSeek 大语言模型**，基于用户情绪关键词（"好多了""焦虑""压力"等）**自动触发心理健康自评表单**，提交后生成情绪评分记录
- **ECharts 三维度数据可视化**：情绪评分趋势折线图（含良好/较差参考线）、情绪分布饼图（CSS Grid 自定义图例）、等级分布柱状图，支持周/月/年筛选
- 对话列表支持**置顶、重命名、删除、清空**，草稿自动持久化到 localStorage 防止页面关闭丢失
- AI 回复渲染 Markdown（marked.js），代码块语法高亮，消息一键**复制 Markdown** 原文

**8. 社区文章与睡眠管理**

- 社区文章 CRUD（创建、编辑、删除、点赞/点踩），后端种子数据预填充 5 篇示例文章
- 睡眠记录追踪：入睡/起床时间、睡眠质量评分、当日感受，列表分页展示
- 登录状态门控组件 `LoginGate` 统一处理未登录引导，跨页面复用

---

## 技术栈详情

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端框架 | Vue 3 (Composition API) | `<script setup>` + SFC |
| 构建工具 | Vite 8 + Rolldown | 开发秒级 HMR，生产代码分割 |
| 状态管理 | Pinia + persist 插件 | Composition Store 风格 |
| UI 组件库 | Element Plus 2.9 | 按需导入，中文 locale |
| 图表可视化 | ECharts 5 | 折线图、饼图、柱状图 |
| HTTP 客户端 | Axios | 拦截器 + 自动 token 刷新 |
| CSS 预处理 | SCSS (Dart Sass) | 全局变量 + 混入自动注入 |
| 后端框架 | FastAPI | 异步 Python Web 框架 |
| ORM | SQLAlchemy 2.0 | 模型定义 + 会话管理 |
| 数据库 | SQLite | 本地文件数据库，零配置 |
| 鉴权 | JWT (python-jose) | 双 token 机制 |
| AI 模型 | DeepSeek (OpenAI SDK) | 流式对话 + 工具调用 |
| 容器化 | Docker + docker-compose | 前后端分离部署 |
| 反向代理 | Nginx | 静态资源 + API 代理 + SSE |
| 安全 | DOMPurify + ASGI 消毒 | XSS 多层防御 |

---

## 教育背景

_[自行填写]_

## 自我评价

- 具备独立全栈项目从零到交付的完整能力，涵盖架构设计、开发、安全加固、性能优化、容器化部署
- 注重代码可维护性：组件拆分合理、纯函数与副作用分离、单一数据源原则
- 关注用户体验：loading/empty/error 三态覆盖、流式响应即时反馈、断线自动恢复
