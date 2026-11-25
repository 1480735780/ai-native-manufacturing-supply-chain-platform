-- 阶段7：巡检归档表（ADR-020）。
-- 单表 JSONB 归档：已结案告警、告警事件、扫描摘要。row 为原行的 to_jsonb 快照
-- （列名保持 snake_case），只用于审计回看与摘要接口回落，不参与业务查询；
-- 相比按表复制列结构，不受后续迁移改列影响。
-- 主键 (table_name, row_id) 让归档任务可重入：重复归档只补删除线上行。
CREATE TABLE IF NOT EXISTS wms_agent.agent_archive_rows (
    table_name   TEXT        NOT NULL,
    row_id       TEXT        NOT NULL,
    row          JSONB       NOT NULL,
    archived_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_archive_rows PRIMARY KEY (table_name, row_id)
);

-- 归档保留期清理按 archived_at 扫描
CREATE INDEX IF NOT EXISTS idx_archive_rows_archived_at
    ON wms_agent.agent_archive_rows (archived_at);

-- 摘要接口在线上无行时按 scan_id 回落归档：给这个查找一个索引
CREATE INDEX IF NOT EXISTS idx_archive_rows_summary_scan
    ON wms_agent.agent_archive_rows ((row->>'scan_id'))
    WHERE table_name = 'agent_scan_summaries';
