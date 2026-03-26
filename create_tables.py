"""Script to manually create all database tables"""
from app.db.base import Base
from app.db.session import engine
from app.models.identity import (
    User, Role, Permission, UserRole, RolePermission,
    SessionToken, SensitiveAccessLog, ImmutableAuditLog
)
from app.models.product import Product

if __name__ == "__main__":
    print("Creating all tables...")
    print("Registered tables before create:", list(Base.metadata.tables.keys()))
    Base.metadata.create_all(bind=engine)
    print("\nTables created successfully!")
    print("Final tables:", list(Base.metadata.tables.keys()))
