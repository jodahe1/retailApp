"""Permission boundary placeholders for future role/policy enforcement."""

from enum import StrEnum


class Permission(StrEnum):
    SYSTEM_HEALTH_READ = "system:health:read"


class Domain(StrEnum):
    SYSTEM = "system"
    CHECKOUT = "checkout"
    INVENTORY = "inventory"
    ENTREPRENEURSHIP = "entrepreneurship"
