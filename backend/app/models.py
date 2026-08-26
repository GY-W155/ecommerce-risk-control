"""ORM 模型：对应 2.3.8 的 8 张数据表。

说明：
- `event_payload_json` / `condition_json` / `feature_json` 使用 MySQL JSON 类型，
  SQLAlchemy 自动完成 dict <-> JSON 互转。
- 统一主键用 BIGINT 自增。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class RiskEvent(Base):
    """风险事件表：每一次风险检查的原始入参。"""

    __tablename__ = "risk_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)
    source_id = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=False, index=True)
    order_id = Column(String(64), index=True)
    event_payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assessment = relationship("RiskAssessment", back_populates="event", uselist=False)


class RiskAssessment(Base):
    """风险评估结果表。"""

    __tablename__ = "risk_assessments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(BigInteger, ForeignKey("risk_events.id"), nullable=False, index=True)
    risk_score = Column(Float, nullable=False, default=0.0)
    risk_level = Column(String(10), nullable=False, default="low")
    decision = Column(String(20), nullable=False, default="pass")
    assessment_status = Column(String(20), nullable=False, default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("RiskEvent", back_populates="assessment")
    feature_snapshot = relationship(
        "FeatureSnapshot", back_populates="assessment", uselist=False
    )
    rule_hits = relationship("RuleHit", back_populates="assessment")


class FeatureSnapshot(Base):
    """特征快照表：按键值对保存特征，便于回看。"""

    __tablename__ = "feature_snapshots"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    assessment_id = Column(
        BigInteger, ForeignKey("risk_assessments.id"), nullable=False, index=True
    )
    feature_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    assessment = relationship("RiskAssessment", back_populates="feature_snapshot")


class RiskRule(Base):
    """风控规则表。"""

    __tablename__ = "risk_rules"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    rule_code = Column(String(64), nullable=False, unique=True, index=True)
    rule_name = Column(String(128), nullable=False)
    rule_status = Column(Integer, nullable=False, default=1)  # 1 启用 / 0 停用
    priority = Column(Integer, nullable=False, default=0)  # 大者优先
    score = Column(Float, nullable=False, default=0.0)
    condition_json = Column(JSON, nullable=False)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RuleHit(Base):
    """规则命中记录表。"""

    __tablename__ = "rule_hits"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    assessment_id = Column(
        BigInteger, ForeignKey("risk_assessments.id"), nullable=False, index=True
    )
    rule_id = Column(BigInteger, ForeignKey("risk_rules.id"), nullable=False)
    hit_score = Column(Float, nullable=False, default=0.0)
    hit_message = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    assessment = relationship("RiskAssessment", back_populates="rule_hits")
    rule = relationship("RiskRule")


class RiskCase(Base):
    """风险案件审核表。"""

    __tablename__ = "risk_cases"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    assessment_id = Column(
        BigInteger, ForeignKey("risk_assessments.id"), nullable=False, index=True
    )
    user_id = Column(String(64), nullable=False, index=True)
    order_id = Column(String(64), index=True)
    risk_level = Column(String(10), nullable=False, default="high")
    case_status = Column(String(20), nullable=False, default="pending")  # pending/reviewing/approved/rejected/resolved
    reviewer_id = Column(String(64), nullable=True)
    review_result = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assessment = relationship("RiskAssessment")
    review_logs = relationship("ReviewLog", back_populates="case")


class Blacklist(Base):
    """黑名单表。"""

    __tablename__ = "blacklists"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    blacklist_type = Column(String(20), nullable=False)  # user / order / address / phone / ip
    blacklist_value = Column(String(128), nullable=False, index=True)
    remark = Column(String(255), nullable=True)
    status = Column(Integer, nullable=False, default=1)  # 1 生效 / 0 失效
    created_at = Column(DateTime, default=datetime.utcnow)


class ReviewLog(Base):
    """审核日志表。"""

    __tablename__ = "review_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, ForeignKey("risk_cases.id"), nullable=False, index=True)
    operator_id = Column(String(64), nullable=True)
    action_type = Column(String(30), nullable=False)  # auto_create / review / status_change
    action_remark = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("RiskCase", back_populates="review_logs")
