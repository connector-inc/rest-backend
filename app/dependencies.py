from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
)
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.database import r as redis
from app.models import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    user_email = redis.get(f"session:{session_id}")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired"
        )

    user_query = await db.execute(select(User).where(User.email == user_email))
    user = user_query.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user


async def get_current_user_email(
    request: Request,
) -> EmailStr:
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    user_email = redis.get(f"session:{session_id}")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired"
        )

    return str(user_email)
