# 搜索语法指南

## Windows 搜索（Everything SDK）

以下高级搜索功能仅在 Windows 上使用 Everything SDK 时可用：

### 基本运算符

- `空格`：AND 运算符
- `|`：OR 运算符
- `!`：NOT 运算符
- `< >`：分组
- `" "`：搜索精确短语

### 通配符

- `*`：匹配零个或多个字符
- `?`：匹配恰好一个字符

注意：通配符默认匹配整个文件名。关闭"匹配完整文件名"可在任意位置匹配通配符。

### 函数

#### 大小和数量

- `size:<大小>[kb|mb|gb]`：按文件大小搜索
- `count:<最大数量>`：限制结果数量
- `childcount:<数量>`：包含指定数量子项的文件夹
- `childfilecount:<数量>`：包含指定数量文件的文件夹
- `childfoldercount:<数量>`：包含指定数量子文件夹的文件夹
- `len:<长度>`：匹配文件名长度

#### 日期

- `datemodified:<日期>`, `dm:<日期>`：修改日期
- `dateaccessed:<日期>`, `da:<日期>`：访问日期
- `datecreated:<日期>`, `dc:<日期>`：创建日期
- `daterun:<日期>`, `dr:<日期>`：最后运行日期
- `recentchange:<日期>`, `rc:<日期>`：最近更改日期

日期格式：YYYY[-MM[-DD[Thh[:mm[:ss[.sss]]]]]] 或 today、yesterday、lastweek 等。

#### 文件属性和类型

- `attrib:<属性>`, `attributes:<属性>`：按文件属性搜索（A:归档，H:隐藏，S:系统等）
- `type:<类型>`：按文件类型搜索
- `ext:<列表>`：按分号分隔的扩展名列表搜索

#### 路径和名称

- `path:<路径>`：在指定路径中搜索
- `parent:<路径>`, `infolder:<路径>`, `nosubfolders:<路径>`：在指定路径中搜索（不含子文件夹）
- `startwith:<文本>`：以指定文本开头的文件
- `endwith:<文本>`：以指定文本结尾的文件
- `child:<文件名>`：包含指定子文件的文件夹
- `depth:<数量>`, `parents:<数量>`：指定文件夹深度的文件
- `root`：没有父文件夹的文件
- `shell:<名称>`：在已知 Shell 文件夹中搜索

#### 重复项和列表

- `dupe, namepartdupe, attribdupe, dadupe, dcdupe, dmdupe, sizedupe`：查找重复项
- `filelist:<列表>`：搜索管道符（|）分隔的文件列表
- `filelistfilename:<文件名>`：从列表文件搜索文件
- `frn:<frn列表>`：按文件引用编号搜索
- `fsi:<索引>`：按文件系统索引搜索
- `empty`：查找空文件夹

### 函数语法

- `function:value`：等于该值
- `function:<=value`：小于或等于
- `function:<value`：小于
- `function:=value`：等于
- `function:>value`：大于
- `function:>=value`：大于或等于
- `function:start..end`：值范围
- `function:start-end`：值范围

### 修饰符

- `case:`, `nocase:`：启用/禁用大小写敏感
- `file:`, `folder:`：仅匹配文件或文件夹
- `path:`, `nopath:`：匹配完整路径或仅文件名
- `regex:`, `noregex:`：启用/禁用正则表达式
- `wfn:`, `nowfn:`：匹配完整文件名或任意位置
- `wholeword:`, `ww:`：仅匹配完整单词
- `wildcards:`, `nowildcards:`：启用/禁用通配符

### 示例

1. 查找今天修改的 Python 文件：
   `ext:py datemodified:today`

2. 查找大型视频文件：
   `ext:mp4|mkv|avi size:>1gb`

3. 在特定文件夹中查找文件：
   `path:C:\Projects *.js`

## macOS 搜索（mdfind）

macOS 通过 `mdfind` 命令使用 Spotlight 的元数据搜索功能。支持以下特性：

### 命令选项

- `-live`：文件更改时实时更新搜索结果
- `-count`：仅显示匹配数量
- `-onlyin directory`：将搜索限制在特定目录
- `-literal`：将查询视为字面文本，不做解释
- `-interpret`：将查询解释为在 Spotlight 菜单中键入的格式

### 基本搜索

- 简单文本搜索在任何元数据属性中查找匹配
- 搜索字符串支持通配符（`*`）
- 多个单词视为 AND 条件
- 查询中的空格有意义
- 使用圆括号 () 对表达式分组

### 搜索运算符

- `|`（OR）：匹配任一单词，如 `"image|photo"`
- `-`（NOT）：排除匹配，如 `-screenshot`
- `=`、`==`（等于）
- `!=`（不等于）
- `<`、`>`（小于/大于）
- `<=`、`>=`（小于等于/大于等于）

### 值比较修饰符

使用方括号配合以下修饰符：

- `[c]`：大小写不敏感比较
- `[d]`：变音符号不敏感
- 可以组合使用，如 `[cd]` 同时启用两者

### 内容类型（kind:）

- `application`、`app`：应用程序
- `audio`、`music`：音频/音乐文件
- `bookmark`：书签
- `contact`：联系人
- `email`、`mail message`：电子邮件
- `event`：日历事件
- `folder`：文件夹
- `font`：字体
- `image`：图片
- `movie`：影片
- `pdf`：PDF 文档
- `preferences`：系统偏好设置
- `presentation`：演示文稿
- `todo`：日历待办事项

### 日期过滤器（date:）

使用以下关键词进行基于时间的搜索：

- `today`、`yesterday`、`tomorrow`
- `this week`、`next week`
- `this month`、`next month`
- `this year`、`next year`

或使用时间函数：

- `$time.today()`
- `$time.yesterday()`
- `$time.this_week()`
- `$time.this_month()`
- `$time.this_year()`
- `$time.tomorrow()`
- `$time.next_week()`
- `$time.next_month()`
- `$time.next_year()`

### 常用元数据属性

使用以下属性搜索特定元数据：

- `kMDItemAuthors`：文档作者
- `kMDItemContentType`：文件类型
- `kMDItemContentTypeTree`：文件类型层级
- `kMDItemCreator`：创建应用程序
- `kMDItemDescription`：文件描述
- `kMDItemDisplayName`：显示名称
- `kMDItemFSContentChangeDate`：文件修改日期
- `kMDItemFSCreationDate`：文件创建日期
- `kMDItemFSName`：文件名
- `kMDItemKeywords`：关键词/标签
- `kMDItemLastUsedDate`：最后使用日期
- `kMDItemNumberOfPages`：页数
- `kMDItemTitle`：文档标题
- `kMDItemUserTags`：用户标签

### 示例

1. 查找昨天修改的图片：
   `kind:image date:yesterday`

2. 按作者查找文档（不区分大小写）：
   `kMDItemAuthors ==[c] "John Doe"`

3. 在特定目录中查找文件：
   `mdfind -onlyin ~/Documents "query"`

4. 按标签查找文件：
   `kMDItemUserTags = "Important"`

5. 查找由某应用程序创建的文件：
   `kMDItemCreator = "Pixelmator*"`

6. 查找包含特定文本的 PDF：
   `kind:pdf "search term"`

7. 查找最近的演示文稿：
   `kind:presentation date:this week`

8. 统计匹配文件数：
   `mdfind -count "kind:image date:today"`

9. 监控新的匹配项：
   `mdfind -live "kind:pdf"`

10. 复杂元数据搜索：
    `kMDItemContentTypeTree = "public.image" && kMDItemUserTags = "vacation" && kMDItemFSContentChangeDate >= $time.this_month()`

注意：使用 `mdls filename` 查看特定文件的所有可用元数据属性。

## Linux 搜索（locate/plocate）

Linux 使用 locate/plocate 命令进行快速文件名搜索。支持以下特性：

### 基本搜索

- 简单文本搜索匹配文件名
- 多个单词视为 AND 条件
- 支持通配符（`*` 和 `?`）
- 默认不区分大小写

### 搜索选项

- `-i`：不区分大小写搜索（默认）
- `-c`：统计匹配数而不显示结果
- `-r` 或 `--regex`：使用正则表达式
- `-b`：仅匹配基本名称
- `-w`：仅匹配完整单词

### 示例

1. 查找所有 Python 文件：
   `*.py`

2. 在主目录中查找文件：
   `/home/username/*`

3. 区分大小写搜索特定文件：
   `--regex "^/etc/[A-Z].*\.conf$"`

4. 统计匹配文件数：
   结合 `-c` 参数使用

注意：locate 数据库必须保持最新才能获得准确结果。运行 `sudo updatedb` 手动更新数据库。
