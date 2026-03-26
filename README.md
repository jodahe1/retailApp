# Offline Retail Checkout and Entrepreneurship Project Incubation Operation Middle Platform API

## Project Overview
This repository contains a production-structured offline-first API for retail checkout and incubation operations.

Implemented domains include:
- Identity/Auth/Authorization/Security baseline
- Product POS retrieval
- Order and promotion rules
- Payment settlement (offline accounting)

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

## Commands
- Run API: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- Docs: `http://localhost:8000/docs`
- Migrate: `alembic upgrade head`
- Payment tests: `pytest -q tests/test_payment_domain.py`
- Full tests: `pytest -q`
