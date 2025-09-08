from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError, Page
from .config import USER_DATA_DIR, TARGET_URL, NAV_TIMEOUT
from .selectors import REPORT_READY

def log(msg: str, level: str = "INFO"):
    print(f"[{level}] {msg}")

BLOCK_MARKERS = [
    "Sorry, you have been blocked",
    "Cloudflare Ray ID",
    "Attention Required!",
]

async def detect_cloudflare_block(page: Page) -> bool:
    try:
        html = await page.content()
        return any(marker in html for marker in BLOCK_MARKERS)
    except Exception:
        return False

async def launch_chrome_to_target():
    pw = await async_playwright().start()
    context = await pw.chromium.launch_persistent_context(
        USER_DATA_DIR,
        headless=False,
        channel="chrome",  # use real Chrome if installed
        viewport={"width": 1366, "height": 860},
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = await context.new_page()
    page.set_default_timeout(NAV_TIMEOUT)

    log(f"Opening target: {TARGET_URL}")
    await page.goto(TARGET_URL, wait_until="load")

    return pw, context, page

async def wait_for_manual_login(page: Page):
    log("Waiting for you to login manually (username, password, OTP)…")
    log("Tip: once you land on the report-create page, the bot will continue automatically.")

    while True:
        if await detect_cloudflare_block(page):
            log("Cloudflare block detected. Please try without VPN/proxy or contact the site.", "ERROR")
            raise SystemExit(1)

        try:
            await page.wait_for_selector(REPORT_READY, timeout=3000)
            log("Detected report page ready. ✅", "SUCCESS")
            return
        except PWTimeoutError:
            pass

        url = page.url or ""
        if "qima.taqeem.sa" in url and "/report/create/" in url:
            try:
                await page.wait_for_selector(REPORT_READY, timeout=5000)
                log("Detected report page via URL + ready marker. ✅", "SUCCESS")
                return
            except Exception:
                pass

        await page.wait_for_timeout(1000)

async def open_and_wait_manual():
    pw, ctx, page = await launch_chrome_to_target()
    await wait_for_manual_login(page)
    return pw, ctx, page
