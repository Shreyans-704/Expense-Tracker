from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
load_dotenv()

from pydantic import AliasChoices, AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Telegram Expense Tracker", validation_alias="APP_NAME")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        validation_alias="APP_ENVIRONMENT",
    )
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")

    telegram_bot_token: SecretStr | None = Field(default=None, validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_webhook_secret: str | None = Field(
        default=None,
        validation_alias="TELEGRAM_WEBHOOK_SECRET",
    )
    telegram_webhook_url: AnyHttpUrl | None = Field(
        default=None,
        validation_alias="TELEGRAM_WEBHOOK_URL",
    )
    telegram_send_confirmation: bool = Field(
        default=True,
        validation_alias="TELEGRAM_SEND_CONFIRMATION",
    )

    google_sheet_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_SHEET_ID", "GOOGLE_SHEETS_SPREADSHEET_ID"),
    )
    google_sheets_range: str = Field(default="Expenses!A:F", validation_alias="GOOGLE_SHEETS_RANGE")
    google_service_account_file: str | None = Field(
        default="credentials.json",
        validation_alias=AliasChoices("GOOGLE_SERVICE_ACCOUNT_FILE", "GOOGLE_APPLICATION_CREDENTIALS"),
    )
    google_service_account_json: SecretStr | None = Field(
        default=None,
        validation_alias="GOOGLE_SERVICE_ACCOUNT_JSON",
    )

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"], validation_alias="ALLOWED_HOSTS")
    cors_origins: list[AnyHttpUrl] = Field(default_factory=list, validation_alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def telegram_api_base_url(self) -> str:
        if not self.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required for Telegram API calls.")
        return f"https://api.telegram.org/bot{self.telegram_bot_token.get_secret_value()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
