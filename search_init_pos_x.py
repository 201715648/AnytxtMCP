import sys
import os

# 动态计算路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "mcp-everything-search", "src")
if os.path.exists(src_dir):
    sys.path.insert(0, src_dir)

from mcp_server_everything_search.anytxt_client import AnytxtClient

client = AnytxtClient()

# 搜索init_pos_x
print("搜索 'init_pos_x':")
results = client.get_result("init_pos_x", limit=20)
print(f"找到 {len(results)} 个结果\n")

for i, file_info in enumerate(results, 1):
    print(f"{i}. {file_info['name']}")
    print(f"   路径: {file_info['path']}")
    print(f"   大小: {file_info['size']:,} 字节")
    
    # 获取片段
    try:
        fragment = client.get_fragment(file_info['fid'], 'init_pos_x')
        if fragment:
            print(f"   片段: ...{fragment[:200]}...")
    except Exception as e:
        print(f"   片段获取失败: {e}")
    print()
