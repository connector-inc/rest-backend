import enum
import random
import string
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

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

letters_and_digits = string.ascii_letters + string.digits


def random_id():
    return "".join(random.choices(letters_and_digits, k=12))


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

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
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

    posts: list["Post"] = Relationship(back_populates="user", cascade_delete=True)
    replies: list["Reply"] = Relationship(back_populates="user", cascade_delete=True)


class Post(SQLModel, table=True):
    __tablename__: str = "posts"  # type: ignore

    id: str = Field(default_factory=random_id, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )

    content: str = Field(index=True)
    media: list[str] = Field(sa_column=Column(ARRAY(String)))
    likes: int = Field(default=0)
    edited: bool = Field(default=False)

    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")

    user: Optional["User"] = Relationship(
        back_populates="posts", sa_relationship_kwargs=dict(lazy="selectin")
    )
    replies: list["Reply"] = Relationship(back_populates="post", cascade_delete=True)


class Reply(SQLModel, table=True):
    __tablename__: str = "replies"  # type: ignore

    id: str = Field(default_factory=random_id, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )

    content: str = Field(index=True)
    media: list[str] = Field(sa_column=Column(ARRAY(String)))
    likes: int = Field(default=0)

    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    post_id: Optional[str] = Field(default=None, foreign_key="posts.id")

    user: Optional["User"] = Relationship(back_populates="replies")
    post: Optional["Post"] = Relationship(back_populates="replies")
