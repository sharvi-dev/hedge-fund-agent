"""
app/config.py

Loads environment variables and exposes a typed settings object.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    sec_user_agent: str  # required by SEC: e.g. "yourname@example.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
