import base64

from sqlalchemy import select

from app.models.identity import Permission, Role, RolePermission, User, UserRole


def _create_user(client, username: str, password: str):
    return client.post(
        "/api/v1/auth/users",
        json={"username": username, "password": password, "contact_info": "+251900222222"},
    )


def _login(client, username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _grant_permissions(db_session, username: str, permission_codes: list[str]):
    user = db_session.scalar(select(User).where(User.username == username))
    role = Role(name=f"role-attn-{username}")
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


def _setup_user(client, db_session, username: str, perms: list[str]):
    _create_user(client, username, "abc12345")
    _grant_permissions(db_session, username, perms)
    return _login(client, username, "abc12345").json()["data"]["access_token"]


def test_valid_attachment_metadata(client, db_session):
    token = _setup_user(client, db_session, "att_valid", ["attachment:manage", "attachment:read"])

    content = b"valid-pdf-content"
    payload = {
        "file_name": "proposal.pdf",
        "content_type": "application/pdf",
        "file_size_bytes": len(content),
        "file_content_base64": base64.b64encode(content).decode("utf-8"),
    }

    resp = client.post("/api/v1/attachments", headers=_auth(token), json=payload)
    assert resp.status_code == 200
    assert resp.json()["data"]["content_type"] == "application/pdf"


def test_invalid_file_type(client, db_session):
    token = _setup_user(client, db_session, "att_type", ["attachment:manage"])

    content = b"text-file-content"
    resp = client.post(
        "/api/v1/attachments",
        headers=_auth(token),
        json={
            "file_name": "notes.txt",
            "content_type": "text/plain",
            "file_size_bytes": len(content),
            "file_content_base64": base64.b64encode(content).decode("utf-8"),
        },
    )
    assert resp.status_code == 422


def test_oversized_file_rejection(client, db_session):
    token = _setup_user(client, db_session, "att_large", ["attachment:manage"])

    content = b"small-content"
    resp = client.post(
        "/api/v1/attachments",
        headers=_auth(token),
        json={
            "file_name": "big.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 20 * 1024 * 1024 + 1,
            "file_content_base64": base64.b64encode(content).decode("utf-8"),
        },
    )
    assert resp.status_code == 422


def test_fingerprint_generation(client, db_session):
    token = _setup_user(client, db_session, "att_hash", ["attachment:manage"])

    content = b"fingerprint-source"
    resp = client.post(
        "/api/v1/attachments",
        headers=_auth(token),
        json={
            "file_name": "img.png",
            "content_type": "image/png",
            "file_size_bytes": len(content),
            "file_content_base64": base64.b64encode(content).decode("utf-8"),
        },
    )
    assert resp.status_code == 200
    fp = resp.json()["data"]["fingerprint_sha256"]
    assert len(fp) == 64


def test_event_triggered_notification_creation(client, db_session):
    sender = _setup_user(client, db_session, "noti_sender", ["notification:send"])
    recipient = _setup_user(client, db_session, "noti_recipient", ["notification:read", "notification:subscribe"])

    recipient_user = db_session.scalar(select(User).where(User.username == "noti_recipient"))

    sub = client.post(
        "/api/v1/notifications/subscriptions",
        headers=_auth(recipient),
        json={"event_type": "budget_alert", "channel": "in_site"},
    )
    assert sub.status_code == 200

    resp = client.post(
        "/api/v1/notifications/trigger",
        headers=_auth(sender),
        json={
            "recipient_user_id": recipient_user.id,
            "event_type": "budget_alert",
            "object_type": "project",
            "object_id": "P-101",
            "title": "Budget Alert",
            "message": "Budget reached 90%",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["event_type"] == "budget_alert"


def test_throttling_same_event_object(client, db_session):
    sender = _setup_user(client, db_session, "noti_sender_thr", ["notification:send"])
    recipient = _setup_user(client, db_session, "noti_recipient_thr", ["notification:read"])

    recipient_user = db_session.scalar(select(User).where(User.username == "noti_recipient_thr"))

    payload = {
        "recipient_user_id": recipient_user.id,
        "event_type": "pending_approval",
        "object_type": "project",
        "object_id": "P-200",
        "title": "Pending Approval",
        "message": "Project pending approval",
    }

    first = client.post("/api/v1/notifications/trigger", headers=_auth(sender), json=payload)
    second = client.post("/api/v1/notifications/trigger", headers=_auth(sender), json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"].get("throttled") is True


def test_read_receipt_update(client, db_session):
    sender = _setup_user(client, db_session, "noti_sender_read", ["notification:send"])
    recipient = _setup_user(client, db_session, "noti_recipient_read", ["notification:read"])

    recipient_user = db_session.scalar(select(User).where(User.username == "noti_recipient_read"))

    created = client.post(
        "/api/v1/notifications/trigger",
        headers=_auth(sender),
        json={
            "recipient_user_id": recipient_user.id,
            "event_type": "contract_expiration",
            "object_type": "project",
            "object_id": "P-300",
            "title": "Contract Expiration",
            "message": "Contract expires soon",
        },
    )
    notification_id = created.json()["data"]["id"]

    updated = client.post(
        f"/api/v1/notifications/{notification_id}/read",
        headers=_auth(recipient),
        json={"is_read": True},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["is_read"] is True
    assert updated.json()["data"]["read_at"] is not None


def test_unauthorized_notification_access(client, db_session):
    sender = _setup_user(client, db_session, "noti_sender_authz", ["notification:send"])
    owner = _setup_user(client, db_session, "noti_owner_authz", ["notification:read"])
    other = _setup_user(client, db_session, "noti_other_authz", ["notification:read"])

    owner_user = db_session.scalar(select(User).where(User.username == "noti_owner_authz"))

    created = client.post(
        "/api/v1/notifications/trigger",
        headers=_auth(sender),
        json={
            "recipient_user_id": owner_user.id,
            "event_type": "pending_approval",
            "object_type": "project",
            "object_id": "P-401",
            "title": "Pending",
            "message": "Approval pending",
        },
    )
    notification_id = created.json()["data"]["id"]

    denied = client.post(
        f"/api/v1/notifications/{notification_id}/read",
        headers=_auth(other),
        json={"is_read": True},
    )
    assert denied.status_code == 403
