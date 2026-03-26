from sqlalchemy import select

from app.models.identity import Permission, Role, RolePermission, User, UserRole


def _create_user(client, username: str, password: str):
    return client.post(
        "/api/v1/auth/users",
        json={"username": username, "password": password, "contact_info": "+251900000000"},
    )


def _login(client, username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_password_validation_min_length(client):
    resp = _create_user(client, "short_pwd_user", "abc1234")
    assert resp.status_code in (422, 400)


def test_login_success(client):
    create_resp = _create_user(client, "login_ok_user", "abc12345")
    assert create_resp.status_code == 200

    login_resp = _login(client, "login_ok_user", "abc12345")
    assert login_resp.status_code == 200
    data = login_resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_failure_lockout(client, db_session):
    create_resp = _create_user(client, "lock_user", "abc12345")
    assert create_resp.status_code == 200

    for _ in range(5):
        failed = _login(client, "lock_user", "wrong_password")
        assert failed.status_code == 401

    locked = _login(client, "lock_user", "abc12345")
    assert locked.status_code == 423


def test_protected_route_requires_auth(client):
    resp = client.get("/api/v1/protected/me")
    assert resp.status_code == 401


def test_permission_denial(client, db_session):
    _create_user(client, "no_perm_user", "abc12345")
    login_resp = _login(client, "no_perm_user", "abc12345")
    token = login_resp.json()["data"]["access_token"]

    denied = client.get(
        "/api/v1/protected/permission-test",
        headers=_auth_header(token),
    )
    assert denied.status_code == 403


def test_permission_granted(client, db_session):
    _create_user(client, "perm_user", "abc12345")

    role = Role(name="health-reader")
    perm = Permission(code="system:health:read")
    db_session.add_all([role, perm])
    db_session.flush()
    db_session.add(RolePermission(role_id=role.id, permission_id=perm.id))

    user = db_session.scalar(select(User).where(User.username == "perm_user"))
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    db_session.commit()

    login_resp = _login(client, "perm_user", "abc12345")
    token = login_resp.json()["data"]["access_token"]

    allowed = client.get(
        "/api/v1/protected/permission-test",
        headers=_auth_header(token),
    )
    assert allowed.status_code == 200
