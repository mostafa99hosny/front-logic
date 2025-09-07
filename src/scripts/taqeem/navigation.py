from browser import wait_for_element
import asyncio

async def post_login_navigation(page):
    try:
        await page.get("https://qima.taqeem.sa/report/create/1/137")
        await asyncio.sleep(1)

        translate = await wait_for_element(page, "a[href='https://qima.taqeem.sa/setlocale/en']", timeout=30)
        if not translate:
            return {"status": "FAILED", "error": "Translate link not found"}
        await translate.click()

        return {"status": "SUCCESS"}

    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
