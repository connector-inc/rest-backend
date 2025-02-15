from datetime import datetime, timedelta, timezone
from typing import Annotated

import boto3
import jwt
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import (
    AfterValidator,
    BaseModel,
    EmailStr,
    ValidationError,
)

from app.config import get_settings
from app.database import r as redis
from app.validators import email_validator

AWS_REGION_NAME = get_settings().aws_region_name
AWS_ACCESS_KEY_ID = get_settings().aws_access_key_id
AWS_SECRET_ACCESS_KEY = get_settings().aws_secret_access_key
SES_SENDER_EMAIL = get_settings().sender_email

JWT_SECRET_KEY = get_settings().jwt_secret_key
JWT_ALGORITHM = "HS256"

WEB_APP_URL = get_settings().web_app_url

LOGIN_TOKEN_EXPIRATION_MINUTES = 30
ACCESS_TOKEN_EXPIRATION_HOURS = 1
REFRESH_TOKEN_EXPIRATION_DAYS = 7


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

ses_client = boto3.client(
    "ses",
    region_name=AWS_REGION_NAME,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


def generate_login_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=LOGIN_TOKEN_EXPIRATION_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def generate_access_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc)
        + timedelta(hours=ACCESS_TOKEN_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def generate_refresh_token(email: str):
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc)
        + timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS),
    }
    refresh_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    redis.setex(
        f"refresh:{email}",
        REFRESH_TOKEN_EXPIRATION_DAYS * 24 * 60 * 60,
        refresh_token,
    )

    return refresh_token


def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail={"message": "Invalid token"})


def send_verification_email(to_email: str, token: str):
    try:
        login_url = f"{WEB_APP_URL}/auth/verify?token={token}"
        subject = "Log in to Connector"
        body = f"Click the link below to log in:\n\n{login_url}\n\nThis link will expire in {LOGIN_TOKEN_EXPIRATION_MINUTES} minutes."

        ses_client.send_email(
            Source=SES_SENDER_EMAIL,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}},
            },
        )
    except (BotoCoreError, NoCredentialsError):
        raise HTTPException(status_code=500, detail="Email sending failed.")


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
async def request_login(background_tasks: BackgroundTasks, request: LoginRequest):
    try:
        email = request.email
        token = generate_login_token(email)
        redis.setex(f"login:{email}", LOGIN_TOKEN_EXPIRATION_MINUTES * 60, token)
        background_tasks.add_task(send_verification_email, email, token)
        return {"message": "Login email sent"}

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(e)}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(e)}
        )
    except (BotoCoreError, NoCredentialsError, ClientError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to send email"},
        )


@router.get(
    "/verify",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bad Request"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Server Error"},
    },
)
async def verify(token: str):
    email = verify_token(token)
    is_token = redis.get(f"login:{email}") == token

    if not is_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token"
        )

    redis.delete(f"login:{token}")

    access_token = generate_access_token(email)
    refresh_token = generate_refresh_token(email)

    response = RedirectResponse(url=f"{WEB_APP_URL}/")
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRATION_HOURS * 60 * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRATION_DAYS * 24 * 60 * 60,
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
