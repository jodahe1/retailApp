from sqlalchemy import select

from app.models.identity import Permission, Role, RolePermission, User, UserRole


def _create_user(client, username: str, password: str):
    return client.post(
        "/api/v1/auth/users",
        json={"username": username, "password": password, "contact_info": "+251900111111"},
    )


def _login(client, username: str, password: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def _grant_permissions(db_session, username: str, permission_codes: list[str]):
    user = db_session.scalar(select(User).where(User.username == username))
    role = Role(name=f"role-proj-{username}")
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


def _setup_applicant(client, db_session, username: str):
    _create_user(client, username, "abc12345")
    _grant_permissions(
        db_session,
        username,
        [
            "project:own",
            "project:read",
            "project:deactivate",
        ],
    )
    token = _login(client, username, "abc12345").json()["data"]["access_token"]
    return token


def _setup_reviewer(client, db_session, username: str):
    _create_user(client, username, "abc12345")
    _grant_permissions(db_session, username, ["project:review", "project:read"])
    token = _login(client, username, "abc12345").json()["data"]["access_token"]
    user = db_session.scalar(select(User).where(User.username == username))
    return token, user.id


def _setup_admin(client, db_session, username: str):
    _create_user(client, username, "abc12345")
    _grant_permissions(
        db_session,
        username,
        ["project:manage", "project:read", "project:deactivate", "project:review"],
    )
    token = _login(client, username, "abc12345").json()["data"]["access_token"]
    return token


def _create_project_payload(reviewer_id: int | None = None):
    payload = {
        "name": "Market Growth Initiative",
        "category": "retail-tech",
        "description": "Plan to expand retail support to rural stores.",
        "contact_phone": "+251900123456",
    }
    if reviewer_id is not None:
        payload["assigned_reviewer_user_id"] = reviewer_id
    return payload


def test_applicant_creates_project(client, db_session):
    applicant_token = _setup_applicant(client, db_session, "proj_applicant_create")

    resp = client.post(
        "/api/v1/projects",
        headers=_auth(applicant_token),
        json=_create_project_payload(),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "draft"
    assert data["current_version"] == 0


def test_applicant_edits_draft(client, db_session):
    applicant_token = _setup_applicant(client, db_session, "proj_applicant_edit")

    created = client.post(
        "/api/v1/projects",
        headers=_auth(applicant_token),
        json=_create_project_payload(),
    ).json()["data"]

    edited = client.patch(
        f"/api/v1/projects/{created['id']}",
        headers=_auth(applicant_token),
        json={"description": "Updated scope and revenue plan."},
    )
    assert edited.status_code == 200
    assert edited.json()["data"]["description"] == "Updated scope and revenue plan."


def test_submit_for_review(client, db_session):
    applicant_token = _setup_applicant(client, db_session, "proj_submit")

    project_id = client.post(
        "/api/v1/projects",
        headers=_auth(applicant_token),
        json=_create_project_payload(),
    ).json()["data"]["id"]

    submit_resp = client.post(
        f"/api/v1/projects/{project_id}/submit",
        headers=_auth(applicant_token),
        json={"submission_note": "Ready for review"},
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["data"]["status"] == "submitted"
    assert submit_resp.json()["data"]["current_version"] == 1


def test_rejection_and_resubmission(client, db_session):
    reviewer_token, reviewer_id = _setup_reviewer(client, db_session, "proj_reviewer")
    applicant_token = _setup_applicant(client, db_session, "proj_applicant_resubmit")

    project_id = client.post(
        "/api/v1/projects",
        headers=_auth(applicant_token),
        json=_create_project_payload(reviewer_id),
    ).json()["data"]["id"]

    client.post(
        f"/api/v1/projects/{project_id}/submit",
        headers=_auth(applicant_token),
        json={"submission_note": "please review"},
    )

    rejected = client.post(
        f"/api/v1/projects/{project_id}/reject",
        headers=_auth(reviewer_token),
        json={"reason": "Need more detailed financials"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["data"]["status"] == "rejected"

    resubmitted = client.post(
        f"/api/v1/projects/{project_id}/resubmit",
        headers=_auth(applicant_token),
        json={"submission_note": "Updated financial section"},
    )
    assert resubmitted.status_code == 200
    assert resubmitted.json()["data"]["status"] == "submitted"


def test_version_increment(client, db_session):
    reviewer_token, reviewer_id = _setup_reviewer(client, db_session, "proj_reviewer_ver")
    applicant_token = _setup_applicant(client, db_session, "proj_applicant_ver")

    project_id = client.post(
        "/api/v1/projects",
        headers=_auth(applicant_token),
        json=_create_project_payload(reviewer_id),
    ).json()["data"]["id"]

    client.post(f"/api/v1/projects/{project_id}/submit", headers=_auth(applicant_token), json={})
    client.post(
        f"/api/v1/projects/{project_id}/reject",
        headers=_auth(reviewer_token),
        json={"reason": "Need update"},
    )
    client.post(f"/api/v1/projects/{project_id}/resubmit", headers=_auth(applicant_token), json={})

    detail = client.get(f"/api/v1/projects/{project_id}", headers=_auth(applicant_token))
    assert detail.status_code == 200
    assert detail.json()["data"]["current_version"] == 2


def test_diff_summary_generation(client, db_session):
    reviewer_token, reviewer_id = _setup_reviewer(client, db_session, "proj_reviewer_diff")
    applicant_token = _setup_applicant(client, db_session, "proj_applicant_diff")

    project_id = client.post(
        "/api/v1/projects",
        headers=_auth(applicant_token),
        json=_create_project_payload(reviewer_id),
    ).json()["data"]["id"]

    client.post(f"/api/v1/projects/{project_id}/submit", headers=_auth(applicant_token), json={})
    client.post(
        f"/api/v1/projects/{project_id}/reject",
        headers=_auth(reviewer_token),
        json={"reason": "Update category and description"},
    )
    client.patch(
        f"/api/v1/projects/{project_id}",
        headers=_auth(applicant_token),
        json={"category": "retail-platform", "description": "Revised plan"},
    )
    client.post(f"/api/v1/projects/{project_id}/resubmit", headers=_auth(applicant_token), json={})

    versions = client.get(f"/api/v1/projects/{project_id}/versions", headers=_auth(applicant_token))
    assert versions.status_code == 200
    assert len(versions.json()["data"]) == 2
    assert "category:" in (versions.json()["data"][1]["diff_summary"] or "")


def test_object_level_authorization_denial(client, db_session):
    owner_token = _setup_applicant(client, db_session, "proj_owner_denied")
    other_token = _setup_applicant(client, db_session, "proj_other_denied")

    project_id = client.post(
        "/api/v1/projects",
        headers=_auth(owner_token),
        json=_create_project_payload(),
    ).json()["data"]["id"]

    denied = client.patch(
        f"/api/v1/projects/{project_id}",
        headers=_auth(other_token),
        json={"description": "malicious edit"},
    )
    assert denied.status_code == 403


def test_reviewer_admin_permitted_actions(client, db_session):
    reviewer_token, reviewer_id = _setup_reviewer(client, db_session, "proj_reviewer_allowed")
    admin_token = _setup_admin(client, db_session, "proj_admin_allowed")
    applicant_token = _setup_applicant(client, db_session, "proj_applicant_allowed")

    project_id = client.post(
        "/api/v1/projects",
        headers=_auth(applicant_token),
        json=_create_project_payload(reviewer_id),
    ).json()["data"]["id"]

    client.post(f"/api/v1/projects/{project_id}/submit", headers=_auth(applicant_token), json={})

    rejected = client.post(
        f"/api/v1/projects/{project_id}/reject",
        headers=_auth(reviewer_token),
        json={"reason": "Need documents"},
    )
    assert rejected.status_code == 200

    deactivated = client.post(
        f"/api/v1/projects/{project_id}/deactivate",
        headers=_auth(admin_token),
        json={"reason": "Administrative close"},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["data"]["status"] == "deactivated"
