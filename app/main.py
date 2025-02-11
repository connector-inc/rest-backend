from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.dependencies import get_query_token, get_token_header
from .api.v1.routers import items, users
from .api.v1.internal import admin

app = FastAPI(
    title="Connector API",
    # docs_url=None,
    # redoc_url=None,
    # openapi_url=None,
    dependencies=[Depends(get_query_token)],
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

app.include_router(users.router, prefix="/v1")
app.include_router(items.router, prefix="/v1")
app.include_router(
    admin.router,
    prefix="/v1/admin",
    tags=["admin"],
    dependencies=[Depends(get_token_header)],
    responses={418: {"description": "I'm a teapot"}},
)


@app.get("/")
async def root():
    return {"message": "Hello Connectors!"}
