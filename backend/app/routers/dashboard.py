"""用户画像与运营看板接口。"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Blacklist, RiskAssessment, RiskCase, RiskEvent, RiskRule, RuleHit
from ..schemas import UserProfileOut
from ..services import business_data as biz

router = APIRouter()


@router.get("/users/{user_id}/profile", response_model=UserProfileOut)
def user_profile(user_id: str, db: Session = Depends(get_db)):
    user = biz.get_user(user_id)
    orders = biz.get_orders(user_id)
    addresses = biz.get_addresses(user_id)
    refunds = biz.get_refunds(user_id)
    complaints = biz.get_complaints(user_id)

    # 黑名单命中
    user_values = [user_id, user.get("phone")]
    blacklist_hit = (
        db.query(Blacklist)
        .filter(
            Blacklist.status == 1, Blacklist.blacklist_value.in_(user_values)
        )
        .count()
    )

    # 最近风险事件
    recent_events = (
        db.query(RiskEvent)
        .filter(RiskEvent.user_id == user_id)
        .order_by(RiskEvent.id.desc())
        .limit(10)
        .all()
    )
    recent_risk = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "order_id": e.order_id,
            "created_at": e.created_at,
        }
        for e in recent_events
    ]

    related_cases = (
        db.query(RiskCase)
        .filter(RiskCase.user_id == user_id)
        .order_by(RiskCase.id.desc())
        .all()
    )

    return {
        "user_id": user_id,
        "order_count": len(orders),
        "refund_count": len(refunds),
        "complaint_count": len(complaints),
        "address_count": len(addresses),
        "blacklist_hit": blacklist_hit,
        "orders": [
            {
                "order_id": o["order_id"],
                "amount": o["amount"],
                "status": "已支付" if o.get("pay_timeout_ms", 0) < 30 * 60 * 1000 else "待支付",
                "created_at": o["created_at"],
            }
            for o in orders
        ],
        "recent_risk_events": recent_risk,
        "related_cases": [
            {
                "id": c.id,
                "assessment_id": c.assessment_id,
                "user_id": c.user_id,
                "order_id": c.order_id,
                "risk_level": c.risk_level,
                "case_status": c.case_status,
                "reviewer_id": c.reviewer_id,
                "review_result": c.review_result,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in related_cases
        ],
    }


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    event_total = db.query(RiskEvent).count()
    level_rows = dict(
        db.query(RiskAssessment.risk_level, func.count()).group_by(RiskAssessment.risk_level).all()
    )
    low = level_rows.get("low", 0)
    medium = level_rows.get("medium", 0)
    high = level_rows.get("high", 0)

    case_total = db.query(RiskCase).count()
    case_done = (
        db.query(RiskCase)
        .filter(RiskCase.case_status.in_(["approved", "resolved", "rejected"]))
        .count()
    )

    # 近 7 天趋势（按事件日期分组）
    since = datetime.utcnow() - timedelta(days=7)
    trend_rows = (
        db.query(
            func.date(RiskEvent.created_at).label("d"), func.count()
        )
        .filter(RiskEvent.created_at >= since)
        .group_by(func.date(RiskEvent.created_at))
        .all()
    )
    trend_map = {str(d): c for d, c in trend_rows}
    trend = []
    for i in range(6, -1, -1):
        day = (datetime.utcnow() - timedelta(days=i)).date()
        trend.append({"date": str(day), "count": trend_map.get(str(day), 0)})

    # 规则命中排行
    rule_rank = (
        db.query(RiskRule.rule_name, func.count(RuleHit.id))
        .join(RuleHit, RuleHit.rule_id == RiskRule.id)
        .group_by(RiskRule.rule_name)
        .order_by(func.count(RuleHit.id).desc())
        .limit(10)
        .all()
    )
    # 黑名单命中次数：以黑名单类规则(REJ001/REJ020)的命中数近似
    blacklist_rank = (
        db.query(RiskRule.rule_name, func.count(RuleHit.id))
        .join(RuleHit, RuleHit.rule_id == RiskRule.id)
        .filter(RiskRule.rule_code.in_(["REJ001", "REJ020"]))
        .group_by(RiskRule.rule_name)
        .order_by(func.count(RuleHit.id).desc())
        .all()
    )

    # 事件类型分布
    event_dist = (
        db.query(RiskEvent.event_type, func.count()).group_by(RiskEvent.event_type).all()
    )

    high_ratio = round(high / event_total * 100, 1) if event_total else 0
    efficiency = round(case_done / case_total * 100, 1) if case_total else 0

    return {
        "cards": [
            {"label": "风险事件总数", "value": event_total},
            {"label": "高风险事件", "value": high},
            {"label": "高风险占比", "value": high_ratio, "suffix": "%"},
            {"label": "案件总数", "value": case_total},
            {"label": "案件处理效率", "value": efficiency, "suffix": "%"},
        ],
        "level_distribution": [
            {"label": "低风险 low", "value": low},
            {"label": "中风险 medium", "value": medium},
            {"label": "高风险 high", "value": high},
        ],
        "trend": trend,
        "rule_rank": [{"name": n, "value": c} for n, c in rule_rank],
        "blacklist_rank": [{"name": n, "value": c} for n, c in blacklist_rank],
        "event_type_distribution": [{"name": e, "value": c} for e, c in event_dist],
    }
