"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    secret_key: str = "change-me"
    database_url: str = "sqlite:///./eviction_defense.db"
    app_url: str = "https://evictions.help"
    debug: bool = True

    # Authorize.net
    authorize_login_id: str = ""
    authorize_transaction_key: str = ""
    authorize_sandbox: bool = True  # True = test mode, False = live
    product_price: int = 39500  # $395.00 in cents

    # LLM Provider (OpenAI, DeepSeek, or any OpenAI-compatible API)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"  # or "deepseek-chat", "gpt-4o", etc.

    # Google Cloud
    google_application_credentials: Optional[str] = None

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # SendGrid
    sendgrid_api_key: str = ""

    # DeepSeek (for chat intake)
    deepseek_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
