"""Anytxt MCP Server 功能测试"""

import sys
import os

# 添加路径
sys.path.insert(0, r"D:\Workspace\0-0\AnytxtMCP\mcp-everything-search\src")

from mcp_server_everything_search.anytxt_client import AnytxtClient


def test_search():
    """测试搜索功能"""
    print("=" * 50)
    print("测试1: 搜索功能")
    print("=" * 50)
    
    client = AnytxtClient()
    
    # 测试搜索
    results = client.get_result("python", limit=5)
    print(f"搜索 'python' 找到 {len(results)} 个结果")
    
    for i, file_info in enumerate(results[:3], 1):
        name = file_info.get("name", "未知")
        path = file_info.get("path", "未知")
        print(f"  {i}. {name}")
        print(f"     路径: {path}")
    
    return results


def test_get_fragment(results):
    """测试获取片段功能"""
    print("\n" + "=" * 50)
    print("测试2: 获取片段功能")
    print("=" * 50)
    
    client = AnytxtClient()
    
    if not results:
        print("无测试数据")
        return
    
    fid = results[0].get("fid")
    if not fid:
        print("无文件ID")
        return
    
    # 测试获取片段
    fragment = client.get_fragment(fid, "python")
    print(f"文件 {results[0].get('name')} 的片段:")
    print(f"  {fragment[:100]}..." if len(fragment) > 100 else f"  {fragment}")
    
    # 测试获取所有片段
    fragments = client.get_fragment_all(fid, "python")
    print(f"\n找到 {len(fragments)} 个片段")


def test_get_raw_text(results):
    """测试获取完整文本功能"""
    print("\n" + "=" * 50)
    print("测试3: 获取完整文本功能")
    print("=" * 50)
    
    client = AnytxtClient()
    
    if not results:
        print("无测试数据")
        return
    
    fid = results[0].get("fid")
    if not fid:
        print("无文件ID")
        return
    
    # 测试获取完整文本
    text = client.get_raw_text_by_fid(fid)
    print(f"文件 {results[0].get('name')} 的内容:")
    print(f"  长度: {len(text)} 字符")
    print(f"  预览: {text[:200]}..." if len(text) > 200 else f"  内容: {text}")


def test_ocr():
    """测试OCR功能"""
    print("\n" + "=" * 50)
    print("测试4: OCR功能（需要OCR版）")
    print("=" * 50)
    
    client = AnytxtClient()
    
    # 这里需要一个测试图片路径
    # test_image = r"C:\path\to\test.png"
    # text = client.ocr(test_image)
    # print(f"OCR结果: {text[:100]}")
    
    print("  跳过（需要测试图片）")


def test_sync_index():
    """测试同步索引功能"""
    print("\n" + "=" * 50)
    print("测试5: 同步索引功能")
    print("=" * 50)
    
    client = AnytxtClient()
    
    # 测试同步（使用临时目录）
    # success = client.sync_index(r"C:\Temp\test")
    # print(f"同步结果: {'成功' if success else '失败'}")
    
    print("  跳过（避免意外同步）")


def main():
    """运行所有测试"""
    print("Anytxt MCP Server 功能测试")
    print("=" * 50)
    
    try:
        # 测试搜索
        results = test_search()
        
        # 测试获取片段
        test_get_fragment(results)
        
        # 测试获取完整文本
        test_get_raw_text(results)
        
        # 测试OCR
        test_ocr()
        
        # 测试同步索引
        test_sync_index()
        
        print("\n" + "=" * 50)
        print("所有测试完成!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
