# Project Overview

A production-ready Telegram platform built with Python and aiogram 3.x.

The project follows Clean Architecture principles and is designed for scalability, maintainability and long-term development.

## Main Features

- Modular architecture
- Asynchronous application
- PostgreSQL database
- Redis caching
- SQLAlchemy ORM
- Alembic migrations
- Docker & Docker Compose
- Role-Based Access Control (RBAC)
- Granular permission system
- Administrative panel
- User management
- Order management
- Wallet and balance system
- Review system
- Dispute management
- Accounting module
- Audit logging
- Notification system
- Background scheduler
- Centralized error handling
- Soft Delete support
- Repository Pattern
- Service Layer
- Dependency Injection
- Structured logging
- Configuration via environment variables
- Production-ready deployment

## Code Quality

- Python 3.13+
- aiogram 3.x
- SQLAlchemy 2.x
- PostgreSQL
- Redis
- Docker
- Alembic
- Ruff
- Black
- MyPy
- Pytest

## Architecture

The project is designed with a clear separation of responsibilities.

- Presentation Layer
- Business Logic Layer
- Repository Layer
- Database Layer
- Infrastructure Layer

Every module is isolated and can be extended independently.

The permission system is fully granular, allowing each action to be controlled independently through RBAC.

The project is intended for long-term maintenance, scalability and production deployment.
