import enum
from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import UUID, uuid4

from pydantic import AfterValidator, EmailStr
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

from app.validators import email_validator


class UserStatus(str, enum.Enum):
    active = "active"
    deactivated = "deactivated"
    deleted = "deleted"


class UserGender(str, enum.Enum):
    male = "male"
    female = "female"
    prefer_not_to_say = "prefer_not_to_say"


class User(SQLModel, table=True):
    __tablename__: str = "users"  # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default=datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    status: UserStatus = Field(
        default=UserStatus.active,
        sa_column=Column(Enum(UserStatus, name="user_status")),
    )

    email: Annotated[EmailStr, AfterValidator(email_validator)] = Field(
        sa_column=Column(String, index=True, unique=True)
    )
    username: Optional[str] = Field(default=None, index=True, unique=True, min_length=3)
    name: Optional[str] = Field(default=None, min_length=3, max_length=30)
    gender: Optional[UserGender] = Field(
        default=None, sa_column=Column(Enum(UserGender, name="user_gender"))
    )
    profile_picture: Optional[str] = Field(default=None)
    bio: Optional[str] = Field(default=None)
    is_private: bool = Field(default=False)

    threads: list["Thread"] = Relationship(back_populates="user", cascade_delete=True)
    replies: list["Reply"] = Relationship(back_populates="user", cascade_delete=True)


class Thread(SQLModel, table=True):
    __tablename__: str = "threads"  # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default=datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )
    updated_at: datetime = Field(
        default=datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True))
    )

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
    created_at: datetime = Field(
        default=datetime.today(), sa_column=Column(DateTime(timezone=True))
    )

    content: str = Field(index=True)
    media: list[str] = Field(sa_column=Column(ARRAY(String)))
    likes: int = Field(default=0)

    user_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    user: Optional["User"] = Relationship(back_populates="replies")

    thread_id: Optional[UUID] = Field(default=None, foreign_key="threads.id")
    thread: Optional["Thread"] = Relationship(back_populates="replies")
