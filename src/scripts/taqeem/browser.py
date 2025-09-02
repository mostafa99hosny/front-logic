import asyncio, time
import nodriver as uc

browser = None
page = None

async def wait_for_element(page, selector, timeout=30, check_interval=1):
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            element = await page.query_selector(selector)

            if element:
                return element
            
        except Exception:
            pass

        await asyncio.sleep(check_interval)
    return None

async def get_browser():
    global browser

    if browser is None:
        browser = await uc.start(headless=False, window_size=(1200, 800))

    return browser

async def closeBrowser():
    global browser, page

    if browser:
        try:
            await browser.stop()

        except Exception:
            pass
        
    browser, page = None, None

def set_page(new_page):
    global page
    page = new_page

def get_page():
    global page
    return page