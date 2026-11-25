-- 回滚 V002：恢复 agent_alert_events 的 9 列结构。
-- 先备份事件类型与级别变化（覆盖上一次备份），再 DROP；数据可找回。

DROP TABLE IF EXISTS wms_agent.agent_alert_events_v002_backup;
CREATE TABLE wms_agent.agent_alert_events_v002_backup AS
SELECT event_id, event_type, from_severity, to_severity FROM wms_agent.agent_alert_events;

DROP INDEX IF EXISTS wms_agent.idx_agent_alert_events_alert;

ALTER TABLE wms_agent.agent_alert_events
    DROP COLUMN IF EXISTS to_severity,
    DROP COLUMN IF EXISTS from_severity,
    DROP COLUMN IF EXISTS event_type;