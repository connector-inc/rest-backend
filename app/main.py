import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.v1.internal import admin
from app.api.v1.routers import auth, posts, users
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # if get_settings().environment == "production":
    #     from app.database import create_tables, drop_tables

    #     await drop_tables()
    #     await create_tables()
    yield


app = FastAPI(
    title="Connector API",
    openapi_url=get_settings().openapi_url,
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
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(posts.router)


@app.get("/", response_model=dict[str, str])
async def root():
    return {
        "message": "Hello Connectors!",
        "current_date": datetime.today().isoformat(),
    }


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


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
