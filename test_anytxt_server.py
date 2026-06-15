import sys
import os

# 设置环境变量
os.environ["ANYTXT_ENABLED"] = "true"

# 添加路径
sys.path.insert(0, r"D:\Workspace\0-0\AnytxtMCP\mcp-everything-search\src")

# 导入并测试
from mcp_server_everything_search.anytxt_client import AnytxtClient

client = AnytxtClient()
print("Anytxt客户端测试:")
print(f"  搜索 'python': {client.search('python')} 个结果")
print(f"  搜索 'error': {client.search('error')} 个结果")
print("\nAnytxt MCP服务器模块加载成功!")
