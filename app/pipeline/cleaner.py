"""热点数据清洗引擎：去重、阈值过滤、敏感词拦截、分类标签化。"""
from typing import List, Tuple

from app.crawler.base import HotspotItem
from app.utils.hash import content_hash
from app.utils.sensitive import contains_sensitive
from app.config import settings
from app.logger import get_logger

logger = get_logger("pipeline.cleaner")


def clean_items(items: List[HotspotItem]) -> Tuple[List[HotspotItem], int]:
    """
    清洗热点列表。
    返回 (清洗后的列表, 过滤掉的数量)。
    """
    seen_hashes = set()
    cleaned: List[HotspotItem] = []
    filtered = 0

    for item in items:
        # 1. 敏感词过滤
        if contains_sensitive(item.word):
            logger.debug("敏感词过滤: %s", item.word)
            filtered += 1
            continue

        # 2. 热度阈值过滤（有排名的热搜即使无明确热度值也保留）
        if item.heat_value < settings.HEAT_THRESHOLD and item.rank == 0:
            filtered += 1
            continue

        # 3. 去重（基于词的内容哈希）
        h = content_hash(item.word)
        if h in seen_hashes:
            filtered += 1
            continue
        seen_hashes.add(h)

        cleaned.append(item)

    logger.info("清洗完成: 输入 %d 条, 保留 %d 条, 过滤 %d 条", len(items), len(cleaned), filtered)
    return cleaned, filtered


def merge_by_word(items: List[HotspotItem]) -> List[HotspotItem]:
    """
    跨源合并：相同词合并，累加数据源计数，取最高热度。
    """
    merged: dict = {}
    for item in items:
        key = content_hash(item.word)
        if key not in merged:
            merged[key] = item
        else:
            existing = merged[key]
            existing.heat_value = max(existing.heat_value, item.heat_value)
            existing.rank = min(existing.rank, item.rank) if existing.rank else item.rank
    return list(merged.values())
