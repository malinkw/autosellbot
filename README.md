# AutoSale — Telegram-бот магазина

Промышленный Telegram-бот интернет-магазина на **aiogram 3** с чистой архитектурой,
гранулярной системой прав (RBAC), кошельком, диспутами, отзывами и полноценной
административной панелью.

## Возможности

- **Пользователи**: онбординг с выбором уникального ника, профиль (ID, баланс, заказы,
  отзывы, дата регистрации, статус).
- **Каталог**: категории и подкатегории, товары, поиск, карточка товара с рейтингом и
  наличием.
- **Заказы**: покупка с оплатой балансом, статусы, бессрочная история, возвраты.
- **Кошелёк**: баланс, история операций, заявки на пополнение с прикреплением PDF-чека
  и ручным подтверждением администратором.
- **Диспуты**: открытие в течение 24 часов после завершения заказа, автоматический подбор
  участников по правам, ответственный сотрудник, неизменяемая история, возвраты.
- **Отзывы**: оценка 0–5, модерация (ответ, скрытие, удаление).
- **RBAC**: каждое действие защищено отдельным правом (104 права), гибкое управление
  должностями, копирование и экспорт прав.
- **Админ-панель**: товары, категории, позиции, местность, сотрудники, должности, заявки,
  диспуты, отзывы, бухгалтерия, реквизиты, настройки, логи, статистика, бэкапы.
- **Безопасность**: защита от SQL Injection (ORM), Race Condition (`SELECT ... FOR UPDATE`,
  `SKIP LOCKED`), Replay/двойных нажатий (идемпотентность на Redis), Flood (rate limit),
  Soft Delete, полный аудит действий.
- **Инфраструктура**: PostgreSQL, Redis (FSM/кэш/троттлинг), APScheduler (бэкапы, авто-закрытие
  диспутов), structlog (5 отдельных журналов), Docker Compose.

## Архитектура

Clean Architecture + Repository Pattern + Service Layer:

```
handlers / keyboards   ← presentation (aiogram)
        │
     services          ← бизнес-логика, транзакции, проверка прав
        │
   repositories        ← доступ к данным (SQLAlchemy)
        │
      models           ← ORM-модели (UUID, created_at, updated_at, deleted_at)
```

Полная структура — в каталоге `app/` (`config`, `logging`, `database`, `models`,
`permissions`, `schemas`, `repositories`, `services`, `bot`, `middlewares`, `filters`,
`keyboards`, `handlers`, `scheduler`, `utils`, `tests`).

## Технологии

Python 3.13 · aiogram 3 · SQLAlchemy 2 (async) · Alembic · PostgreSQL · asyncpg · Redis ·
APScheduler · Pydantic Settings · Structlog · Docker.

## Быстрый старт (Docker)

```bash
cp .env.example .env
# отредактируйте .env: BOT__TOKEN, BOT__ADMIN_IDS, пароли БД
docker compose up -d --build
```

Контейнер `bot` при старте применяет миграции (`alembic upgrade head`) и запускает бота.
Опциональный pgAdmin: `docker compose --profile tools up -d`.

## Локальный запуск

```bash
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env                              # настройте подключения
alembic upgrade head
python -m app
```

## Разработка

```bash
make lint        # ruff
make format      # ruff --fix + black
make typecheck   # mypy
make test        # pytest
make migrate     # alembic upgrade head
make revision m="описание"   # автогенерация миграции
```

Тесты используют in-memory SQLite и покрывают реестр прав, кошелёк (в т.ч. недостаток
средств), оформление заказов, RBAC и диспуты (окно 24 ч, авто-участники, возврат).

## Конфигурация

Все настройки — через `.env` (см. `.env.example`). Разделы с префиксами `BOT__`, `DB__`,
`REDIS__`, `APP__`; вложенность через двойное подчёркивание. Владельцы (`BOT__ADMIN_IDS`)
получают безусловные суперправа.

## Система прав

Все права объявлены в `app/permissions/registry.py` — единый источник правды. Каждое
действие (просмотр, создание, изменение, удаление, блокировка и т.д.) — отдельное право.
При старте права синхронизируются в БД, создаётся системная должность «Владелец» со всеми
правами. Новая функциональность обязана добавлять собственное право в реестр.

## Резервное копирование

Ежедневный бэкап по cron (`APP__BACKUP_CRON`) через `pg_dump`. Восстановление — одной
командой из админ-панели или `BackupService.restore(path)`.

## Лицензия

Проприетарный проект. Все права защищены.
