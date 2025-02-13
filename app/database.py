from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.config import settings

async_engine = create_async_engine(
    url=settings.database_url_async,
    echo=True,
    # Disable the PostgreSQL JIT to improve ENUM datatype handling
    # https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#disabling-the-postgresql-jit-to-improve-enum-datatype-handling
    connect_args={"server_settings": {"jit": "off"}},
)

async_session = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def drop_tables():
    async with async_engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.drop_all)


async def create_db_and_tables():
    async with async_engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)


async def get_session():
    async with async_session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
