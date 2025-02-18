import logging
from typing import Annotated

import jwt
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
    ValidationError,
)
from sqlmodel import select

from app.config import get_settings
from app.database import SessionDep
from app.database import r as redis
from app.dependencies import get_current_user
from app.jwt import (
    create_access_token,
    create_login_token,
    create_refresh_token,
    decode_jwt,
    decode_jwt_without_exception,
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
        token = create_login_token(email)
        background_tasks.add_task(
            redis.setex,
            f"login:{email}",
            get_settings().verification_email_expiry_minutes * 60,
            token,
        )
        background_tasks.add_task(send_verification_email, email, token)
        return {"message": "Login email sent"}  # Keep this line
    except ValidationError or ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/verify",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Server Error"},
    },
)
async def verify(token: str, response: Response, background_tasks: BackgroundTasks):
    try:
        payload = decode_jwt(token)
        email = payload.get("sub")
        is_valid_token = redis.get(f"login:{email}") == token

        if not is_valid_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

        background_tasks.add_task(redis.delete, f"login:{email}")

        access_token = create_access_token(data={"sub": email})  # Keep "sub"
        refresh_token = create_refresh_token(subject=email)

        # Store the refresh token in Redis (with jti as key)
        background_tasks.add_task(redis.set, f"refresh:{refresh_token}", "valid")

        # Set cookies
        response = RedirectResponse(url=f"{get_settings().web_app_url}/")
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=get_settings().access_token_expiry_minutes * 60,
            domain=get_settings().cookie_domain,
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=get_settings().refresh_token_expiry_days * 24 * 60 * 60,
            domain=get_settings().cookie_domain,
        )

        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Unexpected error during verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post(
    "/refresh",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Too Many Requests"},
    },
)
async def refresh(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
):
    # Rate limiting
    # client_ip = request.client.host
    # rate_limit_key = f"rate_limit:refresh:{client_ip}"
    # current_attempts = redis.incr(rate_limit_key)
    # if current_attempts == 1:
    #     redis.expire(rate_limit_key, 60)  # Set 60 seconds expiry
    # if current_attempts > 5:  # Max 5 attempts per minute
    #     raise HTTPException(
    #         status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    #         detail="Too many refresh attempts. Please try again later.",
    #     )

    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token"
        )

    try:
        payload = decode_jwt_without_exception(refresh_token)
        email = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        # Check if the refresh token is valid (exists in Redis)
        session_state = redis.get(f"refresh:{refresh_token}")
        print(session_state)
        if session_state != "valid":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        # --- Refresh Token Rotation ---
        background_tasks.add_task(
            redis.delete, f"refresh:{refresh_token}"
        )  # Invalidate the old refresh token

        new_access_token = create_access_token(data={"sub": email})
        new_refresh_token = create_refresh_token(subject=email)

        background_tasks.add_task(
            redis.set, f"refresh:{new_refresh_token}", "valid"
        )  # Store the new refresh token

        # response = Response(content=json.dumps({"access_token": new_access_token}))
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=get_settings().access_token_expiry_minutes * 60,
            domain=get_settings().cookie_domain,
        )
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=get_settings().refresh_token_expiry_days * 24 * 60 * 60,
            domain=get_settings().cookie_domain,
        )

        return {"message": "Access token refreshed"}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request, response: Response, background_tasks: BackgroundTasks
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        background_tasks.add_task(
            redis.delete, f"refresh:{refresh_token}"
        )  # Invalidate refresh token
    response = Response()
    response.delete_cookie("access_token", domain=get_settings().cookie_domain)
    response.delete_cookie("refresh_token", domain=get_settings().cookie_domain)
    return response


@router.get("/me")
async def read_users_me(
    db_session: SessionDep,
    current_user: dict[str, str] = Depends(get_current_user),
):
    email = current_user["email"]
    query = await db_session.execute(select(User).where(User.email == email))
    user = query.scalars().first()
    if not user:
        return {"message": "User not found"}
    return {"message": "User found"}
