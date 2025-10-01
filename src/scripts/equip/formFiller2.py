import asyncio
import time
import traceback
import json
import time
from datetime import datetime
import unicodedata, re

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from formSteps2 import form_steps, macro_form_config
from addAssets import check_incomplete_macros_after_creation

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

import json
import asyncio

import asyncio

import asyncio
import json

import asyncio
import json

_location_cache = {}

async def set_location(page, country_name, region_name, city_name):
    try:
        cache_key = f"{country_name}|{region_name}|{city_name}"

        def normalize_text(text: str) -> str:
            if not text:
                return ""
            text = unicodedata.normalize("NFKC", text)
            text = re.sub(r"\s+", " ", text)  
            return text.strip()

        async def get_location_code(name, selector):
            if not name:
                return None
            el = await wait_for_element(page, selector, timeout=5)
            if not el:
                return None
            for opt in el.children:
                text = normalize_text(opt.text)
                if normalize_text(name).lower() in text.lower():
                    return opt.attrs.get("value")
            return None

        async def set_field(selector, value):
            args = json.dumps({"selector": selector, "value": value})
            await page.evaluate(f"""
                (function() {{
                    const args = {args};
                    if (window.$) {{
                        // Use Select2/jQuery API if available
                        window.$(args.selector).val(args.value).trigger("change");
                    }} else {{
                        // fallback to native
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

        # Cache lookup
        if cache_key in _location_cache:
            region_code, city_code = _location_cache[cache_key]
        else:
            region_code = await get_location_code(region_name, "#region")
            city_code = await get_location_code(city_name, "#city")
            _location_cache[cache_key] = (region_code, city_code)

        # Apply values using Select2 API
        await set_field("#country_id", "1")
        await asyncio.sleep(1)  
        await set_field("#region", region_code)
        await asyncio.sleep(1) 
        await set_field("#city", city_code)
        await asyncio.sleep(1)

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

        # Normalize date to YYYY-MM-DD
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

    # JS injection function
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
                        el.selectedIndex = 0; // fallback
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


# async def fill_clients(page, clients):
#     if not clients:
#         return
#     client = clients[0]
#     selectors = {
#         "[name='client[0][name]']": client.get("client_name", ""),
#         "[name='client[0][telephone]']": client.get("telephone_number", ""),
#         "[name='client[0][email]']": client.get("email_address", ""),
#     }
#     for sel, val in selectors.items():
#         el = await wait_for_element(page, sel, timeout=5)
#         if el:
#             await el.clear_input()
#             await asyncio.sleep(0.05)
#             await el.send_keys(val)

# async def fill_valuers(page, valuers):
#     if len(valuers) > 1:
#         for _ in range(len(valuers)-1):
#             add_btn = await wait_for_element(page, "#duplicateValuer", timeout=5)
#             if add_btn:
#                 await add_btn.click()
#                 await asyncio.sleep(0.5)
#     for idx, valuer in enumerate(valuers):
#         name_sel = f"[name='valuer[{idx}][id]']"
#         contrib_sel = f"[name='valuer[{idx}][contribution]']"
#         for sel, val in [(name_sel, valuer.get("valuer_name","")), (contrib_sel, str(valuer.get("contribution_percentage","")))]:
#             select_element = await wait_for_element(page, sel, timeout=10)
#             if not select_element:
#                 continue
#             options = select_element.children
#             for opt in options:
#                 text = (opt.text or "").strip()
#                 if val.lower() in text.lower():
#                     await opt.select_option()
#                     break

# async def fill_report_users(page, users):
#     if not users:
#         return
#     if len(users) > 1:
#         for _ in range(len(users)-1):
#             add_btn = await wait_for_element(page, "#duplicateUser", timeout=5)
#             if add_btn:
#                 await add_btn.click()
#                 await asyncio.sleep(0.5)
#     for idx, name in enumerate(users):
#         sel = f"[name='user[{idx}][name]']"
#         el = await wait_for_element(page, sel, timeout=5)
#         if el:
#             await el.clear_input()
#             await asyncio.sleep(0.05)
#             await el.send_keys(name)

async def fill_form(page, record, field_map, field_types, is_last_step=False, retries=0, max_retries=2, skip_special_fields=False):
    try:
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
                    return await fill_form(page, record, field_map, field_types, is_last_step, retries+1, max_retries)
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
    """
    Given the total number of assets, the maximum number of tabs allowed,
    and the batch size (10 by default), return a list where each element
    represents the number of assets assigned to that tab.

    Example:
      total_assets=25, max_tabs=5
      -> [10, 10, 5]
    """
    if total_assets <= batch_size:
        return [total_assets]  # only one tab needed
    
    # calculate how many tabs are theoretically required
    required_tabs = (total_assets + batch_size - 1) // batch_size  # ceil division
    tabs_to_use = min(required_tabs, max_tabs)

    # Distribute assets across tabs
    # Each tab ideally gets close to total_assets / tabs_to_use
    base, extra = divmod(total_assets, tabs_to_use)
    result = []
    for i in range(tabs_to_use):
        size = base + (1 if i < extra else 0)
        result.append(size)
    return result


async def handle_macros_multi(browser, record, tab_nums=3, batch_size=10):
    macros = record.get("asset_data", [])
    total_assets = len(macros)
    if not total_assets:
        return True

    distribution = calculate_tab_batches(total_assets, tab_nums, batch_size)
    print(f"[MACRO DISTRIBUTION] total={total_assets}, tabs={len(distribution)}, split={distribution}")

    main_page = browser.tabs[0]  
    current_url = await main_page.evaluate("window.location.href")

    pages = [main_page]
    for _ in range(len(distribution) - 1):
        new_tab = await browser.get(current_url, new_tab=True)
        pages.append(new_tab)

        # Wait until the new tab is fully loaded
        for _ in range(20):  # max wait 10s (20*0.5)
            ready_state = await new_tab.evaluate("document.readyState")
            key_el = await wait_for_element(new_tab, "#macros", timeout=0.5)
            if ready_state == "complete" and key_el:
                break
            await asyncio.sleep(0.5)

    async def process_assets(page, start_index, count):
        end_index = start_index + count
        subset = macros[start_index:end_index]
        for i in range(0, len(subset), batch_size):
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
                skip_special_fields=True
            )

            if isinstance(result, dict):
                if result.get("status") == "FAILED":
                    print(f"[ERROR] Tab failed for batch {start_index+i}–{start_index+i+len(chunk)}: {result}")
                    return result
                elif result.get("status") == "SAVED":
                    print(f"[SUCCESS] Save button clicked successfully for batch {start_index+i}–{start_index+i+len(chunk)}")
            else:
                print(f"[INFO] fill_form completed for batch {start_index+i}–{start_index+i+len(chunk)}, unknown save status")

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



async def handle_macros(page, record):
    macros = record.get("asset_data", [])
    if not macros: return True
    batches = list(chunk_macros(macros, 10))
    for idx, batch in enumerate(batches, start=1):
        temp_record = record.copy()
        temp_record["asset_data"] = batch
        temp_record["number_of_macros"] = str(len(batch))
        result = await fill_form(
            page,
            temp_record,
            form_steps[1]["field_map"],
            form_steps[1]["field_types"],
            is_last_step=True,
            skip_special_fields=True
        )
        if isinstance(result, dict) and result.get("status")=="FAILED":
            return result
       
        if idx < len(batches):
            formId = (await page.evaluate("window.location.href")).rstrip("/").split("/")[-1]
            next_url = f"https://qima.taqeem.sa/report/asset/create/{formId}"
            await page.get(next_url)
            await asyncio.sleep(1)
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

async def fill_macro_form(page, macro_id, macro_data, field_map, field_types):
    await page.get(f"https://qima.taqeem.sa/report/macro/{macro_id}/edit")
    await asyncio.sleep(0.5)
    try:
        result = await fill_form(page, macro_data, field_map, field_types, is_last_step=True, skip_special_fields=True)
        return result
    except Exception as e:
        print(f"Filling macro {macro_id} failed: {e}")
        return {"status": "FAILED", "error": str(e)}
    
async def fill_assets_via_macro_urls(browser, record, macro_urls, tabs_num=3):
    asset_data = record.get("asset_data", [])
    if not asset_data or not macro_urls:
        return {"status": "FAILED", "error": "No assets or macro URLs provided"}

    main_page = await browser.get(macro_urls[0])
    pages = [main_page] + [await browser.get("about:blank", new_tab=True) for _ in range(min(tabs_num-1, len(macro_urls)-1))]
    
    chunks = balanced_chunks(macro_urls, len(pages))

    async def process_chunk(chunk, page, offset):
        for idx, url in enumerate(chunk):
            if asset_data[offset + idx].get("submitState") == 1:
                continue
            
            element_index = offset + idx
            try:
                await page.get(url)
                await asyncio.sleep(0.5)  

                macro_id = int(url.rstrip("/").split("/")[-2])
                print("macro_id", macro_id)

                asset_id = asset_data[element_index]["_id"]
                
                await db.assetdatas.update_one(
                    {"_id": asset_id},
                    {"$set": {"id": macro_id}},
                )

                await fill_macro_form(
                    page,
                    macro_id,
                    asset_data[element_index],
                    macro_form_config["field_map"],
                    macro_form_config["field_types"]
                )
                print(f"[FILLED] asset index {element_index} -> macro_id {macro_id}")

            except Exception as e:
                print(f"[ERROR] Filling macro {url} failed: {e}")

    tasks = [process_chunk(chunk, page, sum(len(c) for c in chunks[:i])) for i, (page, chunk) in enumerate(zip(pages, chunks))]
    await asyncio.gather(*tasks)

    for p in pages[1:]:
        await p.close()

    return {"status": "SUCCESS", "message": f"Filled {len(asset_data)} macros using provided URLs"}

async def handle_macro_edits(browser, record, tabs_num=3):
    asset_data = record.get("asset_data", [])
    if not asset_data: return True


    main_page = browser.tabs[0]
    first_macro_id = await get_first_macro_id(main_page)
    if first_macro_id is None:
        return {"status":"FAILED","error":"Could not determine first macro id"}

    chunks = balanced_chunks(asset_data, tabs_num)
    pages = [main_page] + [await browser.get("", new_tab=True) for _ in range(tabs_num - 1)]

    async def process_chunk(chunk, page, offset):
        for idx, macro in enumerate(chunk):
            macro_id = first_macro_id + idx + offset
            element_index = offset + idx

            try:
                res = await db.halfreports.update_one(
                    {"_id": record["_id"]},
                    {"$set": {f"asset_data.{element_index}.id": int(macro_id)}}
                )
                print(f"[DB PATCH] index {element_index} -> macro_id {macro_id} (matched={res.matched_count}, modified={res.modified_count})")
                if res.modified_count == 0:
                    doc = await db.halfreports.find_one({"_id": record["_id"]})
                    ad = doc.get("asset_data", [])
                    print(f"[DB PATCH WARNING] no modification. asset_data length={len(ad)}. element at index:",
                        ad[element_index] if element_index < len(ad) else "INDEX OUT OF RANGE")
            except Exception as e:
                print(f"[DB PATCH ERROR] {e}")
            try:
                macro = merge_asset_with_parent(macro, record)
                await fill_macro_form(
                    page,
                    macro_id,
                    macro,
                    macro_form_config["field_map"],
                    macro_form_config["field_types"]
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


async def runFormFill2(browser, record_id, tabs_num=3):
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
            is_last = step_num == len(form_steps)
            results.append({"status":"STEP_STARTED","step":step_num,"recordId":str(record["_id"])})

            if step_num == 2 and len(record.get("asset_data", [])) > 10:
                result = await handle_macros_multi(browser, record, tab_nums=tabs_num, batch_size=10)
            else:
                result = await fill_form(
                    main_page, 
                    record, 
                    step_config["field_map"], 
                    step_config["field_types"], 
                    is_last, 
                    skip_special_fields=True
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
                if res.modified_count == 0:
                    results.append({"status":"FAILED","step":"report_id","recordId":str(record["_id"]),"error":"Could not set report_id"})
                    return {"status":"FAILED","results":results}
                print(f"[DB PATCH] report_id set: {form_id}")

                macro_result = await handle_macro_edits(browser, record, tabs_num=tabs_num)
                if isinstance(macro_result, dict) and macro_result.get("status")=="FAILED":
                    results.append({"status":"FAILED","step":"macro_edit","recordId":str(record["_id"]),"error":macro_result.get("error")})
                    return {"status":"FAILED","results":results}

                results.append({"status":"MACRO_EDIT_SUCCESS","message":"All macros filled","recordId":str(record["_id"])})

                pages = browser.tabs
                for p in pages[1:]:
                    await p.close()

                checker_result = await check_incomplete_macros_after_creation(browser, record_id, browsers_num=tabs_num)
                results.append({"status":"CHECKER_RESULT", "recordId":str(record["_id"]), "result":checker_result})

        return {"status":"SUCCESS","results":results}

    except Exception as e:
        tb = traceback.format_exc() 
        return {"status":"FAILED","error":str(e),"traceback":tb}
    
async def runCheckMacros(browser, record_id, tabs_num=3):
    try:
        if not ObjectId.is_valid(record_id):
            return {"status":"FAILED","error":"Invalid record_id"}
        
        check_result = await check_incomplete_macros_after_creation(browser, record_id, browsers_num=tabs_num)
        return {"status":"CHECKER_RESULT", "recordId":str(record_id), "result":check_result}
    
    except Exception as e:
        tb = traceback.format_exc()
        return {"status":"FAILED","error":str(e),"traceback":tb}
    
async def retryMacros(browser, record_id, tabs_num=3):
    try:
        report = await db.halfreports.find_one({"_id": ObjectId(record_id)})
        if not report:
            return {"status": "FAILED", "error": "Report not found"}

        assets = report.get("asset_data", [])
        if not assets:
            return {"status": "FAILED", "error": "No assets found"}

        retry_assets = [(idx, a) for idx, a in enumerate(assets) if a.get("submitState") == 0]
        if not retry_assets:
            return {"status": "SUCCESS", "message": "All macros are already complete"}

        print(f"[RETRY] Retrying {len(retry_assets)} incomplete macros for report {record_id}")

        pages = [await browser.get("about:blank", new_tab=True) for _ in range(min(tabs_num, len(retry_assets)))]
        chunks = [retry_assets[i::len(pages)] for i in range(len(pages))]

        async def process_chunk(page, assets_chunk):
            for idx, asset in assets_chunk:
                macro_id = asset.get("id")
                if not macro_id:
                    print(f"[SKIP] No macro_id for asset index {idx}")
                    continue

                try:
                    merged_asset = merge_asset_with_parent(asset, report)

                    await fill_macro_form(
                        page,
                        macro_id,
                        merged_asset,
                        macro_form_config["field_map"],
                        macro_form_config["field_types"]
                    )

                    await db.halfreports.update_one(
                        {"_id": report["_id"]},
                        {"$set": {f"asset_data.{idx}.submitState": 1}}
                    )

                    print(f"[RETRY FILLED] macro_id={macro_id} asset_index={idx}")

                except Exception as e:
                    print(f"[RETRY ERROR] macro_id={macro_id}: {e}")

        await asyncio.gather(*[process_chunk(p, chunk) for p, chunk in zip(pages, chunks)])

        for p in pages:
            await p.close()

        return {"status": "SUCCESS", "message": f"Retried {len(retry_assets)} incomplete macros"}

    except Exception as e:
        tb = traceback.format_exc()
        return {"status": "FAILED", "error": str(e), "traceback": tb}

