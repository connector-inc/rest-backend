from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException, status

from app.config import get_settings


def create_login_token(email: str, expires_delta: Optional[timedelta] = None):
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=get_settings().verification_email_expiry_minutes
        )
    payload = {
        "sub": email,
        "exp": expire,
    }
    token = jwt.encode(
        payload,
        get_settings().jwt_private_key,
        algorithm=get_settings().jwt_algorithm,
    )

    return token


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
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
