from dataclasses import dataclass


@dataclass(slots=True)
class ProductScopeContext:
    actor_user_id: int
    actor_is_superuser: bool
    actor_permissions: set[str]


class ProductPolicy:
    """Object-level hook scaffold for future store/resource scoping in product retrieval."""

    @staticmethod
    def can_access_store_product(context: ProductScopeContext, store_id: int | None) -> bool:
        if context.actor_is_superuser:
            return True
        # Placeholder until store ownership/scope mapping is introduced.
        return True
