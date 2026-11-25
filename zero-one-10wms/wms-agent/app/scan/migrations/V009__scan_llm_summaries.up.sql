-- 阶段6：LLM 聚合摘要（只摘要，不判定）。
-- 一次扫描内按 rule_id + warehouse + customer 聚合，一组一行；
-- summary_source 区分模型产出与确定性模板，fallback_reason 记录降级原因。
-- 告警的级别/证据不在此表，LLM 输出也永远不会回写告警。
CREATE TABLE IF NOT EXISTS wms_agent.agent_scan_summaries (
    summary_id        BIGSERIAL PRIMARY KEY,
    scan_id           TEXT NOT NULL,
    trace_id          TEXT,
    rule_id           TEXT NOT NULL,
    rule_version      TEXT,
    warehouse         TEXT NOT NULL,
    customer          TEXT NOT NULL DEFAULT '',
    severity          TEXT NOT NULL,
    object_count      INTEGER NOT NULL,
    severity_counts   JSONB NOT NULL DEFAULT '{}'::jsonb,
    sample_objects    JSONB NOT NULL DEFAULT '[]'::jsonb,
    summary           TEXT NOT NULL,
    summary_source    TEXT NOT NULL,
    fallback_reason   TEXT,
    fallback_detail   TEXT,
    suggested_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    model             TEXT,
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    llm_duration_ms   INTEGER,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_scan_summaries
        UNIQUE (scan_id, rule_id, warehouse, customer),
    CONSTRAINT ck_scan_summaries_source
        CHECK (summary_source IN ('llm', 'template'))
);

CREATE INDEX IF NOT EXISTS idx_scan_summaries_warehouse
    ON wms_agent.agent_scan_summaries (warehouse, rule_id, created_at);
