import asyncio
import importlib
import inspect
from playwright.async_api import Page
from .selectors import SELECTORS
from .config import settings

# ---------- stealth resolver (robust across versions) ----------
async def _fallback_apply(page: Page):
    # Try to use our local patch; if missing, inline a minimal one.
    try:
        from stealth_patch import apply_basic_stealth
        await apply_basic_stealth(page)
        return
    except Exception:
        pass

    # Inline minimal stealth (runs before navigation in main.py)
    await page.add_init_script(r"""
    (() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
      window.navigator.chrome = { runtime: {} };
      Object.defineProperty(navigator, 'languages', { get: () => ['ar-SA','ar','en-US','en'] });
      Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
      const origQuery = navigator.permissions && navigator.permissions.query;
      if (origQuery) {
        navigator.permissions.query = (p) => (
          p && p.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : origQuery(p)
        );
      }
      const getParameter = WebGLRenderingContext.prototype.getParameter;
      WebGLRenderingContext.prototype.getParameter = function (p) {
        if (p === 37445) return 'Intel Inc.';
        if (p === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.call(this, p);
      };
    })();
    """)

def _resolve_stealth_callable():
    # Try root module
    try:
        mod = importlib.import_module("playwright_stealth")
    except Exception:
        mod = None

    candidates = []
    if mod:
        candidates += [getattr(mod, n, None) for n in ("stealth_async", "stealth", "apply_stealth")]

    # Try submodule playwright_stealth.stealth
    try:
        sub = importlib.import_module("playwright_stealth.stealth")
        candidates += [getattr(sub, n, None) for n in ("stealth_async", "stealth", "apply_stealth")]
    except Exception:
        pass

    for fn in candidates:
        if callable(fn):
            return fn
    return None

_STEALTH_FUNC = _resolve_stealth_callable()

async def apply_stealth(page: Page):
    """Use playwright-stealth if available; otherwise fall back to local patch."""
    if _STEALTH_FUNC is None:
        await _fallback_apply(page)
        return
    result = _STEALTH_FUNC(page)
    if inspect.iscoroutine(result):
        await result

# ---------- human delay + login ----------
async def human_delay():
    await asyncio.sleep(settings.ACTION_DELAY_MS / 1000)

async def login(page: Page, username: str, password: str) -> None:
    # Stealth is already applied in main.py BEFORE navigation.
    await page.wait_for_load_state("domcontentloaded")
    await human_delay()

    await page.wait_for_selector(SELECTORS["username"], state="visible", timeout=30000)
    await page.fill(SELECTORS["username"], username or "")
    await human_delay()

    await page.fill(SELECTORS["password"], password or "")
    await human_delay()

    await page.click(SELECTORS["submit"])
    try:
        await page.wait_for_selector(SELECTORS["filter_panel_btn"], state="visible", timeout=60000)
    except Exception:
        await page.wait_for_load_state("networkidle")
