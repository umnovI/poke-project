"""File with database configuration."""

from datetime import datetime
from typing import List

from sqlalchemy import CHAR, TEXT
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from sqlmodel import Field, Relationship, SQLModel, create_engine

from backend.secrets import DATABASE_URL


class THeaders(SQLModel, table=True):
    """Table with headers."""

    id: str = Field(primary_key=True, unique=True, sa_type=CHAR(32))
    etag: str = Field(sa_type=TEXT)

    content: List["TContent"] = Relationship(back_populates="header")


class TRequestedURL(SQLModel, table=True):
    """URLs we're sending head requests to."""

    id: str = Field(primary_key=True, unique=True, sa_type=CHAR(32))
    url: str = Field(sa_type=TEXT)
    requested: datetime
    etag: str = Field(sa_type=TEXT)


class TContent(SQLModel, table=True):
    """Table with content."""

    id: str = Field(primary_key=True, unique=True, foreign_key="theaders.id", sa_type=CHAR(32))
    content: bytes = Field(sa_type=MEDIUMBLOB)
    created: datetime
    updated: datetime | None = None
    # Foreign key must have the same type and length as the key it's referring to.
    reference_point: str = Field(
        foreign_key="trequestedurl.id",
        sa_type=CHAR(32),
        description="What remote url to check for staleness.",
        nullable=True,
    )
    source: str = Field(sa_type=TEXT, description="Where was the data taken from.")

    header: THeaders = Relationship(back_populates="content")


class TPartialContent(SQLModel, table=True):
    """Table with modified body. Depends on Hishel cache."""

    id: str = Field(primary_key=True, unique=True, sa_type=CHAR(32))
    content: bytes = Field(sa_type=MEDIUMBLOB)
    created: datetime
    updated: datetime | None = None
    source: str = Field(sa_type=TEXT, description="Where was the data taken from.")


db_engine = create_engine(DATABASE_URL)


async def create_tables():  # pragma: no cover
    """Create DB tables."""

    SQLModel.metadata.create_all(db_engine)


async def close_db_connections():  # pragma: no cover
    """Fully closing all currently checked in database connections."""

    db_engine.dispose()
