"""全链路任务编排器：抓取→评估→校验→文案→图片→视频→发布→通知。"""
import asyncio
from datetime import datetime
from typing import Optional

from app.crawler.runner import run_crawl
from app.accuracy.service import run_accuracy_check
from app.heat.service import run_heat_evaluation
from app.copywriting.generator import generate_copy
from app.image.generator import generate_cover
from app.video.generator import generate_video
from app.publisher.douyin_publisher import publish_video
from app.notify.notifier import notify
from app.database import SessionLocal
from app.models import Hotspot, MediaAsset
from app.config import settings
from app.logger import get_logger

logger = get_logger("scheduler.orchestrator")


def _get_ready_hotspots(limit: int = 5) -> list:
    """获取爆发期且已通过审核的热点。"""
    db = SessionLocal()
    try:
        return (
            db.query(Hotspot)
            .filter(Hotspot.lifecycle == "爆发期", Hotspot.review_status == "approved")
            .order_by(Hotspot.heat_score.desc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()


def _save_media(hotspot_id, asset_type, path, meta=""):
    db = SessionLocal()
    try:
        a = MediaAsset(hotspot_id=hotspot_id, asset_type=asset_type, local_path=path, meta=meta)
        db.add(a)
        db.commit()
        db.refresh(a)
        return a.id
    except Exception as e:
        db.rollback()
        logger.error("素材保存失败: %s", e)
        return None
    finally:
        db.close()


async def run_full_pipeline(max_topics: int = 3) -> dict:
    """
    执行一次完整生产流水线。
    每步依赖前一步成功，失败则跳过该话题。
    """
    stats = {"crawl": 0, "approved": 0, "burst": 0, "copy": 0, "image": 0, "video": 0, "publish": 0, "failed": 0}
    start = datetime.utcnow()

    # Step 1: 抓取
    logger.info("=== Step 1: 热点抓取 ===")
    try:
        items = await run_crawl()
        stats["crawl"] = len(items)
    except Exception as e:
        logger.error("抓取失败: %s", e)
        notify("流水线异常", f"热点抓取失败: {e}")
        return stats

    # Step 2: 准确性校验
    logger.info("=== Step 2: 准确性校验 ===")
    acc_stats = run_accuracy_check()
    stats["approved"] = acc_stats.get("approved", 0)

    # Step 3: 热度评估
    logger.info("=== Step 3: 热度评估 ===")
    heat_stats = run_heat_evaluation()
    stats["burst"] = heat_stats.get("burst", 0)

    # Step 4-7: 对爆发期话题逐个生产内容
    hotspots = _get_ready_hotspots(limit=max_topics)
    logger.info("=== Step 4-7: 内容生产（%d 个爆发期话题）===", len(hotspots))

    for hs in hotspots:
        try:
            # Step 4: 文案
            tags = [t for t in (hs.tags or "").split(",") if t]
            copy = generate_copy(hs.word, tags=tags or [hs.word], style=settings.COPYWRITING_STYLE)
            if copy.need_human_polish:
                logger.warning("文案需人工润色，跳过: %s", hs.word)
                continue
            stats["copy"] += 1

            # Step 5: 图片
            img_path = generate_cover(copy.title, tags=copy.tags)
            if not img_path:
                logger.error("图片生成失败: %s", hs.word)
                continue
            _save_media(hs.id, "image", str(img_path))
            stats["image"] += 1

            # Step 6: 视频
            video_info = generate_video(
                str(img_path), title=copy.title, body=copy.body,
                duration=20, tags=copy.tags,
            )
            if not video_info:
                logger.error("视频生成失败: %s", hs.word)
                continue
            _save_media(hs.id, "video", video_info["video_path"], meta=str(video_info))
            stats["video"] += 1

            # Step 7: 发布
            pub = await publish_video(
                video_info["video_path"], title=copy.title, desc=copy.body,
                tags=copy.tags, word=hs.word,
            )
            if pub["success"]:
                stats["publish"] += 1
            else:
                stats["failed"] += 1
                logger.warning("发布失败: %s - %s", hs.word, pub["error"])

        except Exception as e:
            stats["failed"] += 1
            logger.error("话题 %s 处理失败: %s", hs.word, e)

    # Step 8: 通知
    elapsed = (datetime.utcnow() - start).total_seconds()
    detail = (
        f"耗时 {elapsed:.0f}s\n"
        f"抓取 {stats['crawl']} 条 | 通过 {stats['approved']} | 爆发 {stats['burst']}\n"
        f"文案 {stats['copy']} | 图片 {stats['image']} | 视频 {stats['video']} | 发布 {stats['publish']} | 失败 {stats['failed']}"
    )
    notify("流水线执行完成", detail)
    logger.info("=== 流水线完成 ===\n%s", detail)
    return stats
