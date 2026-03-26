from sqlalchemy.orm import Session

from app.models.identity import SensitiveAccessLog


def record_sensitive_access(
    db: Session,
    *,
    actor_user_id: int | None,
    target_user_id: int | None,
    field_name: str,
    action: str,
    reason: str | None = None,
) -> None:
    db.add(
        SensitiveAccessLog(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            field_name=field_name,
            action=action,
            reason=reason,
        )
    )
