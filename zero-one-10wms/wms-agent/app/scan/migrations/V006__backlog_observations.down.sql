-- 回滚 V006：删除待办积压观测表（仅派生数据，可由后续完整扫描重建基线）。
DROP TABLE IF EXISTS wms_agent.agent_backlog_observations;
