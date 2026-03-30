from fastapi import APIRouter

from app.controllers.root_controller import get_root_message

router = APIRouter(tags=["root"])


@router.get("/")
def read_root() -> dict:
    return get_root_message()
