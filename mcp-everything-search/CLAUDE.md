# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在此仓库中工作时提供指导。

## 项目概述

这是一个双模式 MCP（模型上下文协议）服务器：

**Everything 模式（默认）** — 跨平台文件名搜索：
- **Windows**：使用 Everything SDK 进行快速索引搜索
- **macOS**：使用 `mdfind`（Spotlight）进行原生搜索
- **Linux**：使用 `locate`/`plocate` 进行文件系统搜索
- 暴露单个 `search` 工具

**Anytxt 模式**（`ANYTXT_ENABLED=true`） — Windows 本地文件**内容**全文检索：
- 通过 Anytxt HTTP JSON-RPC 2.0 API 进行搜索
- 独立 MCP Server 实例，注册 5 个工具
- `__main__.py` 根据环境变量分发到两个模式之一

两种模式**互斥**，不同时注册工具。

## 开发命令

### 测试和运行

```bash
# 使用 MCP 检查器测试运行
npx @modelcontextprotocol/inspector uv run mcp-server-everything-search

# 直接用 uv 运行
uv run mcp-server-everything-search

# 作为 Python 模块运行（pip 安装后）
python -m mcp_server_everything_search
```

### 代码质量

```bash
# 类型检查
uv run pyright

# 代码检查
uv run ruff check

# 代码格式化
uv run ruff format

# 运行测试
uv run pytest
```

### 构建

```bash
# 构建包
uv build
```

## 架构

### 入口路由（`__main__.py`）

`__main__.py:main()` 根据 `ANYTXT_ENABLED` 环境变量分发：
- `true` → `anytxt_server.main()`
- `false` → `server.main()`（默认）

两个服务器各自独立注册 MCP 工具，**不共享工具列表**。

### Everything 分支

1. **server.py** - 主 MCP 服务器实现
   - 定义 `search` 工具，使用平台特定的 schema
   - 使用 Pydantic 处理参数解析和验证
   - 将搜索请求路由到对应平台提供者
   - 返回格式化的搜索结果（TextContent）

2. **search_interface.py** - 抽象搜索提供者接口
   - `SearchProvider`：定义搜索契约的抽象基类
   - `WindowsSearchProvider`：Everything SDK 封装
   - `MacSearchProvider`：mdfind 命令封装
   - `LinuxSearchProvider`：locate/plocate 命令封装
   - `SearchResult`：所有平台通用的数据类

3. **platform_search.py** - 平台特定参数模型
   - `BaseSearchQuery`：通用搜索参数（query、max_results）
   - `WindowsSpecificParams`：Everything SDK 选项（match_path、match_case 等）
   - `MacSpecificParams`：mdfind 选项（live_updates、search_directory 等）
   - `LinuxSpecificParams`：locate 选项（ignore_case、regex_search 等）
   - `UnifiedSearchQuery`：组合所有参数模型，带平台感知的 schema 生成

4. **everything_sdk.py** - Windows Everything SDK 封装
   - `EverythingSDK`：Everything64.dll 的 ctypes 封装
   - Windows filetime 到 Python datetime 的转换
   - 完整错误处理，包含自定义 EverythingError 异常

### Anytxt 分支

1. **anytxt_client.py** — Anytxt HTTP JSON-RPC 2.0 客户端
   - `AnytxtClient`：封装 7 个 API 方法（search/get_result/get_fragment/get_fragment_all/get_raw_text_by_fid/sync_index/ocr）
   - `get_client()`：全局单例工厂函数
   - `get_result()` 负责将 Anytxt 原始格式 `[fid, lastModify, size, path]` 转换为字典格式
   - `limit` 参数自动转为字符串（Anytxt API 要求）

2. **anytxt_server.py** — Anytxt MCP 服务器
   - 注册 5 个 MCP 工具：`anytxt_search`、`anytxt_get_context`、`anytxt_read_file`、`anytxt_sync_index`、`anytxt_ocr`
   - 每个工具有独立的 handler 函数

### 关键设计模式

- **策略模式**：平台特定的搜索提供者实现通用的 SearchProvider 接口
- **工厂模式**：`SearchProvider.get_provider()` 根据 `platform.system()` 返回正确的提供者
- **单例模式**：`AnytxtClient` 通过 `get_client()` 全局共享一个实例

### 平台特定说明

**Windows**：
- Everything 模式需要 `EVERYTHING_SDK_PATH` 指向 Everything64.dll
- Anytxt 模式需要 ATGUI 进程运行并监听 `127.0.0.1:9920`

**macOS**：
- 使用子进程调用 `mdfind` 命令
- 无需额外依赖（内置）

**Linux**：
- 先检查 `plocate`，回退到 `locate`

### Anytxt API 注意点

- `GetResult` 的 `limit` 参数必须是字符串类型（`"300"` 而非 `300`）
- `order` 参数文档存在笔误：`3` 在文档中出现两次（路径升序/降序），第二个应为 `4`
- Unix 时间戳上限 `2147483647` = 2038-01-19（32 位上限）

## 环境变量

- `EVERYTHING_SDK_PATH`（Windows）：Everything64.dll 路径（默认：`D:\dev\tools\Everything-SDK\dll\Everything64.dll`）
- `ANYTXT_ENABLED`（默认：`false`）：启用 Anytxt 模式
- `ANYTXT_RPC_URL`（默认：`http://127.0.0.1:9920`）：Anytxt JSON-RPC 地址
- `ANYTXT_TIMEOUT_MS`（默认：`10000`）：请求超时时间
- `ANYTXT_DEFAULT_DIR`：默认搜索目录
- `ANYTXT_DEFAULT_EXT`（默认：`*`）：默认文件扩展名
- `ANYTXT_MAX_RESULTS`（默认：`50`）：最大搜索结果数
- `ANYTXT_MAX_FRAGMENTS`（默认：`20`）：最大片段数
- `ANYTXT_MAX_RAW_CHARS`（默认：`20000`）：最大返回字符数
- `ANYTXT_ENABLE_SYNC`（默认：`false`）：启用索引同步工具
- `ANYTXT_ENABLE_OCR`（默认：`false`）：启用 OCR 工具

## 安装方式

服务器支持三种安装方式：
1. **Smithery CLI**：`npx -y @smithery/cli install mcp-server-everything-search --client claude`
2. **uv（推荐）**：使用 `uvx mcp-server-everything-search`
3. **pip**：`pip install mcp-server-everything-search`，然后 `python -m mcp_server_everything_search`
