import logging
import os
import sys

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.services.telegram_service import TelegramService

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

def main() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env")
        sys.exit(1)

    service = TelegramService()
    
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", service.handle_start))
    application.add_handler(CommandHandler("undo", service.handle_undo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, service.handle_text))
    application.add_error_handler(service.handle_error)

    logger.info("Starting Telegram polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
