"""种子脚本：预置规则、黑名单、演示业务数据与历史事件/案件。

用法：`python -m app.seed`  （或在应用启动时调用 create_tables + seed_all）
幂等：按 rule_code / value 判断，重复执行不会产生脏数据。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from .database import Base, SessionLocal, engine
from .models import (
    Blacklist,
    FeatureSnapshot,
    ReviewLog,
    RiskAssessment,
    RiskCase,
    RiskEvent,
    RiskRule,
    RuleHit,
)
from .services import business_data as biz

# ---------------------------------------------------------------------------
# 规则（28 条，覆盖用户/订单/地址三维度；rule_code 前缀 REJ/MAN/SCR 决定决策归属）
# ---------------------------------------------------------------------------
def _c(feature: str, op: str, value: Any):
    return {"feature": feature, "op": op, "value": value}


def _and(*conds):
    return {"operator": "AND", "conditions": list(conds)}


def _or(*conds):
    return {"operator": "OR", "conditions": list(conds)}


RULES: List[Dict[str, Any]] = [
    # --- 用户维度 ---
    dict(rule_code="REJ001", rule_name="命中用户黑名单", score=90, priority=100,
         condition=_and(_c("user_blacklist_hit", "=", 1)),
         description="用户ID或手机号命中黑名单，直接拒绝"),
    dict(rule_code="MAN001", rule_name="新注册用户大额订单", score=55, priority=80,
         condition=_and(_c("user_new_flag", "=", 1), _c("order_amount", ">", 5000)),
         description="新注册用户下单金额过高，人工复核"),
    dict(rule_code="MAN002", rule_name="退款次数过多", score=60, priority=70,
         condition=_and(_c("user_refund_count_30d", ">", 3)),
         description="近30天退款超3次，人工复核"),
    dict(rule_code="MAN003", rule_name="投诉次数过多", score=55, priority=70,
         condition=_and(_c("user_complaint_count_30d", ">", 1)),
         description="近30天投诉超1次，人工复核"),
    dict(rule_code="MAN004", rule_name="历史高风险事件多", score=60, priority=70,
         condition=_and(_c("user_history_high_risk_events", ">=", 2)),
         description="存在多条历史高风险事件，人工复核"),
    dict(rule_code="MAN005", rule_name="设备数异常", score=45, priority=60,
         condition=_and(_c("user_device_count", ">", 3)),
         description="关联设备数过多，疑似多账号，人工复核"),
    dict(rule_code="MAN006", rule_name="手机号频繁变更", score=50, priority=60,
         condition=_and(_c("user_mobile_changed_7d", "=", 1)),
         description="近7天更换过手机号，人工复核"),
    dict(rule_code="MAN007", rule_name="新用户高频下单", score=50, priority=60,
         condition=_and(_c("user_new_flag", "=", 1), _c("user_order_freq_7d", ">", 2)),
         description="新用户7天下单超2次，人工复核"),
    dict(rule_code="MAN008", rule_name="新用户即退款", score=40, priority=50,
         condition=_and(_c("user_new_flag", "=", 1), _c("user_refund_count_30d", ">=", 1)),
         description="新注册用户即出现退款，人工复核"),
    dict(rule_code="MAN009", rule_name="远超历史消费均值", score=45, priority=50,
         condition=_and(_c("order_amount_vs_avg", ">", 5)),
         description="订单金额远超该用户历史均值，人工复核"),
    # --- 订单维度 ---
    dict(rule_code="SCR010", rule_name="大额订单", score=35, priority=40,
         condition=_and(_c("order_high_value", "=", 1)),
         description="订单金额>=5000元，命中大额订单规则"),
    dict(rule_code="SCR011", rule_name="夜间大额订单", score=30, priority=40,
         condition=_and(_c("order_night_flag", "=", 1), _c("order_amount", ">=", 3000)),
         description="凌晨时段高金额订单，命中夜间大额规则"),
    dict(rule_code="MAN012", rule_name="低折扣高价值订单", score=55, priority=60,
         condition=_and(_c("order_discount_ratio", ">", 0.5), _c("order_amount", ">=", 8000)),
         description="高金额且折扣异常，人工复核"),
    dict(rule_code="MAN013", rule_name="优惠券套利", score=40, priority=50,
         condition=_and(_c("order_has_coupon", "=", 1), _c("order_amount_vs_avg", ">", 2)),
         description="用券且金额异常偏高，人工复核"),
    dict(rule_code="MAN014", rule_name="订单支付超时", score=35, priority=45,
         condition=_and(_c("order_pay_timeout", "=", 1)),
         description="支付耗时过长，人工复核"),
    dict(rule_code="MAN015", rule_name="敏感商品批量下单", score=55, priority=60,
         condition=_and(_c("order_sensitive_goods", "=", 1), _c("order_item_count", ">=", 3)),
         description="敏感商品且件数>=3，人工复核"),
    dict(rule_code="MAN016", rule_name="高折扣异常订单", score=55, priority=55,
         condition=_and(_c("order_discount_ratio", ">", 0.8)),
         description="折扣比例超过80%，疑似异常订单"),
    dict(rule_code="MAN017", rule_name="敏感商品高折扣", score=45, priority=50,
         condition=_and(_c("order_discount_ratio", ">", 0.3), _c("order_sensitive_goods", "=", 1)),
         description="敏感商品叠加高折扣，人工复核"),
    dict(rule_code="SCR018", rule_name="多件商品订单", score=25, priority=30,
         condition=_and(_c("order_item_count", ">=", 5)),
         description="单笔订单件数>=5，命中多件商品规则"),
    dict(rule_code="MAN019", rule_name="7天高频下单", score=40, priority=50,
         condition=_and(_c("user_order_freq_7d", ">=", 3)),
         description="7天内下单>=3次，疑似刷单，人工复核"),
    # --- 地址维度 ---
    dict(rule_code="REJ020", rule_name="地址命中黑名单", score=95, priority=100,
         condition=_and(_c("address_blacklist_hit", "=", 1)),
         description="收货地址命中黑名单，直接拒绝"),
    dict(rule_code="MAN021", rule_name="高危地区地址", score=55, priority=60,
         condition=_and(_c("address_region_risk", "=", 1)),
         description="收货地址位于高危地区，人工复核"),
    dict(rule_code="MAN022", rule_name="地址被频繁使用", score=30, priority=40,
         condition=_and(_c("address_used_count", ">", 20)),
         description="收货地址使用次数过高，可能多人共用"),
    dict(rule_code="MAN023", rule_name="收件人不符", score=45, priority=50,
         condition=_and(_c("address_mismatch", "=", 1)),
         description="收件人与注册实名不一致，人工复核"),
    dict(rule_code="MAN024", rule_name="地址频繁变更", score=40, priority=45,
         condition=_and(_c("address_area_changed_7d", "=", 1)),
         description="近7天更换收货区域，人工复核"),
    dict(rule_code="MAN025", rule_name="远程地址大额订单", score=50, priority=55,
         condition=_and(_c("address_distance_km", ">", 1000), _c("order_amount", ">", 5000)),
         description="远程地址伴随大额订单，人工复核"),
    dict(rule_code="REJ026", rule_name="高危省份地址", score=80, priority=90,
         condition=_and(_c("address_province_risk_score", ">=", 100)),
         description="收货地址所在省份风险分>=100，直接拒绝"),
    dict(rule_code="MAN027", rule_name="新用户高危区下单", score=45, priority=55,
         condition=_and(_c("user_risk_region", "=", 1), _c("user_new_flag", "=", 1)),
         description="位于高地势风险区域的新用户下单，人工复核"),
]


def seed_rules(db) -> None:
    existing = {r.rule_code for r in db.query(RiskRule.rule_code).all()}
    for r in RULES:
        if r["rule_code"] in existing:
            continue
        db.add(RiskRule(
            rule_code=r["rule_code"],
            rule_name=r["rule_name"],
            rule_status=1,
            priority=r["priority"],
            score=r["score"],
            condition_json=r["condition"],
            description=r["description"],
        ))
    db.commit()


def seed_blacklists(db) -> None:
    values = [
        ("user", "U3003", "高风险用户"),
        ("address", "高风险街道 88 号", "高危收货地址"),
        ("address", "边境自贸区", "高危地区街道"),
        ("phone", "13800001111", "高风险手机号"),
    ]
    existing = {b.blacklist_value for b in db.query(Blacklist.blacklist_value).all()}
    for t, v, remark in values:
        if v in existing:
            continue
        db.add(Blacklist(blacklist_type=t, blacklist_value=v, remark=remark, status=1))
    db.commit()


def seed_demo_history(db) -> None:
    """生成若干历史风险事件/评估/案件，让看板与画像页开箱有数据。"""
    if db.query(RiskAssessment).count() > 0:
        return
    now = datetime.utcnow()
    # (user_id, order_id, event_type, days_ago, level, decision, score)
    plan = [
        ("U1001", "U1001-O1001", "order_create", 2, "low", "pass", 20),
        ("U1001", "U1001-O1002", "order_pay", 1, "low", "pass", 25),
        ("U2002", "U2002-O2001", "order_create", 1, "high", "reject", 88),
        ("U2002", "U2002-O2001", "order_pay", 1, "high", "manual_review", 75),
        ("U2002", "U2002-O2002", "after_sale_apply", 2, "medium", "manual_review", 60),
        ("U2002", "U2002-O2003", "logistics_complaint", 3, "medium", "manual_review", 55),
        ("U3003", "U3003-O3001", "order_create", 0, "high", "reject", 92),
        ("U1001", "U1001-O1003", "order_create", 5, "low", "pass", 15),
        ("U1001", "U1001-O1004", "order_pay", 6, "low", "pass", 18),
        ("U2002", "U2002-O2004", "order_create", 7, "medium", "manual_review", 48),
    ]
    rule_map = {r.rule_code: r for r in db.query(RiskRule).all()}
    for user_id, order_id, etype, days, level, decision, score in plan:
        event = RiskEvent(
            event_type=etype, source_id=f"seed-{etype}", user_id=user_id,
            order_id=order_id, event_payload_json={"amount": score * 10},
            created_at=now - timedelta(days=days),
        )
        db.add(event)
        db.flush()
        assessment = RiskAssessment(
            event_id=event.id, risk_score=score, risk_level=level,
            decision=decision, assessment_status="completed",
            created_at=now - timedelta(days=days),
        )
        db.add(assessment)
        db.flush()
        db.add(FeatureSnapshot(
            assessment_id=assessment.id,
            feature_json={"user_id": user_id, "event_type": etype, "order_amount": score * 10},
            created_at=now - timedelta(days=days),
        ))
        if rule_map:
            # 挑一条近似 rule_code 命中以填充命中统计
            code = "REJ001" if level == "high" and decision == "reject" else (
                "MAN001" if decision == "manual_review" else "SCR010"
            )
            rule = rule_map.get(code) or list(rule_map.values())[0]
            db.add(RuleHit(
                assessment_id=assessment.id, rule_id=rule.id,
                hit_score=rule.score * 0.6, hit_message=rule.description,
                created_at=now - timedelta(days=days),
            ))
        # 高/中风险自动产生案件（含一笔已审核）
        if level in ("high", "medium"):
            case = RiskCase(
                assessment_id=assessment.id, user_id=user_id, order_id=order_id,
                risk_level=level, case_status="pending",
                created_at=now - timedelta(days=days),
                updated_at=now - timedelta(days=days),
            )
            db.add(case)
            db.flush()
            db.add(ReviewLog(
                case_id=case.id, operator_id="system", action_type="auto_create",
                action_remark=f"自动生成：{level} / {decision}",
                created_at=now - timedelta(days=days),
            ))
    db.commit()


def seed_all(db) -> None:
    biz.seed_business_data()
    seed_rules(db)
    seed_blacklists(db)
    seed_demo_history(db)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def main() -> None:
    create_tables()
    db = SessionLocal()
    try:
        seed_all(db)
        print("种子数据初始化完成。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
