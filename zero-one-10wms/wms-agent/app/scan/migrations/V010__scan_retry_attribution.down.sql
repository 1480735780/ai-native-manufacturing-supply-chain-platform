-- 回滚 V010：先备份归属字段，再删除新增列；备份表不覆盖已有历史备份。
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'wms_agent' AND table_name = 'agent_scan_runs'
          AND column_name = 'retry_of_scan_id'
    ) THEN
        CREATE TABLE IF NOT EXISTS wms_agent.agent_scan_runs_v010_retry_backup AS
        SELECT scan_id, retry_of_scan_id, origin_actor_type, origin_actor_id, origin_trigger
        FROM wms_agent.agent_scan_runs;

        DROP INDEX IF EXISTS wms_agent.idx_scan_runs_retry_of;
        ALTER TABLE wms_agent.agent_scan_runs
            DROP COLUMN IF EXISTS retry_of_scan_id,
            DROP COLUMN IF EXISTS origin_actor_type,
            DROP COLUMN IF EXISTS origin_actor_id,
            DROP COLUMN IF EXISTS origin_trigger;
    END IF;
END $$;
