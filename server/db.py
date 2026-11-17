"""Database models and session handling."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy import JSON, Column, Index, event
from sqlmodel import Field, Session, SQLModel, create_engine

from server import config


def utcnow() -> datetime:
    return datetime.now(UTC)


class Account(SQLModel, table=True):
    username: str = Field(primary_key=True, max_length=16)
    bal: int = 0
    discordid: str | None = None
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utcnow)


class LedgerEntry(SQLModel, table=True):
    """Append-only record of every balance change."""

    __table_args__ = (Index("ix_ledger_gain_window", "username", "server_id", "created_at"),)

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, max_length=16)
    kind: str  # deposit / withdraw / transfer / migrate
    amount: int
    balance_after: int
    server_id: str | None = None  # hash of the API key the change was made with
    client_ip: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


engine = create_engine(
    config.DB_URL,
    connect_args={"check_same_thread": False} if config.DB_URL.startswith("sqlite") else {},
)

if engine.dialect.name == "sqlite":
    # Make every transaction take the write lock up front (BEGIN IMMEDIATE), so a
    # read-modify-write of a balance can't interleave with another one, even across
    # worker processes. See SQLAlchemy's "Serializable isolation / Savepoints" note for pysqlite.
    @event.listens_for(engine, "connect")
    def _disable_pysqlite_begin(dbapi_connection, connection_record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin_immediate(conn):
        conn.exec_driver_sql("BEGIN IMMEDIATE")


def create_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
