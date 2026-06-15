# Anytxt MCP Server

基于 [mcp-everything-search](https://github.com/201715648/mcp-everything-search) 扩展的 Anytxt 本地文档检索 MCP 服务器。

## 功能特性

- **anytxt_search** - 搜索本地文档内容，返回文件路径和匹配片段
- **anytxt_get_context** - 获取文件中与关键词相关的上下文片段
- **anytxt_read_file** - 读取文件完整内容
- **anytxt_sync_index** - 同步指定文件夹到索引
- **anytxt_ocr** - OCR识别图片文字（需要Anytxt OCR版）

## 前置条件

1. **Anytxt软件** - 从 [anytxt.net](https://anytxt.net/) 下载安装
2. **启用API** - 在Anytxt中：帮助 → API → 启用HTTP JSON-RPC API
3. **Python 3.10+** - 已安装
4. **uv** - 推荐的包管理器

## 快速开始

### 1. 安装uv（如果未安装）

```bash
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 克隆项目

```bash
git clone https://github.com/201715648/mcp-everything-search.git
cd mcp-everything-search
```

### 3. 安装依赖

```bash
uv sync
```

### 4. 配置Claude Desktop

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "anytxt-search": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-everything-search",
        "run",
        "mcp-server-everything-search"
      ],
      "env": {
        "ANYTXT_ENABLED": "true",
        "ANYTXT_RPC_URL": "http://127.0.0.1:9920"
      }
    }
  }
}
```

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `ANYTXT_ENABLED` | `false` | 启用Anytxt模式 |
| `ANYTXT_RPC_URL` | `http://127.0.0.1:9920` | Anytxt JSON-RPC地址 |
| `ANYTXT_DEFAULT_DIR` | 空 | 默认搜索目录 |
| `ANYTXT_DEFAULT_EXT` | `*` | 默认文件扩展名 |
| `ANYTXT_TIMEOUT_MS` | `10000` | 请求超时时间（毫秒） |
| `ANYTXT_MAX_RESULTS` | `50` | 最大搜索结果数 |
| `ANYTXT_MAX_FRAGMENTS` | `20` | 最大片段数 |
| `ANYTXT_MAX_RAW_CHARS` | `20000` | 最大返回字符数 |
| `ANYTXT_ENABLE_SYNC` | `false` | 启用索引同步工具 |
| `ANYTXT_ENABLE_OCR` | `false` | 启用OCR工具 |

## 使用示例

### 搜索文档

```
用户: 帮我找一下认证函数的文档
AI: [调用 anytxt_search] 搜索 "认证函数"
```

### 日志分析

```
用户: [粘贴错误日志]
AI: [分析日志] 发现未知错误码，调用 anytxt_search 搜索相关文档
```

### 代码理解

```
用户: 这个函数是干什么的？
AI: [阅读代码] 遇到不熟悉的API，调用 anytxt_search 搜索文档
```

## 搜索语法

Anytxt支持多种搜索语法：

- **普通关键词**: `Hello`
- **精确短语**: `"This is"`
- **布尔运算**: `Hello AND World`, `Hello OR World`, `NOT Hello`
- **通配符**: `*.txt`, `Hello*`

## 开发

### 测试

```bash
# 运行MCP检查器
npx @modelcontextprotocol/inspector uv run mcp-server-everything-search

# 运行单元测试
uv run pytest
```

### 代码质量

```bash
# 类型检查
uv run pyright

# 代码检查
uv run ruff check

# 代码格式化
uv run ruff format
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 致谢

- [mcp-everything-search](https://github.com/201715648/mcp-everything-search) - 基础项目
- [Anytxt](https://anytxt.net/) - 本地文档搜索引擎
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP协议
