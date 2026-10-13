from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings, sqlalchemy_database_url


@lru_cache
def get_engine() -> Engine:
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return create_engine(
        sqlalchemy_database_url(database_url),
        pool_pre_ping=True,
        pool_recycle=300,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with get_session_factory()() as session:
        yield session
