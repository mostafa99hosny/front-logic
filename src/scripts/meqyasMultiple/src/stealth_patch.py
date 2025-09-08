from playwright.async_api import Page

STEALTH_SNIPPET = r"""
(() => {
  Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  window.navigator.chrome = { runtime: {} };
  Object.defineProperty(navigator, 'languages', { get: () => ['ar-SA','ar','en-US','en'] });
  Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
  const originalQuery = navigator.permissions && navigator.permissions.query;
  if (originalQuery) {
    navigator.permissions.query = (parameters) => (
      parameters && parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters)
    );
  }
  const getParameter = WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter = function (parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.call(this, parameter);
  };
})();
"""

async def apply_basic_stealth(page: Page) -> None:
    await page.add_init_script(STEALTH_SNIPPET)
