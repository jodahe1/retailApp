# Offline Retail Checkout and Entrepreneurship Project Incubation Operation Middle Platform API

## Project Overview
This repository contains a production-structured, offline-first API for retail checkout and incubation operations.

Implemented domains include:
- Identity/Auth/Authorization/Security baseline
- Product POS retrieval
- Order and promotion rules
- Payment settlement (offline accounting)
- After-sales (returns, exchanges, reverse settlements)

## Tech Stack
- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Alembic migrations
- Pytest

## Payment Domain Notes
- Offline accounting only (no third-party online gateway call).
- Supported payment methods:
  - `cash`
  - `bank_card`
  - `stored_value`
- Split payment is supported in one or multiple settlement calls.
- Overpayment is rejected.
- Non-cash offline settlement requires `offline_approval_code`.
- Order status transition:
  - `pending` -> `partially_paid` -> `settled`
  - payment on `void`/`settled` order is blocked.

## After-Sales Domain Notes
- Supports `return`, `exchange`, and `refund` (reverse settlement).
- Every after-sales action must reference an existing original order.
- Return and refund are limited to a 7-day window from original order creation.
- Refund ceiling enforced: cumulative refunded amount cannot exceed original order total.
- Refund requests require idempotency key and are idempotent for repeated same payload.
- Critical actions write immutable audit entries.

## Local Setup
1. Create and activate virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Configure env from `.env.example`.
4. Run migrations: `alembic upgrade head`

## Run Commands
- API: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Swagger: `http://localhost:8000/docs`

## Local Settlement Test Steps
1. Create user and login.
2. Grant permissions: `product:manage`, `order:create`, `payment:settle`, optionally `payment:read`.
3. Create product (`POST /api/v1/products`).
4. Create order (`POST /api/v1/orders`).
5. Settle payment (`POST /api/v1/payments/settle`):
   - cash only example:
     - `{"order_id":1,"payments":[{"method":"cash","amount":10.0}]}`
   - split example:
     - `{"order_id":1,"payments":[{"method":"cash","amount":4.0},{"method":"bank_card","amount":6.0,"offline_approval_code":"OFF1234"}]}`
6. Verify records (`GET /api/v1/payments/orders/{order_id}`).

## Local After-Sales Verification Steps
1. Ensure permission assignment includes `after_sales:handle` and `after_sales:refund`.
2. Create and settle an order.
3. Create return:
   - `POST /api/v1/after-sales/returns`
   - `{"original_order_id": 1001, "refund_amount": 5.0, "reason": "Damaged item"}`
4. Create exchange:
   - `POST /api/v1/after-sales/exchanges`
   - `{"original_order_id": 1001, "note": "Exchange to another size"}`
5. Reverse settlement:
   - `POST /api/v1/after-sales/reverse-settlements`
   - `{"original_order_id": 1001, "refund_amount": 3.0, "idempotency_key": "refund-1001-001", "reason": "Customer requested refund"}`
6. Re-send the same reverse-settlement payload and confirm same after-sales record ID is returned.

## Test Commands
- Health: `pytest -q tests/test_health.py`
- Auth/Security: `pytest -q tests/test_auth_security.py`
- Product: `pytest -q tests/test_product_retrieval.py`
- Order: `pytest -q tests/test_order_domain.py`
- Payment: `pytest -q tests/test_payment_domain.py`
- After-sales: `pytest -q tests/test_after_sales_domain.py`
- Full suite: `pytest -q`
