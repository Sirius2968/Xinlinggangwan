"""
MCP Web Search Server —— 互联网搜索工具

多引擎回退：百度 → 搜狗 → 360搜索
全部使用国内搜索引擎，针对中文心理健康内容优化。

启动方式:
    python mcp_web_search.py
"""

import sys
import os
import gzip
import urllib.request
import urllib.parse
import urllib.error
import re
from html import unescape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("web-search-tools")

TOOLS = [
    types.Tool(
        name="web_search",
        description="搜索互联网信息。优先使用百度搜索中文内容。当用户询问需要实时信息的心理健康问题时使用此工具查找相关资料。支持中文和英文搜索。返回网页标题、摘要和链接。",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，中英文均可（如：焦虑症自我调节方法、CBT therapy techniques）",
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回结果数量 1-8",
                    "minimum": 1,
                    "maximum": 8,
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    ),
]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
}

# ============================================================
# 引擎 1：百度
# ============================================================

def _search_baidu(query: str, max_results: int) -> str | None:
    """百度网页搜索，失败返回 None"""
    try:
        params = urllib.parse.urlencode({"wd": query, "rn": max_results})
        req = urllib.request.Request(
            f"https://www.baidu.com/s?{params}",
            headers=_HEADERS,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            html = raw.decode("utf-8", errors="replace")

        results = _parse_baidu(html, max_results)
        if not results:
            return None

        lines = [f"百度搜索「{query}」的结果：\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. **{r['title']}**")
            lines.append(f"   {r['snippet']}")
            if r.get("url"):
                lines.append(f"   {r['url']}")
            lines.append("")
        return "\n".join(lines)

    except Exception as e:
        print(f"[MCP] 百度搜索失败: {e}")
        return None


def _parse_baidu(html: str, max_results: int) -> list[dict]:
    """解析百度 PC 版搜索结果"""
    results = []
    # 匹配每个结果块：<div class="result c-container" ...> 到对应的闭合 </div>
    # 百度 HTML 嵌套很深，用宽松匹配
    blocks = re.findall(
        r'<div[^>]*class="[^"]*result c-container[^"]*".*?</div>\s*</div>\s*</div>\s*</div>',
        html, re.DOTALL,
    )
    if not blocks:
        # 回退：按 class="result" 切分
        parts = html.split('class="result')
        blocks = ['class="result' + p for p in parts[1:]]

    for block in blocks[:max_results * 2]:
        # 标题：<h3> 内 <a> 的文本
        title_match = re.search(r'<h3[^>]*>.*?<a[^>]*>(.*?)</a>', block, re.DOTALL)
        # 摘要
        snippet_match = re.search(
            r'<span[^>]*class="[^"]*content-right_[^"]*"[^>]*>(.*?)</span>',
            block, re.DOTALL,
        )
        if not snippet_match:
            snippet_match = re.search(
                r'<span[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</span>',
                block, re.DOTALL,
            )
        if not snippet_match:
            snippet_match = re.search(
                r'<div[^>]*class="[^"]*c-abstract[^"]*"[^>]*>(.*?)</div>',
                block, re.DOTALL,
            )
        # 链接
        url_match = re.search(r'<a[^>]*href="(https?://[^"]+)"[^>]*>', block)

        title = unescape(re.sub(r'<[^>]*>', '', title_match.group(1))).strip() if title_match else ""
        snippet = unescape(re.sub(r'<[^>]*>', '', snippet_match.group(1))).strip() if snippet_match else ""

        if title and len(results) < max_results:
            results.append({"title": title, "snippet": snippet, "url": url_match.group(1) if url_match else ""})

    return results


# ============================================================
# 引擎 2：搜狗
# ============================================================

def _search_sogou(query: str, max_results: int) -> str | None:
    """搜狗网页搜索，失败返回 None"""
    try:
        params = urllib.parse.urlencode({"query": query})
        req = urllib.request.Request(
            f"https://www.sogou.com/web?{params}",
            headers=_HEADERS,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            html = raw.decode("utf-8", errors="replace")

        results = _parse_sogou(html, max_results)
        if not results:
            return None

        lines = [f"搜狗搜索「{query}」的结果：\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. **{r['title']}**")
            lines.append(f"   {r['snippet']}")
            if r.get("url"):
                lines.append(f"   {r['url']}")
            lines.append("")
        return "\n".join(lines)

    except Exception as e:
        print(f"[MCP] 搜狗搜索失败: {e}")
        return None


def _parse_sogou(html: str, max_results: int) -> list[dict]:
    """解析搜狗搜索结果"""
    results = []
    # 搜狗结果块：<div class="vrwrap"> ... </div>
    blocks = re.findall(r'<div[^>]*class="[^"]*vrwrap[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
    if not blocks:
        # 回退：<div class="rb">
        blocks = re.findall(r'<div[^>]*class="[^"]*rb[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)

    for block in blocks[:max_results]:
        title_match = re.search(r'<h3[^>]*>.*?<a[^>]*>(.*?)</a>', block, re.DOTALL)
        snippet_match = re.search(r'<p[^>]*class="[^"]*star-last-str[^"]*"[^>]*>(.*?)</p>', block, re.DOTALL)
        if not snippet_match:
            snippet_match = re.search(r'<div[^>]*class="[^"]*space-txt[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL)
        if not snippet_match:
            snippet_match = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL)
        url_match = re.search(r'<a[^>]*href="(https?://[^"]+)"[^>]*>', block)

        title = unescape(re.sub(r'<[^>]*>', '', title_match.group(1))).strip() if title_match else ""
        snippet = unescape(re.sub(r'<[^>]*>', '', snippet_match.group(1))).strip() if snippet_match else ""

        if title and len(results) < max_results:
            results.append({"title": title, "snippet": snippet, "url": url_match.group(1) if url_match else ""})

    return results


# ============================================================
# 引擎 3：360搜索
# ============================================================

def _search_360(query: str, max_results: int) -> str | None:
    """360搜索，失败返回 None"""
    try:
        params = urllib.parse.urlencode({"q": query})
        req = urllib.request.Request(
            f"https://www.so.com/s?{params}",
            headers=_HEADERS,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            html = raw.decode("utf-8", errors="replace")

        results = _parse_360(html, max_results)
        if not results:
            return None

        lines = [f"360搜索「{query}」的结果：\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. **{r['title']}**")
            lines.append(f"   {r['snippet']}")
            if r.get("url"):
                lines.append(f"   {r['url']}")
            lines.append("")
        return "\n".join(lines)

    except Exception as e:
        print(f"[MCP] 360搜索失败: {e}")
        return None


def _parse_360(html: str, max_results: int) -> list[dict]:
    """解析360搜索结果"""
    results = []
    # 360结果块：<li class="res-list"> ... </li>
    blocks = re.findall(r'<li[^>]*class="[^"]*res-list[^"]*"[^>]*>(.*?)</li>', html, re.DOTALL)

    for block in blocks[:max_results]:
        title_match = re.search(r'<h3[^>]*>.*?<a[^>]*>(.*?)</a>', block, re.DOTALL)
        snippet_match = re.search(r'<p[^>]*class="[^"]*res-desc[^"]*"[^>]*>(.*?)</p>', block, re.DOTALL)
        if not snippet_match:
            snippet_match = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL)
        url_match = re.search(r'<a[^>]*href="(https?://[^"]+)"[^>]*>', block)

        title = unescape(re.sub(r'<[^>]*>', '', title_match.group(1))).strip() if title_match else ""
        snippet = unescape(re.sub(r'<[^>]*>', '', snippet_match.group(1))).strip() if snippet_match else ""

        if title and len(results) < max_results:
            results.append({"title": title, "snippet": snippet, "url": url_match.group(1) if url_match else ""})

    return results


# ============================================================
# 统一入口：百度 → 搜狗 → 360搜索 回退
# ============================================================

def web_search(query: str, max_results: int = 5) -> str:
    """多引擎搜索：百度 → 必应 → DuckDuckGo 逐级回退"""
    max_results = max(1, min(max_results, 8))

    engines = [
        ("百度", _search_baidu),
        ("搜狗", _search_sogou),
        ("360搜索", _search_360),
    ]

    for name, engine_fn in engines:
        result = engine_fn(query, max_results)
        if result:
            return result
        print(f"[MCP] {name}无结果，尝试下一个引擎…")

    return f"未找到关于「{query}」的搜索结果。请尝试其他关键词。"


TOOL_REGISTRY = {"web_search": web_search}


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return TOOLS


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    func = TOOL_REGISTRY.get(name)
    if not func:
        raise ValueError(f"未知工具: {name}")
    result = func(**arguments)
    return [types.TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
