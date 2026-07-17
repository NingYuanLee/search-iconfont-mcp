# Iconfont MCP Server

基于 Python 的 MCP (Model Context Protocol) 服务，为 AI 助手 (Cursor / Claude Desktop 等) 提供从 [iconfont.cn](https://www.iconfont.cn/) 搜索和下载 SVG 图标的能力。

---

## 目录

- [功能特性](#功能特性)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [MCP 配置](#mcp-配置)
  - [Cursor 配置](#cursor-配置)
  - [Claude Desktop 配置](#claude-desktop-配置)
  - [环境变量说明](#环境变量说明)
- [工具说明](#工具说明)
  - [iconfont_login](#iconfont_login)
  - [iconfont_search_icons](#iconfont_search_icons)
  - [iconfont_download_icon](#iconfont_download_icon)
  - [iconfont_check_status](#iconfont_check_status)
  - [iconfont_logout](#iconfont_logout)
- [HTML 原型使用指南](#html-原型使用指南)
  - [典型工作流](#典型工作流)
  - [对话示例](#对话示例)
  - [SVG 嵌入方式](#svg-嵌入方式)
- [常见问题](#常见问题)
- [故障排查](#故障排查)
- [License](#license)

---

## 功能特性

- **图标搜索**: 通过中文关键词搜索 iconfont.cn 百万级图标库
- **风格过滤**: 支持线性(line)、填充(fill)、扁平(flat)、手绘(hand)、简约(simple)、复杂(complex) 六种风格
- **SVG 下载**: 下载完整矢量 SVG 文件到本地，可直接嵌入 HTML
- **双登录方式**: 支持 Playwright 自动登录（手机号+密码）或直接 Cookie 注入
- **验证码处理**: 自动检测验证码，提示用户手动处理

---

## 环境要求

- Python 3.10+
- Playwright (用于自动登录)
- 一个 [iconfont.cn](https://www.iconfont.cn/) 账号 (免费注册)

---

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd search-iconfont
```

### 2. 安装依赖

```bash
pip install -r requirements.txt

# 安装 Playwright 浏览器 (仅 Chromium)
playwright install chromium
```

### 3. 配置环境变量

在 MCP 配置中设置以下环境变量:

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `ICONFONT_PHONE` | 条件必填¹ | iconfont.cn 注册手机号 |
| `ICONFONT_PASSWORD` | 条件必填¹ | iconfont.cn 登录密码 |
| `ICONFONT_COOKIE` | 条件必填¹ | EGG_SESS_ICONFONT Cookie 值 |

> ¹ 三种登录方式任选其一: (1) 手机号+密码自动登录, (2) 直接 Cookie 注入, (3) 先配置再调用 `iconfont_login` 工具

### 4. 验证安装

```bash
python server.py
# 输出: Iconfont MCP Server 启动中...
```

---

## MCP 配置

### Cursor 配置

编辑项目根目录的 `.cursor/mcp.json` (或 Cursor 全局设置):

```json
{
  "mcpServers": {
    "iconfont": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/search-iconfont",
      "env": {
        "ICONFONT_PHONE": "13800138000",
        "ICONFONT_PASSWORD": "your_password"
      }
    }
  }
}
```

> **Windows 路径示例**: `"cwd": "D:/工作文件/mcp_project/search-iconfont"`

### Claude Desktop 配置

编辑 `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "iconfont": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/search-iconfont",
      "env": {
        "ICONFONT_PHONE": "13800138000",
        "ICONFONT_PASSWORD": "your_password"
      }
    }
  }
}
```

### 环境变量说明

**方式一：手机号+密码自动登录 (推荐)**

```json
"env": {
  "ICONFONT_PHONE": "13800138000",
  "ICONFONT_PASSWORD": "your_password"
}
```

首次使用时，MCP 服务启动后需先调用 `iconfont_login` 工具完成登录。Playwright 会打开无头浏览器自动填充并登录。

**方式二：直接 Cookie 注入 (跳过自动登录)**

如果你遇到验证码无法自动登录，可以手动获取 Cookie:

1. 浏览器访问 https://www.iconfont.cn/ 并登录
2. 按 F12 打开开发者工具
3. 进入 Application → Cookies → www.iconfont.cn
4. 复制 `EGG_SESS_ICONFONT` 的值

然后在 MCP 配置中设置:

```json
"env": {
  "ICONFONT_COOKIE": "U8AXvqwdm-42-umGXGwgKq_..."
}
```

> Cookie 有效期约 1 年，过期后需重新获取。

---

## 工具说明

### iconfont_login

登录 iconfont.cn。

- **参数**: 无 (从环境变量读取凭据)
- **返回示例**:

```json
{
  "success": true,
  "message": "登录成功 (账号: 138****8000)"
}
```

### iconfont_search_icons

搜索图标。

- **参数**:
  - `query` (必填): 搜索关键词，如 "首页"、"搜索"、"用户"
  - `icon_type` (可选): 图标风格 — `""`(全部), `"line"`(线性), `"fill"`(填充), `"flat"`(扁平), `"hand"`(手绘), `"simple"`(简约), `"complex"`(复杂)
  - `page` (可选): 页码，默认 1
  - `page_size` (可选): 每页数量 1-100，默认 20
- **返回示例**:

```json
{
  "total": 156,
  "page": 1,
  "page_size": 20,
  "icons": [
    {
      "id": "145442",
      "name": "用户",
      "preview_url": "https://...",
      "author": "设计师A",
      "width": 1024,
      "height": 1024
    }
  ]
}
```

### iconfont_download_icon

下载图标 SVG 文件。

- **参数**:
  - `icon_id` (必填): 图标 ID，从搜索结果的 `id` 字段获取
  - `output_dir` (可选): 保存目录，默认 `"./icons"`
  - `filename` (可选): 自定义文件名 (不含 `.svg`)，默认使用图标名
- **返回示例**:

```json
{
  "icon_id": "145442",
  "name": "用户",
  "file_path": ".\\icons\\用户.svg",
  "svg_size": 2048
}
```

### iconfont_check_status

检查登录状态。

- **参数**: 无
- **返回示例**:

```json
{
  "logged_in": true,
  "username": "13800138000",
  "login_time": 1752723000.0
}
```

### iconfont_logout

退出登录，清除 Cookie。

- **参数**: 无
- **返回示例**:

```json
{
  "success": true,
  "message": "已退出登录"
}
```

---

## HTML 原型使用指南

### 典型工作流

```
需求 → 搜索图标 → 选择图标 → 下载SVG → 嵌入HTML
```

### 对话示例

**示例 1: 制作带图标的侧边栏**

> **你**: 帮我做一个后台管理系统的侧边栏，包含首页、用户管理、订单管理、数据统计、系统设置五个菜单项，每个前面要有图标。
>
> **AI**:
> 1. 调用 `iconfont_search_icons(query="首页", icon_type="fill")`
> 2. 调用 `iconfont_search_icons(query="用户", icon_type="fill")`
> 3. ... (并行搜索)
> 4. 选择合适图标，调用 `iconfont_download_icon` 下载
> 5. 读取 SVG 文件内容，嵌入 HTML
> 6. 输出完整原型

**示例 2: 给现有页面添加表格操作图标**

> **你**: 我这个表格每行的操作列需要编辑、删除、查看三个图标按钮。
>
> **AI**:
> 1. 搜索 "编辑"、"删除"、"查看" 图标
> 2. 下载并内联到 HTML 的 `<td class="actions">` 中

### SVG 嵌入方式

**方式 A — 内联 SVG (推荐)**

能通过 CSS 控制图标颜色和大小:

```html
<button class="btn-icon" title="编辑">
  <svg viewBox="0 0 1024 1024" width="20" height="20" fill="currentColor">
    <path d="...下载的SVG路径..."/>
  </svg>
  <span>编辑</span>
</button>

<style>
.btn-icon {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #666;
  cursor: pointer;
}
.btn-icon:hover { color: #4A90D9; }
</style>
```

**方式 B — 外部引用**

```html
<img src="icons/编辑.svg" alt="编辑" width="20" height="20">
```

---

## 常见问题

### Q: 登录时报错 "检测到验证码"

A: iconfont.cn 在检测到异常登录时会弹出滑块或图片验证码，Playwright 无法自动处理。请改用 Cookie 注入方式:
1. 手动访问 iconfont.cn 完成登录 (包括验证码)
2. 获取 `EGG_SESS_ICONFONT` Cookie
3. 在 MCP 配置中设置 `ICONFONT_COOKIE` 环境变量

### Q: Cookie 有效期多久？

A: 约 1 年。过期后需要重新获取 Cookie 或重新调用 `iconfont_login`。

### Q: 下载的 SVG 图标如何调整颜色？

A: 使用内联 SVG 方式，图标颜色由 CSS `fill` 控制。下载的 SVG 通常带有 `fill="currentColor"` 属性（如果原始图标有此属性），可通过父元素的 `color` 来控制。

### Q: 搜索返回 401 或 "未登录" 错误

A: Cookie 已过期，请调用 `iconfont_login` 重新登录。

### Q: 如何搜索英文图标？

A: iconfont.cn 主要使用中文关键词，建议用英文对应的中文翻译搜索，如搜索 "home" 用 "首页"。

---

## 故障排查

### 问题: `playwright` 导入失败

```bash
pip install playwright
playwright install chromium
```

### 问题: MCP 服务启动后无响应

检查 Python 版本和依赖:

```bash
python --version  # 需要 >= 3.10
pip list | grep mcp
```

### 问题: 搜索返回空结果

1. 确认已登录: 先调用 `iconfont_check_status`
2. 尝试更简短的关键词，如 "用户" 而非 "用户图标按钮"
3. 尝试近义词，如 "主页" → "首页"

### 问题: Windows 路径报错

在 `.cursor/mcp.json` 中使用正斜杠:

```json
"cwd": "D:/工作文件/mcp_project/search-iconfont"
```

---

## License

MIT
