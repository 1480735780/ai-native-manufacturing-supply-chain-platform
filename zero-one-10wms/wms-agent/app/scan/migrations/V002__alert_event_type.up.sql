-- 告警事件补齐“事件类型 + 级别变化”：created（新建）/ escalated（升级）/ transition（人工状态转移）。
-- 告警 upsert 把 事件 + 通知 与告警放在同一事务里提交，升级不再只靠通知去重键推断。

ALTER TABLE wms_agent.agent_alert_events
    ADD COLUMN IF NOT EXISTS event_type     TEXT,
    ADD COLUMN IF NOT EXISTS from_severity  TEXT,
    ADD COLUMN IF NOT EXISTS to_severity    TEXT;

-- 历史事件全部是人工状态转移
UPDATE wms_agent.agent_alert_events SET event_type = 'transition' WHERE event_type IS NULL;

CREATE INDEX IF NOT EXISTS idx_agent_alert_events_alert
    ON wms_agent.agent_alert_events(alert_id, event_id);