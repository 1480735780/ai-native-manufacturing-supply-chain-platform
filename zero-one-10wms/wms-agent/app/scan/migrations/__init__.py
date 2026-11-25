"""巡检存储的版本化、可回滚迁移。

约定：
- 迁移文件为 ``VNNN__description.up.sql`` / ``VNNN__description.down.sql``；
- 已应用版本记录在 ``wms_agent.schema_migrations``；
- ``apply_pending`` 按版本顺序逐个在独立事务内执行，失败即回滚该版本，advisory lock 串行化；
- ``rollback`` 只允许回滚“已应用且最新”的版本；down 脚本先备份再删除，数据可找回。
"""

from app.scan.migrations.runner import (
    MIGRATIONS_DIR,
    apply_migrations,
    apply_pending,
    applied_versions,
    rollback,
    rollback_migration,
)

__all__ = [
    "MIGRATIONS_DIR",
    "apply_migrations",
    "apply_pending",
    "applied_versions",
    "rollback",
    "rollback_migration",
]
