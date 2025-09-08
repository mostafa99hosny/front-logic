import asyncio
import sys

from playwright.async_api import async_playwright
from .config import settings
from .auth import login, apply_stealth
from .filters import run_filters
from .listing import scrape_all_pages_and_save


async def flow(username: str, password: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=settings.USER_DATA_DIR,
            headless=settings.HEADLESS,
            locale=settings.LOCALE,
            timezone_id=settings.TIMEZONE_ID,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        page = await browser.new_page()

        # Apply stealth BEFORE first navigation
        await apply_stealth(page)

        await page.goto(settings.TARGET_URL, wait_until="domcontentloaded")
        await login(page, username, password)

        # Apply filters
        await run_filters(page)
        print("✅ Filters applied. Reading records…")

        # Scrape all pages, save in Mongo
        scraped_count, upserted = await scrape_all_pages_and_save(page)
        print(f"✅ Done. Scraped {scraped_count} rows, upserted {upserted} in MongoDB "
              f"[{settings.DB_NAME}/{settings.COLLECTION_NAME}].")

        if not settings.HEADLESS:
            await page.wait_for_timeout(1500)
        await browser.close()


def main():
    # Args: username, password
    if len(sys.argv) < 3:
        print("Usage: python -m src.main <username> <password>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]

    asyncio.run(flow(username, password))


if __name__ == "__main__":
    main()
