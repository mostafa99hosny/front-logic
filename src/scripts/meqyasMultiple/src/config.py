from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    TARGET_URL: str = os.getenv("TARGET_URL", "http://212.95.38.174:21802/home?tab-id=transactions")
    HEADLESS: bool = os.getenv("HEADLESS", "false").lower() == "true"
    ACTION_DELAY_MS: int = int(os.getenv("ACTION_DELAY_MS", "400"))

    USERNAME: str | None = os.getenv("USERNAME") or None
    PASSWORD: str | None = os.getenv("PASSWORD") or None

    MONGO_URI: str = os.getenv("MONGO_URI", "")
    DB_NAME: str = os.getenv("DB_NAME", "projectForever")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "reportHeaders")

    # Browser prefs
    LOCALE: str = "ar-SA"
    TIMEZONE_ID: str = "Asia/Riyadh"
    USER_DATA_DIR: str = os.getenv("USER_DATA_DIR", "./user_data")

    # Logging
    LOG_JSON: bool = os.getenv("LOG_JSON", "false").lower() == "true"

settings = Settings()
