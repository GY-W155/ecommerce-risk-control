"""评估引擎：编排一次风险检查的完整链路并落库。

链路：写事件 → 算特征 → 匹配规则 → 评分决策 → 落库(评估/特征快照/规则命中)
      → (按需)自动建案 → 返回结果。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import (
    FeatureSnapshot,
    ReviewLog,
    RiskAssessment,
    RiskCase,
    RiskEvent,
    RiskRule,
    RuleHit,
)
from ..schemas import RiskCheckRequest
from . import business_data as biz
from . import decision_engine, feature_engine, rule_engine

logger = logging.getLogger("risk.assessment")


def _payload_of(req: RiskCheckRequest) -> Dict[str, Any]:
    payload = dict(req.event_payload or {})
    payload["source_id"] = req.source_id
    return payload


def run_check(db: Session, req: RiskCheckRequest) -> Dict[str, Any]:
    """执行一次风险检查，返回 {event_id, assessment_id, ..., case_id}。"""
    payload = _payload_of(req)

    # 1. 写事件
    event = RiskEvent(
        event_type=req.event_type,
        source_id=req.source_id,
        user_id=req.user_id,
        order_id=req.order_id,
        event_payload_json=payload,
    )
    db.add(event)
    db.flush()  # 得到 event.id
    logger.info("接受事件 type=%s user=%s order=%s source=%s", req.event_type, req.user_id, req.order_id, req.source_id)

    # 2. 计算特征（复用函数，保证对未知用户也能算）
    features = feature_engine.compute_features(
        db, req.event_type, req.user_id, req.order_id, payload
    )

    # 3. 规则匹配
    hits = rule_engine.match_rules(db, features)
    logger.info("规则匹配 事件id=%s 命中=%s 条", event.id, len(hits))

    # 4. 评分、分级、建议
    decision = decision_engine.decide(hits)

    # 5. 落库评估结果
    assessment = RiskAssessment(
        event_id=event.id,
        risk_score=decision["risk_score"],
        risk_level=decision["risk_level"],
        decision=decision["decision"],
        assessment_status="completed",
    )
    db.add(assessment)
    db.flush()

    # 6. 特征快照 + 规则命中
    snapshot = FeatureSnapshot(assessment_id=assessment.id, feature_json=features)
    db.add(snapshot)
    for h in hits:
        db.add(
            RuleHit(
                assessment_id=assessment.id,
                rule_id=h["rule_id"],
                hit_score=h["hit_score"],
                hit_message=h["hit_message"],
            )
        )

    # 7. 自动建案
    case_id: Optional[int] = None
    if decision["auto_create_case"]:
        case = RiskCase(
            assessment_id=assessment.id,
            user_id=req.user_id,
            order_id=req.order_id,
            risk_level=decision["risk_level"],
            case_status="pending",
        )
        db.add(case)
        db.flush()
        case_id = case.id
        db.add(
            ReviewLog(
                case_id=case.id,
                operator_id="system",
                action_type="auto_create",
                action_remark=(
                    f"自动创建案件：风险等级 {decision['risk_level']}，"
                    f"处理建议 {decision['decision']}，评分 {decision['risk_score']}"
                ),
            )
        )
        logger.info("自动建案 case_id=%s assessment_id=%s level=%s decision=%s", case.id, assessment.id, decision["risk_level"], decision["decision"])

    db.commit()
    logger.info("评估完成 assessment_id=%s score=%s level=%s decision=%s", assessment.id, decision["risk_score"], decision["risk_level"], decision["decision"])

    return {
        "event_id": event.id,
        "assessment_id": assessment.id,
        "risk_score": decision["risk_score"],
        "risk_level": decision["risk_level"],
        "decision": decision["decision"],
        "rule_hits": hits,
        "feature_snapshot": features,
        "case_id": case_id,
    }


def get_assessment_detail(db: Session, assessment_id: int) -> Optional[Dict[str, Any]]:
    """组装 GET /assessments/{id} 的响应。"""
    assessment = db.query(RiskAssessment).filter(RiskAssessment.id == assessment_id).first()
    if not assessment:
        return None
    event = db.query(RiskEvent).filter(RiskEvent.id == assessment.event_id).first()
    snapshot = (
        db.query(FeatureSnapshot)
        .filter(FeatureSnapshot.assessment_id == assessment.id)
        .first()
    )
    hit_rows = (
        db.query(RuleHit).filter(RuleHit.assessment_id == assessment.id).all()
    )
    rule_map = {}
    if hit_rows:
        rule_map = {
            r.id: r
            for r in db.query(RiskRule)
            .filter(RiskRule.id.in_([h.rule_id for h in hit_rows]))
            .all()
        }

    hits_payload = [
        {
            "rule_id": h.rule_id,
            "rule_code": rule_map[h.rule_id].rule_code if h.rule_id in rule_map else "",
            "rule_name": rule_map[h.rule_id].rule_name if h.rule_id in rule_map else "",
            "hit_score": h.hit_score,
            "hit_message": h.hit_message,
        }
        for h in hit_rows
    ]

    return {
        "id": assessment.id,
        "event_id": assessment.event_id,
        "risk_score": assessment.risk_score,
        "risk_level": assessment.risk_level,
        "decision": assessment.decision,
        "assessment_status": assessment.assessment_status,
        "created_at": assessment.created_at,
        "feature_snapshot": snapshot.feature_json if snapshot else {},
        "rule_hits": hits_payload,
        "event_type": event.event_type if event else None,
        "user_id": event.user_id if event else None,
        "order_id": event.order_id if event else None,
    }
