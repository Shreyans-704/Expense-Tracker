from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, Field

class ParsedExpense(BaseModel):
    amount: Decimal
    item: str
    category: str
    notes: str
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ExpenseRecord(ParsedExpense):
    telegram_user_id: int
    chat_id: int
    message_id: int | None = None
    username: str | None = None
    raw_text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
