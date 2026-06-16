import sys
import os

# 设置环境变量
os.environ["ANYTXT_ENABLED"] = "true"

# 动态计算路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "mcp-everything-search", "src")
if os.path.exists(src_dir):
    sys.path.insert(0, src_dir)

# 导入并测试
from mcp_server_everything_search.anytxt_client import AnytxtClient

client = AnytxtClient()
print("Anytxt客户端测试:")
print(f"  搜索 'python': {client.search('python')} 个结果")
print(f"  搜索 'error': {client.search('error')} 个结果")
print("\nAnytxt MCP服务器模块加载成功!")
