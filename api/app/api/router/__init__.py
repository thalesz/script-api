from fastapi import APIRouter

from app.api.router.imovel import router as imovel_router
from app.api.router.root import router as root_router

api_router = APIRouter()
api_router.include_router(root_router)
api_router.include_router(imovel_router)
