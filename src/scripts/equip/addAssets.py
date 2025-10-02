import asyncio
import traceback
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

MONGO_URI = "mongodb+srv://test:JUL3OvyCSLVjSixj@assetval.pu3bqyr.mongodb.net/projectForever"
client = AsyncIOMotorClient(MONGO_URI)
db = client["projectForever"]

from formFiller import wait_for_element, fill_assets_via_macro_urls
from macrosFetcher import get_macros, get_macros_from_page, get_macro_pages_num

async def check_incomplete_macros(browser, record_id):
    try:
        print(f"[CHECK] Starting incomplete macro check for report {record_id}")

        # First, fetch halfreport to map macro IDs
        report = await db.halfreports.find_one({"_id": ObjectId(record_id)})
        if not report:
            return {"status": "FAILED", "error": f"Report {record_id} not found in halfreports"}

        report_id = report.get("report_id")
        if not report_id:
            return {"status": "FAILED", "error": f"No report_id found for {record_id}"}

        base_url = f"https://qima.taqeem.sa/report/{report_id}"
        page = await browser.get(base_url)
        await asyncio.sleep(1)

        incomplete_ids = []

        # Outer loop = report pages
        while True:
            # Inner loop = table sub-pages
            while True:
                await wait_for_element(page, "#m-table", timeout=5)
                rows = await page.query_selector_all("#m-table tbody tr")

                for row in rows:
                    status_cell = await row.query_selector("td:nth-child(6)")
                    status_text = (status_cell.text).strip() if status_cell else ""

                    id_cell = await row.query_selector("td:nth-child(1) a")
                    macro_id = (id_cell.text).strip() if id_cell else None

                    if not macro_id:
                        continue

                    submit_state = 0 if "غير مكتملة" in status_text else 1

                    await db.halfreports.update_one(
                        {"_id": ObjectId(record_id), "asset_data.id": int(macro_id)},
                        {"$set": {"asset_data.$.submitState": submit_state}}
                    )

                    if submit_state == 0:
                        print(f"[INCOMPLETE] Macro {macro_id}")
                        incomplete_ids.append(int(macro_id))

                # Try next sub-page
                next_btn = await wait_for_element(page, "#m-table_next", timeout=5)
                if next_btn:
                    classes = next_btn.attrs.get("class_") or ""
                    if "disabled" not in classes:
                        await next_btn.click()
                        await asyncio.sleep(1)
                        continue
                # no more sub-pages
                break

            # Try next outer page
            alt_btn_list = await page.xpath('/html/body/div/div[5]/div[2]/div/div[8]/div/div/div/nav/ul/li[5]/a')
            alt_btn = alt_btn_list[0] if alt_btn_list else None
            if alt_btn:
                classes = alt_btn.attrs.get("class_") or ""
                if "disabled" not in classes:
                    await alt_btn.click()
                    await asyncio.sleep(1)
                    continue

            # no more outer pages
            print("[CHECK] No next page, stopping.")
            break

        return {
            "status": "SUCCESS",
            "incomplete_ids": incomplete_ids,
            "macro_count": len(incomplete_ids)
        }

    except Exception as e:
        tb = traceback.format_exc()
        print("[CHECK] Error:", tb)
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