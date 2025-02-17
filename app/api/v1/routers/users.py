import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlmodel import select

from app.config import get_settings
from app.database import SessionDep
from app.database import r as redis
from app.models import User, UserGender

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


async def get_current_user_email(request: Request):
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            return RedirectResponse(url=f"{get_settings().web_app_url}/login")
            # raise HTTPException(
            #     status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            # )

        session_value = json.loads(redis.get(f"session:{session_id}"))  # type: ignore
        if not session_value:
            return RedirectResponse(url=f"{get_settings().web_app_url}/login")
            # raise HTTPException(
            #     status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            # )

        email = session_value.get("user_email")
        return email
    except Exception as e:
        logging.error(e)
        return RedirectResponse(url=f"{get_settings().web_app_url}/login")
        # raise HTTPException(
        #     status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        # )


class CreateUserRequest(BaseModel):
    name: str
    username: str
    gender: str


@router.post(
    "/",
    response_model=User,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_409_CONFLICT: {"description": "Conflict"},
    },
)
async def create_user(
    db_session: SessionDep,
    request: CreateUserRequest,
    email: str = Depends(get_current_user_email),
):
    try:
        user = User(email=email)
        user.name = request.name
        user.username = request.username
        if request.gender not in UserGender.__members__:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="")
        user.gender = UserGender[request.gender]

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return {"message": "User created successfully"}
    except ValueError as e:
        logging.error(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logging.error(e)
        await db_session.rollback()
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User already exists."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create user."
        )


class CheckUsernameAvailabilityRequest(BaseModel):
    username: str


@router.post("/username")
async def check_username_availability(
    db_session: SessionDep,
    request: CheckUsernameAvailabilityRequest,
    email: str = Depends(get_current_user_email),
):
    try:
        username_exists = await db_session.execute(
            select(User).where(User.username == request.username)
        )
        if username_exists.scalars().first():
            return {"message": "Username already exists."}
        return {"message": "Username is available."}
    except Exception as e:
        logging.error(e)
        return {"message": "Failed to check username."}


@router.get(
    "/",
    response_model=list[User],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
    },
)
async def read_users(
    db_session: SessionDep, offset: int = 0, limit: Annotated[int, Query(le=10)] = 10
):
    try:
        users = await db_session.execute(select(User).offset(offset).limit(limit))
        return users.scalars().all()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{user_id}",
    response_model=User,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_404_NOT_FOUND: {"description": "Not Found"},
    },
)
async def read_user(db_session: SessionDep, user_id: UUID):
    try:
        user = await db_session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/{user_id}",
    response_model=User,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_404_NOT_FOUND: {"description": "Not Found"},
    },
)
async def update_user(db_session: SessionDep, user_id: UUID, user_data: User):
    try:
        user = await db_session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        for key, value in user_data.model_dump().items():
            setattr(user, key, value)

        await db_session.commit()
        await db_session.refresh(user)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{user_id}",
    response_model=dict[str, str],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_404_NOT_FOUND: {"description": "Not Found"},
    },
)
async def delete_user(db_session: SessionDep, user_id: UUID):
    try:
        user = await db_session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )
        await db_session.delete(user)
        await db_session.commit()
        return {"message": "User deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
