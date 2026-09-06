"""知乎热榜爬虫。"""
from typing import List

from app.crawler.base import BaseCrawler, HotspotItem
from app.utils.http import async_get
from app.logger import get_logger

logger = get_logger("crawler.zhihu")

ZHIHU_HOT_URL = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50"


class ZhihuCrawler(BaseCrawler):
    source_name = "zhihu"

    async def fetch(self) -> List[HotspotItem]:
        items: List[HotspotItem] = []
        try:
            headers = {
                "Referer": "https://www.zhihu.com/hot",
                "x-requested-with": "fetch",
            }
            resp = await async_get(ZHIHU_HOT_URL, timeout=15.0, headers=headers)
            if resp.status_code != 200:
                logger.warning("知乎热榜接口状态码异常: %s", resp.status_code)
                return items
            data = resp.json()
            for entry in data.get("data", []):
                target = entry.get("target", {})
                title = target.get("title", "")
                if not title:
                    continue
                detail_text = entry.get("detail_text", "0 万热度")
                heat = 0.0
                try:
                    num = float(detail_text.replace("万热度", "").replace(" 万热度", "").strip())
                    heat = num * 10000
                except (TypeError, ValueError):
                    heat = 0.0
                url = target.get("url", "")
                items.append(HotspotItem(
                    word=title,
                    heat_value=heat,
                    rank=len(items) + 1,
                    category="知识",
                    source=self.source_name,
                    url=url,
                ))
        except Exception as e:
            logger.error("知乎热榜抓取失败: %s", e)
        logger.info("知乎热榜抓取到 %d 条", len(items))
        return items
