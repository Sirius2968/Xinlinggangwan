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


# ============================================================
# 对话相关
# ============================================================

class SendMessageRequest(BaseModel):
    chat_id: str = Field(..., description="对话 ID")
    message: str = Field(..., min_length=1, description="用户消息")
