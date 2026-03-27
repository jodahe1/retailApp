from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from app.models.after_sales import AfterSalesOrder
from app.models.identity import Permission, Role, RolePermission, User, UserRole
from app.models.order import Order


def _create_user(client, username: str, password: str):
    return client.post("/api/v1/auth/users", json={"username": username, "password": password})


def _login(client, username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _grant_permissions(db_session, username: str, permission_codes: list[str]):
    user = db_session.scalar(select(User).where(User.username == username))
    role = Role(name=f"role-as-{username}")
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


def _prepare_settled_order(client, db_session, username: str):
    _create_user(client, username, "abc12345")
    _grant_permissions(
        db_session,
        username,
        ["product:manage", "order:create", "payment:settle", "after_sales:handle", "after_sales:refund"],
    )
    token = _login(client, username, "abc12345").json()["data"]["access_token"]

    client.post(
        "/api/v1/products",
        headers=_auth(token),
        json={
            "name": f"AS Product {username}",
            "name_pinyin": "tuihuo",
            "barcode": f"693{abs(hash(username)) % 10000000000:010d}"[:13],
            "internal_code": f"SKU-AS-{username}",
            "unit_price": 10.0,
        },
    )

    order_resp = client.post(
        "/api/v1/orders",
        headers=_auth(token),
        json={"lines": [{"product_query": f"SKU-AS-{username}", "quantity": 1}]},
    )
    order_id = order_resp.json()["data"]["id"]

    client.post(
        "/api/v1/payments/settle",
        headers=_auth(token),
        json={"order_id": order_id, "payments": [{"method": "cash", "amount": 10.0}]},
    )

    return token, order_id


def test_valid_return_within_7_days(client, db_session):
    token, order_id = _prepare_settled_order(client, db_session, "as_valid_return")

    resp = client.post(
        "/api/v1/after-sales/returns",
        headers=_auth(token),
        json={"original_order_id": order_id, "refund_amount": 5.0, "reason": "Customer return"},
    )
    assert resp.status_code == 200


def test_invalid_return_after_7_days(client, db_session):
    token, order_id = _prepare_settled_order(client, db_session, "as_expired_return")

    order = db_session.get(Order, order_id)
    order.created_at = order.created_at - timedelta(days=8)
    db_session.commit()

    resp = client.post(
        "/api/v1/after-sales/returns",
        headers=_auth(token),
        json={"original_order_id": order_id, "refund_amount": 5.0},
    )
    assert resp.status_code == 422


def test_refund_amount_exceeding_original_order(client, db_session):
    token, order_id = _prepare_settled_order(client, db_session, "as_refund_ceiling")

    resp = client.post(
        "/api/v1/after-sales/reverse-settlements",
        headers=_auth(token),
        json={"original_order_id": order_id, "refund_amount": 11.0, "idempotency_key": "refund-over-001"},
    )
    assert resp.status_code == 422


def test_duplicate_refund_request_idempotency(client, db_session):
    token, order_id = _prepare_settled_order(client, db_session, "as_idempotent")

    payload = {
        "original_order_id": order_id,
        "refund_amount": 4.0,
        "idempotency_key": "refund-idem-001",
    }

    first = client.post("/api/v1/after-sales/reverse-settlements", headers=_auth(token), json=payload)
    second = client.post("/api/v1/after-sales/reverse-settlements", headers=_auth(token), json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]


def test_exchange_creation(client, db_session):
    token, order_id = _prepare_settled_order(client, db_session, "as_exchange")

    resp = client.post(
        "/api/v1/after-sales/exchanges",
        headers=_auth(token),
        json={"original_order_id": order_id, "note": "Exchange to other item"},
    )
    assert resp.status_code == 200


def test_unauthorized_after_sales_action(client, db_session):
    _create_user(client, "as_unauth", "abc12345")
    _grant_permissions(db_session, "as_unauth", ["product:manage", "order:create", "payment:settle"])
    token = _login(client, "as_unauth", "abc12345").json()["data"]["access_token"]

    client.post(
        "/api/v1/products",
        headers=_auth(token),
        json={
            "name": "AS Unauthorized Product",
            "name_pinyin": "wq",
            "barcode": "6940000000000",
            "internal_code": "SKU-AS-UNAUTH",
            "unit_price": 10.0,
        },
    )
    order_resp = client.post(
        "/api/v1/orders",
        headers=_auth(token),
        json={"lines": [{"product_query": "SKU-AS-UNAUTH", "quantity": 1}]},
    )
    order_id = order_resp.json()["data"]["id"]

    resp = client.post(
        "/api/v1/after-sales/returns",
        headers=_auth(token),
        json={"original_order_id": order_id, "refund_amount": 5.0},
    )
    assert resp.status_code == 403


def test_reverse_settlement_consistency(client, db_session):
    token, order_id = _prepare_settled_order(client, db_session, "as_reverse_consistency")

    refund_resp = client.post(
        "/api/v1/after-sales/reverse-settlements",
        headers=_auth(token),
        json={"original_order_id": order_id, "refund_amount": 6.0, "idempotency_key": "refund-consistency-001"},
    )
    assert refund_resp.status_code == 200

    order = db_session.get(Order, order_id)
    assert Decimal(str(order.paid_amount)) == Decimal("4.00")
    assert order.status == "partially_paid"

    entries = db_session.scalars(
        select(AfterSalesOrder).where(AfterSalesOrder.original_order_id == order_id)
    ).all()
    assert len(entries) >= 1
