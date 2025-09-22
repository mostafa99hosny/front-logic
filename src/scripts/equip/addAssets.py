import asyncio
import traceback
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb+srv://test:JUL3OvyCSLVjSixj@assetval.pu3bqyr.mongodb.net/projectForever"
client = AsyncIOMotorClient(MONGO_URI)
db = client["projectForever"]

from formFiller import wait_for_element, fill_assets_via_macro_urls
from macrosFetcher import get_macros  

async def add_assets_to_report(browser, report_id, browsers_num=5):
    try:
        assets = await db.assetdatas.find({"report_id": report_id}).to_list(None)
        if not assets:
            return {"status": "FAILED", "error": f"No assets found for reportId={report_id}"}

        record = {"_id": report_id, "asset_data": assets}
        record["number_of_macros"] = str(len(assets))
        print(f"➡️ Linking {len(assets)} assets to report {report_id}")

        macro_urls = await get_macros(browser, report_id, assets, browsers_num)
        if not macro_urls:
            return {"status": "FAILED", "error": "No macro edit URLs found"}

        print(f"✅ Found {len(macro_urls)} macro edit links: {macro_urls}")

        page = await browser.get(f"https://qima.taqeem.sa/report/{report_id}")
        translate = await wait_for_element(page, "a[href='https://qima.taqeem.sa/setlocale/ar']", timeout=30)
        if not translate:
            return {"status": "FAILED", "error": "Translate link not found"}
        await translate.click()
        await asyncio.sleep(1)

        macro_result = await fill_assets_via_macro_urls(browser, record, macro_urls, tabs_num=3)
        if isinstance(macro_result, dict) and macro_result.get("status") == "FAILED":
            return macro_result


        return {
            "status": "SUCCESS",
            "message": f"Assets linked & macros filled successfully for report {report_id}",
            "recordId": str(record["_id"]),
            "macro_urls": macro_urls
        }

    except Exception as e:
        tb = traceback.format_exc()
        return {"status": "FAILED", "error": str(e), "traceback": tb}
