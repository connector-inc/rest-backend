import logging
import uuid
from typing import Annotated

import resend
import resend.exceptions
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
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
)

from app.config import get_settings
from app.database import r as redis
from app.dependencies import get_current_user, get_current_user_email
from app.jwt import (
    create_login_token,
    decode_jwt,
)
from app.models import User
from app.validators import email_validator

router = APIRouter(prefix="/auth", tags=["auth"])

resend.api_key = get_settings().resend_api_key


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
            detail="Email sending failed",
        )


class LoginRequestBody(BaseModel):
    email: Annotated[EmailStr, AfterValidator(email_validator)]


@router.post(
    "/login",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Server Error"},
    },
)
async def login(
    request: Request,
    request_body: LoginRequestBody,
    background_tasks: BackgroundTasks,
):
    try:
        session_id = request.cookies.get("session_id")
        if session_id:
            current_user_email = redis.get(f"session:{session_id}")
            if current_user_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already logged in",
                )

        email = request_body.email
        print(email)
        token = create_login_token(email)
        background_tasks.add_task(
            redis.setex,
            f"login:{email}",
            get_settings().verification_email_expiry_minutes * 60,
            token,
        )
        background_tasks.add_task(send_verification_email, email, token)
        return {"message": "Successfully sent verification email"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Failed to send verification email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to send verification email",
        )


@router.get(
    "/verify",
)
async def verify(
    token: str,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
):
    try:
        session_id = request.cookies.get("session_id")
        if session_id:
            current_user_email = redis.get(f"session:{session_id}")
            if current_user_email:
                return RedirectResponse(
                    url=f"{get_settings().web_app_url}/",
                    status_code=status.HTTP_302_FOUND,
                )

        payload = decode_jwt(token)
        if not payload or "sub" not in payload:
            raise Exception("Invalid payload in token")

        email = payload["sub"]
        print(email)
        session_token = str(redis.get(f"login:{email}"))
        if not session_token:
            raise Exception("Login session expired")

        background_tasks.add_task(redis.delete, f"login:{email}")

        session_id = str(uuid.uuid4())
        session_expiry = get_settings().session_expiry_days * 24 * 60 * 60

        # Create session in Redis
        background_tasks.add_task(
            redis.setex,
            f"session:{session_id}",
            session_expiry,
            email,
        )

        # Create redirect response with session cookie
        response = RedirectResponse(
            url=f"{get_settings().web_app_url}/",
            status_code=status.HTTP_302_FOUND,
        )
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=session_expiry,
            domain=get_settings().cookie_domain,
        )

        return response
    except Exception as e:
        logging.error(f"Failed to verify token: {str(e)}")
        return RedirectResponse(
            url=f"{get_settings().web_app_url}/login?error=invalid_or_expired_token",
            status_code=status.HTTP_302_FOUND,
        )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    session_id = request.cookies.get("session_id")
    if session_id:
        background_tasks.add_task(redis.delete, f"session:{session_id}")

    response.delete_cookie(key="session_id")
    return {"message": "Successfully logged out"}


@router.get("/check-user-logged-in")
async def check_user_logged_in(
    current_user_email: EmailStr = Depends(get_current_user_email),
):
    return {"message": "User logged in", "email": current_user_email}
