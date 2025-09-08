
# utils.py
import os
from datetime import datetime
from pathlib import Path

def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    icons = {"INFO":"ℹ️", "OK":"✅", "ERR":"❌", "WARN":"⚠️"}
    icon = icons.get(level.upper(), "ℹ️")
    print(f"[{ts}] {icon} {level.upper():<4} | {msg}")

def ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)
    return path

async def snap(page, path: str):
    """Save a full-page screenshot to path."""
    ensure_dir(os.path.dirname(path))
    try:
        await page.screenshot(path=path, full_page=True)
        log(f"Saved screenshot: {path}")
    except Exception as e:
        log(f"Could not save screenshot {path}: {e}", "WARN")
