"""百度热搜爬虫。"""
from typing import List

from app.crawler.base import BaseCrawler, HotspotItem
from app.utils.http import async_get
from app.logger import get_logger

logger = get_logger("crawler.baidu")

BAIDU_HOT_URL = "https://top.baidu.com/api/board?platform=wise&tab=realtime"


class BaiduCrawler(BaseCrawler):
    source_name = "baidu"

    async def fetch(self) -> List[HotspotItem]:
        items: List[HotspotItem] = []
        try:
            resp = await async_get(BAIDU_HOT_URL, timeout=15.0)
            if resp.status_code != 200:
                logger.warning("百度热搜接口状态码异常: %s", resp.status_code)
                return items
            data = resp.json()
            cards = data.get("data", {}).get("cards", [])
            raw_list = []
            for card in cards:
                outer = card.get("content", [])
                for entry in outer:
                    # 百度热榜结构嵌套：content[0].content 为实际列表
                    inner = entry.get("content", []) if isinstance(entry, dict) else []
                    if inner:
                        raw_list.extend(inner)
                    elif isinstance(entry, dict) and entry.get("word"):
                        raw_list.append(entry)
            for content in raw_list:
                word = content.get("word", "")
                if not word:
                    continue
                # 百度接口无直接热度值，用排名换算热度
                rank = len(items) + 1
                heat = float(content.get("hotScore", 0) or 0)
                if heat <= 0:
                    heat = max(1.0, 10000.0 - rank * 100.0)
                url = content.get("url", "")
                items.append(HotspotItem(
                    word=word,
                    heat_value=heat,
                    rank=rank,
                    category="社会",
                    source=self.source_name,
                    url=url,
                ))
        except Exception as e:
            logger.error("百度热搜抓取失败: %s", e)
        logger.info("百度热搜抓取到 %d 条", len(items))
        return items
