"""日志配置。"""
import logging
import sys
from datetime import datetime
from pathlib import Path

from app.config import STORAGE_DIR

LOG_DIR = STORAGE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_logger(name: str = "douyin_hot") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler(LOG_DIR / f"app_{datetime.now():%Y%m%d}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger
