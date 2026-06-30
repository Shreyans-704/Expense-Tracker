from fastapi import APIRouter

from app.api.routers import health, sheets, telegram

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(sheets.router, tags=["sheets"])
api_router.include_router(telegram.router, tags=["telegram"])
