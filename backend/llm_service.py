"""
LLM 服务 —— DeepSeek 驱动的心理咨询对话

基于 LangChain Agent，集成呼吸练习、情绪追踪两个工具。
上下文窗口：保留最近 5 条消息，更早的自动压缩为摘要。
"""

import os
import re
import asyncio
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()

# ============================================================
# 配置
# ============================================================
STREAM_DELAY = 0.08         # 流式输出间隔（秒）
MAX_CONTEXT_MSGS = 5         # 上下文窗口：最多保留最近 N 条消息原文，更早的压缩为摘要

# ============================================================
# DeepSeek 配置（通过 OpenAI 兼容接口）
# ============================================================
os.environ["OPENAI_API_KEY"] = os.getenv("DEEPSEEK_API_KEY", "")
os.environ["OPENAI_API_BASE"] = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 总结用的轻量模型（同 DeepSeek，温度更低，输出更稳定）
SUMMARY_LLM = ChatOpenAI(
    model=DEEPSEEK_MODEL,
    temperature=0.3,
    max_tokens=150,
)


# ============================================================
# 工具：呼吸练习
# ============================================================
@tool
def breathing_exercise(technique: str = "4-7-8") -> str:
    """
    提供呼吸练习指导，帮助用户放松身心。
    Args: technique: 呼吸技巧类型，可选：4-7-8, box, calm
    """
    exercises = {
        "4-7-8": "请用鼻子深深吸气4秒，感受腹部像气球一样鼓起；屏住呼吸7秒；然后用嘴巴慢慢呼气8秒。重复3-5次。",
        "box": "吸气4秒 → 屏住4秒 → 呼气4秒 → 停顿4秒。这是一个方形呼吸法，非常适合焦虑时使用。",
        "calm": "吸气时在心里数'1-2-3-4'，呼气时数'1-2-3-4-5-6'。延长呼气可以帮助激活副交感神经，让身体放松。",
    }
    return exercises.get(technique, exercises["4-7-8"])


# ============================================================
# 工具：情绪追踪
# ============================================================
@tool
def mood_tracker(mood: str, intensity: int = 5) -> str:
    """
    帮助用户记录和理解自己的情绪。
    Args:
        mood: 当前情绪（如：sad, anxious, angry, happy, tired）
        intensity: 情绪强度 1-10
    """
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
- 不回答数学问题：如果用户问数学题或其他知识性问题，请礼貌地转移话题到心理健康上
- 不提供学术解答：专注于情感和心理层面的支持，而非知识解答
- 温和转移：当话题偏离心理主题时，用关怀的方式引导回到情绪和感受上
- 简洁回复：每次回复控制在50-100字左右，不要太长，严格遵循字数限制
- 不用符号：不要使用任何表情符号、Markdown格式、特殊符号或编号列表
- 不主动展开话题：只回答用户的问题，不主动引导话题到其他主题，可以适当引导用户探索自己的情感和感受
- 绝对禁止重复：永远不要重复你之前说过的内容，每次回复都要根据用户最新的问题给出新的回应
- 利用历史：如果对话开头附带了"历史对话摘要"，请基于摘要内容理解用户的背景，但不要机械复述摘要
- 对于敏感信息持回避态度

回应风格：
- 温和、耐心、不评判
- 使用开放式问题引导对话
- 避免专业术语，用通俗易懂的语言
- 给予希望和积极的反馈
"""


# ============================================================
# 创建 LangChain Agent
# ============================================================
AGENT = create_agent(
    model=f"openai:{DEEPSEEK_MODEL}",
    tools=[breathing_exercise, mood_tracker],
    system_prompt=SYSTEM_PROMPT,
)


# ============================================================
# 去重
# ============================================================
def _deduplicate(text: str, previous_replies: list[str] | None = None) -> str:
    """移除重复的句子和段落，可选与历史回复交叉去重"""
    if not text:
        return text

    # 1. 句内去重
    sentences = text.split("。")
    result = []
    last = ""
    for s in sentences:
        s = s.strip()
        if s and s != last:
            result.append(s)
            last = s
    text = "。".join(result) + ("。" if text.endswith("。") else "")

    # 2. 段落内连续重复（10~全文一半长度）
    for pat_len in range(len(text) // 2, 9, -1):
        i = 0
        while i <= len(text) - 2 * pat_len:
            pat = text[i : i + pat_len]
            nxt = text[i + pat_len : i + 2 * pat_len]
            if pat == nxt:
                text = text[: i + pat_len] + text[i + 2 * pat_len :]
            else:
                i += 1

    # 3. 跨轮去重
    if previous_replies:
        for prev in previous_replies:
            if not prev:
                continue
            i = 0
            while i <= len(text) - 20:
                for pat_len in range(min(60, len(text) - i), 19, -1):
                    pat = text[i : i + pat_len]
                    if pat in prev:
                        text = text[:i] + text[i + pat_len :]
                        break
                else:
                    i += 1

    return text.strip()


# ============================================================
# 上下文窗口管理
# ============================================================
async def _summarize_old_messages(messages: list[dict]) -> str:
    """用 LLM 把较早的消息压缩成一句简短摘要（中文，30字以内）"""
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
        # 摘要失败不阻塞主流程，用简单拼接兜底
        topics = [m["content"][:30] for m in messages if m["role"] == "user"]
        return "、".join(topics[-3:])


async def _prepare_context(full_context: list[dict]) -> list[dict]:
    """
    管理上下文窗口：
    - 总消息数 ≤ MAX_CONTEXT_MSGS → 原样返回
    - 超过 → 保留最后 N 条原文，更早的压缩为一条摘要，注入到第一条用户消息前面
    """
    if len(full_context) <= MAX_CONTEXT_MSGS:
        return full_context

    recent = full_context[-MAX_CONTEXT_MSGS:]
    old = full_context[:-MAX_CONTEXT_MSGS]

    summary = await _summarize_old_messages(old)
    if not summary:
        return recent

    # 把摘要注入到保留窗口的第一条消息里
    recent[0] = dict(recent[0])
    recent[0]["content"] = f"[历史对话摘要：{summary}]\n\n{recent[0]['content']}"

    return recent


# ============================================================
# 公开接口：流式生成回复
# ============================================================
async def generate_stream(context: list[dict]):
    """
    异步生成器 —— 调用 DeepSeek LangChain Agent，逐 token 产出回复。

    参数:
        context: [{"role": "user"|"assistant", "content": "..."}, ...]
    产出:
        str: 增量文本内容
    """
    # 1. 上下文窗口处理（>5条自动摘要）
    context = await _prepare_context(context)

    # 2. 收集历史 AI 回复，用于跨轮去重
    previous_replies = [
        m["content"] for m in context if m["role"] == "assistant"
    ]

    # 3. 构建 LangChain 消息
    messages = []
    for m in context:
        if m["role"] in ("user", "assistant"):
            messages.append({"role": m["role"], "content": m["content"]})

    full_text = ""
    sent_text = ""

    try:
        async for event in AGENT.astream_events(
            {"messages": messages},
            version="v2",
        ):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    full_text += chunk.content
                    new_part = full_text[len(sent_text):]
                    if new_part:
                        sent_text = full_text
                        await asyncio.sleep(STREAM_DELAY)
                        yield new_part

        # 4. 最终去重：用 \0 前缀标记为"修正"事件，前端会替换而非追加
        final = _deduplicate(full_text, previous_replies)
        if len(final) < len(sent_text):
            yield "\0" + final

        yield ""  # 完成信号

    except asyncio.CancelledError:
        # 客户端断开，立即停止生成，不返回错误消息
        raise
    except Exception as e:
        yield f"抱歉，AI服务暂时出现问题：{str(e)}"
