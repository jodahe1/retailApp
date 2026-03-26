"""Script to manually create all database tables"""
from app.db.base import Base
from app.db.session import engine
from app.db import models  # noqa: F401

if __name__ == "__main__":
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
    print("Tables:", list(Base.metadata.tables.keys()))
