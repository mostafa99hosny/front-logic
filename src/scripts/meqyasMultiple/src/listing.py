import asyncio
from datetime import datetime
from typing import Dict, List, Tuple, Any
from playwright.async_api import Page, Locator, TimeoutError as PWTimeoutError
from .config import settings
from .selectors import SELECTORS
from .db import upsert_records
from .logger import log

# ---------- small helpers ----------
async def _sleep():
    await asyncio.sleep(settings.ACTION_DELAY_MS / 1000)

async def _text_or_empty(loc: Locator) -> str:
    try:
        t = await loc.first.text_content()
        return (t or "").strip()
    except Exception:
        return ""

def _loc(row: Locator, css: str) -> Locator:
    return row.locator(css)

# ---------- record parsing (concurrent) ----------
async def extract_record_from_row(row: Locator) -> Dict[str, Any]:
    """
    Pulls the most useful fields. Uses Playwright's :has-text engine, but groups awaits
    with asyncio.gather to cut round-trips and speed up overall scraping.
    """
    locs = {
        "code":        _loc(row, 'div.cardRowTrxMode:has(> label:has-text("الرمز")) div[title], div.columnRowNew > label[title]'),
        "ref":         _loc(row, 'div.cardRowTrxMode:has(> label:has-text("الرقم المرجعي")) div[title]'),
        "input_date":  _loc(row, 'div.cardRowTrxMode:has(> label:has-text("تاريخ الإدخال")) div[title]'),
        "requester":   _loc(row, 'div.cardRowTrxMode:has(> label:has-text("الجهة الطالبة")) div[title]'),
        "client":      _loc(row, 'div.cardRowTrxMode:has(> label:has-text("العميل")) .style_clientContainer__Z0ebL > label, div.cardRowTrxMode:has(> label:has-text("العميل")) div[title]'),
        "city":        _loc(row, 'div.cardRowTrxMode:has(> label:has-text("المدينة")) div[title]'),
        "district":    _loc(row, 'div.cardRowTrxMode:has(> label:has-text("الحي")) div[title]'),
        "prop_type":   _loc(row, 'div.cardRowTrxMode:has(> label:has-text("نوع العقار")) .overflowTableField, div.cardRowTrxMode:has(> label:has-text("نوع العقار")) div[title]'),
        "valuation_v": _loc(row, 'div.cardRowTrxMode:has(> label:has-text("قيمة التقييم")) .overflowTableField, div.cardRowTrxMode:has(> label:has-text("قيمة التقييم")) div[title]'),
        "inputter":    _loc(row, 'div.cardRowTrxMode:has(> label:has-text("المدخل")) .overflowTableField, div.cardRowTrxMode:has(> label:has-text("المدخل")) div[title]'),
        "inspector":   _loc(row, 'div.cardRowTrxMode:has(> label:has-text("المعاين")) .overflowTableField, div.cardRowTrxMode:has(> label:has-text("المعاين")) div[title]'),
        "valuer":      _loc(row, 'div.cardRowTrxMode:has(> label:has-text("المقيم")) .overflowTableField, div.cardRowTrxMode:has(> label:has-text("المقيم")) div[title]'),
        "coordinator": _loc(row, 'div.cardRowTrxMode:has(> label:has-text("المنسق")) .overflowTableField, div.cardRowTrxMode:has(> label:has-text("المنسق")) div[title]'),
        "status":      _loc(row, 'label[title], span[class*=statusLbl], span:has-text("أكتملت")'),
        "attachments": _loc(row, 'button[title="المرفقات"] .style_notifiction__KPgXq'),
        "trx_title":   _loc(row, 'div.cardRowMode[title]'),
    }

    keys = list(locs.keys())
    texts = await asyncio.gather(*(_text_or_empty(locs[k]) for k in keys))

    # Map gathered texts back to keys
    out = dict(zip(keys, texts))
    code = out.get("code") or out.get("ref")

    return {
        "code": code,
        "reference": out.get("ref") or out.get("code"),
        "input_date": out.get("input_date"),
        "requester": out.get("requester"),
        "client": out.get("client"),
        "city": out.get("city"),
        "district": out.get("district"),
        "property_type": out.get("prop_type"),
        "valuation_value": out.get("valuation_v"),
        "inputter": out.get("inputter"),
        "inspector": out.get("inspector"),
        "valuer": out.get("valuer"),
        "coordinator": out.get("coordinator"),
        "status": out.get("status"),
        "attachments_count": out.get("attachments"),
        "trx_title": out.get("trx_title"),
        "scraped_at": datetime.utcnow(),
    }

async def _get_container(page: Page) -> Locator:
    # primary: use XPath you provided
    try:
        await page.wait_for_selector(SELECTORS["records_container_xpath"], timeout=15000)
        return page.locator(SELECTORS["records_container_xpath"])
    except PWTimeoutError:
        # fallback: try some generic containers
        for sel in ['div[role="table"]',
                    'div:has(div.trxRow)',
                    'div:has([class^="style_estimationTransactionsRow__"])']:
            try:
                await page.wait_for_selector(sel, state="visible", timeout=3000)
                return page.locator(sel)
            except Exception:
                pass
        return page.locator("body")

async def _get_rows(container: Locator) -> Locator:
    rows = container.locator('[class^="style_checkboxRow__"]')
    if await rows.count() == 0:
        rows = container.locator('.trxRow')
    return rows

# ---------- pagination ----------
async def _click_next(page: Page, page_no: int) -> bool:
    """
    Click the numbered pager <a role="button" rel="next">…</a> until disabled.
    """
    try:
        next_btn = page.locator(SELECTORS.get("pager_next", 'a[role="button"][rel="next"]')).first
        if await next_btn.count() == 0:
            return False
        aria_disabled = (await next_btn.get_attribute("aria-disabled")) or ""
        tab_idx = (await next_btn.get_attribute("tabindex")) or ""
        cls = (await next_btn.get_attribute("class")) or ""
        if aria_disabled.lower() == "true" or tab_idx == "-1" or "disabled" in cls:
            return False
        await next_btn.click()
        await _sleep()
        await page.wait_for_load_state("networkidle")
        return True
    except Exception as e:
        log("PAGER_WARN", f"Next click failed on page {page_no}", error=str(e))
        return False

# ---------- main public API ----------
async def scrape_all_pages_and_save(page: Page) -> Tuple[int, int]:
    """
    Scrape all pages after filters are applied.
    Logs per-page progress and upserts after each page (faster feedback).
    Returns (total_scraped, total_upserted).
    """
    total_scraped, total_upserted = 0, 0
    seen_keys: set[str] = set()

    MAX_PAGES = 200
    page_no = 1

    for _ in range(MAX_PAGES):
        log("PAGE_START", f"Scraping page {page_no}…", page=page_no)

        container = await _get_container(page)
        rows = await _get_rows(container)
        count = await rows.count()
        log("PAGE_ROWS", "Rows detected", page=page_no, rows=count)

        page_records: List[Dict[str, Any]] = []

        if count > 0:
            # Extract rows concurrently (still bounded by Playwright's pipeline)
            recs = await asyncio.gather(*(extract_record_from_row(rows.nth(i)) for i in range(count)))
            # de-dup within the run
            for rec in recs:
                key = rec.get("code") or rec.get("reference") or rec.get("trx_title")
                if not key or key in seen_keys:
                    continue
                seen_keys.add(key)
                page_records.append(rec)

        # Upsert right away for faster end-to-end progress
        upserts = 0
        if page_records:
            upserts = upsert_records(page_records)

        total_scraped += len(page_records)
        total_upserted += upserts

        log("PAGE_DONE", "Page processed",
            page=page_no, scraped=len(page_records), upserted=upserts,
            total_scraped=total_scraped, total_upserted=total_upserted)

        moved = await _click_next(page, page_no)
        if not moved:
            break

        page_no += 1

    log("RUN_DONE", "All pages scraped",
        pages=page_no, total_scraped=total_scraped, total_upserted=total_upserted)
    return total_scraped, total_upserted
