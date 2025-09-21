import asyncio
import time
import traceback
from motor.motor_asyncio import AsyncIOMotorClient

from formSteps import form_steps

import json

import json

async def bulk_inject_inputs(page, record, field_map, field_types):
    selects = {}
    others = {}

    for key, selector in field_map.items():
        if key not in record:
            continue

        field_type = field_types.get(key, "text")
        value = str(record[key] or "")

        # separate dynamic selects from normal
        if field_type == "select":
            selects[selector] = {"type": "select", "value": value}
        elif field_type == "text":
            others[selector] = {"type": "text", "value": value}
        elif field_type == "checkbox":
            others[selector] = {"type": "checkbox", "value": bool(value)}
        elif field_type in ["dynamic_select", "location", "file"]:
          continue

    async def inject(jsdata):
        if not jsdata:
            return
        data_json = json.dumps(jsdata)
        js = f"""
        (function() {{
            const data = {data_json};
            for (const [selector, meta] of Object.entries(data)) {{
                const el = document.querySelector(selector);
                if (!el) continue;

                switch (meta.type) {{
                    case "checkbox":
                        el.checked = meta.value;
                        el.dispatchEvent(new Event("change", {{ bubbles: true }}));
                        break;

                    case "select":
                        let matched = false;
                        for (const option of el.options) {{
                            if (option.value == meta.value || option.text == meta.value) {{
                                el.value = option.value;
                                matched = true;
                                break;
                            }}
                        }}
                        if (!matched && el.options.length) {{
                            el.selectedIndex = 0;
                        }}
                        el.dispatchEvent(new Event("change", {{ bubbles: true }}));
                        break;

                    case "text":
                    default:
                        el.value = meta.value;
                        el.dispatchEvent(new Event("input", {{ bubbles: true }}));
                        el.dispatchEvent(new Event("change", {{ bubbles: true }}));
                        break;
                }}
            }}
            return true;
        }})();
        """
        await page.evaluate(js)

    # Inject selects first (so dependent dropdowns can update)
    await inject(selects)

    # Then inject text + checkboxes
    await inject(others)


async def select_select2_option_simple(page, selector, value):
    try:
        print(f"Selecting Select2 option: {value}")
        element = await page.find(selector)
        
        if not element:
            print(f"No Select2 element found for {selector}")
            return False

        await element.apply("""
        (el) => {
            const evt = new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window });
            el.dispatchEvent(evt);
        }
        """)
        await asyncio.sleep(1)

        search_input = await wait_for_element(page, "input.select2-search__field", timeout=5)
        if not search_input:
            print("No search input found")
            return False

        await search_input.focus()
        await search_input.clear_input()
        await asyncio.sleep(0.1)
        await search_input.send_keys(value)

        await search_input.apply("""
        (el) => {
            const evt = new KeyboardEvent('keydown', {
                key: 'Enter',
                code: 'Enter',
                keyCode: 13,
                which: 13,
                bubbles: true,
                cancelable: true,
                view: window
            });
            el.dispatchEvent(evt);
        }
        """)

        await asyncio.sleep(1)
        print(f"Successfully selected: {value}")
        return True
        
    except Exception as e:
        print(f"Select2 selection failed: {e}")
        return False


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


# ------------------------------
# Fill form (with bulk injection)
# ------------------------------
async def fill_form(page, record, field_map, field_types, is_last_step=False, retries=0, max_retries=2):
    try:
        # bulk inject everything except location/file
        await bulk_inject_inputs(page, record, field_map, field_types)

        # handle location + file separately
        for key, selector in field_map.items():
            if key not in record:
                continue

            value = str(record[key] or "")
            field_type = field_types.get(key, "text")

            try:

                if field_type == "dynamic_select":
                    print("trying to select element")
                    select_element = await wait_for_element(page, selector, timeout=10)
                    print(f"selected element: {select_element}")
                    if not select_element:
                        print(f"Warning: No select element found for selector {selector}")
                        continue

                    options = select_element.children
                    option_found = False

                    for option in options:
                        option_text = option.text or ""
                        if option_text.lower() == value.lower():
                            await option.select_option()
                            option_found = True
                            break

                    if not option_found:
                        for option in options:
                            option_text = (option.text or "").strip()
                            if value.lower() in option_text.lower():
                                await option.select_option()
                                option_found = True
                                print(f"Warning: Approx match used for '{value}'")
                                break

                elif field_type == "location":
                    success = await select_select2_option_simple(page, selector, value)
                    if not success:
                        print(f"Failed to select location '{value}'")


                elif field_type == "file":
                    file_input = await wait_for_element(page, selector, timeout=10)
                    if file_input:
                        print(f"Sending file {value}")
                        try:
                            await file_input.send_file(value)
                            print("File uploaded successfully")
                        except Exception as e:
                            print(f"send_files failed: {e}")
                    else:
                        print(f"Warning: No file input found for selector {selector}")

            except Exception as e:
                print(f"Error handling special field {key}: {e}")
                continue

        if not is_last_step:
            continue_btn = await wait_for_element(page, "input[name='continue']", timeout=10)
            if continue_btn:
                print("Clicking continue button...")
                await asyncio.sleep(0.5)
                await continue_btn.click()
                await asyncio.sleep(2)

                error_div = await wait_for_element(page, "div[class='alert alert-danger']", timeout=10)
                if error_div:
                    print("Validation error found: retrying step")
                    if retries < max_retries:
                        await asyncio.sleep(1)
                        return await fill_form(page, record, field_map, field_types, is_last_step, retries + 1, max_retries)
                    else:
                        return {"status": "FAILED", "error": "Validation error found"}
                await wait_for_element(page, "input", timeout=10)
                return True
            else:
                print("No continue button found - may be on final step")
                return False
        else:
            print("Last step completed - clicking save button")
            save_btn = await wait_for_element(page, "input[name='save']", timeout=10)
            if save_btn:
                await asyncio.sleep(0.5)
                await save_btn.click()
                await asyncio.sleep(5)
                current_url = await page.evaluate("window.location.href")
                print(f"Current URL: {current_url}")
                form_id = current_url.rstrip("/").split("/")[-1]
                print(f"Extracted formId: {form_id}")

                if form_id:
                    await db.taqeemforms.update_one(
                        {"_id": record["_id"]},
                        {"$set": {"formId": form_id}}
                    )
                    print(f"Updated record {record['_id']} with formId {form_id}")
            else:
                return {"status": "FAILED", "error": "Save button not found"}
            
    except Exception as e:
        print(f"Error filling form: {e}")
        return False

MONGO_URI = "mongodb+srv://uzairrather3147:Uzair123@cluster0.h7vvr.mongodb.net/mekyas"
client = AsyncIOMotorClient(MONGO_URI)
db = client["mekyas"]

async def runFormFill(page, batch_id):
    try:
        cursor = db.taqeemforms.find({"batchId": batch_id})
        records = await cursor.to_list(length=None)
        results = [{"status": "FETCHED_DATA", "count": len(records)}]

        if not records:
            return {"status": "FAILED", "error": f"No records for batchId={batch_id}", "records": results}

        failed_count = 0
        for record in records:
            if record.get("formId"):
                continue

            record_failed = False
            for step_num, step_config in enumerate(form_steps, 1):
                is_last_step = (step_num == len(form_steps))
                results.append({"status": "STEP_STARTED", "step": step_num, "recordId": str(record["_id"])})

                result = await fill_form(page, record, step_config["field_map"], step_config["field_types"], is_last_step)

                if isinstance(result, dict) and result.get("status") == "FAILED":
                    record_failed = True
                    failed_count += 1
                    results.append({"status": "FAILED", "step": step_num, "recordId": str(record["_id"]), "error": result.get("error")})
                    break

                if is_last_step and not record_failed:
                    results.append({"status": "FORM_FILL_SUCCESS", "message": "Form submitted", "recordId": str(record["_id"]), "batchId": batch_id})

            await page.get("https://qima.taqeem.sa/report/create/1/137")
            await asyncio.sleep(1)

        return {"status": "SUCCESS", "batchId": batch_id, "failed_records": failed_count, "results": results}

    except Exception as e:
        tb = traceback.format_exc()
        return {"status": "FAILED", "error": str(e), "traceback": tb}
