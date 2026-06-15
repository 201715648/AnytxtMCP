"""MCP服务器入口点 - 支持Everything和Anytxt两种模式"""

import os
import sys


def main():
    """根据环境变量选择启动模式"""
    # 检查是否启用Anytxt模式
    anytxt_enabled = os.environ.get("ANYTXT_ENABLED", "true").lower() == "true"
    
    if anytxt_enabled:
        # Anytxt模式
        from .anytxt_server import main as anytxt_main
        anytxt_main()
    else:
        # Everything模式（默认）
        from .server import main as everything_main
        everything_main()


if __name__ == "__main__":
    main()
