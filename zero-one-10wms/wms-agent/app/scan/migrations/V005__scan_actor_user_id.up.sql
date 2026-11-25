-- 阶段1：扫描记录保留发起用户的稳定 user_id。
-- 异步执行时 worker 只有服务账号身份，无法从令牌取回发起人的 id；
-- 落库后 in_app 通知才能按稳定 user_id 隔离已读状态。
ALTER TABLE wms_agent.agent_scan_runs
    ADD COLUMN IF NOT EXISTS actor_user_id TEXT;
