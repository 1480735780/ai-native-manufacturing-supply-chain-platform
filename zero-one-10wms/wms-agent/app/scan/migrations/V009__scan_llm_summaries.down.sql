-- 回滚前先备份数据，避免误删摘要证据。
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'wms_agent'
          AND table_name = 'agent_scan_summaries'
    ) THEN
        EXECUTE 'CREATE TABLE IF NOT EXISTS wms_agent.agent_scan_summaries_v009_backup AS
                 SELECT * FROM wms_agent.agent_scan_summaries';
    END IF;
END
$$;

DROP INDEX IF EXISTS wms_agent.idx_scan_summaries_warehouse;
DROP TABLE IF EXISTS wms_agent.agent_scan_summaries;
