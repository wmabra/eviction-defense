"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    secret_key: str = "change-me"
    database_url: str = "sqlite:///./eviction_defense.db"
    app_url: str = "http://localhost:8000"
    debug: bool = True

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
