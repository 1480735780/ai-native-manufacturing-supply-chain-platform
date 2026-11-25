-- 回滚 V011：归档表里只有线上已删除的行，删表即不可恢复，所以先整表备份。
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'wms_agent' AND table_name = 'agent_archive_rows'
    ) THEN
        CREATE TABLE IF NOT EXISTS wms_agent.agent_archive_rows_v011_backup AS
        SELECT * FROM wms_agent.agent_archive_rows;

        DROP INDEX IF EXISTS wms_agent.idx_archive_rows_archived_at;
        DROP INDEX IF EXISTS wms_agent.idx_archive_rows_summary_scan;
        DROP TABLE IF EXISTS wms_agent.agent_archive_rows;
    END IF;
END $$;
