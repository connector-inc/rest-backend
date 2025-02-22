import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.dependencies import get_current_user_email
from app.models import User, UserGender

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    name: str
    username: str
    gender: UserGender  # Use enum directly for better validation


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_409_CONFLICT: {"description": "Conflict"},
    },
)
async def create_user(
    request: CreateUserRequest,
    email: str = Depends(get_current_user_email),
    db: AsyncSession = Depends(get_session),
):
    try:
        # Check if user already exists
        existing_user = await db.execute(
            select(User).where(
                (User.email == email) | (User.username == request.username)
            )
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email or username already exists",
            )

        # Create new user
        user = User(
            email=email,
            name=request.name,
            username=request.username,
            gender=request.gender,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)
        return {"message": "User created successfully", "user_id": str(user.id)}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Failed to create user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create user"
        )


class CheckUsernameAvailabilityRequest(BaseModel):
    username: str


@router.post(
    "/check-username",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
    },
)
async def check_username_availability(
    request: CheckUsernameAvailabilityRequest,
    db: AsyncSession = Depends(get_session),
    user_email: EmailStr = Depends(get_current_user_email),
):
    try:
        result = await db.execute(select(User).where(User.username == request.username))
        user = result.scalar_one_or_none()

        if user:
            available = False
        else:
            available = True
        return {"available": available, "username": request.username}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Failed to check username availability: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to check username availability",
        )


@router.get("/check-user-created")
async def check_user_created(
    db: AsyncSession = Depends(get_session),
    user_email: EmailStr = Depends(get_current_user_email),
):
    user_query = await db.execute(select(User).where(User.email == user_email))
    user = user_query.scalars().first()
    if not user:
        created = False
    else:
        created = True

    return {"created": created}
