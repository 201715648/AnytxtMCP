"""Anytxt MCP Server - 基于Anytxt of 文档内容检索"""

import asyncio
import json
import os
import platform
import sys
from typing import List, Union
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import ImageContent, TextContent, Tool

from .anytxt_client import (
    AnytxtClient,
    get_client,
    is_image_file,
    read_image_base64,
    get_max_images_in_search,
    get_max_image_kb,
    get_available_drives,
)

# 环境变量默认值（代码级读取，不依赖 README 文档）
ENV_MAX_RESULTS = int(os.environ.get("ANYTXT_MAX_RESULTS", "100"))
ENV_DEFAULT_DIR = os.environ.get("ANYTXT_DEFAULT_DIR", "")
ENV_DEFAULT_EXT = os.environ.get("ANYTXT_DEFAULT_EXT", "*")
ENV_TIMEOUT_MS = int(os.environ.get("ANYTXT_TIMEOUT_MS", "10000"))
ENV_MAX_FRAGMENTS = int(os.environ.get("ANYTXT_MAX_FRAGMENTS", "20"))
ENV_MAX_RAW_CHARS = int(os.environ.get("ANYTXT_MAX_RAW_CHARS", "20000"))
ENV_ENABLE_SYNC = os.environ.get("ANYTXT_ENABLE_SYNC", "false").lower() in ("true", "1")
ENV_ENABLE_OCR = os.environ.get("ANYTXT_ENABLE_OCR", "false").lower() in ("true", "1")


def get_tools() -> List[Tool]:
    """返回Anytxt工具列表，供StdIO及SSE模式共享定义"""
    tools = [
        Tool(
            name="anytxt_search",
            description="""搜索本地文档内容，返回文件路径和匹配片段。

搜索范围：不指定目录时，自动搜索所有可用驱动器（C:、D:等）。
如需限定范围，请明确指定 directory 参数。

支持的搜索语法：
- 普通关键词：Hello
- 精确短语："This is"
- 布尔运算：Hello AND World, Hello OR World, NOT Hello
- 通配符：*.txt, Hello*

示例：
- "认证函数" - 搜索包含"认证函数"的文档
- "error AND log" - 搜索同时包含error and log的文档
- "*.md" - 搜索所有Markdown文件""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，支持布尔语法和通配符"
                    },
                    "directory": {
                        "type": "string",
                        "description": "限定搜索目录（留空则自动搜索所有驱动器 C:、D: 等）",
                        "default": ""
                    },
                    "extension": {
                        "type": "string",
                        "description": "文件扩展名过滤（如 txt, pdf, *）",
                        "default": "*"
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"返回结果数量限制（默认20，最大{ENV_MAX_RESULTS}）",
                        "default": 20,
                        "minimum": 1,
                        "maximum": ENV_MAX_RESULTS
                    },
                    "offset": {
                        "type": "integer",
                        "description": "分页偏移量",
                        "default": 0,
                        "minimum": 0
                    },
                    "order": {
                        "type": "integer",
                        "description": "排序方式: 0=默认, 1=修改时间升序, 2=修改时间降序, 3=路径升序, 4=路径降序",
                        "default": 0,
                        "minimum": 0,
                        "maximum": 4
                    },
                    "modified_after": {
                        "type": "integer",
                        "description": "修改时间起始（Unix时间戳），0 表示不限",
                        "default": 0,
                        "minimum": 0
                    },
                    "modified_before": {
                        "type": "integer",
                        "description": "修改时间结束（Unix时间戳），2147483647 表示不限",
                        "default": 2147483647,
                        "minimum": 0
                    },
                    "include_fragment": {
                        "type": "boolean",
                        "description": "是否返回内容片段",
                        "default": True
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="anytxt_get_context",
            description="""获取文件中与关键词相关的上下文片段。

用于深入查看某个文件中与搜索词相关的所有内容。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "fid": {
                        "type": "string",
                        "description": "文件ID，来自anytxt_search结果"
                    },
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "max_fragments": {
                        "type": "integer",
                        "description": "最大返回片段数（默认5）",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    }
                },
                "required": ["fid", "query"]
            }
        ),
        Tool(
            name="anytxt_read_file",
            description="""读取文件完整内容。

用于深度分析某个文件的完整内容。注意：大文件会被截断。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "fid": {
                        "type": "string",
                        "description": "文件ID，来自anytxt_search结果"
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "最大返回字符数（默认10000）",
                        "default": 10000,
                        "minimum": 1000,
                        "maximum": 50000
                    }
                },
                "required": ["fid"]
            }
        ),
    ]
    if ENV_ENABLE_SYNC:
        tools.append(Tool(
            name="anytxt_sync_index",
            description="""同步指定文件夹到Anytxt索引。

用于确保搜索结果包含最新的文件内容。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "description": "要同步的文件夹路径"
                    }
                },
                "required": ["folder"]
            }
        ))
    if ENV_ENABLE_OCR:
        tools.append(Tool(
            name="anytxt_ocr",
            description="""识别图片中的文字内容（需要Anytxt OCR版）。

用于提取图片、扫描件中的文字。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "图片文件路径"
                    }
                },
                "required": ["file_path"]
            }
        ))
    tools.append(Tool(
        name="anytxt_count",
        description="""统计匹配文档数量（不返回文件列表）。

用于快速了解有多少文件包含指定内容。支持与 anytxt_search 相同的搜索语法，速度更快。
适用场景：确认知识库中是否有相关内容，无需查看具体文件时。""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，支持布尔语法和通配符"
                },
                "directory": {
                    "type": "string",
                    "description": "限定搜索目录（留空则搜索所有驱动器 C:、D: 等）",
                    "default": ""
                },
                "extension": {
                    "type": "string",
                    "description": "文件扩展名过滤（如 txt, pdf, *）",
                    "default": "*"
                },
                "modified_after": {
                    "type": "integer",
                    "description": "修改时间起始（Unix时间戳），0 表示不限",
                    "default": 0,
                    "minimum": 0
                },
                "modified_before": {
                    "type": "integer",
                    "description": "修改时间结束（Unix时间戳），2147483647 表示不限",
                    "default": 2147483647,
                    "minimum": 0
                }
            },
            "required": ["query"]
        }
    ))
    tools.append(Tool(
        name="anytxt_status",
        description="""检查 Anytxt 服务状态和索引统计信息。

返回 Anytxt 连接状态、服务地址、超时设置和索引文件总数。无需参数。""",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ))
    tools.append(Tool(
        name="anytxt_view_image",
        description="""查看图片文件原图，将图片内容直接传递给 AI 视觉分析。

用于 anytxt_search 搜索到图片文件时，OCR 文本可能不完整或有误，通过此工具查看原图让 AI 直接识别。
每次调用只返回一张图片，避免上下文过载。不支持查看非图片文件。""",
        inputSchema={
            "type": "object",
            "properties": {
                "fid": {
                    "type": "string",
                    "description": "图片文件ID（来自 anytxt_search 结果，优先使用）"
                },
                "file_path": {
                    "type": "string",
                    "description": "图片文件路径（当没有 fid 时使用）"
                },
                "max_size_kb": {
                    "type": "integer",
                    "description": "图片大小上限(KB)，默认5120（5MB），超过此大小会拒绝",
                    "default": 5120,
                    "minimum": 100,
                    "maximum": 10240
                }
            },
            "required": []
        }
    ))
    tools.append(Tool(
        name="anytxt_search_files",
        description="""按文件名搜索文件（Everything 引擎，仅 Windows）。

这是纯文件名搜索工具，不搜索文件内容。使用 Everything SDK 进行高速文件索引查找。
支持 Everything 搜索语法：通配符(*,?)、布尔运算(|, !, <>)、函数(size:, ext:, datemodified: 等)。

**重要**：使用此工具前必须向用户说明并获得明确同意，然后将 user_confirmed 设为 true。
典型场景：Anytxt 不可用时作为文件名搜索替代方案，或用户明确要求按文件名搜索。""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询，支持 Everything 搜索语法"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数（默认100）",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000
                },
                "match_path": {
                    "type": "boolean",
                    "description": "匹配完整路径而非仅文件名",
                    "default": False
                },
                "match_case": {
                    "type": "boolean",
                    "description": "区分大小写",
                    "default": False
                },
                "match_whole_word": {
                    "type": "boolean",
                    "description": "全词匹配",
                    "default": False
                },
                "match_regex": {
                    "type": "boolean",
                    "description": "使用正则表达式",
                    "default": False
                },
                "sort_by": {
                    "type": "integer",
                    "description": "排序: 1=名称升 2=名称降 3=路径升 4=路径降 5=大小升 6=大小降 13=修改升 14=修改降",
                    "default": 1,
                    "minimum": 1,
                    "maximum": 26
                },
                "user_confirmed": {
                    "type": "boolean",
                    "description": "用户已明确同意使用 Everything 进行文件名搜索。必须先向用户说明并得到确认后设为 true。",
                    "default": False
                }
            },
            "required": ["query", "user_confirmed"]
        }
    ))
    return tools


async def dispatch_tool(client: AnytxtClient, name: str, arguments: dict) -> List[Union[TextContent, ImageContent]]:
    """分发工具调用接口，供 StdIO 及 SSE 模式共享"""
    if name == "anytxt_search":
        return await _handle_search(client, arguments)
    elif name == "anytxt_get_context":
        return await _handle_get_context(client, arguments)
    elif name == "anytxt_read_file":
        return await _handle_read_file(client, arguments)
    elif name == "anytxt_sync_index":
        return await _handle_sync_index(client, arguments)
    elif name == "anytxt_ocr":
        return await _handle_ocr(client, arguments)
    elif name == "anytxt_count":
        return await _handle_count(client, arguments)
    elif name == "anytxt_status":
        return await _handle_status(client, arguments)
    elif name == "anytxt_view_image":
        return await _handle_view_image(client, arguments)
    elif name == "anytxt_search_files":
        return await _handle_search_files(arguments)
    else:
        return [TextContent(
            type="text",
            text=f"未知工具: {name}"
        )]


async def serve() -> None:
    """运行Anytxt MCP服务器"""
    server = Server("anytxt-search")
    client = get_client()

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return get_tools()

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[Union[TextContent, ImageContent]]:
        try:
            return await dispatch_tool(client, name, arguments)
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"错误: {str(e)}"
            )]

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)


async def _get_result_all_drives_async(
    client: AnytxtClient,
    pattern: str,
    filter_ext: str = "*",
    last_modify_begin: int = 0,
    last_modify_end: int = 2147483647,
    limit: int = 300,
    offset: int = 0,
    order: int = 0,
) -> list[dict]:
    """在所有可用驱动器上异步并行搜索并合并结果"""
    drives = await asyncio.to_thread(get_available_drives)
    all_files: list[dict] = []
    seen_fids: set[str] = set()
    per_drive_limit = max(limit + offset, 100)

    tasks = []
    for drive in drives:
        tasks.append(
            asyncio.to_thread(
                client.get_result,
                pattern=pattern,
                filter_dir=drive,
                filter_ext=filter_ext,
                last_modify_begin=last_modify_begin,
                last_modify_end=last_modify_end,
                limit=per_drive_limit,
                offset=0,
                order=order,
            )
        )

    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results_list:
        if isinstance(res, Exception):
            continue
        for f in res:
            fid = f.get("fid", "")
            if fid and fid not in seen_fids:
                seen_fids.add(fid)
                all_files.append(f)

    # 安全的 modified 提取函数，防止 TypeError
    def safe_get_modified(f):
        val = f.get("modified", 0)
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    if order == 2:
        all_files.sort(key=safe_get_modified, reverse=True)
    elif order == 1:
        all_files.sort(key=safe_get_modified)
    elif order == 4:
        all_files.sort(key=lambda f: f.get("path", ""), reverse=True)
    elif order == 3:
        all_files.sort(key=lambda f: f.get("path", ""))

    return all_files[offset:offset + limit]


async def _search_all_drives_async(
    client: AnytxtClient,
    pattern: str,
    filter_ext: str = "*",
    last_modify_begin: int = 0,
    last_modify_end: int = 2147483647,
) -> int:
    """在所有可用驱动器上异步并行搜索匹配文件总数"""
    drives = await asyncio.to_thread(get_available_drives)
    tasks = []
    for drive in drives:
        tasks.append(
            asyncio.to_thread(
                client.search,
                pattern=pattern,
                filter_dir=drive,
                filter_ext=filter_ext,
                last_modify_begin=last_modify_begin,
                last_modify_end=last_modify_end,
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)
    total = 0
    for res in results:
        if isinstance(res, (int, float)):
            total += int(res)
    return total


async def _handle_search(client: AnytxtClient, args: dict) -> List[TextContent]:
    """处理anytxt_search工具调用"""
    query = args["query"]
    directory = args.get("directory", ENV_DEFAULT_DIR)
    extension = args.get("extension", ENV_DEFAULT_EXT)
    limit = min(args.get("limit", 20), ENV_MAX_RESULTS)
    offset = args.get("offset", 0)
    order = args.get("order", 0)
    include_fragment = args.get("include_fragment", True)
    modified_after = args.get("modified_after", 0)
    modified_before = args.get("modified_before", 2147483647)

    get_kwargs = dict(
        pattern=query,
        filter_ext=extension,
        limit=limit,
        offset=offset,
        order=order,
        last_modify_begin=modified_after,
        last_modify_end=modified_before,
    )

    if directory:
        results = await asyncio.to_thread(client.get_result, filter_dir=directory, **get_kwargs)
    else:
        results = await _get_result_all_drives_async(client, **get_kwargs)

    if not results:
        scope = directory or "所有驱动器(C:、D:等)"
        return [TextContent(
            type="text",
            text=f"未找到包含 '{query}' 的文档\n搜索范围: {scope}\n扩展名过滤: {extension}\n建议: 尝试更换关键词、扩大搜索范围或检查 Anytxt 索引是否包含目标文件"
        )]

    # 格式化输出
    output_lines = [f"找到 {len(results)} 个相关文档:\n"]
    max_images = get_max_images_in_search()
    image_count = 0

    for i, file_info in enumerate(results, 1):
        fid = file_info.get("fid", "")
        name = file_info.get("name", "未知")
        path = file_info.get("path", "未知")
        ext = file_info.get("extension", "")
        size = file_info.get("size", 0)
        modified = file_info.get("modified", "")

        # 检测图片文件
        is_image = is_image_file(path)

        output_lines.append(f"## {i}. {name}")
        output_lines.append(f"- **文件ID**: {fid}")
        output_lines.append(f"- **路径**: {path}")
        if ext:
            if is_image and image_count < max_images:
                output_lines.append(f"- **类型**: {ext} ※ 图片文件，**OCR 识别可能不完整或有误**，可调用 `anytxt_view_image` 查看原图让 AI 直接分析")
                image_count += 1
            elif is_image:
                output_lines.append(f"- **类型**: {ext} ※ 图片文件，OCR 可能不完整（本次已标注 {max_images} 张图片，此结果不再重复提示）")
            else:
                output_lines.append(f"- **类型**: {ext}")
        if size:
            output_lines.append(f"- **大小**: {size:,} 字节")
        if modified:
            output_lines.append(f"- **修改时间**: {modified}")

        # 获取内容片段
        if include_fragment and fid:
            try:
                fragment = await asyncio.to_thread(client.get_fragment, fid, query)
                # 回退：片段为空时读取原文提取关键词上下文
                if not fragment:
                    try:
                        raw_text = await asyncio.to_thread(client.get_raw_text_by_fid, fid)
                        if raw_text and query:
                            idx = raw_text.lower().find(query.lower())
                            if idx >= 0:
                                start = max(0, idx - 100)
                                end = min(len(raw_text), idx + len(query) + 100)
                                fragment = raw_text[start:end]
                                if start > 0:
                                    fragment = "..." + fragment
                                if end < len(raw_text):
                                    fragment = fragment + "..."
                    except Exception:
                        pass
                if fragment:
                    prefix = "- **OCR识别**" if is_image else "- **匹配内容**"
                    output_lines.append(f"{prefix}: {fragment}")
            except Exception:
                pass

        output_lines.append("")

    return [TextContent(
        type="text",
        text="\n".join(output_lines)
    )]


async def _handle_get_context(client: AnytxtClient, args: dict) -> List[TextContent]:
    """处理anytxt_get_context工具调用"""
    fid = args["fid"]
    query = args["query"]
    max_fragments = min(args.get("max_fragments", 5), ENV_MAX_FRAGMENTS)

    # 获取所有片段
    fragments = await asyncio.to_thread(client.get_fragment_all, fid, query)

    if not fragments:
        return [TextContent(
            type="text",
            text=f"未找到与 '{query}' 相关的上下文 (FID: {fid})"
        )]

    # 限制数量
    fragments = fragments[:max_fragments]

    output_lines = [f"找到 {len(fragments)} 个相关片段:\n"]

    for i, fragment in enumerate(fragments, 1):
        output_lines.append(f"### 片段 {i}")
        output_lines.append(f"```\n{fragment}\n```\n")

    return [TextContent(
        type="text",
        text="\n".join(output_lines)
    )]


async def _handle_read_file(client: AnytxtClient, args: dict) -> List[TextContent]:
    """处理anytxt_read_file工具调用"""
    fid = args["fid"]
    max_chars = min(args.get("max_chars", 10000), ENV_MAX_RAW_CHARS)

    # 获取完整文本
    raw_text = await asyncio.to_thread(client.get_raw_text_by_fid, fid)

    if not raw_text:
        return [TextContent(
            type="text",
            text=f"无法读取文件内容 (FID: {fid})，文件可能已被删除或索引中不存在"
        )]

    original_len = len(raw_text)
    truncated = original_len > max_chars
    display_text = raw_text[:max_chars] + "\n\n... [内容已截断]" if truncated else raw_text

    output_lines = [f"文件内容 (原始 {original_len} 字符):"]
    if truncated:
        output_lines.append(f"注意: 已截断，显示前 {max_chars} 字符\n")
    output_lines.append(f"```\n{display_text}\n```")

    return [TextContent(
        type="text",
        text="\n".join(output_lines)
    )]


async def _handle_sync_index(client: AnytxtClient, args: dict) -> List[TextContent]:
    """处理anytxt_sync_index工具调用"""
    folder = args["folder"]

    success = await asyncio.to_thread(client.sync_index, folder)

    if success:
        return [TextContent(
            type="text",
            text=f"已成功同步文件夹: {folder}"
        )]
    else:
        return [TextContent(
            type="text",
            text=f"同步文件夹失败: {folder}"
        )]


async def _handle_ocr(client: AnytxtClient, args: dict) -> List[TextContent]:
    """处理anytxt_ocr工具调用"""
    file_path = args["file_path"]

    text = await asyncio.to_thread(client.ocr, file_path)

    if not text:
        return [TextContent(
            type="text",
            text=f"无法识别图片中的文字: {file_path}"
        )]

    return [TextContent(
        type="text",
        text=f"识别结果:\n\n```\n{text}\n```"
    )]


async def _handle_view_image(client: AnytxtClient, args: dict) -> List[Union[TextContent, ImageContent]]:
    """处理anytxt_view_image工具调用 - 读取图片返回给AI"""
    fid = args.get("fid", "")
    file_path = args.get("file_path", "")
    max_size_kb = args.get("max_size_kb", get_max_image_kb())

    # 优先通过 fid 获取文件路径 (利用 AnytxtClient 实例维护的缓存字典)
    if fid and not file_path:
        file_path = client.get_path_by_fid(fid) or ""

    if not file_path:
        return [TextContent(
            type="text",
            text="错误: 未能根据提供的 fid 找到文件路径，或未提供 file_path（图片文件路径）。可从 anytxt_search 结果中获取路径。"
        )]

    if not is_image_file(file_path):
        return [TextContent(
            type="text",
            text=f"错误: 不是图片文件 ({os.path.splitext(file_path)[1]}). 仅支持 jpg/png/bmp/gif/tiff/webp/ico"
        )]

    result = await asyncio.to_thread(read_image_base64, file_path, max_size_kb)

    if not result["ok"]:
        return [TextContent(
            type="text",
            text=f"读取图片失败: {result['error']}"
        )]

    return [
        TextContent(
            type="text",
            text=f"图片: {os.path.basename(file_path)} ({result['size_kb']:.0f}KB)\n路径: {file_path}\n"
                 f"以下为原始图片内容，AI 可直接识别图中文字或信息，与 OCR 结果交叉验证："
        ),
        ImageContent(
            type="image",
            data=result["data"],
            mimeType=result["mime"],
        ),
    ]


async def _handle_count(client: AnytxtClient, args: dict) -> List[TextContent]:
    """处理anytxt_count工具调用 - 仅返回匹配数量"""
    query = args["query"]
    directory = args.get("directory", ENV_DEFAULT_DIR)
    extension = args.get("extension", ENV_DEFAULT_EXT)
    modified_after = args.get("modified_after", 0)
    modified_before = args.get("modified_before", 2147483647)

    if directory:
        count = await asyncio.to_thread(
            client.search,
            pattern=query,
            filter_dir=directory,
            filter_ext=extension,
            last_modify_begin=modified_after,
            last_modify_end=modified_before,
        )
    else:
        count = await _search_all_drives_async(
            client,
            pattern=query,
            filter_ext=extension,
            last_modify_begin=modified_after,
            last_modify_end=modified_before,
        )

    scope = directory or "所有驱动器(C:、D:等)"
    return [TextContent(
        type="text",
        text=f"搜索 '{query}' 找到 {count} 个匹配文档\n搜索范围: {scope}\n扩展名过滤: {extension}"
    )]


async def _handle_status(client: AnytxtClient, args: dict) -> List[TextContent]:
    """处理anytxt_status - 健康检查和状态查询"""
    lines = []
    lines.append(f"**Anytxt 服务地址**: {client.rpc_url}")
    lines.append(f"**超时时间**: {client.timeout}s")
    lines.append("")

    try:
        await asyncio.to_thread(client.search, pattern="anytxt_health_check_test_xyz", filter_ext="*")
        lines.append("**连接状态**: 已连接")
        lines.append("")

        try:
            total1 = await asyncio.to_thread(client.search, pattern="the", filter_dir="C:\\", filter_ext="*")
            total2 = await asyncio.to_thread(client.search, pattern="the", filter_dir="D:\\", filter_ext="*")
            lines.append(f"**索引规模估算**: C盘 {total1:,} / D盘 {total2:,} (含 'the' 的文件)")
        except Exception:
            lines.append("**索引规模**: 无法获取（索引可能为空或查询超时）")

    except Exception as e:
        lines.append("**连接状态**: 已断开")
        lines.append(f"**错误信息**: {str(e)}")
        lines.append("**建议**: 确认 ATGUI 正在运行并监听正确端口（默认 127.0.0.1:9920）")

    return [TextContent(
        type="text",
        text="\n".join(lines)
    )]


async def _handle_search_files(args: dict) -> List[TextContent]:
    """处理anytxt_search_files - Everything 文件名搜索（需用户确认）"""
    if not args.get("user_confirmed", False):
        return [TextContent(
            type="text",
            text="此工具使用 Everything 文件索引引擎进行文件名搜索（不搜索文件内容）。\n"
                 "请先向用户说明并得到确认后，将 user_confirmed 参数设为 true 再调用。"
        )]

    if platform.system().lower() != "windows":
        return [TextContent(
            type="text",
            text="anytxt_search_files 仅支持 Windows 平台（需要 Everything SDK）。"
        )]

    query = args["query"]
    max_results = args.get("max_results", 100)
    match_path = args.get("match_path", False)
    match_case = args.get("match_case", False)
    match_whole_word = args.get("match_whole_word", False)
    match_regex = args.get("match_regex", False)
    sort_by = args.get("sort_by", 1)

    try:
        from .search_interface import WindowsSearchProvider
        provider = WindowsSearchProvider()
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"无法加载 Everything SDK: {str(e)}\n"
                 "请确认 EVERYTING_SDK_PATH 环境变量指向 Everything64.dll"
        )]

    try:
        results = await asyncio.to_thread(
            provider.everything_sdk.search_files,
            query=query,
            max_results=max_results,
            match_path=match_path,
            match_case=match_case,
            match_whole_word=match_whole_word,
            match_regex=match_regex,
            sort_by=sort_by,
        )
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Everything 搜索失败: {str(e)}"
        )]

    if not results:
        return [TextContent(
            type="text",
            text=f"未找到匹配 '{query}' 的文件"
        )]

    output_lines = [f"找到 {len(results)} 个匹配文件:\n"]
    for i, r in enumerate(results, 1):
        path = r.path
        name = r.filename
        ext = r.extension or ""
        size = r.size
        modified = r.modified or "N/A"
        created = r.created or "N/A"

        output_lines.append(f"## {i}. {name}")
        output_lines.append(f"- **路径**: {path}")
        if ext:
            output_lines.append(f"- **类型**: {ext}")
        output_lines.append(f"- **大小**: {size:,} 字节")
        output_lines.append(f"- **创建时间**: {created}")
        output_lines.append(f"- **修改时间**: {modified}")
        output_lines.append("")

    return [TextContent(
        type="text",
        text="\n".join(output_lines)
    )]


def configure_windows_console():
    """配置Windows控制台UTF-8输出"""
    import ctypes

    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(handle, mode)
        
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')


def main() -> None:
    """主入口"""
    import asyncio
    import logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    configure_windows_console()
    
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logging.info("服务器已停止")
        sys.exit(0)
    except Exception as e:
        logging.error(f"服务器错误: {e}", exc_info=True)
        sys.exit(1)
