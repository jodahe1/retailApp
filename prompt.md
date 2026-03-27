Offline Retail Checkout and Entrepreneurship Project Incubation Operation Middle Platform API

Project objective:
Build a production-structured, offline-deployable pure backend service using FastAPI + SQLAlchemy + PostgreSQL.

Major phased requirements (summary of original prompt intent):
1. Foundation
- FastAPI bootstrap
- SQLAlchemy session/transaction handling
- PostgreSQL integration
- migration-ready structure
- logging, exception handling, shared responses, health check

2. Identity/Auth/Security baseline
- users/roles/permissions
- hashed password policy (>=8 chars)
- failed-login lockout
- route-level authorization
- object-level authorization hooks
- field-level encryption for sensitive fields
- immutable audit logs and sensitive access logs

3. Product/POS retrieval
- retrieval by barcode/pinyin/internal code
- quick match for cashier flow
- pre-checkout item building
- active/availability validation and logging

4. Order domain
- order/order-line/promotion rule models
- item/order discounts
- spend-save, buy-get, tiered, purchase-limit promotions
- order expiry after 30 minutes if unsettled

5. Payment domain
- offline accounting only
- cash/bank-card/stored-value
- split settlement
- overpayment and duplicate settlement prevention

6. After-sales domain
- return/exchange/reverse settlement
- trace to original order
- 7-day return window
- refund ceiling and idempotency

7. Project lifecycle domain
- create/edit/submit/reject/resubmit/deactivate
- version increment and diff summary
- applicant/reviewer/admin scope boundaries

8. Attachment + Notification
- file type/size restrictions and fingerprint
- event subscriptions and in-site/in-process notifications
- 10-minute throttle for same event+object
- delivery/read receipts

9. Operations analytics/config
- feature definition/value models
- TTL hot/cold routing
- consistency and lineage tracking
- daily metrics and export
- gradual rollout + one-click rollback with audit

10. Hardening/acceptance readiness
- standardized errors/logging/auth coverage
- migration reliability
- seed and tests coverage
- README acceptance runbook

11. Docker delivery
- one-command startup via docker compose up
- backend + postgres containers
- automatic migration and startup flow
- documented verification steps
