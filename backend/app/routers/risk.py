"""风险检查与规则管理接口。"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import RiskRule, RuleHit
from ..schemas import (
    AssessmentOut,
    RiskCheckRequest,
    RiskCheckResponse,
    RuleCreate,
    RuleDelete,
    RuleOut,
    RuleStatus,
    RuleUpdate,
)
from ..services.assessment_engine import get_assessment_detail, run_check
from ..services.rule_engine import validate_condition

router = APIRouter()


# ---------------------------------------------------------------------------
# 风险检查 / 评估查询
# ---------------------------------------------------------------------------
@router.post("/check", response_model=RiskCheckResponse)
def check_risk(req: RiskCheckRequest, db: Session = Depends(get_db)):
    return run_check(db, req)


@router.get("/assessments/{assessment_id}", response_model=AssessmentOut)
def assessment_detail(assessment_id: int, db: Session = Depends(get_db)):
    detail = get_assessment_detail(db, assessment_id)
    if not detail:
        raise HTTPException(status_code=404, detail="评估记录不存在")
    return detail


# ---------------------------------------------------------------------------
# 规则管理
# ---------------------------------------------------------------------------
def _rule_to_out(rule: RiskRule, hit_counts: Dict[int, int]) -> RuleOut:
    out = RuleOut.model_validate(rule)
    out.hit_count = hit_counts.get(rule.id, 0)
    return out


@router.get("/rules", response_model=List[RuleOut])
def list_rules(db: Session = Depends(get_db)):
    rules = db.query(RiskRule).order_by(RiskRule.priority.desc(), RiskRule.id.asc()).all()
    counts = (
        dict(db.query(RuleHit.rule_id, func.count()).group_by(RuleHit.rule_id).all())
        if rules
        else {}
    )
    return [_rule_to_out(r, counts) for r in rules]


@router.post("/rules", response_model=RuleOut)
def create_rule(body: RuleCreate, db: Session = Depends(get_db)):
    err = validate_condition(body.condition_json)
    if err:
        raise HTTPException(400, err)
    if db.query(RiskRule).filter(RiskRule.rule_code == body.rule_code).first():
        raise HTTPException(400, f"规则编码 {body.rule_code} 已存在")
    rule = RiskRule(**body.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_to_out(rule, {})


@router.post("/rules/update", response_model=RuleOut)
def update_rule(body: RuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(RiskRule).filter(RiskRule.id == body.id).first()
    if not rule:
        raise HTTPException(404, "规则不存在")
    err = validate_condition(body.condition_json)
    if err:
        raise HTTPException(400, err)
    duplicate = (
        db.query(RiskRule)
        .filter(RiskRule.rule_code == body.rule_code, RiskRule.id != body.id)
        .first()
    )
    if duplicate:
        raise HTTPException(400, f"规则编码 {body.rule_code} 已被占用")
    for k, v in body.model_dump().items():
        setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    return _rule_to_out(rule, {})


@router.post("/rules/status", response_model=RuleOut)
def change_rule_status(body: RuleStatus, db: Session = Depends(get_db)):
    rule = db.query(RiskRule).filter(RiskRule.id == body.id).first()
    if not rule:
        raise HTTPException(404, "规则不存在")
    rule.rule_status = 1 if body.rule_status == 1 else 0
    db.commit()
    db.refresh(rule)
    return _rule_to_out(rule, {})


@router.post("/rules/delete")
def delete_rule(body: RuleDelete, db: Session = Depends(get_db)):
    rule = db.query(RiskRule).filter(RiskRule.id == body.id).first()
    if not rule:
        raise HTTPException(404, "规则不存在")
    db.delete(rule)
    db.commit()
    return {"ok": True, "id": body.id}
