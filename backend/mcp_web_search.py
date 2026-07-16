"""
MCP Web Search Server —— 互联网搜索工具

通过 DuckDuckGo HTML 搜索实现无需 API Key 的网页搜索。
支持中文搜索，返回标题、摘要和链接。

启动方式:
    python mcp_web_search.py
"""

import sys
import os
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
        description="搜索互联网信息。当用户询问需要实时信息的心理健康问题时使用此工具查找相关资料。支持中文和英文搜索。返回网页标题、摘要和链接。",
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

_DDG_URL = "https://html.duckduckgo.com/html/"


def _parse_ddg_html(html: str) -> list[dict]:
    """解析 DuckDuckGo HTML 搜索结果"""
    results = []
    # 匹配每个搜索结果块
    blocks = re.split(r'<div class="result results_links', html)
    for block in blocks[1:]:  # 跳过第一个分割前的内容
        title_match = re.search(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', block, re.DOTALL)
        snippet_match = re.search(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
        url_match = re.search(r'<a[^>]*class="result__url"[^>]*>(.*?)</a>', block, re.DOTALL)

        title = unescape(re.sub(r'<[^>]*>', '', title_match.group(1))).strip() if title_match else ""
        snippet = unescape(re.sub(r'<[^>]*>', '', snippet_match.group(1))).strip() if snippet_match else ""
        url_raw = unescape(re.sub(r'<[^>]*>', '', url_match.group(1))).strip() if url_match else ""

        if title and snippet:
            results.append({"title": title, "snippet": snippet, "url": url_raw})
    return results


def web_search(query: str, max_results: int = 5) -> str:
    """执行 DuckDuckGo 网页搜索"""
    max_results = max(1, min(max_results, 8))

    try:
        params = urllib.parse.urlencode({"q": query}).encode("utf-8")
        req = urllib.request.Request(
            _DDG_URL,
            data=params,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        results = _parse_ddg_html(html)[:max_results]

        if not results:
            return f"未找到关于「{query}」的搜索结果。请尝试其他关键词。"

        lines = [f"关于「{query}」的搜索结果：\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. **{r['title']}**")
            lines.append(f"   {r['snippet']}")
            if r['url']:
                lines.append(f"   {r['url']}")
            lines.append("")

        return "\n".join(lines)

    except urllib.error.URLError:
        return f"搜索「{query}」时网络连接失败，请检查网络后重试。"
    except Exception as e:
        return f"搜索时发生错误：{str(e)}"


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
