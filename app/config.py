from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./app/)
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        frozen=True,
    )

    PROJECT_NAME: str = "Articler"
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

    WEB_SCRAPING_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: str = ""

    ENVIRONMENT: Literal["development", "production"] = "development"


settings = Settings()  # type: ignore
