"""MCP服务器入口点 - 支持Everything和Anytxt两种模式，stdio和SSE两种传输"""

import os
import sys


def main():
    """根据环境变量选择启动模式"""
    transport = os.environ.get("ANYTXT_TRANSPORT", "stdio").lower()
    anytxt_enabled = os.environ.get("ANYTXT_ENABLED", "true").lower() == "true"

    if anytxt_enabled:
        if transport == "sse":
            from .anytxt_sse_server import main as anytxt_main
        else:
            from .anytxt_server import main as anytxt_main
        anytxt_main()
    else:
        from .server import main as everything_main
        everything_main()


if __name__ == "__main__":
    main()
