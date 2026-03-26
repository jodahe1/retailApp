# Offline Retail Checkout and Entrepreneurship Incubation Middle Platform API

## Business Summary
This service is an offline-first, single-machine deployable middle-platform API for:
- retail POS checkout and settlement operations
- after-sales workflows (returns, exchanges, reverse settlements)
- entrepreneurship project lifecycle review workflows
- attachment/notification support
- operations analytics and configuration governance

The system is designed for local/private network deployments where cloud dependencies are unavailable or disallowed.

## Architecture Overview
This is a layered FastAPI service with explicit domain boundaries:
- API layer: `app/api/v1/endpoints/*`
- Domain service layer: `app/services/*`
- Data layer: SQLAlchemy ORM models in `app/models/*`, DB session in `app/db/session.py`
- Security layer: authn/authz dependencies, field encryption, audit and access logging in `app/security/*`
- Exception contract: centralized in `app/exceptions/*`
- Migrations: Alembic in `alembic/*`

### Concise Architecture Notes
- Route-level authorization is enforced via `require_permission(...)` and `require_any_permission(...)` dependencies.
- Object-level authorization is enforced in services/policies (for example: project ownership/reviewer scope and attachment/notification ownership checks).
- Critical actions append immutable audit logs (`immutable_audit_logs`) through `write_audit_log(...)`.
- Sensitive data access paths write `sensitive_access_logs` through `record_sensitive_access(...)`.

## Module List
- Identity/Auth/Security baseline
- Product & POS retrieval
- Order & promotion engine
- Payment settlement (offline accounting)
- After-sales
- Entrepreneurship project lifecycle
- Attachment management
- Notification center
- Operations analytics + operation configuration rollout/rollback

## Tech Stack
- FastAPI
- SQLAlchemy ORM
- PostgreSQL
- Alembic
- Pydantic v2
- Pytest + FastAPI TestClient

## Project Structure
```text
app/
  api/v1/endpoints/
  core/
  db/
  exceptions/
  models/
  schemas/
  security/
  services/
alembic/
  versions/
scripts/
tests/
```

## Environment Setup
1. Create virtual environment.
2. Install dependencies.
3. Configure `.env` from `.env.example`.
4. Ensure PostgreSQL is available locally.

### Example `.env`
Use `.env.example` as baseline:
- `DATABASE_URL=postgresql+psycopg://retail_user:retail_pass@localhost:5432/retail_db`
- `FIELD_ENCRYPTION_KEY=<fernet-key>`
- `LOG_FORMAT=json`

## Startup Instructions
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed_demo
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger/OpenAPI:
- `http://localhost:8000/docs`

## Migration Commands
```bash
alembic current
alembic history
alembic upgrade head
alembic downgrade -1
alembic revision -m "your_change"
```

Notes:
- The project uses explicit migration files in `alembic/versions`.
- `alembic/env.py` imports model registry from `app.db.models` to guarantee metadata discovery.

## Local Run Commands
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Test Commands
```bash
pytest -q
pytest -q tests/test_auth_security.py
pytest -q tests/test_product_retrieval.py
pytest -q tests/test_order_domain.py
pytest -q tests/test_payment_domain.py
pytest -q tests/test_after_sales_domain.py
pytest -q tests/test_project_lifecycle.py
pytest -q tests/test_attachment_notification.py
pytest -q tests/test_operations_domain.py
pytest -q tests/test_acceptance_hardening.py
```

## Test Overview
The test suite includes unit/API-level verification for:
- authentication and password policy
- route-level authorization and permission denial
- object-level authorization boundaries (ownership/reviewer/admin scopes)
- order/payment/after-sales financial consistency
- idempotency and rollback behavior
- notification throttling and attachment restrictions
- major HTTP exception paths (`401`, `403`, `404`, `409`, `422`)

## Example Verification Checklist by Module
### Auth/Security
- create user with valid password
- reject short password
- login success/failure and lockout after 5 failed attempts
- protected route `401`/`403` behavior
- role/permission assignment via admin endpoints

### Product/POS
- retrieve by barcode/pinyin/internal code
- inactive product rejected for checkout
- missing product returns not found

### Order/Promotion
- create order with discounts
- promotion rule calculations
- unpaid order expiry via maintenance endpoint

### Payment
- cash and split settlement
- overpayment rejection
- duplicate settlement protection
- order status transitions: unpaid/partially paid/settled

### After-sales
- return within 7 days accepted
- return after 7 days rejected
- refund ceiling enforcement
- reverse settlement idempotency behavior

### Project Lifecycle
- draft create/edit/submit
- rejection and resubmission with version increment
- diff summary persistence
- ownership and reviewer/admin scope checks

### Attachment/Notification
- file type/size enforcement
- fingerprint generation
- notification trigger and throttling
- delivery and read receipts

### Operations Analytics/Config
- sliding window/frequency/correlation proxy
- hot/cold TTL routing
- consistency check and lineage persistence
- gradual rollout and rollback

## Offline Deployment Boundary
- Intended for single-machine Docker-compatible local deployment.
- No mandatory external cloud dependencies.
- Payment uses offline accounting records and local validation rules.
- Notification channels are in-site and in-process only.

## Security & Audit Notes
- Passwords are strongly hashed (`passlib[argon2]`).
- Sensitive fields are encrypted at rest via `FieldEncryption`.
- Immutable audit table is append-only in model event hooks (update/delete blocked).
- Sensitive access paths are logged in `sensitive_access_logs`.
- Logs avoid password/token/plain sensitive field output.

## Mock/Stub Areas and Acceptability
- Receipt printing is an abstraction (`app/services/receipt.py`) with no hardware binding by default; acceptable for offline acceptance where printer integration varies by site.
- Correlation in operations analytics is a proxy score, not a full statistical engine; acceptable as baseline with explicit documentation and tests.
- No external payment gateway integration: settlement is internal/offline-accounting only by design.
