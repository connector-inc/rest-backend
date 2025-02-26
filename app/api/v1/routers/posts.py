import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import asc, select, desc

from app.database import get_session
from app.dependencies import get_current_user
from app.models import Post, User

router = APIRouter(prefix="/posts", tags=["posts"])


class CreatePostRequest(BaseModel):
    content: str
    media: list[str]


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_409_CONFLICT: {"description": "Conflict"},
    },
)
async def create_post(
    request: CreatePostRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    try:
        content = request.content.strip()

        post = Post(
            user_id=current_user.id,
            content=content,
            media=request.media,
        )

        db.add(post)
        await db.commit()
        await db.refresh(post)
        return {"message": "Post created successfully", "post_id": str(post.id)}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logging.error(f"Failed to create post: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create post"
        )


@router.get(
    "/",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
    },
)
async def get_posts(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    try:
        query = (
            select(Post)
            .join(User)
            .where(Post.user_id == User.id)
            .offset(offset)
            .limit(limit)
            .order_by(asc(Post.created_at))
        )
        posts = await db.execute(query)
        posts_with_user = [
            {
                "id": post.id,
                "created_at": post.created_at,
                "updated_at": post.updated_at,
                "content": post.content,
                "media": post.media,
                "likes": post.likes,
                "edited": post.edited,
                "user": {
                    "username": post.user.username,
                    "profile_picture": post.user.profile_picture,
                    "name": post.user.name,
                    "bio": post.user.bio,
                },
            }
            for post in posts.scalars()
        ]

        return posts_with_user
    except Exception as e:
        logging.error(f"Failed to get posts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get posts"
        )
