"""准确性保障服务：批量评估热点可信度并更新数据库。"""
from datetime import datetime, timedelta
from typing import List

from app.database import SessionLocal
from app.models import Hotspot, PublishRecord
from app.accuracy.credibility import evaluate_credibility
from app.accuracy.review import create_ticket
from app.config import settings
from app.logger import get_logger

logger = get_logger("accuracy.service")


def check_repeat_degree(db, word: str) -> int:
    """检测话题重复度：7 天内发布次数。"""
    since = datetime.utcnow() - timedelta(days=7)
    count = (
        db.query(PublishRecord)
        .filter(PublishRecord.hotspot_word == word, PublishRecord.created_at >= since)
        .count()
    )
    return count


def run_accuracy_check() -> dict:
    """对所有 pending 热点执行准确性校验，返回统计。"""
    db = SessionLocal()
    stats = {"approved": 0, "review": 0, "rejected": 0, "total": 0}
    try:
        hotspots = db.query(Hotspot).filter(Hotspot.review_status == "pending").all()
        stats["total"] = len(hotspots)
        for hs in hotspots:
            result = evaluate_credibility(
                word=hs.word,
                source=hs.source.split(",")[0] if hs.source else "",
                source_count=hs.source_count or 1,
                heat_value=hs.heat_value or 0.0,
            )
            hs.credibility_score = result.score
            hs.category = result.category
            hs.match_score = result.match_score
            hs.is_sensitive = result.is_sensitive

            # 重复度检测：7 天内 >= 3 次降为 rejected
            repeat = check_repeat_degree(db, hs.word)
            if repeat >= 3:
                result.decision = "rejected"
                result.reasons.append(f"7天内已发布 {repeat} 次，重复度过高")

            hs.review_status = result.decision

            if result.decision == "review":
                create_ticket(hs, result.score, ";".join(result.reasons), result.category)
                stats["review"] += 1
            elif result.decision == "approved":
                stats["approved"] += 1
            else:
                stats["rejected"] += 1

        db.commit()
        logger.info("准确性校验完成: %s", stats)
    except Exception as e:
        db.rollback()
        logger.error("准确性校验失败: %s", e)
    finally:
        db.close()
    return stats
