"""内存中的演示业务数据集。

风控系统需要读取真实业务侧的订单/地址/退款/投诉等数据来"计算特征"。
本模块充当一个简化版的业务系统：由 seed.py 预置若干演示用户及其订单/地址等，
并支持对未知用户按入参动态生成默认画像（保证任意 user_id 都能算出合理特征）。

说明：这些是演示业务数据，不落库到 2.3.8 的 8 张风险表；风险检查本身产生的
历史事件/案件落在 risk_events / risk_cases 中，供统计与画像页查询。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 数据结构说明
# user: {user_id, name, phone, reg_days, device_count, mobile_changed_7d, risk_region}
# order: {order_id, user_id, amount, item_count, discount_ratio, created_at,
#         address, recipient, sensitive_goods, has_coupon, pay_timeout_ms}
# address: {user_id, province, city, address, used_count, last_used_at, risk_region}
# refund: {user_id, amount, created_at}
# complaint: {user_id, level, created_at}
# ---------------------------------------------------------------------------

USERS: Dict[str, Dict[str, Any]] = {}
ORDERS: Dict[str, Dict[str, Any]] = {}
ADDRESSES: Dict[str, List[Dict[str, Any]]] = {}
REFUNDS: Dict[str, List[Dict[str, Any]]] = {}
COMPLAINTS: Dict[str, List[Dict[str, Any]]] = {}

_NOW = datetime.utcnow()


def _days_ago(n: int) -> datetime:
    return _NOW - timedelta(days=n)


def _default_user(user_id: str) -> Dict[str, Any]:
    """为未知用户生成一个中规中矩的默认画像。"""
    seed = abs(hash(user_id)) % 10000
    return {
        "user_id": user_id,
        "name": "用户" + user_id[-4:],
        "phone": "138%08d" % seed,
        "reg_days": max(1, seed % 300),
        "device_count": max(1, seed % 3),
        "mobile_changed_7d": 0,
        "risk_region": 0,
    }


def _default_addresses(user_id: str) -> List[Dict[str, Any]]:
    seed = abs(hash(user_id)) % 10000
    return [
        {
            "user_id": user_id,
            "province": "广东省",
            "city": "深圳市",
            "address": "南山区科技园",
            "used_count": max(1, seed % 20),
            "last_used_at": _days_ago(seed % 60),
            "risk_region": 0,
        }
    ]


def _default_orders(user_id: str) -> List[Dict[str, Any]]:
    seed = abs(hash(user_id)) % 10000
    n = 3 + seed % 5
    orders = []
    for i in range(n):
        orders.append(
            {
                "order_id": f"{user_id}-O{1000 + i}",
                "user_id": user_id,
                "amount": round(20 + (seed % 1000) + i * 10, 2),
                "item_count": 1 + seed % 4,
                "discount_ratio": 0.0,
                "created_at": _days_ago(10 + i * 3),
                "recipient": None,
                "sensitive_goods": 0,
                "has_coupon": 0,
                "pay_timeout_ms": 30 * 60 * 1000,
            }
        )
    return orders


def ensure_user(user_id: str) -> None:
    if user_id not in USERS:
        USERS[user_id] = _default_user(user_id)
    if user_id not in ADDRESSES:
        ADDRESSES[user_id] = _default_addresses(user_id)
    if len(ORDERS_INDEX(user_id)) == 0:
        for o in _default_orders(user_id):
            ORDERS[o["order_id"]] = o


def ORDERS_INDEX(user_id: str) -> List[str]:
    return [oid for oid, o in ORDERS.items() if o["user_id"] == user_id]


def ensure_order(order_id: str, user_id: str, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """若订单不存在则按入参创建（便于演示"新建订单后对其做风控"）。"""
    if order_id in ORDERS:
        return ORDERS[order_id]
    payload = payload or {}
    amount = float(payload.get("amount", 0) or (abs(hash(order_id)) % 500) + 50)
    order = {
        "order_id": order_id,
        "user_id": user_id,
        "amount": round(amount, 2),
        "item_count": int(payload.get("item_count", 1) or (abs(hash(order_id)) % 5) + 1),
        "discount_ratio": float(payload.get("discount_ratio", 0) or 0),
        "created_at": _NOW,
        "recipient": payload.get("recipient", USERS.get(user_id, {}).get("name")),
        "sensitive_goods": int(payload.get("sensitive_goods", 0) or 0),
        "has_coupon": int(payload.get("has_coupon", 0) or 0),
        "pay_timeout_ms": int(payload.get("pay_timeout_ms", 30 * 60 * 1000)),
        "address": payload.get("address", ""),
        "address_risk_region": int(payload.get("address_risk_region", 0) or 0),
    }
    ORDERS[order_id] = order
    return order


def get_user(user_id: str) -> Dict[str, Any]:
    ensure_user(user_id)
    return USERS[user_id]


def get_orders(user_id: str) -> List[Dict[str, Any]]:
    ensure_user(user_id)
    return [ORDERS[oid] for oid in ORDERS_INDEX(user_id)]


def get_order(order_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    order = ORDERS.get(order_id)
    if order is not None:
        return order
    # 允许在检查时按入参补建订单，保证特征可算
    return None


def get_addresses(user_id: str) -> List[Dict[str, Any]]:
    ensure_user(user_id)
    return ADDRESSES[user_id]


def get_refunds(user_id: str) -> List[Dict[str, Any]]:
    ensure_user(user_id)
    if user_id not in REFUNDS:
        # 默认给 0-1 笔小额历史退款
        seed = abs(hash(user_id)) % 100
        if seed < 30:
            REFUNDS[user_id] = [{"user_id": user_id, "amount": 30.0, "created_at": _days_ago(20)}]
        else:
            REFUNDS[user_id] = []
    return REFUNDS[user_id]


def get_complaints(user_id: str) -> List[Dict[str, Any]]:
    ensure_user(user_id)
    if user_id not in COMPLAINTS:
        seed = abs(hash(user_id)) % 100
        if seed < 20:
            COMPLAINTS[user_id] = [{"user_id": user_id, "level": 1, "created_at": _days_ago(15)}]
        else:
            COMPLAINTS[user_id] = []
    return COMPLAINTS[user_id]


# ---------------------------------------------------------------------------
# 种子：预置 3 个典型用户，用于"演示链路"与看板/画像页
# ---------------------------------------------------------------------------
def seed_business_data() -> None:
    # U1001 正常用户
    USERS["U1001"] = {
        "user_id": "U1001", "name": "张三", "phone": "13800000001",
        "reg_days": 120, "device_count": 1, "mobile_changed_7d": 0, "risk_region": 0,
    }
    ADDRESSES["U1001"] = [
        {"user_id": "U1001", "province": "广东省", "city": "广州市",
         "address": "天河区体育西路", "used_count": 18, "last_used_at": _days_ago(3), "risk_region": 0},
        {"user_id": "U1001", "province": "广东省", "city": "佛山市",
         "address": "南海区桂城", "used_count": 5, "last_used_at": _days_ago(25), "risk_region": 0},
    ]
    ORDERS.update({
        "U1001-O1001": {"order_id": "U1001-O1001", "user_id": "U1001", "amount": 259.00,
                        "item_count": 2, "discount_ratio": 0.0, "created_at": _days_ago(2),
                        "recipient": "张三", "sensitive_goods": 0, "has_coupon": 0,
                        "pay_timeout_ms": 8 * 60 * 1000},
        "U1001-O1002": {"order_id": "U1001-O1002", "user_id": "U1001", "amount": 899.00,
                        "item_count": 1, "discount_ratio": 0.05, "created_at": _days_ago(15),
                        "recipient": "张三", "sensitive_goods": 0, "has_coupon": 1,
                        "pay_timeout_ms": 10 * 60 * 1000},
    })
    REFUNDS["U1001"] = []
    COMPLAINTS["U1001"] = []

    # U2002 高疑用户：退款/投诉多、地址高危、金额大、夜间下单、超时支付
    USERS["U2002"] = {
        "user_id": "U2002", "name": "李四", "phone": "13800000002",
        "reg_days": 5, "device_count": 4, "mobile_changed_7d": 1, "risk_region": 1,
    }
    ADDRESSES["U2002"] = [
        {"user_id": "U2002", "province": "新疆维吾尔自治区", "city": "某市",
         "address": "边境自贸区", "used_count": 30, "last_used_at": _days_ago(1), "risk_region": 1},
    ]
    ORDERS.update({
        "U2002-O2001": {"order_id": "U2002-O2001", "user_id": "U2002", "amount": 12800.00,
                        "item_count": 6, "discount_ratio": 0.8, "created_at": _days_ago(1),
                        "recipient": "李四", "sensitive_goods": 1, "has_coupon": 1,
                        "pay_timeout_ms": 120 * 60 * 1000},
    })
    REFUNDS["U2002"] = [
        {"user_id": "U2002", "amount": 3000.00, "created_at": _days_ago(1)},
        {"user_id": "U2002", "amount": 1500.00, "created_at": _days_ago(8)},
        {"user_id": "U2002", "amount": 800.00, "created_at": _days_ago(12)},
    ]
    COMPLAINTS["U2002"] = [
        {"user_id": "U2002", "level": 2, "created_at": _days_ago(2)},
    ]

    # U3003 命中黑名单用户
    USERS["U3003"] = {
        "user_id": "U3003", "name": "王五", "phone": "13800000003",
        "reg_days": 3, "device_count": 2, "mobile_changed_7d": 0, "risk_region": 1,
    }
    ADDRESSES["U3003"] = [
        {"user_id": "U3003", "province": "海南省", "city": "某市",
         "address": "高风险街道 88 号", "used_count": 12, "last_used_at": _days_ago(0), "risk_region": 1},
    ]
    ORDERS.update({
        "U3003-O3001": {"order_id": "U3003-O3001", "user_id": "U3003", "amount": 6600.00,
                        "item_count": 3, "discount_ratio": 0.2, "created_at": _days_ago(0),
                        "recipient": "王五", "sensitive_goods": 1, "has_coupon": 0,
                        "pay_timeout_ms": 90 * 60 * 1000},
    })
    REFUNDS["U3003"] = []
    COMPLAINTS["U3003"] = []
