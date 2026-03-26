import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.identity import ImmutableAuditLog


def write_audit_log(
    db: Session,
    *,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    entry = ImmutableAuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details or {}, ensure_ascii=True),
    )
    db.add(entry)
