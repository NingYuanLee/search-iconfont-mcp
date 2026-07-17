# -*- coding: utf-8 -*-
"""
Iconfont MCP Server
提供从 iconfont.cn 搜索和下载 SVG 图标的能力，用于 AI 生成 HTML 原型。
"""

import os
import json
import logging

from mcp.server.fastmcp import FastMCP

from login_manager import (
    is_logged_in,
    get_login_info,
    clear_cookie,
    login_with_playwright,
)
from iconfont_api import search_icons, download_icon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP("iconfont-mcp-server")


@mcp.tool(
    name="iconfont_login",
    annotations={
        "title": "登录 iconfont.cn",
        "readOnlyHint": False,
        "openWorldHint": True,
    },
)
async def iconfont_login() -> str:
    """登录 iconfont.cn 图标库。

    使用 MCP 配置中的环境变量 ICONFONT_PHONE 和 ICONFONT_PASSWORD 进行自动登录。
    如果遇到验证码，会提示用户手动操作。

    若已登录，返回当前登录状态。

    Returns:
        str: JSON 格式的登录结果
            - success: 是否成功
            - message: 提示信息
            - need_manual: 是否需要手动处理 (验证码情况)
    """
    if is_logged_in():
        info = get_login_info()
        return json.dumps({
            "success": True,
            "message": f"已登录 (账号: {info.get('username', 'unknown')})",
            "already_logged_in": True,
        }, ensure_ascii=False)

    phone = os.environ.get("ICONFONT_PHONE", "").strip()
    password = os.environ.get("ICONFONT_PASSWORD", "").strip()

    # 检查是否配置了直接 Cookie (跳过自动登录)
    direct_cookie = os.environ.get("ICONFONT_COOKIE", "").strip()
    if direct_cookie:
        from login_manager import set_cookie
        set_cookie(direct_cookie, username="cookie-user")
        logger.info("使用直接配置的 ICONFONT_COOKIE")
        return json.dumps({
            "success": True,
            "message": "已通过 ICONFONT_COOKIE 环境变量登录",
            "method": "direct_cookie",
        }, ensure_ascii=False)

    if not phone or not password:
        return json.dumps({
            "success": False,
            "message": (
                "未配置登录凭据。请在 MCP 配置中设置环境变量:\n"
                "  ICONFONT_PHONE=你的手机号\n"
                "  ICONFONT_PASSWORD=你的密码\n\n"
                "或者手动获取 Cookie 后设置:\n"
                "  ICONFONT_COOKIE=你的EGG_SESS_ICONFONT值\n\n"
                "获取 Cookie 方法:\n"
                "1. 浏览器访问 https://www.iconfont.cn/ 并登录\n"
                "2. 按 F12 → Application → Cookies\n"
                "3. 复制 EGG_SESS_ICONFONT 的值"
            ),
        }, ensure_ascii=False)

    logger.info(f"开始自动登录: {phone}")
    result = await login_with_playwright(phone, password)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool(
    name="iconfont_search_icons",
    annotations={
        "title": "搜索 iconfont.cn 图标",
        "readOnlyHint": True,
        "openWorldHint": True,
    },
)
async def iconfont_search_icons(
    query: str,
    icon_type: str = "",
    page: int = 1,
    page_size: int = 20,
) -> str:
    """在 iconfont.cn 搜索图标。

    根据关键词搜索图标库，返回图标列表 (含ID、名称、预览图)。需要先登录。

    Args:
        query: 搜索关键词 (如 "首页"、"搜索"、"用户")
        icon_type: 图标风格过滤。空字符串=全部, "line"=线性, "fill"=填充, "flat"=扁平, "hand"=手绘, "simple"=简约, "complex"=复杂
        page: 页码 (从1开始)
        page_size: 每页数量 (1-100, 默认20)

    Returns:
        str: JSON 格式搜索结果，包含 total(总数), page, page_size, icons 列表。
             icons 中每项含 id(图标ID), name(名称), preview_url(预览图), author(作者), width, height
    """
    try:
        result = await search_icons(
            query=query,
            icon_type=icon_type if icon_type in {"", "line", "fill", "flat", "hand", "simple", "complex"} else "",
            page=page,
            page_size=page_size,
        )
        return json.dumps(result, ensure_ascii=False)
    except RuntimeError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        logger.exception("搜索图标异常")
        return json.dumps({"error": f"搜索异常: {str(e)}"}, ensure_ascii=False)


@mcp.tool(
    name="iconfont_download_icon",
    annotations={
        "title": "下载 iconfont.cn 图标 SVG",
        "readOnlyHint": False,
        "openWorldHint": True,
    },
)
async def iconfont_download_icon(
    icon_id: str,
    output_dir: str = "./icons",
    filename: str = "",
) -> str:
    """下载指定图标的 SVG 文件到本地。

    根据 icon_id 下载图标的完整 SVG 矢量数据并保存为 .svg 文件。
    icon_id 从 iconfont_search_icons 的搜索结果中获取。

    Args:
        icon_id: 图标ID (从搜索结果中的 id 字段获取)
        output_dir: 输出目录路径 (默认 "./icons")
        filename: 自定义文件名 (不含 .svg 扩展名，留空则使用图标名)

    Returns:
        str: JSON 格式下载结果，包含 icon_id, name(图标名), file_path(保存路径), svg_size(字节数)
    """
    try:
        result = await download_icon(
            icon_id=icon_id,
            output_dir=output_dir,
            filename=filename if filename else None,
        )
        return json.dumps(result, ensure_ascii=False)
    except RuntimeError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        logger.exception("下载图标异常")
        return json.dumps({"error": f"下载异常: {str(e)}"}, ensure_ascii=False)


@mcp.tool(
    name="iconfont_check_status",
    annotations={
        "title": "检查 iconfont.cn 登录状态",
        "readOnlyHint": True,
        "openWorldHint": False,
    },
)
async def iconfont_check_status() -> str:
    """检查当前 iconfont.cn 的登录状态。

    不需要参数，返回当前是否已登录及登录账号信息。

    Returns:
        str: JSON 格式状态信息，包含 logged_in(bool), username(str或null), login_time(时间戳)
    """
    info = get_login_info()
    return json.dumps(info, ensure_ascii=False)


@mcp.tool(
    name="iconfont_logout",
    annotations={
        "title": "退出 iconfont.cn 登录",
        "readOnlyHint": False,
        "openWorldHint": False,
    },
)
async def iconfont_logout() -> str:
    """清除当前 iconfont.cn 登录状态。

    Returns:
        str: JSON 格式结果
    """
    clear_cookie()
    return json.dumps({"success": True, "message": "已退出登录"}, ensure_ascii=False)


if __name__ == "__main__":
    logger.info("Iconfont MCP Server 启动中...")
    mcp.run()
