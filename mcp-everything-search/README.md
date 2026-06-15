# Everything Search MCP 服务器

[![smithery badge](https://smithery.ai/badge/mcp-server-everything-search)](https://smithery.ai/server/mcp-server-everything-search)

一个跨平台快速文件搜索 MCP 服务器，支持 Windows、macOS 和 Linux。Windows 上使用 [Everything](https://www.voidtools.com/) SDK，macOS 使用内置 `mdfind` 命令，Linux 使用 `locate`/`plocate` 命令。

## 工具

### search

在整个系统中搜索文件和文件夹。搜索能力和语法支持因平台而异：

- Windows：完整的 Everything SDK 功能（参见下方语法指南）
- macOS：基于 Spotlight 数据库的基本文件名和内容搜索
- Linux：基于 locate 数据库的基本文件名搜索

参数：

- `query`（必填）：搜索查询字符串。详见下方各平台说明。
- `max_results`（可选）：返回结果的最大数量（默认：100，最大：1000）
- `match_path`（可选）：匹配完整路径而非仅文件名（默认：false）
- `match_case`（可选）：启用大小写敏感搜索（默认：false）
- `match_whole_word`（可选）：仅匹配完整单词（默认：false）
- `match_regex`（可选）：启用正则表达式搜索（默认：false）
- `sort_by`（可选）：结果排序方式（默认：1）。可用选项：

```
  - 1: 按文件名排序（A → Z）
  - 2: 按文件名排序（Z → A）
  - 3: 按路径排序（A → Z）
  - 4: 按路径排序（Z → A）
  - 5: 按大小排序（小 → 大）
  - 6: 按大小排序（大 → 小）
  - 7: 按扩展名排序（A → Z）
  - 8: 按扩展名排序（Z → A）
  - 11: 按创建日期排序（旧 → 新）
  - 12: 按创建日期排序（新 → 旧）
  - 13: 按修改日期排序（旧 → 新）
  - 14: 按修改日期排序（新 → 旧）
```

示例：

```json
{
  "query": "*.py",
  "max_results": 50,
  "sort_by": 6
}
```

```json
{
  "query": "ext:py datemodified:today",
  "max_results": 10
}
```

响应包含：

- 文件/文件夹路径
- 文件大小（字节）
- 最后修改日期

### 搜索语法指南

各平台（Windows、macOS、Linux）支持的搜索语法详情，请参见 [SEARCH_SYNTAX.md](SEARCH_SYNTAX.md)。

## 前置条件

### Windows

1. [Everything](https://www.voidtools.com/) 搜索工具：
   - 从 https://www.voidtools.com/ 下载安装
   - **确保 Everything 服务正在运行**
2. Everything SDK：
   - 从 https://www.voidtools.com/support/everything/sdk/ 下载
   - 将 SDK 文件解压到系统中的某个位置

### Linux

1. 安装并初始化 `locate` 或 `plocate` 命令：
   - Ubuntu/Debian：`sudo apt-get install plocate` 或 `sudo apt-get install mlocate`
   - Fedora：`sudo dnf install mlocate`
2. 安装后更新数据库：
   - plocate：`sudo updatedb`
   - mlocate：`sudo /etc/cron.daily/mlocate`

### macOS

无需额外设置。服务器使用内置的 `mdfind` 命令。

## 安装

### 通过 Smithery 安装

通过 [Smithery](https://smithery.ai/server/mcp-server-everything-search) 为 Claude Desktop 自动安装：

```bash
npx -y @smithery/cli install mcp-server-everything-search --client claude
```

### 使用 uv（推荐）

使用 [`uv`](https://docs.astral.sh/uv/) 时无需专门安装。直接用 [`uvx`](https://docs.astral.sh/uv/guides/tools/) 运行 _mcp-server-everything-search_。

### 使用 PIP

也可以通过 pip 安装：

```
pip install mcp-server-everything-search
```

安装后，使用以下命令作为脚本运行：

```
python -m mcp_server_everything_search
```

## 配置

### Windows

服务器需要 Everything SDK DLL 可用：

环境变量：

```
EVERYTHING_SDK_PATH=path\to\Everything-SDK\dll\Everything64.dll
```

### Linux 和 macOS

无需额外配置。

### Claude Desktop 配置

根据你的平台，将以下配置之一添加到 `claude_desktop_config.json`：

<details>
<summary>Windows（使用 uvx）</summary>

```json
"mcpServers": {
  "everything-search": {
    "command": "uvx",
    "args": ["mcp-server-everything-search"],
    "env": {
      "EVERYTHING_SDK_PATH": "path/to/Everything-SDK/dll/Everything64.dll"
    }
  }
}
```

</details>

<details>
<summary>Windows（使用 pip 安装）</summary>

```json
"mcpServers": {
  "everything-search": {
    "command": "python",
    "args": ["-m", "mcp_server_everything_search"],
    "env": {
      "EVERYTHING_SDK_PATH": "path/to/Everything-SDK/dll/Everything64.dll"
    }
  }
}
```

</details>

<details>
<summary>Linux 和 macOS</summary>

```json
"mcpServers": {
  "everything-search": {
    "command": "uvx",
    "args": ["mcp-server-everything-search"]
  }
}
```

或使用 pip 安装：

```json
"mcpServers": {
  "everything-search": {
    "command": "python",
    "args": ["-m", "mcp_server_everything_search"]
  }
}
```

</details>

## 调试

可以使用 MCP 检查器调试服务器。uvx 安装方式：

```
npx @modelcontextprotocol/inspector uvx mcp-server-everything-search
```

如果在特定目录安装了包或正在进行开发：

```
git clone https://github.com/201715648/mcp-everything-search.git
cd mcp-everything-search/src/mcp_server_everything_search
npx @modelcontextprotocol/inspector uv run mcp-server-everything-search
```

查看服务器日志：

Linux/macOS：

```bash
tail -f ~/.config/Claude/logs/mcp*.log
```

Windows（PowerShell）：

```powershell
Get-Content -Path "$env:APPDATA\Claude\logs\mcp*.log" -Tail 20 -Wait
```

## 开发

如果进行本地开发，有两种测试更改的方式：

1. 运行 MCP 检查器测试更改。参见[调试](#调试)部分的运行说明。

2. 使用 Claude Desktop 应用测试。在 `claude_desktop_config.json` 中添加：

```json
"everything-search": {
  "command": "uv",
  "args": [
    "--directory",
    "/path/to/mcp-everything-search/src/mcp_server_everything_search",
    "run",
    "mcp-server-everything-search"
  ],
  "env": {
    "EVERYTHING_SDK_PATH": "path/to/Everything-SDK/dll/Everything64.dll"
  }
}
```

## 许可证

本 MCP 服务器基于 MIT License 授权。你可以在遵守 MIT License 条款的前提下自由使用、修改和分发本软件。详情请参见项目仓库中的 LICENSE 文件。

## 免责声明

本项目与 voidtools（Everything 搜索工具的创建者）无关联、未经其认可或赞助。这是一个独立项目，使用了公开可用的 Everything SDK。
