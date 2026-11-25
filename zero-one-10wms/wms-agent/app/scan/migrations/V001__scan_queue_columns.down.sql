-- 回滚 V001：恢复 17 列旧表结构。
-- 先把要删的列备份到 wms_agent.*_v001_backup（覆盖上一次备份），再 DROP：
-- 结构可回滚且数据可找回；确认不需要后由人工 DROP 备份表。

DROP TABLE IF EXISTS wms_agent.agent_scan_runs_v001_backup;
CREATE TABLE wms_agent.agent_scan_runs_v001_backup AS
SELECT scan_id, queued_at, warehouse, dry_run, notification_mode, payload_hash,
       trace_id, attempt, lease_owner, leased_at, executor_type, executor_id
FROM wms_agent.agent_scan_runs;

DROP TABLE IF EXISTS wms_agent.agent_notifications_v001_backup;
CREATE TABLE wms_agent.agent_notifications_v001_backup AS
SELECT notification_id, dedupe_key FROM wms_agent.agent_notifications;

DROP INDEX IF EXISTS wms_agent.uq_agent_notifications_dedupe;
DROP INDEX IF EXISTS wms_agent.idx_scan_runs_queued;

ALTER TABLE wms_agent.agent_notifications
    DROP COLUMN IF EXISTS dedupe_key;

ALTER TABLE wms_agent.agent_scan_runs
    DROP COLUMN IF EXISTS executor_id,
    DROP COLUMN IF EXISTS executor_type,
    DROP COLUMN IF EXISTS leased_at,
    DROP COLUMN IF EXISTS lease_owner,
    DROP COLUMN IF EXISTS attempt,
    DROP COLUMN IF EXISTS trace_id,
    DROP COLUMN IF EXISTS payload_hash,
    DROP COLUMN IF EXISTS notification_mode,
    DROP COLUMN IF EXISTS dry_run,
    DROP COLUMN IF EXISTS warehouse,
    DROP COLUMN IF EXISTS queued_at;