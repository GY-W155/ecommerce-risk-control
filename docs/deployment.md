# 部署与运行说明

## 一、整体架构
- 后端：Python 3.8 + FastAPI + SQLAlchemy，端口 `8000`，自带 Swagger `/docs`
- 前端：Vue 3 + Vite + Element Plus + ECharts，开发端口 `5173`，生产由 nginx 托管并反代后端
- 数据库：MySQL 8（docker-compose 中映射宿主机 `3308` → 容器 `3306`）

```
浏览器 ──► nginx:8080 ──► /api 反向代理 ──► FastAPI:8000 ──► MySQL:3306
```

## 二、方式 A：Docker 一键部署（推荐）

前置：已安装并启动 Docker Desktop（本机已有 3306/3307 被占用，故映射 3308）。

```bash
docker compose up --build -d
```

将以三个容器启动 MySQL、后端、前端：
- 前端：http://localhost:8080
- 后端 Swagger：http://localhost:8000/docs

首次启动后端会自动建表并灌入 28 条规则、黑名单、演示业务数据与示例事件（`app/seed.py`）。

## 三、方式 B：本地运行（便于调试）

### 1. 启动 MySQL 容器
```bash
docker compose up -d mysql
```
MySQL 容器就绪后，后端连接配置见 `backend/.env`（默认 127.0.0.1:3308 / risk / risk2024 / risk_control）。

### 2. 启动后端
```bash
cd backend
python -m venv .venv
.venv/Scripts/activate            # Windows；Linux 用 source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed                # 建表 + 种子（幂等，可重复执行）
python run.py                     # 监听 0.0.0.0:8000
```

### 3. 启动前端
```bash
cd frontend
npm install
npm run dev                       # 监听 5173，/api 代理到 127.0.0.1:8000
```
访问 http://localhost:5173。

## 四、完整演示链路（验收脚本）

按以下顺序即可看到「事件接入 → 规则命中 → 评分 → 自动建案 → 人工审核 → 结果回查」的闭环：

1. **风险检查**：进入“风险检查”页，选择事件类型 `order_create`，用户编号 `U2002`（高疑）、订单 `U2002-O2001`，金额 12800 → 提交。
   预期：评分 100、等级「高」、建议「拒绝」，命中多条规则（REJ026 / MAN012 / MAN015 等），并提示“已自动创建案件”。
2. **案件查看**：点击“查看案件”，进入案件详情页，查看风险结果、命中规则、特征快照。
3. **人工审核**：在“审核处理”中选择结论（如 通过 / 拒绝），填写备注与操作人，提交 → 下方“审核日志”出现一条人工审核记录。
4. **规则联动统计**：进入“规则管理”，可看到第 1 步命中的规则 `hit_count` 增加；可尝试新增/编辑/启停用规则，再回检查页复核。
5. **黑名单生效**：进入“黑名单”页，用 `U3003`（已入黑名单）在检查页发起检查 → 命中 REJ001，直接拒绝。
6. **画像与看板**：进入“用户画像”查询 `U2002`，可看到订单/退款/投诉/地址数与关联案件；“运营看板”展示统计卡片、7 天趋势、规则命中排行、黑名单命中。

## 五、接口联调示例

```bash
# 发起一次高风险的创建订单检查
curl -X POST http://127.0.0.1:8000/api/risk/check \
  -H "Content-Type: application/json" \
  -d '{"event_type":"order_create","source_id":"demo","user_id":"U2002","order_id":"U2002-O2001","event_payload":{"amount":12800}}'
```

返回 `risk_level=high`、`decision=reject`、`case_id`，随后对 `case_id` 调用审核接口：

```bash
curl -X POST http://127.0.0.1:8000/api/risk/cases/review \
  -H "Content-Type: application/json" \
  -d '{"case_id":10,"review_result":"approved","review_remark":"材料齐全，放行","operator_id":"auditor_001"}'
```

## 六、数据初始化脚本
- `database/init.sql`：8 张表 DDL（等价于后端建表）
- `database/seed.sql`：黑名单与示例事件（规则由后端 `seed.py` 生成）
