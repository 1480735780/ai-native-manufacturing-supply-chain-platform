-- 阶段3：待办积压观测样本（BACKLOG-GROWTH 的历史基线）。
-- 只有完整快照（非 partial、非超时、四队列齐全）才落样本；partial / 快照失败 / 基线缺失不落样本。
-- 唯一键 (scan_id, queue_type)：同一扫描重复回放不重复落样本（租约失效后重试也只保留一份）。
-- 基线查询按 rule_version 过滤（规则升版不混用旧基线），并按 (observed_at, observation_id) 稳定排序。
CREATE TABLE IF NOT EXISTS wms_agent.agent_backlog_observations (
    observation_id BIGSERIAL PRIMARY KEY,
    scan_id        TEXT NOT NULL,
    warehouse      TEXT NOT NULL,
    queue_type     TEXT NOT NULL,
    value          NUMERIC(18,4) NOT NULL CHECK (value >= 0),
    observed_at    TIMESTAMPTZ NOT NULL,
    rule_version   TEXT NOT NULL,
    source_status  TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_backlog_observations_scan_queue UNIQUE (scan_id, queue_type)
);

CREATE INDEX IF NOT EXISTS idx_backlog_observations_baseline
    ON wms_agent.agent_backlog_observations (warehouse, queue_type, rule_version, observed_at, observation_id);
