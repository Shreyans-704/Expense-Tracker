with open("app/api/routers/telegram.py", "r", encoding="utf-8") as f:
    content = f.read()

new_content = """from fastapi import APIRouter, Request, BackgroundTasks
from app.schemas.telegram import TelegramWebhookResponse
from app.services.telegram_service import TelegramService
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import os
import asyncio

router = APIRouter()

# Global application instance
_application = None

def get_application() -> Application:
    global _application
    if _application is None:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")
            
        _application = Application.builder().token(token).build()
        service = TelegramService()
        
        _application.add_handler(CommandHandler("start", service.handle_start))
        _application.add_handler(CommandHandler("balance", service.handle_balance))
        _application.add_handler(CommandHandler("undo", service.handle_undo))
        _application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, service.handle_text))
        _application.add_error_handler(service.handle_error)
        
        # Initialize the application
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_application.initialize())
        else:
            loop.run_until_complete(_application.initialize())
            
    return _application


@router.post("/webhook", response_model=TelegramWebhookResponse)
async def telegram_webhook(request: Request) -> TelegramWebhookResponse:
    update_data = await request.json()
    application = get_application()
    
    update = Update.de_json(update_data, application.bot)
    
    # Process update asynchronously
    await application.process_update(update)
    
    return TelegramWebhookResponse(ok=True, detail="Update processed")


@router.post("/set-webhook", response_model=TelegramWebhookResponse)
async def set_webhook() -> TelegramWebhookResponse:
    detail = await TelegramService.set_webhook()
    return TelegramWebhookResponse(ok=True, detail=detail)
"""

with open("app/api/routers/telegram.py", "w", encoding="utf-8") as f:
    f.write(new_content)
