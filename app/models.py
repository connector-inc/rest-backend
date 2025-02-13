import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import (
    ARRAY,
    Column,
    DateTime,
    Enum,
    Field,
    Relationship,
    SQLModel,
    String,
)


class UserStatus(str, enum.Enum):
    verified = "verified"
    unverified = "unverified"
    deactivated = "deactivated"
    deleted = "deleted"


class User(SQLModel, table=True):
    __tablename__: str = "users"  # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default=datetime.today(), sa_column=Column(DateTime))

    name: str = Field()
    email: str = Field(index=True)
    username: str = Field(index=True)
    status: UserStatus = Field(
        default=UserStatus.unverified,
        sa_column=Column(Enum(UserStatus, name="user_status")),
    )

    threads: list["Thread"] = Relationship(back_populates="user")
    replies: list["Reply"] = Relationship(back_populates="user", cascade_delete=True)


class Thread(SQLModel, table=True):
    __tablename__: str = "threads"  # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default=datetime.today(), sa_column=Column(DateTime))
    updated_at: datetime = Field(default=datetime.today(), sa_column=Column(DateTime))

    content: str = Field(index=True)
    media: list[str] = Field(sa_column=Column(ARRAY(String)))
    likes: int = Field(default=0)
    edited: bool = Field(default=False)

    replies: list["Reply"] = Relationship(back_populates="thread", cascade_delete=True)

    user_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    user: Optional["User"] = Relationship(back_populates="threads")


class Reply(SQLModel, table=True):
    __tablename__: str = "replies"  # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default=datetime.today(), sa_column=Column(DateTime))

    content: str = Field(index=True)
    media: list[str] = Field(sa_column=Column(ARRAY(String)))
    likes: int = Field(default=0)

    user_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    user: Optional["User"] = Relationship(back_populates="replies")

    thread_id: Optional[UUID] = Field(default=None, foreign_key="threads.id")
    thread: Optional["Thread"] = Relationship(back_populates="replies")
