import asyncio
import time
import traceback
import json
from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from formSteps2 import form_steps, macro_form_config
from addAssets import check_incomplete_macros_after_creation, check_incomplete_macros

MONGO_URI="mongodb+srv://test:JUL3OvyCSLVjSixj@assetval.pu3bqyr.mongodb.net/projectForever"
client = AsyncIOMotorClient(MONGO_URI)
db = client["projectForever"]

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

_location_cache = {}

async def set_location(page, country_name, region_name, city_name):
    try:
        import re, unicodedata

        cache_key = f"{country_name}|{region_name}|{city_name}"

        def normalize_text(text: str) -> str:
            if not text:
                return ""
            text = unicodedata.normalize("NFKC", text)
            text = re.sub(r"\s+", " ", text)
            return text.strip()

        async def wait_for_options(selector, min_options=2, timeout=10):
            for _ in range(timeout * 2):
                el = await wait_for_element(page, selector, timeout=1)
                if el and getattr(el, "children", None) and len(el.children) >= min_options:
                    return el
                await asyncio.sleep(0.5)
            return None

        async def get_location_code(name, selector):
            if not name:
                return None
            el = await wait_for_options(selector)
            if not el:
                return None
            for opt in el.children:
                text = normalize_text(opt.text)
                if normalize_text(name).lower() in text.lower():
                    return opt.attrs.get("value")
            return None

        async def set_field(selector, value):
            if not value:
                return
            args = json.dumps({"selector": selector, "value": value})
            await page.evaluate(f"""
                (function() {{
                    const args = {args};
                    if (window.$) {{
                        window.$(args.selector).val(args.value).trigger("change");
                    }} else {{
                        const el = document.querySelector(args.selector);
                        if (!el) return;
                        if (el.value !== args.value) {{
                            el.value = args.value;
                            el.dispatchEvent(new Event("input", {{ bubbles: true }}));
                            el.dispatchEvent(new Event("change", {{ bubbles: true }}));
                        }}
                    }}
                }})();
            """)

        region_code, city_code = _location_cache.get(cache_key, (None, None))

        if not region_code:
            region_code = await get_location_code(region_name, "#region")
        if not city_code:
            city_code = await get_location_code(city_name, "#city")

        if region_code or city_code:
            _location_cache[cache_key] = (region_code, city_code)

        await set_field("#country_id", "1")
        await asyncio.sleep(0.5)
        await set_field("#region", region_code)
        await asyncio.sleep(0.5)
        await set_field("#city", city_code)
        await asyncio.sleep(0.5)

        print(f"Location set → 1 / {region_code} / {city_code}")
        return True

    except Exception as e:
        print(f"Location injection failed: {e}")
        return False

async def bulk_inject_inputs(page, record, field_map, field_types):
    jsdata = {}

    for key, selector in field_map.items():
        if key not in record:
            continue

        field_type = field_types.get(key, "text")
        value = str(record[key] or "").strip()

        if field_type == "date" and value:
            try:
                value = datetime.strptime(value, "%d-%m-%Y").strftime("%Y-%m-%d")
            except ValueError:
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    print(f"[WARNING] Invalid date format for {key}: {value}")
                    continue

        jsdata[selector] = {"type": field_type, "value": value}

    js = f"""
    (function() {{
        const data = {json.dumps(jsdata)};
        for (const [selector, meta] of Object.entries(data)) {{
            const el = document.querySelector(selector);
            if (!el) continue;

            switch(meta.type) {{
                case "checkbox":
                    el.checked = Boolean(meta.value);
                    el.dispatchEvent(new Event("change", {{ bubbles: true }}));
                    break;

                case "select":
                    let found = false;
                    for (const opt of el.options) {{
                        if (opt.value == meta.value || opt.text == meta.value) {{
                            el.value = opt.value;
                            found = true;
                            break;
                        }}
                    }}
                    if (!found && el.options.length) {{
                        el.selectedIndex = 0;
                    }}
                    el.dispatchEvent(new Event("change", {{ bubbles: true }}));
                    break;

                case "radio":
                    const labels = document.querySelectorAll('label.form-check-label');
                    for (const lbl of labels) {{
                        if ((lbl.innerText || '').trim() === meta.value) {{
                            const radio = document.getElementById(lbl.getAttribute('for'));
                            if (radio) {{
                                radio.checked = true;
                                radio.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                            break;
                        }}
                    }}
                    break;

                case "date":
                case "text":
                default:
                    el.value = meta.value ?? "";
                    el.dispatchEvent(new Event("input", {{ bubbles: true }}));
                    el.dispatchEvent(new Event("change", {{ bubbles: true }}));
                    break;
            }}
        }}
    }})();
    """

    await page.evaluate(js)

async def fill_form(page, record, field_map, field_types, is_last_step=False, retries=0, max_retries=2, skip_special_fields=False, control_state=None):
    try:
        # Import here to access shared state
        from worker_equip import check_control
        if control_state:
            await check_control(control_state)
        
        start_time = time.time()
        await bulk_inject_inputs(page, record, field_map, field_types)

        for key, selector in field_map.items():
            if key not in record: continue
            value = str(record[key] or "")
            ftype = field_types.get(key,"text")
            try:
                if ftype == "location":
                    country_name = record.get("country","")
                    region_name = record.get("region","")
                    city_name = record.get("city","")
                    await set_location(page, country_name, region_name, city_name)

                elif ftype == "file":
                    file_input = await wait_for_element(page, selector, timeout=10)
                    if file_input: await file_input.send_file(value)
                    
                elif ftype == "dynamic_select":
                    select_element = await wait_for_element(page, selector, timeout=10)
                    if select_element:
                        for opt in select_element.children:
                            if value.lower() in (opt.text or "").lower():
                                await opt.select_option()
                                break

            except Exception:
                continue
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"[FORM] filled in {elapsed_time:.2f} seconds")

        if not is_last_step:
            continue_btn = await wait_for_element(page, "input[name='continue']", timeout=10)
            if continue_btn:
                await continue_btn.click()
                await asyncio.sleep(2)
                error_div = await wait_for_element(page, "div.alert.alert-danger", timeout=5)
                if error_div and retries < max_retries:
                    await asyncio.sleep(1)
                    return await fill_form(page, record, field_map, field_types, is_last_step, retries+1, max_retries, skip_special_fields, control_state)
        else:
            save_btn = await wait_for_element(page, "input[type='submit']", timeout=10)
            if save_btn:
                await asyncio.sleep(0.5)
                await save_btn.click()
                await asyncio.sleep(2)
                return {"status":"SAVED"}
            else:
                return {"status":"FAILED","error":"Save button not found"}
        return True
    except Exception as e:
        return {"status":"FAILED","error": str(e)}

def chunk_macros(macros, chunk_size=10):
    for i in range(0, len(macros), chunk_size):
        yield macros[i:i+chunk_size]

def calculate_tab_batches(total_assets: int, max_tabs: int, batch_size: int = 10):
    if total_assets <= batch_size:
        return [total_assets] 
    
    required_tabs = (total_assets + batch_size - 1) // batch_size
    tabs_to_use = min(required_tabs, max_tabs)

    base, extra = divmod(total_assets, tabs_to_use)
    result = []
    for i in range(tabs_to_use):
        size = base + (1 if i < extra else 0)
        result.append(size)
    return result

async def handle_macros_multi(browser, record, tab_nums=3, batch_size=10, control_state=None):
    from worker_equip import check_control
    
    macros = record.get("asset_data", [])
    total_assets = len(macros)
    if not total_assets:
        return True

    if control_state:
        await check_control(control_state)

    distribution = calculate_tab_batches(total_assets, tab_nums, batch_size)
    print(f"[MACRO DISTRIBUTION] total={total_assets}, tabs={len(distribution)}, split={distribution}")

    main_page = browser.tabs[0]  
    current_url = await main_page.evaluate("window.location.href")

    pages = [main_page]
    for _ in range(len(distribution) - 1):
        new_tab = await browser.get(current_url, new_tab=True)
        pages.append(new_tab)

    for page in pages:
        for _ in range(20):  
            ready_state = await page.evaluate("document.readyState")
            key_el = await wait_for_element(page, "#macros", timeout=0.5)
            if ready_state == "complete" and key_el:
                break
            await asyncio.sleep(0.5)

    async def process_assets(page, start_index, count):
        end_index = start_index + count
        subset = macros[start_index:end_index]
        for i in range(0, len(subset), batch_size):
            if control_state:
                await check_control(control_state)
            
            chunk = subset[i:i+batch_size]
            temp_record = record.copy()
            temp_record["asset_data"] = chunk
            temp_record["number_of_macros"] = str(len(chunk))
            
            result = await fill_form(
                page,
                temp_record,
                form_steps[1]["field_map"],
                form_steps[1]["field_types"],
                is_last_step=True,
                skip_special_fields=True,
                control_state=control_state
            )

            if isinstance(result, dict):
                if result.get("status") == "FAILED":
                    print(f"[ERROR] Tab failed for batch {start_index+i}–{start_index+i+len(chunk)}: {result}")
                    return result
                elif result.get("status") == "SAVED":
                    print(f"[SUCCESS] Save button clicked for batch {start_index+i}–{start_index+i+len(chunk)}")

            if i + batch_size < len(subset):
                await page.get(current_url)
                await asyncio.sleep(1)

        return True

    tasks = []
    idx = 0
    for page, count in zip(pages, distribution):
        tasks.append(process_assets(page, idx, count))
        idx += count

    await asyncio.gather(*tasks)

    await asyncio.sleep(2)
    for p in pages[1:]:
        await p.close()

    return True

def merge_asset_with_parent(asset, parent):
    inherit_fields = ["inspection_date", "owner_name", "country", "region", "city"]
    merged = asset.copy()
    for f in inherit_fields:
        if f not in merged or not merged[f]:
            merged[f] = parent.get(f)
    return merged

async def get_first_macro_id(page):
    tbody = await wait_for_element(page, "tbody", timeout=10)
    trs = await tbody.query_selector_all("tr") if tbody else []
    first_tr = trs[0] if trs else None
    tds = await first_tr.query_selector_all("td") if first_tr else []
    link = await tds[0].query_selector("a") if tds else None
    return int(link.text.strip()) if link else None

async def fill_macro_form(page, macro_id, macro_data, field_map, field_types, control_state=None):
    await page.get(f"https://qima.taqeem.sa/report/macro/{macro_id}/edit")
    await asyncio.sleep(0.5)
    try:
        result = await fill_form(page, macro_data, field_map, field_types, is_last_step=True, skip_special_fields=True, control_state=control_state)
        return result
    except Exception as e:
        print(f"Filling macro {macro_id} failed: {e}")
        return {"status": "FAILED", "error": str(e)}

async def handle_macro_edits(browser, record, tabs_num=3, control_state=None):
    from worker_equip import check_control
    
    asset_data = record.get("asset_data", [])
    if not asset_data: return True

    if control_state:
        await check_control(control_state)

    main_page = browser.tabs[0]
    first_macro_id = await get_first_macro_id(main_page)
    if first_macro_id is None:
        return {"status":"FAILED","error":"Could not determine first macro id"}

    chunks = balanced_chunks(asset_data, tabs_num)
    pages = [main_page] + [await browser.get("", new_tab=True) for _ in range(tabs_num - 1)]

    async def process_chunk(chunk, page, offset):
        for idx, macro in enumerate(chunk):
            if control_state:
                await check_control(control_state)
            
            macro_id = first_macro_id + idx + offset
            element_index = offset + idx

            try:
                res = await db.halfreports.update_one(
                    {"_id": record["_id"]},
                    {"$set": {f"asset_data.{element_index}.id": int(macro_id)}}
                )
                print(f"[DB PATCH] index {element_index} -> macro_id {macro_id}")
            except Exception as e:
                print(f"[DB PATCH ERROR] {e}")
            
            try:
                macro = merge_asset_with_parent(macro, record)
                await fill_macro_form(
                    page,
                    macro_id,
                    macro,
                    macro_form_config["field_map"],
                    macro_form_config["field_types"],
                    control_state
                )
            except Exception as e:
                print(f"Filling macro {macro_id} failed: {e}")

    tasks = [process_chunk(chunk, page, sum(len(c) for c in chunks[:i])) for i, (page, chunk) in enumerate(zip(pages, chunks))]
    await asyncio.gather(*tasks)
    return True

def balanced_chunks(lst, n):
    k, m = divmod(len(lst), n)
    chunks = []
    start = 0
    for i in range(n):
        size = k + (1 if i < m else 0)
        chunks.append(lst[start:start+size])
        start += size
    return chunks

async def runFormFill2(browser, record_id, tabs_num=3, control_state=None):
    from worker_equip import check_control
    
    try:
        if not ObjectId.is_valid(record_id):
            return {"status":"FAILED","error":"Invalid record_id"}
        
        record = await db.halfreports.find_one({"_id": ObjectId(record_id)})
        if not record: 
            return {"status":"FAILED","error":"Record not found"}

        results=[]
        record["number_of_macros"] = str(len(record.get("asset_data",[])))

        main_page = await browser.get("https://qima.taqeem.sa/report/create/4/487")
        await asyncio.sleep(1)

        for step_num, step_config in enumerate(form_steps, 1):
            if control_state:
                await check_control(control_state)
            
            is_last = step_num == len(form_steps)
            results.append({"status":"STEP_STARTED","step":step_num,"recordId":str(record["_id"])})

            if step_num == 2 and len(record.get("asset_data", [])) > 10:
                result = await handle_macros_multi(browser, record, tab_nums=tabs_num, batch_size=10, control_state=control_state)
            else:
                result = await fill_form(
                    main_page, 
                    record, 
                    step_config["field_map"], 
                    step_config["field_types"], 
                    is_last, 
                    skip_special_fields=True,
                    control_state=control_state
                )

            if isinstance(result, dict) and result.get("status")=="FAILED":
                results.append({
                    "status":"FAILED",
                    "step":step_num,
                    "recordId":str(record["_id"]),
                    "error":result.get("error")
                })
                return {"status":"FAILED","results":results}

            if is_last:
                main_url = await main_page.evaluate("window.location.href")
                form_id = main_url.split("/")[-1]
                if not form_id:
                    results.append({"status":"FAILED","step":"report_id","recordId":str(record["_id"]),"error":"Could not determine report_id"})
                    return {"status":"FAILED","results":results}

                res = await db.halfreports.update_one(
                    {"_id": record["_id"]}, 
                    {"$set": {"report_id": form_id}}
                )
                print(f"[DB PATCH] report_id set: {form_id}")

                macro_result = await handle_macro_edits(browser, record, tabs_num=tabs_num, control_state=control_state)
                if isinstance(macro_result, dict) and macro_result.get("status")=="FAILED":
                    results.append({"status":"FAILED","step":"macro_edit","recordId":str(record["_id"]),"error":macro_result.get("error")})
                    return {"status":"FAILED","results":results}

                results.append({"status":"MACRO_EDIT_SUCCESS","message":"All macros filled","recordId":str(record["_id"])})

                pages = browser.tabs
                for p in pages[1:]:
                    await p.close()

                checker_result = await check_incomplete_macros_after_creation(browser, record_id, browsers_num=tabs_num)
                results.append({"status":"CHECKER_RESULT", "recordId":str(record["_id"]), "result":checker_result})

                if checker_result["macro_count"] > 0:
                    await retryMacros(browser, record_id, tabs_num=tabs_num, control_state=control_state)

        return {"status":"SUCCESS","results":results}

    except Exception as e:
        tb = traceback.format_exc() 
        return {"status":"FAILED","error":str(e),"traceback":tb}

async def retryMacros(browser, record_id, tabs_num=3, control_state=None):
    from worker_equip import check_control
    
    try:
        if control_state:
            await check_control(control_state)
        
        report = await db.halfreports.find_one({"_id": ObjectId(record_id)})
        if not report:
            return {"status": "FAILED", "error": "Report not found"}

        assets = report.get("asset_data", [])
        retry_assets = [(idx, a) for idx, a in enumerate(assets) if a.get("submitState") == 0]
        if not retry_assets:
            return {"status": "SUCCESS", "message": "All macros complete"}

        print(f"[RETRY] Retrying {len(retry_assets)} incomplete macros")

        # FIXED: Include main tab in pages list, then create additional tabs as needed
        num_tabs = min(tabs_num, len(retry_assets))
        pages = [browser.tabs[0]]  # Start with main tab
        
        # Only create additional tabs if we need more than 1
        if num_tabs > 1:
            pages.extend([await browser.get("about:blank", new_tab=True) for _ in range(num_tabs - 1)])
        
        print(f"[RETRY] Using {len(pages)} tabs for {len(retry_assets)} assets")
        
        # Distribute assets across tabs
        chunks = [retry_assets[i::len(pages)] for i in range(len(pages))]

        async def process_chunk(page, assets_chunk):
            for idx, asset in assets_chunk:
                if control_state:
                    await check_control(control_state)
                
                macro_id = asset.get("id")
                if not macro_id:
                    print(f"[RETRY] Skipping asset at index {idx} - no macro_id")
                    continue

                try:
                    merged_asset = merge_asset_with_parent(asset, report)
                    await fill_macro_form(
                        page, 
                        macro_id, 
                        merged_asset, 
                        macro_form_config["field_map"], 
                        macro_form_config["field_types"], 
                        control_state
                    )

                    show_url = f"https://qima.taqeem.sa/report/macro/{macro_id}/show"
                    await page.get(show_url)
                    await asyncio.sleep(0.5)
                    html_content = await page.get_content()

                    submit_state = 0 if (html_content and "غير مكتملة" in html_content) else 1
                    await db.halfreports.update_one(
                        {"_id": report["_id"]}, 
                        {"$set": {f"asset_data.{idx}.submitState": submit_state}}
                    )

                    print(f"[RETRY {'SUCCESS' if submit_state == 1 else 'INCOMPLETE'}] macro_id={macro_id}, index={idx}")
                except Exception as e:
                    print(f"[RETRY ERROR] macro_id={macro_id}, index={idx}: {e}")

        # Process all chunks in parallel
        await asyncio.gather(*[process_chunk(p, chunk) for p, chunk in zip(pages, chunks)])

        # Close only the additional tabs (not the main one)
        for p in pages[1:]:
            await p.close()

        print(f"[RETRY] Closed {len(pages) - 1} additional tabs")

        return {"status": "SUCCESS", "message": f"Retried {len(retry_assets)} macros"}

    except Exception as e:
        tb = traceback.format_exc()
        return {"status": "FAILED", "error": str(e), "traceback": tb}

async def runCheckMacros(browser, record_id, tabs_num=3):
    try:
        if not ObjectId.is_valid(record_id): 
            return {"status": "FAILED", "error": "Invalid record_id"}
    
        check_result = await check_incomplete_macros(browser, record_id)
        return {
            "status": "SUCCESS",
            "recordId": str(record_id),
            "result": check_result
        }

    except Exception as e:
        tb = traceback.format_exc()
        return {
            "status": "FAILED",
            "error": str(e),
            "traceback": tb
        }