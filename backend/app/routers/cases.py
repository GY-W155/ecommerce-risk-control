"""风险案件审核接口。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ReviewLog, RiskCase
from ..schemas import CaseDetailOut, CaseOut, CaseReviewIn, ReviewLogOut
from ..services.assessment_engine import get_assessment_detail

router = APIRouter()


@router.get("/cases")
def list_cases(
    status: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
):
    q = db.query(RiskCase)
    if status:
        q = q.filter(RiskCase.case_status == status)
    total = q.count()
    rows = (
        q.order_by(RiskCase.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    items = [CaseOut.model_validate(r) for r in rows]
    return {"total": total, "items": [i.model_dump(mode="json") for i in items]}


@router.get("/cases/{case_id}", response_model=CaseDetailOut)
def case_detail(case_id: int, db: Session = Depends(get_db)):
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "案件不存在")
    assessment = get_assessment_detail(db, case.assessment_id)
    logs = (
        db.query(ReviewLog)
        .filter(ReviewLog.case_id == case.id)
        .order_by(ReviewLog.id.desc())
        .all()
    )
    return {
        "case": CaseOut.model_validate(case),
        "assessment": assessment,
        "review_logs": [ReviewLogOut.model_validate(l) for l in logs],
    }


@router.post("/cases/review")
def review_case(body: CaseReviewIn, db: Session = Depends(get_db)):
    case = db.query(RiskCase).filter(RiskCase.id == body.case_id).first()
    if not case:
        raise HTTPException(404, "案件不存在")
    case.case_status = body.review_result
    case.reviewer_id = body.operator_id or "auditor_001"
    case.review_result = body.review_remark

    log = ReviewLog(
        case_id=case.id,
        operator_id=case.reviewer_id,
        action_type="review",
        action_remark=f"审核结论：{body.review_result}；备注：{body.review_remark or ''}",
    )
    db.add(log)
    db.commit()
    db.refresh(case)
    return {
        "case": CaseOut.model_validate(case),
        "message": "审核完成",
    }
