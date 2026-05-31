from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from realtyscope.config import get_settings


def create_database_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    return create_engine(url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
