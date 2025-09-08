# main.py
import asyncio
import getpass
from datetime import datetime, timezone
import sys

from .browser import launch_browser
from .auth import login
from .actions import run_quick_search
from .pdf_flow import try_download_pdf
from .db import save_event
from .utils import log
from .eval_scraper import scrape_eval_model

async def flow(username: str, password: str, query: str):
    async with launch_browser() as page:
        # 1) Login
        await login(page, username, password)

        # 2) Run the quick search
        await run_quick_search(page, query)

        # 3) Try to download PDF (returns (bool, pdf_meta))
        pdf_ok, pdf_meta = await try_download_pdf(page, item_hint=query)

        # Record the quick search action (optional)
        save_event({
            "type": "quick_search_executed",
            "query": query,
            "pdf_attempted": True,
            "pdf_success": bool(pdf_ok),
            "ts": datetime.now(timezone.utc),
        })

        # 4) Scrape the evaluation model fields, INLINE the pdf info to payload
        try:
            data = await scrape_eval_model(page, pdf_meta=pdf_meta)
            save_event({
                "type": "eval_model_scraped",
                "query": query,
                "payload": data,             # <-- single record with pdf_file_path + pdf_url included
                "ts": datetime.now(timezone.utc),
            })
            log("Evaluation model scraped and saved (with PDF meta embedded).")
        except Exception as e:
            log(f"Failed to scrape evaluation model: {e}", "WARN")
            # save_event({
            #     "type": "eval_model_scrape_failed",
            #     "query": query,
            #     "error": str(e),
            #     "ts": datetime.now(timezone.utc),
            # })

        log("Done. (Next step: expand field coverage as needed)")

def main():
    print("\n=== FI Playwright Stealth Scraper (v2) ===")
    username = sys.argv[1]
    password = sys.argv[2]
    query = sys.argv[3]
    asyncio.run(flow(username, password, query))

if __name__ == "__main__":
    main()
