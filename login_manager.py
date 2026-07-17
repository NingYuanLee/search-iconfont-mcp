# -*- coding: utf-8 -*-
"""
iconfont.cn 登录管理器
使用 Playwright 浏览器自动化完成登录，管理 EGG_SESS_ICONFONT Cookie。
"""

import os
import time
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

# 模块级 Cookie 存储 (进程生命周期)
_cookie: Optional[str] = None
_username: Optional[str] = None
_login_time: Optional[float] = None


def get_cookie() -> Optional[str]:
    """获取当前存储的 Cookie。"""
    return _cookie


def set_cookie(cookie: str, username: str = "") -> None:
    """设置 Cookie 和登录信息。"""
    global _cookie, _username, _login_time
    _cookie = cookie
    _username = username
    _login_time = time.time()


def clear_cookie() -> None:
    """清除 Cookie 和登录信息。"""
    global _cookie, _username, _login_time
    _cookie = None
    _username = None
    _login_time = None


def is_logged_in() -> bool:
    """检查是否已登录 (Cookie 是否存在)。"""
    return _cookie is not None


def get_login_info() -> dict:
    """获取当前登录状态信息。"""
    return {
        "logged_in": _cookie is not None,
        "username": _username,
        "login_time": _login_time,
    }


def extract_cookie_from_page(cookies: list) -> Optional[str]:
    """从浏览器 cookies 列表中提取 EGG_SESS_ICONFONT。"""
    for c in cookies:
        if c.get("name") == "EGG_SESS_ICONFONT":
            return c.get("value")
    return None


async def login_with_playwright(phone: str, password: str) -> dict:
    """
    使用 Playwright 无头浏览器自动登录 iconfont.cn。

    处理完整登录流程: 填充表单 → 勾选隐私协议 → 提交登录 → 提取 Cookie

    Args:
        phone: 手机号
        password: 密码

    Returns:
        dict: {success, message, cookie?, need_manual?}
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "success": False,
            "message": "playwright 未安装，请运行: pip install playwright && python -m playwright install chromium",
        }

    phone = phone.strip()
    password = password.strip()

    if not phone or not password:
        return {
            "success": False,
            "message": "手机号或密码为空，请检查环境变量 ICONFONT_PHONE 和 ICONFONT_PASSWORD",
        }

    logger.info("启动无头浏览器...")
    browser = None

    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        logger.info("打开 iconfont.cn 登录页...")
        await page.goto("https://www.iconfont.cn/login", wait_until="networkidle", timeout=30000)

        # 等待表单加载
        await page.wait_for_selector("#userid", timeout=10000)
        await page.wait_for_selector("#password", timeout=10000)

        # 填充账号密码
        await page.fill("#userid", phone)
        logger.info("已填充手机号")
        await page.click("#password")
        await page.fill("#password", password)
        logger.info("已填充密码")

        # 勾选隐私协议 (iconfont 登录时会弹出协议勾选框)
        # 先检查复选框是否可见，如果不可见则先点一次登录触发它
        checkbox = await page.query_selector("#register-agreement")
        if checkbox:
            is_visible = await checkbox.is_visible()
            if not is_visible:
                # 协议框可能被隐藏，需要先点登录触发
                logger.info("点击登录按钮以触发协议勾选...")
                await page.click(".mx-btn-submit")
                await page.wait_for_timeout(1500)

            # 勾选协议
            await page.check("#register-agreement")
            logger.info("已勾选隐私协议")
        else:
            logger.info("未找到协议勾选框，可能不需要")

        # 检查验证码
        captcha_el = await page.query_selector(".nc_wrapper, .captcha, .geetest_panel, .verify-code, .slider, #nc_1_wrapper")
        if captcha_el:
            is_visible = await captcha_el.is_visible()
            if is_visible:
                await browser.close()
                return {
                    "success": False,
                    "need_manual": True,
                    "message": (
                        "iconfont.cn 登录出现滑块验证码，无法自动完成。\n"
                        "请在 MCP 配置中设置 ICONFONT_COOKIE 环境变量代替:\n"
                        "1. 浏览器访问 https://www.iconfont.cn/ 并登录\n"
                        "2. 按 F12 → Application → Cookies\n"
                        "3. 复制 EGG_SESS_ICONFONT 的值"
                    ),
                }

        # 提交登录
        await page.click(".mx-btn-submit")
        logger.info("已点击登录按钮")

        # 轮询等待 Cookie (最多30秒)
        cookie_value = None
        for i in range(30):
            await asyncio.sleep(1)
            cookies = await context.cookies()
            cookie_value = extract_cookie_from_page(cookies)
            if cookie_value:
                logger.info(f"Cookie 获取成功 (等待 {i + 1}s)")
                break

        if cookie_value:
            set_cookie(cookie_value, username=phone)
            await browser.close()
            return {
                "success": True,
                "message": "登录成功",
            }

        # 检查错误信息
        await page.wait_for_timeout(2000)
        error_el = await page.query_selector(".error-msg, .mx-form-item-error, .login-error, #register-agreement-error")
        if error_el:
            try:
                error_text = await error_el.inner_text()
            except Exception:
                error_text = "未知错误"

            await browser.close()
            return {
                "success": False,
                "message": f"登录失败: {error_text}",
            }

        await browser.close()
        return {
            "success": False,
            "message": "登录后未获取到 Cookie，请检查账号密码是否正确，或改用 ICONFONT_COOKIE 方式",
        }

    except Exception as e:
        logger.error(f"登录异常: {e}")
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        return {
            "success": False,
            "message": f"登录异常: {str(e)}",
        }
