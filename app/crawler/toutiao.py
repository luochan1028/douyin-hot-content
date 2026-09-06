"""今日头条热榜爬虫（免费公开接口）。"""
from typing import List

from app.crawler.base import BaseCrawler, HotspotItem
from app.utils.http import async_get
from app.logger import get_logger

logger = get_logger("crawler.toutiao")

TOUTIAO_HOT_URL = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"


class ToutiaoCrawler(BaseCrawler):
    source_name = "toutiao"

    async def fetch(self) -> List[HotspotItem]:
        items: List[HotspotItem] = []
        try:
            headers = {"Referer": "https://www.toutiao.com/"}
            resp = await async_get(TOUTIAO_HOT_URL, timeout=15.0, headers=headers)
            if resp.status_code != 200:
                logger.warning("头条热榜接口状态码异常: %s", resp.status_code)
                return items
            data = resp.json()
            for v in data.get("data", []):
                title = v.get("Title", "")
                if not title:
                    continue
                heat = float(v.get("HotValue", 0) or 0)
                cat = v.get("InterestCategory", "") or "综合"
                if isinstance(cat, list):
                    cat = ",".join(str(c) for c in cat)
                url = v.get("Url", "")
                items.append(HotspotItem(
                    word=title,
                    heat_value=heat,
                    rank=len(items) + 1,
                    category=cat,
                    source=self.source_name,
                    url=url,
                ))
        except Exception as e:
            logger.error("头条热榜抓取失败: %s", e)
        logger.info("头条热榜抓取到 %d 条", len(items))
        return items
