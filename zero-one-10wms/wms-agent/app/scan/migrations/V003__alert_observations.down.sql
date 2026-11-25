-- 回滚 V003：删除告警观测表（数据不可恢复，但仅派生数据）。
DROP TABLE IF EXISTS wms_agent.agent_scan_observations;
