"""
FastAPI 应用入口

启动方式:
    cd backend
    uvicorn main:app --reload --port 8000

API 文档自动生成:
    http://localhost:8000/docs
"""

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from database import engine, Base, seed_knowledge_articles
from routers import users, chat, mental_health, sleep, articles
from sanitize import SanitizeMiddleware

# ============================================================
# 创建所有数据库表（如果不存在则自动创建）
# ============================================================
Base.metadata.create_all(bind=engine)

# 首次启动时填充内置心理知识文章
seed_knowledge_articles()

# ============================================================
# 创建 FastAPI 应用
# 跨域由开发环境 Vite proxy 和生产环境 Nginx 反向代理处理，无需 CORS 中间件
# ============================================================
app = FastAPI(
    title="心灵港湾 API",
    description="心理健康咨询平台后端，提供用户认证和AI对话服务",
    version="1.0",
)

# ---- 输入消毒（防 XSS） ----
app.add_middleware(SanitizeMiddleware)

# ---- 安全响应头 ----
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ============================================================
# 注册路由
# ============================================================
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(mental_health.router)
app.include_router(sleep.router)
app.include_router(articles.router)
