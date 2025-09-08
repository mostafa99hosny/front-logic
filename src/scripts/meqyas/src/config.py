
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

def _as_bool(v, default=False):
    if v is None:
        return default
    return str(v).strip().lower() in {"1","true","yes","on"}

TARGET_URL = os.getenv("TARGET_URL", "http://212.95.38.174:21802/home?tab-id=transactions")

HEADLESS = _as_bool(os.getenv("HEADLESS", "true"), default=False)
SLOW_MO_MS = int(os.getenv("SLOW_MO_MS", "0"))
DEFAULT_TIMEOUT_MS = int(os.getenv("DEFAULT_TIMEOUT_MS", "30000"))
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
TIMEZONE_ID = os.getenv("TIMEZONE_ID", "Asia/Riyadh")
CHROME_EXECUTABLE = os.getenv("CHROME_EXECUTABLE", "")

TRACE = _as_bool(os.getenv("TRACE", "true"), default=True)
SCREENSHOTS = _as_bool(os.getenv("SCREENSHOTS", "true"), default=True)
ARTIFACTS_DIR = os.getenv("ARTIFACTS_DIR", "artifacts")

MONGO_URI = os.getenv("MONGO_URI", "")
DB_NAME = os.getenv("DB_NAME", "projectForever")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "completed_reports")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
