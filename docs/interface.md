# 接口说明（电商风控系统）

Base URL：后端 `http://<host>:8000`，所有接口前缀 `/api`。
开发环境前端通过 Vite 代理 `/api` → `http://127.0.0.1:8000`。
接口文档也可直接访问 FastAPI 自带 Swagger：`http://<host>:8000/docs`。

## 风险检查

### POST /api/risk/check
**请求体**：`event_type`、`source_id`、`user_id`、`order_id`（可选），可附带 `event_payload`（金额、收货距离等）。

```json
{
  "event_type": "order_create",
  "source_id": "订单中心",
  "user_id": "U2002",
  "order_id": "U2002-O2001",
  "event_payload": { "amount": 12800, "address_distance_km": 0 }
}
```

**响应**（评分 0~100 / 等级 low·medium·high / 建议 pass·manual_review·reject / 命中规则 / 特征快照）：

```json
{
  "event_id": 11,
  "assessment_id": 12,
  "risk_score": 100.0,
  "risk_level": "high",
  "decision": "reject",
  "rule_hits": [
    { "rule_id": 1, "rule_code": "REJ001", "rule_name": "命中用户黑名单", "hit_score": 90.0, "hit_message": "用户ID或手机号命中黑名单，直接拒绝" }
  ],
  "feature_snapshot": { "user_id": "U2002", "user_new_flag": 1, "order_amount": 12800.0, "order_high_value": 1, "address_region_risk": 1, ... },
  "case_id": 10
}
```

> `case_id` 非空表示该结果已自动创建案件（等级 high 或建议 manual_review / reject）。

### GET /api/risk/assessments/{assessment_id}
**响应**：`risk_score`、`risk_level`、`decision`、`feature_snapshot`、`rule_hits`，并附带事件与用户信息。

## 规则管理

| 方法 | 路径 | 说明 | 请求体 |
|---|---|---|---|
| GET | /api/risk/rules | 规则列表（含命中次数 hit_count） | — |
| POST | /api/risk/rules | 新增规则 | rule_code/rule_name/rule_status/priority/score/condition_json/description |
| POST | /api/risk/rules/update | 更新规则 | 上表字段 + id |
| POST | /api/risk/rules/status | 启停用 | id + rule_status(1/0) |
| POST | /api/risk/rules/delete | 删除 | id |

`condition_json` 结构（支持 AND/OR 嵌套）：

```json
{
  "operator": "AND",
  "conditions": [
    { "feature": "user_refund_count_30d", "op": ">", "value": 3 },
    { "operator": "OR", "conditions": [
        { "feature": "order_amount", "op": ">", "value": 5000 },
        { "feature": "order_sensitive_goods", "op": "=", "value": 1 }
    ]}
  ]
}
```

支持操作符：`>`、`<`、`>=`、`<=`、`=`、`!=`、`contains`。

## 案件审核

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/risk/cases?status=&page=&size= | 案件分页列表 |
| GET | /api/risk/cases/{case_id} | 案件详情（含风险结果、命中规则、特征快照、审核日志） |
| POST | /api/risk/cases/review | 审核：`case_id`、`review_result`(approved/rejected/resolved/reviewing)、`review_remark`、`operator_id` |

## 黑名单

| 方法 | 路径 | 说明 | 请求体 |
|---|---|---|---|
| GET | /api/risk/blacklists?blacklist_type= | 黑名单列表 | — |
| POST | /api/risk/blacklists | 新增 | blacklist_type/blacklist_value/remark |
| POST | /api/risk/blacklists/import | 批量导入 | blacklist_type + text（每行一个或逗号分隔）+ remark |
| POST | /api/risk/blacklists/delete | 删除 | ids: [1,2,3] |

`blacklist_type`：user / order / address / phone / ip。

## 画像与看板

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/risk/users/{user_id}/profile | 用户画像：订单/退款/投诉/地址数、最近风险事件、关联案件 |
| GET | /api/risk/dashboard | 看板：统计卡片、等级分布、7 天趋势、规则命中排行、黑名单命中、事件类型分布 |

## 系统

- `GET /api/health`：探活，返回 `{"status":"ok"}`。
