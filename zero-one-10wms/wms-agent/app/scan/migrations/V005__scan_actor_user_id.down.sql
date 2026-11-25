-- 回滚 V005：删除 actor_user_id 列。
ALTER TABLE wms_agent.agent_scan_runs
    DROP COLUMN IF EXISTS actor_user_id;
