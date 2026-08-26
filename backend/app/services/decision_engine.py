"""决策引擎：根据命中规则与评分，输出风险等级与处理建议，并判定是否自动建案。

映射关系（需求 2.3.4 / 2.3.10）：
- 风险评分 0~100
- 风险等级 low / medium / high（按阈值）
- 处理建议 pass / manual_review / reject
- level==high 或 decision∈{manual_review, reject} 时自动创建案件

规则意图由 rule_code 前缀表达（区别于得分型 SCR 规则）：
- REJxxx  → 拒绝（如命中黑名单）
- MANxxx  → 人工复核（如退款多、高危地址、异常大额）
- SCRxxx  → 纯得分，仅贡献评分，不直接决定建议

决策优先级（F3 有意设计，详见 decide）：
- 命中 REJ → 拒绝；命中 MAN → 人工复核；否则按等级兜底。
- level==high 但只命中 MAN 规则时，仍为 manual_review（人工把关而非自动拒绝，
  避免仅凭累计过错失地自动拒绝；只有 REJ 类规则才自动拒绝）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..config import settings


def _category(rule_code: str, score: float) -> str:
    """按规则编码前缀提取意图；得分型 SCR 规则返回空串（仅贡献评分）。"""
    code = (rule_code or "").upper()
    if code.startswith(("REJ", "REJECT")):
        return "reject"
    if code.startswith(("MAN", "MANUAL")):
        return "manual_review"
    return ""


def decide(hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """输入规则命中列表，返回 {risk_score, risk_level, decision, auto_create_case}。

    评分：命中分值累加，clamp 到 [0, 100]。
    等级：score<low_threshold→low，<high_threshold→medium，否则 high。
    建议（决策表）：
      1) 命中 REJ 类规则 → reject
      2) 命中 MAN 类规则 → manual_review
      3) 否则按等级兜底：high→reject、medium→manual_review、low→pass

    说明（F3）：当等级为 high 但仅命中 MAN 类规则（无 REJ）时，结果取 manual_review
    而非 reject —— 这是有意设计：只靠累计得分自动拒绝容易误伤，把「高风险但仍需
    人工判断」的场景交给人工把关；自动拒绝仅由明确的 REJ 类规则（如命中黑名单）触发。
    """
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
