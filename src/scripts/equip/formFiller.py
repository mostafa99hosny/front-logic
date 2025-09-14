import asyncio
import time
import traceback
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from formSteps import form_steps, macro_form_config


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


async def wait_for_element(page, selector, timeout=30, check_interval=0.5):
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

async def fill_clients(page, clients):
    if not clients:
        return

    client = clients[0]  # Only take the first one

    name_selector = "[name='client[0][name]']"
    tel_selector = "[name='client[0][telephone]']"
    email_selector = "[name='client[0][email]']"

    for selector, value in [
        (name_selector, client.get("client_name", "")),
        (tel_selector, client.get("telephone_number", "")),
        (email_selector, client.get("email_address", "")),
    ]:
        el = await wait_for_element(page, selector, timeout=5)
        if el:
            await el.clear_input()
            await asyncio.sleep(0.05)
            await el.send_keys(value)
        else:
            print(f"⚠️ Could not find element for selector {selector}")

async def fill_valuers(page, valuers):
    count = len(valuers)
    if count > 1:
        for _ in range(count - 1):
            add_btn = await wait_for_element(page, "#duplicateValuer", timeout=5)
            if add_btn:
                await add_btn.click()
                await asyncio.sleep(0.5)

    # Now fill the data
    for idx, valuer in enumerate(valuers):
        name_selector = f"[name='valuer[{idx}][id]']"
        contrib_selector = f"[name='valuer[{idx}][contribution]']"

        # Handle plain select dropdowns
        for selector, value in [
            (name_selector, valuer.get("valuer_name", "")),
            (contrib_selector, str(valuer.get("contribution_percentage", "")))
        ]:
            select_element = await wait_for_element(page, selector, timeout=10)
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


async def fill_report_users(page, report_users):
    if not report_users:
        return

    count = len(report_users)

    # If multiple report users, add extra rows
    if count > 1:
        for _ in range(count - 1):
            add_btn = await wait_for_element(page, "#duplicateUser", timeout=5)
            if add_btn:
                await add_btn.click()
                await asyncio.sleep(0.5)

    # Now fill the names
    for idx, name in enumerate(report_users):
        selector = f"[name='user[{idx}][name]']"
        el = await wait_for_element(page, selector, timeout=5)
        if el:
            await el.clear_input()
            await asyncio.sleep(0.05)
            await el.send_keys(name)
            print(f"✅ Filled report user {idx+1}: {name}")
        else:
            print(f"⚠️ Could not find input for report user {idx+1}")




async def fill_form(page, record, field_map, field_types, is_last_step=False, retries=0, max_retries=2, skip_special_fields=False):
    if not skip_special_fields:
        if "clients" in record and record["clients"]:
            await fill_clients(page, record["clients"])

        if "valuers" in record and record["valuers"]:
            await fill_valuers(page, record["valuers"])

        if "report_users" in record and record["report_users"]:
            await fill_report_users(page, record["report_users"])

    # 🔹 Handle normal fields
    for key, selector in field_map.items():
        if key not in record:
            continue

        value = str(record[key] or "")
        field_type = field_types.get(key, "text")

        try:
            if field_type == "text":
                element = await wait_for_element(page, selector, timeout=10)
                if element:
                    await element.apply("(el) => el.removeAttribute('readonly')")
                    await element.clear_input()
                    await asyncio.sleep(0.1)
                    await element.send_keys(value)

            elif field_type == "location":
                success = await select_select2_option_simple(page, selector, value)
                if not success:
                    print(f"Failed to select location '{value}'")

            elif field_type == "select":
                select_element = await wait_for_element(page, selector, timeout=10)
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

            elif field_type == "radio":
                elements = await page.query_selector_all(selector)
                if elements:
                    for element in elements:
                        parent = element.parent
                        if parent:
                            sibling = await parent.query_selector("label")
                            if sibling:
                                labelText = sibling.text
                                if labelText and value.lower() in labelText.lower():
                                    await element.click()
                                    print(f"Selected radio by label text: {value}")
                                    break

            elif field_type == "file":
                file_input = await wait_for_element(page, selector, timeout=10)
                if file_input:
                    try:
                        await file_input.send_file(value)
                        print("File uploaded")
                    except Exception as e:
                        print(f"send_files failed: {e}")
                else:
                    print(f"Warning: No file input found for selector {selector}")

            elif field_type == "checkbox":
                checkbox = await wait_for_element(page, selector, timeout=5)
                if not checkbox:
                    print(f"⚠️ No checkbox found for selector {selector}")
                else:
                    if value: 
                        await checkbox.click()
                        print("✅ Checkbox checked")

        except Exception as e:
            print(f"Error filling {key}: {e}")
            continue

    try:
        if not is_last_step:
            continue_btn = await wait_for_element(page, "input[name='continue']", timeout=10)
            if continue_btn:
                await asyncio.sleep(0.5)
                await continue_btn.click()
                await asyncio.sleep(2)

                error_div = await wait_for_element(page, "div[class='alert alert-danger']", timeout=5)
                if error_div:
                    if retries < max_retries:
                        await asyncio.sleep(1)
                        return await fill_form(page, record, field_map, field_types, is_last_step, retries + 1, max_retries)
                    else:
                        return {"status": "FAILED", "error": "Validation error found"}

                return True
            else:
                print("No continue button found")
                return False
        else:
            save_btn = await wait_for_element(page, "input[type='submit']", timeout=10)
            if save_btn:
                await asyncio.sleep(0.5) 

                await save_btn.click()
                await asyncio.sleep(2)

                return {"status": "SAVED"}
            else:
                return {"status": "FAILED", "error": "Save button not found"}

    except Exception as e:
        print(f"Error clicking button: {e}")
        return {"status": "FAILED", "error": str(e)}



MONGO_URI = "mongodb+srv://uzairrather3147:Uzair123@cluster0.h7vvr.mongodb.net/mekyas"
client = AsyncIOMotorClient(MONGO_URI)
db = client["mekyas"]


def chunk_macros(macros, chunk_size=10):
    for i in range(0, len(macros), chunk_size):
        yield macros[i:i + chunk_size]


async def handle_macros(page, record):
    macros = record.get("asset_data", [])
    if not macros:
        return True

    macro_batches = list(chunk_macros(macros, 10))
    total_batches = len(macro_batches)

    for idx, batch in enumerate(macro_batches, start=1):
        print(f"🔹 Filling batch {idx}/{total_batches} with {len(batch)} macros")

        # Shallow copy with only this batch
        temp_record = record.copy()
        temp_record["asset_data"] = batch
        temp_record["number_of_macros"] = str(len(batch))

        # Force submit each batch
        result = await fill_form(
            page,
            temp_record,
            form_steps[1]["field_map"],   # step 2 = asset step
            form_steps[1]["field_types"],
            is_last_step=True,            # click submit
            skip_special_fields=True
        )

        # Check if save failed
        if isinstance(result, dict) and result.get("status") == "FAILED":
            return result

        # Always extract formId from URL after submit
        url = await page.evaluate("window.location.href")
        formId = url.rstrip("/").split("/")[-1]
        print(f"✅ Batch {idx} saved. formId={formId}")

        # If not last batch → reopen asset form
        if idx < total_batches:
            if not formId:
                return {"status": "FAILED", "error": "Could not determine formId after save"}
            next_url = f"https://qima.taqeem.sa/report/asset/create/{formId}"
            print(f"➡️ Navigating to {next_url} for next batch")
            await page.get(next_url)
            await asyncio.sleep(1)

    return True

async def get_first_macro_id(page):
    # Wait for the table body to appear
    tbody = await wait_for_element(page, "tbody", timeout=10)
    if not tbody:
        raise Exception("Could not find table body")

    # Get all 'td' elements inside the tbody
    trs = await tbody.query_selector_all("tr")
    if not trs:
        raise Exception("No <tr> found in table body")
    
    # Take the first tr
    first_tr = trs[0]
    
    # Get all 'td' elements inside the first tr 

    tds = await first_tr.query_selector_all("td")
    if not tds:
        raise Exception("No <td> found in table body")

    # Take the first td
    first_td = tds[0]

    # Get the <a> inside the first td
    link = await first_td.query_selector("a")
    if not link:
        raise Exception("No <a> found inside first td")

    # Extract macro ID from the text of the <a>
    text = link.text
    macro_id = int(text.strip())

    return macro_id



async def fill_macro_form(page, macro_id, macro_data, field_map, field_types):
    edit_url = f"https://qima.taqeem.sa/report/macro/{macro_id}/edit"
    await page.get(edit_url)
    await asyncio.sleep(1)

    result = await fill_form(
        page,
        macro_data,
        field_map,
        field_types,
        is_last_step=True,
        skip_special_fields=True
    )
    return result


async def handle_macro_edits(page, record):
    asset_data = record.get("asset_data", [])
    if not asset_data:
        print("No asset_data to fill")
        return True

    first_macro_id = await get_first_macro_id(page)
    print(f"🔹 Starting from macro_id={first_macro_id}")

    for idx, macro in enumerate(asset_data):
        macro_id = first_macro_id + idx
        print(f"➡️ Filling macro {idx+1}/{len(asset_data)} (id={macro_id})")
        result = await fill_macro_form(page, macro_id, macro,
                                       macro_form_config["field_map"],
                                       macro_form_config["field_types"])
        if isinstance(result, dict) and result.get("status") == "FAILED":
            return result
        print(f"✅ Saved macro {macro_id}")

    return True

async def runFormFill(page, record_id):
    try:
        if not ObjectId.is_valid(record_id):
            return {"status": "FAILED", "error": f"Invalid record_id: {record_id}"}

        record = await db.halfreports.find_one({"_id": ObjectId(record_id)})
        if not record:
            return {"status": "FAILED", "error": f"No record found for recordId={record_id}"}

        results = []
        record["number_of_macros"] = str(len(record.get("asset_data", [])))

        if "clients" in record and record["clients"]:
            await fill_clients(page, record["clients"])
        if "valuers" in record and record["valuers"]:
            await fill_valuers(page, record["valuers"])

        for step_num, step_config in enumerate(form_steps, 1):
            is_last_step = (step_num == len(form_steps))
            results.append({
                "status": "STEP_STARTED",
                "step": step_num,
                "recordId": str(record["_id"])
            })

            # Special handling for step 2 (assets/macros)
            if step_num == 2 and len(record.get("asset_data", [])) > 10:
                result = await handle_macros(page, record)
            else:
                result = await fill_form(
                    page,
                    record,
                    step_config["field_map"],
                    step_config["field_types"],
                    is_last_step,
                    skip_special_fields=True
                )

            if isinstance(result, dict) and result.get("status") == "FAILED":
                results.append({
                    "status": "FAILED",
                    "step": step_num,
                    "recordId": str(record["_id"]),
                    "error": result.get("error")
                })
                return {"status": "FAILED", "results": results}

            if is_last_step:
                results.append({
                    "status": "FORM_FILL_SUCCESS",
                    "message": "Form submitted successfully",
                    "recordId": str(record["_id"])
                })
        if result is not None and not (isinstance(result, dict) and result.get("status") == "FAILED"):
            # ✅ Only run if the 2-step wizard succeeded
            translate = await wait_for_element(page, "a[href='https://qima.taqeem.sa/setlocale/ar']", timeout=30)
            if not translate:
                results.append({
                    "status": "FAILED",
                    "step": "translate",
                    "recordId": str(record["_id"]),
                    "error": "Translate link not found"
                })
                return {"status": "FAILED", "results": results}
            await translate.click()
            await asyncio.sleep(1)

            macro_result = await handle_macro_edits(page, record)
            if isinstance(macro_result, dict) and macro_result.get("status") == "FAILED":
                results.append({
                    "status": "FAILED",
                    "step": "macro_edit",
                    "recordId": str(record["_id"]),
                    "error": macro_result.get("error")
                })
                return {"status": "FAILED", "results": results}

            results.append({
                "status": "MACRO_EDIT_SUCCESS",
                "message": "All macros filled successfully",
                "recordId": str(record["_id"])
            })



    except Exception as e:
        tb = traceback.format_exc()
        return {"status": "FAILED", "error": str(e), "traceback": tb}