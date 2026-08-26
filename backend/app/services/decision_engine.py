"""决策引擎：根据命中规则与评分，输出风险等级与处理建议，并判定是否自动建案。

映射关系（需求 2.3.4 / 2.3.10）：
- 风险评分 0~100
- 风险等级 low / medium / high（按阈值）
- 处理建议 pass / manual_review / reject
- level==high 或 decision∈{manual_review, reject} 时自动创建案件

规则分类约定（seed 中 rule_code 前缀）：
- REJxxx / score>=60  → 倾向于 reject
- MANxxx / score>=30  → 倾向于 manual_review
- 其余（得分型）按等级兜底
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..config import settings


def _category(rule_code: str, score: float) -> str:
    code = (rule_code or "").upper()
    if code.startswith(("REJ", "REJECT")):
        return "reject"
    if code.startswith(("MAN", "MANUAL")):
        return "manual_review"
    if score >= 60:
        return "reject"
    if score >= 30:
        return "manual_review"
    return ""


def decide(hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """输入规则命中列表，返回 {risk_score, risk_level, decision, auto_create_case}。"""
    risk_score = round(sum(h["hit_score"] for h in hits), 2)
    risk_score = max(0.0, min(100.0, risk_score))

    if risk_score < settings.low_threshold:
        risk_level = "low"
    elif risk_score < settings.high_threshold:
        risk_level = "medium"
    else:
        risk_level = "high"

    cats = {_category(h["rule_code"], h["hit_score"]) for h in hits}
    if "reject" in cats:
        decision = "reject"
    elif "manual_review" in cats:
        decision = "manual_review"
    elif risk_level == "high":
        decision = "reject"
    elif risk_level == "medium":
        decision = "manual_review"
    else:
        decision = "pass"

    auto_create_case = risk_level == "high" or decision in ("manual_review", "reject")

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "decision": decision,
        "auto_create_case": auto_create_case,
    }
