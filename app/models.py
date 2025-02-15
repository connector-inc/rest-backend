import enum
from datetime import datetime
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
    verified = "verified"
    unverified = "unverified"
    deactivated = "deactivated"
    deleted = "deleted"


class User(SQLModel, table=True):
    __tablename__: str = "users"  # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default=datetime.today(),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    email: Annotated[
        EmailStr,
        AfterValidator(email_validator),
    ] = Field(sa_column=Column(String, index=True, unique=True))

    username: Optional[str] = Field(default=None, index=True, unique=True)
    full_name: Optional[str] = Field(default=None)
    status: UserStatus = Field(
        default=UserStatus.unverified,
        sa_column=Column(Enum(UserStatus, name="user_status")),
    )

    threads: list["Thread"] = Relationship(back_populates="user")
    replies: list["Reply"] = Relationship(back_populates="user", cascade_delete=True)


# class UserBase(SQLModel):
#     full_name: str
#     email: EmailStr
#     username: str

#     @field_validator("email")
#     def validate_email(cls, email: str) -> str:
#         BLACKLISTED_DOMAINS = ["tempmail.com", "disposable.com"]
#         MAX_EMAIL_LENGTH = 254  # RFC 5321
#         MIN_EMAIL_LENGTH = 3

#         # Check email length
#         if len(email) > MAX_EMAIL_LENGTH:
#             raise ValueError(f"Email must be less than {MAX_EMAIL_LENGTH} characters")
#         if len(email) < MIN_EMAIL_LENGTH:
#             raise ValueError(f"Email must be at least {MIN_EMAIL_LENGTH} characters")

#         # Basic format validation using regex
#         email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
#         if not re.match(email_regex, email):
#             raise ValueError("Invalid email format")

#         # Check domain not blacklisted
#         domain = email.split("@")[1].lower()
#         if domain in BLACKLISTED_DOMAINS:
#             raise ValueError("Email domain not allowed")

#         return email.lower()


class Thread(SQLModel, table=True):
    __tablename__: str = "threads"  # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default=datetime.today(),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default=datetime.today(),
        sa_column=Column(DateTime(timezone=True), nullable=False),
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
    created_at: datetime = Field(default=datetime.today(), sa_column=Column(DateTime))

    content: str = Field(index=True)
    media: list[str] = Field(sa_column=Column(ARRAY(String)))
    likes: int = Field(default=0)

    user_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    user: Optional["User"] = Relationship(back_populates="replies")

    thread_id: Optional[UUID] = Field(default=None, foreign_key="threads.id")
    thread: Optional["Thread"] = Relationship(back_populates="replies")
