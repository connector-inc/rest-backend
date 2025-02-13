from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.database import SessionDep
from app.models import User

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.post(
    "/",
    responses={
        400: {"description": "Invalid request"},
        409: {"description": "User already exists"},
    },
)
async def create_user(session: SessionDep, user: User):
    try:
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
    except Exception as e:
        await session.rollback()
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=409, detail={"message": "User already exists"}
            )
        raise HTTPException(
            status_code=400, detail={"message": "Failed to create user"}
        )


@router.get(
    "/",
    responses={
        400: {"description": "Invalid request"},
    },
)
async def read_users(
    session: SessionDep, offset: int = 0, limit: Annotated[int, Query(le=10)] = 10
):
    try:
        users = await session.execute(select(User).offset(offset).limit(limit))
        return users.scalars().all()
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})


@router.get(
    "/{user_id}",
    responses={
        400: {"description": "Invalid request"},
        404: {"description": "User not found"},
    },
)
async def read_user(session: SessionDep, user_id: UUID):
    try:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar()
        if not user:
            raise HTTPException(status_code=404, detail={"message": "User not found"})
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})


@router.put(
    "/{user_id}",
    responses={
        400: {"description": "Invalid request"},
        404: {"description": "User not found"},
    },
)
async def update_user(session: SessionDep, user_id: UUID, user: User):
    try:
        db_user = await session.get(User, user_id)
        if not db_user:
            raise HTTPException(status_code=404, detail={"message": "User not found"})

        for key, value in user.model_dump(exclude={"id", "created_at"}).items():
            setattr(db_user, key, value)

        await session.commit()
        await session.refresh(db_user)
        return db_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})


@router.delete(
    "/{user_id}",
    responses={
        400: {"description": "Invalid request"},
        404: {"description": "User not found"},
    },
)
async def delete_user(session: SessionDep, user_id: UUID):
    try:
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail={"message": "User not found"})
        await session.delete(user)
        await session.commit()
        return {"message": "User deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)})
