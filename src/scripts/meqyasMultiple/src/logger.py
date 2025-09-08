import json
from datetime import datetime
from .config import settings

def _ts():
    return datetime.now().strftime("%H:%M:%S")

def log(event: str, message: str = "", **data):
    """Prints either text or JSON logs based on settings.LOG_JSON."""
    if settings.LOG_JSON:
        payload = {"ts": _ts(), "event": event, "message": message, **data}
        print(json.dumps(payload, ensure_ascii=False), flush=True)
    else:
        extra = " ".join(f"{k}={v}" for k, v in data.items() if v is not None)
        line = f"[{_ts()}] [{event}] {message} {extra}".strip()
        print(line, flush=True)
