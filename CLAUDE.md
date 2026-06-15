# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

本项目在 [mcp-everything-search](https://github.com/201715648/mcp-everything-search) 基础上扩展了 Anytxt 本地文档检索能力，形成双模式 MCP 服务器：

- **Everything 模式**（默认）：通过 Everything SDK / mdfind / locate 进行**文件名**搜索，跨 Windows/macOS/Linux
- **Anytxt 模式**（`ANYTXT_ENABLED=true`）：通过 Anytxt HTTP JSON-RPC API 进行**文件内容**全文检索，仅 Windows

## 开发命令

```bash
# 安装依赖
cd mcp-everything-search && uv sync

# 运行服务器（Everything 模式）
uv run mcp-server-everything-search

# 运行服务器（Anytxt 模式）
$env:ANYTXT_ENABLED = "true"; uv run mcp-server-everything-search

# MCP 检查器调试
npx @modelcontextprotocol/inspector uv run mcp-server-everything-search

# 类型检查
uv run pyright

# 代码检查
uv run ruff check

# 代码格式化
uv run ruff format

# 运行测试
uv run pytest

# 构建
uv build
```

## 架构

### 入口路由

`__main__.py` 根据 `ANYTXT_ENABLED` 环境变量分发到不同服务器实现：
- `true` → `anytxt_server.py` 的 `main()`
- `false`（默认）→ `server.py` 的 `main()`

两个服务器各自独立注册 MCP tools，**不共享工具列表**。

### Anytxt 分支（本项目核心扩展）

```
anytxt_client.py     JSON-RPC 2.0 客户端，封装 Anytxt 7 个 API 方法
anytxt_server.py     MCP 服务器，注册 5 个 tools，处理调用分发
```

**AnytxtClient** (`anytxt_client.py:10`) — 单例模式，通过 `get_client()` 获取：
- `_call(method, input_data)` — 底层 JSON-RPC 调用，处理序列化/超时/错误
- `search()` / `get_result()` / `get_fragment()` / `get_fragment_all()` / `get_raw_text_by_fid()` / `sync_index()` / `ocr()` — 7 个 API 方法

**MCP Tools**（注册在 `anytxt_server.py`）：
| Tool | 对应 API |
|------|----------|
| `anytxt_search` | Search → GetResult → 可选 GetFragment |
| `anytxt_get_context` | GetFragmentAll |
| `anytxt_read_file` | GetRawTextByFID |
| `anytxt_sync_index` | SyncIndex（需 `ANYTXT_ENABLE_SYNC=true`） |
| `anytxt_ocr` | OCR（需 `ANYTXT_ENABLE_OCR=true`） |

Anytxt API 的 `GetResult` 返回格式是数组的数组 `[fid, lastModify, size, path]`，`anytxt_client.py:140-161` 将其转换为字典格式。

### Everything 分支（上游项目）

```
server.py            MCP 服务器，注册 "search" tool，使用 Pydantic 校验参数
search_interface.py  策略模式 + 工厂模式，跨平台搜索抽象层
platform_search.py   Pydantic 参数模型，含平台特定的 schema 生成
everything_sdk.py    Windows Everything64.dll 的 ctypes 封装
```

**SearchProvider** (`search_interface.py:24`) — ABC，工厂方法 `get_provider()` 按 `platform.system()` 返回：
- `WindowsSearchProvider` → Everything SDK
- `MacSearchProvider` → mdfind
- `LinuxSearchProvider` → locate/plocate

## 关键设计决策

- **双模式互斥**：Everything 和 Anytxt 各自是完全独立的 MCP 服务器实例，不能同时使用。入口由 `ANYTXT_ENABLED` 环境变量硬切换。
- **Anytxt 仅 Windows**：Anytxt 软件本身只支持 Windows，因此 Anytxt 模式未做跨平台处理。
- **Anytxt 数据归一化**：`anytxt_client.py` 中的 `get_result()` 负责将 Anytxt 原始返回 `[fid, timestamp, size, path]` 转为带 key 的字典，屏蔽上游差异。
- **limit 为字符串**：Anytxt API 要求 `limit` 参数为字符串类型，`anytxt_client.py:133` 做了 `str(limit)` 转换。
- **索引/OCR 默认关闭**：sync_index 和 ocr 的 MCP tool 已注册但默认在环境变量中禁用，需显式开启。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ANYTXT_ENABLED` | `false` | 启用 Anytxt 模式 |
| `ANYTXT_RPC_URL` | `http://127.0.0.1:9920` | Anytxt JSON-RPC 地址 |
| `ANYTXT_DEFAULT_DIR` | 空 | 默认搜索目录 |
| `ANYTXT_DEFAULT_EXT` | `*` | 默认文件扩展名 |
| `ANYTXT_TIMEOUT_MS` | `10000` | 请求超时（毫秒） |
| `ANYTXT_MAX_RESULTS` | `50` | 最大搜索结果数 |
| `ANYTXT_MAX_FRAGMENTS` | `20` | 最大片段数 |
| `ANYTXT_MAX_RAW_CHARS` | `20000` | 最大返回字符数 |
| `ANYTXT_ENABLE_SYNC` | `false` | 启用索引同步工具 |
| `ANYTXT_ENABLE_OCR` | `false` | 启用 OCR 工具 |
| `EVERYTHING_SDK_PATH` | `D:\dev\tools\Everything-SDK\dll\Everything64.dll` | Everything SDK DLL 路径 |
