"""
心理健康记录路由 —— 表单提交、筛选查询、可视化统计
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from database import get_db
from models import MentalHealthRecord
from schemas import MentalHealthRecordRequest, ok, fail
from auth import get_current_user

def _aggregate_trend(records, period):
    """按周期聚合趋势数据：year→12个月, month→3天区间, week→7天"""
    if not records:
        return []

    if period == "year":
        # 按月聚合：1月..12月
        buckets = {}
        for r in records:
            month = r.created_at.month
            buckets.setdefault(month, []).append(r.mood_score)
        result = []
        for m in range(1, 13):
            scores = buckets.get(m, [])
            result.append({
                "label": f"{m}月",
                "score": round(sum(scores) / len(scores), 1) if scores else None,
                "count": len(scores),
            })
        return result

    if period == "week":
        # 按周几聚合：周一..周日
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        buckets = {}
        for r in records:
            wd = r.created_at.weekday()  # 0=周一
            buckets.setdefault(wd, []).append(r.mood_score)
        result = []
        for i, name in enumerate(weekday_names):
            scores = buckets.get(i, [])
            result.append({
                "label": name,
                "score": round(sum(scores) / len(scores), 1) if scores else None,
                "count": len(scores),
            })
        return result

    # month (default): 按3天区间聚合
    buckets = {}
    for r in records:
        day = r.created_at.day
        # 将日期映射到3天区间: 1-3→0, 4-6→1, ..., 28-31→9
        bucket_idx = min((day - 1) // 3, 9)
        buckets.setdefault(bucket_idx, []).append(r.mood_score)
    result = []
    for i in range(10):
        start = i * 3 + 1
        end = min(start + 2, 31)
        label = f"{start}-{end}日"
        scores = buckets.get(i, [])
        result.append({
            "label": label,
            "score": round(sum(scores) / len(scores), 1) if scores else None,
            "count": len(scores),
        })
    return result


router = APIRouter(prefix="/api/mental-health", tags=["心理健康记录"])


@router.post("/submit")
def submit_record(
    req: MentalHealthRecordRequest,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """提交心理健康自评表单"""
    record = MentalHealthRecord(
        user_id=user.get("user_id") if user else None,
        chat_id=req.chat_id,
        mood_score=req.mood_score,
        emotion_type=req.emotion_type,
        description=req.description,
        ai_context=req.ai_context,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return ok(
        {
            "id": record.id,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        },
        "表单已保存",
    )


@router.get("/records")
def get_records(
    period: str | None = Query(default=None, description="时间范围: week/month/year"),
    emotion_type: str | None = Query(default=None, description="按情绪类型筛选"),
    start_date: str | None = Query(default=None, description="自定义起始日期 YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="自定义结束日期 YYYY-MM-DD"),
    min_score: int | None = Query(default=None, description="最低评分筛选 1-10"),
    max_score: int | None = Query(default=None, description="最高评分筛选 1-10"),
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的心理健康记录，支持按时间范围和情绪类型筛选"""
    if not user:
        return ok([])

    query = db.query(MentalHealthRecord).filter(MentalHealthRecord.user_id == user.get("user_id"))

    # 时间范围筛选
    now = datetime.utcnow()
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(MentalHealthRecord.created_at >= start, MentalHealthRecord.created_at < end)
        except ValueError:
            return fail(400, "日期格式错误，请使用 YYYY-MM-DD")
    elif period == "week":
        week_start = now - timedelta(days=now.weekday())
        query = query.filter(MentalHealthRecord.created_at >= week_start.replace(hour=0, minute=0, second=0))
    elif period == "month":
        month_start = now.replace(day=1, hour=0, minute=0, second=0)
        query = query.filter(MentalHealthRecord.created_at >= month_start)
    elif period == "year":
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0)
        query = query.filter(MentalHealthRecord.created_at >= year_start)

    # 情绪类型筛选
    if emotion_type:
        query = query.filter(MentalHealthRecord.emotion_type == emotion_type)

    # 评分范围筛选
    if min_score is not None:
        query = query.filter(MentalHealthRecord.mood_score >= min_score)
    if max_score is not None:
        query = query.filter(MentalHealthRecord.mood_score <= max_score)

    records = query.order_by(MentalHealthRecord.created_at.desc()).all()

    result = [
        {
            "id": r.id,
            "chat_id": r.chat_id,
            "mood_score": r.mood_score,
            "emotion_type": r.emotion_type,
            "description": r.description,
            "ai_context": r.ai_context,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
    return ok(result)


@router.get("/stats")
def get_stats(
    period: str | None = Query(default="month", description="统计周期: week/month/year"),
    emotion_type: str | None = Query(default=None, description="按情绪类型筛选"),
    min_score: int | None = Query(default=None, description="最低评分筛选 1-10"),
    max_score: int | None = Query(default=None, description="最高评分筛选 1-10"),
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取心理健康统计数据，用于 ECharts 可视化"""
    if not user:
        return ok({})

    now = datetime.utcnow()
    if period == "week":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0)
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0)
    else:  # month (default)
        start = now.replace(day=1, hour=0, minute=0, second=0)

    query = (
        db.query(MentalHealthRecord)
        .filter(
            MentalHealthRecord.user_id == user.get("user_id"),
            MentalHealthRecord.created_at >= start,
        )
    )
    if emotion_type:
        query = query.filter(MentalHealthRecord.emotion_type == emotion_type)
    if min_score is not None:
        query = query.filter(MentalHealthRecord.mood_score >= min_score)
    if max_score is not None:
        query = query.filter(MentalHealthRecord.mood_score <= max_score)

    records = query.order_by(MentalHealthRecord.created_at.asc()).all()

    # 1. 情绪评分趋势（按周期聚合）
    trend = _aggregate_trend(records, period or "month")

    # 2. 情绪类型分布（饼图/柱状图）
    emotion_count = {}
    emotion_scores = {}
    for r in records:
        emotion_count[r.emotion_type] = emotion_count.get(r.emotion_type, 0) + 1
        if r.emotion_type not in emotion_scores:
            emotion_scores[r.emotion_type] = []
        emotion_scores[r.emotion_type].append(r.mood_score)

    distribution = [
        {
            "name": em,
            "count": cnt,
            "avg_score": round(sum(emotion_scores[em]) / len(emotion_scores[em]), 1),
        }
        for em, cnt in emotion_count.items()
    ]

    # 3. 情绪评分分布（1-3 较差, 4-6 一般, 7-10 良好）
    level_count = {"较差": 0, "一般": 0, "良好": 0}
    for r in records:
        if r.mood_score <= 3:
            level_count["较差"] += 1
        elif r.mood_score <= 6:
            level_count["一般"] += 1
        else:
            level_count["良好"] += 1
    level_distribution = [
        {"name": k, "count": v} for k, v in level_count.items()
    ]

    # 4. 汇总
    scores = [r.mood_score for r in records]
    summary = {
        "total_records": len(records),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "max_score": max(scores) if scores else 0,
        "min_score": min(scores) if scores else 0,
        "dominant_emotion": max(emotion_count, key=emotion_count.get) if emotion_count else "",
    }

    return ok({
        "trend": trend,
        "distribution": distribution,
        "level_distribution": level_distribution,
        "summary": summary,
    })


@router.delete("/{record_id}")
def delete_record(
    record_id: int,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除某条心理健康记录"""
    if not user:
        return fail(401, "请先登录")
    record = db.query(MentalHealthRecord).filter(
        MentalHealthRecord.id == record_id,
        MentalHealthRecord.user_id == user.get("user_id"),
    ).first()
    if not record:
        return fail(404, "记录不存在")
    db.delete(record)
    db.commit()
    return ok(None, "已删除")
