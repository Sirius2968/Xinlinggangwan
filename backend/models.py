"""
ORM 模型定义
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    sex = Column(String(10), default="")
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联：一个用户可以有多个对话
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class ChatSession(Base):
    """对话会话表"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 可为空，允许未登录使用
    title = Column(String(100), default="新对话")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan",
                            order_by="ChatMessage.created_at")


class ChatMessage(Base):
    """对话消息表"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)   # "user" 或 "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class MentalHealthRecord(Base):
    """心理健康记录表 —— 对话中触发的情绪自评表单"""
    __tablename__ = "mental_health_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    chat_id = Column(String(36), nullable=True)
    mood_score = Column(Integer, nullable=False)            # 情绪评分 1-10
    emotion_type = Column(String(50), nullable=False)        # 情绪类型
    description = Column(Text, default="")                   # 用户补充描述
    ai_context = Column(Text, default="")                    # 触发时的 AI 回复上下文
    created_at = Column(DateTime, server_default=func.now())  # 数据库自动时间戳

    user = relationship("User")


class SleepRecord(Base):
    """睡眠追踪表 —— 记录用户的睡眠数据"""
    __tablename__ = "sleep_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    chat_id = Column(String(36), nullable=True)
    bed_time = Column(String(10), nullable=False)          # 就寝时间 HH:MM
    wake_time = Column(String(10), nullable=False)         # 起床时间 HH:MM
    quality = Column(Integer, nullable=False)               # 睡眠质量 1-10
    duration_hours = Column(Integer, default=0)             # 睡眠时长（小时）
    issues = Column(Text, default="")                       # 睡眠问题描述
    tips_given = Column(Text, default="")                   # AI 给过的建议
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
