"""
Pydantic 请求/响应模型
"""

from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse


# ============================================================
# 通用响应
# ============================================================

def ok(data=None, msg="success"):
    """构建统一成功响应"""
    return {"code": 200, "msg": msg, "data": data}


def fail(code=400, msg="error", data=None):
    """构建统一失败响应，返回真实的 HTTP 状态码"""
    return JSONResponse(
        status_code=code,
        content={"code": code, "msg": msg, "data": data},
    )


# ============================================================
# 用户相关
# ============================================================

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    confirmPassword: str = Field(..., min_length=6, max_length=100)
    sex: str = Field(default="")
    email: str = Field(..., max_length=100)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UpdateUserRequest(BaseModel):
    username: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=100)
    sex: str | None = Field(default=None, max_length=10)


class UpdatePasswordRequest(BaseModel):
    oldPassword: str = Field(..., min_length=1)
    newPassword: str = Field(..., min_length=6, max_length=100)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


# ============================================================
# 对话相关
# ============================================================

class SendMessageRequest(BaseModel):
    chat_id: str = Field(..., description="对话 ID")
    message: str = Field(..., min_length=1, description="用户消息")


# ============================================================
# 心理健康记录相关
# ============================================================

class MentalHealthRecordRequest(BaseModel):
    chat_id: str | None = Field(default=None, description="关联对话 ID")
    mood_score: int = Field(..., ge=1, le=10, description="情绪评分 1-10")
    emotion_type: str = Field(..., min_length=1, max_length=50, description="情绪类型")
    description: str = Field(default="", max_length=500, description="补充描述")
    ai_context: str = Field(default="", max_length=2000, description="AI 回复上下文")


# ============================================================
# 睡眠追踪相关
# ============================================================

class SleepRecordRequest(BaseModel):
    chat_id: str | None = Field(default=None, description="关联对话 ID")
    bed_time: str = Field(..., min_length=1, max_length=10, description="就寝时间 HH:MM")
    wake_time: str = Field(..., min_length=1, max_length=10, description="起床时间 HH:MM")
    quality: int = Field(..., ge=1, le=10, description="睡眠质量 1-10")
    issues: str = Field(default="", max_length=500, description="睡眠问题")


# ============================================================
# 文章分享相关
# ============================================================

class ArticleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="文章标题")
    content: str = Field(..., min_length=1, description="文章内容")
    tags: str = Field(default="", max_length=500, description="标签，逗号分隔")
