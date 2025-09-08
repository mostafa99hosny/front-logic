from .utils import log

_JS_FALLBACK = r"""
// Basic stealth tweaks executed before any page scripts.
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

try {
  // languages
  Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
} catch (e) {}

try {
  // plugins
  Object.defineProperty(navigator, 'plugins', {
    get: () => [{name: 'Chrome PDF Plugin'}]
  });
} catch (e) {}

try {
  // hairline fix for Chrome / WebGL fingerprints
  const getParameter = WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) { return 'Intel Open Source Technology Center'; }
    if (parameter === 37446) { return 'Mesa DRI Intel(R)'; }
    return getParameter.apply(this, [parameter]);
  };
} catch (e) {}

try {
  // permissions
  const originalQuery = window.navigator.permissions.query;
  window.navigator.permissions.query = (parameters) => (
    parameters && parameters.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : originalQuery(parameters)
  );
} catch (e) {}

try {
  // chrome runtime presence
  window.chrome = window.chrome || { runtime: {} };
} catch (e) {}
"""

async def apply_stealth(context, page):
    """
    Try known playwright-stealth variants; if none work,
    add a JS stealth baseline via add_init_script on the context/page.
    """
    # Ensure our fallback runs as early as possible (for all pages in the context)
    added_fallback = False
    try:
        await context.add_init_script(_JS_FALLBACK)
        added_fallback = True
    except Exception:
        # fallback to page-level if context isn't ready
        try:
            await page.add_init_script(_JS_FALLBACK)
            added_fallback = True
        except Exception:
            added_fallback = False

    # 1) top-level async
    try:
        from playwright_stealth import stealth_async as _stealth_async  # type: ignore
        await _stealth_async(page)
        log("Stealth applied via top-level stealth_async")
        return
    except Exception:
        pass

    # 2) top-level sync
    try:
        from playwright_stealth import stealth_sync as _stealth_sync  # type: ignore
        _stealth_sync(page)
        log("Stealth applied via top-level stealth_sync")
        return
    except Exception:
        pass

    # 3) module namespace variants
    try:
        from playwright_stealth import stealth as _stealth_mod  # type: ignore
        for name in ("stealth_async", "stealth_sync", "stealth", "apply_stealth"):
            fn = getattr(_stealth_mod, name, None)
            if callable(fn):
                if "async" in name:
                    await fn(page)
                else:
                    fn(page)
                log(f"Stealth applied via stealth.{name}")
                return
    except Exception:
        pass

    if added_fallback:
        log("Applied JS stealth fallback (playwright-stealth package not usable).", "WARN")
    else:
        log("WARN: No stealth applied (could not add init script).", "WARN")
