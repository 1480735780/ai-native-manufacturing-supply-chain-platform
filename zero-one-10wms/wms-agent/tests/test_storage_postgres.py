"""F-012 trace 持久化测试。

- 单元部分始终执行：DSN 归一化、降级行为；
- 集成部分需要真实 PostgreSQL：设置 `WMS_AGENT_TEST_DB_URL` 后执行，
  例如 `postgresql://postgres:123456@127.0.0.1:5432/ragent`。
"""

from __future__ import annotations

import os

import pytest

from app.storage.postgres import DDL_STATEMENTS, SCHEMA, PostgresTraceStore, normalize_dsn


def _test_dsn() -> str | None:
    return os.environ.get("WMS_AGENT_TEST_DB_URL") or None


SUMMARY = {
    "traceId": "t-20260101000000-abcdef",
    "sessionId": "s-20260101000000-abcdef",
    "userId": "u-1",
    "userName": "tester",
    "query": "查询 A01 库位库存",
    "answer": "共 12 条",
    "status": "success",
    "toolRounds": 1,
    "durationMs": 42,
    "createdAt": "2026-01-01T00:00:00+08:00",
    "toolCalls": [
        {
            "tool": "STOCK-QUERY",
            "params": {"page_index": 1, "page_size": 20},
            "status": "success",
            "rowCount": 12,
            "durationMs": 30,
            "endpoint": "/stock/inventory-query/query-all",
            "errorCode": None,
            "retryable": False,
            "attempt": 1,
            "resultDigest": "sha256:0123456789abcdef",
        }
    ],
}


class TestNormalizeDsn:
    def test_strips_sqlalchemy_scheme(self):
        assert (
            normalize_dsn("postgresql+psycopg://postgres:postgres@127.0.0.1:5432/ragent")
            == "postgresql://postgres:postgres@127.0.0.1:5432/ragent"
        )

    def test_keeps_plain_scheme(self):
        assert normalize_dsn("postgresql://u:p@h:5432/db") == "postgresql://u:p@h:5432/db"

    def test_empty_is_empty(self):
        assert normalize_dsn("") == ""


class TestDegradedMode:
    async def test_unreachable_database_returns_false(self):
        """PG 不可用时 save 返回 False，不抛异常。"""
        store = PostgresTraceStore("postgresql://postgres:postgres@127.0.0.1:5599/ragent", connect_timeout=1)
        assert await store.save(SUMMARY) is False

    async def test_unreachable_database_returns_none(self):
        store = PostgresTraceStore("postgresql://postgres:postgres@127.0.0.1:5599/ragent", connect_timeout=1)
        assert await store.get("t-not-exist") is None


@pytest.mark.skipif(_test_dsn() is None, reason="未设置 WMS_AGENT_TEST_DB_URL，跳过真实 PG 集成测试")
class TestRealPostgres:
    async def test_schema_tables_created_and_trace_roundtrip(self):
        store = PostgresTraceStore(_test_dsn())
        assert await store.ensure_schema() is True

        import psycopg

        with psycopg.connect(_test_dsn()) as conn:
            rows = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = %s ORDER BY table_name",
                (SCHEMA,),
            ).fetchall()
        table_names = {row[0] for row in rows}
        # 同一 schema 自 F-015 起还有巡检四表 + schema_migrations；这里只断言 trace 三表存在
        assert {"agent_sessions", "agent_tool_calls", "agent_traces"} <= table_names

        assert await store.save(SUMMARY) is True

        loaded = await store.get(SUMMARY["traceId"])
        assert loaded is not None
        assert loaded["query"] == SUMMARY["query"]
        assert loaded["answer"] == SUMMARY["answer"]
        assert loaded["status"] == "success"
        assert loaded["toolRounds"] == 1
        assert loaded["durationMs"] == 42
        assert loaded["userName"] == "tester"
        assert len(loaded["toolCalls"]) == 1
        call = loaded["toolCalls"][0]
        assert call["tool"] == "STOCK-QUERY"
        assert call["rowCount"] == 12
        assert call["params"] == {"page_index": 1, "page_size": 20}
        assert call["resultDigest"] == "sha256:0123456789abcdef"

        # 清理，避免污染测试库
        with psycopg.connect(_test_dsn()) as conn:
            conn.execute(f"DELETE FROM {SCHEMA}.agent_traces WHERE trace_id = %s", (SUMMARY["traceId"],))
            conn.execute(f"DELETE FROM {SCHEMA}.agent_sessions WHERE session_id = %s", (SUMMARY["sessionId"],))
            conn.commit()

    async def test_missing_trace_returns_none(self):
        store = PostgresTraceStore(_test_dsn())
        assert await store.ensure_schema() is True
        assert await store.get("t-not-exist-9999") is None

    async def test_save_is_idempotent(self):
        store = PostgresTraceStore(_test_dsn())
        assert await store.ensure_schema() is True
        assert await store.save(SUMMARY) is True
        assert await store.save(SUMMARY) is True

        import psycopg

        with psycopg.connect(_test_dsn()) as conn:
            count = conn.execute(
                f"SELECT count(*) FROM {SCHEMA}.agent_traces WHERE trace_id = %s", (SUMMARY["traceId"],)
            ).fetchone()[0]
            tool_count = conn.execute(
                f"SELECT count(*) FROM {SCHEMA}.agent_tool_calls WHERE trace_id = %s", (SUMMARY["traceId"],)
            ).fetchone()[0]
            conn.execute(f"DELETE FROM {SCHEMA}.agent_traces WHERE trace_id = %s", (SUMMARY["traceId"],))
            conn.execute(f"DELETE FROM {SCHEMA}.agent_sessions WHERE session_id = %s", (SUMMARY["sessionId"],))
            conn.commit()
        assert count == 1
        assert tool_count == 1


def test_ddl_covers_three_tables():
    joined = " ".join(DDL_STATEMENTS)
    assert "agent_sessions" in joined
    assert "agent_traces" in joined
    assert "agent_tool_calls" in joined
