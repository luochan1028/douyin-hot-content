"""抖音热搜爬虫（网页版，无需 API Key）。"""
from typing import List

from app.crawler.base import BaseCrawler, HotspotItem
from app.utils.http import async_get
from app.logger import get_logger

logger = get_logger("crawler.douyin")

# 抖音网页端热榜接口（公开，无需鉴权，但可能随版本变化）
DOUYIN_HOT_URL = "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/"


class DouyinCrawler(BaseCrawler):
    source_name = "douyin"

    async def fetch(self) -> List[HotspotItem]:
        items: List[HotspotItem] = []
        try:
            headers = {
                "Referer": "https://www.douyin.com/",
            }
            resp = await async_get(DOUYIN_HOT_URL, timeout=15.0, headers=headers)
            if resp.status_code != 200:
                logger.warning("抖音热搜接口状态码异常: %s", resp.status_code)
                return items
            data = resp.json()
            word_list = data.get("word_list", [])
            for w in word_list:
                word = w.get("word", "")
                if not word:
                    continue
                heat = float(w.get("hot_value", 0) or 0)
                url = w.get("url", "")
                items.append(HotspotItem(
                    word=word,
                    heat_value=heat,
                    rank=len(items) + 1,
                    category="综合",
                    source=self.source_name,
                    url=url,
                ))
        except Exception as e:
            logger.error("抖音热搜抓取失败: %s", e)
        logger.info("抖音热搜抓取到 %d 条", len(items))
        return items
