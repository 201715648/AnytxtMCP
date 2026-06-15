"""Anytxt MCP Server - SSE/HTTP 传输模式（适用于仅支持远程 MCP 的客户端如 MiMo Code）

启动方式:
    uv run python -c "from mcp_server_everything_search.anytxt_sse_server import main; main()"

客户端配置 (mcpServers):
    {
      "mcp-anytxt-search": {
        "type": "sse",
        "url": "http://127.0.0.1:9921/sse"
      }
    }
"""

import asyncio
import logging
import os
import platform
import sys
from typing import List, Union

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import ImageContent, TextContent, Tool

from .anytxt_client import (
    AnytxtClient,
    get_client,
    is_image_file,
    read_image_base64,
    get_max_images_in_search,
    get_max_image_kb,
)

# 环境变量默认值
ENV_MAX_RESULTS = int(os.environ.get("ANYTXT_MAX_RESULTS", "100"))
ENV_DEFAULT_DIR = os.environ.get("ANYTXT_DEFAULT_DIR", "")
ENV_DEFAULT_EXT = os.environ.get("ANYTXT_DEFAULT_EXT", "*")
ENV_TIMEOUT_MS = int(os.environ.get("ANYTXT_TIMEOUT_MS", "10000"))
ENV_MAX_FRAGMENTS = int(os.environ.get("ANYTXT_MAX_FRAGMENTS", "20"))
ENV_MAX_RAW_CHARS = int(os.environ.get("ANYTXT_MAX_RAW_CHARS", "20000"))
ENV_ENABLE_SYNC = os.environ.get("ANYTXT_ENABLE_SYNC", "false").lower() in ("true", "1")
ENV_ENABLE_OCR = os.environ.get("ANYTXT_ENABLE_OCR", "false").lower() in ("true", "1")
ENV_SSE_HOST = os.environ.get("ANYTXT_SSE_HOST", "127.0.0.1")
ENV_SSE_PORT = int(os.environ.get("ANYTXT_SSE_PORT", "9921"))


def _build_tools() -> List[Tool]:
    """构建工具列表"""
    tools = [
        Tool(
            name="anytxt_search",
            description="""搜索本地文档内容，返回文件路径和匹配片段。

搜索范围：不指定目录时，自动搜索所有可用驱动器（C:、D:等）。
如需限定范围，请明确指定 directory 参数。

支持的搜索语法：
- 普通关键词：Hello
- 精确短语："This is"
- 布尔运算：Hello AND World, Hello OR World, NOT Hello
- 通配符：*.txt, Hello*

示例：
- "认证函数" - 搜索包含"认证函数"的文档
- "error AND log" - 搜索同时包含error和log的文档
- "*.md" - 搜索所有Markdown文件""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词，支持布尔语法和通配符"},
                    "directory": {"type": "string", "description": "限定搜索目录（留空则自动搜索所有驱动器 C:、D: 等）", "default": ""},
                    "extension": {"type": "string", "description": "文件扩展名过滤（如 txt, pdf, *）", "default": "*"},
                    "limit": {"type": "integer", "description": f"返回结果数量限制（默认20，最大{ENV_MAX_RESULTS}）", "default": 20, "minimum": 1, "maximum": ENV_MAX_RESULTS},
                    "offset": {"type": "integer", "description": "分页偏移量", "default": 0, "minimum": 0},
                    "order": {"type": "integer", "description": "排序方式: 0=默认, 1=修改时间升序, 2=修改时间降序, 3=路径升序, 4=路径降序", "default": 0, "minimum": 0, "maximum": 4},
                    "modified_after": {"type": "integer", "description": "修改时间起始（Unix时间戳），0 表示不限", "default": 0, "minimum": 0},
                    "modified_before": {"type": "integer", "description": "修改时间结束（Unix时间戳），2147483647 表示不限", "default": 2147483647, "minimum": 0},
                    "include_fragment": {"type": "boolean", "description": "是否返回内容片段", "default": True},
                },
                "required": ["query"],
            }
        ),
        Tool(
            name="anytxt_get_context",
            description="""获取文件中与关键词相关的上下文片段。

用于深入查看某个文件中与搜索词相关的所有内容。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "fid": {"type": "string", "description": "文件ID，来自anytxt_search结果"},
                    "query": {"type": "string", "description": "搜索关键词"},
                    "max_fragments": {"type": "integer", "description": "最大返回片段数（默认5）", "default": 5, "minimum": 1, "maximum": 20},
                },
                "required": ["fid", "query"],
            }
        ),
        Tool(
            name="anytxt_read_file",
            description="""读取文件完整内容。

用于深度分析某个文件的完整内容。注意：大文件会被截断。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "fid": {"type": "string", "description": "文件ID，来自anytxt_search结果"},
                    "max_chars": {"type": "integer", "description": "最大返回字符数（默认10000）", "default": 10000, "minimum": 1000, "maximum": 50000},
                },
                "required": ["fid"],
            }
        ),
        Tool(
            name="anytxt_view_image",
            description="""查看图片文件原图，将图片内容直接传递给 AI 视觉分析。

用于 anytxt_search 搜索到图片文件时，OCR 文本可能不完整或有误，通过此工具查看原图让 AI 直接识别。
每次调用只返回一张图片，避免上下文过载。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "fid": {"type": "string", "description": "图片文件ID（来自 anytxt_search 结果，优先使用）"},
                    "file_path": {"type": "string", "description": "图片文件路径（当没有 fid 时使用）"},
                    "max_size_kb": {"type": "integer", "description": "图片大小上限(KB)，默认5120（5MB）", "default": 5120, "minimum": 100, "maximum": 10240},
                },
                "required": [],
            }
        ),
        Tool(
            name="anytxt_count",
            description="""统计匹配文档数量（不返回文件列表）。

用于快速了解有多少文件包含指定内容。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词，支持布尔语法和通配符"},
                    "directory": {"type": "string", "description": "限定搜索目录（留空则搜索所有驱动器）", "default": ""},
                    "extension": {"type": "string", "description": "文件扩展名过滤", "default": "*"},
                    "modified_after": {"type": "integer", "description": "修改时间起始", "default": 0, "minimum": 0},
                    "modified_before": {"type": "integer", "description": "修改时间结束", "default": 2147483647, "minimum": 0},
                },
                "required": ["query"],
            }
        ),
        Tool(
            name="anytxt_status",
            description="检查 Anytxt 服务状态和索引统计信息。无需参数。",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="anytxt_search_files",
            description="""按文件名搜索文件（Everything 引擎，仅 Windows）。使用前需用户确认。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询，支持 Everything 搜索语法"},
                    "max_results": {"type": "integer", "description": "最大返回结果数", "default": 100, "minimum": 1, "maximum": 1000},
                    "match_path": {"type": "boolean", "description": "匹配完整路径", "default": False},
                    "match_case": {"type": "boolean", "description": "区分大小写", "default": False},
                    "match_whole_word": {"type": "boolean", "description": "全词匹配", "default": False},
                    "match_regex": {"type": "boolean", "description": "正则表达式", "default": False},
                    "sort_by": {"type": "integer", "description": "排序方式", "default": 1, "minimum": 1, "maximum": 26},
                    "user_confirmed": {"type": "boolean", "description": "用户已确认", "default": False},
                },
                "required": ["query", "user_confirmed"],
            }
        ),
    ]
    if ENV_ENABLE_SYNC:
        tools.append(Tool(
            name="anytxt_sync_index",
            description="同步指定文件夹到Anytxt索引。",
            inputSchema={
                "type": "object",
                "properties": {"folder": {"type": "string", "description": "要同步的文件夹路径"}},
                "required": ["folder"],
            }
        ))
    if ENV_ENABLE_OCR:
        tools.append(Tool(
            name="anytxt_ocr",
            description="识别图片中的文字内容（需要Anytxt OCR版）。",
            inputSchema={
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "图片文件路径"}},
                "required": ["file_path"],
            }
        ))
    return tools


async def _dispatch(client: AnytxtClient, name: str, arguments: dict) -> List[Union[TextContent, ImageContent]]:
    """分发工具调用 - 导入 _handle_* 函数"""
    from .anytxt_server import (
        _handle_search,
        _handle_get_context,
        _handle_read_file,
        _handle_sync_index,
        _handle_ocr,
        _handle_count,
        _handle_status,
        _handle_view_image,
        _handle_search_files,
    )
    handlers = {
        "anytxt_search": _handle_search,
        "anytxt_get_context": _handle_get_context,
        "anytxt_read_file": _handle_read_file,
        "anytxt_sync_index": _handle_sync_index,
        "anytxt_ocr": _handle_ocr,
        "anytxt_count": _handle_count,
        "anytxt_status": _handle_status,
        "anytxt_view_image": _handle_view_image,
        "anytxt_search_files": _handle_search_files,
    }
    handler = handlers.get(name)
    if handler:
        if name == "anytxt_search_files":
            return await handler(arguments)
        return await handler(client, arguments)
    return [TextContent(type="text", text=f"未知工具: {name}")]


async def serve_sse() -> None:
    """运行 Anytxt MCP SSE 服务器"""
    client = get_client()
    server = Server("anytxt-search")

    @server.list_tools()
    async def list_tools():
        return _build_tools()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            return await _dispatch(client, name, arguments)
        except Exception as e:
            return [TextContent(type="text", text=f"错误: {str(e)}")]

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream,
                server.create_initialization_options(),
            )

    starlette_app = Starlette(
        debug=False,
        routes=[
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    logger = logging.getLogger("anytxt-sse")
    logger.info(f"SSE 服务器启动: http://{ENV_SSE_HOST}:{ENV_SSE_PORT}/sse")

    config = uvicorn.Config(
        starlette_app, host=ENV_SSE_HOST, port=ENV_SSE_PORT, log_level="warning"
    )
    await uvicorn.Server(config).serve()


def main() -> None:
    """SSE 模式主入口"""
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    if sys.platform == "win32":
        from .anytxt_server import configure_windows_console
        configure_windows_console()
    try:
        asyncio.run(serve_sse())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        logging.error(f"SSE 服务器错误: {e}", exc_info=True)
        sys.exit(1)
