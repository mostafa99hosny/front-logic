
# auth.py
from playwright.async_api import Page
from .config import TARGET_URL, SCREENSHOTS, ARTIFACTS_DIR
from .selectorsFile import LOGIN
from .utils import log, snap

async def login(page: Page, username: str, password: str):
    log(f"Navigating to: {TARGET_URL}")
    await page.goto(TARGET_URL, wait_until="domcontentloaded")

    # Allow potential bot-protection phase to settle
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

    await page.wait_for_selector(LOGIN["username"], timeout=30000)

    log("Filling login form ...")
    await page.fill(LOGIN["username"], username)
    await page.fill(LOGIN["password"], password)

    if SCREENSHOTS:
        await snap(page, f"{ARTIFACTS_DIR}/01-before-login.png")

    await page.click(LOGIN["submit"])

    try:
        await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass

    if SCREENSHOTS:
        await snap(page, f"{ARTIFACTS_DIR}/02-after-login.png")

    log("Login submitted. Waiting for transactions tab to settle ...")
