from fastapi import APIRouter, Request
from app.schemas.telegram import TelegramWebhookResponse
from app.services.telegram_service import TelegramService

router = APIRouter()


@router.post("/webhook", response_model=TelegramWebhookResponse)
async def telegram_webhook(request: Request) -> TelegramWebhookResponse:
    update = await request.json()
    result = await TelegramService().handle_update(update)
    return TelegramWebhookResponse(ok=True, detail=result)


@router.post("/set-webhook", response_model=TelegramWebhookResponse)
async def set_webhook() -> TelegramWebhookResponse:
    detail = await TelegramService.set_webhook()
    return TelegramWebhookResponse(ok=True, detail=detail)
