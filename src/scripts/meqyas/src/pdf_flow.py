# pdf_flow.py
# Behavior:
# - Prefer inline primary action: click ONLY if it indicates Print/PDF (Arabic/English).
# - If inline looks like View/عرض (or non-PDF), skip it.
# - Always open 3-dots settings afterward.
#     * If the FIRST dropdown item is PDF → click it → F10 → download → close tab →
#       reopen 3-dots and click **"عرض نموذج التقييم"**.
#     * If the FIRST dropdown item is NOT PDF → click **"عرض نموذج التقييم"** directly.
# - Returns True iff a PDF was downloaded. (Eval click is always attempted when menu path is used.)

from typing import Optional,Tuple
from pathlib import Path
import re
from urllib.parse import urlparse
from playwright.async_api import Page, TimeoutError as PWTimeoutError
from .utils import log, snap, ensure_dir
from .config import SCREENSHOTS, ARTIFACTS_DIR, DOWNLOAD_DIR

# ==============================
# Selectors & constants
# ==============================

# Primary inline action (row button)
PRIMARY_ACTION_LOCATOR = (
    'button.style_viewBtn__vhvib.mainbutton, '
    'button.mainbutton:has(label)'
)

# Three-dots settings button + menu
SETTINGS_BUTTON     = 'button.dropdown-open.style_settingBtn__GFzkL, button.style_settingBtn__GFzkL'
DROPDOWN_CONTAINER  = 'div.rc-dropdown.rc-dropdown-placement-bottomLeft'
DROPDOWN_MENU       = 'ul.rc-dropdown-menu.style_actionsMenuContainer__Ntqdj'
OPEN_MENU_LOCATOR   = f'{DROPDOWN_MENU}[data-dropdown-inject="true"]'

# Arabic titles/text we key off
MENU_PDF_TITLE              = 'طباعة (PDF)'
MENU_EVAL_TITLE             = 'عرض نموذج التقييم'

# Optional print dialog hints (best-effort only)
PRINT_DIALOG_CANDIDATES = [
    'div.fitHeightDialog.style_actionDailog__BXkDP.modalDialog',
    '[role="dialog"]:has-text("أختر التقرير")',
    '[role="dialog"]:has-text("اختر التقرير")',
    '[role="dialog"]:has-text("طباعة")',
    '[role="dialog"]:has-text("Print")',
]
DIALOG_PRINT_BTN = '#modal_save_btn'
DIALOG_SPINNER   = '#choose-report-dialog-okButton'

# PDF tab URL pattern
PDF_URL_RE = re.compile(r"/print-valuation-pdf/[^/?#]+\.pdf", re.I)

# ==============================
# Helpers
# ==============================

def _norm_text(s: Optional[str]) -> str:
    if not s:
        return ""
    return " ".join(s.split()).strip().lower()

async def _is_view_like_button(btn) -> bool:
    try:
        lab = btn.locator("label").first
        text = await (lab.text_content() if await lab.count() else btn.text_content())
        t = _norm_text(text)
    except Exception:
        return False
    # View/عرض without any print/pdf hints
    return (("view" in t) or ("عرض" in t)) and not any(k in t for k in ("pdf", "طباعة", "print"))

async def _is_pdf_like_button(btn) -> bool:
    try:
        lab = btn.locator("label").first
        text = await (lab.text_content() if await lab.count() else btn.text_content())
        t = _norm_text(text)
    except Exception:
        return False
    return any(k in t for k in ("pdf", "طباعة", "print"))

async def _maybe_wait_dialog_ready(page: Page):
    try:
        for sel in PRINT_DIALOG_CANDIDATES:
            dlg = page.locator(sel).first
            if await dlg.count() > 0 and await dlg.is_visible():
                spinner = dlg.locator(DIALOG_SPINNER)
                if await spinner.count() > 0:
                    try:
                        await spinner.wait_for(state="hidden", timeout=10_000)
                    except Exception:
                        pass
                btn = dlg.locator(DIALOG_PRINT_BTN).first
                if await btn.count() > 0:
                    try:
                        await btn.wait_for(state="visible", timeout=5_000)
                    except Exception:
                        pass
                break
    except Exception:
        pass

async def _fire_f10(page: Page):
    try:
        await page.bring_to_front()
    except Exception:
        pass
    await page.wait_for_timeout(150)
    await page.keyboard.press("F10")
    log("Sent F10 to page.")

async def _wait_for_new_pdf_tab(page: Page):
    try:
        newp = await page.context.wait_for_event("page", timeout=180_000)
    except PWTimeoutError:
        log("Timed out waiting for new tab after F10.", "WARN")
        return None
    except Exception as e:
        log(f"Error waiting for new tab: {e}", "WARN")
        return None

    for state in ("domcontentloaded", "networkidle"):
        try:
            await newp.wait_for_load_state(state, timeout=60_000)
        except Exception:
            pass

    log(f"New tab URL: {newp.url or ''}")
    return newp

def _filename_from_url(url: str, item_hint: Optional[str]) -> str:
    try:
        path_tail = urlparse(url).path.split("/")[-1]
        name = path_tail.split("?")[0] if path_tail else None
    except Exception:
        name = None
    if not name:
        name = "report.pdf"
    return f"{item_hint}_{name}" if item_hint else name

async def _direct_download_from_url(page: Page, url: str, item_hint: Optional[str]) -> bool:
    try:
        log(f"Attempting direct download: {url}")
        r = await page.context.request.get(url, timeout=600_000)
        if not r.ok:
            log(f"PDF GET failed: status={r.status} url={url}", "WARN")
            return False
        ensure_dir(DOWNLOAD_DIR)
        fname = _filename_from_url(url, item_hint)
        target = str(Path(DOWNLOAD_DIR) / fname)
        with open(target, "wb") as f:
            f.write(await r.body())
        log(f"PDF saved (direct download): {target}")
        return True
    except Exception as e:
        log(f"Direct download error: {e}", "WARN")
        return False

async def open_settings_menu(page: Page) -> bool:
    """Click the three-dots settings button and wait for the menu to appear."""
    try:
        btn = page.locator(SETTINGS_BUTTON).first
        await btn.wait_for(state="visible", timeout=5000)
        await btn.click()
        log("Clicked 3-dots settings button.")
        await page.locator(DROPDOWN_CONTAINER).first.wait_for(state="visible", timeout=5000)
        await page.locator(DROPDOWN_MENU).first.wait_for(state="visible", timeout=5000)
        log("Settings dropdown is visible.")
        return True
    except Exception as e:
        log(f"Failed to open settings menu: {e}", "WARN")
        return False

async def _click_eval_button_strict(page: Page, menu) -> bool:
    """
    Click ONLY the button for: <li title="عرض نموذج التقييم"> ... <button class="style_actionBtnAr__9L-Pm"><label>عرض نموذج التقييم</label>
    Fallbacks: strict button+label selector, then role=button with text.
    """
    # 1) li[title="عرض نموذج التقييم"] → button
    try:
        eval_li = menu.locator(f'li[role="menuitem"][title="{MENU_EVAL_TITLE}"]').first
        if await eval_li.count() > 0 and await eval_li.is_visible():
            btn = eval_li.locator('button.style_actionBtnAr__9L-Pm').first
            if await btn.count() > 0 and await btn.is_visible():
                try: await btn.scroll_into_view_if_needed()
                except: pass
                try:
                    box = await btn.bounding_box()
                    if box: await page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                except: pass
                await btn.click()
                log(f'Dropdown: clicked "{MENU_EVAL_TITLE}" via li[title].')
                return True
    except Exception as e:
        log(f'_click_eval_button_strict (title) failed: {e}', "WARN")

    # 2) strict button+label text
    try:
        strict_btn = menu.locator(f'button.style_actionBtnAr__9L-Pm:has(label:has-text("{MENU_EVAL_TITLE}"))').first
        if await strict_btn.count() > 0 and await strict_btn.is_visible():
            try: await strict_btn.scroll_into_view_if_needed()
            except: pass
            try:
                box = await strict_btn.bounding_box()
                if box: await page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            except: pass
            await strict_btn.click()
            log(f'Dropdown: clicked "{MENU_EVAL_TITLE}" via strict button+label.')
            return True
    except Exception as e:
        log(f'_click_eval_button_strict (strict) failed: {e}', "WARN")

    # 3) role=button has_text
    try:
        text_btn = menu.get_by_role("button").filter(has_text=MENU_EVAL_TITLE).first
        if await text_btn.count() > 0 and await text_btn.is_visible():
            try: await text_btn.scroll_into_view_if_needed()
            except: pass
            try:
                box = await text_btn.bounding_box()
                if box: await page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            except: pass
            await text_btn.click()
            log(f'Dropdown: clicked "{MENU_EVAL_TITLE}" via role=button has_text.')
            return True
    except Exception as e:
        log(f'_click_eval_button_strict (role) failed: {e}', "WARN")

    log(f'Dropdown: "{MENU_EVAL_TITLE}" not found.', "WARN")
    return False

async def _menu_click_first_if_pdf_else_eval(page: Page, item_hint: Optional[str]) -> bool:
    """
    Menu is already open.
    If FIRST li is PDF → click & download → REOPEN menu → click "عرض نموذج التقييم".
    Else → click "عرض نموذج التقييم".
    Returns True iff a PDF was downloaded.
    """
    try:
        menu = page.locator(OPEN_MENU_LOCATOR).last
        await menu.wait_for(state="visible", timeout=6000)

        first_li = menu.locator('li[role="menuitem"]').first
        if await first_li.count() == 0 or not await first_li.is_visible():
            log("Dropdown: first <li> not found; clicking eval directly.", "WARN")
            await _click_eval_button_strict(page, menu)
            return False

        # Identify if the first li is PDF
        title_attr = (await first_li.get_attribute("title")) or ""
        is_pdf_by_title = title_attr.strip() == MENU_PDF_TITLE

        btn_in_li = first_li.locator('button').first
        li_label_text = ""
        try:
            lab = btn_in_li.locator("label").first
            li_label_text = await (lab.text_content() if await lab.count() else btn_in_li.text_content())
            li_label_text = _norm_text(li_label_text)
        except Exception:
            pass
        is_pdf_by_text = any(k in li_label_text for k in ("pdf", "طباعة", "print"))

        if is_pdf_by_title or is_pdf_by_text:
            # Click PDF and download
            try: await btn_in_li.scroll_into_view_if_needed()
            except: pass
            try:
                box = await btn_in_li.bounding_box()
                if box: await page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            except: pass
            await btn_in_li.click()
            log('Dropdown: clicked FIRST item "طباعة (PDF)".')

            if SCREENSHOTS:
                await snap(page, f"{ARTIFACTS_DIR}/05-pdf-modal-before-click.png")
            await _maybe_wait_dialog_ready(page)
            await _fire_f10(page)

            new_tab = await _wait_for_new_pdf_tab(page)
            if not new_tab:
                return False

            if SCREENSHOTS:
                await snap(new_tab, f"{ARTIFACTS_DIR}/07-pdf-tab-open.png")

            url = new_tab.url or ""
            if not PDF_URL_RE.search(url):
                try:
                    await new_tab.wait_for_timeout(1500)
                    url = new_tab.url or url
                except Exception:
                    pass

            ok = False
            if url:
                ok = await _direct_download_from_url(page, url, item_hint)
            else:
                log("New tab did not expose a URL.", "WARN")

            try:
                await new_tab.close()
            except Exception:
                pass

            # Reopen menu and click eval after PDF download
            if await open_settings_menu(page):
                menu2 = page.locator(OPEN_MENU_LOCATOR).last
                await menu2.wait_for(state="visible", timeout=5000)
                await _click_eval_button_strict(page, menu2)
            else:
                log("Could not reopen settings after PDF download.", "WARN")

            return ok

        # Not PDF first → click eval directly
        await _click_eval_button_strict(page, menu)
        return False

    except Exception as e:
        log(f"Dropdown handling failed: {e}", "WARN")
        return False

# ==============================
# Main entry
# ==============================

async def try_download_pdf(page: Page, item_hint: Optional[str] = None) -> bool:
    """
    Flow:
      1) Inline: If primary button is PDF/Print-like → click → (optional dialog) → F10 → download.
         (If inline looked like View/عرض, skip.)
      2) Open 3-dots:
         - If FIRST li is PDF → click & download → reopen menu → click "عرض نموذج التقييم".
         - Else → click "عرض نموذج التقييم".
    Returns True iff any PDF was downloaded.
    """
    downloaded = False

    # 1) Inline primary attempt
    try:
        primary = page.locator(PRIMARY_ACTION_LOCATOR).first
        if await primary.count() > 0 and await primary.is_visible():
            if await _is_view_like_button(primary):
                log("Primary action is 'عرض' / View; skip inline.", "WARN")
            elif await _is_pdf_like_button(primary):
                try:
                    await primary.click()
                    log("Clicked inline PDF action button (primary).")
                    if SCREENSHOTS:
                        await snap(page, f"{ARTIFACTS_DIR}/05-pdf-modal-before-click.png")
                    await _maybe_wait_dialog_ready(page)
                    await _fire_f10(page)

                    new_tab = await _wait_for_new_pdf_tab(page)
                    if new_tab:
                        if SCREENSHOTS:
                            await snap(new_tab, f"{ARTIFACTS_DIR}/07-pdf-tab-open.png")
                        url = new_tab.url or ""
                        if not PDF_URL_RE.search(url):
                            try:
                                await new_tab.wait_for_timeout(1500)
                                url = new_tab.url or url
                            except Exception:
                                pass
                        if url:
                            downloaded = await _direct_download_from_url(page, url, item_hint)
                        else:
                            log("New tab did not expose a URL.", "WARN")
                        try:
                            await new_tab.close()
                        except Exception:
                            pass
                except Exception as e:
                    log(f"Primary inline PDF click/flow failed: {e}", "WARN")
    except Exception as e:
        log(f"Primary inline detection failed: {e}", "WARN")

    # 2) Menu path (always open settings now)
    if await open_settings_menu(page):
        # This will download if first item is PDF; always attempts to click eval at the end.
        menu_downloaded = await _menu_click_first_if_pdf_else_eval(page, item_hint)
        downloaded = downloaded or menu_downloaded
    else:
        log("Could not open settings menu for dropdown handling.", "WARN")

    return downloaded
