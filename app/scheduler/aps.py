"""定时调度器：APScheduler 周期性执行流水线。"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.logger import get_logger
from app.scheduler.orchestrator import run_full_pipeline

logger = get_logger("scheduler.aps")

_scheduler: BackgroundScheduler = None


def _is_peak() -> bool:
    from datetime import datetime
    return datetime.now().hour in settings.PEAK_HOURS


def _job():
    import asyncio
    try:
        asyncio.run(run_full_pipeline())
    except Exception as e:
        logger.error("调度任务异常: %s", e)


def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler()
    # 动态频率：高峰期 5 分钟，低峰期 30 分钟
    interval = settings.CRAWL_PEAK_INTERVAL if _is_peak() else settings.CRAWL_OFFPEAK_INTERVAL
    _scheduler.add_job(_job, IntervalTrigger(minutes=interval), id="pipeline", replace_existing=True)
    _scheduler.start()
    logger.info("调度器已启动，间隔 %d 分钟", interval)


def stop_scheduler():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("调度器已停止")
