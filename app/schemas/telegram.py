from pydantic import BaseModel


class TelegramWebhookResponse(BaseModel):
    ok: bool
    detail: str
