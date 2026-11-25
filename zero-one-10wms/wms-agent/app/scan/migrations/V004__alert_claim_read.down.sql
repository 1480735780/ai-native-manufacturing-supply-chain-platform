-- 回滚 V004：先备份将要删除的列所在行，再删列（可恢复）。
CREATE TABLE IF NOT EXISTS wms_agent.agent_alerts_v004_backup AS
    SELECT alert_id, acknowledged_by, acknowledged_at, assignee_user_id, claimed_at, routed_to
    FROM wms_agent.agent_alerts;
CREATE TABLE IF NOT EXISTS wms_agent.agent_notifications_v004_backup AS
    SELECT notification_id, recipient_user_id, read_at
    FROM wms_agent.agent_notifications;

DROP INDEX IF EXISTS wms_agent.idx_agent_notifications_user;
DROP INDEX IF EXISTS wms_agent.idx_agent_alerts_cursor;

ALTER TABLE wms_agent.agent_alerts
    DROP COLUMN IF EXISTS acknowledged_by,
    DROP COLUMN IF EXISTS acknowledged_at,
    DROP COLUMN IF EXISTS assignee_user_id,
    DROP COLUMN IF EXISTS claimed_at,
    DROP COLUMN IF EXISTS routed_to;
ALTER TABLE wms_agent.agent_notifications
    DROP COLUMN IF EXISTS recipient_user_id;
