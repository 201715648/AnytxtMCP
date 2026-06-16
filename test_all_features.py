"""Anytxt MCP Server 功能测试"""

import sys
import os

# 动态计算路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "mcp-everything-search", "src")
if os.path.exists(src_dir):
    sys.path.insert(0, src_dir)

from mcp_server_everything_search.anytxt_client import AnytxtClient


def test_search(client):
    """测试搜索功能"""
    print("=" * 50)
    print("测试1: 搜索功能")
    print("=" * 50)
    
    # 测试搜索
    results = client.get_result("python", limit=5)
    print(f"搜索 'python' 找到 {len(results)} 个结果")
    
    for i, file_info in enumerate(results[:3], 1):
        name = file_info.get("name", "未知")
        path = file_info.get("path", "未知")
        print(f"  {i}. {name}")
        print(f"     路径: {path}")
    
    return results


def test_get_fragment(client, results):
    """测试获取片段功能"""
    print("\n" + "=" * 50)
    print("测试2: 获取片段功能")
    print("=" * 50)
    
    if not results:
        print("无测试数据")
        return
    
    fid = results[0].get("fid")
    if not fid:
        print("无文件ID")
        return
    
    # 测试获取单片段 (GetFragment 应当普遍支持)
    if "GetFragment" in client.supported_methods:
        fragment = client.get_fragment(fid, "python")
        print(f"文件 {results[0].get('name')} 的单片段:")
        print(f"  {fragment[:100]}..." if len(fragment) > 100 else f"  {fragment}")
    else:
        print("  跳过获取单片段（当前 Anytxt 版本不支持 GetFragment API）")
    
    # 测试获取所有片段
    if "GetFragmentAll" in client.supported_methods:
        try:
            fragments = client.get_fragment_all(fid, "python")
            print(f"\n找到 {len(fragments)} 个片段")
        except Exception as e:
            print(f"  调用 GetFragmentAll 失败: {e}")
    else:
        print("\n  跳过获取多片段（当前 Anytxt 版本不支持 GetFragmentAll API）")


def test_get_raw_text(client, results):
    """测试获取完整文本功能"""
    print("\n" + "=" * 50)
    print("测试3: 获取完整文本功能")
    print("=" * 50)
    
    if not results:
        print("无测试数据")
        return
    
    fid = results[0].get("fid")
    if not fid:
        print("无文件ID")
        return
    
    # 测试获取完整文本
    if "GetRawTextByFID" in client.supported_methods:
        try:
            text = client.get_raw_text_by_fid(fid)
            print(f"文件 {results[0].get('name')} 的内容:")
            print(f"  长度: {len(text)} 字符")
            print(f"  预览: {text[:200]}..." if len(text) > 200 else f"  内容: {text}")
        except Exception as e:
            print(f"  调用 GetRawTextByFID 失败: {e}")
    else:
        print("  跳过（当前 Anytxt 版本不支持 GetRawTextByFID 获取全文 API）")


def test_ocr(client):
    """测试OCR功能"""
    print("\n" + "=" * 50)
    print("测试4: OCR功能（需要OCR版）")
    print("=" * 50)
    
    if "OCR" in client.supported_methods:
        # 这里需要一个测试图片路径
        # test_image = r"C:\path\to\test.png"
        # text = client.ocr(test_image)
        # print(f"OCR结果: {text[:100]}")
        print("  支持 OCR 接口，但跳过实际图片识别（需要测试图片路径）")
    else:
        print("  跳过（当前 Anytxt 版本不支持 OCR API）")


def test_sync_index(client):
    """测试同步索引功能"""
    print("\n" + "=" * 50)
    print("测试5: 同步索引功能")
    print("=" * 50)
    
    if "SyncIndex" in client.supported_methods:
        # 测试同步（使用临时目录）
        # success = client.sync_index(r"C:\Temp\test")
        # print(f"同步结果: {'成功' if success else '失败'}")
        print("  支持 SyncIndex 接口，但跳过实际同步（避免意外同步）")
    else:
        print("  跳过（当前 Anytxt 版本不支持 SyncIndex API）")


def main():
    """运行所有测试"""
    print("Anytxt MCP Server 功能测试与 API 兼容性检测")
    print("=" * 50)
    
    try:
        client = AnytxtClient()
        
        # 强制执行一次能力探测以获得版本和 API 列表
        print("正在检测 Anytxt 服务版本与 API 能力...")
        client.detect_capabilities()
        print(f"Anytxt 软件版本: {client.version}")
        print(f"所支持的 API 接口: {sorted(list(client.supported_methods))}")
        print()
        
        # 测试搜索
        results = test_search(client)
        
        # 测试获取片段
        test_get_fragment(client, results)
        
        # 测试获取完整文本
        test_get_raw_text(client, results)
        
        # 测试OCR
        test_ocr(client)
        
        # 测试同步索引
        test_sync_index(client)
        
        print("\n" + "=" * 50)
        print("所有测试完成!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
