# Clarification Log

## 1) Order expiry behavior
- Question: Should partially paid orders also auto-expire after 30 minutes if not fully settled?
- My Understanding / Assumption: Yes, both `pending` and `partially_paid` are considered unsettled and eligible for timeout void.
- Solution implemented: Expiration job checks both states and marks eligible orders as `void` with audit entry (`order.auto_void`).

## 2) Refund idempotency semantics
- Question: If the same idempotency key is reused with identical payload, should it be treated as success or conflict?
- My Understanding / Assumption: Same key + same payload is idempotent success; same key + different payload is conflict.
- Solution implemented: Reverse settlement returns existing record on exact match; raises `409` on payload mismatch.

## 3) Object-level project access boundaries
- Question: Who can access/modify a project object?
- My Understanding / Assumption: Applicant owns own project; reviewer can act only on assigned/allowed project; admin/manager has broader scope.
- Solution implemented: Policy checks in project service enforce ownership/reviewer scope; unauthorized access returns `403`.

## 4) Notification throttling interpretation
- Question: What defines duplicate reminders for throttling?
- My Understanding / Assumption: Same recipient + same event_type + same object_type + same object_id within 10 minutes is duplicate.
- Solution implemented: Trigger path checks last 10-minute window and returns throttled response instead of creating duplicate notifications.

## 5) Attachment storage behavior
- Question: Are binary files required to be persisted physically in this phase?
- My Understanding / Assumption: Metadata validation + integrity fingerprint is mandatory; actual file backend may be abstracted for offline baseline.
- Solution implemented: Validates type/size/content length, computes SHA-256 fingerprint, stores metadata with offline storage key reference.

## 6) Sensitive field protection and logging
- Question: How should sensitive fields be handled in responses/logs?
- My Understanding / Assumption: Encrypt at rest, avoid plaintext logging, and log every sensitive read path.
- Solution implemented: Encrypted columns for user sensitive fields, controlled reveal endpoint, sensitive access logs for reads, no plaintext secret logging.

## 7) Configuration rollout/rollback behavior
- Question: Should rollback always restore immediate previous active config version?
- My Understanding / Assumption: Yes, rollback targets prior version chain for same config key.
- Solution implemented: Active config is deactivated, previous config reactivated, and rollback action is audited.

## 8) Correlation service depth
- Question: Is full statistical correlation required now?
- My Understanding / Assumption: Baseline proxy is acceptable for this phase if clearly documented.
- Solution implemented: Implemented deterministic proxy correlation metric and documented it as baseline/non-advanced analytics.

## 9) Docker startup and seed behavior
- Question: Should reviewers perform manual migration/seed steps?
- My Understanding / Assumption: No manual steps should be needed for acceptance startup.
- Solution implemented: Container entrypoint waits for DB, runs migrations, runs seed bootstrap, then starts API.

## 10) Test grouping requirement
- Question: Existing tests were under one folder; should delivery expose explicit test groups?
- My Understanding / Assumption: Submission requires visible `unit_tests/` and `API_tests/` groups with one-click runner.
- Solution implemented: Tests reshaped into required directories and `run_tests.sh` added.
