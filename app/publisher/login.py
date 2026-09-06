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


def save_cookies(context):
    cookies = context.cookies()
    COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False), encoding="utf-8")
    logger.info("Cookie 已保存: %s", COOKIE_FILE)


def load_cookies(context) -> bool:
    if COOKIE_FILE.exists():
        try:
            cookies = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
            context.add_cookies(cookies)
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

            if headless:
                # 云服务器：轮询等待用户扫码登录（最多 timeout 秒）
                logger.info("请用抖音 App 扫描二维码登录（截图路径: %s）", QR_SCREENSHOT)
                logger.info("等待登录中，最多 %d 秒...", timeout)
                for i in range(timeout):
                    await asyncio.sleep(1)
                    # 检测是否已登录：URL 是否跳转到创作者中心
                    if "creator.douyin.com" in page.url and "login" not in page.url.lower():
                        # 进一步检测：页面是否出现"内容管理"等登录后元素
                        try:
                            logged_in = await page.locator('text=内容管理, text=数据中心, a[href*="creator-micro"]').count()
                            if logged_in > 0 or i > 5:  # 登录后页面通常几秒内加载
                                break
                        except Exception:
                            pass
                await page.wait_for_timeout(2000)
            else:
                # 本地：提示用户手动登录
                logger.info("请在弹出的浏览器中扫码登录...")
                input("登录完成后按回车继续...")

            save_cookies(context)
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
        load_cookies(context)
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
