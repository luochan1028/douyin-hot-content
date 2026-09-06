"""B站热门爬虫。"""
from typing import List

from app.crawler.base import BaseCrawler, HotspotItem
from app.utils.http import async_get
from app.logger import get_logger

logger = get_logger("crawler.bilibili")

BILI_HOT_URL = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"


class BilibiliCrawler(BaseCrawler):
    source_name = "bilibili"

    async def fetch(self) -> List[HotspotItem]:
        items: List[HotspotItem] = []
        try:
            headers = {"Referer": "https://www.bilibili.com/"}
            resp = await async_get(BILI_HOT_URL, timeout=15.0, headers=headers)
            if resp.status_code != 200:
                logger.warning("B站热门接口状态码异常: %s", resp.status_code)
                return items
            data = resp.json()
            for v in data.get("data", {}).get("list", []):
                title = v.get("title", "")
                if not title:
                    continue
                heat = float(v.get("score", 0) or 0)
                bvid = v.get("bvid", "")
                url = f"https://www.bilibili.com/video/{bvid}" if bvid else ""
                items.append(HotspotItem(
                    word=title,
                    heat_value=heat,
                    rank=len(items) + 1,
                    category="娱乐",
                    source=self.source_name,
                    url=url,
                ))
        except Exception as e:
            logger.error("B站热门抓取失败: %s", e)
        logger.info("B站热门抓取到 %d 条", len(items))
        return items
