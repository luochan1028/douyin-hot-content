"""人工审核工单管理。"""
from datetime import datetime
from typing import List, Optional

from app.database import SessionLocal
from app.models import ReviewTicket, Hotspot
from app.logger import get_logger

logger = get_logger("accuracy.review")


def create_ticket(hotspot: Hotspot, score: float, risk_hint: str, category: str) -> Optional[ReviewTicket]:
    db = SessionLocal()
    try:
        ticket = ReviewTicket(
            hotspot_id=hotspot.id,
            hotspot_word=hotspot.word,
            credibility_score=score,
            risk_hint=risk_hint,
            category_result=category,
            status="pending",
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        logger.info("生成审核工单: %s (可信度 %.1f)", hotspot.word, score)
        return ticket
    except Exception as e:
        db.rollback()
        logger.error("工单创建失败: %s", e)
        return None
    finally:
        db.close()


def resolve_ticket(ticket_id: int, status: str, reviewed_by: str = "system") -> bool:
    """处理工单：approved/rejected。"""
    if status not in ("approved", "rejected"):
        return False
    db = SessionLocal()
    try:
        ticket = db.query(ReviewTicket).filter(ReviewTicket.id == ticket_id).first()
        if not ticket:
            return False
        ticket.status = status
        ticket.reviewed_by = reviewed_by
        ticket.reviewed_at = datetime.utcnow()
        # 同步更新对应热点的审核状态
        if ticket.hotspot_id:
            hs = db.query(Hotspot).filter(Hotspot.id == ticket.hotspot_id).first()
            if hs:
                hs.review_status = status
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error("工单处理失败: %s", e)
        return False
    finally:
        db.close()


def list_pending_tickets() -> List[ReviewTicket]:
    db = SessionLocal()
    try:
        return db.query(ReviewTicket).filter(ReviewTicket.status == "pending").all()
    finally:
        db.close()
