from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=settings.db_pool_pre_ping,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def transactional_session(db: Session) -> Generator[Session, None, None]:
    """Explicit transaction boundary for service/repository write operations."""
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
