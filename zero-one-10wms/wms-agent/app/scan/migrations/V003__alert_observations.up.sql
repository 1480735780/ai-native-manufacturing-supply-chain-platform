-- 告警重放观测：同一 (scan_id, trace_id, fingerprint) 只处理一次。
-- 租约失效后 worker 从头重放扫描时，靠这张表保证不重复 occurrence / 事件 / 通知。
CREATE TABLE IF NOT EXISTS wms_agent.agent_scan_observations (
    scan_id     TEXT NOT NULL,
    trace_id    TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    alert_id    BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (scan_id, trace_id, fingerprint)
);
