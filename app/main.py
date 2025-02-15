from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.v1.internal import admin
from app.api.v1.routers import auth, users
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # from app.database import create_db_and_tables, drop_tables

    # await drop_tables()
    # await create_db_and_tables()
    yield


app = FastAPI(
    title="Connector API",
    openapi_url=get_settings().openapi_url,
    root_path=get_settings().root_path,
    # dependencies=[Depends(get_query_token)],
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
app.include_router(auth.router)


@app.get("/", response_model=dict[str, str])
async def root():
    current_date, current_time = (
        datetime.today().date().isoformat(),
        datetime.today().time().isoformat(),
    )
    return {
        "message": "Hello Connectors!",
        "currentDate": current_date,
        "currentTime": current_time,
    }


# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     """
#     Custom exception handler for validation errors
#     """
#     return ORJSONResponse(
#         status_code=422,
#         content={
#             "message": "Validation error",
#             "details": [
#                 {"loc": error["loc"], "message": error["message"], "type": error["type"]}
#                 for error in exc.errors()
#             ],
#         },
#     )
