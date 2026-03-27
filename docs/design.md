# Design Overview

## 1. Architecture Overview
The system is a layered FastAPI backend organized into:
- Route layer (`app/api/v1/endpoints`)
- Service/domain layer (`app/services`)
- Persistence layer (`app/models`, `app/db`)
- Security layer (`app/security`)
- Shared contracts (`app/schemas`, `app/exceptions`)

The application runs offline-first and is packaged for single-machine container deployment.

## 2. Domain Boundaries
Primary bounded contexts:
- Identity/Auth/Security
- Product POS retrieval
- Order/Promotion
- Payment
- After-sales
- Entrepreneurship project lifecycle
- Attachment management
- Notification center
- Operations analytics/configuration

Each domain has dedicated models, schemas, services, and route modules to avoid monolithic coupling.

## 3. Auth and Permission Model
- Authentication: token-based session model with access/refresh tokens.
- Authorization: route-level dependencies (`require_permission`, `require_any_permission`, `require_superuser`).
- RBAC: user-role and role-permission mappings.
- Object-level authorization: policy/service checks enforce ownership/scope (project, notification, attachment).

## 4. Transaction Consistency Strategy
- Write operations use explicit transaction boundaries via `transactional_session` context manager.
- Multi-step domain changes (order creation, settlement, reverse settlement, config rollback) are committed atomically.
- Conflict and validation exceptions are surfaced as standardized JSON error responses.

## 5. Audit and Sensitive Access Logging
- Immutable audit events are appended to `immutable_audit_logs` for critical actions.
- Model hooks block update/delete attempts on immutable audit rows.
- Sensitive field reads are recorded in `sensitive_access_logs`.
- Logging avoids leaking tokens/passwords/plain sensitive content.

## 6. Encryption Approach
- Sensitive user fields (ID/contact) are encrypted at rest via field encryption utility.
- Decryption is only exposed through protected paths and access logging.

## 7. Order/Payment/After-sales Flow
- Order: supports line items, item/order-level discounts, promotions, final amount pipeline.
- Promotion engine: spend-save, buy-get, tiered pricing, purchase limits.
- Payment: offline accounting, split methods, overpayment prevention, order status transitions.
- Expiry: pending/partially-paid orders are eligible for 30-minute auto-void.
- After-sales: return/exchange/reverse settlement with 7-day window, refund ceiling, and idempotency controls.

## 8. Notification/Event Flow
- Supports in-site and in-process channels.
- Event subscription model for recipient-event combinations.
- Throttling rule: same recipient + same event/object limited to once per 10 minutes.
- Delivery/read receipts are persisted.

## 9. Feature Hot/Cold TTL Design
- Feature definitions carry TTL and mode defaults.
- Feature values are routed to hot/cold logical layers based on expiry.
- Consistency checks verify layer assignment against TTL state.
- Lineage records track source/run/transform metadata.

## 10. Rollout/Rollback Design
- Operation configuration is versioned by key.
- Gradual rollout adjusts rollout percent.
- Rollback reactivates previous configuration version and audits the action.

## 11. Testing Strategy
- Tests are grouped into:
  - `unit_tests/` for security/validation/core behavior
  - `API_tests/` for domain API workflows and authorization paths
- `run_tests.sh` executes both groups for repeatable acceptance verification.

## 12. Docker Runtime Deployment
- `docker compose up` starts PostgreSQL + API.
- API startup script waits for DB, runs Alembic migrations, runs seed, then launches app.
- Healthchecks are configured for DB and API.
- Ports: backend `8000`, postgres `5432`.
