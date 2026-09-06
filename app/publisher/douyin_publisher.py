"""抖音发布模块：Playwright 浏览器自动化（零成本，无需企业号 API）。"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.config import settings, STORAGE_DIR
from app.database import SessionLocal
from app.models import PublishRecord
from app.utils.sensitive import contains_sensitive
from app.logger import get_logger

logger = get_logger("publisher.douyin")

COOKIE_DIR = STORAGE_DIR / "cookies"
COOKIE_DIR.mkdir(parents=True, exist_ok=True)
COOKIE_FILE = COOKIE_DIR / "douyin_cookies.json"

CREATOR_URL = "https://creator.douyin.com/creator-micro/content/upload"


async def _save_cookies(context):
    cookies = await context.cookies()
    COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False), encoding="utf-8")
    logger.info("Cookie 已保存: %s", COOKIE_FILE)


async def _load_cookies(context):
    if COOKIE_FILE.exists():
        try:
            cookies = json.loads(COOKIE_FILE.read_text(encoding="utf-8"))
            await context.add_cookies(cookies)
            return True
        except Exception:
            pass
    return False


def _is_headless() -> bool:
    """判断是否使用无头模式：环境变量 HEADLESS 优先，否则自动检测。"""
    h = os.getenv("HEADLESS", "")
    if h.lower() in ("1", "true", "yes"):
        return True
    if h.lower() in ("0", "false", "no"):
        return False
    # 自动检测：Windows 有界面用 False，Linux 无 DISPLAY 用 True
    return not (os.name == "nt" or os.environ.get("DISPLAY"))


def _today_publish_count() -> int:
    db = SessionLocal()
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            db.query(PublishRecord)
            .filter(PublishRecord.status == "success", PublishRecord.created_at >= today_start)
            .count()
        )
    finally:
        db.close()


def _last_publish_time() -> Optional[datetime]:
    db = SessionLocal()
    try:
        rec = (
            db.query(PublishRecord)
            .filter(PublishRecord.status == "success")
            .order_by(PublishRecord.created_at.desc())
            .first()
        )
        return rec.created_at if rec else None
    finally:
        db.close()


def check_risk_control() -> tuple:
    """
    发布风控检查。
    返回 (allowed: bool, reason: str)
    """
    # 日发布上限
    if _today_publish_count() >= settings.DAILY_PUBLISH_LIMIT:
        return False, f"今日发布已达上限 {settings.DAILY_PUBLISH_LIMIT} 条"
    # 发布间隔
    last = _last_publish_time()
    if last:
        elapsed = (datetime.utcnow() - last).total_seconds() / 3600
        if elapsed < settings.PUBLISH_INTERVAL_HOURS:
            return False, f"距上次发布不足 {settings.PUBLISH_INTERVAL_HOURS} 小时"
    return True, "ok"


def _record_publish(word: str, media_path: str, copy_content: str, tags: str,
                    status: str, error: str = "") -> int:
    db = SessionLocal()
    try:
        rec = PublishRecord(
            hotspot_word=word,
            copy_content=copy_content,
            tags=tags,
            status=status,
            error_msg=error,
            publish_time=datetime.utcnow() if status == "success" else None,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec.id
    except Exception as e:
        db.rollback()
        logger.error("发布记录写入失败: %s", e)
        return -1
    finally:
        db.close()


async def publish_video(video_path: str, title: str, desc: str, tags: list,
                        word: str = "", scheduled_time: Optional[datetime] = None) -> dict:
    """
    发布视频到抖音创作者中心。
    返回 {success, record_id, error}
    """
    copy_content = f"{title}\n{desc}"
    full_tags = ",".join(tags)

    # 发布前二次敏感词校验
    if contains_sensitive(copy_content) or any(contains_sensitive(t) for t in tags):
        rid = _record_publish(word, video_path, copy_content, full_tags, "failed", "发布前敏感词校验未通过")
        return {"success": False, "record_id": rid, "error": "敏感词校验未通过"}

    # 风控检查
    allowed, reason = check_risk_control()
    if not allowed:
        rid = _record_publish(word, video_path, copy_content, full_tags, "failed", reason)
        return {"success": False, "record_id": rid, "error": reason}

    # 失败重试
    last_error = ""
    for attempt in range(1, settings.PUBLISH_RETRY_TIMES + 1):
        try:
            result = await _do_publish(video_path, title, desc, tags, scheduled_time)
            if result["success"]:
                rid = _record_publish(word, video_path, copy_content, full_tags, "success")
                logger.info("发布成功（第 %d 次尝试）", attempt)
                return {"success": True, "record_id": rid, "error": ""}
            last_error = result.get("error", "未知错误")
        except Exception as e:
            last_error = str(e)
        logger.warning("发布失败（第 %d 次）: %s", attempt, last_error)
        await asyncio.sleep(attempt * 5)  # 间隔递增

    rid = _record_publish(word, video_path, copy_content, full_tags, "failed", last_error)
    return {"success": False, "record_id": rid, "error": last_error}


async def _do_publish(video_path: str, title: str, desc: str, tags: list,
                      scheduled_time: Optional[datetime]) -> dict:
    """实际执行浏览器自动化发布。"""
    from playwright.async_api import async_playwright

    if not COOKIE_FILE.exists():
        return {"success": False, "error": "未登录，请先执行: python -m app login"}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=_is_headless())
        context = await browser.new_context()
        if not await _load_cookies(context):
            await browser.close()
            return {"success": False, "error": "Cookie 加载失败，请重新执行: python -m app login"}

        page = await context.new_page()
        try:
            await page.goto(CREATOR_URL, wait_until="networkidle", timeout=60000)
            # 上传视频
            upload_input = page.locator('input[type="file"]')
            await upload_input.set_input_files(video_path)
            await page.wait_for_timeout(5000)

            # 填写标题/描述
            title_input = page.locator('textarea, input[placeholder*="标题"], div[contenteditable="true"]').first
            await title_input.fill(f"{title}\n{desc}")

            # 填写标签
            for tag in tags[:5]:
                tag_input = page.locator('input[placeholder*="标签"], input[placeholder*="话题"]').first
                await tag_input.fill(tag)
                await page.wait_for_timeout(1000)
                await tag_input.press("Enter")

            # 定时发布或立即发布
            if scheduled_time:
                schedule_btn = page.locator('text=定时发布').first
                if await schedule_btn.count() > 0:
                    await schedule_btn.click()
            else:
                publish_btn = page.locator('button:has-text("发布"), button:has-text("发表")').first
                await publish_btn.click()

            await page.wait_for_timeout(8000)
            await _save_cookies(context)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            await browser.close()
