"""
输入消毒工具 —— 防止 XSS 攻击

移除所有用户输入中的 HTML 标签，确保即使前端渲染层失效，
数据库中也不会存储可执行的脚本。
"""

import re
from json import loads, dumps
from starlette.types import ASGIApp, Scope, Receive, Send, Message


# 匹配所有 HTML 标签 <...>
_TAG_RE = re.compile(r"<[^>]*>")

# 不需要消毒的路径（文档、流式端点等）
_SKIP_PATHS = {"/docs", "/redoc", "/openapi.json"}


def strip_html(text: str) -> str:
    """移除字符串中的所有 HTML 标签"""
    if not isinstance(text, str):
        return text
    return _TAG_RE.sub("", text)


class SanitizeMiddleware:
    """
    纯 ASGI 请求体消毒中间件

    在请求进入路由之前，对 JSON 请求体中的字符串递归去除 HTML 标签。
    使用纯 ASGI 实现，兼容流式响应（SSE）。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # 只处理 HTTP 请求
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # 跳过不需要消毒的路径
        if path in _SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        # 检查 Content-Type
        content_type = ""
        for k, v in scope.get("headers", []):
            if k == b"content-type":
                content_type = v.decode("latin-1")
                break

        if "application/json" not in content_type:
            await self.app(scope, receive, send)
            return

        # 收集请求体
        body_chunks = []
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.request":
                body_chunks.append(message.get("body", b""))
                more_body = message.get("more_body", False)
            else:
                # 非 http.request 消息（如 http.disconnect），直接放行
                await self.app(scope, _fake_receive(message), send)
                return

        raw_body = b"".join(body_chunks)

        if not raw_body:
            # 空请求体，用原始 receive 放行
            await self.app(scope, _empty_receive(body_chunks), send)
            return

        # 消毒 JSON
        try:
            data = loads(raw_body)
            cleaned = _sanitize_dict(data)
            sanitized_body = dumps(cleaned, ensure_ascii=False).encode("utf-8")
        except Exception:
            sanitized_body = raw_body

        # 构造新的 receive，首次返回消毒后的 body，后续正常
        body_sent = False

        async def sanitized_receive() -> Message:
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {
                    "type": "http.request",
                    "body": sanitized_body,
                    "more_body": False,
                }
            # 后续 receive 调用返回 disconnect
            while True:
                msg = await receive()
                return msg

        await self.app(scope, sanitized_receive, send)


def _fake_receive(message: Message) -> Receive:
    """返回一个只包含给定消息的 receive 函数"""
    sent = False

    async def receive() -> Message:
        nonlocal sent
        if not sent:
            sent = True
            return message
        # 等待 disconnect
        import asyncio
        while True:
            await asyncio.sleep(60)

    return receive


def _empty_receive(chunks: list[bytes]) -> Receive:
    """对空请求体，返回收集到的消息序列"""
    idx = -1

    async def receive() -> Message:
        nonlocal idx
        idx += 1
        if idx < len(chunks):
            return {"type": "http.request", "body": chunks[idx], "more_body": False}
        import asyncio
        while True:
            await asyncio.sleep(60)

    return receive


def _sanitize_dict(obj):
    """递归消毒字典/列表/字符串"""
    if isinstance(obj, str):
        return strip_html(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_dict(item) for item in obj]
    return obj
