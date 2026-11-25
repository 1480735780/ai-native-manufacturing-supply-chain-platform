-- V012（阶段7.7，ADR-020）：巡检指标日聚合表。
-- 指标接口在 90 天内读实时数据；90 天至 2 年读本表的日聚合（每仓库每天一行，可重复覆盖）。
-- 告警 / 扫描证据归档后，历史指标不再随线上行消失。
CREATE TABLE IF NOT EXISTS wms_agent.agent_metric_daily (
    metric_date DATE         NOT NULL,
    warehouse   TEXT         NOT NULL,
    timezone    TEXT         NOT NULL DEFAULT 'Asia/Shanghai',
    metrics     JSONB        NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_metric_daily PRIMARY KEY (metric_date, warehouse)
);

CREATE INDEX IF NOT EXISTS idx_metric_daily_warehouse_date
    ON wms_agent.agent_metric_daily (warehouse, metric_date);
