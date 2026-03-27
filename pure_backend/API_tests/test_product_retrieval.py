from sqlalchemy import select

from app.models.identity import Permission, Role, RolePermission, User, UserRole


def _create_user(client, username: str, password: str):
    return client.post(
        "/api/v1/auth/users",
        json={"username": username, "password": password},
    )


def _login(client, username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _grant_permissions(db_session, username: str, permission_codes: list[str]):
    user = db_session.scalar(select(User).where(User.username == username))
    role = Role(name=f"role-{username}")
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


def _create_product(client, token: str, payload: dict):
    return client.post("/api/v1/products", json=payload, headers=_auth(token))


def test_barcode_match(client, db_session):
    _create_user(client, "cashier_bar", "abc12345")
    _grant_permissions(db_session, "cashier_bar", ["product:manage", "product:retrieve"])
    token = _login(client, "cashier_bar", "abc12345").json()["data"]["access_token"]

    _create_product(
        client,
        token,
        {
            "name": "Cola 500ml",
            "name_pinyin": "kele",
            "barcode": "6901111111111",
            "internal_code": "SKU-COLA-500",
            "unit_price": 4.5,
        },
    )

    resp = client.get("/api/v1/products/retrieve", params={"query": "6901111111111"}, headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["barcode"] == "6901111111111"


def test_pinyin_match(client, db_session):
    _create_user(client, "cashier_py", "abc12345")
    _grant_permissions(db_session, "cashier_py", ["product:manage", "product:retrieve"])
    token = _login(client, "cashier_py", "abc12345").json()["data"]["access_token"]

    _create_product(
        client,
        token,
        {
            "name": "Orange Juice",
            "name_pinyin": "chengzhi",
            "barcode": "6902222222222",
            "internal_code": "SKU-OJ-1L",
            "unit_price": 7.0,
        },
    )

    resp = client.get("/api/v1/products/retrieve", params={"query": "chengzhi"}, headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["name_pinyin"] == "chengzhi"


def test_internal_code_match(client, db_session):
    _create_user(client, "cashier_code", "abc12345")
    _grant_permissions(db_session, "cashier_code", ["product:manage", "product:retrieve"])
    token = _login(client, "cashier_code", "abc12345").json()["data"]["access_token"]

    _create_product(
        client,
        token,
        {
            "name": "Milk 1L",
            "name_pinyin": "niunai",
            "barcode": "6903333333333",
            "internal_code": "SKU-MILK-1L",
            "unit_price": 5.5,
        },
    )

    resp = client.get("/api/v1/products/retrieve", params={"query": "SKU-MILK-1L"}, headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["data"]["internal_code"] == "SKU-MILK-1L"


def test_inactive_product_rejection(client, db_session):
    _create_user(client, "cashier_inactive", "abc12345")
    _grant_permissions(
        db_session,
        "cashier_inactive",
        ["product:manage", "product:retrieve", "checkout:item:add"],
    )
    token = _login(client, "cashier_inactive", "abc12345").json()["data"]["access_token"]

    create_resp = _create_product(
        client,
        token,
        {
            "name": "Tea",
            "name_pinyin": "cha",
            "barcode": "6904444444444",
            "internal_code": "SKU-TEA-1",
            "unit_price": 3.0,
        },
    )
    product_id = create_resp.json()["data"]["product_id"]

    client.patch(
        f"/api/v1/products/{product_id}/status",
        json={"is_active": False},
        headers=_auth(token),
    )

    resp = client.post(
        "/api/v1/products/precheckout/items",
        json={"query": "6904444444444", "quantity": 1},
        headers=_auth(token),
    )
    assert resp.status_code == 423


def test_missing_product_handling(client, db_session):
    _create_user(client, "cashier_missing", "abc12345")
    _grant_permissions(db_session, "cashier_missing", ["product:retrieve"])
    token = _login(client, "cashier_missing", "abc12345").json()["data"]["access_token"]

    resp = client.get("/api/v1/products/retrieve", params={"query": "NO-SUCH-PRODUCT"}, headers=_auth(token))
    assert resp.status_code == 404


def test_unauthorized_access(client, db_session):
    _create_user(client, "cashier_no_perm", "abc12345")
    token = _login(client, "cashier_no_perm", "abc12345").json()["data"]["access_token"]

    resp = client.get("/api/v1/products/retrieve", params={"query": "6900000000000"}, headers=_auth(token))
    assert resp.status_code == 403
