"""
数据库配置 —— SQLite + SQLAlchemy
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 数据库文件存放在 backend 目录下
DATABASE_URL = "sqlite:///./psychology.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：每个请求获取一个数据库会话，请求结束后关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
