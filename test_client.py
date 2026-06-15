import sys
sys.path.insert(0, r"D:\Workspace\0-0\AnytxtMCP\mcp-everything-search\src")

from mcp_server_everything_search.anytxt_client import AnytxtClient

client = AnytxtClient()
count = client.search("test")
print(f"搜索 test: {count} 个结果")
