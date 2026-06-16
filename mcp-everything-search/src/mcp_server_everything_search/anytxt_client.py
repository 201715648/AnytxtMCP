"""Anytxt HTTP JSON-RPC 2.0 客户端封装"""

import base64
import json
import os
import string
from typing import Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# 图片文件扩展名集合
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp", ".ico"}

# 图片大小限制
DEFAULT_MAX_IMAGE_KB = 5120  # 单张图片最大 5MB
DEFAULT_MAX_IMAGES_IN_SEARCH = 3  # 搜索结果中最多标注几张图片


_cached_drives: Optional[list[str]] = None


def get_available_drives() -> list[str]:
    """获取系统中所有可用驱动器根路径（使用缓存避免重复检测阻塞）"""
    global _cached_drives
    if _cached_drives is not None:
        return _cached_drives
        
    drives = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            drives.append(root)
    _cached_drives = drives
    return drives


class AnytxtClient:
    """Anytxt JSON-RPC 客户端"""
    
    def __init__(
        self,
        rpc_url: Optional[str] = None,
        timeout_ms: int = 10000,
    ):
        self.rpc_url = rpc_url or os.environ.get(
            "ANYTXT_RPC_URL", "http://127.0.0.1:9920"
        )
        self.timeout = timeout_ms / 1000
        self._request_id = 0
        self._fid_to_path: dict[str, str] = {}
        
    def get_path_by_fid(self, fid: str) -> Optional[str]:
        """通过文件ID反查物理路径（从之前搜索结果的缓存中获取）"""
        return self._fid_to_path.get(fid)
    
    def _next_id(self) -> int:
        """生成递增的请求ID"""
        self._request_id += 1
        return self._request_id
    
    def _call(self, method: str, input_data: dict) -> dict:
        """调用Anytxt JSON-RPC方法"""
        payload = {
            "id": self._next_id(),
            "jsonrpc": "2.0",
            "method": method,
            "params": {"input": input_data}
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = Request(
            self.rpc_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            method="POST"
        )
        
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            raise RuntimeError(f"Anytxt HTTP错误: {e.code} {e.reason}") from e
        except URLError as e:
            raise RuntimeError(
                f"无法连接Anytxt服务 ({self.rpc_url})，请确认ATGUI正在运行"
            ) from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Anytxt返回无效JSON: {e}") from e
        
        if "error" in result:
            error_msg = result["error"].get("message", "未知错误")
            raise RuntimeError(f"Anytxt JSON-RPC错误: {error_msg}")
        
        return result.get("result", {})
    
    def search(
        self,
        pattern: str,
        filter_dir: str = "",
        filter_ext: str = "*",
        last_modify_begin: int = 0,
        last_modify_end: int = 2147483647,
    ) -> int:
        """搜索文件，返回匹配数量
        
        Args:
            pattern: 搜索关键词
            filter_dir: 限定搜索目录
            filter_ext: 文件扩展名过滤
            last_modify_begin: 修改时间起始（Unix时间戳）
            last_modify_end: 修改时间结束（Unix时间戳）
        
        Returns:
            匹配文件数量
        """
        result = self._call(
            "ATRpcServer.Searcher.V1.Search",
            {
                "pattern": pattern,
                "filterDir": filter_dir,
                "filterExt": filter_ext,
                "lastModifyBegin": last_modify_begin,
                "lastModifyEnd": last_modify_end,
            }
        )
        # 区分"API 返回了 count 字段"与"result 嵌套为空"：
        # 正常情况下 output 中一定有 count，如果缺失说明返回结构异常
        output = result.get("data", {}).get("output")
        if output is None or "count" not in (output or {}):
            raise RuntimeError(f"Anytxt Search 返回异常: 缺少 count 字段, result={result}")
        return output["count"]
    
    def get_result(
        self,
        pattern: str,
        filter_dir: str = "",
        filter_ext: str = "*",
        last_modify_begin: int = 0,
        last_modify_end: int = 2147483647,
        limit: int = 300,
        offset: int = 0,
        order: int = 0,
    ) -> list[dict]:
        """获取搜索结果列表
        
        Args:
            pattern: 搜索关键词
            filter_dir: 限定搜索目录
            filter_ext: 文件扩展名过滤
            last_modify_begin: 修改时间起始
            last_modify_end: 修改时间结束
            limit: 返回数量限制
            offset: 分页偏移
            order: 排序方式 (0:默认, 1:修改时间升序, 2:修改时间降序, 3:路径升序, 4:路径降序)
        
        Returns:
            文件信息列表，每项包含 fid, name, path, size, modified
        """
        result = self._call(
            "ATRpcServer.Searcher.V1.GetResult",
            {
                "pattern": pattern,
                "filterDir": filter_dir,
                "filterExt": filter_ext,
                "lastModifyBegin": last_modify_begin,
                "lastModifyEnd": last_modify_end,
                "limit": str(limit),
                "offset": offset,
                "order": order,
            }
        )
        
        # Anytxt返回格式: files是数组的数组 [fid, lastModify, size, path]
        raw_files = result.get("data", {}).get("output", {}).get("files", [])
        
        # 转换为字典格式并缓存 fid -> path 映射关系
        files = []
        for file_arr in raw_files:
            if isinstance(file_arr, list) and len(file_arr) >= 4:
                fid = file_arr[0]
                path = file_arr[3]
                # 缓存 fid -> path 映射
                self._fid_to_path[fid] = path
                
                # 从路径中提取文件名
                name = path.split("\\")[-1] if "\\" in path else path.split("/")[-1]
                # 提取扩展名
                ext = "." + name.split(".")[-1] if "." in name else ""
                
                files.append({
                    "fid": fid,
                    "modified": file_arr[1],
                    "size": int(file_arr[2]) if file_arr[2] else 0,
                    "path": path,
                    "name": name,
                    "extension": ext,
                })
        
        return files

    def search_all_drives(
        self,
        pattern: str,
        filter_ext: str = "*",
        last_modify_begin: int = 0,
        last_modify_end: int = 2147483647,
    ) -> int:
        """在所有可用驱动器上搜索，返回总匹配数量"""
        drives = get_available_drives()
        total = 0
        for drive in drives:
            try:
                total += self.search(
                    pattern=pattern,
                    filter_dir=drive,
                    filter_ext=filter_ext,
                    last_modify_begin=last_modify_begin,
                    last_modify_end=last_modify_end,
                )
            except Exception:
                continue
        return total

    def get_result_all_drives(
        self,
        pattern: str,
        filter_ext: str = "*",
        last_modify_begin: int = 0,
        last_modify_end: int = 2147483647,
        limit: int = 300,
        offset: int = 0,
        order: int = 0,
    ) -> list[dict]:
        """在所有可用驱动器上搜索，合并结果

        当用户未指定搜索目录时使用此方法，自动遍历所有驱动器。
        """
        drives = get_available_drives()
        all_files: list[dict] = []
        seen_fids: set[str] = set()
        per_drive_limit = max(limit + offset, 100)  # 每个驱动器拉取足够数量以支持分页

        for drive in drives:
            try:
                files = self.get_result(
                    pattern=pattern,
                    filter_dir=drive,
                    filter_ext=filter_ext,
                    last_modify_begin=last_modify_begin,
                    last_modify_end=last_modify_end,
                    limit=per_drive_limit,
                    offset=0,  # 每个驱动器从0开始，最后统一分页
                    order=order,
                )
                for f in files:
                    fid = f.get("fid", "")
                    if fid and fid not in seen_fids:
                        seen_fids.add(fid)
                        all_files.append(f)
            except Exception:
                continue

        # 按排序规则整理（order=0 保持 Anytxt 默认排序不做二次排序）
        if order == 2:
            all_files.sort(key=lambda f: f.get("modified", 0), reverse=True)
        elif order == 1:
            all_files.sort(key=lambda f: f.get("modified", 0))
        elif order == 4:
            all_files.sort(key=lambda f: f.get("path", ""), reverse=True)
        elif order == 3:
            all_files.sort(key=lambda f: f.get("path", ""))

        # 分页
        return all_files[offset:offset + limit]

    def get_fragment(self, fid: str, pattern: str) -> str:
        """获取单个文本片段
        
        Args:
            fid: 文件ID
            pattern: 搜索关键词
        
        Returns:
            文本片段
        """
        result = self._call(
            "ATRpcServer.Searcher.V1.GetFragment",
            {
                "fid": fid,
                "pattern": pattern,
            }
        )
        return result.get("data", {}).get("output", {}).get("fragment", "")
    
    def get_fragment_all(self, fid: str, pattern: str) -> list[str]:
        """获取所有文本片段
        
        Args:
            fid: 文件ID
            pattern: 搜索关键词
        
        Returns:
            文本片段列表
        """
        result = self._call(
            "ATRpcServer.Searcher.V1.GetFragmentAll",
            {
                "fid": fid,
                "pattern": pattern,
            }
        )
        return result.get("data", {}).get("output", {}).get("fragments", [])
    
    def get_raw_text_by_fid(self, fid: str) -> str:
        """获取文件完整文本
        
        Args:
            fid: 文件ID
        
        Returns:
            文件完整文本
        """
        result = self._call(
            "ATRpcServer.Searcher.V1.GetRawTextByFID",
            {
                "fid": fid,
            }
        )
        return result.get("data", {}).get("output", {}).get("text", "")
    
    def sync_index(self, folder: str) -> bool:
        """同步指定文件夹到索引
        
        Args:
            folder: 要同步的文件夹路径
        
        Returns:
            是否成功
        """
        result = self._call(
            "ATRpcServer.Searcher.V1.SyncIndex",
            {
                "folder": folder,
            }
        )
        return result.get("errno", -1) == 0
    
    def ocr(self, file_path: str) -> str:
        """OCR识别图片文字
        
        Args:
            file_path: 图片文件路径
        
        Returns:
            识别出的文字
        """
        result = self._call(
            "ATRpcServer.Searcher.V1.OCR",
            {
                "file": file_path,
            }
        )
        return result.get("data", {}).get("output", {}).get("text", "")


def read_image_base64(file_path: str, max_size_kb: int = DEFAULT_MAX_IMAGE_KB) -> dict:
    """读取图片文件并返回 base64 数据

    返回格式: {"data": <base64_str>, "mime": <mime_type>, "size_kb": <int>, "ok": True}
    失败时: {"ok": False, "error": <错误信息>}
    """
    if not os.path.exists(file_path):
        return {"ok": False, "error": f"文件不存在: {file_path}"}

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        return {"ok": False, "error": f"不支持的图片格式: {ext}，支持 {', '.join(sorted(IMAGE_EXTENSIONS))}"}

    file_size = os.path.getsize(file_path)
    if file_size > max_size_kb * 1024:
        return {
            "ok": False,
            "error": f"图片过大 ({file_size / 1024:.0f}KB)，超过限制 ({max_size_kb}KB)"
        }

    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".bmp": "image/bmp",
        ".gif": "image/gif", ".tiff": "image/tiff",
        ".tif": "image/tiff", ".webp": "image/webp",
        ".ico": "image/x-icon",
    }

    try:
        with open(file_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        return {
            "ok": True,
            "data": data,
            "mime": mime_map.get(ext, "image/png"),
            "size_kb": file_size / 1024,
        }
    except Exception as e:
        return {"ok": False, "error": f"读取图片失败: {e}"}


def is_image_file(file_path: str) -> bool:
    """判断文件是否为图片"""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in IMAGE_EXTENSIONS


def get_max_images_in_search() -> int:
    """从环境变量读取搜索结果中图片标注数量上限"""
    return int(os.environ.get("ANYTXT_MAX_IMAGES_IN_SEARCH", str(DEFAULT_MAX_IMAGES_IN_SEARCH)))


def get_max_image_kb() -> int:
    """从环境变量读取图片大小上限(KB)"""
    return int(os.environ.get("ANYTXT_MAX_IMAGE_KB", str(DEFAULT_MAX_IMAGE_KB)))


# 全局客户端实例
_client: Optional[AnytxtClient] = None


def get_client() -> AnytxtClient:
    """获取Anytxt客户端单例，timeout 从环境变量读取"""
    global _client
    if _client is None:
        timeout_ms = int(os.environ.get("ANYTXT_TIMEOUT_MS", "10000"))
        _client = AnytxtClient(timeout_ms=timeout_ms)
    return _client
