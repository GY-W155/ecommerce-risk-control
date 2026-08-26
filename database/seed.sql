-- =============================================================
-- 示例数据（与 backend/app/seed.py 保持一致的稳定部分）
-- 说明：28 条规则、演示业务数据与历史事件/案件由后端启动时
--       `python -m app.seed` 自动生成（幂等）。此处仅提供黑名单
--       与少量示例事件，方便用 Navicat 等工具直接查看，或手工建库后快速填入。
-- 执行：mysql -uroot -p risk_control < seed.sql
-- =============================================================
USE `risk_control`;

-- 黑名单
INSERT INTO `blacklists` (`blacklist_type`, `blacklist_value`, `remark`, `status`) VALUES
  ('user',    'U3003',            '高风险用户',       1),
  ('address', '高风险街道 88 号', '高危收货地址',     1),
  ('address', '边境自贸区',       '高危地区街道',     1),
  ('phone',   '13800001111',      '高风险手机号',     1);

-- 示例风险事件（关联演示用户）
INSERT INTO `risk_events` (`event_type`, `source_id`, `user_id`, `order_id`, `event_payload_json`, `created_at`) VALUES
  ('order_create', 'seed', 'U1001', 'U1001-O1001', JSON_OBJECT('amount', 259),  NOW()),
  ('order_create', 'seed', 'U2002', 'U2002-O2001', JSON_OBJECT('amount', 12800), NOW());
