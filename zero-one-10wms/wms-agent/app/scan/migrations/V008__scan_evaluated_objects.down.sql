-- 回滚前先备份数据，避免误删评估覆盖证据。
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'wms_agent'
          AND table_name = 'agent_scan_evaluated_objects'
    ) THEN
        EXECUTE 'CREATE TABLE IF NOT EXISTS wms_agent.agent_scan_evaluated_objects_v008_backup AS
                 SELECT * FROM wms_agent.agent_scan_evaluated_objects';
    END IF;
END
$$;

DROP INDEX IF EXISTS wms_agent.idx_scan_evaluated_objects_warehouse;
DROP INDEX IF EXISTS wms_agent.idx_scan_evaluated_objects_rule;
DROP TABLE IF EXISTS wms_agent.agent_scan_evaluated_objects;
