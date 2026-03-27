from datetime import timedelta

from sqlalchemy import select

from app.models.identity import (
    ImmutableAuditLog,
    Permission,
    Role,
    RolePermission,
    SensitiveAccessLog,
    User,
    UserRole,
)
from app.models.order import Order


def _create_user(client, username: str, password: str):
    return client.post(
        "/api/v1/auth/users",
        json={"username": username, "password": password, "contact_info": "+251900999999"},
    )


def _login(client, username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _grant_permissions(db_session, username: str, permission_codes: list[str]):
    user = db_session.scalar(select(User).where(User.username == username))
    role = Role(name=f"role-accept-{username}")
    db_session.add(role)
    db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))

    for code in permission_codes:
        perm = db_session.scalar(select(Permission).where(Permission.code == code))
        if perm is None:
            perm = Permission(code=code)
            db_session.add(perm)
            db_session.flush()
        db_session.add(RolePermission(role_id=role.id, permission_id=perm.id))

    db_session.commit()


def test_authentication_unauthorized_and_forbidden_paths(client, db_session):
    no_auth = client.get("/api/v1/protected/me")
    assert no_auth.status_code == 401

    _create_user(client, "accept_authz", "abc12345")
    token = _login(client, "accept_authz", "abc12345").json()["data"]["access_token"]

    forbidden = client.get("/api/v1/protected/permission-test", headers=_auth(token))
    assert forbidden.status_code == 403


def test_object_level_authorization_and_data_isolation(client, db_session):
    _create_user(client, "accept_owner", "abc12345")
    _create_user(client, "accept_other", "abc12345")
    _grant_permissions(db_session, "accept_owner", ["project:own", "project:read", "notification:read"])
    _grant_permissions(db_session, "accept_other", ["project:own", "project:read", "notification:read"])

    owner_token = _login(client, "accept_owner", "abc12345").json()["data"]["access_token"]
    other_token = _login(client, "accept_other", "abc12345").json()["data"]["access_token"]

    created = client.post(
        "/api/v1/projects",
        headers=_auth(owner_token),
        json={
            "name": "Isolation Project",
            "category": "retail-tech",
            "description": "Owner only",
            "contact_phone": "+251900888888",
        },
    )
    project_id = created.json()["data"]["id"]

    denied_project = client.get(f"/api/v1/projects/{project_id}", headers=_auth(other_token))
    assert denied_project.status_code == 403

    denied_notification_scope = client.get(
        "/api/v1/notifications",
        headers=_auth(other_token),
        params={"target_user_id": db_session.scalar(select(User.id).where(User.username == "accept_owner"))},
    )
    assert denied_notification_scope.status_code == 403


def test_not_found_conflict_and_idempotency_paths(client, db_session):
    _create_user(client, "accept_paths", "abc12345")
    _grant_permissions(
        db_session,
        "accept_paths",
        [
            "product:manage",
            "order:create",
            "order:read",
            "payment:settle",
            "after_sales:refund",
            "after_sales:handle",
        ],
    )
    token = _login(client, "accept_paths", "abc12345").json()["data"]["access_token"]

    not_found_order = client.get("/api/v1/orders/999999", headers=_auth(token))
    assert not_found_order.status_code == 404

    client.post(
        "/api/v1/products",
        headers=_auth(token),
        json={
            "name": "Acceptance Item",
            "name_pinyin": "yanshou",
            "barcode": "6999999999999",
            "internal_code": "SKU-ACCEPT-1",
            "unit_price": 10.0,
        },
    )

    order_resp = client.post(
        "/api/v1/orders",
        headers=_auth(token),
        json={"lines": [{"product_query": "SKU-ACCEPT-1", "quantity": 1}]},
    )
    order_id = order_resp.json()["data"]["id"]

    settled = client.post(
        "/api/v1/payments/settle",
        headers=_auth(token),
        json={"order_id": order_id, "payments": [{"method": "cash", "amount": 10.0}]},
    )
    assert settled.status_code == 200

    duplicate_settle = client.post(
        "/api/v1/payments/settle",
        headers=_auth(token),
        json={"order_id": order_id, "payments": [{"method": "cash", "amount": 1.0}]},
    )
    assert duplicate_settle.status_code == 409

    first_refund = client.post(
        "/api/v1/after-sales/reverse-settlements",
        headers=_auth(token),
        json={"original_order_id": order_id, "refund_amount": 4.0, "idempotency_key": "idem-accept-001"},
    )
    assert first_refund.status_code == 200

    conflicting_refund = client.post(
        "/api/v1/after-sales/reverse-settlements",
        headers=_auth(token),
        json={"original_order_id": order_id, "refund_amount": 5.0, "idempotency_key": "idem-accept-001"},
    )
    assert conflicting_refund.status_code == 409


def test_order_expiry_refund_ceiling_notification_throttle_attachment_restrictions_and_rollback(
    client,
    db_session,
):
    _create_user(client, "accept_boundaries", "abc12345")
    _grant_permissions(
        db_session,
        "accept_boundaries",
        [
            "product:manage",
            "order:create",
            "order:manage",
            "payment:settle",
            "after_sales:refund",
            "notification:send",
            "notification:read",
            "attachment:manage",
            "operations:admin",
        ],
    )
    token = _login(client, "accept_boundaries", "abc12345").json()["data"]["access_token"]
    user_id = db_session.scalar(select(User.id).where(User.username == "accept_boundaries"))

    client.post(
        "/api/v1/products",
        headers=_auth(token),
        json={
            "name": "Boundary Item",
            "name_pinyin": "bianjie",
            "barcode": "6888888888888",
            "internal_code": "SKU-BOUND-1",
            "unit_price": 10.0,
        },
    )
    order_id = client.post(
        "/api/v1/orders",
        headers=_auth(token),
        json={"lines": [{"product_query": "SKU-BOUND-1", "quantity": 1}]},
    ).json()["data"]["id"]

    order = db_session.get(Order, order_id)
    order.created_at = order.created_at - timedelta(minutes=31)
    db_session.commit()

    expire_run = client.post("/api/v1/orders/maintenance/expire-unpaid", headers=_auth(token))
    assert expire_run.status_code == 200
    assert db_session.get(Order, order_id).status == "void"

    settled_order_id = client.post(
        "/api/v1/orders",
        headers=_auth(token),
        json={"lines": [{"product_query": "SKU-BOUND-1", "quantity": 1}]},
    ).json()["data"]["id"]
    client.post(
        "/api/v1/payments/settle",
        headers=_auth(token),
        json={"order_id": settled_order_id, "payments": [{"method": "cash", "amount": 10.0}]},
    )

    refund_ceiling = client.post(
        "/api/v1/after-sales/reverse-settlements",
        headers=_auth(token),
        json={"original_order_id": settled_order_id, "refund_amount": 11.0, "idempotency_key": "ceiling-001"},
    )
    assert refund_ceiling.status_code == 422

    payload = {
        "recipient_user_id": user_id,
        "event_type": "budget_alert",
        "object_type": "project",
        "object_id": "P-ACCEPT-1",
        "title": "Alert",
        "message": "Threshold",
    }
    first = client.post("/api/v1/notifications/trigger", headers=_auth(token), json=payload)
    second = client.post("/api/v1/notifications/trigger", headers=_auth(token), json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"].get("throttled") is True

    bad_attachment = client.post(
        "/api/v1/attachments",
        headers=_auth(token),
        json={
            "file_name": "bad.bin",
            "content_type": "application/octet-stream",
            "file_size_bytes": 4,
            "file_content_base64": "dGVzdA==",
        },
    )
    assert bad_attachment.status_code == 422

    config_v1 = client.post(
        "/api/v1/operations/configurations",
        headers=_auth(token),
        json={"config_key": "accept_cfg", "config_value": "v1", "rollout_percent": 100},
    )
    config_v2 = client.post(
        "/api/v1/operations/configurations",
        headers=_auth(token),
        json={"config_key": "accept_cfg", "config_value": "v2", "rollout_percent": 10},
    )
    assert config_v1.status_code == 200
    assert config_v2.status_code == 200

    rolled_back = client.post(
        "/api/v1/operations/configurations/rollback",
        headers=_auth(token),
        params={"config_key": "accept_cfg"},
    )
    assert rolled_back.status_code == 200
    assert rolled_back.json()["data"]["config_value"] == "v1"


def test_sensitive_access_log_and_immutable_audit_behavior(client, db_session):
    _create_user(client, "accept_super", "abc12345")
    _create_user(client, "accept_target", "abc12345")

    super_user = db_session.scalar(select(User).where(User.username == "accept_super"))
    super_user.is_superuser = True
    db_session.commit()

    _grant_permissions(
        db_session,
        "accept_super",
        ["auth:sensitive:read", "auth:role:assign", "auth:permission:assign"],
    )

    token = _login(client, "accept_super", "abc12345").json()["data"]["access_token"]
    target_user = db_session.scalar(select(User).where(User.username == "accept_target"))

    read_resp = client.get(
        f"/api/v1/admin/security/users/{target_user.id}/sensitive-contact",
        headers=_auth(token),
        params={"reason": "acceptance_test"},
    )
    assert read_resp.status_code == 200

    access_logs = db_session.scalars(
        select(SensitiveAccessLog).where(
            SensitiveAccessLog.actor_user_id == super_user.id,
            SensitiveAccessLog.target_user_id == target_user.id,
        )
    ).all()
    assert len(access_logs) >= 1

    audit_entry = db_session.scalar(select(ImmutableAuditLog).order_by(ImmutableAuditLog.id.desc()))
    assert audit_entry is not None

    audit_entry.action = "tamper_attempt"
    try:
        db_session.commit()
        assert False, "immutable audit log mutation should fail"
    except Exception:
        db_session.rollback()
