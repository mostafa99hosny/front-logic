import asyncio, traceback
from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from formFiller2 import (
    emit_progress, fill_form, handle_macros_multi, handle_macro_edits,
    retryMacros, check_incomplete_macros_after_creation, check_incomplete_macros
)

from formSteps2 import form_steps

MONGO_URI = "mongodb+srv://test:JUL3OvyCSLVjSixj@assetval.pu3bqyr.mongodb.net/projectForever"
client = AsyncIOMotorClient(MONGO_URI)
db = client["projectForever"]

async def navigate_to_existing_report_assets(browser, report_id, control_state=None):
    from worker_equip import check_control
    
    if control_state:
        await check_control(control_state)
    
    asset_creation_url = f"https://qima.taqeem.sa/report/asset/create/{report_id}"
    emit_progress("NAVIGATING_ASSET_PAGE", f"Navigating to asset creation for report {report_id}", report_id)
    
    main_page = await browser.get(asset_creation_url)
    await asyncio.sleep(2)
    
    current_url = await main_page.evaluate("window.location.href")
    if str(report_id) not in current_url:
        emit_progress("NAVIGATION_FAILED", f"Failed to navigate to asset creation page for report {report_id}", report_id)
        return None
    
    emit_progress("ON_ASSET_PAGE", f"Successfully reached asset creation page: {current_url}", report_id)
    return main_page

async def handle_existing_report_macros(browser, record, tabs_num=3, control_state=None, record_id=None):
    from worker_equip import check_control
    
    results = []
    
    # Get report_id from the record
    report_id = record.get("report_id")
    if not report_id:
        emit_progress("MISSING_REPORT_ID", "Report ID not found in record data", record_id)
        return {"status": "FAILED", "error": "Report ID not found in record data"}
    
    main_page = await navigate_to_existing_report_assets(browser, report_id, control_state)
    if not main_page:
        return {"status": "FAILED", "error": f"Could not navigate to asset creation page for report {report_id}"}
    
    total_macros = len(record.get("asset_data", []))
    record["number_of_macros"] = str(total_macros)
    
    emit_progress("MACRO_CREATION_START", f"Starting macro creation for {total_macros} assets in existing report", record_id)
    
    if total_macros > 10:
        macro_result = await handle_macros_multi(browser, record, tab_nums=tabs_num, batch_size=10, 
                                                control_state=control_state, report_id=record_id)
    else:
        macro_result = await fill_form(
            main_page, 
            record, 
            form_steps[1]["field_map"], 
            form_steps[1]["field_types"], 
            is_last_step=True,
            skip_special_fields=True,
            control_state=control_state,
            report_id=record_id
        )
    
    if isinstance(macro_result, dict) and macro_result.get("status") == "FAILED":
        emit_progress("MACRO_CREATION_FAILED", "Macro creation failed", record_id, error=macro_result.get("error"))
        return {"status": "FAILED", "error": macro_result.get("error")}
    
    emit_progress("MACRO_CREATION_SUCCESS", "Macro creation completed successfully", record_id)
    
    emit_progress("MACRO_EDIT_START", "Starting macro editing process", record_id)
    edit_result = await handle_macro_edits(browser, record, tabs_num=tabs_num, 
                                          control_state=control_state, report_id=record_id)
    
    if isinstance(edit_result, dict) and edit_result.get("status") == "FAILED":
        emit_progress("MACRO_EDIT_FAILED", "Macro editing failed", record_id, error=edit_result.get("error"))
        return {"status": "FAILED", "error": edit_result.get("error")}
    
    emit_progress("MACRO_EDIT_SUCCESS", "Macro editing completed successfully", record_id)
    
    pages = browser.tabs
    for p in pages[1:]:
        await p.close()
    
    emit_progress("CHECKING_INCOMPLETE", "Checking for incomplete macros", record_id)
    checker_result = await check_incomplete_macros_after_creation(browser, record_id, browsers_num=tabs_num)
    results.append({"status": "CHECKER_RESULT", "recordId": str(record["_id"]), "result": checker_result})
    
    if checker_result.get("macro_count", 0) > 0:
        emit_progress("RETRYING_MACROS", f"Retrying {checker_result['macro_count']} incomplete macros", record_id)
        await retryMacros(browser, record_id, tabs_num=tabs_num, control_state=control_state)
    
    return {"status": "SUCCESS", "results": results, "report_id": report_id, "record_id": record_id}

async def noBaserunFormFill(browser, record_id, tabs_num=3, control_state=None):    
    try:
        if not ObjectId.is_valid(record_id):
            return {"status": "FAILED", "error": "Invalid record_id"}
        
        emit_progress("FETCHING_RECORD", f"Fetching record data from database for record_id: {record_id}", record_id)
        
        # Fetch the complete record from MongoDB using record_id
        record = await db.halfreports.find_one({"_id": ObjectId(record_id)})
        if not record:
            return {"status": "FAILED", "error": "Record not found in database"}
        
        # Extract report_id from the record
        report_id = record.get("report_id")
        if not report_id:
            return {"status": "FAILED", "error": "Report ID not found in record data"}
        
        # Check if asset_data exists
        asset_data = record.get("asset_data", [])
        if not asset_data:
            return {"status": "FAILED", "error": "No asset data found in record"}
        
        emit_progress("RECORD_FETCHED", f"Successfully fetched record with {len(asset_data)} assets and report_id: {report_id}", record_id)
        
        # Update start time
        await db.halfreports.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": {"startSubmitTime": datetime.now(timezone.utc)}}
        )
        
        emit_progress("STARTING_PROCESS", f"Starting macro creation process for record {record_id} with report {report_id}", record_id)
        
        # Run the macro creation process
        result = await handle_existing_report_macros(browser, record, tabs_num, control_state, record_id)
        
        # Update end time
        await db.halfreports.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": {"endSubmitTime": datetime.now(timezone.utc)}}
        )
        
        if result.get("status") == "SUCCESS":
            emit_progress("PROCESS_COMPLETE", "Macro creation process completed successfully", record_id)
        else:
            emit_progress("PROCESS_FAILED", "Macro creation process failed", record_id, 
                         error=result.get("error", "Unknown error"))
        
        return result
        
    except Exception as e:
        tb = traceback.format_exc()
        emit_progress("PROCESS_ERROR", f"Macro creation process failed: {str(e)}", record_id, error=str(e))
        
        # Update end time on error
        try:
            await db.halfreports.update_one(
                {"_id": ObjectId(record_id)},
                {"$set": {"endSubmitTime": datetime.now(timezone.utc)}}
            )
        except:
            pass
            
        return {"status": "FAILED", "error": str(e), "traceback": tb}

async def noBaserunCheckMacros(browser, record_id, tabs_num=3):
    """Check incomplete macros for existing reports"""
    try:
        if not ObjectId.is_valid(record_id):
            return {"status": "FAILED", "error": "Invalid record_id"}
        
        emit_progress("CHECK_STARTED", f"Checking incomplete macros for record {record_id}", record_id)
        
        # Use the existing check function
        check_result = await check_incomplete_macros(browser, record_id)
        
        emit_progress("CHECK_COMPLETE", f"Found {check_result.get('macro_count', 0)} incomplete macros", 
                     record_id, result=check_result)
        
        return {
            "status": "SUCCESS",
            "recordId": str(record_id),
            "result": check_result
        }
        
    except Exception as e:
        tb = traceback.format_exc()
        emit_progress("CHECK_FAILED", f"Check failed: {str(e)}", record_id, error=str(e))
        return {
            "status": "FAILED",
            "error": str(e),
            "traceback": tb
        }

async def noBaseRetryMacros(browser, record_id, tabs_num=3, control_state=None):
    from worker_equip import check_control
    
    try:
        if control_state:
            await check_control(control_state)
        
        emit_progress("RETRY_STARTED", f"Starting retry for record {record_id}", record_id)
        
        result = await retryMacros(browser, record_id, tabs_num=tabs_num, control_state=control_state)
        
        if result.get("status") == "SUCCESS":
            emit_progress("RETRY_COMPLETE", "Retry completed successfully", record_id)
        else:
            emit_progress("RETRY_FAILED", "Retry failed", record_id, error=result.get("error"))
        
        return result
        
    except Exception as e:
        tb = traceback.format_exc()
        emit_progress("RETRY_ERROR", f"Retry failed: {str(e)}", record_id, error=str(e))
        return {"status": "FAILED", "error": str(e), "traceback": tb}