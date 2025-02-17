from datetime import datetime, timedelta, timezone
import json
from typing import Annotated
from uuid import uuid4

from fastapi.responses import RedirectResponse
import jwt
import resend
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import OAuth2PasswordBearer
from pydantic import (
    AfterValidator,
    BaseModel,
    EmailStr,
    ValidationError,
)
import resend.exceptions

from app.config import get_settings
from app.database import r as redis
from app.validators import email_validator


JWT_SECRET_KEY = get_settings().jwt_secret_key
JWT_ALGORITHM = "HS256"

WEB_APP_URL = get_settings().web_app_url

VERIFICATION_EMAIL_EXPIRATION_MINUTES = 30
SESSION_EXPIRATION_DAYS = 7


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

resend.api_key = get_settings().resend_api_key


def generate_login_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=VERIFICATION_EMAIL_EXPIRATION_MINUTES),
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    redis.setex(f"login:{email}", VERIFICATION_EMAIL_EXPIRATION_MINUTES * 60, token)

    return token


def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token."
        )


def send_verification_email(to_email: str, token: str):
    try:
        login_url = f"{WEB_APP_URL}/auth/verify?token={token}"
        html = f"<p>Click the link below to log in:</p><br/><p><a href={login_url}>{login_url}</a></p><br/><p>This link will expire in {VERIFICATION_EMAIL_EXPIRATION_MINUTES} minutes.</p>"

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


router = APIRouter(prefix="/auth", tags=["auth"])


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
        token = generate_login_token(email)
        background_tasks.add_task(send_verification_email, email, token)
        return {"message": "Login email sent"}

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/verify",
    # responses={
    #     status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
    #     status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Server Error"},
    # },
)
async def verify(token: str):
    email = verify_token(token)
    is_valid_token = redis.get(f"login:{email}") == token

    if not is_valid_token:
        # raise HTTPException(
        #     status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token."
        # )
        response = RedirectResponse(url=f"{WEB_APP_URL}/login?error=invalid_token")
        return response

    redis.delete(f"login:{email}")

    session_id = str(uuid4())
    redis.setex(
        f"session:{session_id}",
        SESSION_EXPIRATION_DAYS * 24 * 60 * 60,
        json.dumps(
            {
                "user_email": email,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_active": datetime.now(timezone.utc).isoformat(),
            }
        ),
    )

    response = RedirectResponse(url=f"{WEB_APP_URL}/")

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


# async def get_access_token(request: Request):
#     token = request.cookies.get("access_token")
#     print(token)
#     if not token:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Not authenticated",
#         )

#     return token


# @router.get("/me")
# async def read_current_user(access_token: str = Depends(get_access_token)):
#     return {"access_token": access_token}
