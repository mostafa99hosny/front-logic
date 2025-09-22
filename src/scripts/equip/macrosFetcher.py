import asyncio
import re

lock1 = asyncio.Lock()

# ------------------------------
# Helpers
# ------------------------------

async def get_empty_index(empty_indexes):
    for i, v in enumerate(empty_indexes):
        if v == 1:
            return i
    raise RuntimeError("No free page index available")

async def go_to_url(pages, index, url):
    page = pages[index]
    await page.get(url)
    return page

async def safe_query_selector_all(page, selector, max_wait=10):
    """Safely query DOM elements, retrying up to max_wait seconds."""
    for _ in range(max_wait):
        try:
            elements = await page.query_selector_all(selector)
            if elements:
                return elements
        except Exception:
            pass
        await asyncio.sleep(1)
    return []

# ------------------------------
# Macro Fetching
# ------------------------------

async def get_macro_pages_num(browser, report_id):
    page = await browser.get(f"https://qima.taqeem.sa/report/{report_id}")
    await asyncio.sleep(1)
    li = await safe_query_selector_all(page, "ul.pagination > li > *")
    if li:
        try:
            last_text = await li[-2].text_content()
            page_no = int(last_text)
        except Exception:
            page_no = 1
    else:
        page_no = 1
    return page_no, page

async def get_macros_from_page(page):
    urls = []

    # Wait for the next button to appear (or pagination to be rendered)
    while not (next_buttons := await page.select_all(".paginate_button.next")):
        await asyncio.sleep(1)

    # Scrape current page for macro edit URLs
    html_content = await page.get_content()
    await asyncio.sleep(1)
    urls.extend(re.findall(r"(https://qima\.taqeem\.sa/report/macro/\d+/edit)", html_content))

    # If next button exists and is not disabled, click and scrape next page
    if "disabled" not in await next_buttons[0].get_html():
        await next_buttons[0].click()
        await asyncio.sleep(1)

        html_content = await page.get_content()
        await asyncio.sleep(1)
        urls.extend(re.findall(r"(https://qima\.taqeem\.sa/report/macro/\d+/edit)", html_content))

    return urls

async def get_macros(browser, report_id, assets_data, browsers_num=5):
    """
    Fetch macro edit URLs for all assets in a report.
    If assets already have a valid 'id', return URLs directly.
    Otherwise scrape the report pages to discover the macro edit links.
    """
    # 1️⃣ Use asset IDs directly if available (non-empty string only)
    assets_data_url = [
        f'https://qima.taqeem.sa/report/macro/{d["id"]}/edit'
        for d in assets_data
        if d.get("id") and str(d["id"]).strip()  # must exist and not be empty
    ]
    if assets_data_url:
        return assets_data_url

    # 2️⃣ Otherwise fetch from report pages
    pages_num, first_page = await get_macro_pages_num(browser, report_id)
    macros_urls = []

    semaphore = asyncio.Semaphore(browsers_num)
    empty_indexes = [1] * browsers_num
    pages = [first_page]

    # Open extra tabs only if browsers_num > 1
    for _ in range(max(0, browsers_num - 1)):
        p = await browser.get("about:blank", new_tab=True)
        pages.append(p)

    async def limited_task(page_no):
        async with semaphore:
            async with lock1:
                index = await get_empty_index(empty_indexes)
                empty_indexes[index] = 0

            page = await go_to_url(
                pages, index, f"https://qima.taqeem.sa/report/{report_id}?page={page_no}"
            )
            await asyncio.sleep(0.5)
            macros_urls.extend(await get_macros_from_page(page))
            empty_indexes[index] = 1

    # Run scraping tasks
    if pages_num == 1:
        await limited_task(1)
    else:
        tasks = [limited_task(i + 1) for i in range(pages_num)]
        await asyncio.gather(*tasks)

    # cleanup extra tabs
    for p in pages[1:]:
        await p.close()

    return macros_urls

