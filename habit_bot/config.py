import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str


def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    database_url = (
        os.getenv("DATABASE_URL", "").strip()
        or os.getenv("DATABASE_PRIVATE_URL", "").strip()
        or os.getenv("DATABASE_PUBLIC_URL", "").strip()
        or os.getenv("POSTGRES_URL", "").strip()
    )

    if not bot_token:
        raise RuntimeError("BOT_TOKEN environment variable is required")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")

    return Settings(bot_token=bot_token, database_url=database_url)
