import sys
import os

# 动态计算路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "mcp-everything-search", "src")
if os.path.exists(src_dir):
    sys.path.insert(0, src_dir)

from mcp_server_everything_search.anytxt_client import AnytxtClient

client = AnytxtClient()
count = client.search("test")
print(f"搜索 test: {count} 个结果")
