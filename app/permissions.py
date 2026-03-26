"""Permission boundary placeholders for future role/policy enforcement."""

from enum import StrEnum


class Permission(StrEnum):
    SYSTEM_HEALTH_READ = "system:health:read"

    PRODUCT_RETRIEVE = "product:retrieve"
    PRODUCT_MANAGE = "product:manage"
    CHECKOUT_ITEM_ADD = "checkout:item:add"


class Domain(StrEnum):
    SYSTEM = "system"
    CHECKOUT = "checkout"
    INVENTORY = "inventory"
    ENTREPRENEURSHIP = "entrepreneurship"
    PRODUCT = "product"
    POS = "pos"
