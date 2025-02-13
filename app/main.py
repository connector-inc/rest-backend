from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.v1.internal import admin
from app.api.v1.routers import users
from app.config import settings
from app.database import create_db_and_tables, drop_tables
from app.dependencies import get_query_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    await drop_tables()
    await create_db_and_tables()
    yield


app = FastAPI(
    title="Connector API",
    openapi_url=settings.openapi_url,
    root_path=settings.root_path,
    dependencies=[Depends(get_query_token)],
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)


origins = [
    "http://localhost:3000",
    "https://localhost:3000",
    "https://connector.rocks",
    "https://www.connector.rocks",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(admin.router)

app.include_router(users.router)


# You can test it by modifying the root endpoint to:
@app.get("/")
async def root():
    current_date, current_time = datetime.today().date(), datetime.today().time()
    return {
        "message": "Hello Connectors!",
        "currentDate": current_date,
        "currentTime": current_time,
    }
