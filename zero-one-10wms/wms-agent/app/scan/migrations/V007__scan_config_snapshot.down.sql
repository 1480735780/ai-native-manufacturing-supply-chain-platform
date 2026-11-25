-- 回滚 V007：先备份配置快照，再删除新增列；备份表不覆盖已有历史备份。
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'wms_agent' AND table_name = 'agent_scan_runs'
          AND column_name = 'config_snapshot'
    ) THEN
        CREATE TABLE IF NOT EXISTS wms_agent.agent_scan_runs_v007_config_backup AS
        SELECT scan_id, config_snapshot, config_version
        FROM wms_agent.agent_scan_runs;

        ALTER TABLE wms_agent.agent_scan_runs
            DROP COLUMN IF EXISTS config_snapshot,
            DROP COLUMN IF EXISTS config_version;
    END IF;
END $$;
