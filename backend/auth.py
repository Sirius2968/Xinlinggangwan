"""
JWT 令牌处理
"""

import jwt
from datetime import datetime, timedelta
from fastapi import Header, HTTPException

SECRET_KEY = "xinling-gangwan-secret-key-2026"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 72


def create_token(user_id: int, username: str) -> str:
    """生成 JWT 令牌"""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
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
    return decode_token(token)


def require_user(authorization: str = Header(default="")):
    """必须登录才能访问"""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail={"code": 401, "msg": "请先登录", "data": None})
    return user
