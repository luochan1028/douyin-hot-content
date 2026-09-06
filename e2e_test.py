"""端到端集成测试：模拟数据跑完 抓取→评估→文案→图片→视频→发布 全流程。
发布步骤使用 mock，不真实上传抖音。
"""
import asyncio
import os
import sys
from pathlib import Path

# 确保能导入 app
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.crawler.runner import run_crawl
from app.accuracy.service import run_accuracy_check
from app.heat.service import run_heat_evaluation
from app.copywriting.generator import generate_copy
from app.image.generator import generate_cover
from app.video.generator import generate_video
from app.publisher.douyin_publisher import publish_video
from app.notify.notifier import notify
from app.scheduler.orchestrator import _get_ready_hotspots
from app.logger import get_logger

logger = get_logger("e2e")


async def main():
    logger.info("========== 端到端测试开始 ==========")
    results = {}

    # 1. 抓取
    logger.info("[1/6] 热点抓取...")
    items = await run_crawl()
    assert len(items) > 0, "抓取结果为空"
    results["crawl"] = len(items)
    logger.info("  抓取 %d 条", len(items))

    # 2. 准确性校验
    logger.info("[2/6] 准确性校验...")
    acc = run_accuracy_check()
    results["approved"] = acc.get("approved", 0)
    logger.info("  通过 %d 条", results["approved"])

    # 3. 热度评估
    logger.info("[3/6] 热度评估...")
    heat = run_heat_evaluation()
    results["burst"] = heat.get("burst", 0)
    logger.info("  爆发期 %d 条", results["burst"])

    # 4-6. 取一个爆发期话题生成内容
    hotspots = _get_ready_hotspots(limit=1)
    assert hotspots, "无爆发期话题"
    hs = hotspots[0]
    tags = [t for t in (hs.tags or "").split(",") if t] or [hs.word]
    logger.info("[4/6] 文案生成: %s", hs.word)
    copy = generate_copy(hs.word, tags=tags)
    assert copy.title and copy.body and len(copy.tags) >= 3
    results["copy"] = 1
    logger.info("  文案: %s", copy.title)

    logger.info("[5/6] 图片生成...")
    img = generate_cover(copy.title, tags=copy.tags)
    assert img and img.exists()
    from PIL import Image
    assert Image.open(img).size == (1080, 1920)
    results["image"] = str(img)
    logger.info("  图片: %s", img)

    logger.info("[6/6] 视频生成...")
    video = generate_video(str(img), title=copy.title, body=copy.body, duration=15, tags=copy.tags)
    assert video and Path(video["video_path"]).exists()
    assert 15 <= video["duration"] <= 60
    assert video["width"] == 1080 and video["height"] == 1920
    assert video["has_audio"]
    results["video"] = video["video_path"]
    logger.info("  视频: %s", video["video_path"])

    # 发布（mock：不真实发布，仅验证风控与记录）
    logger.info("[发布] 风控检查（不真实发布）...")
    from app.publisher.douyin_publisher import check_risk_control
    allowed, reason = check_risk_control()
    results["publish_allowed"] = allowed
    logger.info("  发布风控: allowed=%s, reason=%s", allowed, reason)

    notify("端到端测试完成", f"全链路验证通过\n抓取 {results['crawl']} 条\n视频: {results['video']}")

    logger.info("========== 端到端测试通过 ==========")
    logger.info("结果: %s", results)
    return results


if __name__ == "__main__":
    asyncio.run(main())
