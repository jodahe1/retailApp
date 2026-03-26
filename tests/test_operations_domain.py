from datetime import timedelta

from sqlalchemy import select

from app.models.identity import Permission, Role, RolePermission, User, UserRole
from app.models.operation import FeatureLineage, FeatureValue, OperationConfiguration
from app.security.tokens import utcnow


def _create_user(client, username: str, password: str):
    return client.post(
        "/api/v1/auth/users",
        json={"username": username, "password": password, "contact_info": "+251900333333"},
    )


def _login(client, username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _grant_permissions(db_session, username: str, permission_codes: list[str]):
    user = db_session.scalar(select(User).where(User.username == username))
    role = Role(name=f"role-ops-{username}")
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


def _setup_ops_admin(client, db_session, username: str) -> str:
    _create_user(client, username, "abc12345")
    _grant_permissions(db_session, username, ["operations:admin"])
    return _login(client, username, "abc12345").json()["data"]["access_token"]


def test_sliding_window_calculations(client, db_session):
    token = _setup_ops_admin(client, db_session, "ops_sw")

    client.post(
        "/api/v1/operations/features/definitions",
        headers=_auth(token),
        json={"code": "sw_metric", "name": "SW Metric", "ttl_seconds": 3600, "default_mode": "online"},
    )
    for v in [10, 20, 30]:
        client.post(
            "/api/v1/operations/features/values",
            headers=_auth(token),
            json={"feature_code": "sw_metric", "object_type": "store", "object_id": "S1", "value_numeric": v},
        )

    resp = client.get(
        "/api/v1/operations/features/sliding-window",
        headers=_auth(token),
        params={"feature_code": "sw_metric", "object_type": "store", "object_id": "S1", "window_minutes": 60},
    )
    assert resp.status_code == 200
    assert round(resp.json()["data"]["value"], 2) == 20.0


def test_ttl_hot_cold_routing(client, db_session):
    token = _setup_ops_admin(client, db_session, "ops_ttl")

    client.post(
        "/api/v1/operations/features/definitions",
        headers=_auth(token),
        json={"code": "ttl_metric", "name": "TTL Metric", "ttl_seconds": 1, "default_mode": "online"},
    )
    create_resp = client.post(
        "/api/v1/operations/features/values",
        headers=_auth(token),
        json={"feature_code": "ttl_metric", "object_type": "store", "object_id": "S2", "value_numeric": 5},
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["data"]["storage_layer"] == "hot"

    row = db_session.scalar(select(FeatureValue).where(FeatureValue.object_id == "S2"))
    row.expires_at = utcnow() - timedelta(seconds=5)
    row.storage_layer = "hot"
    db_session.commit()

    check = client.post(
        "/api/v1/operations/features/consistency-check",
        headers=_auth(token),
        json={"feature_code": "ttl_metric", "object_type": "store", "object_id": "S2"},
    )
    assert check.status_code == 200
    assert check.json()["data"]["is_consistent"] is False


def test_consistency_verification(client, db_session):
    token = _setup_ops_admin(client, db_session, "ops_cons")

    client.post(
        "/api/v1/operations/features/definitions",
        headers=_auth(token),
        json={"code": "cons_metric", "name": "Consistency", "ttl_seconds": 3600, "default_mode": "online"},
    )
    client.post(
        "/api/v1/operations/features/values",
        headers=_auth(token),
        json={"feature_code": "cons_metric", "object_type": "store", "object_id": "S3", "value_numeric": 2},
    )

    check = client.post(
        "/api/v1/operations/features/consistency-check",
        headers=_auth(token),
        json={"feature_code": "cons_metric", "object_type": "store", "object_id": "S3"},
    )
    assert check.status_code == 200
    assert check.json()["data"]["is_consistent"] is True


def test_lineage_persistence(client, db_session):
    token = _setup_ops_admin(client, db_session, "ops_lineage")

    client.post(
        "/api/v1/operations/features/definitions",
        headers=_auth(token),
        json={"code": "lin_metric", "name": "Lineage", "ttl_seconds": 3600, "default_mode": "offline"},
    )
    client.post(
        "/api/v1/operations/features/values",
        headers=_auth(token),
        json={
            "feature_code": "lin_metric",
            "object_type": "store",
            "object_id": "S4",
            "value_numeric": 11,
            "lineage_source": "etl",
            "lineage_run_id": "run-1",
        },
    )

    lineage = db_session.scalar(select(FeatureLineage).where(FeatureLineage.run_id == "run-1"))
    assert lineage is not None


def test_analytics_aggregation(client, db_session):
    token = _setup_ops_admin(client, db_session, "ops_analytics")

    resp = client.post(
        "/api/v1/operations/analytics/daily",
        headers=_auth(token),
        json={
            "metric_day": "2026-03-27T00:00:00Z",
            "transaction_volume": 100,
            "successful_transactions": 80,
            "activity_count": 50,
            "dispute_count": 5,
        },
    )
    assert resp.status_code == 200
    assert round(resp.json()["data"]["conversion_rate"], 2) == 0.8
    assert round(resp.json()["data"]["dispute_rate"], 2) == 0.05


def test_export_endpoint_response(client, db_session):
    token = _setup_ops_admin(client, db_session, "ops_export")

    client.post(
        "/api/v1/operations/analytics/daily",
        headers=_auth(token),
        json={
            "metric_day": "2026-03-27T00:00:00Z",
            "transaction_volume": 100,
            "successful_transactions": 70,
            "activity_count": 40,
            "dispute_count": 2,
        },
    )

    export_resp = client.get("/api/v1/operations/analytics/export", headers=_auth(token))
    assert export_resp.status_code == 200
    assert "metric_day,transaction_volume" in export_resp.text


def test_gradual_rollout_behavior(client, db_session):
    token = _setup_ops_admin(client, db_session, "ops_rollout")

    cfg = client.post(
        "/api/v1/operations/configurations",
        headers=_auth(token),
        json={"config_key": "risk_cfg", "config_value": "{}", "rollout_percent": 10},
    )
    config_id = cfg.json()["data"]["id"]

    updated = client.post(
        f"/api/v1/operations/configurations/{config_id}/rollout",
        headers=_auth(token),
        params={"rollout_percent": 60},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["rollout_percent"] == 60


def test_rollback_behavior(client, db_session):
    token = _setup_ops_admin(client, db_session, "ops_rollback")

    client.post(
        "/api/v1/operations/configurations",
        headers=_auth(token),
        json={"config_key": "cfg_rb", "config_value": "{\"v\":1}", "rollout_percent": 100},
    )
    second = client.post(
        "/api/v1/operations/configurations",
        headers=_auth(token),
        json={"config_key": "cfg_rb", "config_value": "{\"v\":2}", "rollout_percent": 50},
    )
    assert second.status_code == 200

    rolled = client.post(
        "/api/v1/operations/configurations/rollback",
        headers=_auth(token),
        params={"config_key": "cfg_rb"},
    )
    assert rolled.status_code == 200
    assert rolled.json()["data"]["config_value"] == "{\"v\":1}"


def test_unauthorized_config_changes(client, db_session):
    _create_user(client, "ops_noauth", "abc12345")
    token = _login(client, "ops_noauth", "abc12345").json()["data"]["access_token"]

    denied = client.post(
        "/api/v1/operations/configurations",
        headers=_auth(token),
        json={"config_key": "x", "config_value": "{}", "rollout_percent": 10},
    )
    assert denied.status_code == 403
