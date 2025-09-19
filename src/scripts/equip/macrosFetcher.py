import asyncio
import re
from contextlib import asynccontextmanager

lock1 = asyncio.Lock()

async def get_empty_index(empty_indexes):
    for i, v in enumerate(empty_indexes):
        if v == 1:
            return i
    raise RuntimeError("No free page index available")

async def go_to_url(pages, index, url):
    page = pages[index]
    await page.get(url)
    return page

async def get_macro_pages_num(browser, report_id):
    # open first page
    page = await browser.get(f"https://qima.taqeem.sa/report/{report_id}")
    
    # wait until pagination appears
    while not (await page.query_selector(".paginate_button.next")):
        await asyncio.sleep(1)
        
    await asyncio.sleep(1)
    li = await page.query_selector_all("//ul[@class='pagination']/li/*")
    if li:
        last_text = await li[-2].text_content()
        page_no = int(last_text)
    else:
        page_no = 1

    return page_no, page   # return page so caller can reuse

async def get_macros_from_page(page):
    urls = []

    # wait for pagination next button
    while not (await page.query_selector(".paginate_button.next")):
        await asyncio.sleep(1)

    html_content = await page.content()
    urls.extend(re.findall(r"(https://qima\.taqeem\.sa/report/macro/\d+/edit)", html_content))

    next_button = await page.query_selector(".paginate_button.next")
    if next_button and "disabled" not in (await next_button.get_attribute("class") or ""):
        await next_button.click()
        await asyncio.sleep(1)
        html_content = await page.content()
        urls.extend(re.findall(r"(https://qima\.taqeem\.sa/report/macro/\d+/edit)", html_content))
    
    return urls

async def get_macros(browser, report_id, assets_data, browsers_num):
    # ✅ if macros already have IDs, just build the URLs
    assets_data_url = []
    for d in assets_data:
        if int(d["macroid"]) != 0:
            assets_data_url.append(f'https://qima.taqeem.sa/report/macro/{d["macroid"]}/edit')
        else:
            break
    else:
        return assets_data_url

    # otherwise, we must fetch them from the macro listing pages
    pages_num, first_page = await get_macro_pages_num(browser, report_id)
    macros_urls = []

    semaphore = asyncio.Semaphore(browsers_num)
    empty_indexes = [1 for _ in range(browsers_num)]
    pages = [first_page]  # first page already opened

    # pre-open extra tabs
    for _ in range(browsers_num - 1):
        p = await browser.get("about:blank", new_tab=True)
        pages.append(p)

    async def limited_task(page_no):
        async with semaphore:
            async with lock1:
                index = await get_empty_index(empty_indexes)
                empty_indexes[index] = 0

            page = await go_to_url(pages, index, f"https://qima.taqeem.sa/report/{report_id}?page={page_no}")
            await asyncio.sleep(0.5)

            macros_urls.extend(await get_macros_from_page(page))

            empty_indexes[index] = 1

    tasks = [limited_task(i + 1) for i in range(pages_num)]
    await asyncio.gather(*tasks)

    # cleanup: close all extra pages
    for p in pages[1:]:
        await p.close()
    
    return macros_urls
