-- P0: 补齐队列表字段（queued_at/warehouse/dry_run/notification_mode/payload_hash/
-- trace_id + 租约 attempt/lease_owner/leased_at + 执行身份 executor_type/executor_id）。
-- 所有新列可空或带默认值，兼容既有 17 列旧表；可回滚见 .down.sql。

ALTER TABLE wms_agent.agent_scan_runs
    ADD COLUMN IF NOT EXISTS queued_at        TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS warehouse        TEXT,
    ADD COLUMN IF NOT EXISTS dry_run          BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS notification_mode TEXT,
    ADD COLUMN IF NOT EXISTS payload_hash     TEXT,
    ADD COLUMN IF NOT EXISTS trace_id         TEXT,
    ADD COLUMN IF NOT EXISTS attempt          INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS lease_owner      TEXT,
    ADD COLUMN IF NOT EXISTS leased_at        TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS executor_type    TEXT,
    ADD COLUMN IF NOT EXISTS executor_id      TEXT;

-- 队列领取按 queued_at 排序（旧索引按 started_at，兼容保留）
CREATE INDEX IF NOT EXISTS idx_scan_runs_queued
    ON wms_agent.agent_scan_runs(status, queued_at);

-- 通知去重键：同一告警同一事件点只推一次
ALTER TABLE wms_agent.agent_notifications
    ADD COLUMN IF NOT EXISTS dedupe_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_notifications_dedupe
    ON wms_agent.agent_notifications(dedupe_key)
    WHERE dedupe_key IS NOT NULL;
