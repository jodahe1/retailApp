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

## Tech Stack
- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Alembic migrations
- Pytest

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

## Project Lifecycle Notes
- Lifecycle states: draft -> submitted -> rejected -> submitted or deactivated.
- Applicant can manage own projects only (object-level ownership checks).
- Reviewer can reject only projects in allowed scope (assigned or permitted).
- Operation admin (project:manage) has broader management scope.
- Each submit/resubmit increments current_version and creates project_versions snapshot.
- Version diff summaries are retained for audit and review.
- Lifecycle-critical actions are written to immutable audit logs.

## Local Setup
1. Create and activate virtual environment.
2. Install dependencies: pip install -r requirements.txt
3. Configure env from .env.example.
4. Run migrations: alembic upgrade head

## Run Commands
- API: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
- Swagger: http://localhost:8000/docs

## Attachment Validation Steps
1. Grant permissions attachment:manage and attachment:read.
2. Create metadata record (POST /api/v1/attachments) with base64 content.
3. Confirm accepted type and size.
4. Verify fingerprint_sha256 exists in response.
5. Try text/plain or >20MB and confirm 422 rejection.

## Notification Verification Steps
1. Grant permissions: notification:subscribe, notification:send, notification:read as needed.
2. Subscribe recipient (POST /api/v1/notifications/subscriptions).
3. Trigger event (POST /api/v1/notifications/trigger).
4. Repeat same event/object within 10 minutes and verify throttled response.
5. List notifications (GET /api/v1/notifications).
6. Mark read (POST /api/v1/notifications/{id}/read) and verify read_at.

## Test Commands
- Auth/Security: pytest -q tests/test_auth_security.py
- Product: pytest -q tests/test_product_retrieval.py
- Order: pytest -q tests/test_order_domain.py
- Payment: pytest -q tests/test_payment_domain.py
- After-sales: pytest -q tests/test_after_sales_domain.py
- Project lifecycle: pytest -q tests/test_project_lifecycle.py
- Attachment+Notification: pytest -q tests/test_attachment_notification.py
- Full suite: pytest -q
