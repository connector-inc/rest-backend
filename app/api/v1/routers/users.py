import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import BaseModel
from sqlmodel import select

from app.database import SessionDep
from app.dependencies import get_current_user
from app.models import User, UserGender

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    name: str
    username: str
    gender: str


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
    db_session: SessionDep,
    request: CreateUserRequest,
    current_user=Depends(get_current_user),
):
    try:
        email = current_user["email"]
        user = User(email=email)
        user.name = request.name
        user.username = request.username
        user.gender = UserGender[request.gender]

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        return {"message": "User created successfully"}
    except HTTPException as e:
        raise e
    except ValueError as e:
        logging.error(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logging.error(e)
        await db_session.rollback()
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create user"
        )


class CheckUsernameAvailabilityRequest(BaseModel):
    username: str


@router.post(
    "/attempt/username",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
    },
)
async def check_username_availability(
    db_session: SessionDep,
    request: CheckUsernameAvailabilityRequest,
    _=Depends(get_current_user),
):
    try:
        username_exists = await db_session.execute(
            select(User).where(User.username == request.username)
        )
        if username_exists.scalars().first():
            return {"message": "Username already exists"}
        return {"message": "Username is available"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to check username"
        )


# @router.get(
#     "/",
#     responses={
#         status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
#         status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
#         status.HTTP_404_NOT_FOUND: {"description": "Not Found"},
#     },
# )
# async def read_me(
#     db_session: SessionDep,
#     email: str = Depends(get_current_user),
# ):
#     try:
#         query = await db_session.execute(select(User).where(User.email == email))
#         user = query.scalars().first()
#         if not user:
#             print("User not found")
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
#             )
#         return {"user": user}
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         logging.error(e)
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get user"
#         )


# @router.get(
#     "/",
#     responses={
#         status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
#     },
# )
# async def read_users(
#     db_session: SessionDep,
#     offset: int = 0,
#     limit: Annotated[int, Query(le=10)] = 10,
#     _=Depends(get_current_user_email),
# ):
#     try:
#         users = await db_session.execute(select(User).offset(offset).limit(limit))
#         return users.scalars().all()
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# @router.get(
#     "/{user_id}",
#     responses={
#         status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
#         status.HTTP_404_NOT_FOUND: {"description": "Not Found"},
#     },
# )
# async def read_user(
#     db_session: SessionDep,
#     user_id: UUID,
#     _=Depends(get_current_user_email),
# ):
#     try:
#         user = await db_session.get(User, user_id)
#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
#             )
#         return user
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# @router.put(
#     "/{user_id}",
#     responses={
#         status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
#         status.HTTP_404_NOT_FOUND: {"description": "Not Found"},
#     },
# )
# async def update_user(
#     db_session: SessionDep,
#     user_id: UUID,
#     user_data: User,
#     _=Depends(get_current_user_email),
# ):
#     try:
#         user = await db_session.get(User, user_id)
#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
#             )

#         for key, value in user_data.model_dump().items():
#             setattr(user, key, value)

#         await db_session.commit()
#         await db_session.refresh(user)
#         return {"message": "User updated successfully"}
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# @router.delete(
#     "/{user_id}",
#     status_code=status.HTTP_204_NO_CONTENT,
#     responses={
#         status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
#         status.HTTP_404_NOT_FOUND: {"description": "Not Found"},
#     },
# )
# async def delete_user(db_session: SessionDep, user_id: UUID):
#     try:
#         user = await db_session.get(User, user_id)
#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
#             )
#         await db_session.delete(user)
#         await db_session.commit()
#     except ValueError as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
