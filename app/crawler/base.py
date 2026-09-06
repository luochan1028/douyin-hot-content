"""爬虫基类与统一数据结构。"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class HotspotItem:
    word: str
    heat_value: float = 0.0
    rank: int = 0
    category: str = ""
    source: str = ""
    url: str = ""
    crawl_time: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "word": self.word,
            "heat_value": self.heat_value,
            "rank": self.rank,
            "category": self.category,
            "source": self.source,
            "url": self.url,
            "crawl_time": self.crawl_time.isoformat(),
        }


class BaseCrawler:
    """所有爬虫的基类。"""

    source_name: str = "base"

    async def fetch(self) -> List[HotspotItem]:
        """抓取热点列表，子类实现。"""
        raise NotImplementedError
