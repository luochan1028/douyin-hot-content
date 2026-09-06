"""热度评估服务：批量更新热点的热度评分与生命周期。"""
from datetime import datetime
from typing import List

from app.database import SessionLocal
from app.models import Hotspot
from app.heat.scorer import compute_heat_score, generate_seo_tags
from app.logger import get_logger

logger = get_logger("heat.service")


def run_heat_evaluation() -> dict:
    """对所有已通过准确性校验的热点执行热度评估。"""
    db = SessionLocal()
    stats = {"burst": 0, "sprout": 0, "decline": 0, "total": 0}
    try:
        hotspots = (
            db.query(Hotspot)
            .filter(Hotspot.review_status == "approved")
            .all()
        )
        stats["total"] = len(hotspots)
        for hs in hotspots:
            result = compute_heat_score(
                heat_value=hs.heat_value or 0.0,
                history=[hs.heat_value] if hs.heat_value else [],
                interaction_rate=0.0,
                age_hours=0.0,
                is_new=True,
                rising_windows=0,
            )
            hs.heat_score = result["score"]
            hs.lifecycle = result["stage"]
            # 生成 SEO 标签
            vertical = [hs.category] if hs.category else []
            tags = generate_seo_tags(hs.word, vertical, [])
            hs.tags = ",".join(tags)

            if result["stage"] == "爆发期":
                stats["burst"] += 1
            elif result["stage"] == "萌芽期":
                stats["sprout"] += 1
            else:
                stats["decline"] += 1
        db.commit()
        logger.info("热度评估完成: %s", stats)
    except Exception as e:
        db.rollback()
        logger.error("热度评估失败: %s", e)
    finally:
        db.close()
    return stats
