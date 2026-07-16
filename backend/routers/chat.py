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
from routers.chat_utils import should_trigger_form, check_ownership

router = APIRouter(prefix="/api/chat", tags=["对话"])


@router.post("/create")
def create_chat(
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新的对话会话"""
    if not user:
        return fail(401, "请先登录")
    session = ChatSession(user_id=user["user_id"])
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
    if not check_ownership(session, user):
        return fail(403, "无权访问此对话")

    user_msg = ChatMessage(session_id=session.id, role="user", content=body.message)
    db.add(user_msg)
    db.commit()

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    context = [{"role": m.role, "content": m.content} for m in history]

    full_response = ""
    async for chunk in generate_stream(context):
        if chunk == "":
            break
        if chunk.startswith("\x01correction\x01"):
            full_response = chunk[14:]
        elif chunk.startswith("\x01done\x01"):
            pass  # 流结束信号，忽略
        elif chunk.startswith("\x01"):
            pass  # 工具调用等事件，非流式模式忽略
        else:
            full_response += chunk

    ai_msg = ChatMessage(session_id=session.id, role="assistant", content=full_response)
    db.add(ai_msg)
    db.commit()
    db.refresh(session)

    return ok({
        "response": full_response,
        "chat_history": [{"role": m.role, "content": m.content} for m in session.messages],
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
    if not check_ownership(session, user):
        return fail(403, "无权访问此对话")

    user_msg = ChatMessage(session_id=session.id, role="user", content=body.message)
    db.add(user_msg)
    db.commit()

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    context = [{"role": m.role, "content": m.content} for m in history]

    full_text: list[str] = []

    async def event_stream():
        cancelled = False
        try:
            async for chunk in generate_stream(context):
                if chunk == "":
                    break
                # ---- \x01 前缀事件（工具调用 / MCP / 校正 / 完成） ----
                if chunk.startswith("\x01"):
                    if chunk.startswith("\x01mcp\x01"):
                        payload = chunk[6:]
                        yield f"data: {json.dumps({'type': 'mcp_event', 'payload': json.loads(payload)}, ensure_ascii=False)}\n\n"
                    elif chunk.startswith("\x01tool_call\x01"):
                        payload = chunk[12:]
                        yield f"data: {json.dumps({'type': 'tool_call', 'payload': json.loads(payload)}, ensure_ascii=False)}\n\n"
                    elif chunk.startswith("\x01tool_result\x01"):
                        payload = chunk[15:]
                        yield f"data: {json.dumps({'type': 'tool_result', 'payload': json.loads(payload)}, ensure_ascii=False)}\n\n"
                    elif chunk.startswith("\x01correction\x01"):
                        correction = chunk[14:]
                        full_text.clear()
                        full_text.append(correction)
                        yield f"data: {json.dumps({'type': 'correction', 'content': correction}, ensure_ascii=False)}\n\n"
                    elif chunk.startswith("\x01done\x01"):
                        payload = chunk[7:]
                        data = json.loads(payload)
                        yield f"data: {json.dumps({'type': 'done', 'content': ''.join(full_text), 'tool_events': data.get('tool_events', [])}, ensure_ascii=False)}\n\n"
                    else:
                        # 未知前缀事件，当作普通内容
                        full_text.append(chunk)
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
                else:
                    full_text.append(chunk)
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            # 用户中断 —— 保留已生成的部分内容到数据库
            partial = "".join(full_text)
            if partial.strip():
                ai_msg = ChatMessage(session_id=session.id, role="assistant", content=partial)
                db.add(ai_msg)
                db.commit()
                yield f"data: {json.dumps({'type': 'done', 'content': partial, 'interrupted': True}, ensure_ascii=False)}\n\n"
            raise
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
            return

        if not cancelled:
            complete = "".join(full_text)
            ai_msg = ChatMessage(session_id=session.id, role="assistant", content=complete)
            db.add(ai_msg)
            db.commit()

            if should_trigger_form(body.message, complete):
                form_state = json.dumps({
                    "submitted": False,
                    "ai_context": complete[:500],
                }, ensure_ascii=False)
                form_msg = ChatMessage(session_id=session.id, role="form", content=form_state)
                db.add(form_msg)
                db.commit()
                db.refresh(form_msg)
                yield f"data: {json.dumps({'type': 'form_trigger', 'ai_context': complete[:500], 'msg_id': form_msg.id}, ensure_ascii=False)}\n\n"

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
    """列出当前用户的活跃对话"""
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


@router.delete("/clear-all")
def clear_all_chats(
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """清空当前账号下所有对话及消息"""
    if not user:
        return fail(401, "请先登录")
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user["user_id"])
        .all()
    )
    for s in sessions:
        db.query(ChatMessage).filter(ChatMessage.session_id == s.id).delete()
        db.delete(s)
    db.commit()
    return ok(None, "已清空所有对话")


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
    if not check_ownership(session, user):
        return fail(403, "无权访问此对话")
    messages = [{"role": m.role, "content": m.content, "id": m.id} for m in session.messages]
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
    if not check_ownership(session, user):
        return fail(403, "无权访问此对话")
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
    if not check_ownership(session, user):
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
    if not check_ownership(session, user):
        return fail(403, "无权访问此对话")
    title = (body.get("title") or "").strip()
    if not title:
        return fail(400, "标题不能为空")
    session.title = title
    db.commit()
    return ok({"chat_id": session.chat_id, "title": title})


@router.put("/message/{msg_id}")
def update_message(
    msg_id: int,
    body: dict,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新某条消息的内容（用于持久化 form 表单的提交状态）"""
    msg = db.query(ChatMessage).filter(ChatMessage.id == msg_id).first()
    if not msg:
        return fail(404, "消息不存在")
    session = db.query(ChatSession).filter(ChatSession.id == msg.session_id).first()
    if not session or not check_ownership(session, user):
        return fail(403, "无权修改此消息")
    msg.content = body.get("content", msg.content)
    db.commit()
    return ok(None, "已更新")


@router.post("/{chat_id}/regenerate")
def regenerate_message(
    chat_id: str,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除最后一条 AI 回复，返回触发它的用户消息（供前端重新生成）"""
    session = db.query(ChatSession).filter(ChatSession.chat_id == chat_id).first()
    if not session:
        return fail(404, "对话不存在")
    if not check_ownership(session, user):
        return fail(403, "无权访问此对话")

    # 找到最后一条消息
    last_msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .first()
    )
    if not last_msg or last_msg.role != "assistant":
        return fail(400, "没有可重新生成的 AI 回复")

    # 找到上一条用户消息
    prev_user_msg = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session.id,
            ChatMessage.role == "user",
            ChatMessage.id < last_msg.id,
        )
        .order_by(ChatMessage.created_at.desc())
        .first()
    )
    if not prev_user_msg:
        return fail(400, "没有找到对应的用户消息")

    # 删除最后一条 AI 回复
    db.delete(last_msg)
    db.commit()

    return ok({"trigger_message": prev_user_msg.content})
