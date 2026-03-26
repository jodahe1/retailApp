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
- Order and promotion rule calculation domain baseline

## Stack
- Python 3.11+
- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Alembic (migration-ready)
- Passlib Argon2 password hashing
- Cryptography (Fernet) for field-level encryption
- Pytest

## Run Commands
- Start API:
  - `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Swagger UI:
  - `http://localhost:8000/docs`

## Order Verification Steps
1. Create products used by order lines.
2. Create promotion rules (`/api/v1/orders/promotions`) for spend-save, buy-get, tiered, or purchase-limit.
3. Create order (`/api/v1/orders`) with line-level discounts and optional whole-order discount.
4. Verify order detail (`/api/v1/orders/{order_id}`):
   - `subtotal_amount`
   - `item_discount_total`
   - `promotion_discount_total`
   - `order_discount_total`
   - `final_amount`
5. Run unpaid expiration maintenance after test aging:
   - `POST /api/v1/orders/maintenance/expire-unpaid`

## Offline Expiration Operation
- Unpaid orders are considered eligible for auto-void after 30 minutes from creation.
- In offline deployment, run expiration through:
  - scheduled OS task (cron/systemd timer) calling `/api/v1/orders/maintenance/expire-unpaid`
  - or periodic in-app service invocation when integrating the scheduler module in next phase.

## Test Commands
- `pytest -q tests/test_order_domain.py`
- `pytest -q`
