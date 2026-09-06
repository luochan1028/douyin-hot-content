"""话题热度评分与生命周期管理。"""
import math
from datetime import datetime, timedelta
from typing import List, Optional

from app.config import settings
from app.logger import get_logger

logger = get_logger("heat.scorer")


def normalize_heat(value: float, max_value: float = 10_000_000.0) -> float:
    """将原始热度值归一化到 0-100。"""
    if value <= 0:
        return 0.0
    return min(100.0, (value / max_value) * 100.0)


def growth_slope(history: List[float]) -> float:
    """
    计算热度增长斜率（0-100）。
    history 为按时间升序的热度值列表。
    """
    if len(history) < 2:
        return 50.0  # 数据不足，给中性分
    first, last = history[0], history[-1]
    if first <= 0:
        return 100.0 if last > 0 else 0.0
    change = (last - first) / first
    # 映射到 0-100：-50% 以下 -> 0，+100% 以上 -> 100
    slope = 50.0 + change * 50.0
    return max(0.0, min(100.0, slope))


def lifecycle_stage(score: float, slope: float, age_hours: float) -> str:
    """
    生命周期阶段判定。
    - 萌芽期：score < 40 且 slope > 阈值
    - 爆发期：score >= 40
    - 衰退期：score 连续下降或 age 较大且 slope < 0
    """
    if score >= settings.HEAT_SCORE_BURST:
        return "爆发期"
    if slope < 30.0 and age_hours > 6:
        return "衰退期"
    return "萌芽期"


def compute_heat_score(heat_value: float, history: Optional[List[float]] = None,
                       interaction_rate: float = 0.0, age_hours: float = 0.0,
                       is_new: bool = False, rising_windows: int = 0) -> dict:
    """
    综合热度评分（0-100）。
    维度：绝对热度 + 增长趋势 + 互动率 + 生命周期。
    动态加权：新话题 1.5x、持续升温 1.3x。
    """
    history = history or []
    abs_score = normalize_heat(heat_value)
    slope_score = growth_slope(history)

    # 互动率（0-1 映射到 0-100）
    interact_score = min(100.0, interaction_rate * 100.0)

    base = (abs_score * 0.4 + slope_score * 0.35 + interact_score * 0.25)

    # 动态加权
    multiplier = 1.0
    if is_new and slope_score > 60:
        multiplier *= 1.5
    if rising_windows >= 3:
        multiplier *= 1.3

    final_score = min(100.0, base * multiplier)
    stage = lifecycle_stage(final_score, slope_score, age_hours)

    return {
        "score": round(final_score, 2),
        "absolute": round(abs_score, 2),
        "slope": round(slope_score, 2),
        "interaction": round(interact_score, 2),
        "stage": stage,
        "multiplier": round(multiplier, 2),
    }


def generate_seo_tags(core_tag: str, vertical_tags: List[str],
                      long_tail_tags: Optional[List[str]] = None) -> List[str]:
    """
    标签 SEO：1 核心 + 2 垂直 + 1-2 长尾。
    """
    tags = [core_tag]
    tags.extend(vertical_tags[:2])
    if long_tail_tags:
        tags.extend(long_tail_tags[:2])
    # 去重保序
    seen = set()
    result = []
    for t in tags:
        if t and t not in seen:
            result.append(t)
            seen.add(t)
    return result[:5]


def optimal_publish_time(category: str) -> str:
    """根据类别推荐发布时间窗口。"""
    mapping = {
        "科技": "12:00-13:00,18:00-20:00",
        "财经": "08:00-09:00,12:00-13:00",
        "娱乐": "19:00-23:00,周末全天",
        "体育": "赛事时段优先,20:00-22:00",
        "社会": "07:00-09:00,12:00-13:00",
        "生活": "12:00-14:00,19:00-21:00",
        "国际": "08:00-10:00,18:00-20:00",
    }
    return mapping.get(category, "12:00-13:00,18:00-20:00")
