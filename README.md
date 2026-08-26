# 电商风险控制系统

面向电商业务的实时风险控制平台，覆盖 **风险识别 → 规则匹配 → 评分决策 → 案件生成 → 人工审核 → 处置留痕 → 结果回查** 的完整闭环。

## 功能概览

- **检测能力**：事件接入、特征计算（30+ 特征）、规则匹配（28 条规则）、风险评分
- **处置能力**：案件自动生成、案件审核、黑名单管理、用户画像
- **管理能力**：规则增删改查、命中记录查询、审核日志记录、统计报表、运营看板

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.8 · FastAPI · SQLAlchemy 2.x · Pydantic v2 · PyMySQL |
| 前端 | Vue 3 · Vite · Element Plus · ECharts · Pinia · Vue Router |
| 数据库 | MySQL 8（docker-compose） |
| 部署 | Docker Compose（MySQL + 后端 + 前端 nginx） |

## 目录结构

```
├── backend/            FastAPI 后端与核心引擎
│   ├── app/
│   │   ├── main.py     应用入口（CORS、路由、启动初始化）
│   │   ├── config.py   配置（MySQL 连接、评分阈值）
│   │   ├── models.py   8 张表 ORM
│   │   ├── schemas.py  请求/响应模型
│   │   ├── seed.py     建表 + 种子（28 规则、黑名单、演示数据）
│   │   └── services/   特征/规则/决策/编排引擎
│   └── run.py          本地启动脚本
├── frontend/           Vue3 前端（7 个页面）
├── database/           建表与示例 SQL
├── docs/               接口说明、部署文档
├── docker-compose.yml
└── Dockerfile.backend / Dockerfile.frontend
```

## 核心数仓（8 张表）

`risk_events`、`risk_assessments`、`feature_snapshots`、`risk_rules`、`rule_hits`、`risk_cases`、`blacklists`、`review_logs`。

## 快速开始

### Docker 一键启动
```bash
docker compose up --build -d
# 前端 http://localhost:8080   Swagger http://localhost:8000/docs
```

### 本地运行
见 [docs/deployment.md](docs/deployment.md)（MySQL 容器 → 后端 → 前端；亦含完整演示链路与接口联调示例）。

## 关键规则示例
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

## 接口文档
见 [docs/interface.md](docs/interface.md)，或访问 `/docs` 查看 Swagger。

## 权限与认证
当前版本为更好地演示核心业务闭环，**未强制鉴权**（接口无登录校验），三种角色（风控审核员 / 风控管理员 / 数据查看人）为预留设计，后续可按需接入 JWT 或 API-Key 门槛。

## 自动化验收
`python scripts/verify.py` 对全部接口做批量校验并写入 `evaluation_results.csv`（本项目不涉及 RAG，故用功能验收替代 RAGAS 评估）。

## 演示账号 / 数据
- 演示用户：`U1001`（正常）、`U2002`（高疑，退款/投诉多、高危地址）、`U3003`（命中黑名单）
- 26+ 业务事件：`order_create`、`order_pay`、`after_sale_apply`、`logistics_complaint`
