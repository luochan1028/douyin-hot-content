"""健康检查：检测各组件可用性。"""
import shutil
import subprocess
from datetime import datetime

from app.config import settings
from app.database import engine
from app.logger import get_logger

logger = get_logger("notify.health")


def _check_db() -> tuple:
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as e:
        return False, str(e)[:200]


def _check_ffmpeg() -> tuple:
    ffmpeg = shutil.which(settings.FFMPEG_PATH) or settings.FFMPEG_PATH
    try:
        r = subprocess.run([ffmpeg, "-version"], capture_output=True, timeout=10)
        return r.returncode == 0, "ok" if r.returncode == 0 else r.stderr.decode()[:100]
    except Exception as e:
        return False, str(e)[:200]


def _check_playwright() -> tuple:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True, "ok"
    except Exception as e:
        return False, str(e)[:200]


def _check_network() -> tuple:
    import socket
    try:
        socket.create_connection(("www.baidu.com", 80), timeout=5)
        return True, "ok"
    except Exception as e:
        return False, str(e)[:200]


def run_health_check() -> dict:
    checks = {
        "database": _check_db(),
        "ffmpeg": _check_ffmpeg(),
        "playwright": _check_playwright(),
        "network": _check_network(),
    }
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy" if all(c[0] for c in checks.values()) else "degraded",
        "components": {k: {"ok": v[0], "detail": v[1]} for k, v in checks.items()},
    }
    logger.info("健康检查: %s", result["status"])
    if result["status"] == "degraded":
        from app.notify.notifier import notify
        failed = [k for k, v in checks.items() if not v[0]]
        notify("系统异常告警", f"以下组件异常: {', '.join(failed)}")
    return result
