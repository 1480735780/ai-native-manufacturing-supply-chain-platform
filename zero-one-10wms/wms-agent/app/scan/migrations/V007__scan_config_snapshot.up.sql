-- 阶段4：每次扫描冻结的非密生效配置快照与配置版本。
-- 历史终态记录允许为空；新入队记录必须写入，worker 缺快照时失败而不回退当前 YAML。
ALTER TABLE wms_agent.agent_scan_runs
    ADD COLUMN IF NOT EXISTS config_snapshot TEXT,
    ADD COLUMN IF NOT EXISTS config_version TEXT;
