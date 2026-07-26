"""Служба резервного копирования и восстановления базы данных."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.exceptions import AppError
from app.logging import get_logger

log = get_logger("bot")


class BackupService:
    """Создание и восстановление дампов PostgreSQL через ``pg_dump``/``pg_restore``.

    Восстановление выполняется одной командой :meth:`restore`.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _env(self) -> dict[str, str]:
        import os

        env = dict(os.environ)
        env["PGPASSWORD"] = self._settings.db.password.get_secret_value()
        return env

    async def create(self) -> Path:
        """Создать сжатый дамп БД. Возвращает путь к файлу."""
        backup_dir = self._settings.app.backup_dir
        await asyncio.to_thread(backup_dir.mkdir, parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        target = backup_dir / f"backup_{self._settings.db.name}_{stamp}.dump"

        proc = await asyncio.create_subprocess_exec(
            "pg_dump",
            "-h",
            self._settings.db.host,
            "-p",
            str(self._settings.db.port),
            "-U",
            self._settings.db.user,
            "-d",
            self._settings.db.name,
            "-F",
            "c",
            "-f",
            str(target),
            env=self._env(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise AppError(f"Ошибка pg_dump: {stderr.decode(errors='ignore')}")
        log.info("backup_created", path=str(target))
        return target

    async def restore(self, dump_path: Path) -> None:
        """Восстановить БД из дампа одной командой."""
        if not await asyncio.to_thread(dump_path.exists):
            raise AppError("Файл резервной копии не найден.")
        proc = await asyncio.create_subprocess_exec(
            "pg_restore",
            "-h",
            self._settings.db.host,
            "-p",
            str(self._settings.db.port),
            "-U",
            self._settings.db.user,
            "-d",
            self._settings.db.name,
            "--clean",
            "--if-exists",
            "--no-owner",
            str(dump_path),
            env=self._env(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode not in (0, 1):  # pg_restore возвращает 1 при предупреждениях
            raise AppError(f"Ошибка pg_restore: {stderr.decode(errors='ignore')}")
        log.info("backup_restored", path=str(dump_path))

    def list_backups(self) -> list[Path]:
        """Список доступных резервных копий (свежие первыми)."""
        backup_dir = self._settings.app.backup_dir
        if not backup_dir.exists():
            return []
        return sorted(backup_dir.glob("backup_*.dump"), reverse=True)
