"""PostgreSQL trace 持久化（独立 schema `wms_agent`）。

约定（见实施方案 F-012）：
- 只存审计摘要：用户标识、query、answer、状态、时间、耗时、工具名、脱敏参数、行数、错误码、digest；
- 不存 JWT 原文、不存完整工具结果；
- PG 不可用时服务照常启动，问数照常完成，响应里 `persisted=false`；
- 持久化失败不影响问数结果。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import psycopg

from app.storage.store import TraceStore

logger = logging.getLogger(__name__)

SCHEMA = "wms_agent"

DDL_STATEMENTS: tuple[str, ...] = (
    f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}",
    f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA}.agent_sessions (
        session_id     TEXT PRIMARY KEY,
        user_id        TEXT,
        user_name      TEXT,
        created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
        last_query_at  TIMESTAMPTZ
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA}.agent_traces (
        trace_id     TEXT PRIMARY KEY,
        session_id   TEXT,
        user_id      TEXT,
        user_name    TEXT,
        query        TEXT,
        answer       TEXT,
        status       TEXT,
        tool_rounds  INTEGER,
        duration_ms  INTEGER,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA}.agent_tool_calls (
        id             BIGSERIAL PRIMARY KEY,
        trace_id       TEXT NOT NULL REFERENCES {SCHEMA}.agent_traces(trace_id) ON DELETE CASCADE,
        seq            INTEGER,
        tool           TEXT,
        params         TEXT,
        status         TEXT,
        row_count      INTEGER,
        duration_ms    INTEGER,
        endpoint       TEXT,
        error_code     TEXT,
        retryable      BOOLEAN,
        attempt        INTEGER,
        result_digest  TEXT
    )
    """,
    f"CREATE INDEX IF NOT EXISTS idx_agent_tool_calls_trace ON {SCHEMA}.agent_tool_calls(trace_id)",
    f"CREATE INDEX IF NOT EXISTS idx_agent_traces_session ON {SCHEMA}.agent_traces(session_id)",
)


def normalize_dsn(dsn: str) -> str:
    """把 `postgresql+psycopg://` 归一成 psycopg 能吃的 `postgresql://`。"""
    text = (dsn or "").strip()
    for prefix in ("postgresql+psycopg://", "postgres+psycopg://"):
        if text.startswith(prefix):
            return "postgresql://" + text[len(prefix) :]
    return text


def _text(value: Any) -> str | None:
    """把任意值转成可入库的字符串（None 保持 None）。"""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


class PostgresTraceStore:
    """基于 PostgreSQL 的 trace 存储。"""

    def __init__(self, dsn: str, *, connect_timeout: int = 3, statement_timeout_ms: int = 3000) -> None:
        self._dsn = normalize_dsn(dsn)
        self._connect_timeout = connect_timeout
        self._statement_timeout_ms = statement_timeout_ms

    # ---------- 连接与建表 ----------

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(
            self._dsn,
            connect_timeout=self._connect_timeout,
            options=f"-c statement_timeout={self._statement_timeout_ms}",
        )

    def _ensure_schema_sync(self) -> None:
        with self._connect() as conn:
            for statement in DDL_STATEMENTS:
                conn.execute(statement)
            conn.commit()

    async def ensure_schema(self) -> bool:
        """建 schema 与 3 张表；失败只记录日志，不影响服务启动。"""
        try:
            await asyncio.to_thread(self._ensure_schema_sync)
            return True
        except Exception as exc:  # noqa: BLE001 - 建表失败不阻塞启动
            logger.warning("ensure schema failed: %s", type(exc).__name__)
            return False

    # ---------- 写入 ----------

    def _save_sync(self, summary: dict[str, Any]) -> bool:
        trace_id = str(summary.get("traceId") or "")
        if not trace_id:
            return False
        session_id = str(summary.get("sessionId") or "")
        tool_calls = summary.get("toolCalls") or []

        with self._connect() as conn:
            if session_id:
                conn.execute(
                    f"""
                    INSERT INTO {SCHEMA}.agent_sessions (session_id, user_id, user_name, last_query_at)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (session_id) DO UPDATE
                    SET last_query_at = now(), user_id = EXCLUDED.user_id, user_name = EXCLUDED.user_name
                    """,
                    (session_id, _text(summary.get("userId")), _text(summary.get("userName"))),
                )
            conn.execute(
                f"""
                INSERT INTO {SCHEMA}.agent_traces
                    (trace_id, session_id, user_id, user_name, query, answer, status, tool_rounds, duration_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (trace_id) DO UPDATE
                SET answer = EXCLUDED.answer, status = EXCLUDED.status
                """,
                (
                    trace_id,
                    session_id or None,
                    _text(summary.get("userId")),
                    _text(summary.get("userName")),
                    _text(summary.get("query")),
                    _text(summary.get("answer")),
                    _text(summary.get("status")),
                    summary.get("toolRounds"),
                    summary.get("durationMs"),
                ),
            )
            # 同一 trace 重复保存时先清掉旧的工具调用行，保证幂等
            conn.execute(f"DELETE FROM {SCHEMA}.agent_tool_calls WHERE trace_id = %s", (trace_id,))
            for seq, call in enumerate(tool_calls):
                conn.execute(
                    f"""
                    INSERT INTO {SCHEMA}.agent_tool_calls
                        (trace_id, seq, tool, params, status, row_count, duration_ms, endpoint,
                         error_code, retryable, attempt, result_digest)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        trace_id,
                        seq,
                        _text(call.get("tool")),
                        _text(call.get("params")),
                        _text(call.get("status")),
                        call.get("rowCount"),
                        call.get("durationMs"),
                        _text(call.get("endpoint")),
                        _text(call.get("errorCode")),
                        call.get("retryable"),
                        call.get("attempt"),
                        _text(call.get("resultDigest")),
                    ),
                )
            conn.commit()
        return True

    async def save(self, summary: dict[str, Any]) -> bool:
        """保存摘要；失败返回 False（调用方据此置 `persisted=false`）。"""
        try:
            return await asyncio.to_thread(self._save_sync, summary)
        except Exception as exc:  # noqa: BLE001 - 持久化失败不影响问数
            logger.warning("save trace failed: %s", type(exc).__name__)
            return False

    # ---------- 查询 ----------

    def _get_sync(self, trace_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT trace_id, session_id, user_id, user_name, query, answer, status,
                       tool_rounds, duration_ms, created_at
                FROM {SCHEMA}.agent_traces WHERE trace_id = %s
                """,
                (trace_id,),
            ).fetchone()
            if row is None:
                return None
            tool_rows = conn.execute(
                f"""
                SELECT tool, params, status, row_count, duration_ms, endpoint,
                       error_code, retryable, attempt, result_digest
                FROM {SCHEMA}.agent_tool_calls WHERE trace_id = %s ORDER BY seq
                """,
                (trace_id,),
            ).fetchall()

        tool_calls = []
        for tool_row in tool_rows:
            raw_params = tool_row[1]
            try:
                params = json.loads(raw_params) if raw_params else None
            except (TypeError, ValueError):
                params = None
            tool_calls.append(
                {
                    "tool": tool_row[0],
                    "params": params,
                    "status": tool_row[2],
                    "rowCount": tool_row[3],
                    "durationMs": tool_row[4],
                    "endpoint": tool_row[5],
                    "errorCode": tool_row[6],
                    "retryable": tool_row[7],
                    "attempt": tool_row[8],
                    "resultDigest": tool_row[9],
                }
            )

        return {
            "traceId": row[0],
            "sessionId": row[1],
            "userId": row[2],
            "userName": row[3],
            "query": row[4],
            "answer": row[5],
            "status": row[6],
            "toolRounds": row[7],
            "durationMs": row[8],
            "createdAt": row[9].isoformat() if row[9] else None,
            "toolCalls": tool_calls,
        }

    async def get(self, trace_id: str) -> dict[str, Any] | None:
        """按 traceId 取摘要；查不到返回 None。"""
        try:
            return await asyncio.to_thread(self._get_sync, trace_id)
        except Exception as exc:  # noqa: BLE001 - 查询失败按“未命中”处理
            logger.warning("query trace failed: %s", type(exc).__name__)
            return None


__all__ = ["SCHEMA", "DDL_STATEMENTS", "PostgresTraceStore", "normalize_dsn"]
