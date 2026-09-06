"""微博热搜爬虫。"""
from typing import List

from app.crawler.base import BaseCrawler, HotspotItem
from app.utils.http import async_get
from app.logger import get_logger

logger = get_logger("crawler.weibo")

# 微博移动端热榜 JSON 接口
WEIBO_HOT_URL = "https://m.weibo.cn/api/container/getIndex?containerid=106003type%3D25%26t%3D3%26disable_hot%3D1%26filter_type%3Drealtimehot"


class WeiboCrawler(BaseCrawler):
    source_name = "weibo"

    async def fetch(self) -> List[HotspotItem]:
        items: List[HotspotItem] = []
        try:
            resp = await async_get(WEIBO_HOT_URL, timeout=15.0)
            if resp.status_code != 200:
                logger.warning("微博热搜接口状态码异常: %s", resp.status_code)
                return items
            data = resp.json()
            cards = data.get("data", {}).get("cards", [])
            for card in cards:
                card_group = card.get("card_group", [])
                for cg in card_group:
                    desc = cg.get("desc", "")
                    if not desc:
                        continue
                    heat = 0.0
                    desc_extra = cg.get("desc_extr", 0)
                    try:
                        heat = float(desc_extra) if desc_extra else 0.0
                    except (TypeError, ValueError):
                        heat = 0.0
                    scheme = cg.get("scheme", "")
                    items.append(HotspotItem(
                        word=desc,
                        heat_value=heat,
                        rank=len(items) + 1,
                        category="娱乐",
                        source=self.source_name,
                        url=scheme,
                    ))
        except Exception as e:
            logger.error("微博热搜抓取失败: %s", e)
        logger.info("微博热搜抓取到 %d 条", len(items))
        return items
