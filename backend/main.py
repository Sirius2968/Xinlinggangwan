"""
FastAPI 应用入口

启动方式:
    cd backend
    uvicorn main:app --reload --port 8000

API 文档自动生成:
    http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import users, chat, mental_health, sleep

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

# CORS 跨域（开发环境放开，生产环境需限制）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 注册路由
# ============================================================
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(mental_health.router)
app.include_router(sleep.router)


# ============================================================
# 健康检查
# ============================================================
@app.get("/")
def root():
    return {"message": "心灵港湾 API 运行中", "version": "1.0"}
