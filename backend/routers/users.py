from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import (
    RegisterRequest, LoginRequest, UpdateUserRequest, UpdatePasswordRequest,
    RefreshTokenRequest, ok, fail,
)
from auth import create_access_token, create_refresh_token, decode_token, get_current_user
import bcrypt

router = APIRouter(prefix="/api/user", tags=["用户"])


def _hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_pw(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


@router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    # 校验两次密码一致
    if body.password != body.confirmPassword:
        return fail(400, "两次输入的密码不一致")

    # 检查用户名是否已存在
    if db.query(User).filter(User.username == body.username).first():
        return fail(400, "用户名已被注册")

    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == body.email).first():
        return fail(400, "邮箱已被注册")

    user = User(
        username=body.username,
        email=body.email,
        sex=body.sex,
        password_hash=_hash_pw(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return ok({
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }, "注册成功")


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    # 支持用户名或邮箱登录
    user = (
        db.query(User)
        .filter((User.username == body.username) | (User.email == body.username))
        .first()
    )

    if not user or not _check_pw(body.password, user.password_hash):
        return fail(400, "用户名或密码错误")

    access_token = create_access_token(user.id, user.username)
    refresh_token = create_refresh_token(user.id, user.username)

    return ok({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "userInfo": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "sex": user.sex,
        },
    }, "登录成功")


@router.get("/info")
def get_info(user: dict | None = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户信息"""
    if not user:
        return fail(401, "请先登录")

    u = db.query(User).filter(User.id == user["user_id"]).first()
    if not u:
        return fail(404, "用户不存在")

    return ok({
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "sex": u.sex,
    })


@router.put("/update")
def update_user(
    body: UpdateUserRequest,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改用户信息"""
    if not user:
        return fail(401, "请先登录")

    u = db.query(User).filter(User.id == user["user_id"]).first()
    if not u:
        return fail(404, "用户不存在")

    if body.username is not None:
        # 检查新用户名是否冲突
        conflict = db.query(User).filter(
            User.username == body.username, User.id != u.id
        ).first()
        if conflict:
            return fail(400, "用户名已被使用")
        u.username = body.username

    if body.email is not None:
        conflict = db.query(User).filter(
            User.email == body.email, User.id != u.id
        ).first()
        if conflict:
            return fail(400, "邮箱已被使用")
        u.email = body.email

    if body.sex is not None:
        u.sex = body.sex

    db.commit()
    db.refresh(u)

    return ok({
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "sex": u.sex,
    }, "更新成功")


@router.put("/updatePwd")
def update_password(
    body: UpdatePasswordRequest,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码"""
    if not user:
        return fail(401, "请先登录")

    u = db.query(User).filter(User.id == user["user_id"]).first()
    if not u:
        return fail(404, "用户不存在")

    if not _check_pw(body.oldPassword, u.password_hash):
        return fail(400, "原密码错误")

    u.password_hash = _hash_pw(body.newPassword)
    db.commit()

    return ok(None, "密码修改成功")


@router.post("/refresh")
def refresh_token(body: RefreshTokenRequest):
    """使用刷新令牌获取新的访问令牌"""
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        return fail(401, "刷新令牌无效或已过期")

    new_access_token = create_access_token(payload["user_id"], payload["username"])
    new_refresh_token = create_refresh_token(payload["user_id"], payload["username"])

    return ok({
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
    })


@router.post("/logout")
def logout():
    """退出登录（前端清除 token 即可，后端无需操作）"""
    return ok(None, "已退出")
