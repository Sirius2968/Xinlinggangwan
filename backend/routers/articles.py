"""
文章分享路由 —— 用户编写和分享心理知识文章
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import SharedArticle, User, ArticleFavorite, KnowledgeArticle, KnowledgeFavorite
from schemas import ArticleRequest, ok, fail
from auth import get_current_user

router = APIRouter(prefix="/api/articles", tags=["文章分享"])


def _format_article(a, author_name):
    return {
        "id": a.id,
        "title": a.title,
        "content": a.content,
        "tags": a.tags or "",
        "author": author_name,
        "user_id": a.user_id,
        "favorite_count": a.favorite_count or 0,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.post("/")
def create_article(
    req: ArticleRequest,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发布文章（需要登录）"""
    if not user:
        return fail(401, "请先登录")
    article = SharedArticle(
        user_id=user.get("user_id"),
        title=req.title,
        content=req.content,
        tags=req.tags or "",
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    author = db.query(User).filter(User.id == article.user_id).first()
    return ok(_format_article(article, author.username if author else "匿名"), "发布成功")


@router.get("/")
def list_articles(db: Session = Depends(get_db)):
    """获取所有分享文章"""
    articles = (
        db.query(SharedArticle)
        .order_by(SharedArticle.created_at.desc())
        .all()
    )
    result = []
    for a in articles:
        author = db.query(User).filter(User.id == a.user_id).first()
        result.append(_format_article(a, author.username if author else "匿名"))
    return ok(result)


@router.get("/my")
def my_articles(
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取自己发布的文章"""
    if not user:
        return fail(401, "请先登录")
    articles = (
        db.query(SharedArticle)
        .filter(SharedArticle.user_id == user.get("user_id"))
        .order_by(SharedArticle.created_at.desc())
        .all()
    )
    result = []
    for a in articles:
        author = db.query(User).filter(User.id == a.user_id).first()
        result.append(_format_article(a, author.username if author else "匿名"))
    return ok(result)


@router.put("/{article_id}")
def update_article(
    article_id: int,
    req: ArticleRequest,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """编辑自己的文章"""
    if not user:
        return fail(401, "请先登录")
    article = db.query(SharedArticle).filter(
        SharedArticle.id == article_id,
        SharedArticle.user_id == user.get("user_id"),
    ).first()
    if not article:
        return fail(404, "文章不存在或无权编辑")
    article.title = req.title
    article.content = req.content
    article.tags = req.tags or ""
    db.commit()
    db.refresh(article)
    author = db.query(User).filter(User.id == article.user_id).first()
    return ok(_format_article(article, author.username if author else "匿名"), "更新成功")


@router.delete("/{article_id}")
def delete_article(
    article_id: int,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除自己的文章"""
    if not user:
        return fail(401, "请先登录")
    article = db.query(SharedArticle).filter(
        SharedArticle.id == article_id,
        SharedArticle.user_id == user.get("user_id"),
    ).first()
    if not article:
        return fail(404, "文章不存在或无权删除")
    db.delete(article)
    db.commit()
    return ok(None, "已删除")


@router.get("/favorites")
def get_user_favorites(
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户收藏的文章 ID 列表（需要登录）"""
    if not user:
        return fail(401, "请先登录")
    rows = (
        db.query(ArticleFavorite)
        .filter(ArticleFavorite.user_id == user.get("user_id"))
        .all()
    )
    return ok([r.article_id for r in rows])


@router.post("/{article_id}/favorite")
def toggle_favorite(
    article_id: int,
    action: str = "add",
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """收藏/取消收藏文章（需要登录，按账号隔离）"""
    if not user:
        return fail(401, "请先登录")
    article = db.query(SharedArticle).filter(SharedArticle.id == article_id).first()
    if not article:
        return fail(404, "文章不存在")

    uid = user.get("user_id")
    existing = (
        db.query(ArticleFavorite)
        .filter(ArticleFavorite.user_id == uid, ArticleFavorite.article_id == article_id)
        .first()
    )

    if action == "remove":
        if existing:
            db.delete(existing)
            article.favorite_count = max(0, (article.favorite_count or 0) - 1)
    else:
        if not existing:
            fav = ArticleFavorite(user_id=uid, article_id=article_id)
            db.add(fav)
            article.favorite_count = (article.favorite_count or 0) + 1
    db.commit()
    return ok({"favorite_count": article.favorite_count})


# ============================================================
# 系统知识文章（从 Pinia 迁移至数据库渲染）
# ============================================================

def _format_knowledge_article(a, fav_ids: set):
    return {
        "id": a.id,
        "title": a.title,
        "summary": a.summary,
        "content": a.content,
        "category": a.category,
        "tags": [t.strip() for t in (a.tags or "").split(",") if t.strip()],
        "readTime": a.read_time or "4分钟",
        "icon": a.icon or "",
        "isFavorited": a.id in fav_ids,
    }


@router.get("/knowledge")
def list_knowledge_articles(
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取系统知识文章列表（分类筛选、搜索由前端处理）"""
    articles = db.query(KnowledgeArticle).order_by(KnowledgeArticle.id).all()
    fav_ids = set()
    if user:
        rows = (
            db.query(KnowledgeFavorite)
            .filter(KnowledgeFavorite.user_id == user.get("user_id"))
            .all()
        )
        fav_ids = {r.article_id for r in rows}
    return ok([_format_knowledge_article(a, fav_ids) for a in articles])


@router.get("/knowledge/favorites")
def get_knowledge_favorites(
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户收藏的知识文章 ID 列表（需要登录）"""
    if not user:
        return fail(401, "请先登录")
    rows = (
        db.query(KnowledgeFavorite)
        .filter(KnowledgeFavorite.user_id == user.get("user_id"))
        .all()
    )
    return ok([r.article_id for r in rows])


@router.post("/knowledge/{article_id}/favorite")
def toggle_knowledge_favorite(
    article_id: int,
    action: str = "add",
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """收藏/取消收藏知识文章（需要登录，按账号隔离）"""
    if not user:
        return fail(401, "请先登录")

    article = db.query(KnowledgeArticle).filter(KnowledgeArticle.id == article_id).first()
    if not article:
        return fail(404, "文章不存在")

    uid = user.get("user_id")
    existing = (
        db.query(KnowledgeFavorite)
        .filter(KnowledgeFavorite.user_id == uid, KnowledgeFavorite.article_id == article_id)
        .first()
    )

    if action == "remove":
        if existing:
            db.delete(existing)
    else:
        if not existing:
            fav = KnowledgeFavorite(user_id=uid, article_id=article_id)
            db.add(fav)
    db.commit()
    return ok({"is_favorited": action != "remove"})
