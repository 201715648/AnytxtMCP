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
import sys

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent

from .anytxt_client import get_client
from .anytxt_server import get_tools, dispatch_tool

# 环境变量默认值
ENV_SSE_HOST = os.environ.get("ANYTXT_SSE_HOST", "127.0.0.1")
ENV_SSE_PORT = int(os.environ.get("ANYTXT_SSE_PORT", "9921"))


async def serve_sse() -> None:
    """运行 Anytxt MCP SSE 服务器"""
    client = get_client()
    server = Server("anytxt-search")

    @server.list_tools()
    async def list_tools():
        return get_tools()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            return await dispatch_tool(client, name, arguments)
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
