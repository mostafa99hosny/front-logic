import pandas as pd
import asyncio
import json
import os
import time
import traceback

from formSteps import form_steps
from browser import get_page          


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

async def extractData(file_path, pdf_paths):
    try:
        df = pd.read_excel(file_path)
        df = df.fillna("")

        records = df.to_dict(orient="records")

        pdf_lookup = {os.path.basename(pdf_path): os.path.abspath(pdf_path) for pdf_path in pdf_paths}

        for record in records:
            pdf_name = str(record.get("Report Asset File", "")).strip()

            if pdf_name and pdf_name in pdf_lookup:
                record["Report Asset File"] = os.path.normpath(pdf_lookup[pdf_name])
            else:
                record["Report Asset File"] = ""

        json_str = json.dumps(records, default=str, ensure_ascii=False)
        json_data = json.loads(json_str)

        try:
            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception as del_err:
            return {
                "status": "SUCCESS",
                "data": json_data,
                "warning": f"Cleanup error: {del_err}"
            }

        return {"status": "SUCCESS", "data": json_data}

    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

async def fill_form(page, record, field_map, field_types, is_last_step=False):
    for key, selector in field_map.items():
        if key not in record:
            continue

        value = str(record[key] or "")
        field_type = field_types.get(key, "text")

        try:
            if field_type == "text":
                element = await wait_for_element(page, selector, timeout=10)
                if element:
                    if "readonly" in element.attrs:
                        print("element readonly", element)
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
                        option_text = option.text or ""
                        option_text = option_text.strip()
                        if value.lower() in option_text.lower():
                            await option.select_option()
                            option_found = True
                            print(f"Warning: Could not find option with text '{value}'")
                            break
                    
                       

            elif field_type == "radio":
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        for element in elements:
                            sibling = await element.apply("(el) => el.nextElementSibling")
                            if sibling:
                                labelText = sibling.text
                                if labelText and value.lower() in labelText.lower():
                                    await element.click()
                                    option_found = True
                                    print(f"Selected radio by label text: {value}")
                                    break
                            else:
                                print(f"No sibling found for radio {element}")
                    else:
                        print(f"No radio elements found for selector {selector}")

                            
                except Exception as e:
                    print(f"Error selecting radio button '{value}': {e}")

            elif field_type == "file":
                file_input = await wait_for_element(page, selector, timeout=10)
                print("file_input", file_input)

                if file_input:
                    print("sending file", value)
                    
                    try:
                        await file_input.send_file(value)
                        print("File set using send_files")

                    except Exception as e:
                        print(f"send_files failed: {e}")
                        
                else:
                    print(f"Warning: No file input found for selector {selector}")

            elif field_type == "checkbox":
                checkList = await page.query_selector_all(selector)
                if checkList:
                    for check in checkList:
                        parent = check.parent
                        if parent:
                            label = await parent.query_selector("label")
                            if label:
                                label_text = label.text
                                if label_text and value.lower() in label_text.lower():
                                    await check.click()
                                    option_found = True
                                    print(f"Selected checkbox by label text: {value}")
                                    break
                            else:
                                print(f"No label found for checkbox {check}")
                        else:
                            print(f"No parent found for checkbox {check}")

        except Exception as e:
            print(f"Error filling {key}: {e}")
            continue

    try:

        if not is_last_step:
            continue_btn = await wait_for_element(page, "input[name='continue']", timeout=10)
            
            if continue_btn:
                print("Clicking continue button...")
                await asyncio.sleep(0.5)
                await continue_btn.click()

                await asyncio.sleep(5)
                await wait_for_element(page, "input", timeout=10)
                            
                return True  
            else:
                print("No continue button found - may be on final step")
                return False
        else:
            print("Last step completed - not clicking continue button")
            return False
            
    except Exception as e:
        print(f"Error clicking continue button: {e}")
        return False
    

async def runFormFill(page, file_path, pdf_paths):
    try:
        # 1. Extract records
        result = await extractData(file_path, pdf_paths)
        if result["status"] != "SUCCESS":
            return result

        records = result["data"]

        print(json.dumps({"status": "EXTRACTED_DATA", "data": records}), flush=True)

        for record in records:
            for step_num, step_config in enumerate(form_steps, 1):
                is_last_step = (step_num == len(form_steps))
                print(f"Processing step {step_num}...", flush=True)

                await fill_form(
                    page,
                    record,
                    step_config["field_map"],
                    step_config["field_types"],
                    is_last_step
                )

                if is_last_step:
                    print(json.dumps({
                        "status": "FORM_FILL_SUCCESS",
                        "message": "Form submitted successfully",
                        "recoverable": True
                    }), flush=True)
                    break

        return {"status": "SUCCESS"}

    except Exception as e:
        tb = traceback.format_exc()
        return {"status": "FAILED", "error": str(e), "traceback": tb}