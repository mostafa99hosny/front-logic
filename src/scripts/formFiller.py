import pandas as pd
import asyncio
import json
import os
import time

async def select_select2_option_simple(page, selector, value):
    try:
        print(f"Selecting Select2 option: {value}")
        
        select2_container = await wait_for_element(page, selector, timeout=10)
        
        if not select2_container:
            print(f"No Select2 container found for {selector}")
            return False
        
        await select2_container.click()
        await asyncio.sleep(3)
        
        search_input = await wait_for_element(
            page, "input[type='search']", timeout=5
        )
        
        if not search_input:
            print("No search input found in Select2 dropdown")
            return False
                
        await search_input.click()
        await search_input.send_keys(value)                 
        await asyncio.sleep(1)  
        
        await search_input.send_keys("\n")
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
    APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        df = pd.read_excel(file_path)
        df = df.fillna("")

        records = df.to_dict(orient="records")

        pdf_lookup = {os.path.basename(pdf_path): pdf_path for pdf_path in pdf_paths}

        for record in records:
            pdf_name = str(record.get("Report Asset File", "")).strip()
            if pdf_name and pdf_name in pdf_lookup:
                raw_path = os.path.join(APP_ROOT, pdf_lookup[pdf_name])
                record["Report Asset File"] = os.path.normpath(raw_path)
            else:
                record["Report Asset File"] = ""

        json_str = json.dumps(records, default=str, ensure_ascii=False)
        json_data = json.loads(json_str)

        # ✅ delete files after extraction
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            for pdf_path in pdf_paths:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
        except Exception as del_err:
            # Don’t fail the whole thing just because cleanup failed
            return {"status": "SUCCESS", "data": json_data, "warning": f"Cleanup error: {del_err}"}

        return {"status": "SUCCESS", "data": json_data}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}
    
async def handle_location_dropdown(page, selector, value):
    try:
        trigger = await wait_for_element(page, selector, timeout=10)
        if not trigger:
            print(f"Trigger not found: {selector}")
            return False

        # Ensure it’s on screen then do a real mouse click
        await page.evaluate("(el) => el.scrollIntoView({block:'center'})", trigger)
        # nodriver: prefer mouse_click for real user-like event
        try:
            await trigger.mouse_click()
        except Exception:
            await trigger.click()

        # Wait for Select2 to actually open
        open_container = await wait_for_element(
            page, ".select2-container--open", timeout=5
        )
        if not open_container:
            print("Select2 did not open; trying programmatic open")
            # Fallback: programmatic open via jQuery/Select2 API
            try:
                await page.evaluate("""() => {
                    const el = document.querySelector("select[name='region_id']") || 
                               document.querySelector("select[name='country_id']") || 
                               document.querySelector("select#city") ||
                               null;
                    if (el && window.jQuery) jQuery(el).select2('open');
                }""")
                open_container = await wait_for_element(page, ".select2-container--open", timeout=3)
            except Exception:
                pass

        # Prefer the input inside the OPEN container to avoid grabbing the wrong one
        search_input = await wait_for_element(
            page, ".select2-container--open input.select2-search__field", timeout=5
        )

        if search_input:
            await search_input.click()
            # ensure focus in some UIs where focus is lost immediately
            await page.evaluate("(el) => el.focus()", search_input)  # focus fix
            await search_input.send_keys(value)
            await asyncio.sleep(0.3)
            await search_input.send_keys("\n")  # select highlighted
            await asyncio.sleep(0.5)
            return True

    except Exception as e:
        print(f"Location dropdown failed: {e}")
        return False


async def fill_form(page, record, field_map, field_types):
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
                    await element.send_keys(value)

            elif field_type == "location":
                success = await handle_location_dropdown(page, selector, value)
                if not success:
                    print(f"Failed to select location '{value}'")

            elif field_type == "select":
                select_element = await wait_for_element(page, selector, timeout=10)
                if not select_element:
                    print(f"Warning: No select element found for selector {selector}")
                    continue

                select2_container = await select_element.query_selector("xpath=following-sibling::span[contains(@class, 'select2')]")
                
                if select2_container:
                    success = await select_select2_option_simple(page, selector, value)
                    if not success:
                        print(f"Failed to select '{value}' in Select2 dropdown")
                else:
                    # Regular select handling for non-Select2 dropdowns
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
                                break
                    
                    if not option_found:
                        print(f"Warning: Could not find option with text '{value}'")

            elif field_type == "radio":
                escaped_value = value.replace("'", "\\'").replace('"', '\\"')
                radio_selector = f"{selector}[value='{escaped_value}']"
                element = await wait_for_element(page, radio_selector, timeout=10)
                if element:
                    await element.click()
                else:
                    print(f"Warning: No radio button found for value '{value}' with selector {selector}")

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
                checkbox_element = await wait_for_element(page, selector, timeout=10)
                if checkbox_element:
                    # For checkboxes, check if value indicates it should be checked
                    if value.lower() in ['yes', 'true', '1', 'on', 'checked']:
                        if not await checkbox_element.is_checked():
                            await checkbox_element.click()
                    else:
                        if await checkbox_element.is_checked():
                            await checkbox_element.click()
                else:
                    print(f"Warning: No checkbox found for selector {selector}")

        except Exception as e:
            print(f"Error filling {key}: {e}")
            continue

    try:
        continue_btn = await wait_for_element(page, "input[name='continue']", timeout=10)
        
        if continue_btn:
            print("Clicking continue button...")
            await continue_btn.click()

            await wait_for_element(page, "input", timeout=10)
                        
            return True  
        else:
            print("No continue button found - may be on final step")
            return False 
            
    except Exception as e:
        print(f"Error clicking continue button: {e}")
        return False