from playwright.async_api import Page
from .selectorsFile import SEARCH
from .config import SCREENSHOTS, ARTIFACTS_DIR
from .utils import log, snap

async def run_quick_search(page: Page, query: str):
    log("Locating quick search input ...")
    await page.wait_for_selector(SEARCH["quick_search"], timeout=30000)
    await page.fill(SEARCH["quick_search"], query)
    log(f"Filled quick search with: {query}")

    if SCREENSHOTS:
        await snap(page, f"{ARTIFACTS_DIR}/03-before-search-click.png")

    log("Clicking search button ...")
    await page.click(SEARCH["search_button"])

    # Let results load (can be refined with a dedicated results selector later)
    try:
        await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass

    if SCREENSHOTS:
        await snap(page, f"{ARTIFACTS_DIR}/04-after-search-click.png")

    log("Search click done. Page settled.")
