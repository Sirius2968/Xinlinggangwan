"""
LLM 服务 —— DeepSeek 驱动的心理咨询对话 + Markdown 输出

工具：
1. 本地工具：breathing_exercise, mood_tracker
2. MCP 工具（web_search）：互联网搜索

上下文窗口：保留最近 12 条消息，更早的自动压缩为摘要。
"""

import json
import os
import sys
import asyncio
import threading
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI

from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession
from mcp import StdioServerParameters

load_dotenv()

# ============================================================
# 配置
# ============================================================
STREAM_DELAY = 0.02
MAX_CONTEXT_MSGS = 12
MCP_SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_web_search.py")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# LLM 实例延迟创建（避免模块导入时 API Key 未设置导致崩溃）
_summary_llm = None


def _get_summary_llm():
    global _summary_llm
    if _summary_llm is None:
        _summary_llm = ChatOpenAI(
            model=DEEPSEEK_MODEL, temperature=0.3, max_tokens=150,
            api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_API_BASE,
        )
    return _summary_llm


# ============================================================
# 本地工具：呼吸练习
# ============================================================
@tool
def breathing_exercise(technique: str = "4-7-8") -> str:
    """提供呼吸练习指导。technique: 4-7-8, box, calm"""
    exercises = {
        "4-7-8": "**4-7-8 呼吸法**\n\n用鼻子深深吸气 4 秒 → 屏住呼吸 7 秒 → 用嘴巴慢慢呼气 8 秒。重复 3-5 次。",
        "box": "**方形呼吸法**\n\n吸气 4 秒 → 屏住 4 秒 → 呼气 4 秒 → 停顿 4 秒。循环重复。",
        "calm": "**放松呼吸法**\n\n吸气 4 秒，呼气 6 秒。延长呼气可激活副交感神经，帮助身体放松。",
    }
    return exercises.get(technique, exercises["4-7-8"])


# ============================================================
# 本地工具：情绪追踪
# ============================================================
@tool
def mood_tracker(mood: str, intensity: int = 5) -> str:
    """帮助用户记录和理解情绪。mood: sad/anxious/angry/happy/tired。intensity: 1-10"""
    suggestions = {
        "sad": ["试着写下让你感到悲伤的事情", "做一些能让你感到温暖的小事", "和信任的朋友聊聊天"],
        "anxious": ["进行深呼吸练习", "尝试正念冥想", "把担心的事情写下来"],
        "angry": ["先离开让你生气的环境", "进行一些身体运动释放能量", "练习换位思考"],
        "happy": ["记录下让你开心的原因", "和他人分享这份喜悦", "感谢生活中的小确幸"],
        "tired": ["给自己一些休息的时间", "做一些轻度运动提升能量", "检查睡眠质量"],
    }
    mood_lower = mood.lower()
    if mood_lower in suggestions:
        lines = "\n".join(f"- {s}" for s in suggestions[mood_lower])
        return f"我理解你现在感到 **{mood}**（强度：{intensity}/10）。这里有一些建议：\n\n{lines}"
    return f"感谢你记录了当前的情绪状态（{mood}，强度：{intensity}/10）。了解自己的情绪是自我关怀的重要一步。"


# ============================================================
# MCP 客户端会话管理器
# ============================================================
class _MCPSessionManager:
    """后台线程维持与 MCP Web Search Server 的 stdio 连接"""

    def __init__(self):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._session: ClientSession | None = None
        self._tools: list = []
        self._ready = threading.Event()
        self._error: str | None = None
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="mcp-search")
        self._thread.start()
        if not self._ready.wait(timeout=15):
            raise RuntimeError(f"MCP 会话初始化超时: {self._error or '未知错误'}")

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._init_and_keep_alive())
        except Exception as e:
            self._error = str(e)
            self._ready.set()

    async def _init_and_keep_alive(self):
        server_params = StdioServerParameters(command=sys.executable, args=[MCP_SERVER_PATH])
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self._session = session
                await session.initialize()
                result = await session.list_tools()
                self._tools = result.tools
                self._ready.set()
                while True:
                    await asyncio.sleep(3600)

    def list_tools(self) -> list:
        return self._tools

    def call_tool_sync(self, name: str, arguments: dict) -> str:
        async def _call():
            result = await self._session.call_tool(name, arguments)
            return result.content[0].text
        future = asyncio.run_coroutine_threadsafe(_call(), self._loop)
        return future.result(timeout=30)


# ============================================================
# 初始化工具
# ============================================================
_mcp_manager: _MCPSessionManager | None = None
LLM_WITH_TOOLS = None
ALL_TOOLS: list = []
TOOL_BY_NAME: dict[str, callable] = {}


async def _init_tools():
    global _mcp_manager, LLM_WITH_TOOLS, ALL_TOOLS, TOOL_BY_NAME
    if LLM_WITH_TOOLS is not None:
        return

    if not DEEPSEEK_API_KEY:
        raise ValueError("DeepSeek API Key 未配置，请在 .env 文件中设置 DEEPSEEK_API_KEY")

    ALL_TOOLS = [breathing_exercise, mood_tracker]

    loop = asyncio.get_running_loop()
    _mcp_manager = await loop.run_in_executor(None, _MCPSessionManager)
    mcp_tools = _mcp_manager.list_tools()
    print(f"[LLM] MCP 已连接，获取工具: {[t.name for t in mcp_tools]}")

    for mcp_tool in mcp_tools:
        tool_name = mcp_tool.name
        def make_tool_fn(name):
            def tool_fn(**kwargs):
                result = _mcp_manager.call_tool_sync(name, kwargs)
                return result
            return tool_fn
        fn = make_tool_fn(tool_name)
        fn.__name__ = tool_name
        fn.__doc__ = mcp_tool.description or ""
        lc_tool = tool(fn)
        ALL_TOOLS.append(lc_tool)

    for t in ALL_TOOLS:
        TOOL_BY_NAME[t.name] = t

    LLM_WITH_TOOLS = ChatOpenAI(
        model=DEEPSEEK_MODEL, temperature=0.7, max_tokens=800,
        api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_API_BASE,
    ).bind_tools(ALL_TOOLS)

    print(f"[LLM] 已绑定 {len(ALL_TOOLS)} 个工具: {list(TOOL_BY_NAME.keys())}")


# ============================================================
# 系统提示词 —— 使用 Markdown 输出
# ============================================================
SYSTEM_PROMPT = """
你是一位专业、温暖、富有同理心的心理咨询师。你的唯一职责是提供心理支持和情感关怀。

**核心职责：**
1. 倾听与共情：认真倾听用户的情绪表达，表达理解和关心
2. 情感支持：给予温暖的安慰和鼓励
3. 专业建议：提供科学、实用的心理调节方法
4. 引导反思：帮助用户探索内心，找到问题根源
5. 保持边界：不提供医疗诊断，建议严重情况寻求专业帮助

**回复格式要求（Markdown）：**
- 使用 Markdown 格式组织回复，让内容层次清晰、易于阅读
- 用 `**加粗**` 突出重点概念和建议
- 使用有序/无序列表整理步骤和多条建议
- 适当使用标题（`###`）分隔不同主题
- 回复末尾可用 `---` 分隔线后附加参考资料

**重要规则：**
- 不提供学术解答：专注于情感和心理层面的支持
- 温和转移：当话题偏离心理主题时，用关怀的方式引导回到情绪和感受上
- 简洁回复：控制在150字左右，复杂问题可适当展开
- 不主动展开话题：只回答用户的问题，可适当引导用户探索自己的情感和感受
- 绝对禁止重复：不能重复之前说过的内容，每轮对话给全新回应
- 利用历史：如果对话开头附带"历史对话摘要"，基于摘要理解用户背景
- 对敏感信息持回避态度

**工具使用规则：**
- 当用户询问"怎么改善""有什么方法""如何缓解""该怎么办"等心理健康方法时，调用 `web_search` 工具搜索相关资料，将搜索结果自然地融入回复末尾
- 当用户情绪明显低落或焦虑时，主动提供 `breathing_exercise` 呼吸指导
- 当用户表达明确情绪时，建议使用 `mood_tracker` 记录

**引导记录情绪：**
当你感知到用户情绪出现好转时（从焦虑变得平静、从悲伤中找到希望），请在回复末尾自然地建议记录心情。参考话术：'看来你的心情好了许多，要不要记录一下今天的心情呢？'
注意：如果上次已建议过，不要再提。
"""


# ============================================================
# 去重
# ============================================================
def _deduplicate(text: str) -> str:
    """去除连续重复句子"""
    if not text:
        return text
    sentences = text.split("。")
    result = []
    last = ""
    for s in sentences:
        s = s.strip()
        if s and s != last:
            result.append(s)
            last = s
    text = "。".join(result) + ("。" if text.endswith("。") else "")
    # 长段落重复检测
    for pat_len in range(len(text) // 2, 9, -1):
        i = 0
        while i <= len(text) - 2 * pat_len:
            pat = text[i:i + pat_len]
            nxt = text[i + pat_len:i + 2 * pat_len]
            if pat == nxt:
                text = text[:i + pat_len] + text[i + 2 * pat_len:]
            else:
                i += 1
    return text.strip()


# ============================================================
# 上下文窗口管理
# ============================================================
async def _summarize_old_messages(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        role = "用户" if m["role"] == "user" else "咨询师"
        lines.append(f"{role}：{m['content'][:120]}")
    convo = "\n".join(lines)
    try:
        resp = await _get_summary_llm().ainvoke([
            HumanMessage(content=f"请用30字以内的一句话，概括下面这段心理咨询对话中用户的主要问题和情绪变化：\n{convo}\n\n一句话摘要："),
        ])
        return resp.content.strip()
    except Exception:
        topics = [m["content"][:30] for m in messages if m["role"] == "user"]
        return "、".join(topics[-3:])


async def _prepare_context(full_context: list[dict]) -> list[dict]:
    if len(full_context) <= MAX_CONTEXT_MSGS:
        return full_context
    recent = full_context[-MAX_CONTEXT_MSGS:]
    old = full_context[:-MAX_CONTEXT_MSGS]
    summary = await _summarize_old_messages(old)
    if not summary:
        return recent
    recent[0] = dict(recent[0])
    recent[0]["content"] = f"[历史对话摘要：{summary}]\n\n{recent[0]['content']}"
    return recent


# ============================================================
# 搜索触发关键词
# ============================================================
_SEARCH_KEYWORDS = [
    "焦虑", "抑郁", "压力", "缓解", "改善", "方法", "怎么办",
    "正念", "冥想", "呼吸", "放松", "CBT", "认知行为",
    "运动", "睡眠", "失眠", "情绪调节", "怎么调节",
    "如何应对", "怎么处理", "怎么改善", "自我关怀", "抗压",
    "治疗", "疗法", "建议", "技巧", "策略",
]


def _should_search(user_message: str) -> bool:
    return bool(user_message) and any(kw in user_message for kw in _SEARCH_KEYWORDS)


# ============================================================
# 公开接口：流式生成回复
# ============================================================
async def generate_stream(context: list[dict]):
    await _init_tools()
    context = await _prepare_context(context)

    lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for m in context:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))

    full_text = ""
    sent_text = ""

    # 收集工具调用日志（供开发者面板查看）
    tool_events: list[dict] = []

    try:
        # 检测是否需要搜索，通过 MCP 获取结果
        last_user_msg = next((m["content"] for m in reversed(context) if m["role"] == "user"), "")
        if _should_search(last_user_msg) and "web_search" in TOOL_BY_NAME:
            matched = [kw for kw in _SEARCH_KEYWORDS if kw in last_user_msg]
            query = "心理健康 " + " ".join(matched[:3]) if matched else last_user_msg[:30]
            try:
                loop = asyncio.get_running_loop()
                search_text = await loop.run_in_executor(
                    None, _mcp_manager.call_tool_sync, "web_search",
                    {"query": query, "max_results": 3},
                )
                mcp_event = {"name": "web_search", "type": "mcp_auto", "query": query, "ok": False}
                if search_text and "未找到" not in search_text and "连接失败" not in search_text:
                    lc_messages[-1] = HumanMessage(content=(
                        last_user_msg +
                        "\n\n[系统已自动搜索相关资料，请将以下搜索结果自然地融入回复末尾]" +
                        "\n" + search_text
                    ))
                    mcp_event["ok"] = True
                tool_events.append(mcp_event)
                yield f"\x01mcp\x01{json.dumps(mcp_event, ensure_ascii=False)}"
            except Exception as e:
                print(f"[LLM] 搜索失败: {e}")
                tool_events.append({"name": "web_search", "type": "mcp_auto", "query": query, "ok": False, "error": str(e)})
                yield f"\x01mcp\x01{json.dumps({'name': 'web_search', 'type': 'mcp_auto', 'query': query, 'ok': False, 'error': str(e)}, ensure_ascii=False)}"

        response = await LLM_WITH_TOOLS.ainvoke(lc_messages)

        tool_calls = getattr(response, "tool_calls", None)
        if not tool_calls:
            tool_calls = response.additional_kwargs.get("tool_calls", []) if hasattr(response, "additional_kwargs") else []

        if tool_calls:
            print(f"[LLM] 工具调用: {[tc.get('name', '?') for tc in tool_calls]}")
            lc_messages.append(response)
            for tc in tool_calls:
                tc_name = tc.get("name", "")
                tc_args = tc.get("args", {})
                tc_id = tc.get("id", "call_1")

                # 通知前端：工具被调用
                tc_event = {"name": tc_name, "type": "tool_call", "args": tc_args}
                tool_events.append(tc_event)
                yield f"\x01tool_call\x01{json.dumps(tc_event, ensure_ascii=False)}"

                if tc_name in TOOL_BY_NAME:
                    try:
                        tool_result = TOOL_BY_NAME[tc_name].invoke(tc_args)
                        lc_messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc_id))
                        yield f"\x01tool_result\x01{json.dumps({'name': tc_name, 'ok': True}, ensure_ascii=False)}"
                    except Exception as e:
                        lc_messages.append(ToolMessage(content=f"工具调用失败：{e}", tool_call_id=tc_id))
                        yield f"\x01tool_result\x01{json.dumps({'name': tc_name, 'ok': False, 'error': str(e)}, ensure_ascii=False)}"

            async for chunk in LLM_WITH_TOOLS.astream(lc_messages):
                if hasattr(chunk, "content") and chunk.content:
                    if isinstance(chunk.content, str):
                        full_text += chunk.content
                        new_part = full_text[len(sent_text):]
                        if new_part:
                            sent_text = full_text
                            await asyncio.sleep(STREAM_DELAY)
                            yield new_part
        else:
            content = response.content if hasattr(response, "content") else ""
            if isinstance(content, str) and content:
                full_text = content
                chunk_size = 15
                pos = 0
                while pos < len(content):
                    end = min(pos + chunk_size, len(content))
                    yield content[pos:end]
                    pos = end
                    await asyncio.sleep(STREAM_DELAY)

        final = _deduplicate(full_text)
        if len(final) < len(sent_text):
            yield f"\x01correction\x01{final}"
        yield f"\x01done\x01{json.dumps({'tool_events': tool_events}, ensure_ascii=False)}"

    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"[LLM] 异常: {e}")
        yield f"抱歉，AI服务暂时出现问题：{str(e)}"
        yield "\x01done\x01{}"
