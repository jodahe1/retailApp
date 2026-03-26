# Offline Retail Checkout and Entrepreneurship Project Incubation Operation Middle Platform API

## Project Overview
This repository contains the foundation of a production-structured backend API for offline-first single-machine retail operations and entrepreneurship incubation workflows.

Current phase provides:
- FastAPI service bootstrap
- Configuration and environment management
- SQLAlchemy engine/session foundation for PostgreSQL
- Shared response and exception handling
- Router modularization and health endpoint
- Logging initialization structure
- Alembic-ready migration scaffolding
- Seed/bootstrap placeholder script

## Stack
- Python 3.11+
- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Alembic (migration-ready)
- Pytest (test placeholder)

## Project Structure
- `app/` - application source
- `app/api/` - API routers and endpoint modules
- `app/core/` - settings and logging setup
- `app/db/` - SQLAlchemy base/session/model registry
- `app/models/` - domain models (future phases)
- `app/schemas/` - shared and domain schemas
- `app/services/` - service layer (future phases)
- `app/repositories/` - repository layer (future phases)
- `app/exceptions/` - custom exceptions and handlers
- `alembic/` - migrations environment and versions
- `scripts/` - operational/bootstrap scripts
- `tests/` - test modules

## Local Setup
1. Create virtual environment:
   - `python -m venv venv`
   - `source venv/bin/activate`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Configure environment:
   - `cp .env.example .env`
   - Update `DATABASE_URL` for local PostgreSQL

## Run Commands
- Start API:
  - `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Health check:
  - `curl http://localhost:8000/api/v1/health`
- Seed/bootstrap placeholder:
  - `python scripts/seed_demo.py`

## Migration Commands
- Initialize migration (after first model exists):
  - `alembic revision --autogenerate -m "init schema"`
- Apply migrations:
  - `alembic upgrade head`

## Test Commands (Placeholder)
- `pytest -q`

## Notes for Offline Single-Machine Deployment
- No external cloud dependency is required by the foundation layer.
- PostgreSQL is expected to run on the same machine or local network segment.
- Docker compatibility is preserved by environment-driven config and clean process entrypoint.
