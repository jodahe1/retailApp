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
- Identity, authentication, authorization, and security baseline
- Swagger/OpenAPI endpoint docs with request/response examples
- Product and POS retrieval domain baseline

## Stack
- Python 3.11+
- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Alembic (migration-ready)
- Passlib Argon2 password hashing
- Cryptography (Fernet) for field-level encryption
- Pytest

## Project Structure
- `app/` - application source
- `app/api/` - API routers and endpoint modules
- `app/core/` - settings and logging setup
- `app/db/` - SQLAlchemy base/session/model registry
- `app/models/` - domain models
- `app/schemas/` - shared and domain schemas
- `app/services/` - service layer
- `app/security/` - hashing, encryption, token, authz, policy, audit/access utilities
- `app/repositories/` - repository layer (future phases)
- `app/exceptions/` - custom exceptions and handlers
- `alembic/` - migrations environment and versions
- `scripts/` - operational/bootstrap scripts
- `tests/` - test modules

## Local Setup
1. Create virtual environment:
   - `python3 -m venv venv`
   - `source venv/bin/activate`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Configure environment:
   - `cp .env.example .env`
   - Update `DATABASE_URL` for local PostgreSQL
   - Set `FIELD_ENCRYPTION_KEY` (Fernet-compatible 32-byte base64 key)

## Run Commands
- Start API:
  - `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Swagger UI:
  - `http://localhost:8000/docs`
- ReDoc:
  - `http://localhost:8000/redoc`
- OpenAPI JSON:
  - `http://localhost:8000/openapi.json`

## API Examples
- Create user:
  - `curl -X POST http://localhost:8000/api/v1/auth/users -H "Content-Type: application/json" -d '{"username":"admin","password":"Admin1234"}'`
- Login:
  - `curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"Admin1234"}'`
- Create product:
  - `curl -X POST http://localhost:8000/api/v1/products -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"name":"Cola 500ml","name_pinyin":"kele","barcode":"6901111111111","internal_code":"SKU-COLA-500","unit_price":4.50}'`
- Retrieve product by barcode:
  - `curl "http://localhost:8000/api/v1/products/retrieve?query=6901111111111" -H "Authorization: Bearer <TOKEN>"`
- Retrieve product by pinyin:
  - `curl "http://localhost:8000/api/v1/products/retrieve?query=kele" -H "Authorization: Bearer <TOKEN>"`
- Retrieve product by internal code:
  - `curl "http://localhost:8000/api/v1/products/retrieve?query=SKU-COLA-500" -H "Authorization: Bearer <TOKEN>"`
- Quick match for cashier:
  - `curl -X POST http://localhost:8000/api/v1/products/quick-match -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"query":"ke","limit":10}'`
- Build pre-checkout item:
  - `curl -X POST http://localhost:8000/api/v1/products/precheckout/items -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d '{"query":"6901111111111","quantity":2}'`

## Migration Commands
- Initialize migration (after model changes):
  - `alembic revision --autogenerate -m "product pos retrieval baseline"`
- Apply migrations:
  - `alembic upgrade head`

## Test Commands
- Run all tests:
  - `pytest -q`
- Run auth/security tests only:
  - `pytest -q tests/test_auth_security.py`
- Run product retrieval tests only:
  - `pytest -q tests/test_product_retrieval.py`

## Swagger Documentation Convention
- Every endpoint should define `summary`, `description`, and error `responses`.
- Every request schema field should include `examples`.
- Every endpoint should include at least one success example and key error examples.

## Security Baseline Notes
- Usernames are uniquely indexed.
- Password policy enforces minimum length and complexity.
- Passwords are hashed using Argon2.
- Account lockout is 15 minutes after 5 consecutive failed login attempts.
- Sensitive fields support field-level encryption.
- Sensitive field access is logged in `sensitive_access_logs`.
- Critical operations (login success/failure, password change, role/permission assignment) are appended into immutable audit logs.
- Route-level authorization is enforced via dependencies.
- Object-level authorization scaffolding is included for ownership/scope checks.
- Admin-only interfaces are protected using superuser + permission checks.

## Notes for Offline Single-Machine Deployment
- No external cloud dependency is required by the foundation layer.
- PostgreSQL is expected to run on the same machine or local network segment.
- Docker compatibility is preserved by environment-driven config and clean process entrypoint.
