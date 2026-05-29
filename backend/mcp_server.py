"""
MCP Server —— 专业学术文献查询工具（Model Context Protocol）

通过 MCP 协议对外暴露 PubMed 学术文献查询能力。
连接美国国立医学图书馆 E-utilities API，支持搜索心理学相关研究文献。

启动方式:
    python mcp_server.py

Claude Desktop 配置 (claude_desktop_config.json):
    {
      "mcpServers": {
        "psychology-tools": {
          "command": "python",
          "args": ["backend/mcp_server.py"],
          "cwd": "/path/to/vue-project"
        }
      }
    }
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from tools import TOOL_REGISTRY

server = Server("psychology-tools")

TOOLS = [
    types.Tool(
        name="search_psychology_literature",
        description="查询 PubMed 学术数据库中与心理健康相关的专业文献。连接美国国立医学图书馆 E-utilities API，可搜索认知行为疗法、焦虑、抑郁、正念冥想等心理学议题的最新研究。返回文献标题、作者、期刊年份和 PubMed 链接。适合需要了解循证心理学研究或寻找学术参考文献的场景。",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，英文效果更佳（如：cognitive behavioral therapy anxiety、mindfulness meditation depression、PTSD treatment）",
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回文献数量 1-10",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    ),
]


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
