"""规则引擎：解析 condition_json 并对特征快照做匹配。

condition_json 结构（支持嵌套）:
{
  "operator": "AND" | "OR",
  "conditions": [
    {"feature": "user_refund_count_30d", "op": ">", "value": 2},
    {"operator": "OR", "conditions": [
        {"feature": "order_amount", "op": ">", "value": 5000},
        {"feature": "order_sensitive_goods", "op": "=", "value": 1}
    ]}
  ]
}

基础判断：>, <, >=, <=, =, !=, contains；复合判断：AND, OR（可嵌套）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import RiskRule

VALID_OPS = {">", "<", ">=", "<=", "=", "!=", "contains"}


def validate_condition(node: Dict[str, Any], path: str = "condition") -> str:
    """校验条件树结构是否合法，返回 '' 表示通过，否则返回错误信息。"""
    if not isinstance(node, dict):
        return f"{path} 必须是对象"
    if isinstance(node.get("conditions"), list):
        operator = node.get("operator", "AND").upper()
        if operator not in ("AND", "OR"):
            return f"{path}.operator 仅支持 AND/OR"
        for i, c in enumerate(node["conditions"]):
            err = validate_condition(c, f"{path}.conditions[{i}]")
            if err:
                return err
        return ""
    feature = node.get("feature")
    op = node.get("op")
    if not feature:
        return f"{path} 缺少 feature"
    if op not in VALID_OPS:
        return f"{path}.op 非法（支持 {sorted(VALID_OPS)}）"
    if "value" not in node:
        return f"{path} 缺少 value"
    return ""


def _coerce(v: Any, target: Any) -> Any:
    """尽力将 v 转成与 target 同类型的值，用于比较。"""
    if isinstance(target, bool):
        return v in (target, 1, True, "1", "true") if isinstance(v, (int, float, str, bool)) else False
    if isinstance(target, (int, float)):
        try:
            return float(v)
        except (TypeError, ValueError):
            return v
    return v


def _compare(actual: Any, op: str, value: Any) -> bool:
    if actual is None and op != "contains":
        return False
    if op == "contains":
        return str(value) in str(actual) if actual is not None else False
    if op == "=" and isinstance(value, str):
        return str(actual) == value
    c = _coerce(actual, value)
    v = value
    if op == ">":
        return bool(c > v)
    if op == "<":
        return bool(c < v)
    if op == ">=":
        return bool(c >= v)
    if op == "<=":
        return bool(c <= v)
    if op == "=":
        return bool(c == v)
    if op == "!=":
        return bool(c != v)
    return False


def eval_condition(node: Dict[str, Any], features: Dict[str, Any]) -> bool:
    """递归判断一个条件节点是否满足。"""
    if node.get("conditions"):
        operator = node.get("operator", "AND").upper()
        results = [eval_condition(c, features) for c in node.get("conditions", [])]
        if operator == "AND":
            return all(results)
        if operator == "OR":
            return any(results)
        # fallback
        return all(results)

    feature = node.get("feature")
    op = node.get("op", "=")
    value = node.get("value")
    if feature is None:
        return False
    actual = features.get(feature)
    return _compare(actual, op, value)


def match_rules(db: Session, features: Dict[str, Any]) -> List[Dict[str, Any]]:
    """按 priority 从大到小匹配启用中的规则，返回命中列表。"""
    rules = (
        db.query(RiskRule)
        .filter(RiskRule.rule_status == 1)
        .order_by(RiskRule.priority.desc(), RiskRule.id.asc())
        .all()
    )
    hits: List[Dict[str, Any]] = []
    for rule in rules:
        cond = rule.condition_json or {}
        if eval_condition(cond, features):
            hit_message = rule.description or f"命中规则 {rule.rule_name}"
            hits.append(
                {
                    "rule_id": rule.id,
                    "rule_code": rule.rule_code,
                    "rule_name": rule.rule_name,
                    "hit_score": rule.score,
                    "hit_message": hit_message,
                }
            )
    return hits
