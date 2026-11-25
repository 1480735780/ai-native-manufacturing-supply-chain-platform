-- 阶段1：告警确认/认领审计 + 通知稳定接收人。
-- 全部 ADD COLUMN IF NOT EXISTS，旧行默认 NULL，向后兼容。
-- acknowledged_*: ack 只记录"谁在何时确认"，不改 assignee（认领是独立动作）。
-- assignee_user_id/claimed_at: 认领人（稳定 user_id）与认领时间。
-- routed_to: 告警实际路由到的接收人（展示名列表，逗号分隔）。
ALTER TABLE wms_agent.agent_alerts
    ADD COLUMN IF NOT EXISTS acknowledged_by   TEXT,
    ADD COLUMN IF NOT EXISTS acknowledged_at  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS assignee_user_id TEXT,
    ADD COLUMN IF NOT EXISTS claimed_at       TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS routed_to        TEXT;

-- 通知按稳定 user_id 隔离：recipient 是展示名，recipient_user_id 是 JWT id claim。
-- 已读状态属于这一行（一个接收人一条通知记录），故 read_at 天然按用户隔离。
ALTER TABLE wms_agent.agent_notifications
    ADD COLUMN IF NOT EXISTS recipient_user_id TEXT;

-- 游标分页：lastSeenAt + alertId 复合键，避免同时间戳漏行/重复。
CREATE INDEX IF NOT EXISTS idx_agent_alerts_cursor
    ON wms_agent.agent_alerts(last_seen_at DESC, alert_id DESC);
-- 通知已读查询：按稳定用户 + 已读时间。
CREATE INDEX IF NOT EXISTS idx_agent_notifications_user
    ON wms_agent.agent_notifications(recipient_user_id, read_at, notification_id DESC);
