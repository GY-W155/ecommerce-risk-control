"""Pydantic 请求/响应模型，对齐需求文档 2.3.9 / 2.3.10。"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------
class EventType(str, enum.Enum):
    order_create = "order_create"
    order_pay = "order_pay"
    after_sale_apply = "after_sale_apply"
    logistics_complaint = "logistics_complaint"


# ---------------------------------------------------------------------------
# 风险检查
# ---------------------------------------------------------------------------
class RiskCheckRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_type: str
    source_id: str
    user_id: str
    order_id: Optional[str] = None
    # 业务侧可能附带的事件补充信息（金额、商品等），落库到 event_payload
    event_payload: Optional[Dict[str, Any]] = None

    @field_validator("event_type")
    @classmethod
    def check_event_type(cls, v: str) -> str:
        if v not in EventType._value2member_map_:
            raise ValueError(f"event_type 仅支持: {list(EventType._value2member_map_.keys())}")
        return v


class RuleHitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rule_id: int
    rule_code: str
    rule_name: str
    hit_score: float
    hit_message: Optional[str] = None


class RiskCheckResponse(BaseModel):
    event_id: int
    assessment_id: int
    risk_score: float
    risk_level: str
    decision: str
    rule_hits: List[RuleHitOut] = Field(default_factory=list)
    feature_snapshot: Dict[str, Any] = Field(default_factory=dict)
    case_id: Optional[int] = None


# ---------------------------------------------------------------------------
# 评估结果查询
# ---------------------------------------------------------------------------
class AssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    risk_score: float
    risk_level: str
    decision: str
    assessment_status: str
    created_at: datetime
    feature_snapshot: Optional[Dict[str, Any]] = None
    rule_hits: List[RuleHitOut] = Field(default_factory=list)
    event_type: Optional[str] = None
    user_id: Optional[str] = None
    order_id: Optional[str] = None


# ---------------------------------------------------------------------------
# 规则
# ---------------------------------------------------------------------------
class RuleBase(BaseModel):
    rule_code: str
    rule_name: str
    rule_status: int = 1
    priority: int = 0
    score: float = 0.0
    condition_json: Dict[str, Any]
    description: Optional[str] = None


class RuleCreate(RuleBase):
    pass


class RuleUpdate(RuleBase):
    id: int


class RuleStatus(BaseModel):
    id: int
    rule_status: int  # 1 启用 / 0 停用


class RuleDelete(BaseModel):
    id: int


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_code: str
    rule_name: str
    rule_status: int
    priority: int
    score: float
    condition_json: Dict[str, Any]
    description: Optional[str] = None
    updated_at: Optional[datetime] = None
    hit_count: int = 0


# ---------------------------------------------------------------------------
# 案件
# ---------------------------------------------------------------------------
class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: int
    user_id: str
    order_id: Optional[str] = None
    risk_level: str
    case_status: str
    reviewer_id: Optional[str] = None
    review_result: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ReviewLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_id: int
    operator_id: Optional[str] = None
    action_type: str
    action_remark: Optional[str] = None
    created_at: datetime


class CaseDetailOut(BaseModel):
    case: CaseOut
    assessment: Optional[AssessmentOut] = None
    review_logs: List[ReviewLogOut] = Field(default_factory=list)


class CaseReviewIn(BaseModel):
    case_id: int
    review_result: str
    review_remark: Optional[str] = None
    operator_id: Optional[str] = None

    @field_validator("review_result")
    @classmethod
    def check_review_result(cls, v: str) -> str:
        if v not in ("approved", "rejected", "resolved", "reviewing"):
            raise ValueError(
                "review_result 仅支持: approved / rejected / resolved / reviewing"
            )
        return v


# ---------------------------------------------------------------------------
# 黑名单
# ---------------------------------------------------------------------------
class BlacklistBase(BaseModel):
    blacklist_type: str  # user / order / address / phone / ip
    blacklist_value: str
    remark: Optional[str] = None


class BlacklistCreate(BlacklistBase):
    pass


class BlacklistDelete(BaseModel):
    ids: List[int]


class BlacklistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    blacklist_type: str
    blacklist_value: str
    remark: Optional[str] = None
    status: int
    created_at: datetime


# ---------------------------------------------------------------------------
# 用户画像 / 看板
# ---------------------------------------------------------------------------
class UserOrderItem(BaseModel):
    order_id: str
    amount: float
    status: str
    created_at: datetime


class UserProfileOut(BaseModel):
    user_id: str
    order_count: int
    refund_count: int
    complaint_count: int
    address_count: int
    blacklist_hit: int
    orders: List[UserOrderItem] = Field(default_factory=list)
    recent_risk_events: List[Dict[str, Any]] = Field(default_factory=list)
    related_cases: List[CaseOut] = Field(default_factory=list)


class DashboardCard(BaseModel):
    label: str
    value: float
    suffix: Optional[str] = None


class NameValueItem(BaseModel):
    name: str
    value: float


class DashboardOut(BaseModel):
    cards: List[DashboardCard] = Field(default_factory=list)
    level_distribution: List[DashboardCard] = Field(default_factory=list)
    trend: List[Dict[str, Any]] = Field(default_factory=list)
    rule_rank: List[NameValueItem] = Field(default_factory=list)
    blacklist_rank: List[NameValueItem] = Field(default_factory=list)
    event_type_distribution: List[NameValueItem] = Field(default_factory=list)
