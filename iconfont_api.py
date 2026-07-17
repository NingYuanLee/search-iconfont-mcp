# -*- coding: utf-8 -*-
"""
iconfont.cn API 封装
提供图标搜索、SVG 下载功能。

注意: iconfont.cn 的 /api/icon/detail.json 端点返回 HTML 而非 JSON,
因此 SVG 数据直接从搜索 API 的 show_svg 字段获取。
"""

import os
import re
import time
import logging
from typing import Optional

import httpx

from login_manager import get_cookie, is_logged_in

logger = logging.getLogger(__name__)

BASE_URL = "https://www.iconfont.cn"
SEARCH_API = f"{BASE_URL}/api/icon/search.json"

# 合法的 icon_type 值
VALID_ICON_TYPES = {"", "line", "fill", "flat", "hand", "simple", "complex"}

# 默认请求头
_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
    "Referer": "https://www.iconfont.cn/",
}

# 搜索缓存: {icon_id: {id, name, show_svg, ...}}
# 搜索时自动缓存，下载时直接命中，避免重复请求
_search_cache: dict = {}


def _safe_filename(name: str) -> str:
    """将图标名转为安全的文件名 (保留中文)。"""
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name.strip()


async def search_icons(
    query: str,
    icon_type: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    搜索 iconfont.cn 图标库。

    Args:
        query: 搜索关键词
        icon_type: 图标风格 (空=全部, line=线性, fill=填充, flat=扁平, hand=手绘, simple=简约, complex=复杂)
        page: 页码 (从1开始)
        page_size: 每页数量 (最大100)

    Returns:
        dict: {total, page, page_size, icons: [{id, name, preview_url, author, width, height, show_svg}]}
    """
    if not is_logged_in():
        raise RuntimeError("未登录，请先调用 iconfont_login 工具进行登录")

    if icon_type not in VALID_ICON_TYPES:
        raise ValueError(f"无效的 icon_type '{icon_type}'，可选值: {', '.join(v or '空' for v in VALID_ICON_TYPES)}")

    page_size = min(max(1, page_size), 100)
    page = max(1, page)

    cookie = get_cookie()
    headers = {**_HEADERS, "Cookie": f"EGG_SESS_ICONFONT={cookie}"}

    body = {
        "q": query,
        "page": str(page),
        "pageSize": str(page_size),
        "sortType": "updated_at",
        "t": str(int(time.time() * 1000)),
    }
    if icon_type:
        body["icon_type"] = icon_type

    logger.info(f"搜索图标: query='{query}', type='{icon_type}', page={page}, pageSize={page_size}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(SEARCH_API, headers=headers, data=body)
        resp.raise_for_status()
        data = resp.json()

    if data.get("code") != 200:
        error_msg = data.get("message", "搜索API返回错误")
        if any(kw in str(error_msg).lower() for kw in ["未登录", "cookie", "未登入"]):
            raise RuntimeError("登录已过期，请重新调用 iconfont_login 登录")
        raise RuntimeError(f"搜索失败: {error_msg}")

    raw_icons = data.get("data", {}).get("icons", [])
    icons = []
    for icon in raw_icons:
        icons.append({
            "id": str(icon.get("id", "")),
            "name": icon.get("name", ""),
            "preview_url": icon.get("url") or icon.get("preview_url", ""),
            "author": icon.get("author_name") or icon.get("author", ""),
            "width": icon.get("width", 0),
            "height": icon.get("height", 0),
            "show_svg": icon.get("show_svg", ""),
        })

    total = data.get("data", {}).get("total", len(icons))

    # 缓存搜索结果，供 download_icon 直接用
    for item in icons:
        if item["show_svg"]:
            _search_cache[item["id"]] = item

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "icons": icons,
    }


async def download_icon(
    icon_id: str,
    output_dir: str = "./icons",
    filename: Optional[str] = None,
) -> dict:
    """
    下载图标 SVG 文件到本地。

    通过搜索 API 获取图标的完整 SVG 数据并保存。

    Args:
        icon_id: 图标ID (从搜索结果的 id 字段获取)
        output_dir: 输出目录 (默认 ./icons)
        filename: 自定义文件名 (不含扩展名，默认使用图标名)

    Returns:
        dict: {icon_id, name, file_path, svg_size}
    """
    if not is_logged_in():
        raise RuntimeError("未登录，请先调用 iconfont_login 工具进行登录")

    # 优先从缓存获取 (search_icons 时自动缓存)
    cached = _search_cache.get(str(icon_id))
    if cached and cached.get("show_svg"):
        logger.info(f"下载图标 (缓存命中): icon_id={icon_id}, name={cached['name']}")
        show_svg = cached["show_svg"]
        icon_name = cached.get("name", icon_id)
    else:
        # 缓存未命中，通过搜索 API 查找
        cookie = get_cookie()
        headers = {**_HEADERS, "Cookie": f"EGG_SESS_ICONFONT={cookie}"}

        logger.info(f"下载图标 (缓存未命中，搜索寻找): icon_id={icon_id}")

        body = {
            "q": str(icon_id),
            "page": "1",
            "pageSize": "50",
            "sortType": "updated_at",
            "t": str(int(time.time() * 1000)),
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(SEARCH_API, headers=headers, data=body)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != 200:
            raise RuntimeError(f"搜索图标失败: {data.get('message', '未知错误')}")

        raw_icons = data.get("data", {}).get("icons", [])
        target_icon = None
        for icon in raw_icons:
            if str(icon.get("id", "")) == str(icon_id):
                target_icon = icon
                break

        if not target_icon:
            raise RuntimeError(f"未找到图标 (id={icon_id})，请先调用 iconfont_search_icons 搜索后再下载")

        show_svg = target_icon.get("show_svg", "")
        icon_name = target_icon.get("name", icon_id)

        # 也缓存起来
        if show_svg:
            _search_cache[str(icon_id)] = {
                "id": str(target_icon.get("id", "")),
                "name": icon_name,
                "show_svg": show_svg,
            }

    if not show_svg:
        raise RuntimeError(f"图标 {icon_id} 无 SVG 数据")

    safe_name = filename or _safe_filename(icon_name)

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    file_path = os.path.join(output_dir, f"{safe_name}.svg")

    # 如果文件已存在，追加数字后缀
    counter = 1
    while os.path.exists(file_path):
        file_path = os.path.join(output_dir, f"{safe_name}_{counter}.svg")
        counter += 1

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(show_svg)

    svg_size = len(show_svg.encode("utf-8"))

    logger.info(f"图标已下载: {file_path} ({svg_size} bytes)")

    return {
        "icon_id": icon_id,
        "name": icon_name,
        "file_path": file_path,
        "svg_size": svg_size,
    }
