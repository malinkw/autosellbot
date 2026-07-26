"""Конфигурация structlog и отдельных файловых журналов.

Пять журналов из ТЗ (``bot`` / ``admin`` / ``payments`` / ``security`` / ``errors``)
реализованы как именованные каналы: запись направляется в нужный файл по значению
``channel`` в событии. Так каждый домен пишет в свой ``*.log``, а консоль получает
единый цветной поток в development.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

import structlog

# Имена каналов ⇄ файлы журналов.
LOG_CHANNELS: dict[str, str] = {
    "bot": "bot.log",
    "admin": "admin.log",
    "payments": "payments.log",
    "security": "security.log",
    "errors": "errors.log",
}


class ChannelFileHandler(logging.Handler):
    """Маршрутизирует записи по имени логгера (каналу) в отдельные файлы.

    Канал определяется именем логгера (``get_logger("payments")`` → канал
    ``payments``). Ошибки (уровень ``ERROR`` и выше) дополнительно дублируются
    в ``errors.log``.
    """

    def __init__(self, log_dir: Path) -> None:
        super().__init__()
        log_dir.mkdir(parents=True, exist_ok=True)
        self._handlers: dict[str, logging.Handler] = {}
        for channel, filename in LOG_CHANNELS.items():
            handler = logging.handlers.RotatingFileHandler(
                log_dir / filename,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            handler.setFormatter(self.formatter or logging.Formatter("%(message)s"))
            self._handlers[channel] = handler

    def setFormatter(self, fmt: logging.Formatter | None) -> None:
        super().setFormatter(fmt)
        for handler in getattr(self, "_handlers", {}).values():
            handler.setFormatter(fmt)

    def emit(self, record: logging.LogRecord) -> None:
        channel = record.name if record.name in self._handlers else "bot"
        self._handlers[channel].emit(record)
        if record.levelno >= logging.ERROR and channel != "errors":
            self._handlers["errors"].emit(record)


def setup_logging(*, log_dir: Path, level: str = "INFO", development: bool = False) -> None:
    """Инициализировать structlog + стандартный logging.

    :param log_dir: каталог, куда пишутся файловые журналы.
    :param level: минимальный уровень логирования.
    :param development: при ``True`` включается человекочитаемый цветной вывод.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    numeric_level = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Консольный вывод.
    console_handler = logging.StreamHandler(sys.stdout)
    if development:
        console_renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        console_renderer = structlog.processors.JSONRenderer(ensure_ascii=False)
    console_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                console_renderer,
            ],
        )
    )

    # Файловый вывод (JSON) с маршрутизацией по каналам.
    file_handler = ChannelFileHandler(log_dir)
    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(ensure_ascii=False),
            ],
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(console_handler)
    root.addHandler(file_handler)
    root.setLevel(numeric_level)

    # Приглушаем болтливые сторонние логгеры.
    for noisy in ("aiogram.event", "aiosqlite", "asyncio", "apscheduler.executors"):
        logging.getLogger(noisy).setLevel(max(numeric_level, logging.WARNING))


def get_logger(channel: str = "bot", **initial: Any) -> structlog.stdlib.BoundLogger:
    """Вернуть логгер, привязанный к каналу (``bot`` по умолчанию).

    Использование::

        log = get_logger("payments")
        log.info("topup_confirmed", user_id=..., amount=...)
    """
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(channel)
    return logger.bind(channel=channel, **initial)
