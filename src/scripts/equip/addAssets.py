import asyncio
import traceback
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# import helpers from your formFiller file
from formSteps import form_steps
from formFiller import wait_for_element, handle_macros, handle_macro_edits, fill_form

# ---- DB Connection ----
MONGO_URI = "mongodb+srv://uzairrather3147:Uzair123@cluster0.h7vvr.mongodb.net/mekyas"
client = AsyncIOMotorClient(MONGO_URI)
db = client["mekyas"]


async def add_assets_to_report(page, report_id):
    try:

        assets = await db.assetdatas.find({"report_id": report_id}).to_list(None)
        if not assets:
            return {"status": "FAILED", "error": f"No assets found for reportId={report_id}"}

        record = {"_id": report_id, "asset_data": assets}
        record["number_of_macros"] = str(len(assets))

        print(f"➡️ Adding {len(assets)} assets to report {report_id}")

        # 2️⃣ Navigate to the asset creation page
        asset_url = f"https://qima.taqeem.sa/report/asset/create/{report_id}"
        await page.get(asset_url)
        await asyncio.sleep(1)

        # 3️⃣ Handle assets step (reuse form_steps[1] for asset fields)
        if len(assets) > 10:
            result = await handle_macros(page, record)
        else:
            result = await fill_form(
                page,
                record,
                form_steps[1]["field_map"],  
                form_steps[1]["field_types"],
                is_last_step=True,
                skip_special_fields=True
            )

        if isinstance(result, dict) and result.get("status") == "FAILED":
            return result

        translate = await wait_for_element(page, "a[href='https://qima.taqeem.sa/setlocale/ar']", timeout=30)
        if not translate:
            return {
                "status": "FAILED",
                "step": "translate",
                "error": "Translate link not found"
            }
        await translate.click()
        await asyncio.sleep(1)

        macro_result = await handle_macro_edits(page, record)
        if isinstance(macro_result, dict) and macro_result.get("status") == "FAILED":
            return macro_result

        return {
            "status": "SUCCESS",
            "message": f"Assets added & macros filled successfully for report {report_id}",
            "recordId": str(record["_id"])
        }

    except Exception as e:
        tb = traceback.format_exc()
        return {"status": "FAILED", "error": str(e), "traceback": tb}

