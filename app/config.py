from typing import Literal
import os
from dotenv import load_dotenv

from pydantic_settings import BaseSettings, SettingsConfigDict

# Explicitly load .env file for deployment environments like Render
load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./app/)
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        frozen=True,
    )

    PROJECT_NAME: str = "Ahody"
    NWT_USERNAME: str = ""
    NWT_PASSWORD: str = ""
    NT_USERNAME: str = ""
    NT_PASSWORD: str = ""
    NSD_USERNAME: str = ""
    NSD_PASSWORD: str = ""
    KURIREN_USERNAME: str = ""
    KURIREN_PASSWORD: str = ""
    NORRAN_USERNAME: str = ""
    NORRAN_PASSWORD: str = ""
    CORREN_USERNAME: str = ""
    CORREN_PASSWORD: str = ""
    EXPRESSEN_USERNAME: str = ""
    EXPRESSEN_PASSWORD: str = ""

    WEB_SCRAPING_MODEL: str = "gpt-4.1-mini"
    OPENAI_API_KEY: str = ""

    ENVIRONMENT: Literal["development", "production"] = "development"


settings = Settings()  # type: ignore

# Debug logging for deployment troubleshooting
if settings.ENVIRONMENT == "production":
    print(f"OPENAI_API_KEY loaded: {'✓' if settings.OPENAI_API_KEY else '✗'}")
    if settings.OPENAI_API_KEY:
        print(f"API Key starts with: {settings.OPENAI_API_KEY[:10]}...")
