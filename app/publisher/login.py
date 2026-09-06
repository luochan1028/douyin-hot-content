"""抖音登录模块：支持本地有界面和云服务器 headless 两种模式。"""
import asyncio
import json
from pathlib import Path
from typing import Optional

from app.config import STORAGE_DIR
from app.logger import get_logger

logger = get_logger("publisher.login")

COOKIE_DIR = STORAGE_DIR / "cookies"
COOKIE_DIR.mkdir(parents=True, exist_ok=True)
COOKIE_FILE = COOKIE_DIR / "douyin_cookies.json"
QR_SCREENSHOT = STORAGE_DIR / "douyin_qr.png"

CREATOR_URL = "https://creator.douyin.com/"


def has_cookies() -> bool:
    """检查是否已有登录 Cookie。"""
    return COOKIE_FILE.exists()


def clear_cookies():
    """清除登录 Cookie（重新登录时调用）。"""
    if COOKIE_FILE.exists():
        COOKIE_FILE.unlink()
        logger.info("已清除登录 Cookie")


def import_cookies(cookie_input: str) -> dict:
    """
    导入用户从浏览器复制的 Cookie，保存为 Playwright 格式。

    支持两种格式：
    1. JSON 数组格式: [{"name":"sessionid","value":"xxx","domain":".douyin.com",...}, ...]
    2. 字符串格式:   "sessionid=xxx; ttwid=yyy; msToken=zzz"

    Returns: {success, message, count}
    """
    cookie_input = cookie_input.strip()
    if not cookie_input:
        return {"success": False, "message": "Cookie 内容为空", "count": 0}

    cookies = []

    # 尝试解析为 JSON 数组
    if cookie_input.startswith("["):
        try:
            cookies = json.loads(cookie_input)
            if not isinstance(cookies, list):
                return {"success": False, "message": "JSON 格式必须是数组", "count": 0}
            # 校验每个 cookie 至少有 name 和 value
            for c in cookies:
                if "name" not in c or "value" not in c:
                    return {"success": False, "message": "每个 Cookie 必须包含 name 和 value 字段", "count": 0}
                # 补齐必要字段
                c.setdefault("domain", ".douyin.com")
                c.setdefault("path", "/")
        except json.JSONDecodeError as e:
            return {"success": False, "message": f"JSON 解析失败: {e}", "count": 0}
    else:
        # 字符串格式: name1=value1; name2=value2
        for part in cookie_input.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            name, _, value = part.partition("=")
            name = name.strip()
            value = value.strip()
            if name:
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": ".douyin.com",
                    "path": "/",
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Lax",
                })

    if not cookies:
        return {"success": False, "message": "未解析到任何有效 Cookie", "count": 0}

    COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("已导入 %d 个 Cookie 到 %s", len(cookies), COOKIE_FILE)

    # 检查是否有关键的 sessionid
    has_session = any(c["name"] == "sessionid" for c in cookies)
    msg = f"成功导入 {len(cookies)} 个 Cookie"
    if not has_session:
        msg += "（警告：未检测到 sessionid，可能无法正常登录）"
    return {"success": True, "message": msg, "count": len(cookies)}


async def save_cookies(context):
    cookies = await context.cookies()
    COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False), encoding="utf-8")
    logger.info("Cookie 已保存: %s", COOKIE_FILE)


async def load_cookies(context) -> bool:
    if COOKIE_FILE.exists():
        try:
            cookies = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
            await context.add_cookies(cookies)
            return True
        except Exception as e:
            logger.warning("Cookie 加载失败: %s", e)
    return False


async def login(headless: Optional[bool] = None, timeout: int = 300) -> dict:
    """
    登录抖音创作者中心。

    Args:
        headless: 是否无头模式。None=自动（有显示用 False，无显示用 True）
        timeout: 等待登录的最大秒数

    Returns:
        {success, message, qr_screenshot}
    """
    import os
    from playwright.async_api import async_playwright

    # 自动判断 headless：Linux 无 DISPLAY 则 headless
    if headless is None:
        headless = not (os.name == "nt" or os.environ.get("DISPLAY"))

    logger.info("启动浏览器登录 (headless=%s)...", headless)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        try:
            await page.goto(CREATOR_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            # 截图保存二维码（供云服务器用户查看）
            await page.screenshot(path=str(QR_SCREENSHOT), full_page=False)
            logger.info("登录页截图已保存: %s", QR_SCREENSHOT)

            # 轮询等待用户扫码登录（最多 timeout 秒）
            logger.info("请在浏览器中扫码登录，等待中（最多 %d 秒）...", timeout)
            for i in range(timeout):
                await asyncio.sleep(1)
                # 检测是否已登录：URL 是否跳转到创作者中心且不含 login
                if "creator.douyin.com" in page.url and "login" not in page.url.lower():
                    # 检测登录后特征元素
                    try:
                        logged_in = await page.locator('text=内容管理, text=数据中心, a[href*="creator-micro"]').count()
                        if logged_in > 0 or i > 5:
                            break
                    except Exception:
                        pass
            await page.wait_for_timeout(2000)

            await save_cookies(context)
            return {"success": True, "message": "登录成功，Cookie 已保存", "qr_screenshot": str(QR_SCREENSHOT)}

        except Exception as e:
            logger.error("登录失败: %s", e)
            return {"success": False, "message": f"登录失败: {e}", "qr_screenshot": ""}
        finally:
            await browser.close()


async def check_login_status() -> dict:
    """检查当前 Cookie 是否仍然有效（是否已登录）。"""
    from playwright.async_api import async_playwright

    if not has_cookies():
        return {"logged_in": False, "message": "未登录，无 Cookie"}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await load_cookies(context)
        page = await context.new_page()
        try:
            await page.goto(CREATOR_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            url = page.url
            # 登录成功不会跳转到 login 页面
            if "login" in url.lower():
                return {"logged_in": False, "message": "Cookie 已过期，请重新登录"}
            # 检查登录后特征元素
            try:
                content_el = await page.locator('text=内容管理').count()
                if content_el > 0:
                    return {"logged_in": True, "message": "已登录"}
            except Exception:
                pass
            return {"logged_in": True, "message": "疑似已登录（未检测到登录页）"}
        except Exception as e:
            return {"logged_in": False, "message": f"检查失败: {e}"}
        finally:
            await browser.close()
