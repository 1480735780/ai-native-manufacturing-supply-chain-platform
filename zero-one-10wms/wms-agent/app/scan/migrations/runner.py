"""扫描存储的版本化迁移执行器。

- 迁移脚本放在本目录，命名 ``VNNN__name.up.sql`` / ``VNNN__name.down.sql``；
- ``wms_agent.schema_migrations`` 记录已应用版本（version, description, applied_at）；
- 每个版本在单独事务内执行，失败自动回滚该版本；多实例并发启动用 advisory lock 串行化；
- 库里已应用但目录里不存在的版本视为漂移，拒绝继续；
- ``rollback(version)`` 只允许回滚**已应用且是最新**的版本（按逆序回滚），
  执行 down 脚本并删除版本记录；down 脚本负责先备份再删除（数据可恢复）。

不依赖任何第三方迁移框架；仅用 psycopg。DSN 归一复用 storage.postgres。
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.storage.postgres import normalize_dsn

MIGRATIONS_DIR = Path(__file__).resolve().parent
SCHEMA = "wms_agent"
_VERSION_RE = re.compile(r"^V(\d{3,})__(.+)\.(up|down)\.sql$")
# advisory lock 键（固定值）：同一库上的多个 agent 实例串行迁移
_LOCK_KEY: tuple[int, int] = (20261124, 1)


class MigrationError(RuntimeError):
    """迁移执行失败或被拒绝（未应用 / 非最新 / 版本漂移）。"""


@dataclass(frozen=True)
class Migration:
    version: int
    description: str

    @property
    def name(self) -> str:
        return f"V{self.version:03d}__{self.description}"

    @property
    def up_path(self) -> Path:
        return MIGRATIONS_DIR / f"{self.name}.up.sql"

    @property
    def down_path(self) -> Path:
        return MIGRATIONS_DIR / f"{self.name}.down.sql"


def discover_migrations() -> list[Migration]:
    """扫描目录中的 up 脚本，返回按版本排序的迁移列表。"""
    found: dict[int, Migration] = {}
    for path in MIGRATIONS_DIR.glob("V*.up.sql"):
        match = _VERSION_RE.match(path.name)
        if match is None:
            continue
        version = int(match.group(1))
        found[version] = Migration(version=version, description=match.group(2))
    return [found[v] for v in sorted(found)]


def _connect(dsn: str):
    import psycopg

    return psycopg.connect(normalize_dsn(dsn), connect_timeout=3)


def _ensure_migrations_table(conn: Any) -> None:
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.schema_migrations (
            version     INTEGER PRIMARY KEY,
            description TEXT,
            applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def _ensure_version(conn: Any, version: int, description: str) -> None:
    conn.execute(
        f"""
        INSERT INTO {SCHEMA}.schema_migrations (version, description)
        VALUES (%s, %s) ON CONFLICT (version) DO NOTHING
        """,
        (version, description),
    )


def _applied_on(conn: Any) -> set[int]:
    _ensure_migrations_table(conn)
    rows = conn.execute(f"SELECT version FROM {SCHEMA}.schema_migrations").fetchall()
    return {int(r[0]) for r in rows}


def _applied_sync(dsn: str) -> set[int]:
    with _connect(dsn) as conn:
        applied = _applied_on(conn)
        conn.commit()
    return applied


async def applied_versions(dsn: str) -> set[int]:
    return await asyncio.to_thread(_applied_sync, dsn)


def _apply_all_sync(dsn: str) -> list[int]:
    """应用全部未执行迁移，返回本次应用的版本列表（advisory lock 串行化）。"""
    migrations = discover_migrations()
    known = {m.version for m in migrations}
    done: list[int] = []
    with _connect(dsn) as conn:
        _ensure_migrations_table(conn)
        conn.commit()
        conn.execute("SELECT pg_advisory_lock(%s, %s)", _LOCK_KEY)
        conn.commit()
        try:
            applied = _applied_on(conn)
            conn.commit()
            drifted = sorted(applied - known)
            if drifted:
                raise MigrationError(
                    "applied migrations missing from repository: "
                    + ", ".join(f"V{v:03d}" for v in drifted)
                )
            for migration in migrations:
                if migration.version in applied:
                    continue
                sql = migration.up_path.read_text(encoding="utf-8")
                with conn.transaction():
                    conn.execute(sql)
                    _ensure_version(conn, migration.version, migration.description)
                done.append(migration.version)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s, %s)", _LOCK_KEY)
            conn.commit()
    return done


def apply_migrations_sync(dsn: str) -> list[int]:
    """同步应用全部未执行迁移（供 ensure_schema 在线程内调用）。"""
    return _apply_all_sync(dsn)


async def apply_migrations(dsn: str) -> list[int]:
    """应用全部未执行迁移，返回本次应用的版本列表。"""
    return await asyncio.to_thread(apply_migrations_sync, dsn)


async def apply_pending(dsn: str) -> list[int]:
    """apply_migrations 的别名。"""
    return await apply_migrations(dsn)


def _rollback_one_sync(dsn: str, migration: Migration) -> None:
    sql = migration.down_path.read_text(encoding="utf-8")
    with _connect(dsn) as conn:
        _ensure_migrations_table(conn)
        conn.commit()
        conn.execute("SELECT pg_advisory_lock(%s, %s)", _LOCK_KEY)
        conn.commit()
        try:
            with conn.transaction():
                conn.execute(sql)
                conn.execute(
                    f"DELETE FROM {SCHEMA}.schema_migrations WHERE version = %s",
                    (migration.version,),
                )
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s, %s)", _LOCK_KEY)
            conn.commit()


async def rollback_migration(dsn: str, version: int) -> None:
    """回滚指定版本：须目录中存在、已应用、且是最新已应用版本（按逆序回滚）。"""
    migrations = {m.version: m for m in discover_migrations()}
    migration = migrations.get(version)
    if migration is None:
        raise MigrationError(f"unknown migration version: {version}")
    if not migration.down_path.is_file():
        raise MigrationError(f"no down script for {migration.name}")
    applied = await applied_versions(dsn)
    if version not in applied:
        raise MigrationError(f"{migration.name} is not applied")
    latest = max(applied)
    if version != latest:
        raise MigrationError(
            f"only the latest applied migration can be rolled back "
            f"(latest V{latest:03d}); roll back in reverse order"
        )
    await asyncio.to_thread(_rollback_one_sync, dsn, migration)


async def rollback(dsn: str, version: int) -> None:
    """rollback_migration 的别名。"""
    await rollback_migration(dsn, version)