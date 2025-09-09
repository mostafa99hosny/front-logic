# eval_scraper.py
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, Optional

from playwright.async_api import Page
from .utils import log, snap
from .config import SCREENSHOTS, ARTIFACTS_DIR

# ---------- helpers ----------

def _normalize_ws(s: str) -> str:
    s = s.replace("\xa0", " ")
    s = re.sub(r"\r\n|\r", "\n", s)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.split("\n")]
    collapsed = []
    for ln in lines:
        if ln == "" and (not collapsed or collapsed[-1] == ""):
            continue
        collapsed.append(ln)
    return "\n".join(collapsed).strip()

def _short(v: Optional[str], limit: int = 200) -> str:
    if v is None:
        return "None"
    vv = re.sub(r"\s+", " ", v).strip()
    return vv if len(vv) <= limit else vv[: limit - 1] + "…"

async def _text_from_input(page: Page, selector: str) -> Optional[str]:
    loc = page.locator(selector).first
    if await loc.count() == 0:
        return None
    # Try input value
    try:
        val = await loc.input_value()
        if val is not None and str(val).strip() != "":
            return _normalize_ws(val)
    except Exception:
        pass
    # Try attributes
    for attr in ("value", "title"):
        try:
            v = await loc.get_attribute(attr)
            if v and v.strip():
                return _normalize_ws(v)
        except Exception:
            pass
    # Fallback to inner_text
    try:
        txt = await loc.inner_text()
        txt = _normalize_ws(txt)
        return txt or None
    except Exception:
        return None

async def _text_from_select_single_value(page: Page, container_id: str) -> Optional[str]:
    """
    React-Select visible value:
        #{container_id}-container .css-wgdcft-singleValue
    """
    sel = f'#{container_id}-container .css-wgdcft-singleValue'
    loc = page.locator(sel).first
    if await loc.count() == 0:
        return None
    try:
        txt = (await loc.inner_text()).strip()
        txt = re.sub(r"\s+", " ", txt)
        return txt or None
    except Exception:
        return None

async def _yes_no_from_toggle(page: Page, container_id: str) -> Optional[str]:
    """
    For the two-button Yes/No groups, e.g.:
      <div id="{container_id}" class="style_evaluationBtn__K3cG0">
        <button class="style_evaluationBtnActive__8wa7r">نعم</button>
        <button class="">لا</button>
      </div>
    Returns the active button's text (e.g., "نعم" / "لا") or None.
    """
    try:
        root = page.locator(f'#{container_id}').first
        if await root.count() == 0:
            return None
        active = root.locator('button.style_evaluationBtnActive__8wa7r').first
        if await active.count() == 0:
            return None
        txt = await active.inner_text()
        txt = _normalize_ws(txt)
        return txt or None
    except Exception:
        return None

async def _wait_eval_panel(page: Page) -> bool:
    """
    Wait until the evaluation panel is visible and at least one known field is present.
    """
    try:
        root = page.locator('#block-content-1').first
        await root.wait_for(state="visible", timeout=30_000)
    except Exception:
        log("Evaluation panel container not visible.", "WARN")
        return False

    anchors = [
        '#MTA_ESTIMATION_REASON_id-container',   # Valuation Purpose
        '#TRI_ESTIMATION_DATE_TIME_id',          # Valuation Date
        '#DTR_FINAL_PRICE-feild',                # Final Value
        '#TRI_CLIENT_NAME-text',                 # Client
    ]
    try:
        await page.wait_for_selector(",".join(anchors), state="attached", timeout=10_000)
        return True
    except Exception:
        log("Evaluation panel anchor fields not found.", "WARN")
        return False

# ---------- payload shape (ONLY requested fields + pdf) ----------

def _empty_eval_payload() -> Dict[str, Optional[str]]:
    keys = [
        # Valuation Purpose 
        "valuationPurpose",

        # Value Premise
        "valuePremise",

        # Valuation Date
        "valuationDate",

        #Report Issuing Date
        "reportIssuingDate",

        #Assumptions
        "assumptions",

        #Special Assumptions
        "specialAssumptions",

        #Valuation Currency 
        "valuationCurrency",


        # Final Value
        "finalValue",
        # Client Value
        "clientName",

        #Telephone Number
        "telephoneNumber",

        #E-mail Address 
        "emailAddress",

        #Valuer Name 
        "valuerName",



        # Asset Being Valued Usage\Sector *  (from "نوع العقار")
        "assetUsageSector",
        # Inspection Date *
        "inspectionDate",
        # Market/Income/Cost Approach *
        "marketApproach",
        "incomeApproach",
        "costApproach",

        #Country 
        "country",
        # Region (city + district in one field)
        "regionCityDistrict",
        # Longitude / Latitude
        "longitude",
        "latitude",
        # Block Number / Property Number / Certificate Number
        "blockNumber",
        "propertyNumber",
        "certificateNumber",
        # Ownership Type *
        "ownershipType",
        # Land Area
        "landArea",
        # Building Area *
        "buildingArea",
        # Street width *
        "streetWidth",
        # PDF meta (flat)
        "pdfFilePath",
        "pdfUrl",
        # meta
        "scrapedAt",
    ]
    return {k: None for k in keys}

# ---------- main scraping ----------

async def scrape_eval_model(page: Page, pdf_meta: Optional[Dict[str, Optional[str]]] = None) -> Dict[str, Optional[str]]:
    """
    Scrape ONLY the fields requested (plus pdf_file_path/pdf_url) and default to None if missing.
    """
    ok = await _wait_eval_panel(page)
    if not ok:
        if SCREENSHOTS:
            await snap(page, f"{ARTIFACTS_DIR}/08-eval-model-visible.png")
        data = _empty_eval_payload()
        data["scraped_at"] = datetime.now(timezone.utc).isoformat()
        if pdf_meta:
            data["pdf_file_path"] = pdf_meta.get("pdf_file_path")
            data["pdf_url"] = pdf_meta.get("pdf_url")
        log("Scraped eval model (panel missing) -> values: " + str(data))
        return data

    # --- Valuation Purpose * (غرض التقييم)
    valuation_purpose = await _text_from_select_single_value(page, 'MTA_ESTIMATION_REASON_id')

    # --- Valuation Date * (تاريخ التقييم الفعلي(م))
    valuation_date = await _text_from_input(page, '#TRI_ESTIMATION_DATE_TIME_id')

    # --- Final Value * (قيمة التقييم النهائية)
    final_value = await _text_from_input(page, '#DTR_FINAL_PRICE-feild')

    # --- Client Value (العميل)
    client_name = await _text_from_input(page, '#TRI_CLIENT_NAME-text')

    # --- Asset Being Valued Usage\Sector * (نوع العقار)
    asset_usage_sector = await _text_from_select_single_value(page, 'TRI_MYO_ID_id')

    # --- Inspection Date * (المعاينة الفعلي(م))
    inspection_date = await _text_from_input(page, '#TRI_EST_ACTUAL_DATE_TIME_id')

    # --- Approach toggles * (Yes/No Arabic: نعم / لا)
    market_approach = await _yes_no_from_toggle(page, 'TRI_APROACH_MARKET-feild')
    income_approach = await _yes_no_from_toggle(page, 'TRI_APROACH_INCOME-feild')
    cost_approach   = await _yes_no_from_toggle(page, 'TRI_APROACH_COST-feild')

    # --- Region (city + district in one field: الموقع)
    region_city_district = await _text_from_select_single_value(page, 'TRI_CRI_ID_id')

    # --- Coordinates
    longitude = await _text_from_input(page, '#TRI_LONGITUDE-feild')
    latitude  = await _text_from_input(page, '#TRI_LATITUDE-feild')

    # --- Numbers
    block_number      = await _text_from_input(page, '#DTR_PLAN_NO-text')
    property_number   = await _text_from_input(page, '#DTR_PARCEL_NO-text')
    certificate_number= await _text_from_input(page, '#TRI_TITLE_DEED_NO-text')

    # --- Ownership Type *
    ownership_type = await _text_from_select_single_value(page, 'MTA_OWNERSHIP_TYPE2_id')

    # --- Areas
    land_area     = await _text_from_input(page, '#DTR_LAND_AREA-feild')
    building_area = await _text_from_input(page, '#ARI_TOTAL_BUILD_AREA-feild')

    # --- Street width *
    street_width = await _text_from_input(page, '#DTR_STREET_VIEW-text')

    payload = _empty_eval_payload()
    payload.update({
        "valuationPurpose": valuation_purpose,
        "valuePremise": None,
        "valuationDate": valuation_date,
        "assumptions": None,
        "specialAssumptions": None,
        "valuationCurrency": None,
        "finalValue": final_value,
       
        "clientName": client_name,
        "telephoneNumber": None,
        "emailAddress": None,
        "valuerName": None,

        "assetUsageSector": asset_usage_sector,
        "inspectionDate": inspection_date,
        "marketApproach": market_approach,
        "incomeApproach": income_approach,
        "costApproach": cost_approach,

        "country": "country",
        "regionCityDistrict": region_city_district,
        "longitude": longitude,
        "latitude": latitude,
        "blockNumber": block_number,
        "propertyNumber": property_number,
        "certificateNumber": certificate_number,
        "ownershipType": ownership_type,
        "landArea": land_area,
        "buildingArea": building_area,
        "streetWidth": street_width,
        "scrapedAt": datetime.now(timezone.utc).isoformat(),
    })

    # Inline PDF meta (flat in payload, not nested)
    if pdf_meta:
        payload["pdfFilePath"] = pdf_meta.get("pdf_file_path")
        payload["pdfUrl"] = pdf_meta.get("pdf_url")

    if SCREENSHOTS:
        await snap(page, f"{ARTIFACTS_DIR}/08-eval-model-visible.png")

    # Concise log
    preview_keys = [
        "valuation_purpose","valuation_date","final_value","client_name",
        "asset_usage_sector","inspection_date","market_approach","income_approach","cost_approach",
        "region_city_district","country","longitude","latitude","block_number","property_number",
        "certificate_number","ownership_type","land_area","building_area","street_width",
        "pdf_file_path","pdf_url","scraped_at"
    ]
    lines = ["Scraped eval model (values):"]
    for k in preview_keys:
        lines.append(f"  - {k}: {_short(payload.get(k))}")
    log("\n".join(lines))

    return payload
