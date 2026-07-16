"""
JWT 双令牌处理 —— 访问令牌（15分钟）+ 刷新令牌（14天）
"""

import os
import jwt
from datetime import datetime, timedelta
from fastapi import Header, HTTPException

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "xinling-gangwan-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 14


def create_access_token(user_id: int, username: str) -> str:
    """生成短期访问令牌（15分钟）"""
    payload = {
        "user_id": user_id,
        "username": username,
        "type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int, username: str) -> str:
    """生成长期刷新令牌（14天）"""
    payload = {
        "user_id": user_id,
        "username": username,
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    """解密令牌，失败返回 None"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user(authorization: str = Header(default="")) -> dict | None:
    """从 Authorization 头中提取当前用户信息（可选鉴权）"""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    # 仅接受 access token，拒绝 refresh token 用于鉴权
    if payload.get("type") != "access":
        return None
    return payload


def require_user(authorization: str = Header(default="")):
    """必须登录才能访问"""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail={"code": 401, "msg": "请先登录", "data": None})
    return user
