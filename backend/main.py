"""
FastAPI 应用入口

启动方式:
    cd backend
    uvicorn main:app --reload --port 8000

API 文档自动生成:
    http://localhost:8000/docs
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from database import engine, Base
from routers import users, chat, mental_health, sleep, articles
from sanitize import SanitizeMiddleware

# ============================================================
# 创建所有数据库表（如果不存在则自动创建）
# ============================================================
Base.metadata.create_all(bind=engine)

# ============================================================
# 创建 FastAPI 应用
# ============================================================
app = FastAPI(
    title="心灵港湾 API",
    description="心理健康咨询平台后端，提供用户认证和AI对话服务",
    version="1.0",
)

# ---- CORS 跨域 ----
# 使用 Bearer Token 认证（非 Cookie），无需 allow_credentials
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
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


# ============================================================
# 前端静态文件托管（生产模式）
# ============================================================
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dist")

if os.path.isdir(FRONTEND_DIST):
    from fastapi.responses import FileResponse

    # CSS/JS/图片等静态资源（类如 /assets/index-Dke6wJ7I.js）
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    # SPA 兜底：API 路由未命中 → 尝试匹配文件 → 否则返回 index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
