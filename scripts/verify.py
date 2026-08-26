# -*- coding: utf-8 -*-
"""自动化验收脚本：对接口做批量校验并写入 evaluation_results.csv。

用法：
    python scripts/verify.py                 # 默认 http://localhost:8000
    BASE_URL=http://localhost:8001 python scripts/verify.py
    python scripts/verify.py --csv evaluation_results.csv

说明：本项目不涉及 RAG，故用功能验收替代 RAGAS 评估；每次运行会新增少量演示数据。
"""
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
CSV_PATH = os.getenv("CSV_PATH", "evaluation_results.csv")


def http(method, path, body=None, timeout=15):
    url = BASE_URL + path
    data = None
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"detail": raw}
    except Exception as e:
        return 0, {"detail": str(e)}


# ---------------------------------------------------------------------------
# 测试用例：每个返回 (name, passed, actual_summary)
# ---------------------------------------------------------------------------
def run():
    results = []

    def record(name, path, method, pld, expect, ok, actual):
        results.append({
            "name": name, "method": method, "path": path,
            "input": json.dumps(pld, ensure_ascii=False) if pld is not None else "-",
            "expect": expect, "actual": actual, "ok": "PASS" if ok else "FAIL",
        })

    # 1. 健康检查
    s, _ = http("GET", "/api/health")
    record("健康检查", "/api/health", "GET", None, "200", s == 200, f"HTTP {s}")

    # 2. 四类事件风险检查
    for et in ["order_create", "order_pay", "after_sale_apply", "logistics_complaint"]:
        body = {"event_type": et, "source_id": "verify", "user_id": "V-NOR",
                "event_payload": {"amount": 259, "address_distance_km": 0}}
        s, d = http("POST", "/api/risk/check", body)
        ok = s == 200 and isinstance(d.get("risk_score"), (int, float)) and \
             d.get("risk_level") in ("low", "medium", "high") and \
             d.get("decision") in ("pass", "manual_review", "reject") and \
             isinstance(d.get("rule_hits"), list) and isinstance(d.get("feature_snapshot"), dict)
        record(f"四类事件-{et}", "/api/risk/check", "POST", body, "200+结构完整",
               ok, f"HTTP {s} score={d.get('risk_score')} level={d.get('risk_level')} decision={d.get('decision')}")

    # 3. 高风险自动建案（U2002 高疑用户）
    body = {"event_type": "order_create", "source_id": "verify", "user_id": "U2002",
            "order_id": "U2002-O2001", "event_payload": {"amount": 12800, "address_distance_km": 0}}
    s, d = http("POST", "/api/risk/check", body)
    ok = s == 200 and d.get("risk_level") == "high" and d.get("case_id") is not None
    record("高风险自动建案", "/api/risk/check", "POST", body, "level=high 且 case_id 非空",
           ok, f"HTTP {s} score={d.get('risk_score')} level={d.get('risk_level')} case={d.get('case_id')}")

    # 4. 黑名单命中 → 拒绝
    body = {"event_type": "order_create", "source_id": "verify", "user_id": "U3003",
            "order_id": "U3003-O3001", "event_payload": {"amount": 6600}}
    s, d = http("POST", "/api/risk/check", body)
    ok = s == 200 and d.get("decision") == "reject" and \
         d.get("feature_snapshot", {}).get("user_blacklist_hit") == 1
    record("黑名单命中拒绝", "/api/risk/check", "POST", body, "decision=reject 且 user_blacklist_hit=1",
           ok, f"HTTP {s} decision={d.get('decision')} user_bl={d.get('feature_snapshot', {}).get('user_blacklist_hit')}")

    # 5. 规则 CRUD
    cond = {"operator": "AND", "conditions": [{"feature": "order_amount", "op": ">", "value": 99999}]}
    s, d = http("POST", "/api/risk/rules", {"rule_code": "SCR_VERIFY", "rule_name": "verify_tmp",
                 "rule_status": 1, "priority": 1, "score": 10, "condition_json": cond, "description": "verify"})
    rid = d.get("id") if s == 200 else None
    record("规则-新增", "/api/risk/rules", "POST", {"rule_code": "SCR_VERIFY"}, "200 且返回 id", s == 200 and rid, f"HTTP {s} id={rid}")
    s, d = http("POST", "/api/risk/rules/status", {"id": rid, "rule_status": 0})
    record("规则-停用", "/api/risk/rules/status", "POST", {"id": rid}, "rule_status=0", s == 200 and d.get("rule_status") == 0, f"HTTP {s} status={d.get('rule_status')}")
    s, d = http("POST", "/api/risk/rules/update", {"id": rid, "rule_code": "SCR_VERIFY", "rule_name": "verify_tmp",
                 "rule_status": 0, "priority": 1, "score": 20, "condition_json": cond, "description": "verify"})
    record("规则-更新", "/api/risk/rules/update", "POST", {"id": rid}, "score=20", s == 200 and d.get("score") == 20, f"HTTP {s} score={d.get('score')}")
    s, _ = http("POST", "/api/risk/rules/delete", {"id": rid})
    record("规则-删除", "/api/risk/rules/delete", "POST", {"id": rid}, "ok", s == 200, f"HTTP {s}")

    # 6. 黑名单 CRUD / 导入去重
    s, d = http("POST", "/api/risk/blacklists", {"blacklist_type": "phone", "blacklist_value": "13900009999", "remark": "verify"})
    bid = d.get("id") if s == 200 else None
    record("黑名单-新增", "/api/risk/blacklists", "POST", {"blacklist_value": "13900009999"}, "200", s == 200, f"HTTP {s} id={bid}")
    s, d = http("POST", "/api/risk/blacklists/import", {"blacklist_type": "user", "text": "U3003", "remark": "dup"})
    record("黑名单-导入去重", "/api/risk/blacklists/import", "POST", {"text": "U3003"}, "skipped>=1", s == 200 and d.get("skipped", -1) >= 1, f"HTTP {s} {d}")
    s, _ = http("POST", "/api/risk/blacklists/delete", {"ids": [bid]})
    record("黑名单-删除", "/api/risk/blacklists/delete", "POST", {"ids": [bid]}, "ok", s == 200, f"HTTP {s}")

    # 7. 案件分页 / 详情 / 审核 + 日志
    s, d = http("GET", "/api/risk/cases?size=5&page=1")
    record("案件-分页列表", "/api/risk/cases", "GET", {"size": 5}, "200+items", s == 200 and isinstance(d.get("items"), list), f"HTTP {s} total={d.get('total')}")
    cid = d.get("items", [{}])[0].get("id") if d else None
    s, detail = http("GET", f"/api/risk/cases/{cid}")
    record("案件-详情含日志", f"/api/risk/cases/{cid}", "GET", None, "含 review_logs", s == 200 and isinstance(detail.get("review_logs"), list), f"HTTP {s} logs={len(detail.get('review_logs', []))}")
    s, _ = http("POST", "/api/risk/cases/review", {"case_id": cid, "review_result": "approved",
                "review_remark": "verify pass", "operator_id": "verify_script"}) if cid else (0, None)
    s2, d2 = http("GET", f"/api/risk/cases/{cid}") if cid else (0, None)
    actions = [x.get("action_type") for x in (d2 or {}).get("review_logs", [])] if d2 else []
    record("案件-审核+日志", "/api/risk/cases/review", "POST", {"case_id": cid, "review_result": "approved"},
           "status 变更且新增 review 日志", "review" in actions, f"HTTP {s} actions={actions}")

    # 8. 用户画像
    s, d = http("GET", "/api/risk/users/U2002/profile")
    keys = ["order_count", "refund_count", "complaint_count", "address_count", "blacklist_hit"]
    ok = s == 200 and all(k in d for k in keys)
    record("用户画像", "/api/risk/users/{uid}/profile", "GET", None, "五类指标齐全", ok,
           f"HTTP {s} " + json.dumps({k: d.get(k) for k in keys}, ensure_ascii=False))

    # 9. 看板
    s, d = http("GET", "/api/risk/dashboard")
    ok = s == 200 and isinstance(d.get("cards"), list) and len(d.get("trend", [])) >= 1 and isinstance(d.get("rule_rank"), list)
    record("运营看板", "/api/risk/dashboard", "GET", None, "cards/trend/rule_rank", ok,
           f"HTTP {s} cards={len(d.get('cards', []))} trend={len(d.get('trend', []))}")

    return results


def main():
    results = run()
    passed = sum(1 for r in results if r["ok"] == "PASS")
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "method", "path", "input", "expect", "actual", "ok"])
        writer.writeheader()
        writer.writerows(results)
    print(f"\n[验收完成] 通过 {passed}/{len(results)} -> 结果写入 {CSV_PATH}")
    for r in results:
        mark = "[PASS]" if r["ok"] == "PASS" else "[FAIL]"
        print(f"  {mark} {r['name']}: {r['actual']}  期望: {r['expect']}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
