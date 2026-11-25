-- V012 回滚：先整表备份，再删索引与表（与 V007 / V011 的回滚写法一致）。
DO $$
BEGIN
    IF to_regclass('wms_agent.agent_metric_daily') IS NOT NULL THEN
        CREATE TABLE IF NOT EXISTS wms_agent.agent_metric_daily_v012_backup AS
            SELECT * FROM wms_agent.agent_metric_daily;
        DROP INDEX IF EXISTS wms_agent.idx_metric_daily_warehouse_date;
        DROP TABLE wms_agent.agent_metric_daily;
    END IF;
END $$;
