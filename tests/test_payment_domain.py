from decimal import Decimal

from sqlalchemy import select

from app.models.identity import Permission, Role, RolePermission, User, UserRole
from app.models.order import Order
from app.models.payment import PaymentRecord


def _create_user(client, username: str, password: str):
    return client.post("/api/v1/auth/users", json={"username": username, "password": password})


def _login(client, username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _grant_permissions(db_session, username: str, permission_codes: list[str]):
    user = db_session.scalar(select(User).where(User.username == username))
    role = Role(name=f"role-pay-{username}")
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


def _create_product(client, token: str):
    return client.post(
        "/api/v1/products",
        headers=_auth(token),
        json={
            "name": "Payment Test Product",
            "name_pinyin": "zhifu",
            "barcode": "6920000000000",
            "internal_code": "SKU-PAY-001",
            "unit_price": 10.0,
        },
    )


def _create_order(client, token: str):
    return client.post(
        "/api/v1/orders",
        headers=_auth(token),
        json={"lines": [{"product_query": "6920000000000", "quantity": 1}]},
    )


def test_cash_payment(client, db_session):
    _create_user(client, "cashier_pay_cash", "abc12345")
    _grant_permissions(db_session, "cashier_pay_cash", ["product:manage", "order:create", "payment:settle"])
    token = _login(client, "cashier_pay_cash", "abc12345").json()["data"]["access_token"]

    _create_product(client, token)
    order_resp = _create_order(client, token)
    order_id = order_resp.json()["data"]["id"]

    pay_resp = client.post(
        "/api/v1/payments/settle",
        headers=_auth(token),
        json={"order_id": order_id, "payments": [{"method": "cash", "amount": 10.0}]},
    )
    assert pay_resp.status_code == 200
    assert pay_resp.json()["data"]["order_status"] == "settled"


def test_mixed_split_payment(client, db_session):
    _create_user(client, "cashier_pay_split", "abc12345")
    _grant_permissions(db_session, "cashier_pay_split", ["product:manage", "order:create", "payment:settle"])
    token = _login(client, "cashier_pay_split", "abc12345").json()["data"]["access_token"]

    _create_product(client, token)
    order_id = _create_order(client, token).json()["data"]["id"]

    pay_resp = client.post(
        "/api/v1/payments/settle",
        headers=_auth(token),
        json={
            "order_id": order_id,
            "payments": [
                {"method": "cash", "amount": 4.0},
                {"method": "bank_card", "amount": 6.0, "offline_approval_code": "OFF1234"},
            ],
        },
    )
    assert pay_resp.status_code == 200
    assert pay_resp.json()["data"]["order_status"] == "settled"


def test_exact_settlement(client, db_session):
    _create_user(client, "cashier_pay_exact", "abc12345")
    _grant_permissions(db_session, "cashier_pay_exact", ["product:manage", "order:create", "payment:settle"])
    token = _login(client, "cashier_pay_exact", "abc12345").json()["data"]["access_token"]

    _create_product(client, token)
    order_id = _create_order(client, token).json()["data"]["id"]

    resp = client.post(
        "/api/v1/payments/settle",
        headers=_auth(token),
        json={"order_id": order_id, "payments": [{"method": "stored_value", "amount": 10.0, "offline_approval_code": "SV-1111"}]},
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["data"]["remaining_amount"])) == Decimal("0.00")


def test_overpayment_rejection(client, db_session):
    _create_user(client, "cashier_pay_over", "abc12345")
    _grant_permissions(db_session, "cashier_pay_over", ["product:manage", "order:create", "payment:settle"])
    token = _login(client, "cashier_pay_over", "abc12345").json()["data"]["access_token"]

    _create_product(client, token)
    order_id = _create_order(client, token).json()["data"]["id"]

    resp = client.post(
        "/api/v1/payments/settle",
        headers=_auth(token),
        json={"order_id": order_id, "payments": [{"method": "cash", "amount": 11.0}]},
    )
    assert resp.status_code == 422


def test_duplicate_settlement_protection(client, db_session):
    _create_user(client, "cashier_pay_dupe", "abc12345")
    _grant_permissions(db_session, "cashier_pay_dupe", ["product:manage", "order:create", "payment:settle"])
    token = _login(client, "cashier_pay_dupe", "abc12345").json()["data"]["access_token"]

    _create_product(client, token)
    order_id = _create_order(client, token).json()["data"]["id"]

    first = client.post(
        "/api/v1/payments/settle",
        headers=_auth(token),
        json={"order_id": order_id, "payments": [{"method": "cash", "amount": 10.0}]},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/payments/settle",
        headers=_auth(token),
        json={"order_id": order_id, "payments": [{"method": "cash", "amount": 1.0}]},
    )
    assert second.status_code == 409


def test_unauthorized_payment_attempt(client, db_session):
    _create_user(client, "cashier_pay_noauth", "abc12345")
    _grant_permissions(db_session, "cashier_pay_noauth", ["product:manage", "order:create"])
    token = _login(client, "cashier_pay_noauth", "abc12345").json()["data"]["access_token"]

    _create_product(client, token)
    order_id = _create_order(client, token).json()["data"]["id"]

    resp = client.post(
        "/api/v1/payments/settle",
        headers=_auth(token),
        json={"order_id": order_id, "payments": [{"method": "cash", "amount": 10.0}]},
    )
    assert resp.status_code == 403


def test_payment_order_status_consistency(client, db_session):
    _create_user(client, "cashier_pay_consistency", "abc12345")
    _grant_permissions(db_session, "cashier_pay_consistency", ["product:manage", "order:create", "payment:settle"])
    token = _login(client, "cashier_pay_consistency", "abc12345").json()["data"]["access_token"]

    _create_product(client, token)
    order_id = _create_order(client, token).json()["data"]["id"]

    part = client.post(
        "/api/v1/payments/settle",
        headers=_auth(token),
        json={"order_id": order_id, "payments": [{"method": "cash", "amount": 4.0}]},
    )
    assert part.status_code == 200
    assert part.json()["data"]["order_status"] == "partially_paid"

    final = client.post(
        "/api/v1/payments/settle",
        headers=_auth(token),
        json={"order_id": order_id, "payments": [{"method": "cash", "amount": 6.0}]},
    )
    assert final.status_code == 200
    assert final.json()["data"]["order_status"] == "settled"

    order = db_session.get(Order, order_id)
    assert Decimal(str(order.paid_amount)) == Decimal("10.00")
    payments = db_session.scalars(select(PaymentRecord).where(PaymentRecord.order_id == order_id)).all()
    assert len(payments) == 2
