import json
from datetime import datetime, timezone

from fastapi import BackgroundTasks, Header, HTTPException, Request, status

from app.config import get_settings
from app.database import r as redis


async def get_token_header(x_token: str = Header()):
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")


async def get_query_token(token: str):
    if token != "jessica":
        raise HTTPException(status_code=400, detail="No Jessica token provided")


async def get_current_user_email(
    request: Request, background_tasks: BackgroundTasks
) -> str:
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized."
            )

        session_key = f"session:{session_id}"
        session_value: str = redis.get(session_key)  # type: ignore

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

        return session_json.get("user_email")
    except HTTPException as e:
        raise e
    # except Exception as e:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
