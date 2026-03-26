"""Seed/demo data bootstrap for local acceptance verification.

Usage:
  python -m scripts.seed_demo
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import SessionLocal, transactional_session
from app.models.identity import Permission, Role, RolePermission, User, UserRole
from app.schemas.auth import UserCreateRequest
from app.services.auth_service import create_user

logger = logging.getLogger("seed")

DEFAULT_USERS = [
    ("seed_admin", "Admin12345", True),
    ("seed_cashier", "Cashier12345", False),
    ("seed_reviewer", "Reviewer12345", False),
    ("seed_ops_admin", "OpsAdmin12345", False),
]

DEFAULT_PERMISSIONS = [
    "system:health:read",
    "product:manage",
    "product:retrieve",
    "checkout:item:add",
    "order:create",
    "order:read",
    "order:manage",
    "promotion:manage",
    "payment:settle",
    "payment:read",
    "after_sales:handle",
    "after_sales:refund",
    "project:own",
    "project:read",
    "project:review",
    "project:manage",
    "project:deactivate",
    "attachment:manage",
    "attachment:read",
    "notification:send",
    "notification:read",
    "notification:subscribe",
    "operations:admin",
    "auth:role:assign",
    "auth:permission:assign",
    "auth:sensitive:read",
]

ROLE_PERMISSIONS = {
    "seed_admin_role": DEFAULT_PERMISSIONS,
    "seed_cashier_role": [
        "product:manage",
        "product:retrieve",
        "checkout:item:add",
        "order:create",
        "order:read",
        "payment:settle",
        "payment:read",
        "after_sales:handle",
        "after_sales:refund",
    ],
    "seed_reviewer_role": ["project:review", "project:read", "notification:read"],
    "seed_ops_role": ["operations:admin", "project:manage", "notification:send"],
}

USER_ROLE_MAP = {
    "seed_admin": "seed_admin_role",
    "seed_cashier": "seed_cashier_role",
    "seed_reviewer": "seed_reviewer_role",
    "seed_ops_admin": "seed_ops_role",
}


def _get_or_create_permission(db, code: str) -> Permission:
    existing = db.scalar(select(Permission).where(Permission.code == code))
    if existing is not None:
        return existing

    entity = Permission(code=code, description=f"Seeded permission: {code}")
    db.add(entity)
    db.flush()
    return entity


def _get_or_create_role(db, name: str) -> Role:
    existing = db.scalar(select(Role).where(Role.name == name))
    if existing is not None:
        return existing

    entity = Role(name=name, description=f"Seeded role: {name}")
    db.add(entity)
    db.flush()
    return entity


def _bind_role_permission(db, role_id: int, permission_id: int) -> None:
    existing = db.scalar(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
    )
    if existing is None:
        db.add(RolePermission(role_id=role_id, permission_id=permission_id))


def _bind_user_role(db, user_id: int, role_id: int) -> None:
    existing = db.scalar(select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id))
    if existing is None:
        db.add(UserRole(user_id=user_id, role_id=role_id))


def _get_or_create_user(db, username: str, password: str, is_superuser: bool) -> User:
    existing = db.scalar(select(User).where(User.username == username))
    if existing is not None:
        if is_superuser and not existing.is_superuser:
            existing.is_superuser = True
        return existing

    user = create_user(
        db,
        UserCreateRequest(
            username=username,
            password=password,
            contact_info=f"{username}@local.test",
        ),
        actor_user_id=None,
    )
    if is_superuser:
        user.is_superuser = True
    return user


def main() -> None:
    settings = get_settings()
    setup_logging(settings)

    db = SessionLocal()
    try:
        with transactional_session(db):
            permissions = {code: _get_or_create_permission(db, code) for code in DEFAULT_PERMISSIONS}
            roles = {name: _get_or_create_role(db, name) for name in ROLE_PERMISSIONS}

            for role_name, codes in ROLE_PERMISSIONS.items():
                role = roles[role_name]
                for code in codes:
                    _bind_role_permission(db, role.id, permissions[code].id)

            users: dict[str, User] = {}
            for username, password, is_superuser in DEFAULT_USERS:
                users[username] = _get_or_create_user(db, username, password, is_superuser)

            for username, role_name in USER_ROLE_MAP.items():
                _bind_user_role(db, users[username].id, roles[role_name].id)

        logger.info("seed_completed users=%s roles=%s permissions=%s", len(DEFAULT_USERS), len(ROLE_PERMISSIONS), len(DEFAULT_PERMISSIONS))
        logger.info("seed_credentials seed_admin/Admin12345 seed_cashier/Cashier12345")
    finally:
        db.close()


if __name__ == "__main__":
    main()
