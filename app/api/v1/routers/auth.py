import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID, uuid4

import jwt
import resend
import resend.exceptions
from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from pydantic import (
    AfterValidator,
    BaseModel,
    EmailStr,
    ValidationError,
)
from sqlmodel import select

from app.config import get_settings
from app.database import SessionDep
from app.database import r as redis
from app.models import User
from app.validators import email_validator

router = APIRouter(prefix="/auth", tags=["auth"])


resend.api_key = get_settings().resend_api_key


async def generate_login_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=get_settings().verification_email_expiry_minutes),
    }

    token = jwt.encode(
        payload, get_settings().jwt_secret_key, algorithm=get_settings().jwt_algorithm
    )

    redis.setex(
        f"login:{email}", get_settings().verification_email_expiry_minutes * 60, token
    )

    return token


async def verify_token(token: str):
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_secret_key,
            algorithms=[get_settings().jwt_algorithm],
        )
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
        )


async def send_verification_email(to_email: str, token: str):
    try:
        login_url = f"{get_settings().web_app_url}/auth/verify?token={token}"
        html = f"<p>Click the link below to log in:</p><br/><p><a href={login_url}>{login_url}</a></p><br/><p>This link will expire in {get_settings().verification_email_expiry_minutes} minutes.</p>"
        params: resend.Emails.SendParams = {
            "from": f"Connector <{get_settings().sender_email}>",
            "to": [to_email],
            "subject": "Log in to Connector",
            "html": html,
        }
        resend.Emails.send(params)
    except resend.exceptions.ResendError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email sending failed.",
        )


class LoginRequest(BaseModel):
    email: Annotated[EmailStr, AfterValidator(email_validator)]


@router.post(
    "/login",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Server Error"},
    },
)
async def request_login(request: LoginRequest, background_tasks: BackgroundTasks):
    try:
        email = request.email
        token = await generate_login_token(email)
        background_tasks.add_task(send_verification_email, email, token)
        return {"message": "Login email sent"}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/verify",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
    },
)
async def verify(token: str):
    try:
        email = await verify_token(token)
        is_valid_token = redis.get(f"login:{email}") == token

        if not is_valid_token:
            response = RedirectResponse(
                url=f"{get_settings().web_app_url}/login?error=invalid_token"
            )
            return response

        redis.delete(f"login:{email}")

        session_id = str(uuid4())
        redis.setex(
            f"session:{session_id}",
            get_settings().session_expiry_days * 24 * 60 * 60,
            json.dumps(
                {
                    "user_email": email,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_active": datetime.now(timezone.utc).isoformat(),
                }
            ),
        )

        response = RedirectResponse(url=f"{get_settings().web_app_url}/")
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=365 * 24 * 60 * 60,  # 365 days
            samesite="strict",
            httponly=True,
            secure=True,
            domain=get_settings().cookie_domain,
        )
        return response
    except Exception as e:
        logging.error(e)
        response = RedirectResponse(
            url=f"{get_settings().web_app_url}/login?error=invalid_token"
        )
        return response


@router.get(
    "/",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"description": "Not Found"},
    },
)
async def get_session(
    db_session: SessionDep,
    session_id: UUID,
    background_tasks: BackgroundTasks,
):
    try:
        session_key = f"session:{str(session_id)}"
        session_value: UUID = redis.get(session_key)  # type: ignore

        if not session_value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized."
            )

        session_json = json.loads(session_value)

        session_json["last_active"] = datetime.now(timezone.utc).isoformat()

        pipe = redis.pipeline()
        pipe.set(session_key, json.dumps(session_json))
        pipe.expire(session_key, get_settings().session_expiry_days * 24 * 60 * 60)
        background_tasks.add_task(pipe.execute)

        email = session_json.get("user_email")
        user = await db_session.execute(select(User).where(User.email == email))
        if not user.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException as e:
        logging.error(e)
        raise e
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post(
    "/logout",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
    },
)
async def logout(request: Request, background_tasks: BackgroundTasks):
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized."
            )

        session_key = f"session:{session_id}"
        background_tasks.add_task(redis.delete, session_key)

        response = RedirectResponse(url=f"{get_settings().web_app_url}/")
        response.delete_cookie("session_id", domain=get_settings().cookie_domain)

        return response
    except HTTPException as e:
        logging.error(e)
        raise e
    except Exception as e:
        logging.error(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
