from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import jwt
from fastapi import (
    HTTPException,
    status,
)

from app.config import get_settings


def create_login_token(email: str):
    expires_delta = timedelta(minutes=get_settings().verification_email_expiry_minutes)
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    encoded_jwt = jwt.encode(
        payload,
        get_settings().jwt_private_key,
        algorithm=get_settings().jwt_algorithm,
    )
    return encoded_jwt


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    payload = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=get_settings().access_token_expiry_minutes
        )
    payload.update({"exp": expire})
    encoded_jwt = jwt.encode(
        payload,
        get_settings().jwt_private_key,
        algorithm=get_settings().jwt_algorithm,
    )
    return encoded_jwt


def create_refresh_token(subject: str):  # sub is user's email in this case
    expires_delta = timedelta(days=get_settings().refresh_token_expiry_days)
    payload = {
        "sub": subject,
        "exp": datetime.now(timezone.utc) + expires_delta,
        "jti": str(uuid4()),  # Add a unique identifier (JWT ID)
    }
    encoded_jwt = jwt.encode(
        payload,
        get_settings().jwt_private_key,
        algorithm=get_settings().jwt_algorithm,
    )
    return encoded_jwt


def decode_jwt(token: str):
    try:
        payload = jwt.decode(
            token,
            get_settings().jwt_public_key,
            algorithms=[get_settings().jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def decode_jwt_without_exception(token: str):
    payload = jwt.decode(
        token,
        get_settings().jwt_public_key,
        algorithms=[get_settings().jwt_algorithm],
    )
    return payload
