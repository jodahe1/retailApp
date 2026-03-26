# Offline Retail Checkout and Entrepreneurship Project Incubation Operation Middle Platform API

## Project Overview
This repository contains a production-structured, offline-first API for retail checkout and incubation operations.

Implemented domains include:
- Identity/Auth/Authorization/Security baseline
- Product POS retrieval
- Order and promotion rules
- Payment settlement (offline accounting)
- After-sales (returns, exchanges, reverse settlements)
- Entrepreneurship project lifecycle (create/edit/submit/reject/resubmit/deactivate with version tracking)
- Attachment management and notification center
- Operations analytics and operation configuration management

## Tech Stack
- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Alembic migrations
- Pytest

## Operations Analytics
- Feature values support online/offline processing modes.
- TTL-based storage layer routing:
  - hot for unexpired values
  - cold for expired values
- Sliding window statistic endpoint for rolling averages.
- Frequency service for event rates.
- Correlation proxy service for feature relationship checks.
- Consistency verification validates layer assignment vs TTL.
- Lineage persistence stores source/run/transform digest.
- Daily operations metrics include:
  - transaction volume
  - conversion rate
  - activity count
  - dispute rate
- CSV export endpoint available.

## Operation Configuration
- Versioned operation configurations with rollout percent.
- Gradual rollout updates rollout percent.
- One-click rollback restores previous active version.
- All config create/rollout/rollback actions are audited.

## Attachment Rules
- Allowed file types: application/pdf, image/jpeg, image/png
- Max size per file: 20MB
- Metadata validation includes declared size vs decoded content size
- SHA-256 fingerprint stored for integrity verification

## Notification Center Rules
- Channels:
  - in_site
  - in_process
- Supported trigger examples:
  - pending_approval
  - contract_expiration
  - budget_alert
- Frequency control: same event_type + object_type + object_id + recipient only once per 10 minutes
- Delivery receipt: is_delivered, delivered_at
- Read receipt: is_read, read_at

## Local Setup
1. Create and activate virtual environment.
2. Install dependencies: pip install -r requirements.txt
3. Configure env from .env.example.
4. Run migrations: alembic upgrade head

## Run Commands
- API: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
- Swagger: http://localhost:8000/docs

## Operations Usage Examples
1. Create feature definition:
   - POST /api/v1/operations/features/definitions
2. Insert feature value:
   - POST /api/v1/operations/features/values
3. Check consistency:
   - POST /api/v1/operations/features/consistency-check
4. Build daily analytics:
   - POST /api/v1/operations/analytics/daily
5. Export analytics CSV:
   - GET /api/v1/operations/analytics/export
6. Create config and rollout:
   - POST /api/v1/operations/configurations
   - POST /api/v1/operations/configurations/{id}/rollout
7. Rollback config:
   - POST /api/v1/operations/configurations/rollback?config_key=...

## Test Commands
- Auth/Security: pytest -q tests/test_auth_security.py
- Product: pytest -q tests/test_product_retrieval.py
- Order: pytest -q tests/test_order_domain.py
- Payment: pytest -q tests/test_payment_domain.py
- After-sales: pytest -q tests/test_after_sales_domain.py
- Project lifecycle: pytest -q tests/test_project_lifecycle.py
- Attachment+Notification: pytest -q tests/test_attachment_notification.py
- Operations: pytest -q tests/test_operations_domain.py
- Full suite: pytest -q
