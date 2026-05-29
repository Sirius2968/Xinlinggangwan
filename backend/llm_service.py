"""
LLM 服务 —— DeepSeek 驱动的心理咨询对话

工具分为两类：
1. 本地工具（@tool 直接定义）：breathing_exercise, mood_tracker
2. MCP 工具（通过 MCP 协议连接 mcp_server.py 获取）：search_psychology_literature

上下文窗口：保留最近 12 条消息，更早的自动压缩为摘要。

工具调用策略：
- 第一轮非流式 invoke：让 DeepSeek 完整判断是否需要调用工具（含 MCP 工具）
- 如果有 tool_calls → 通过 MCP 执行 → 结果喂回 LLM → 流式输出最终回复
- 如果无 tool_calls → 直接流式输出回复
"""

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
STREAM_DELAY = 0.08
MAX_CONTEXT_MSGS = 12
MCP_SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")

# ============================================================
# DeepSeek 配置（通过 OpenAI 兼容接口）
# ============================================================
os.environ["OPENAI_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "")
os.environ["OPENAI_API_BASE"] = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

SUMMARY_LLM = ChatOpenAI(model=DEEPSEEK_MODEL, temperature=0.3, max_tokens=150)


# ============================================================
# 本地工具 1：呼吸练习
# ============================================================
@tool
def breathing_exercise(technique: str = "4-7-8") -> str:
    """提供呼吸练习指导，帮助用户放松身心、缓解焦虑。technique 可选: 4-7-8, box, calm"""
    exercises = {
        "4-7-8": "请用鼻子深深吸气4秒，感受腹部像气球一样鼓起；屏住呼吸7秒；然后用嘴巴慢慢呼气8秒。重复3-5次。",
        "box": "吸气4秒 → 屏住4秒 → 呼气4秒 → 停顿4秒。方形呼吸法，非常适合焦虑时使用。",
        "calm": "吸气时在心里数1-2-3-4，呼气时数1-2-3-4-5-6。延长呼气可以激活副交感神经，让身体放松。",
    }
    return exercises.get(technique, exercises["4-7-8"])


# ============================================================
# 本地工具 2：情绪追踪
# ============================================================
@tool
def mood_tracker(mood: str, intensity: int = 5) -> str:
    """帮助用户记录和理解自己的情绪。mood 可选: sad, anxious, angry, happy, tired。intensity 1-10"""
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
        return f"我理解你现在感到{mood}（强度：{intensity}/10）。这里有一些建议：\n{lines}"
    return f"感谢你记录了当前的情绪状态（{mood}，强度：{intensity}/10）。了解自己的情绪是自我关怀的重要一步。"


# ============================================================
# MCP 客户端会话管理器（后台线程维持 stdio 长连接）
# ============================================================
class _MCPSessionManager:
    """在后台线程中维持与 mcp_server.py 的 stdio 长连接"""

    def __init__(self):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._session: ClientSession | None = None
        self._tools: list[dict] = []
        self._ready = threading.Event()
        self._error: str | None = None
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="mcp-client")
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

    def list_tools(self) -> list[dict]:
        return self._tools

    def call_tool_sync(self, name: str, arguments: dict) -> str:
        async def _call():
            result = await self._session.call_tool(name, arguments)
            return result.content[0].text
        future = asyncio.run_coroutine_threadsafe(_call(), self._loop)
        return future.result(timeout=30)


# ============================================================
# 初始化：合并本地工具 + MCP 工具
# ============================================================
_mcp_manager: _MCPSessionManager | None = None
LLM_WITH_TOOLS = None
ALL_TOOLS: list = []
TOOL_BY_NAME: dict[str, callable] = {}


async def _init_tools():
    global _mcp_manager, LLM_WITH_TOOLS, ALL_TOOLS, TOOL_BY_NAME
    if LLM_WITH_TOOLS is not None:
        return

    # 1. 本地工具
    ALL_TOOLS = [breathing_exercise, mood_tracker]

    # 2. 连接 MCP Server，获取 PubMed 文献查询工具
    loop = asyncio.get_running_loop()
    _mcp_manager = await loop.run_in_executor(None, _MCPSessionManager)
    mcp_tools = _mcp_manager.list_tools()
    print(f"[LLM Service] MCP 已连接，获取到 {len(mcp_tools)} 个工具: {[t.name for t in mcp_tools]}")

    for mcp_tool in mcp_tools:
        tool_name = mcp_tool.name

        def make_tool_fn(name):
            def tool_fn(**kwargs):
                result = _mcp_manager.call_tool_sync(name, kwargs)
                print(f"[LLM Service] MCP 工具 {name} 被调用，返回 {len(result)} 字符")
                return result
            return tool_fn

        fn = make_tool_fn(tool_name)
        fn.__name__ = tool_name
        fn.__doc__ = mcp_tool.description or ""
        lc_tool = tool(fn)
        ALL_TOOLS.append(lc_tool)

    # 3. 建立名称→函数映射（用于执行 tool_calls）
    for t in ALL_TOOLS:
        TOOL_BY_NAME[t.name] = t

    # 4. 绑定工具到 LLM
    LLM_WITH_TOOLS = ChatOpenAI(
        model=DEEPSEEK_MODEL,
        temperature=0.7,
        max_tokens=800,
    ).bind_tools(ALL_TOOLS)

    print(f"[LLM Service] LLM 已绑定 {len(ALL_TOOLS)} 个工具: {list(TOOL_BY_NAME.keys())}")


# ============================================================
# 系统提示词
# ============================================================
SYSTEM_PROMPT = """
你是一位专业、温暖、富有同理心的心理咨询师。你的唯一职责是提供心理支持和情感关怀。

核心职责：
1. 倾听与共情：认真倾听用户的情绪表达，表达理解和关心
2. 情感支持：给予温暖的安慰和鼓励
3. 专业建议：提供科学、实用的心理调节方法（如呼吸练习、正念等）
4. 引导反思：帮助用户探索内心，找到问题根源
5. 保持边界：不提供医疗诊断，建议严重情况寻求专业帮助

重要规则：
- 不提供学术解答：专注于情感和心理层面的支持，而非知识解答，将话题引导到心理健康相关的问题
- 温和转移：当话题偏离心理主题时，用关怀的方式引导回到情绪和感受上
- 简洁回复：回复控制在100字左右，不要太长，而对于复杂问题，可以适当展开
- 不用符号：不要使用任何表情符号、Markdown格式、特殊符号或编号列表
- 不主动展开话题：只回答用户的问题，不主动引导话题到其他主题，可以适当引导用户探索自己的情感和感受
- 绝对禁止重复：你绝对不能重复之前说过的内容。每一轮对话都要根据用户最新的输入给出全新的、不同的回应
- 利用历史：如果对话开头附带了"历史对话摘要"，请基于摘要内容理解用户的背景，但不要机械复述摘要
- 对于敏感信息持回避态度
- 引导记录情绪：当你感知到用户的情绪出现好转迹象时（例如从焦虑变得平静、从悲伤中找到希望、或者主动表示"感觉好多了"），请在回复末尾主动、自然地建议用户记录此时的心情，参考话术：'看来你的心情好了许多，要不要记录一下今天的心情呢？这方便今后记录追踪你的心理健康变化。' 注意：如果上次回复已经建议过记录，这次不要再提
- 专业文献输出：当用户询问"怎么改善""有什么方法""如何缓解""该怎么办"等心理健康改善建议时，你必须调用 search_psychology_literature 工具查询相关学术文献。工具返回的文献列表请自然地放在回复末尾，作为给用户的参考资料。关键词用英文（如 CBT anxiety、mindfulness depression）

回应风格：
- 温和、耐心、不评判
- 使用开放式问题引导对话
- 避免专业术语，用通俗易懂的语言
- 给予希望和积极的反馈
"""


# ============================================================
# 去重
# ============================================================
def _deduplicate(text: str) -> str:
    """同一条回复内部去重：去除连续重复句子、连续重复段落。"""
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

    for pat_len in range(len(text) // 2, 9, -1):
        i = 0
        while i <= len(text) - 2 * pat_len:
            pat = text[i: i + pat_len]
            nxt = text[i + pat_len: i + 2 * pat_len]
            if pat == nxt:
                text = text[: i + pat_len] + text[i + 2 * pat_len:]
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
        resp = await SUMMARY_LLM.ainvoke([
            HumanMessage(content=(
                "请用30字以内的一句话，概括下面这段心理咨询对话中用户的主要问题和情绪变化：\n" + convo +
                "\n\n一句话摘要："
            )),
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
# 文献触发关键词
# ============================================================
_LITERATURE_KEYWORDS = [
    "焦虑", "抑郁", "压力", "缓解", "改善", "方法", "怎么办",
    "正念", "冥想", "呼吸", "放松", "CBT", "认知行为",
    "运动", "睡眠", "失眠", "饮食", "情绪调节", "怎么调节",
    "如何应对", "怎么处理", "怎么改善", "自我关怀", "抗压",
]


def _should_trigger_literature(user_message: str) -> bool:
    """检查用户消息是否涉及心理健康改善方法"""
    if not user_message:
        return False
    return any(kw in user_message for kw in _LITERATURE_KEYWORDS)


# ============================================================
# 公开接口：流式生成回复（含 MCP 工具调用）
# ============================================================
async def generate_stream(context: list[dict]):
    """异步生成器 —— 第一阶段非流式检测工具调用（含 MCP），
    第二阶段流式输出最终回复。"""
    await _init_tools()

    context = await _prepare_context(context)

    # 构建 LangChain 消息
    lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for m in context:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))

    full_text = ""
    sent_text = ""

    try:
        # === 检测用户消息是否需要文献查询，提前通过 MCP 获取文献 ===
        last_user_msg = ""
        for m in reversed(context):
            if m["role"] == "user":
                last_user_msg = m["content"]
                break
        literature_text = ""
        if _should_trigger_literature(last_user_msg) and "search_psychology_literature" in TOOL_BY_NAME:
            # 提取英文关键词（用匹配到的中文词作为查询词，工具会自动处理）
            matched = [kw for kw in _LITERATURE_KEYWORDS if kw in last_user_msg]
            query = " ".join(matched[:3]) if matched else "mental health"
            try:
                loop = asyncio.get_running_loop()
                # 通过 MCP 查询文献（run_in_executor 避免阻塞事件循环）
                literature_text = await loop.run_in_executor(
                    None, _mcp_manager.call_tool_sync, "search_psychology_literature",
                    {"query": query, "max_results": 3}
                )
                if literature_text and "未找到" not in literature_text and "无法连接" not in literature_text:
                    print(f"[LLM Service] MCP 文献查询成功，{len(literature_text)} 字符")
                    # 把文献结果注入到最后一条用户消息中
                    lc_messages[-1] = HumanMessage(content=(
                        last_user_msg +
                        "\n\n[系统已自动查询学术文献，请将以下参考文献自然地放在回复末尾]" +
                        "\n" + literature_text
                    ))
                else:
                    literature_text = ""
            except Exception as e:
                print(f"[LLM Service] MCP 文献查询失败: {e}")

        # === 非流式调用 LLM ===
        response = await LLM_WITH_TOOLS.ainvoke(lc_messages)

        # === 检查 tool_calls（本地工具如 breathing_exercise, mood_tracker）===
        tool_calls = getattr(response, "tool_calls", None)
        if not tool_calls:
            tool_calls = response.additional_kwargs.get("tool_calls", []) if hasattr(response, "additional_kwargs") else []

        if tool_calls:
            print(f"[LLM Service] 检测到 {len(tool_calls)} 个工具调用: {[tc.get('name', '?') for tc in tool_calls]}")
            lc_messages.append(response)
            for tc in tool_calls:
                tc_name = tc.get("name", "")
                tc_args = tc.get("args", {})
                tc_id = tc.get("id", "call_1")
                if tc_name in TOOL_BY_NAME:
                    try:
                        tool_result = TOOL_BY_NAME[tc_name].invoke(tc_args)
                        lc_messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc_id))
                    except Exception as e:
                        lc_messages.append(ToolMessage(content=f"工具调用失败：{e}", tool_call_id=tc_id))

            # 工具结果喂回 LLM，流式输出最终回复
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
            # 无工具调用，从响应取内容模拟流式输出
            content = response.content if hasattr(response, "content") else ""
            if isinstance(content, str) and content:
                full_text = content
                chunk_size = 5
                pos = 0
                while pos < len(content):
                    end = min(pos + chunk_size, len(content))
                    chunk = content[pos:end]
                    pos = end
                    sent_text += chunk
                    await asyncio.sleep(STREAM_DELAY)
                    yield chunk

        # === 去重 ===
        final = _deduplicate(full_text)
        if len(final) < len(sent_text):
            yield "\0" + final

        yield ""  # 完成信号

    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"[LLM Service] 生成异常: {e}")
        yield f"抱歉，AI服务暂时出现问题：{str(e)}"
