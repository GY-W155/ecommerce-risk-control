"""特征引擎：根据业务数据计算风险特征快照。

覆盖用户 / 订单 / 地址三个维度共 30+ 个特征。特征名即规则 condition_json 中
`feature` 字段的取值，二者必须一一对应。

数据来源：
- business_data：内存中的演示业务数据（用户/订单/地址/退款/投诉）
- risk_events + risk_assessments：该用户历史风险事件（高风险计数）
- blacklists：命中黑名单判断
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import Blacklist, RiskAssessment, RiskEvent
from . import business_data as biz

_NOW = datetime.utcnow()


def _safe_div(a: float, b: float) -> float:
    return round(a / b, 4) if b else 0.0


def _blacklist_hits(db: Session, candidates: List[Optional[str]]) -> set:
    """返回命中、且 status=1 的黑名单值（小写规范化，避免大小写/空格漏判）。"""
    norm_candidates = {str(c).strip().lower() for c in candidates if c}
    if not norm_candidates:
        return set()
    rows = db.query(Blacklist.blacklist_value).filter(Blacklist.status == 1).all()
    all_values = {str(r[0]).strip().lower() for r in rows}
    return norm_candidates & all_values


def _build_virtual_order(user_id: str, payload: Dict[str, Any], now) -> Dict[str, Any]:
    """当未传 order_id 时，用 payload 中的金额等字段构造一个虚拟订单，
    保证订单维度特征始终拿到本次请求携带的信息（F1 修复）。"""
    return {
        "order_id": payload.get("order_id"),
        "user_id": user_id,
        "amount": float(payload.get("amount", 0) or 0),
        "item_count": int(payload.get("item_count", 1) or 1),
        "discount_ratio": float(payload.get("discount_ratio", 0) or 0),
        "created_at": now,
        "recipient": payload.get("recipient"),
        "sensitive_goods": int(payload.get("sensitive_goods", 0) or 0),
        "has_coupon": int(payload.get("has_coupon", 0) or 0),
        "pay_timeout_ms": int(payload.get("pay_timeout_ms", 30 * 60 * 1000)),
        "address": payload.get("address", ""),
        "address_risk_region": int(payload.get("address_risk_region", 0) or 0),
    }


def _has_order_info(payload: Dict[str, Any]) -> bool:
    return any(
        payload.get(k) is not None
        for k in ("amount", "item_count", "sensitive_goods", "discount_ratio", "has_coupon", "pay_timeout_ms")
    )


def compute_features(
    db: Session,
    event_type: str,
    user_id: str,
    order_id: Optional[str],
    payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """核心入口：返回一个可落库为 feature_snapshot 的键值对字典。"""
    payload = payload or {}
    user = biz.get_user(user_id)
    orders = biz.get_orders(user_id)
    addresses = biz.get_addresses(user_id)
    refunds = biz.get_refunds(user_id)
    complaints = biz.get_complaints(user_id)

    # 当前事件关联订单（不存在则按入参补建，保证订单维度可算）
    order = biz.ensure_order(order_id, user_id, payload) if order_id else None
    # F1：无 order_id 但 payload 携带订单信息时，构造虚拟订单，避免金额输入被忽略
    if order is None and _has_order_info(payload):
        order = _build_virtual_order(user_id, payload, _NOW)

    now = _NOW
    within = lambda d, days: (d is not None) and (now - d).days <= days

    order_counts_30d = sum(1 for o in orders if within(o["created_at"], 30))
    order_counts_7d = sum(1 for o in orders if within(o["created_at"], 7))
    total_amount_30d = round(
        sum(o["amount"] for o in orders if within(o["created_at"], 30)), 2
    )
    avg_amount = _safe_div(sum(o["amount"] for o in orders), len(orders)) if orders else 0.0
    refund_30d = sum(1 for r in refunds if within(r["created_at"], 30))
    complaint_30d = sum(1 for c in complaints if within(c["created_at"], 30))
    last_refund_days = None
    if refunds:
        last_refund = max(r["created_at"] for r in refunds)
        last_refund_days = (now - last_refund).days

    # 历史高风险事件数（当前事件尚末生成 assessment，不会被计入）
    hist_event_ids = [
        r[0] for r in db.query(RiskEvent.id).filter(RiskEvent.user_id == user_id).all()
    ]
    history_high_risk = 0
    if hist_event_ids:
        history_high_risk = (
            db.query(RiskAssessment)
            .filter(
                RiskAssessment.event_id.in_(hist_event_ids),
                RiskAssessment.risk_level == "high",
            )
            .count()
        )

    # 黑名单命中
    user_values = [user_id, user.get("phone")]
    hits = _blacklist_hits(db, user_values + [order_id])
    if order:
        hits = hits | _blacklist_hits(db, [order.get("address"), order.get("recipient")])

    # 地址维度取值（优先取当前订单地址，否则取最近使用地址）
    current_order_addr = (order or {}).get("address")
    addr = next((a for a in addresses if a["address"] == current_order_addr), None)
    sorted_addrs = sorted(
        addresses, key=lambda a: (a.get("last_used_at") or now), reverse=True
    )
    if addr is None and sorted_addrs:
        addr = sorted_addrs[0]

    # 订单维度（当前订单缺失时取最高一笔替代）
    src_order = order or max(orders, key=lambda o: o["amount"]) if orders else None
    order_hour = src_order["created_at"].hour if src_order and src_order.get("created_at") else now.hour
    pay_timeout_ms = src_order.get("pay_timeout_ms") if src_order else 30 * 60 * 1000

    features: Dict[str, Any] = {
        # --- 用户维度 ---
        "user_id": user_id,
        "user_reg_days": user.get("reg_days", 0),
        "user_new_flag": 1 if user.get("reg_days", 999) < 7 else 0,
        "user_device_count": user.get("device_count", 1),
        "user_mobile_changed_7d": user.get("mobile_changed_7d", 0),
        "user_blacklist_hit": (
            1
            if (
                str(user_values[0]).strip().lower() in hits
                or (user.get("phone") and str(user.get("phone")).strip().lower() in hits)
            )
            else 0
        ),
        "user_order_count_30d": order_counts_30d,
        "user_order_count_total": len(orders),
        "user_order_freq_7d": order_counts_7d,
        "user_refund_count_30d": refund_30d,
        "user_refund_count_total": len(refunds),
        "user_complaint_count_30d": complaint_30d,
        "user_address_count": len(addresses),
        "user_order_total_amount_30d": total_amount_30d,
        "user_avg_order_amount": avg_amount,
        "user_last_refund_days": last_refund_days,
        "user_history_high_risk_events": history_high_risk,
        "user_risk_region": user.get("risk_region", 0),
        # --- 订单维度 ---
        "order_amount": round((src_order or {}).get("amount", 0), 2),
        "order_item_count": (src_order or {}).get("item_count", 0),
        "order_discount_ratio": (src_order or {}).get("discount_ratio", 0),
        "order_night_flag": 1 if order_hour < 6 else 0,
        "order_has_coupon": (src_order or {}).get("has_coupon", 0),
        "order_sensitive_goods": (src_order or {}).get("sensitive_goods", 0),
        "order_pay_timeout": 1 if pay_timeout_ms > 30 * 60 * 1000 else 0,
        "order_amount_vs_avg": _safe_div((src_order or {}).get("amount", 0), avg_amount),
        "order_high_value": 1 if (src_order or {}).get("amount", 0) >= 5000 else 0,
        "order_blacklist_hit": 1 if (order_id and str(order_id).strip().lower() in hits) else 0,
        # --- 地址维度 ---
        "address_blacklist_hit": (
            1
            if (addr and str(addr.get("address")).strip().lower() in hits)
            else 0
        ),
        "address_region_risk": (addr or {}).get("risk_region", 0),
        "address_used_count": (addr or {}).get("used_count", 0),
        "address_distance_km": float(payload.get("address_distance_km", 0) or 0),
        "address_mismatch": (
            1
            if (src_order and src_order.get("recipient") and user.get("name")
                and src_order["recipient"] != user["name"])
            else 0
        ),
        "address_area_changed_7d": (
            1
            if len(sorted_addrs) >= 2
            and within(sorted_addrs[0].get("last_used_at"), 7)
            and sorted_addrs[0].get("province") != sorted_addrs[1].get("province")
            else 0
        ),
        "address_province_risk_score": float(
            (addr or {}).get("risk_region", 0)
        ) * 100,
        # --- 事件元信息 ---
        "event_type": event_type,
        "source_id": payload.get("source_id", ""),
        "order_id": order_id,
    }
    return features
