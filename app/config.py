"""应用配置：通过环境变量加载，支持 .env 文件。"""
import os
from pathlib import Path
from typing import List

# 加载 .env 文件（跨平台，本地与 Linux 云主机通用）
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage")))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class Settings:
    # 数据库
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'app.db'}")

    # 调度频率（分钟）
    CRAWL_PEAK_INTERVAL: int = int(os.getenv("CRAWL_PEAK_INTERVAL", "5"))
    CRAWL_OFFPEAK_INTERVAL: int = int(os.getenv("CRAWL_OFFPEAK_INTERVAL", "30"))
    PEAK_HOURS: List[int] = [int(h) for h in os.getenv("PEAK_HOURS", "11,12,18,19,20,21").split(",") if h.strip()]

    # 热度阈值
    HEAT_THRESHOLD: float = float(os.getenv("HEAT_THRESHOLD", "100"))
    HEAT_SCORE_BURST: float = float(os.getenv("HEAT_SCORE_BURST", "40"))

    # 可信度阈值
    CREDIBILITY_PASS: float = float(os.getenv("CREDIBILITY_PASS", "60"))
    CREDIBILITY_REVIEW: float = float(os.getenv("CREDIBILITY_REVIEW", "40"))

    # 账号定位
    ACCOUNT_CATEGORY: str = os.getenv("ACCOUNT_CATEGORY", "科技")
    ACCOUNT_TAGS: str = os.getenv("ACCOUNT_TAGS", "AI,人工智能,科技,数码,职场")
    COPYWRITING_STYLE: str = os.getenv("COPYWRITING_STYLE", "专业科普")

    # 发布风控
    DAILY_PUBLISH_LIMIT: int = int(os.getenv("DAILY_PUBLISH_LIMIT", "3"))
    PUBLISH_INTERVAL_HOURS: int = int(os.getenv("PUBLISH_INTERVAL_HOURS", "2"))
    PUBLISH_RETRY_TIMES: int = int(os.getenv("PUBLISH_RETRY_TIMES", "3"))

    # 通知渠道（留空表示不启用）
    DINGTALK_WEBHOOK: str = os.getenv("DINGTALK_WEBHOOK", "")
    WECOM_WEBHOOK: str = os.getenv("WECOM_WEBHOOK", "")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_TO: str = os.getenv("SMTP_TO", "")

    # 可插拔 AI（默认不启用，保持零成本）
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    SD_BASE_URL: str = os.getenv("SD_BASE_URL", "")

    # Web
    WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8000"))

    # Redis（可选，无则降级内存缓存）
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # FFmpeg 路径（默认从 PATH 查找）
    FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg")
    FFPROBE_PATH: str = os.getenv("FFPROBE_PATH", "ffprobe")


settings = Settings()


def account_tags() -> List[str]:
    return [t.strip() for t in settings.ACCOUNT_TAGS.split(",") if t.strip()]
