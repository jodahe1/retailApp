from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from app.models.identity import Permission, Role, RolePermission, User, UserRole
from app.models.order import Order, OrderStatus


def _create_user(client, username: str, password: str):
    return client.post("/api/v1/auth/users", json={"username": username, "password": password})


def _login(client, username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _grant_permissions(db_session, username: str, permission_codes: list[str]):
    user = db_session.scalar(select(User).where(User.username == username))
    role = Role(name=f"role-order-{username}")
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


def _create_promo(client, token: str, payload: dict):
    return client.post("/api/v1/orders/promotions", json=payload, headers=_auth(token))


def test_normal_order_creation(client, db_session):
    _create_user(client, "cashier_order_normal", "abc12345")
    _grant_permissions(
        db_session,
        "cashier_order_normal",
        ["product:manage", "order:create", "order:read", "promotion:manage"],
    )
    token = _login(client, "cashier_order_normal", "abc12345").json()["data"]["access_token"]

    _create_product(
        client,
        token,
        {
            "name": "Water",
            "name_pinyin": "shui",
            "barcode": "6905555555555",
            "internal_code": "SKU-WATER-1",
            "unit_price": 2.0,
        },
    )

    resp = client.post(
        "/api/v1/orders",
        json={"lines": [{"product_query": "6905555555555", "quantity": 2}]},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["data"]["final_amount"])) == Decimal("4.00")


def test_item_discount(client, db_session):
    _create_user(client, "cashier_item_disc", "abc12345")
    _grant_permissions(db_session, "cashier_item_disc", ["product:manage", "order:create"])
    token = _login(client, "cashier_item_disc", "abc12345").json()["data"]["access_token"]

    _create_product(
        client,
        token,
        {
            "name": "Bread",
            "name_pinyin": "mianbao",
            "barcode": "6906666666666",
            "internal_code": "SKU-BREAD-1",
            "unit_price": 5.0,
        },
    )

    resp = client.post(
        "/api/v1/orders",
        json={"lines": [{"product_query": "6906666666666", "quantity": 1, "item_discount_amount": 2.0}]},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["data"]["final_amount"])) == Decimal("3.00")


def test_whole_order_discount(client, db_session):
    _create_user(client, "cashier_order_disc", "abc12345")
    _grant_permissions(db_session, "cashier_order_disc", ["product:manage", "order:create"])
    token = _login(client, "cashier_order_disc", "abc12345").json()["data"]["access_token"]

    _create_product(
        client,
        token,
        {
            "name": "Rice",
            "name_pinyin": "mifan",
            "barcode": "6907777777777",
            "internal_code": "SKU-RICE-1",
            "unit_price": 10.0,
        },
    )

    resp = client.post(
        "/api/v1/orders",
        json={
            "lines": [{"product_query": "6907777777777", "quantity": 2}],
            "order_discount_amount": 5.0,
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["data"]["final_amount"])) == Decimal("15.00")


def test_spend_and_save(client, db_session):
    _create_user(client, "cashier_spend_save", "abc12345")
    _grant_permissions(
        db_session,
        "cashier_spend_save",
        ["product:manage", "order:create", "promotion:manage"],
    )
    token = _login(client, "cashier_spend_save", "abc12345").json()["data"]["access_token"]

    _create_product(
        client,
        token,
        {
            "name": "Oil",
            "name_pinyin": "you",
            "barcode": "6908888888888",
            "internal_code": "SKU-OIL-1",
            "unit_price": 60.0,
        },
    )

    _create_promo(
        client,
        token,
        {
            "name": "Spend 100 Save 10",
            "rule_type": "spend_and_save",
            "threshold_amount": 100.0,
            "discount_amount": 10.0,
        },
    )

    resp = client.post(
        "/api/v1/orders",
        json={"lines": [{"product_query": "6908888888888", "quantity": 2}]},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["data"]["final_amount"])) == Decimal("110.00")


def test_buy_and_get(client, db_session):
    _create_user(client, "cashier_buy_get", "abc12345")
    _grant_permissions(
        db_session,
        "cashier_buy_get",
        ["product:manage", "order:create", "promotion:manage"],
    )
    token = _login(client, "cashier_buy_get", "abc12345").json()["data"]["access_token"]

    create_resp = _create_product(
        client,
        token,
        {
            "name": "Soda",
            "name_pinyin": "qishui",
            "barcode": "6909999999999",
            "internal_code": "SKU-SODA-1",
            "unit_price": 10.0,
        },
    )
    product_id = create_resp.json()["data"]["product_id"]

    _create_promo(
        client,
        token,
        {
            "name": "Buy2Get1 Soda",
            "rule_type": "buy_and_get",
            "buy_quantity": 2,
            "get_quantity": 1,
            "applies_to_product_id": product_id,
        },
    )

    resp = client.post(
        "/api/v1/orders",
        json={"lines": [{"product_query": "6909999999999", "quantity": 3}]},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["data"]["final_amount"])) == Decimal("20.00")


def test_tiered_pricing(client, db_session):
    _create_user(client, "cashier_tiered", "abc12345")
    _grant_permissions(
        db_session,
        "cashier_tiered",
        ["product:manage", "order:create", "promotion:manage"],
    )
    token = _login(client, "cashier_tiered", "abc12345").json()["data"]["access_token"]

    create_resp = _create_product(
        client,
        token,
        {
            "name": "Noodles",
            "name_pinyin": "mian",
            "barcode": "6910000000000",
            "internal_code": "SKU-NOODLE-1",
            "unit_price": 6.0,
        },
    )
    product_id = create_resp.json()["data"]["product_id"]

    _create_promo(
        client,
        token,
        {
            "name": "Tiered Noodles",
            "rule_type": "tiered_pricing",
            "tier_quantity": 3,
            "tier_unit_price": 4.0,
            "applies_to_product_id": product_id,
        },
    )

    resp = client.post(
        "/api/v1/orders",
        json={"lines": [{"product_query": "6910000000000", "quantity": 3}]},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["data"]["final_amount"])) == Decimal("12.00")


def test_purchase_limit_rejection(client, db_session):
    _create_user(client, "cashier_limit", "abc12345")
    _grant_permissions(
        db_session,
        "cashier_limit",
        ["product:manage", "order:create", "promotion:manage"],
    )
    token = _login(client, "cashier_limit", "abc12345").json()["data"]["access_token"]

    create_resp = _create_product(
        client,
        token,
        {
            "name": "Egg",
            "name_pinyin": "jidan",
            "barcode": "6911111111111",
            "internal_code": "SKU-EGG-1",
            "unit_price": 1.0,
        },
    )
    product_id = create_resp.json()["data"]["product_id"]

    _create_promo(
        client,
        token,
        {
            "name": "Egg Limit",
            "rule_type": "purchase_limit",
            "purchase_limit_quantity": 5,
            "applies_to_product_id": product_id,
        },
    )

    resp = client.post(
        "/api/v1/orders",
        json={"lines": [{"product_query": "6911111111111", "quantity": 6}]},
        headers=_auth(token),
    )
    assert resp.status_code == 422


def test_auto_void_eligibility_after_30_minutes(client, db_session):
    _create_user(client, "cashier_void", "abc12345")
    _grant_permissions(
        db_session,
        "cashier_void",
        ["product:manage", "order:create", "order:manage"],
    )
    token = _login(client, "cashier_void", "abc12345").json()["data"]["access_token"]

    _create_product(
        client,
        token,
        {
            "name": "Soap",
            "name_pinyin": "xiangzao",
            "barcode": "6912222222222",
            "internal_code": "SKU-SOAP-1",
            "unit_price": 3.0,
        },
    )

    create_resp = client.post(
        "/api/v1/orders",
        json={"lines": [{"product_query": "6912222222222", "quantity": 1}]},
        headers=_auth(token),
    )
    order_id = create_resp.json()["data"]["id"]

    order = db_session.get(Order, order_id)
    order.created_at = order.created_at - timedelta(minutes=31)
    db_session.commit()

    run_resp = client.post("/api/v1/orders/maintenance/expire-unpaid", headers=_auth(token))
    assert run_resp.status_code == 200

    refreshed = db_session.get(Order, order_id)
    assert refreshed.status == OrderStatus.VOID


def test_pricing_consistency_edge_case(client, db_session):
    _create_user(client, "cashier_edge", "abc12345")
    _grant_permissions(db_session, "cashier_edge", ["product:manage", "order:create"])
    token = _login(client, "cashier_edge", "abc12345").json()["data"]["access_token"]

    _create_product(
        client,
        token,
        {
            "name": "Candy",
            "name_pinyin": "tang",
            "barcode": "6913333333333",
            "internal_code": "SKU-CANDY-1",
            "unit_price": 1.0,
        },
    )

    resp = client.post(
        "/api/v1/orders",
        json={
            "lines": [{"product_query": "6913333333333", "quantity": 1, "item_discount_amount": 2.0}],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 422
