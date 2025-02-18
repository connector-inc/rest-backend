from fastapi import APIRouter


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={418: {"description": "I'm a teapot"}},
)


@router.post("/")
async def update_admin():
    return {"message": "Admin getting schwifty"}
