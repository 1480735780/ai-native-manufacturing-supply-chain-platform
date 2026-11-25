-- 阶段5：评估覆盖记录（自动 resolved 的证据）
-- 记录本次扫描“实际评估过”的对象：命中与未命中都要落库，
-- 只有这样才能判断某个告警对象的异常条件是否真的消失。
CREATE TABLE IF NOT EXISTS wms_agent.agent_scan_evaluated_objects (
    scan_id        TEXT NOT NULL,
    rule_id        TEXT NOT NULL,
    object_type    TEXT NOT NULL,
    object_id      TEXT NOT NULL,
    dimension_hash TEXT NOT NULL,
    warehouse      TEXT NOT NULL,
    evaluated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_scan_evaluated_objects
        UNIQUE (scan_id, rule_id, object_id, dimension_hash)
);

CREATE INDEX IF NOT EXISTS idx_scan_evaluated_objects_rule
    ON wms_agent.agent_scan_evaluated_objects (scan_id, rule_id);

CREATE INDEX IF NOT EXISTS idx_scan_evaluated_objects_warehouse
    ON wms_agent.agent_scan_evaluated_objects (warehouse, rule_id, evaluated_at);
