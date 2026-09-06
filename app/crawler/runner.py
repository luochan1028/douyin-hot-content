"""爬虫调度器：并发抓取所有数据源，清洗后入库。"""
import asyncio
from datetime import datetime
from typing import List

from app.crawler.base import HotspotItem
from app.crawler.weibo import WeiboCrawler
from app.crawler.baidu import BaiduCrawler
from app.crawler.zhihu import ZhihuCrawler
from app.crawler.bilibili import BilibiliCrawler
from app.crawler.douyin import DouyinCrawler
from app.crawler.toutiao import ToutiaoCrawler
from app.pipeline.cleaner import clean_items, merge_by_word
from app.database import SessionLocal
from app.models import Hotspot
from app.utils.hash import content_hash
from app.logger import get_logger

logger = get_logger("crawler.runner")

CRAWLERS = [
    WeiboCrawler(),       # 需登录 Cookie，尽力而为
    BaiduCrawler(),
    ZhihuCrawler(),       # 需登录 Cookie，尽力而为
    BilibiliCrawler(),
    DouyinCrawler(),
    ToutiaoCrawler(),
]


async def run_crawl() -> List[HotspotItem]:
    """执行一次全量抓取并入库，返回清洗后的热点列表。"""
    logger.info("开始抓取热点...")
    tasks = [c.fetch() for c in CRAWLERS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_items: List[HotspotItem] = []
    for crawler, result in zip(CRAWLERS, results):
        if isinstance(result, Exception):
            logger.error("爬虫 %s 异常: %s", crawler.source_name, result)
            continue
        all_items.extend(result)

    logger.info("共抓取原始热点 %d 条", len(all_items))

    # 清洗
    cleaned, filtered = clean_items(all_items)
    # 跨源合并
    merged = merge_by_word(cleaned)
    logger.info("清洗+合并后保留 %d 条", len(merged))

    # 入库
    saved = _save_to_db(merged)
    logger.info("入库 %d 条热点", saved)
    return merged


def _save_to_db(items: List[HotspotItem]) -> int:
    db = SessionLocal()
    saved = 0
    try:
        now = datetime.utcnow()
        for item in items:
            h = content_hash(item.word)
            existing = db.query(Hotspot).filter(Hotspot.content_hash == h).first()
            if existing:
                # 更新热度与来源计数
                existing.heat_value = max(existing.heat_value, item.heat_value)
                existing.source_count = (existing.source_count or 1) + 1
                existing.crawl_time = now
                existing.source = f"{existing.source},{item.source}" if item.source not in (existing.source or "").split(",") else existing.source
            else:
                db.add(Hotspot(
                    word=item.word,
                    heat_value=item.heat_value,
                    rank=item.rank,
                    category=item.category,
                    source=item.source,
                    url=item.url,
                    content_hash=h,
                    source_count=1,
                    crawl_time=now,
                ))
            saved += 1
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("入库失败: %s", e)
    finally:
        db.close()
    return saved
