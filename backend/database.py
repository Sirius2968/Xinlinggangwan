"""
数据库配置 —— SQLite + SQLAlchemy
"""

import json
import os
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


def seed_knowledge_articles():
    """首次启动时从 JSON 文件填充心理知识文章"""
    from models import KnowledgeArticle

    db = SessionLocal()
    try:
        if db.query(KnowledgeArticle).count() > 0:
            return

        seed_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_data.json")
        with open(seed_file, "r", encoding="utf-8") as f:
            articles = json.load(f)

        for a in articles:
            db.add(KnowledgeArticle(**a))
        db.commit()
        print(f"[数据库] 已填充 {len(articles)} 篇心理知识文章")
    finally:
        db.close()
