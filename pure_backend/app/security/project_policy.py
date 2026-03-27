from dataclasses import dataclass


@dataclass(slots=True)
class ProjectScopeContext:
    actor_user_id: int
    actor_is_superuser: bool
    actor_permissions: set[str]


class ProjectPolicy:
    """Object-level authorization checks for entrepreneurship project resources."""

    @staticmethod
    def can_manage_own_project(context: ProjectScopeContext, applicant_user_id: int) -> bool:
        if context.actor_is_superuser:
            return True
        return context.actor_user_id == applicant_user_id

    @staticmethod
    def can_review_project(
        context: ProjectScopeContext,
        applicant_user_id: int,
        assigned_reviewer_user_id: int | None,
    ) -> bool:
        if context.actor_is_superuser:
            return True
        if "project:manage" in context.actor_permissions:
            return True
        if "project:review" not in context.actor_permissions:
            return False
        if context.actor_user_id == applicant_user_id:
            return False
        if assigned_reviewer_user_id is None:
            return True
        return context.actor_user_id == assigned_reviewer_user_id
