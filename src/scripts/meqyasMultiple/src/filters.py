import asyncio
from datetime import datetime
from playwright.async_api import Page
from .selectors import SELECTORS
from .config import settings
from .db import save_filter_snapshot

async def human_delay():
    await asyncio.sleep(settings.ACTION_DELAY_MS / 1000)

async def open_filter_panel(page: Page) -> None:
    await page.wait_for_selector(SELECTORS["filter_panel_btn"], state="visible", timeout=30000)
    await page.click(SELECTORS["filter_panel_btn"])
    await human_delay()

async def set_status_completed(page: Page) -> None:
    await page.wait_for_selector(SELECTORS["status_input"], state="visible", timeout=30000)
    await page.click(SELECTORS["status_input"])
    await human_delay()
    value = "أكتملت"
    await page.fill(SELECTORS["status_input"], value)
    await human_delay()
    await page.keyboard.press("Enter")
    await human_delay()

async def click_show_results(page: Page) -> None:
    await page.wait_for_selector(SELECTORS["show_results_btn"], state="visible", timeout=30000)
    await page.click(SELECTORS["show_results_btn"])
    await human_delay()

async def run_filters(page: Page) -> str:
    await open_filter_panel(page)
    await set_status_completed(page)
    await click_show_results(page)
  
