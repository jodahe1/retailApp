from dataclasses import dataclass


@dataclass(slots=True)
class ObjectPolicyContext:
    actor_user_id: int
    actor_is_superuser: bool
    actor_permissions: set[str]


class ObjectPolicy:
    """Scaffolding for object-level authorization checks by resource ownership/scope."""

    @staticmethod
    def can_access_owned_resource(context: ObjectPolicyContext, owner_user_id: int) -> bool:
        if context.actor_is_superuser:
            return True
        return context.actor_user_id == owner_user_id

    @staticmethod
    def can_access_with_scope(context: ObjectPolicyContext, required_scope: str) -> bool:
        if context.actor_is_superuser:
            return True
        return required_scope in context.actor_permissions
