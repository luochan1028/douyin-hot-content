"""数据库模型。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class Hotspot(Base):
    """热点词汇表。"""
    __tablename__ = "hotspots"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(255), nullable=False, index=True)
    heat_value = Column(Float, default=0.0)
    rank = Column(Integer, default=0)
    category = Column(String(64), default="")
    source = Column(String(64), nullable=False)  # 数据源标识
    url = Column(String(512), default="")
    content_hash = Column(String(64), index=True)
    # 热度评估
    heat_score = Column(Float, default=0.0)
    lifecycle = Column(String(32), default="萌芽期")  # 萌芽期/爆发期/衰退期
    # 准确性保障
    credibility_score = Column(Float, default=0.0)
    review_status = Column(String(32), default="pending")  # pending/approved/rejected/review
    is_sensitive = Column(Boolean, default=False)
    match_score = Column(Float, default=0.0)
    source_count = Column(Integer, default=1)  # 出现的数据源数量
    first_seen = Column(DateTime, default=datetime.utcnow)
    crawl_time = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    tags = Column(String(512), default="")  # 组合后的 SEO 标签，逗号分隔

    media_assets = relationship("MediaAsset", back_populates="hotspot", cascade="all, delete-orphan")


class MediaAsset(Base):
    """媒体素材表。"""
    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True, index=True)
    hotspot_id = Column(Integer, ForeignKey("hotspots.id"), nullable=True)
    asset_type = Column(String(16), nullable=False)  # image/video
    local_path = Column(String(512), nullable=False)
    url = Column(String(512), default="")
    status = Column(String(16), default="success")  # generating/success/failed
    meta = Column(Text, default="")  # JSON 元信息
    created_at = Column(DateTime, default=datetime.utcnow)

    hotspot = relationship("Hotspot", back_populates="media_assets")


class PublishRecord(Base):
    """发布记录表。"""
    __tablename__ = "publish_records"

    id = Column(Integer, primary_key=True, index=True)
    hotspot_word = Column(String(255), default="")
    media_asset_id = Column(Integer, ForeignKey("media_assets.id"), nullable=True)
    douyin_video_id = Column(String(128), default="")
    status = Column(String(16), default="pending")  # pending/success/failed/withdrawn
    copy_content = Column(Text, default="")
    tags = Column(String(512), default="")
    error_msg = Column(Text, default="")
    scheduled_time = Column(DateTime, nullable=True)
    publish_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReviewTicket(Base):
    """人工审核工单表。"""
    __tablename__ = "review_tickets"

    id = Column(Integer, primary_key=True, index=True)
    hotspot_id = Column(Integer, nullable=True)
    hotspot_word = Column(String(255), default="")
    credibility_score = Column(Float, default=0.0)
    risk_hint = Column(Text, default="")
    category_result = Column(String(64), default="")
    status = Column(String(16), default="pending")  # pending/approved/rejected
    reviewed_by = Column(String(64), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)


class TaskLog(Base):
    """任务执行日志表。"""
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(128), nullable=False)
    status = Column(String(16), default="running")  # running/success/failed/skipped
    detail = Column(Text, default="")
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
