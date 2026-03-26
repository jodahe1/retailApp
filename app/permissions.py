"""Permission boundary placeholders for future role/policy enforcement."""

from enum import StrEnum


class Permission(StrEnum):
    SYSTEM_HEALTH_READ = "system:health:read"

    PRODUCT_RETRIEVE = "product:retrieve"
    PRODUCT_MANAGE = "product:manage"
    CHECKOUT_ITEM_ADD = "checkout:item:add"

    ORDER_CREATE = "order:create"
    ORDER_READ = "order:read"
    ORDER_MANAGE = "order:manage"
    PROMOTION_MANAGE = "promotion:manage"

    PAYMENT_SETTLE = "payment:settle"
    PAYMENT_READ = "payment:read"


class Domain(StrEnum):
    SYSTEM = "system"
    CHECKOUT = "checkout"
    INVENTORY = "inventory"
    ENTREPRENEURSHIP = "entrepreneurship"
    PRODUCT = "product"
    POS = "pos"
    ORDER = "order"
    PROMOTION = "promotion"
    PAYMENT = "payment"
