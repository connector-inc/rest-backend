from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.database import SessionDep
from app.models import User

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.post(
    "/",
    response_model=User,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_409_CONFLICT: {"description": "Conflict"},
    },
)
async def create_user(session: SessionDep, user_data: User):
    try:
        user = User(**user_data.model_dump())
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(e)}
        )
    except Exception as e:
        await session.rollback()
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "User already exists"},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Failed to create user"},
        )


@router.get(
    "/",
    response_model=list[User],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
    },
)
async def read_users(
    session: SessionDep, offset: int = 0, limit: Annotated[int, Query(le=10)] = 10
):
    try:
        users = await session.execute(select(User).offset(offset).limit(limit))
        return users.scalars().all()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(e)}
        )


@router.get(
    "/{user_id}",
    response_model=User,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_404_NOT_FOUND: {"description": "Not Found"},
    },
)
async def read_user(session: SessionDep, user_id: UUID):
    try:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail={"message": "User not found"})
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(e)}
        )


@router.put(
    "/{user_id}",
    response_model=User,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_404_NOT_FOUND: {"description": "Not Found"},
    },
)
async def update_user(session: SessionDep, user_id: UUID, user_data: User):
    try:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail={"message": "User not found"})

        for key, value in user_data.model_dump().items():
            setattr(user, key, value)

        await session.commit()
        await session.refresh(user)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(e)}
        )


@router.delete(
    "/{user_id}",
    response_model=dict[str, str],
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_404_NOT_FOUND: {"description": "Not Found"},
    },
)
async def delete_user(session: SessionDep, user_id: UUID):
    try:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail={"message": "User not found"}
            )
        await session.delete(user)
        await session.commit()
        return {"message": "User deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(e)}
        )
