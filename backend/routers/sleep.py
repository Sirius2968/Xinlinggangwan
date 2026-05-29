"""
睡眠追踪路由 —— 记录 & 查询睡眠数据
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import SleepRecord
from schemas import SleepRecordRequest, ok, fail
from auth import get_current_user

router = APIRouter(prefix="/api/sleep", tags=["睡眠追踪"])


def _calc_hours(bed_time: str, wake_time: str) -> int:
    try:
        bh, bm = map(int, bed_time.strip().split(":"))
        wh, wm = map(int, wake_time.strip().split(":"))
        bm_total = bh * 60 + bm
        wm_total = wh * 60 + wm
        if wm_total <= bm_total:
            wm_total += 24 * 60
        return (wm_total - bm_total) // 60
    except Exception:
        return 0


@router.post("/track")
def track_sleep(
    req: SleepRecordRequest,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """记录一晚的睡眠数据"""
    duration = _calc_hours(req.bed_time, req.wake_time)

    record = SleepRecord(
        user_id=user.get("user_id") if user else None,
        chat_id=req.chat_id,
        bed_time=req.bed_time,
        wake_time=req.wake_time,
        quality=req.quality,
        duration_hours=duration,
        issues=req.issues,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    quality_label = "较差" if req.quality <= 3 else ("一般" if req.quality <= 6 else "良好")
    return ok(
        {
            "id": record.id,
            "duration_hours": duration,
            "quality_label": quality_label,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        },
        f"睡眠数据已记录：{req.bed_time}→{req.wake_time}，约{duration}小时，质量{quality_label}",
    )


@router.get("/records")
def get_sleep_records(
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的所有睡眠记录"""
    if not user:
        return ok([])
    records = (
        db.query(SleepRecord)
        .filter(SleepRecord.user_id == user.get("user_id"))
        .order_by(SleepRecord.created_at.desc())
        .all()
    )
    result = [
        {
            "id": r.id,
            "chat_id": r.chat_id,
            "bed_time": r.bed_time,
            "wake_time": r.wake_time,
            "quality": r.quality,
            "duration_hours": r.duration_hours,
            "issues": r.issues,
            "tips_given": r.tips_given,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
    return ok(result)


@router.delete("/{record_id}")
def delete_sleep_record(
    record_id: int,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除某条睡眠记录"""
    if not user:
        return fail(401, "请先登录")
    record = db.query(SleepRecord).filter(
        SleepRecord.id == record_id,
        SleepRecord.user_id == user.get("user_id"),
    ).first()
    if not record:
        return fail(404, "记录不存在")
    db.delete(record)
    db.commit()
    return ok(None, "已删除")
