import pandas as pd
import asyncio
import json
import os
import time

async def handle_checkbox_group_comprehensive(page, selector, target_value, field_name):
    """Comprehensive checkbox handler for your specific HTML structure"""
    try:
        # Find all checkbox containers
        checkbox_containers = await page.query_selector_all("div.form-check")
        
        for container in checkbox_containers:
            # Get the label within this container
            label = await container.query_selector("label.form-check-label")
            if not label:
                continue
                
            label_text = await label.text_content()
            label_text = label_text.strip() if label_text else ""
            
            # Check if this label matches our target value
            if label_text and target_value.lower() in label_text.lower():
                # Get the checkbox within this container
                checkbox = await container.query_selector("input[type='checkbox']")
                if checkbox:
                    # Determine if we should check or uncheck
                    should_check = target_value.lower() not in ['no', 'false', '0', 'off', 'unchecked']
                    
                    is_checked = await checkbox.is_checked()
                    if should_check != is_checked:
                        await checkbox.click()
                        print(f"{'Checked' if should_check else 'Unchecked'} '{label_text}'")
                    return True
        
        print(f"Checkbox '{target_value}' not found in group {field_name}")
        return False
        
    except Exception as e:
        print(f"Error in comprehensive checkbox handling: {e}")
        return False

async def find_associated_label(page, element):
    """Find label associated with an input element using various methods"""
    try:
        # Method 1: Label with for attribute
        element_id = await element.get_attribute("id")
        if element_id:
            label = await page.query_selector(f"label[for='{element_id}']")
            if label:
                return label
        
        # Method 2: Label that wraps the input (parent label)
        parent_label = await element.query_selector("xpath=./ancestor::label")
        if parent_label:
            return parent_label
        
        # Method 3: Label that is next sibling or previous sibling
        # Look for immediate sibling label
        next_sibling = await element.query_selector("xpath=./following-sibling::label[1]")
        if next_sibling:
            return next_sibling
        
        prev_sibling = await element.query_selector("xpath=./preceding-sibling::label[1]")
        if prev_sibling:
            return prev_sibling
        
        # Method 4: Look for label in the same container/row
        # This is more complex and might need customization based on your HTML structure
        container = await element.query_selector("xpath=./ancestor::div[contains(@class, 'form-group') or contains(@class, 'checkbox') or contains(@class, 'radio')]")
        if container:
            label = await container.query_selector("label")
            if label:
                return label
        
        # Method 5: Look for text near the input that might be a label
        # This is a fallback approach
        parent = await element.query_selector("xpath=./..")
        if parent:
            parent_text = await parent.text_content()
            if parent_text and len(parent_text.strip()) > 0:
                # If parent has text, it might be acting as a label
                return parent
        
        return None
        
    except Exception as e:
        print(f"Error finding associated label: {e}")
        return None

async def select_select2_option_simple(page, selector, value):
    try:
        print(f"Selecting Select2 option: {value}")
        
        element = await page.find(selector)
        print("this the boy", element)
        
        if not element:
            print(f"No Select2 element found for {selector}")
            return False

        # Force open dropdown
        await element.apply("""
        (el) => {
            const evt = new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window });
            el.dispatchEvent(evt);
        }
        """)
        await asyncio.sleep(0.5)


        search_input = await wait_for_element(page, "input.select2-search__field", timeout=5)
        if not search_input:
            print("No search input found")
            return False

        await search_input.focus()
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
        await asyncio.sleep(0.5)
        
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
        # Read Excel file
        df = pd.read_excel(file_path)
        df = df.fillna("")

        records = df.to_dict(orient="records")

        # Build lookup by file name -> absolute path
        pdf_lookup = {os.path.basename(pdf_path): os.path.abspath(pdf_path) for pdf_path in pdf_paths}

        for record in records:
            pdf_name = str(record.get("Report Asset File", "")).strip()
            if pdf_name and pdf_name in pdf_lookup:
                # ✅ Directly use the absolute path from multer
                record["Report Asset File"] = os.path.normpath(pdf_lookup[pdf_name])
            else:
                record["Report Asset File"] = ""

        json_str = json.dumps(records, default=str, ensure_ascii=False)
        json_data = json.loads(json_str)

        # ✅ Cleanup after processing
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
                            parent = await element.parent
                            sibling = await parent.query_selector("div")
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
                                    # Click either the label or the checkbox
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