# eval_scraper.py
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, Optional, List, Any

from playwright.async_api import Page
from .utils import log, snap
from .config import SCREENSHOTS, ARTIFACTS_DIR
from .db import save_event


# =========================
# Helpers
# =========================

def _normalize_ws(s: str) -> str:
    """Collapse whitespace/newlines; keep Arabic intact."""
    s = s.replace("\xa0", " ")
    s = re.sub(r"\r\n|\r", "\n", s)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.split("\n")]
    out: List[str] = []
    for ln in lines:
        if ln == "" and (not out or out[-1] == ""):
            continue
        out.append(ln)
    return "\n".join(out).strip()


def _short(v: Optional[str], limit: int = 200) -> str:
    if v is None:
        return "None"
    vv = re.sub(r"\s+", " ", v).strip()
    return vv if len(vv) <= limit else vv[: limit - 1] + "…"


async def _text_from_input(page: Page, selector: str) -> Optional[str]:
    """Best-effort text getter from <input> (value/title/fallback inner_text)."""
    loc = page.locator(selector).first
    if await loc.count() == 0:
        return None
    # value()
    try:
        val = await loc.input_value()
        if val is not None and f"{val}".strip() != "":
            return _normalize_ws(val)
    except Exception:
        pass
    # attributes
    for attr in ("value", "title"):
        try:
            v = await loc.get_attribute(attr)
            if v and v.strip():
                return _normalize_ws(v)
        except Exception:
            pass
    # inner_text
    try:
        txt = await loc.inner_text()
        if txt and txt.strip():
            return _normalize_ws(txt)
    except Exception:
        pass
    return None


async def _text_from_select_single_value(page: Page, container_id: str) -> Optional[str]:
    """
    Read the visible value from react-select-like control:
    '#<id>-container .css-wgdcft-singleValue'
    """
    sel = f'#{container_id}-container .css-wgdcft-singleValue'
    loc = page.locator(sel).first
    if await loc.count() == 0:
        return None
    try:
        txt = await loc.inner_text()
        txt = re.sub(r"\s+", " ", txt or "").strip()
        return txt or None
    except Exception:
        return None


async def _active_yes_no(page: Page, field_id: str) -> Optional[str]:
    """
    Read 'نعم'/'لا' from a two-button toggle group like:
    <div id="{field_id}" class="style_evaluationBtn__K3cG0">
        <button class="style_evaluationBtnActive__8wa7r">نعم</button>
        <button class="">لا</button>
    </div>
    Returns 'نعم', 'لا', or None.
    """
    root = page.locator(f'#{field_id}').first
    if await root.count() == 0:
        return None
    try:
        active = root.locator("button.style_evaluationBtnActive__8wa7r").first
        if await active.count() > 0:
            txt = (await active.inner_text()).strip()
            return re.sub(r"\s+", " ", txt)
        # fallback: if no active class found, return first button text
        btn = root.locator("button").first
        if await btn.count() > 0:
            txt = (await btn.inner_text()).strip()
            return re.sub(r"\s+", " ", txt)
    except Exception:
        pass
    return None


async def _wait_eval_panel(page: Page) -> bool:
    """
    Wait until any of the anchor fields below exists/visible.
    This page renders sections lazily sometimes; use a generous timeout.
    """
    anchors = [
        "#MTA_ESTIMATION_REASON_id-container",
        "#MTA_ESTIMATION_BASE_id-container",
        "#TRI_ESTIMATION_DATE_TIME_id",
        "#TRI_CLIENT_NAME-text",
        "#TRI_MYO_ID_id-container",
        "#MIS_PROPERTY_USE_id-container",
        "#TRI_EST_ACTUAL_DATE_TIME_id",
        "#TRI_APROACH_MARKET-feild",
        "#TRI_CRI_ID_id-container",
        "#TRI_LATITUDE-feild",
        "#TRI_LONGITUDE-feild",
        "#DTR_PLAN_NO-text",
        "#DTR_LAND_AREA-feild",
        "#DTR_FINAL_PRICE-feild",
    ]
    try:
        await page.wait_for_selector(",".join(anchors), state="attached", timeout=30_000)
        # Also try to ensure main content container is visible if present
        root_candidates = [
            '#block-content-1',
            '#block-content-63',
            '.form-templates-panel.block-content',
        ]
        for rc in root_candidates:
            r = page.locator(rc).first
            if await r.count() > 0:
                try:
                    await r.wait_for(state="visible", timeout=2_000)
                    break
                except Exception:
                    continue
        return True
    except Exception:
        log("Evaluation panel anchors not found/visible.", "WARN")
        return False


# =========================
# Scraping of comparable offers table (rows 1..3)
# =========================

def _offer_row_ids(i: int) -> Dict[str, str]:
    # IDs follow the pattern with suffix i; some are -text, some -feild
    return {
        "sell_date":        f"#ELS_OFFER_BULID_SELL_DAT{i}-text",
        "subject_type":     f"#ELS_OFFER_BULID_TYPE{i}-text",
        "comp_type":        f"#ELS_OFFER_BULID_COMP_TYPE{i}-text",
        "land_area":        f"#ELS_OFFER_BULID_LAND_AREA{i}-feild",
        "build_area":       f"#ELS_OFFER_BULID_BULID_AREA{i}-feild",
        "total_price":      f"#ELS_OFFER_BULID_TOT_PRICE{i}-feild",
        "source":           f"#ELS_OFFER_BULID_DISTANCE_{i}-text",
        "streets_count":    f"#ELS_OFFER_BULID_STRET_NO_{i}-text",
        "street_width":     f"#ELS_OFFER_BULID_STRET_WIDTH_{i}-text",
        "description":      f"#ELS_OFFER_BULID_DESC{i}-text",
        "coordinates":      f"#ELS_OFFER_BULID_COORDINATE{i}-text",
    }


async def _scrape_offer_row(page: Page, i: int) -> Dict[str, Optional[str]]:
    ids = _offer_row_ids(i)
    row = {}
    for key, sel in ids.items():
        row[key] = await _text_from_input(page, sel)
    return row


# =========================
# Main scraping API
# =========================

def _empty_payload() -> Dict[str, Any]:
    """Only the fields requested 'for now'."""
    return {
        # High-level purpose/base
        "estimation_reason": None,   # غرض التقييم
        "estimation_base": None,     # أساس القيمة

        # Dates
        "actual_evaluation_date_m": None,  # TRI_ESTIMATION_DATE_TIME_id
        "actual_inspection_date_m": None,  # TRI_EST_ACTUAL_DATE_TIME_id

        # Client & categoricals
        "client_name": None,         # TRI_CLIENT_NAME-text
        "property_type": None,       # TRI_MYO_ID_id
        "property_use": None,        # MIS_PROPERTY_USE_id
        "location": None,            # TRI_CRI_ID_id

        # Toggles (yes/no)
        "approach_market": None,     # نعم/لا
        "approach_income": None,     # نعم/لا
        "approach_cost": None,       # نعم/لا

        # Numbers / coordinates
        "final_valuation_value": None,  # DTR_FINAL_PRICE-feild
        "latitude": None,               # TRI_LATITUDE-feild
        "longitude": None,              # TRI_LONGITUDE-feild
        "plan_no": None,                # DTR_PLAN_NO-text
        "parcel_no": None,              # DTR_PARCEL_NO-text
        "title_deed_no": None,          # TRI_TITLE_DEED_NO-text
        "land_area": None,              # DTR_LAND_AREA-feild
        "street_view": None,            # DTR_STREET_VIEW-text
        "ownership_type": None,


        # Comparable offers (rows 1..3)
        "offers": [],

        # Metadata
        "scraped_at": None,
    }


async def scrape_eval_model(page: Page) -> Dict[str, Any]:
    """
    Scrape ONLY the fields you specified 'for now'.
    """
    ok = await _wait_eval_panel(page)
    if not ok:
        if SCREENSHOTS:
            await snap(page, f"{ARTIFACTS_DIR}/08-eval-model-visible.png")
        data = _empty_payload()
        data["scraped_at"] = datetime.now(timezone.utc).isoformat()
        log("Scraped eval (panel missing) -> values: " + str(data))
        return data

    # --- Purpose & Base ---
    estimation_reason = await _text_from_select_single_value(page, "MTA_ESTIMATION_REASON_id")
    estimation_base   = await _text_from_select_single_value(page, "MTA_ESTIMATION_BASE_id")

    # --- Dates ---
    actual_eval_date  = await _text_from_input(page, "#TRI_ESTIMATION_DATE_TIME_id")
    actual_insp_date  = await _text_from_input(page, "#TRI_EST_ACTUAL_DATE_TIME_id")

    # --- Client & categoricals ---
    client_name   = await _text_from_input(page, "#TRI_CLIENT_NAME-text")
    property_type = await _text_from_select_single_value(page, "TRI_MYO_ID_id")
    property_use  = await _text_from_select_single_value(page, "MIS_PROPERTY_USE_id")
    location      = await _text_from_select_single_value(page, "TRI_CRI_ID_id")

    # --- Toggles (yes/no) ---
    approach_market = await _active_yes_no(page, "TRI_APROACH_MARKET-feild")
    approach_income = await _active_yes_no(page, "TRI_APROACH_INCOME-feild")
    approach_cost   = await _active_yes_no(page, "TRI_APROACH_COST-feild")

    # --- Numbers / coordinates ---
    final_value = await _text_from_input(page, "#DTR_FINAL_PRICE-feild")
    latitude    = await _text_from_input(page, "#TRI_LATITUDE-feild")
    longitude   = await _text_from_input(page, "#TRI_LONGITUDE-feild")
    plan_no     = await _text_from_input(page, "#DTR_PLAN_NO-text")
    parcel_no   = await _text_from_input(page, "#DTR_PARCEL_NO-text")
    title_deed  = await _text_from_input(page, "#TRI_TITLE_DEED_NO-text")
    land_area   = await _text_from_input(page, "#DTR_LAND_AREA-feild")
    street_view = await _text_from_input(page, "#DTR_STREET_VIEW-text")
    ownership_type = await _text_from_select_single_value(page, 'MTA_OWNERSHIP_TYPE2_id')


    # --- Comparable offers (rows 1..3) ---
    offers: List[Dict[str, Optional[str]]] = []
    for i in (1, 2, 3):
        offers.append(await _scrape_offer_row(page, i))

    payload = {
        "estimation_reason": estimation_reason,
        "estimation_base": estimation_base,

        "actual_evaluation_date_m": actual_eval_date,
        "actual_inspection_date_m": actual_insp_date,

        "client_name": client_name,
        "property_type": property_type,
        "property_use": property_use,
        "location": location,

        "approach_market": approach_market,
        "approach_income": approach_income,
        "approach_cost": approach_cost,

        "final_valuation_value": final_value,
        "latitude": latitude,
        "longitude": longitude,
        "plan_no": plan_no,
        "parcel_no": parcel_no,
        "title_deed_no": title_deed,
        "land_area": land_area,
        "street_view": street_view,

        "offers": offers,
        "ownership_type": ownership_type,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }

    if SCREENSHOTS:
        await snap(page, f"{ARTIFACTS_DIR}/08-eval-model-visible.png")

    # Compact log with shortened values
    lines = ["Scraped eval (selected fields):"]
    for k, v in payload.items():
        if k == "offers":
            lines.append(f"  - offers: [{len(offers)} rows]")
        else:
            lines.append(f"  - {k}: {_short(v if isinstance(v, str) else str(v))}")
    log("\n".join(lines))

    return payload


async def scrape_eval_model_and_store(page: Page) -> Dict[str, Any]:
    """
    Scrape and persist (via save_event) using the limited field set above.
    """
    data = await scrape_eval_model(page)
    try:
        save_event({
            "type": "eval_model_scraped",
            "payload": data,
            "ts": datetime.now(timezone.utc),
        })
        log("Evaluation model scraped and saved.")
    except Exception as e:
        log(f"Failed to save eval model: {e}", "WARN")
    return data
