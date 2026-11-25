-- 阶段7：重试扫描的审计归属。
-- actor_* / trigger=retry 记录「谁点了重试」；retry_of_scan_id 指向被重试的扫描；
-- origin_* 保留根来源（首次触发时的人或服务与触发方式）。非重试记录保持为空。
ALTER TABLE wms_agent.agent_scan_runs
    ADD COLUMN IF NOT EXISTS retry_of_scan_id TEXT,
    ADD COLUMN IF NOT EXISTS origin_actor_type TEXT,
    ADD COLUMN IF NOT EXISTS origin_actor_id TEXT,
    ADD COLUMN IF NOT EXISTS origin_trigger TEXT;

CREATE INDEX IF NOT EXISTS idx_scan_runs_retry_of
    ON wms_agent.agent_scan_runs (retry_of_scan_id)
    WHERE retry_of_scan_id IS NOT NULL;
