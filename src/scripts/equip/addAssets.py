import asyncio
import traceback
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

MONGO_URI = "mongodb+srv://test:JUL3OvyCSLVjSixj@assetval.pu3bqyr.mongodb.net/projectForever"
client = AsyncIOMotorClient(MONGO_URI)
db = client["projectForever"]

from formFiller import wait_for_element, fill_assets_via_macro_urls
from macrosFetcher import get_macros, get_macros_from_page, get_macro_pages_num

async def check_incomplete_macros(browser, report_id, browsers_num=3):
    try:
        print("Fetching assets for report ID:", report_id)
        assets = await db.assetdatas.find({"report_id": report_id}).to_list(None)
        print("assets:", assets)
        if not assets:
            return {"status": "FAILED", "error": "No assets found in DB"}

        pages_num, _ = await get_macro_pages_num(browser, report_id)
        if pages_num == 0:
            return {"status": "SUCCESS", "macro_count": 0, "message": "No macros to check"}

        macros_urls = []

        async def fetch_macros_from_page(page_no):
            page = await browser.get(f"https://qima.taqeem.sa/report/{report_id}?page={page_no}")
            await asyncio.sleep(0.5)
            page_macros = await get_macros_from_page(page)
            macros_urls.extend(page_macros)

        tasks = [fetch_macros_from_page(page_no) for page_no in range(1, pages_num + 1)]
        await asyncio.gather(*tasks)
        macros_urls = list(set(macros_urls)) 

        incomplete_count = 0

        for url in macros_urls:
            macro_id = url.rstrip("/").split("/")[-2].strip()
            print("Macro ID to check:", macro_id)
            show_url = url.replace("edit", "show")
            page = await browser.get(show_url)
            await asyncio.sleep(0.5)
            html_content = await page.get_content()
            if html_content and "غير مكتملة" in html_content:
                print("Macro is incomplete:", macro_id)
                incomplete_count += 1
                await db.assetdatas.update_one(
                    {"id": int(macro_id)},
                    {"$set": {"submitState": 0}}
                )
            else:
                print("Macro is complete:", macro_id)
                result = await db.assetdatas.update_one(
                    {"id": int(macro_id)},
                    {"$set": {"submitState": 1}}
                )
                print("Matched:", result.matched_count, "Modified:", result.modified_count)

        return {"status": "SUCCESS", "macro_count": incomplete_count}

    except Exception as e:
        tb = traceback.format_exc()
        print("traceback:", tb)
        return {"status": "FAILED", "error": str(e), "traceback": tb}
    

async def check_incomplete_macros_after_creation(browser, record_id, browsers_num=3):
    try:
        print("Fetching assets for DB ID:", record_id)
        report = await db.halfreports.find_one({"_id": ObjectId(record_id)})
        assets = report.get("asset_data", [])
        if not assets:
            return {"status": "FAILED", "error": "No assets found in DB"}
        
        report_id = report.get("report_id")
        report_url = f"https://qima.taqeem.sa/report/{report_id}"

        # Open the main report page
        main_page = await browser.get(report_url)
        await asyncio.sleep(1)

        # Check for delete button
        delete_btn = await wait_for_element(main_page, "#delete_report", timeout=5)
        if delete_btn:
            print("[INFO] Delete button exists, assuming all macros complete.")
            # Mark all assets as complete
            await db.halfreports.update_one(
                {"_id": ObjectId(record_id)},
                {"$set": {f"asset_data.{i}.submitState": 1 for i in range(len(assets))}}
            )
            return {"status": "SUCCESS", "macro_count": 0, "message": "All macros complete"}

        macro_ids = [str(asset["id"]) for asset in assets if "id" in asset]
        if not macro_ids:
            return {"status": "SUCCESS", "macro_count": 0, "message": "No macros found in DB assets"}

        macros_urls = [f"https://qima.taqeem.sa/report/macro/{macro_id}/show" for macro_id in macro_ids]

        pages = [await browser.get("about:blank", new_tab=True) for _ in range(min(browsers_num, len(macros_urls)))]
        chunks = [macros_urls[i::len(pages)] for i in range(len(pages))]

        incomplete_count = 0

        async def process_chunk(page, urls):
            nonlocal incomplete_count
            for url in urls:
                macro_id = url.rstrip("/").split("/")[-2].strip()
                await page.get(url)
                await asyncio.sleep(0.5)
                html_content = await page.get_content()

                submit_state = 0 if (html_content and "غير مكتملة" in html_content) else 1

                await db.halfreports.update_one(
                    {"_id": ObjectId(record_id), "asset_data.id": int(macro_id)},
                    {"$set": {"asset_data.$.submitState": submit_state}}
                )

                if submit_state == 0:
                    incomplete_count += 1

        await asyncio.gather(*[process_chunk(p, chunk) for p, chunk in zip(pages, chunks)])

        for p in pages:
            await p.close()

        return {"status": "SUCCESS", "macro_count": incomplete_count}

    except Exception as e:
        tb = traceback.format_exc()
        print("traceback:", tb)
        return {"status": "FAILED", "error": str(e), "traceback": tb}



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
        if translate:
            await translate.click()
            await asyncio.sleep(1)
        else:
            print("⚠️ No translate link found")

        macro_result = await fill_assets_via_macro_urls(browser, record, macro_urls, tabs_num=3)
        if isinstance(macro_result, dict) and macro_result.get("status") == "FAILED":
            return macro_result

        check_result = await check_incomplete_macros(browser, report_id, browsers_num=3)
        if check_result.get("status") == "FAILED":
            print("⚠️ Warning: Failed to check incomplete macros:", check_result.get("error"))

        return {
            "status": "SUCCESS",
            "message": f"Assets linked & macros filled successfully for report {report_id}",
            "recordId": str(record["_id"]),
            "macro_urls": macro_urls,
            "incomplete_macros": check_result.get("macro_count", 0)
        }


    except Exception as e:
        tb = traceback.format_exc()
        return {"status": "FAILED", "error": str(e), "traceback": tb}
