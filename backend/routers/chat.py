import json
import asyncio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from models import ChatSession, ChatMessage
from schemas import SendMessageRequest, ok, fail
from auth import get_current_user
from llm_service import generate_stream

router = APIRouter(prefix="/api/chat", tags=["对话"])


def _check_ownership(session, user: dict | None) -> bool:
    """校验对话是否属于当前用户。session.user_id 为 NULL 视为匿名对话，不限制。"""
    if session.user_id is None:
        return True  # 匿名对话，任何人可访问
    if user is None:
        return False  # 有归属但未登录，拒绝
    return str(session.user_id) == str(user["user_id"])


@router.post("/create")
def create_chat(
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新的对话会话"""
    session = ChatSession(user_id=user["user_id"] if user else None)
    db.add(session)
    db.commit()
    db.refresh(session)
    return ok({"id": session.id, "chat_id": session.chat_id})


@router.post("/message")
async def send_message(
    body: SendMessageRequest,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发送消息（非流式），返回完整回复"""
    session = db.query(ChatSession).filter(ChatSession.chat_id == body.chat_id).first()
    if not session:
        return fail(404, "对话不存在")
    if not _check_ownership(session, user):
        return fail(403, "无权访问此对话")

    # 保存用户消息
    user_msg = ChatMessage(session_id=session.id, role="user", content=body.message)
    db.add(user_msg)
    db.commit()

    # 获取历史消息作为 LLM 上下文
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    context = [{"role": m.role, "content": m.content} for m in history]

    # 异步流式生成回复，收集完整结果
    full_response = ""
    async for chunk in generate_stream(context):
        if chunk == "":           # 完成信号
            break
        if chunk.startswith("\0"):
            full_response = chunk[1:]  # 去重修正：替换
        else:
            full_response += chunk

    # 保存 AI 回复
    ai_msg = ChatMessage(session_id=session.id, role="assistant", content=full_response)
    db.add(ai_msg)
    db.commit()

    # 返回完整历史
    db.refresh(session)
    chat_history = [{"role": m.role, "content": m.content} for m in session.messages]

    return ok({
        "response": full_response,
        "chat_history": chat_history,
    })


@router.post("/message/stream")
async def send_message_stream(
    body: SendMessageRequest,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发送消息（SSE 流式），逐步返回模型输出"""
    session = db.query(ChatSession).filter(ChatSession.chat_id == body.chat_id).first()
    if not session:
        return fail(404, "对话不存在")
    if not _check_ownership(session, user):
        return fail(403, "无权访问此对话")

    # 保存用户消息
    user_msg = ChatMessage(session_id=session.id, role="user", content=body.message)
    db.add(user_msg)
    db.commit()

    # 获取历史消息作为上下文
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    context = [{"role": m.role, "content": m.content} for m in history]

    # 收集完整回复（用于最后存储）
    full_text = []

    async def event_stream():
        cancelled = False
        try:
            async for chunk in generate_stream(context):
                if chunk == "":  # 完成信号
                    break
                if chunk.startswith("\0"):
                    # 去重修正：前端应替换最后一条 AI 消息，而非追加
                    correction = chunk[1:]
                    full_text.clear()
                    full_text.append(correction)
                    yield f"data: {json.dumps({'type': 'correction', 'content': correction}, ensure_ascii=False)}\n\n"
                else:
                    full_text.append(chunk)
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            # 客户端断开连接 — 删除已保存的用户消息，不保存 AI 回复
            cancelled = True
            db.delete(user_msg)
            db.commit()
            raise

        if not cancelled:
            # 保存 AI 回复到数据库
            complete = "".join(full_text)
            ai_msg = ChatMessage(session_id=session.id, role="assistant", content=complete)
            db.add(ai_msg)
            db.commit()

            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done', 'content': complete}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/list")
def list_chats(
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出当前用户的活跃对话（静态路径必须在参数化路径之前定义）"""
    if not user:
        return ok([])

    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user["user_id"])
        .order_by(ChatSession.created_at.desc())
        .all()
    )

    result = [
        {
            "id": s.id,
            "chat_id": s.chat_id,
            "title": s.title,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]
    return ok(result)


@router.get("/{chat_id}/history")
def get_history(
    chat_id: str,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取对话历史"""
    session = db.query(ChatSession).filter(ChatSession.chat_id == chat_id).first()
    if not session:
        return fail(404, "对话不存在")

    if not _check_ownership(session, user):
        return fail(403, "无权访问此对话")

    messages = [{"role": m.role, "content": m.content} for m in session.messages]
    return ok({"chat_id": chat_id, "messages": messages})


@router.delete("/{db_id}")
def delete_chat(
    db_id: int,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除对话及其所有消息"""
    session = db.query(ChatSession).filter(ChatSession.id == db_id).first()
    if not session:
        return fail(404, "对话不存在")
    if not _check_ownership(session, user):
        return fail(403, "无权访问此对话")
    # 级联删除：先删消息，再删会话（cascade 也会自动处理）
    db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete()
    db.delete(session)
    db.commit()
    return ok(None, "已删除")


@router.delete("/{db_id}/messages")
def clear_messages(
    db_id: int,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """清空对话中的所有消息"""
    session = db.query(ChatSession).filter(ChatSession.id == db_id).first()
    if not session:
        return fail(404, "对话不存在")
    if not _check_ownership(session, user):
        return fail(403, "无权访问此对话")
    db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete()
    db.commit()
    return ok(None, "已清空")


@router.put("/{db_id}/rename")
def rename_chat(
    db_id: int,
    body: dict,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重命名对话"""
    session = db.query(ChatSession).filter(ChatSession.id == db_id).first()
    if not session:
        return fail(404, "对话不存在")
    if not _check_ownership(session, user):
        return fail(403, "无权访问此对话")
    title = (body.get("title") or "").strip()
    if not title:
        return fail(400, "标题不能为空")
    session.title = title
    db.commit()
    return ok({"chat_id": session.chat_id, "title": title})
