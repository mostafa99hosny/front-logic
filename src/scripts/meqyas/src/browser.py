# browser.py
import os
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, Page
from .config import HEADLESS, SLOW_MO_MS, DEFAULT_TIMEOUT_MS, USER_AGENT, CHROME_EXECUTABLE, TIMEZONE_ID, TRACE, ARTIFACTS_DIR
from .utils import log, ensure_dir
from .stealth import apply_stealth

def _attach_page_listeners(page: Page):
    # Proper callback registration (no decorator form for Playwright Python)
    def on_console(msg):
        try:
            log(f"Page console [{msg.type}] {msg.text()}")
        except Exception:
            pass

    def on_pageerror(err):
        try:
            log(f"Page error: {err}", "WARN")
        except Exception:
            pass

    def on_request(req):
        try:
            if req.is_navigation_request():
                log(f"Request: {req.method} {req.url}")
        except Exception:
            pass

    def on_response(res):
        try:
            if res.request.is_navigation_request():
                log(f"Response: {res.status} {res.url}")
        except Exception:
            pass

    page.on("console", on_console)
    page.on("pageerror", on_pageerror)
    page.on("request", on_request)
    page.on("response", on_response)

@asynccontextmanager
async def launch_browser():
    """Launch Chromium with stealth, tracing, and sensible defaults."""
    log(f"Launching Chromium (headless={HEADLESS}) ...")
    ensure_dir(ARTIFACTS_DIR)

    async with async_playwright() as p:
        launch_kwargs = {
            "headless": HEADLESS,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-gpu",
            ],
            "slow_mo": SLOW_MO_MS,
        }
        if CHROME_EXECUTABLE:
            launch_kwargs["executable_path"] = CHROME_EXECUTABLE

        browser: Browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            accept_downloads=True,
            user_agent=USER_AGENT,
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id=TIMEZONE_ID,
        )

        if TRACE:
            try:
                await context.tracing.start(screenshots=True, snapshots=True, sources=True)
                log("Tracing started.")
            except Exception as e:
                log(f"Could not start tracing: {e}", "WARN")

        page: Page = await context.new_page()
        page.set_default_timeout(DEFAULT_TIMEOUT_MS)
        _attach_page_listeners(page)

        # Apply stealth (robust shim + JS fallback)
        await apply_stealth(context, page)

        try:
            yield page
        finally:
            if TRACE:
                try:
                    trace_path = os.path.join(ARTIFACTS_DIR, "trace.zip")
                    await context.tracing.stop(path=trace_path)
                    log(f"Trace saved: {trace_path}")
                except Exception as e:
                    log(f"Could not save trace: {e}", "WARN")
            await context.close()
            await browser.close()
            log("Closing browser ...")
