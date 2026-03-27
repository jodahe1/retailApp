# API Specification (Module-Oriented)

All APIs are served under `/api/v1`.
All protected endpoints use bearer token auth.
Standard error response shape:
- `success: false`
- `error_code`
- `message`
- `details`

## 1. Auth
### POST `/auth/users`
- Purpose: Create user with hashed password and encrypted sensitive fields
- Request: `{ username, password, id_number?, contact_info? }`
- Response: `{ user_id, username }`
- Errors: `409` username exists, `422` invalid password format
- Permission: public (bootstrap path)

### POST `/auth/login`
- Purpose: Authenticate and create session token pair
- Request: `{ username, password }`
- Response: `{ access_token, refresh_token, token_type, expires_at }`
- Errors: `401` bad credential, `423` lockout
- Permission: public

### POST `/auth/refresh`
- Purpose: Rotate tokens
- Request: `{ refresh_token }`
- Response: token payload
- Errors: `401` invalid/expired refresh
- Permission: authenticated token context

### POST `/auth/logout`
- Purpose: Revoke one/all active sessions
- Request: `{ refresh_token? }`
- Response: success message
- Errors: `401`
- Permission: authenticated

### POST `/auth/password/change`
- Purpose: Change password
- Request: `{ old_password, new_password }`
- Response: success message
- Errors: `401` old password mismatch, `422` policy fail
- Permission: authenticated

## 2. Users/Roles/Permissions (Admin)
### POST `/admin/permissions`
- Purpose: Create permission code
- Request: `{ code, description? }`
- Response: `{ id, code }`
- Errors: `403`, `409`
- Permission: `superuser` + `auth:permission:assign`

### POST `/admin/roles`
- Purpose: Create role
- Request: `{ name, description? }`
- Response: `{ id, name }`
- Errors: `403`, `409`
- Permission: `superuser` + `auth:role:assign`

### POST `/admin/users/{user_id}/roles`
- Purpose: Assign role(s) to user
- Request: `{ role_ids: [] }`
- Response: assignment summary
- Errors: `403`, `404`
- Permission: `superuser` + `auth:role:assign`

### POST `/admin/roles/{role_id}/permissions`
- Purpose: Assign permission(s) to role
- Request: `{ permission_ids: [] }`
- Response: assignment summary
- Errors: `403`, `404`
- Permission: `superuser` + `auth:permission:assign`

## 3. Products / POS
### POST `/products`
- Purpose: Create product
- Request: `{ name, name_pinyin, barcode, internal_code, unit_price }`
- Response: product id and keys
- Errors: `403`, `422`, `409`
- Permission: `product:manage`

### GET `/products/retrieve?query=...`
- Purpose: Retrieve by barcode/pinyin/internal code
- Response: product payload
- Errors: `403`, `404`, `423`
- Permission: `product:retrieve`

### POST `/products/quick-match`
- Purpose: Cashier quick match list
- Request: `{ query, limit }`
- Response: product list
- Errors: `403`
- Permission: `product:retrieve`

### POST `/products/precheckout/items`
- Purpose: Build pre-checkout line item
- Request: `{ query, quantity }`
- Response: pre-checkout item
- Errors: `403`, `404`, `423`, `422`
- Permission: `checkout:item:add`

## 4. Orders / Promotions
### POST `/orders`
- Purpose: Create order with discount/promotion pipeline
- Request: `{ lines[], order_discount_amount? }`
- Response: order detail
- Errors: `403`, `404`, `422`, `423`
- Permission: `order:create`

### GET `/orders`
- Purpose: List orders
- Response: order summary list
- Errors: `403`
- Permission: `order:read`

### GET `/orders/{order_id}`
- Purpose: Get order detail
- Response: order detail
- Errors: `403`, `404`
- Permission: `order:read`

### POST `/orders/promotions`
- Purpose: Create promotion rule
- Request: promotion rule fields
- Response: created rule id
- Errors: `403`, `422`
- Permission: `promotion:manage`

### POST `/orders/maintenance/expire-unpaid`
- Purpose: Auto-void eligible unpaid orders
- Response: checked/voided counts
- Errors: `403`
- Permission: `order:manage`

## 5. Payments
### POST `/payments/settle`
- Purpose: Offline settlement (supports split)
- Request: `{ order_id, payments[] }`
- Response: settlement result + records
- Errors: `403`, `404`, `409`, `422`, `423`
- Permission: `payment:settle`

### GET `/payments/orders/{order_id}`
- Purpose: List payment records by order
- Response: payment record list
- Errors: `403`
- Permission: `payment:read`

## 6. After-sales
### POST `/after-sales/returns`
- Purpose: Return request processing
- Request: `{ original_order_id, refund_amount, reason? }`
- Response: after-sales order
- Errors: `403`, `404`, `422`
- Permission: `after_sales:handle`

### POST `/after-sales/exchanges`
- Purpose: Exchange processing
- Request: `{ original_order_id, note? }`
- Response: after-sales order
- Errors: `403`, `404`, `422`
- Permission: `after_sales:handle`

### POST `/after-sales/reverse-settlements`
- Purpose: Refund/reverse settlement
- Request: `{ original_order_id, refund_amount, idempotency_key, reason? }`
- Response: after-sales order
- Errors: `403`, `404`, `409`, `422`
- Permission: `after_sales:refund`

## 7. Projects / Versions
### POST `/projects`
- Purpose: Applicant creates draft project
- Request: project create payload
- Response: project detail
- Errors: `403`, `422`
- Permission: `project:own`

### PATCH `/projects/{project_id}`
- Purpose: Edit draft/rejected project
- Request: editable fields
- Response: updated project
- Errors: `403`, `404`, `422`
- Permission: `project:own` + object ownership

### POST `/projects/{project_id}/submit`
- Purpose: Submit project for review
- Request: `{ submission_note? }`
- Response: submitted project
- Errors: `403`, `404`, `422`
- Permission: `project:own` + object ownership

### POST `/projects/{project_id}/reject`
- Purpose: Reject submitted project
- Request: `{ reason }`
- Response: rejected project
- Errors: `403`, `404`, `422`
- Permission: `project:review` or `project:manage` + reviewer scope

### POST `/projects/{project_id}/resubmit`
- Purpose: Resubmit rejected project with new version
- Request: `{ submission_note? }`
- Response: submitted project
- Errors: `403`, `404`, `422`
- Permission: `project:own` + object ownership

### POST `/projects/{project_id}/deactivate`
- Purpose: Deactivate project
- Request: `{ reason }`
- Response: deactivated project
- Errors: `403`, `404`
- Permission: `project:deactivate` or `project:manage` + scope checks

### GET `/projects/{project_id}`
- Purpose: Read project detail
- Response: project
- Errors: `403`, `404`
- Permission: `project:*` read/manage/review/own + object scope

### GET `/projects/{project_id}/versions`
- Purpose: Read project version history with diff summaries
- Response: version list
- Errors: `403`, `404`
- Permission: same scoped project read access

## 8. Attachments
### POST `/attachments`
- Purpose: Validate metadata and register fingerprint
- Request: `{ file_name, content_type, file_size_bytes, file_content_base64, entity_type?, entity_id? }`
- Response: attachment metadata
- Errors: `403`, `422`
- Permission: `attachment:manage`

### GET `/attachments/{attachment_id}`
- Purpose: Read attachment metadata
- Response: attachment metadata
- Errors: `403`, `404`
- Permission: `attachment:read` + owner/admin object check

## 9. Notifications
### POST `/notifications/subscriptions`
- Purpose: Subscribe events
- Request: `{ event_type, object_type?, channel }`
- Response: subscription payload
- Errors: `403`, `422`
- Permission: `notification:subscribe`

### POST `/notifications/trigger`
- Purpose: Trigger notification with throttle
- Request: `{ recipient_user_id, event_type, object_type, object_id, title, message }`
- Response: notification payload or `{ throttled: true }`
- Errors: `403`, `404`
- Permission: `notification:send` or `project:manage`

### GET `/notifications`
- Purpose: List notifications
- Request: `target_user_id?` (admin scope path)
- Response: list
- Errors: `403`
- Permission: `notification:read` + object scope

### POST `/notifications/{notification_id}/read`
- Purpose: mark read/unread
- Request: `{ is_read }`
- Response: updated notification
- Errors: `403`, `404`
- Permission: `notification:read` + owner/admin object check

## 10. Analytics / Feature / Configuration
### POST `/operations/features/definitions`
- Purpose: Create feature definition
- Request: definition payload
- Response: definition
- Errors: `403`, `422`
- Permission: `operations:admin`

### POST `/operations/features/values`
- Purpose: Upsert feature value with TTL routing + lineage
- Request: feature value payload
- Response: feature value
- Errors: `403`, `404`, `422`
- Permission: `operations:admin`

### POST `/operations/features/consistency-check`
- Purpose: Verify hot/cold consistency
- Request: feature/object selector
- Response: consistency result
- Errors: `403`, `404`
- Permission: `operations:admin`

### GET `/operations/features/sliding-window`
- Purpose: Sliding average
- Response: `{ value }`
- Errors: `403`, `404`
- Permission: `operations:admin`

### GET `/operations/features/frequency`
- Purpose: Frequency per minute
- Response: `{ value }`
- Errors: `403`, `404`
- Permission: `operations:admin`

### GET `/operations/features/correlation`
- Purpose: Proxy correlation score
- Response: `{ value }`
- Errors: `403`, `404`
- Permission: `operations:admin`

### POST `/operations/analytics/daily`
- Purpose: Build daily aggregated metrics
- Request: day metrics payload
- Response: daily analytics
- Errors: `403`, `422`
- Permission: `operations:admin`

### GET `/operations/analytics/export`
- Purpose: Export daily analytics CSV
- Response: text/csv
- Errors: `403`
- Permission: `operations:admin`

### POST `/operations/configurations`
- Purpose: Create versioned operation configuration
- Request: `{ config_key, config_value, rollout_percent }`
- Response: config payload
- Errors: `403`, `422`
- Permission: `operations:admin`

### POST `/operations/configurations/{config_id}/rollout`
- Purpose: Adjust rollout percent
- Request: query param `rollout_percent`
- Response: config payload
- Errors: `403`, `404`, `422`
- Permission: `operations:admin`

### POST `/operations/configurations/rollback`
- Purpose: One-click rollback to previous version
- Request: query param `config_key`
- Response: rolled-back active config
- Errors: `403`, `404`, `422`
- Permission: `operations:admin`
