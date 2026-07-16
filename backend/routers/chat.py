import json
import asyncio
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from models import ChatSession, ChatMessage
from schemas import SendMessageRequest, ok, fail
from auth import get_current_user, require_user
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
    if (e := check_ownership(session, user)): return e

    # 幂等性检查
    if body.idempotency_key:
        existing = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.session_id == session.id,
                ChatMessage.idempotency_key == body.idempotency_key,
                ChatMessage.role == "user",
            )
            .first()
        )
        if existing:
            ai_reply = (
                db.query(ChatMessage)
                .filter(
                    ChatMessage.session_id == session.id,
                    ChatMessage.role == "assistant",
                    ChatMessage.id > existing.id,
                )
                .order_by(ChatMessage.created_at.desc())
                .first()
            )
            if ai_reply and ai_reply.content:
                return ok({
                    "response": ai_reply.content,
                    "cached": True,
                    "chat_history": [{"role": m.role, "content": m.content} for m in session.messages],
                })

    kwargs = {"session_id": session.id, "role": "user", "content": body.message}
    if body.idempotency_key:
        kwargs["idempotency_key"] = body.idempotency_key
    user_msg = ChatMessage(**kwargs)
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
            full_response = chunk[12:]
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


def _sse_event(event_id: int, data: dict) -> str:
    """构造标准 SSE 事件（含 id 字段，支持 Last-Event-ID 重连）"""
    return f"id: {event_id}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/message/stream")
async def send_message_stream(
    body: SendMessageRequest,
    request: Request,
    user: dict | None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发送消息（SSE 流式），逐步返回模型输出

    支持 Last-Event-ID 断线重连：
    - 客户端在重连请求中携带 Last-Event-ID 头
    - 服务端跳过创建 user 消息，基于已保存的部分 AI 回复继续流式输出
    """
    session = db.query(ChatSession).filter(ChatSession.chat_id == body.chat_id).first()
    if not session:
        return fail(404, "对话不存在")
    if (e := check_ownership(session, user)): return e

    is_resume = body.resume or (request.headers.get("Last-Event-ID") is not None)

    # 幂等性检查：相同 idempotency_key 不重复创建用户消息
    idempotent_skip = False
    existing_user_msg = None
    if body.idempotency_key and not is_resume:
        existing_user_msg = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.session_id == session.id,
                ChatMessage.idempotency_key == body.idempotency_key,
                ChatMessage.role == "user",
            )
            .first()
        )
        if existing_user_msg:
            idempotent_skip = True
            print(f"[幂等] idempotency_key={body.idempotency_key} 已存在，跳过创建用户消息")

    if not is_resume and not idempotent_skip:
        # 正常请求：创建用户消息（带幂等令牌）
        kwargs = {"session_id": session.id, "role": "user", "content": body.message}
        if body.idempotency_key:
            kwargs["idempotency_key"] = body.idempotency_key
        user_msg = ChatMessage(**kwargs)
        db.add(user_msg)
        db.commit()

    # 查找可恢复的部分 AI 回复；幂等命中时返回已有完成回复
    partial_ai_msg = None
    cached_full_response = None

    if idempotent_skip and existing_user_msg:
        # 查找该用户消息之后是否有 AI 回复
        last_ai = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.session_id == session.id,
                ChatMessage.role == "assistant",
                ChatMessage.id > existing_user_msg.id,
            )
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        if last_ai and last_ai.completed:
            # 已有完成的 AI 回复 → 直接返回缓存，不重新生成
            cached_full_response = last_ai.content
        elif last_ai:
            # AI 消息未完成（被中断）→ 当作续接处理
            is_resume = True
            partial_ai_msg = last_ai

    if is_resume and not partial_ai_msg:
        partial_ai_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id, ChatMessage.role == "assistant")
            .order_by(ChatMessage.created_at.desc())
            .first()
        )

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    context = [{"role": m.role, "content": m.content} for m in history]

    # 续接时：用已保存的部分内容作为起点
    full_text: list[str] = []
    if partial_ai_msg and partial_ai_msg.content:
        full_text = [partial_ai_msg.content]

    async def event_stream():
        nonlocal full_text
        event_id = 0
        cancelled = False

        # 幂等命中：直接返回缓存的完成回复
        if cached_full_response:
            yield _sse_event(1, {'type': 'content', 'content': cached_full_response})
            yield _sse_event(2, {'type': 'done', 'content': cached_full_response, 'interrupted': False, 'cached': True})
            return

        try:
            async for chunk in generate_stream(context):
                event_id += 1
                if chunk == "":
                    break
                # ---- \x01 前缀事件（工具调用 / MCP / 校正 / 完成） ----
                if chunk.startswith("\x01"):
                    if chunk.startswith("\x01mcp\x01"):
                        payload = chunk[5:]
                        yield _sse_event(event_id, {'type': 'mcp_event', 'payload': json.loads(payload)})
                    elif chunk.startswith("\x01tool_call\x01"):
                        payload = chunk[11:]
                        yield _sse_event(event_id, {'type': 'tool_call', 'payload': json.loads(payload)})
                    elif chunk.startswith("\x01tool_result\x01"):
                        payload = chunk[13:]
                        yield _sse_event(event_id, {'type': 'tool_result', 'payload': json.loads(payload)})
                    elif chunk.startswith("\x01correction\x01"):
                        correction = chunk[12:]
                        full_text.clear()
                        full_text.append(correction)
                        yield _sse_event(event_id, {'type': 'correction', 'content': correction})
                    elif chunk.startswith("\x01done\x01"):
                        payload = chunk[6:]
                        data = json.loads(payload)
                        yield _sse_event(event_id, {'type': 'done', 'content': ''.join(full_text), 'tool_events': data.get('tool_events', [])})
                    else:
                        full_text.append(chunk)
                        yield _sse_event(event_id, {'type': 'content', 'content': chunk})
                else:
                    full_text.append(chunk)
                    yield _sse_event(event_id, {'type': 'content', 'content': chunk})
        except asyncio.CancelledError:
            # 连接断开 —— 保存已生成的部分内容供重连续接（标记为未完成）
            partial = "".join(full_text)
            if partial.strip():
                if partial_ai_msg:
                    partial_ai_msg.content = partial
                    partial_ai_msg.completed = False
                else:
                    ai_msg = ChatMessage(session_id=session.id, role="assistant", content=partial, completed=False)
                    db.add(ai_msg)
                db.commit()
                yield _sse_event(event_id, {'type': 'done', 'content': partial, 'interrupted': True})
            raise
        except Exception as e:
            yield _sse_event(event_id, {'type': 'error', 'error': str(e)})
            return

        if not cancelled:
            complete = "".join(full_text)
            if partial_ai_msg:
                # 续接完成：更新已有的部分消息并标记完成
                partial_ai_msg.content = complete
                partial_ai_msg.completed = True
            else:
                ai_msg = ChatMessage(session_id=session.id, role="assistant", content=complete, completed=True)
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
                event_id += 1
                yield _sse_event(event_id, {'type': 'form_trigger', 'ai_context': complete[:500], 'msg_id': form_msg.id})

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
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    """列出当前用户的活跃对话"""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user["user_id"])
        .order_by(ChatSession.is_pinned.desc(), ChatSession.pinned_at.desc(), ChatSession.created_at.desc())
        .all()
    )
    result = [
        {
            "id": s.id,
            "chat_id": s.chat_id,
            "title": s.title,
            "is_pinned": s.is_pinned,
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
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    """获取对话历史"""
    session = db.query(ChatSession).filter(ChatSession.chat_id == chat_id).first()
    if not session:
        return fail(404, "对话不存在")
    if (e := check_ownership(session, user)): return e
    messages = [{"role": m.role, "content": m.content, "id": m.id, "created_at": m.created_at.isoformat() if m.created_at else None} for m in session.messages]
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
    if (e := check_ownership(session, user)): return e
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
    if (e := check_ownership(session, user)): return e
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
    if (e := check_ownership(session, user)): return e
    title = (body.get("title") or "").strip()
    if not title:
        return fail(400, "标题不能为空")
    session.title = title
    db.commit()
    return ok({"chat_id": session.chat_id, "title": title})


@router.post("/{chat_id}/pin")
def pin_chat(
    chat_id: str,
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    """置顶对话"""
    session = db.query(ChatSession).filter(ChatSession.chat_id == chat_id).first()
    if not session:
        return fail(404, "对话不存在")
    if not check_ownership(session, user):
        return fail(403, "无权操作此对话")
    from datetime import datetime
    session.is_pinned = True
    session.pinned_at = datetime.utcnow()
    db.commit()
    return ok(None, "已置顶")


@router.post("/{chat_id}/unpin")
def unpin_chat(
    chat_id: str,
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    """取消置顶"""
    session = db.query(ChatSession).filter(ChatSession.chat_id == chat_id).first()
    if not session:
        return fail(404, "对话不存在")
    if not check_ownership(session, user):
        return fail(403, "无权操作此对话")
    session.is_pinned = False
    session.pinned_at = None
    db.commit()
    return ok(None, "已取消置顶")


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
    if not session:
        return fail(404, "对话不存在")
    if (e := check_ownership(session, user)):
        return e
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
    if (e := check_ownership(session, user)): return e

    # 找到最后一条 AI 回复（可能后面还有 form 消息）
    last_ai_msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id, ChatMessage.role == "assistant")
        .order_by(ChatMessage.created_at.desc())
        .first()
    )
    if not last_ai_msg:
        return fail(400, "没有可重新生成的 AI 回复")

    # 找到上一条用户消息（id 在 AI 消息之前的最后一条 user 消息）
    prev_user_msg = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session.id,
            ChatMessage.role == "user",
            ChatMessage.id < last_ai_msg.id,
        )
        .order_by(ChatMessage.created_at.desc())
        .first()
    )
    if not prev_user_msg:
        return fail(400, "没有找到对应的用户消息")

    # 删除最后一条 AI 回复
    db.delete(last_ai_msg)
    db.commit()

    return ok({"trigger_message": prev_user_msg.content})
