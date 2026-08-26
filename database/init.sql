-- =============================================================
-- 电商风险控制系统 - 数据库初始化脚本（MySQL 8）
-- 建库 + 建表（8 张），与 backend/app/models.py 一一对应
-- 执行：mysql -uroot -p < init.sql
-- =============================================================

CREATE DATABASE IF NOT EXISTS `risk_control` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `risk_control`;

-- 1. 风险事件表
CREATE TABLE IF NOT EXISTS `risk_events` (
  `id`                 BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  `event_type`         VARCHAR(50)  NOT NULL COMMENT '事件类型',
  `source_id`          VARCHAR(64)  NOT NULL COMMENT '事件来源标识',
  `user_id`            VARCHAR(64)  NOT NULL COMMENT '用户编号',
  `order_id`           VARCHAR(64)  DEFAULT NULL COMMENT '订单编号',
  `event_payload_json` JSON         DEFAULT NULL COMMENT '原始入参扩展',
  `created_at`         DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_event_type` (`event_type`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_order_id` (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='风险事件表';

-- 2. 风险评估结果表
CREATE TABLE IF NOT EXISTS `risk_assessments` (
  `id`                 BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
  `event_id`           BIGINT      NOT NULL COMMENT '关联事件ID',
  `risk_score`         DOUBLE      NOT NULL DEFAULT 0 COMMENT '风险评分0-100',
  `risk_level`         VARCHAR(10) NOT NULL DEFAULT 'low' COMMENT 'low/medium/high',
  `decision`           VARCHAR(20) NOT NULL DEFAULT 'pass' COMMENT 'pass/manual_review/reject',
  `assessment_status`  VARCHAR(20) NOT NULL DEFAULT 'completed' COMMENT '评估状态',
  `created_at`         DATETIME    DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_event_id` (`event_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='风险评估结果表';

-- 3. 特征快照表
CREATE TABLE IF NOT EXISTS `feature_snapshots` (
  `id`            BIGINT   NOT NULL AUTO_INCREMENT COMMENT '主键',
  `assessment_id` BIGINT   NOT NULL COMMENT '关联评估ID',
  `feature_json`  JSON     NOT NULL COMMENT '特征键值对快照',
  `created_at`    DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_assessment_id` (`assessment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='特征快照表';

-- 4. 风险规则表
CREATE TABLE IF NOT EXISTS `risk_rules` (
  `id`             BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  `rule_code`      VARCHAR(64)  NOT NULL COMMENT '规则编码',
  `rule_name`      VARCHAR(128) NOT NULL COMMENT '规则名称',
  `rule_status`    INT          NOT NULL DEFAULT 1 COMMENT '1启用/0停用',
  `priority`       INT          NOT NULL DEFAULT 0 COMMENT '优先级，大者优先',
  `score`          DOUBLE       NOT NULL DEFAULT 0 COMMENT '命中分值',
  `condition_json` JSON         NOT NULL COMMENT '条件JSON(支持AND/OR嵌套)',
  `description`    VARCHAR(255) DEFAULT NULL COMMENT '命中描述',
  `updated_at`     DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_rule_code` (`rule_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='风险规则表';

-- 5. 规则命中记录表
CREATE TABLE IF NOT EXISTS `rule_hits` (
  `id`            BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
  `assessment_id` BIGINT      NOT NULL COMMENT '关联评估ID',
  `rule_id`       BIGINT      NOT NULL COMMENT '关联规则ID',
  `hit_score`     DOUBLE      NOT NULL DEFAULT 0 COMMENT '命中分值',
  `hit_message`   VARCHAR(255) DEFAULT NULL COMMENT '命中原因',
  `created_at`    DATETIME    DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_assessment_id` (`assessment_id`),
  KEY `idx_rule_id` (`rule_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='规则命中记录表';

-- 6. 风险案件表
CREATE TABLE IF NOT EXISTS `risk_cases` (
  `id`            BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
  `assessment_id` BIGINT      NOT NULL COMMENT '关联评估ID',
  `user_id`       VARCHAR(64) NOT NULL COMMENT '关联用户',
  `order_id`      VARCHAR(64) DEFAULT NULL COMMENT '关联订单',
  `risk_level`    VARCHAR(10) NOT NULL DEFAULT 'high' COMMENT '风险等级',
  `case_status`   VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending/reviewing/approved/rejected/resolved',
  `reviewer_id`   VARCHAR(64) DEFAULT NULL COMMENT '审核人',
  `review_result` VARCHAR(255) DEFAULT NULL COMMENT '审核结论/备注',
  `created_at`    DATETIME    DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`    DATETIME    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_assessment_id` (`assessment_id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='风险案件表';

-- 7. 黑名单表
CREATE TABLE IF NOT EXISTS `blacklists` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  `blacklist_type` VARCHAR(20) NOT NULL COMMENT 'user/order/address/phone/ip',
  `blacklist_value` VARCHAR(128) NOT NULL COMMENT '命中值',
  `remark`        VARCHAR(255) DEFAULT NULL COMMENT '备注',
  `status`        INT          NOT NULL DEFAULT 1 COMMENT '1生效/0失效',
  `created_at`    DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_value` (`blacklist_value`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='黑名单表';

-- 8. 审核日志表
CREATE TABLE IF NOT EXISTS `review_logs` (
  `id`            BIGINT      NOT NULL AUTO_INCREMENT COMMENT '主键',
  `case_id`       BIGINT      NOT NULL COMMENT '关联案件ID',
  `operator_id`   VARCHAR(64) DEFAULT NULL COMMENT '操作人',
  `action_type`   VARCHAR(30) NOT NULL COMMENT 'auto_create/review/status_change',
  `action_remark` TEXT        DEFAULT NULL COMMENT '操作说明',
  `created_at`    DATETIME    DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_case_id` (`case_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审核日志表';
