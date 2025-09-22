import asyncio
import nodriver as uc
import re
import random
import json
import pandas as pd
import sqlite3
import os
from imap_tools import MailBox, AND
from datetime import datetime
VERIFICATION_CODES = []
async def fetch_latest_otp_from_email(timeout_seconds: int = 180, poll_interval: float = 3.0, require_newer_than: datetime | None = None):
    """Poll Gmail for the latest 6-digit OTP from any taqeem sender within a timeout.
    Only returns codes from emails received at or after `require_newer_than` (if provided).
    Returns the code as a string or None if not found."""
    try:
        with MailBox('imap.gmail.com').login(account_data["gmail_username"], account_data["gmail_password"], "INBOX") as mailbox:
            start = datetime.now()
            seen_codes = set()
            while (datetime.now() - start).total_seconds() < timeout_seconds:
                try:
                    # Fetch most recent messages from today; reverse=True returns newest first
                    emails = list(mailbox.fetch(AND(date_gte=datetime.now().date()), limit=30, reverse=True))
                except Exception as e:
                    print(f"{datetime.now()} IMAP fetch error: {e}")
                    await asyncio.sleep(poll_interval)
                    continue

                for email in emails:
                    # Skip emails older than the login attempt time (avoid stale OTPs)
                    try:
                        if require_newer_than and getattr(email, 'date', None) and email.date < require_newer_than:
                            continue
                    except Exception:
                        # If email has no usable date, ignore time filter
                        ...

                    sender = (email.from_ or '').lower()
                    # Accept any taqeem sender (e.g., @taqeem.sa, @taqeem.gov.sa)
                    if 'taqeem' not in sender:
                        continue
                    # Search both subject, text and html bodies for 6-digit sequences
                    content = f"{email.subject or ''}\n{email.text or ''}\n{email.html or ''}"
                    codes = re.findall(r"\b(\d{6})\b", content)
                    for code in codes[::-1]:  # prefer later matches within the same email
                        if code in seen_codes:
                            continue
                        seen_codes.add(code)
                        if code not in VERIFICATION_CODES:
                            VERIFICATION_CODES.append(code)
                        print(f"{datetime.now()} OTP candidate from {sender}: {code}")
                        return code

                await asyncio.sleep(poll_interval)
    except Exception as e:
        print(f"{datetime.now()} IMAP login error: {e}")
    return None
lock1 = asyncio.Lock()
account_data = None

async def create_report(browser, data):
    await browser.tabs[0].activate()  # Activate tab 0 to bring it into focus
    await browser.tabs[0].sleep(1)  # Give the browser a moment to focus
    page = await browser.get(f"https://qima.taqeem.sa/report/create/{data['sector_id']}/{data['organization_id']}")

    await page.sleep(1)

    report_file_path = data["report_file"]
    if not os.path.exists(report_file_path):
        raise FileNotFoundError(f"Report file not found at: {report_file_path}")

#     csrf = await page.select("form[id='report'] input[name='_token']", timeout=60)
#     form_element = await page.select("form[id='report']")

#     await form_element.apply("""
#         (elem) => {
#             elem.innerHTML = `
# <input name='sector_id' value='""" + str(data['sector_id']) + """'>
# <input name='organization_id' value='""" + str(data['organization_id']) + """'>
# <input name='title' value='""" + str(data['title']) + """'>
# <input name='purpose_id' value='""" + str(data['purpose_id']) + """'>
# <input name='value_premise_id' value='""" + str(data['value_premise_id']) + """'>
# <input name='report_type' value='""" + str(data['report_type']) + """'>
# <input name='valued_at' value='""" + str(data['valued_at']) + """'>
# <input name='submitted_at' value='""" + str(data['submitted_at']) + """'>
# <input name='assumptions' value='""" + str(data['assumptions']) + """'>
# <input name='special_assumptions' value='""" + str(data['special_assumptions']) + """'>
# <input name='value' value='""" + str(data['value']) + """'>
# <input name='currency_id' value='""" + str(data['currency_id']) + """'>
# <input name="report_file" type="file" accept="application/pdf">
# <input name='client[0][name]' value='""" + str(data['name']) + """'>
# <input name='client[0][telephone]' value='""" + str(data['telephone']) + """'>
# <input name='client[0][email]' value='""" + str(data['email']) + """'>
# <input name='valuer[0][id]' value='""" + str(data['valuer_id']) + """'>
# <input name='valuer[0][contribution]' value='""" + str(data['valuer_contribution']) + """'>
# <input class="btn btn-primary btn-lg " name="continue" type="submit" value="حفظ واستمرار">
# """ + await csrf.get_html() + """`;
#         }
#     """)
#     'has_user': (None, '1'),

# <input name='has_user' value='""" +  + """'>
# <input name='user[0][name]' value='""" +  + """'>




    # عنوان التقرير
    e = await page.select('input[name="title"]')
    await e.focus()
    await page.sleep(1)
    await e.send_keys(str(data["title"]))
    # الغرض من التقييم
    await (await page.find(f'//select[@name="purpose_id"]/option[@value="{data["purpose_id"]}"]')).select_option()
    # فرضية القيمة
    await (await page.find(f'//select[@name="value_premise_id"]/option[@value="{data["value_premise_id"]}"]')).select_option()
    # نوع التقرير
    await (await page.find(f'//input[@value="{data["report_type"]}"]')).click()
    # تاريخ التقييم
    e = await page.select('input[name="valued_at"]')
    await e.apply('''
        (elem) => { elem.removeAttribute("readonly"); }
    ''')
    await e.send_keys(str(data["valued_at"]))
    # تاريخ إصدار التقرير
    e = await page.select('input[name="submitted_at"]')
    await e.apply('''
        (elem) => { elem.removeAttribute("readonly"); }
    ''')
    await e.send_keys(str(data["submitted_at"]))
    # الافتراضات
    await (await page.select('input[name="assumptions"]')).send_keys(str(data["assumptions"]))
    # الافتراضات الخاصة
    await (await page.select('input[name="special_assumptions"]')).send_keys(str(data["special_assumptions"]))
    # الرأي النهائي في القيمة
    await (await page.select('input[name="value"]')).send_keys(str(data["value"]))
    await (await page.find(f'//select[@name="currency_id"]/option[@value="{data["currency_id"]}"]')).select_option()
    # ملف أصل التقرير
    e = await page.select('input[name="report_file"]')
    await e.send_file(report_file_path)
    # اسم العميل
    await (await page.select('input[name="client[0][name]"]')).send_keys(str(data["name"]))
    # رقم الهاتف
    await (await page.select('input[name="client[0][telephone]"]')).send_keys(str(data["telephone"]))
    # البريد الإلكتروني
    await (await page.select('input[name="client[0][email]"]')).send_keys(str(data["email"]))
    # # المقيم
    # await (await page.select('input[name="valuer[0][id]"]')).send_keys(str(data["valuer_id"]))
    # # نسبة المساهمة
    # await (await page.select('input[name="valuer[0][contribution]"]')).send_keys(str(data["valuer_contribution"]))

    # Submit the form
    await proceed_to_next_page(browser, 0, 'input[name="title"]')

    # await pass_captcha(page)

async def create_asset(browser, index, num, report_id):
    if num <= 0:
        return
    # await pass_captcha(page)

    # e = await try_or_reload_page(
    #     browser, index,
    #     browser.tabs[index].select('a[class="btn btn-primary "]', timeout=60),
    #     1
    # )
    # await e.click()
    
    await go_to_url(browser, index, f"https://qima.taqeem.sa/report/asset/create/{report_id}")

    # await go_to_url(f"https://qima.taqeem.sa/report/macro_asset/create/{report_id}/{num}")
    await browser.tabs[index].sleep(1)


    csrf = await browser.tabs[index].select("form[action='https://qima.taqeem.sa/report/ME_asset'] input[name='_token']", timeout=120)
    form_element = await browser.tabs[index].select("form[action='https://qima.taqeem.sa/report/ME_asset']")

    await form_element.apply("""
        (elem) => {
            elem.innerHTML = `
<input id='macros' name='macros' value='""" + str(min(10, num)) + """' />
<input id='machines' name='machines' value='0' />
<input id='equipments' name='equipments' value='0' />

<input id='report_id' name='report_id' value='""" + str(report_id) + """' />
<input id="save" class="btn btn-primary" name="update" type="submit" value="حفظ">
""" + await csrf.get_html() + """`;
        }
    """)

    # # عدد الأوصاف الكلية
    # e = await browser.tabs[0].select('input[name="macros"]', timeout=100)
    # await browser.tabs[0].sleep(1)

    # await e.clear_input()
    # await browser.tabs[0].sleep(.1)
    # await e.send_keys(str(min(10, num)))
    num -= 10

    # await browser.tabs[0].sleep(2)
    # await (await browser.tabs[0].select('input[type="submit"]')).click()

    # make sure page is loaded
    await proceed_to_next_page(browser, index, 'input[name="macros"]')
    # await (await browser.tabs[index].select('input[type="submit"]')).click()

    await create_asset(browser, index, num, report_id)

    # await pass_captcha(page)    

async def create_asset_res(browser, index, num, report_id):
    if num <= 0:
        return
    # await pass_captcha(page)

    # e = await try_or_reload_page(
    #     browser, index,
    #     browser.tabs[index].select('a[class="btn btn-primary "]', timeout=60),
    #     1
    # )
    # await e.click()
    
    await go_to_url(browser, index, f"https://qima.taqeem.sa/report/asset/create/{report_id}")

    # await go_to_url(f"https://qima.taqeem.sa/report/macro_asset/create/{report_id}/{num}")
    await browser.tabs[index].sleep(1)


    csrf = await browser.tabs[index].select("form[action='https://qima.taqeem.sa/report/ME_asset'] input[name='_token']", timeout=120)
    form_element = await browser.tabs[index].select("form[action='https://qima.taqeem.sa/report/ME_asset']")

    await form_element.apply("""
        (elem) => {
            elem.innerHTML = `
<input id='macros' name='macros' value='""" + str( num) + """' />
<input id='machines' name='machines' value='0' />
<input id='equipments' name='equipments' value='0' />

<input id='report_id' name='report_id' value='""" + str(report_id) + """' />
<input id="save" class="btn btn-primary" name="update" type="submit" value="حفظ">
""" + await csrf.get_html() + """`;
        }
    """)

    # # عدد الأوصاف الكلية
    # e = await browser.tabs[0].select('input[name="macros"]', timeout=100)
    # await browser.tabs[0].sleep(1)

    # await e.clear_input()
    # await browser.tabs[0].sleep(.1)
    # await e.send_keys(str(min(10, num)))
    # num -= 10

    # await browser.tabs[0].sleep(2)
    # await (await browser.tabs[0].select('input[type="submit"]')).click()

    # make sure page is loaded
    await proceed_to_next_page(browser, index, 'input[name="macros"]')
    # await (await browser.tabs[index].select('input[type="submit"]')).click()

    await create_asset(browser, index, num, report_id)

    # await pass_captcha(page)

async def get_macro_pages_num(browser, report_id):
    browser.tabs[0] = await browser.get(f"https://qima.taqeem.sa/report/{report_id}")
    
    while not len(next_button := await browser.tabs[0].select_all(".paginate_button.next")):
        await browser.tabs[0].sleep(1)
        
    await browser.tabs[0].sleep(1)
    if len(li := (await browser.tabs[0].find_all("//ul[@class='pagination']/li/*"))):
        page_no = int(li[-2].text)
    else:
        page_no = 1

    return page_no

async def get_macros_from_page(page):
    urls = []

    # Wait for the next button to appear (or pagination to be rendered)
    while not (next_buttons := await page.select_all(".paginate_button.next")):
        await asyncio.sleep(1)

    # Scrape current page for macro edit URLs
    html_content = await page.get_content()
    await asyncio.sleep(1)
    urls.extend(re.findall(r"(https://qima\.taqeem\.sa/report/macro/\d+/edit)", html_content))

    # If next button exists and is not disabled, click and scrape next page
    if "disabled" not in await next_buttons[0].get_html():
        await next_buttons[0].click()
        await asyncio.sleep(1)

        html_content = await page.get_content()
        await asyncio.sleep(1)
        urls.extend(re.findall(r"(https://qima\.taqeem\.sa/report/macro/\d+/edit)", html_content))

    return urls


async def get_macros(browser, report_id, assets_data,browsers_num):
    is_there_no_id_macro = False
    assets_data_url = []
    for d in assets_data:
        if int(d["macroid"]) == 0:
            is_there_no_id_macro = True
            break
        assets_data_url.append(f'https://qima.taqeem.sa/report/macro/{d["macroid"]}/edit')
    
    if not is_there_no_id_macro:
        return assets_data_url

    pages_num = await get_macro_pages_num(browser, report_id)

    macros_urls = []

    semaphore = asyncio.Semaphore(browsers_num)
    empty_indexes = [1 for i in range(browsers_num)]

    async def limited_task(page_no):
        async with semaphore:
            async with lock1:
                index = await get_empty_index(empty_indexes) + 1
                empty_indexes[index - 1] = 0

            await go_to_url(browser, index, f"https://qima.taqeem.sa/report/{report_id}?page={page_no}")
            await browser.tabs[index].sleep(.5)

            macros_urls.extend(await get_macros_from_page(browser, index))

            empty_indexes[index - 1] = 1
    

    for i in range(browsers_num):
        page = await browser.get("", new_tab=True)

    tasks = []
    for i in range(pages_num):
        tasks.append(limited_task(i+1))
    await asyncio.gather(*tasks)

    for j in range(browsers_num, 0, -1):
        await browser.tabs[j].close()
    
    return macros_urls

async def edit_macro(browser, index, data, report_id, macro_id, browsers_num):
    await go_to_url(browser, index, f"https://qima.taqeem.sa/report/macro/{macro_id}/edit")

    await browser.tabs[index].select("input[id='asset_type']", timeout=200)

    csrf = await try_or_reload_page(
        browser, index,
        "form[id='macro_update'] input[name='_token']",
        2
    )
    form_element = await browser.tabs[index].select("form[id='macro_update']", timeout=60)

    if form_element is None:
        raise Exception(f"Form 'macro_update' not found on page for macro {macro_id}")

    country = data['country']
    region = data['region']
    city = data['city']

    while True:
        try:
            page_content = await browser.tabs[index].get_content()
            country_v = int(re.findall(
                f'value="(\\d+)".*?>{country}<',
                page_content
            )[0])
            break
        except:
            await browser.tabs[index].sleep(2)

    json_tab_index = index - (browsers_num - (browsers_num // 2))
    page2 = await browser.tabs[json_tab_index].get(f"https://qima.taqeem.sa/common/regions?country_id={country_v}")

    while True:
        try:
            json_data = json.loads(
                (await (await browser.tabs[json_tab_index].select("pre", timeout=100)).get_html())[5:-6]
            )
            break
        except:
            await browser.tabs[json_tab_index].sleep(1)

    for k, v in json_data.items():
        if v == region:
            region_v = int(k)
            break

    page2 = await browser.tabs[json_tab_index].get(f"https://qima.taqeem.sa/common/cities?region_id={region_v}")

    while True:
        try:
            json_data = json.loads(
                (await (await browser.tabs[json_tab_index].select("pre", timeout=100)).get_html())[5:-6]
            )
            break
        except:
            await browser.tabs[json_tab_index].sleep(1)

    for k, v in json_data.items():
        if v == city:
            city_v = int(k)
            break

    print(country_v, region_v, city_v, country, region, city)

    await form_element.apply("""
        (elem) => {
            elem.innerHTML = `
<input id='asset_type' name='asset_type' value='""" + str(data["asset_type"]) + """' />
<input id='asset_name' name='asset_name' value='""" + str(data["asset_name"]) + """' />
<input id='asset_usage_id' name='asset_usage_id' value='""" + str(data["asset_usage_id"]) + """' />
<input id='value_base_id' name='value_base_id' value='""" + str(data["value_base"]) + """' />
<input id='inspected_at' name='inspected_at' value='""" + "-".join(str(data["inspection_date"]).split("-")[::-1]) + """' />
<input id='value' name='value' value='""" + str(data["final_value"]) + """' />
<input id='production_capacity' name='production_capacity' value='""" + str(data["production_capacity"]) + """' />
<input id='production_capacity_measuring_unit' name='production_capacity_measuring_unit' value='""" + str(data["production_capacity_measuring_unit"]) + """' />
<input id='owner_name' name='owner_name' value='""" + str(data['owner_name']) + """' />
<input id='product_type' name='product_type' value='""" + str(data['product_type']) + """' />
<input id='approach' name='approach[1][is_primary]' value='""" + str(data['market_approach']) + """' />
<input id='approach' name='approach[1][value]' value='""" + str(data['market_approach_value']) + """' />
<input id='approach' name='approach[3][is_primary]' value='""" + str(data['cost_approach']) + """' />
<input id='approach' name='approach[3][value]' value='""" + str(data['cost_approach_value']) + """' />
<input id='country_id' name='country_id' value='""" + str(country_v) + """' />
<input id='region_id' name='region_id' value='""" + str(region_v) + """' />
<input id='city_id' name='city_id' value='""" + str(city_v) + """' />

<input id='report_id' name='report_id' value='""" + str(report_id) + """' />
<input id="save" class="btn btn-primary" name="update" type="submit" value="حفظ">
""" + await csrf.get_html() + """`;
        }
    """)

    # make sure page is loaded
    await proceed_to_next_page(browser, index, 'input[name="asset_type"]')
    return index

async def try_or_reload_page(browser, index, selector, a = 0):
    while True:
        try:
            return await browser.tabs[index].select(selector, timeout=120)
        except Exception as e:
            print(a, e)
            await browser.tabs[index].reload()
            await asyncio.sleep(1)

async def create_micro_asset(browser, index, data, macro_id, report_id):
    # e = await try_or_reload_page(
    #     browser, index,
    #     browser.tabs[index].select('.btn.btn-outline-primary', timeout=60)
    # )
    # await e.parent.click()
    
    await go_to_url(browser, index, f"https://qima.taqeem.sa/report/macro_asset/create/{report_id}/{macro_id}")

    csrf = await try_or_reload_page(
        browser, index,
        "form[action='https://qima.taqeem.sa/report/ME_asset'] input[name='_token']",
        3
    )
    # csrf = await browser.tabs[index].select("form[action='https://qima.taqeem.sa/report/ME_asset'] input[name='_token']", timeout=100)

    form_element = await browser.tabs[index].select("form[action='https://qima.taqeem.sa/report/ME_asset']")

    await form_element.apply("""
        (elem) => {
            elem.innerHTML = `
<input id='machines' name='machines' value='1' />
<input id='equipments' name='equipments' value='0' />

<input id='macro_id' name='macro_id' value='""" + str(macro_id) + """' />
<input id='report_id' name='report_id' value='""" + str(report_id) + """' />
<input id="save" class="btn btn-primary" name="update" type="submit" value="حفظ">
""" + await csrf.get_html() + """`;
        }
    """)

    # await browser.tabs[index].sleep(1)

    # # عدد الآلات
    # e = await browser.tabs[index].select('input[name="machines"]', timeout=100)
    # await e.clear_input()
    # await e.focus()
    # await browser.tabs[index].sleep(1)
    # await e.send_keys("1") # data

    # make sure page is loaded
    await proceed_to_next_page(browser, index, 'input[name="machines"]')
    # await (await browser.tabs[index].select('input[type="submit"]')).click()

async def get_micros(browser, index):
    await browser.tabs[index].select("table[class='table table-responsive']", timeout=120)

    html_content = await browser.tabs[index].get_content()
    return re.findall("(https://qima.taqeem.sa/report/micro/\\d+/edit)", html_content)

async def edit_micro_asset(browser, index, data, report_id, macro_id, micro_id):
    await go_to_url(browser, index, f"https://qima.taqeem.sa/report/micro/{micro_id}/edit")

    csrf = await try_or_reload_page(
        browser, index,
        "form[id='macro_update'] input[name='_token']",
        4
    )
    form_element = await browser.tabs[index].select("form[id='macro_update']")

    await form_element.apply("""
        (elem) => {
            elem.innerHTML = `
<input id='asset_name' name='asset_name' value='""" + str(data["asset_name_micro"]) + """' />
<input id='serial_no' name='serial_no' value='""" + str(data["serial_no"]) + """' />
<input id='asset_usage_id' name='asset_usage_id' value='""" + str(data["asset_usage_id_micro"]) + """' />
<input id='value_base_id' name='value_base_id' value='""" + str(data["value_base_id_micro"]) + """' />
<input id='inspected_at' name='inspected_at' value='""" + "-".join(str(data["inspected_at_micro"]).split("-")[::-1]) + """' />
<input id='value' name='value' value='""" + str(data["final_value_micro"]) + """' />
<input id='approach[1][is_primary]' name='approach[1][is_primary]' value='""" + str(data["market_approach_micro"]) + """' />
<input id='approach[1][value]' name='approach[1][value]' value='""" + str(data["market_approach_value_mirco"]) + """' />
<input id='approach[3][is_primary]' name='approach[3][is_primary]' value='""" + str(data["cost_approach_micro"]) + """' />
<input id='approach[3][value]' name='approach[3][value]' value='""" + str(data["cost_approach_value_micro"]) + """' />
<input id='country_id' name='country_id' value='""" + str(data["manufacturing_country"]) + """' />
<input id='year_made' name='year_made' value='""" + str(data["year_made"]) + """' />
<input id='purchase_or_manufacture_date' name='purchase_or_manufacture_date' value='""" + "-".join(str(data["purchase_manufacture_date"]).split("-")[::-1]) + """' />
<input id='start_operation_date' name='start_operation_date' value='""" + "-".join(str(data["start_operation_date"]).split("-")[::-1]) + """' />
<input id='capacity' name='capacity' value='""" + str(data["capacity"]) + """' />
<input id='production_capacity_measuring_unit' name='production_capacity_measuring_unit' value='""" + str(data["capacity_measuring_unit"]) + """' />
<input id='normal_useful_life' name='normal_useful_life' value='""" + str(data["normal_useful_life"]) + """' />
<input id='effective_age' name='effective_age' value='""" + str(data["effective_age"]) + """' />
<input id='depreciation' name='depreciation' value='""" + str(data["depreciation"]) + """' />
<input id='cost_source' name='cost_source' value='""" + str(data["cost_source"]) + """' />
<input id='cost' name='cost' value='""" + str(data["cost"]) + """' />
<input id='brand' name='brand' value='""" + str(data["brand_manufacturer"]) + """' />
<input id='model' name='model' value='""" + str(data["model"]) + """' />
<input id='additional_equipment' name='additional_equipment' value='""" + str(data["additional_equipment_accessories"]) + """' />
<input id='supplier_name' name='supplier_name' value='""" + str(data["supplier_name"]) + """' />
<input id='measurement' name='measurement' value='""" + str(data["measurement"]) + """' />
<input id='machinery_specification' name='machinery_specification' value='""" + str(data["machinery_equipment_specification"]) + """' />

<input id='macro_id' name='macro_id' value='""" + str(macro_id) + """' />
<input id='report_id' name='report_id' value='""" + str(report_id) + """' />
<input id="save" class="btn btn-primary" name="update" type="submit" value="حفظ">
""" + await csrf.get_html() + """`;
        }
    """)

    # # اسم/وصف الأصل
    # e = await browser.tabs[index].select('#asset_name', timeout=100)
    # await e.clear_input()
    # await e.focus()
    # await browser.tabs[index].sleep(.5)
    # await e.send_keys(str(data["asset_name_micro"]))

    # # الرقم التسلسلي
    # e = await browser.tabs[index].select('#serial_no')
    # await e.clear_input()
    # await e.send_keys(str(data["serial_no"]))

    # # استخدام/قطاع الأصل محل التقييم
    # try:
    #     await (await browser.tabs[index].find(f'//select[@name="asset_usage_id"]/option[@value="{data["asset_usage_id_micro"]}"]')).select_option()
    # except AttributeError:
    #     ...

    # # أساس القيمة
    # try:
    #     await (await browser.tabs[index].find(f'//select[@name="value_base_id"]/option[@value="{data["value_base_id_micro"]}"]')).select_option()
    # except AttributeError:
    #     ...

    # # تاريخ معاينة الأصل
    # b = str(data["inspected_at_micro"]).split(" ")[0]
    # # b = b[5:].replace("-", "") + b[:4]
    # b = b[5:] + "-" + b[:4]
    # e = await browser.tabs[index].select('input[name="inspected_at"]')
    # await e.apply('''
    #     (elem) => { elem.removeAttribute("readonly"); }
    # ''')
    # await e.clear_input()
    # await e.send_keys(b)

    # # الرأي النهائي في القيمة
    # await (await browser.tabs[index].select('input[name="value"]')).send_keys(str(data["final_value_micro"]))

    # # أسلوب السوق
    # try:
    #     await (await browser.tabs[index].find(f'//select[@name="approach[1][is_primary]"]/option[@value="{data["market_approach_micro"]}"]')).select_option()
    # except AttributeError:
    #     ...

    # # القيمة
    # e = await browser.tabs[index].select('input[name="approach[1][value]"]')
    # await e.clear_input()
    # await e.send_keys(str(data["market_approach_value_mirco"]))

    # # أسلوب التكلفة
    # try:
    #     await (await browser.tabs[index].find(f'//select[@name="approach[3][is_primary]"]/option[@value="{data["cost_approach_micro"]}"]')).select_option()
    # except AttributeError:
    #     ...

    # # القيمة
    # e = await browser.tabs[index].select('input[name="approach[3][value]"]')
    # await e.clear_input()
    # await e.send_keys(str(data["cost_approach_value_micro"]))

    # # الدولة المصنّعة
    # try:
    #     await (await browser.tabs[index].find(f'//select[@name="country_id"]/option[@value="{data["manufacturing_country"]}"]')).select_option()
    # except AttributeError:
    #     ...
    # # await (await browser.tabs[index].find(f'//select[@name="country_id"]/option[text()="{data["manufacturing_country"]}"]')).select_option()

    # # سنة التصنيع
    # e = await browser.tabs[index].select('input[name="year_made"]')
    # await e.clear_input()
    # await e.send_keys(str(data["year_made"]))

    # # تاريخ الشراء/التصنيع
    # b = str(data["purchase_manufacture_date"]).split(" ")[0]
    # # b = b[5:].replace("-", "") + b[:4]
    # b = b[5:] + "-" + b[:4]
    # e = await browser.tabs[index].select('input[name="purchase_or_manufacture_date"]')
    # await e.apply('''
    #     (elem) => { elem.removeAttribute("readonly"); }
    # ''')
    # await e.clear_input()
    # await e.send_keys(b)

    # # تاريخ بدء التشغيل
    # b = str(data["start_operation_date"]).split(" ")[0]
    # # b = b[5:].replace("-", "") + b[:4]
    # b = b[5:] + "-" + b[:4]
    # e = await browser.tabs[index].select('input[name="start_operation_date"]')
    # await e.apply('''
    #     (elem) => { elem.removeAttribute("readonly"); }
    # ''')
    # await e.clear_input()
    # await e.send_keys(b)

    # # القدرة
    # e = await browser.tabs[index].select('input[name="capacity"]')
    # await e.clear_input()
    # await e.send_keys(str(data["capacity"]))

    # # وحدة قياس القدرة
    # e = await browser.tabs[index].select('input[name="production_capacity_measuring_unit"]')
    # await e.clear_input()
    # await e.send_keys(str(data["capacity_measuring_unit"]))

    # # العمر الافتراضي الطبيعي
    # e = await browser.tabs[index].select('input[name="normal_useful_life"]')
    # await e.clear_input()
    # await e.send_keys(str(data["normal_useful_life"]))

    # # العمر الفعّال
    # e = await browser.tabs[index].select('input[name="effective_age"]')
    # await e.clear_input()
    # await e.send_keys(str(data["effective_age"]))

    # # الإهلاك
    # e = await browser.tabs[index].select('input[name="depreciation"]')
    # await e.clear_input()
    # await e.send_keys(str(data["depreciation"]))

    # # مصدر التكلفة
    # e = await browser.tabs[index].select('input[name="cost_source"]')
    # await e.clear_input()
    # await e.send_keys(str(data["cost_source"]))

    # # التكلفة
    # e = await browser.tabs[index].select('input[name="cost"]')
    # await e.clear_input()
    # await e.send_keys(str(data["cost"]))

    # # العلامة التجارية/المصنّع
    # e = await browser.tabs[index].select('input[name="brand"]')
    # await e.clear_input()
    # await e.send_keys(str(data["brand_manufacturer"]))

    # # الطراز/النوع
    # e = await browser.tabs[index].select('input[name="model"]')
    # await e.clear_input()
    # await e.send_keys(str(data["model"]))

    # # معدّات/ملحقات إضافية
    # e = await browser.tabs[index].select('input[name="additional_equipment"]')
    # await e.clear_input()
    # await e.send_keys(str(data["additional_equipment_accessories"]))

    # # اسم المورّد
    # e = await browser.tabs[index].select('input[name="supplier_name"]')
    # await e.clear_input()
    # await e.send_keys(str(data["supplier_name"]))

    # # القياسات
    # e = await browser.tabs[index].select('input[name="measurement"]')
    # await e.clear_input()
    # await e.send_keys(str(data["measurement"]))

    # # وصف الآلة/المعدة
    # e = await browser.tabs[index].select('textarea[name="machinery_specification"]')
    # await e.clear_input()
    # await e.send_keys(str(data["machinery_equipment_specification"]))

    # make sure page is loaded
    await proceed_to_next_page(browser, index, '#serial_no')
    # await (await browser.tabs[index].select('input[type="submit"]')).click()
async def login(browser):
    page = await browser.get("https://qima.taqeem.sa/valuer/login")
    await browser.tabs[0].sleep(0.5)

    try:
        # Credentials
        e = await browser.tabs[0].select('#username')
        try:
            await e.clear_input()
        except Exception:
            ...
        await e.send_keys(str(account_data["taqeem_username"]))
        await browser.tabs[0].sleep(0.5)

        e = await browser.tabs[0].select('#password')
        try:
            await e.clear_input()
        except Exception:
            ...
        await e.send_keys(str(account_data["taqeem_password"]))
        await browser.tabs[0].sleep(0.5)

        # Submit login
        e = await browser.tabs[0].select('[name="login"]')
        await e.click()
        await browser.tabs[0].sleep(1.0)

        # If OTP field appears, poll mailbox until a valid code is retrieved
        try:
            c = await browser.tabs[0].select('#emailCode', timeout=5)
            print(f"{datetime.now()} Waiting for OTP email...")

            for attempt in range(60):  # Up to ~3 minutes
                # Short polling within helper to get a fresh code
                code = await fetch_latest_otp_from_email(timeout_seconds=10, poll_interval=2.0)
                if not code and VERIFICATION_CODES:
                    code = VERIFICATION_CODES[-1]
                if not code:
                    await asyncio.sleep(2)
                    continue

                await c.clear_input()
                await c.send_keys(str(code))
                await browser.tabs[0].sleep(0.5)
                try:
                    submit2 = await browser.tabs[0].select('input[type="submit"]', timeout=10)
                    await submit2.click()
                except Exception:
                    ...
                await browser.tabs[0].sleep(1)

                # Check if OTP page still present
                try:
                    c = await browser.tabs[0].select('#emailCode', timeout=3)
                    print(f"{datetime.now()} OTP {code} did not pass, retrying...")
                    continue
                except Exception:
                    print(f"{datetime.now()} OTP accepted")
                    return page

            raise Exception("OTP verification failed or timed out.")
        except Exception:
            # No OTP requested; likely already logged in
            return page

    except Exception as e:
        print(f"{datetime.now()} Login flow exception: {e}. Assuming already logged in.")
        return page

    return page

async def get_cookies(browser):
    return dict(map(
        lambda x: (x.name, x.value),
        await browser.cookies.get_all()
    ))

async def get_tabs_num(browser):
    n = 0
    while True:
        try:
            await browser.tabs[n].get_content()
            # await browser.tabs[n].select('html')
            n += 1
        except:
            break

    return n

async def get_tab_url(browser, tab_index):
    while True:
        try:
            e = await try_or_reload_page(
                browser, tab_index, 'html',
                5
            )
            await e.apply('''
                (elem) => {
                    let input = document.createElement("input");
                    input.type = "hidden";
                    input.id = "current_url";
                    input.innerText = window.location.href;
                    document.body.appendChild(input);
                }
            ''')

            await browser.tabs[tab_index].sleep(1)

            current_url_input = await browser.tabs[tab_index].select('input[id="current_url"]')
            
            return current_url_input.text
        except:
            ...

async def go_to_url(browser, tab_index, url):
    current_url = await get_tab_url(browser, tab_index)

    if url == current_url:
        return

    while True:
        try:
            e = await browser.tabs[tab_index].select('html', timeout=120)
            break
        except:
            await browser.tabs[tab_index].reload()
            await asyncio.sleep(2)

    while True:
        await e.apply('''
            (elem) => {
                elem.innerHTML = `<a href="''' + url + '''">link</a>`;
            }
        ''')
        # await browser.tabs[tab_index].sleep(1)

        link_element = await browser.tabs[tab_index].select(f'a[href="{url}"]', timeout=120)
        # await browser.tabs[tab_index].sleep(.5)
        await link_element.click()

        await browser.tabs[tab_index].sleep(1)

        current_url = await get_tab_url(browser, tab_index)
        
        if current_url == url:
            break

async def fix_data(data):
    for i, d in enumerate(data):
        for key, value in d.items():
            if value == None:
                data[i][key] = "0"
    
    return data

async def get_empty_index(empty_indexes):
    index = -1

    while index == -1:
        for i, index_ in enumerate(empty_indexes):
            if index_ == 1:
                index = i
                break
        else:
            await asyncio.sleep(1)

    return index

async def add_report(browser, report_data, assets_data, conn, browsers_num):
    assets_data = await fix_data(assets_data)
    semaphore = asyncio.Semaphore(browsers_num)
    page = await login(browser)
    cursor = conn.cursor()

    original_report_id = report_data["report_id"]
    if int(original_report_id) >= 0:  # New report creation
        await create_report(browser, report_data)
        await asyncio.sleep(2)
        while True:
            try:
                report_id = re.findall("تقرير رقم (\\d+)", await browser.tabs[0].get_content())[0]
                break
            except:
                await browser.tabs[0].sleep(1)
        # Update reports table
        cursor.execute("UPDATE reports SET report_id = ? WHERE id = ?", (report_id, report_data['id']))
        # Update assets table with the new report_id
        cursor.execute("UPDATE assets SET report_id = ? WHERE report_id = ?", (report_id, original_report_id))
        conn.commit()
        macros_urls_exists = []
    else:
        report_id = original_report_id  # Use existing report_id if no new report is created

    # Fetch existing macros from the site
    macros_urls_exists = await get_macros(browser, report_id, assets_data,browsers_num)
    num_assets = len(assets_data)
    num_existing_macros = len(macros_urls_exists)
    num_macros_to_create = max(0, num_assets - num_existing_macros)
    
    empty_indexes = [1 for i in range(browsers_num)]

    async def limited_task(num):
        async with semaphore:
            async with lock1:
                index = await get_empty_index(empty_indexes) + 1
                empty_indexes[index - 1] = 0
            await create_asset(browser, index, num, report_id)
            empty_indexes[index - 1] = 1

    for _ in range(browsers_num):
        page = await browser.get('', new_tab=True)

    tasks = []
    z = num_macros_to_create // browsers_num
    y = num_macros_to_create % browsers_num
    for i in range(browsers_num):
        tasks.append(limited_task(z + y if i == 0 else z))

    await asyncio.gather(*tasks)
    for i in range(browsers_num, 0, -1):
        await browser.tabs[i].close()

    if num_macros_to_create > 0:
        macros_urls_exists = await get_macros(browser, report_id, assets_data,browsers_num)

    macros_data_urls = []
    used_macro_ids = set()
    for i, d in enumerate(assets_data):
        if int(d["submitState"]) != 0:
            continue
        if len(macros_urls_exists) == 0:
            print(f"Warning: Not enough macros for asset {d['id']}")
            continue
        new_macro_id = macros_urls_exists[0].split("/")[-2]
        while new_macro_id in used_macro_ids and macros_urls_exists:
            macros_urls_exists.pop(0)
            new_macro_id = macros_urls_exists[0].split("/")[-2] if macros_urls_exists else None
        if new_macro_id:
            used_macro_ids.add(new_macro_id)
            macros_urls_exists.pop(0)
            cursor.execute("UPDATE assets SET macroid = ? WHERE id = ?", (new_macro_id, d['id']))
            macros_data_urls.append((d, f'https://qima.taqeem.sa/report/macro/{new_macro_id}/edit'))
        else:
            print(f"Error: No macro available for asset {d['id']}")

    conn.commit()

    async def limited_task(data_row, url):
        async with semaphore:
            async with lock1:
                index = await get_empty_index(empty_indexes) + bb
                empty_indexes[index - bb] = 0

            macro_id = url.split("/")[-2]
            print(f"{macro_id} started")
            try:
                await edit_macro(browser, index, data_row, report_id, macro_id, browsers_num)  # Pass browsers_num
                print(f"{macro_id} edited")

                if int(data_row["microid"]) != 0:
                    micros_urls = [f'https://qima.taqeem.sa/report/micro/{data_row["microid"]}/edit']
                else:
                    micros_urls = await get_micros(browser, index)
                    if len(micros_urls) == 0:
                        await create_micro_asset(browser, index, data_row, macro_id, report_id)
                        await browser.tabs[index].sleep(2)
                    micros_urls = await get_micros(browser, index)

                micro_url = micros_urls[0]
                micro_id = micros_urls[0].split("/")[-2]
                print(f"{macro_id} {micro_id} created")
                await edit_micro_asset(browser, index, data_row, report_id, macro_id, micro_id)
                print(f"{macro_id} {micro_id} edited")

                cursor = conn.cursor()
                cursor.execute("UPDATE assets SET submitState = '1', micro_url = ?, microid = ? WHERE id = ?", 
                              (micro_url, micro_id, data_row['id']))
                conn.commit()
                print(f"{macro_id} {micro_id} saved")
            except Exception as e:
                print(f"{macro_id} Failed: {str(e)}")
            finally:
                empty_indexes[index - bb] = 1

    for i in range(browsers_num):
        page = await browser.get("", new_tab=True)

    tasks = []
    b = browsers_num // 2
    bb = b + browsers_num % 2
    semaphore = asyncio.Semaphore(bb)
    empty_indexes = [1 for i in range(bb)]

    for data_row, url in macros_data_urls:
        if data_row['submitState'] == 0:
            tasks.append(limited_task(data_row, url))

    await asyncio.gather(*tasks)
    for i in range(browsers_num, 0, -1):
        await browser.tabs[i].close()

    cursor.execute("UPDATE reports SET submitState = '1' WHERE id = ?", (report_data['id'],))
    conn.commit()
    print("Finished")

def fetch_table_from_db(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    columns = [desc[0] for desc in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return rows

async def submit_reports(report_internal_id, conn=None, browsers_num=5):
    global account_data
    if account_data is None:
        with open("scripts/account.json", "r") as f:
            account_data = json.load(f)

    if conn is None:
        conn = sqlite3.connect("scripts/report_submit_db.db")
        close_conn = True
    else:
        close_conn = False

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE id = ?", (report_internal_id,))
    report_row = cursor.fetchone()
    if not report_row:
        if close_conn:
            conn.close()
        raise ValueError(f"No report found with internal ID {report_internal_id}")
    report_data = dict(zip([desc[0] for desc in cursor.description], report_row))

    # Fetch assets with the original report_id (temporary or existing)
    cursor.execute("SELECT * FROM assets WHERE report_id = ?", (report_data['report_id'],))
    assets_data = [dict(zip([desc[0] for desc in cursor.description], row)) for row in cursor.fetchall()]
    if not assets_data:
        if close_conn:
            conn.close()
        raise ValueError(f"No assets found for report with report_id {report_data['report_id']}")

    browser = None
    try:
        browser = await uc.start(user_data_dir="scripts/browser_data", no_sandbox=True)
        print(f"{datetime.now()} Starting submission for report_internal_id {report_internal_id}")

        # Pre-create tabs before starting the process
        # while len(browser.tabs) < browsers_num + 1:
        #     try:
        #         await browser.get("", new_tab=True)
        #         await asyncio.sleep(0.1)  # Small delay to ensure tab creation
        #     except Exception as e:
        #         print(f"{datetime.now()} Error creating tab: {str(e)}")
        #         raise
        # print(f"{datetime.now()} Pre-created {len(browser.tabs)} tabs")

        await login(browser)  # Will reuse cookies if already logged in
        cookies = await get_cookies(browser)
        if not cookies:
            raise Exception("No cookies retrieved after login")
        print(f"{datetime.now()} Logged in successfully")

        # Ensure tab 0 is active for report creation
        await browser.tabs[0].activate()
        await browser.tabs[0].sleep(1)
        print(f"{datetime.now()} Tab 0 activated for report creation")

        await add_report(browser, report_data, assets_data, conn, browsers_num)  # Pass browsers_num
        print(f"{datetime.now()} Report and assets submitted successfully")

        # Final update to ensure consistency
        cursor.execute("UPDATE reports SET submitState = 1 WHERE id = ?", (report_internal_id,))
        cursor.execute("UPDATE assets SET submitState = 1 WHERE report_id = ?", (report_data['report_id'],))
        conn.commit()
        print(f"{datetime.now()} Database updated successfully")
        return True

    except Exception as e:
        print(f"{datetime.now()} Error in submit_reports: {str(e)}")
        raise

    finally:
        # Ensure browser cleanup with a timeout
        if browser is not None:
            try:
                # Close all tabs with a timeout
                async def close_tabs():
                    for i in range(len(browser.tabs) - 1, -1, -1):
                        try:
                            print(f"{datetime.now()} Closing tab {i}")
                            await browser.tabs[i].close()
                            await asyncio.sleep(0.1)  # Small delay to avoid overwhelming the browser
                        except Exception as e:
                            print(f"{datetime.now()} Failed to close tab {i}: {str(e)}")

                # Run tab closure with a 10-second timeout
                await asyncio.wait_for(close_tabs(), timeout=10)

                # Stop the browser with a 5-second timeout
                print(f"{datetime.now()} Stopping browser")
                await asyncio.wait_for(browser.stop(), timeout=5)
                print(f"{datetime.now()} Browser stopped successfully")

            except asyncio.TimeoutError:
                print(f"{datetime.now()} Timeout during browser cleanup; forcing browser stop")
                try:
                    browser.stop()  # Force stop without await
                except:
                    print(f"{datetime.now()} Warning: Failed to force-stop browser")
            except Exception as e:
                print(f"{datetime.now()} Error during browser cleanup: {str(e)}")
                try:
                    browser.stop()  # Force stop without await
                except:
                    print(f"{datetime.now()} Warning: Failed to force-stop browser after error")

        # Close the database connection
        if close_conn:
            try:
                conn.close()
                print(f"{datetime.now()} Database connection closed")
            except Exception as e:
                print(f"{datetime.now()} Error closing database connection: {str(e)}")

        print(f"{datetime.now()} Browser stopped and connection closed")

async def assets_upload(report_id, browsers_num=5):
    global account_data

    # Load account data if needed
    if account_data is None:
        with open("scripts/account.json", "r") as f:
            account_data = json.load(f)

    # Connect to the local DB and fetch assets for the report
    conn = sqlite3.connect("scripts/report_submit_db.db", check_same_thread=True)
    cursor = conn.cursor()
    browser = None
    try:
        # Fetch assets
        cursor.execute("SELECT * FROM assets")
        columns = [desc[0] for desc in cursor.description]
        assets_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        if not assets_data:
            raise Exception("No assets found in the assets table")

        # Normalize data
        assets_data = await fix_data(assets_data)

        # Start browser and login
        browser = await uc.start(user_data_dir="scripts/browser_data", no_sandbox=True)
        await login(browser)
        cookies = await get_cookies(browser)
        if not cookies:
            raise Exception("No cookies retrieved after login")

        # Activate tab 0
        await browser.tabs[0].activate()
        await browser.tabs[0].sleep(1)

        # Navigate to report page
        report_url = f"https://qima.taqeem.sa/report/{report_id}"
        await go_to_url(browser, 0, report_url)
        await browser.tabs[0].sleep(5)

        # Step 1: Fetch existing macros once
        macros_urls_exists = None
        for attempt in range(3):
            try:
                macros_urls_exists = await get_macros(browser, str(report_id), [{'macroid': 0}], 1)
                current_num = len(macros_urls_exists)
                print(f"{datetime.now()} Step 1: macros on website = {current_num}")
                break
            except Exception as e:
                print(f"{datetime.now()} Step 1: fetch attempt {attempt+1} failed: {str(e)}")
                await browser.tabs[0].reload()
                await browser.tabs[0].sleep(2)
        if attempt == 2:
            raise Exception("Failed to fetch macros")

        num_assets = len(assets_data)
        print(f"{datetime.now()} Step 1: total assets in DB = {num_assets}")

        needed = max(0, num_assets - current_num)
        if needed > 0:
            print(f"{datetime.now()} Step 1: Need to create {needed} more assets")
            batch_size = 10
            num_batches = (needed + batch_size - 1) // batch_size
            concurrency = 10  # Fixed to 10 tabs for parallel creation

            # Pre-create 10 tabs for creation
            creation_tabs = []
            for _ in range(concurrency):
                new_tab = await browser.get("", new_tab=True)
                creation_tabs.append(new_tab)
            print(f"{datetime.now()} Step 1: pre-created {concurrency} tabs for parallel creation")

            semaphore = asyncio.Semaphore(concurrency)

            async def create_batch(tab_idx, batches_for_tab):
                async with semaphore:
                    tab = creation_tabs[tab_idx]
                    for to_create in batches_for_tab:
                        for retry in range(3):
                            try:
                                create_url = f"https://qima.taqeem.sa/report/asset/create/{report_id}"
                                await go_to_url(browser, tab_idx + 1, create_url)  # Tabs start from 1
                                await tab.sleep(2)

                                form_sel = "form[action='https://qima.taqeem.sa/report/ME_asset']"
                                await tab.select(form_sel, timeout=120)

                                macros_input = None
                                try:
                                    macros_input = await tab.select(f"{form_sel} input#macros", timeout=60)
                                except:
                                    macros_input = await tab.select(f"{form_sel} input[name='macros']", timeout=60)
                                await macros_input.clear_input()
                                await macros_input.send_keys(str(to_create))
                                print(f"{datetime.now()} Step 1: Tab {tab_idx+1} set macros to {to_create}")

                                submit_button = await tab.select(f"{form_sel} input[type='submit']", timeout=60)
                                await submit_button.click()
                                print(f"{datetime.now()} Step 1: Tab {tab_idx+1} form submitted")

                                await tab.sleep(5)  # Wait for auto redirect
                                break
                            except Exception as e:
                                print(f"{datetime.now()} Step 1: Tab {tab_idx+1} retry {retry+1} failed: {str(e)}")
                                if retry < 2:
                                    await tab.reload()
                                    await tab.sleep(2)

            # Distribute batches across tabs
            tasks = []
            batches_per_tab = [[] for _ in range(concurrency)]
            batch_index = 0
            while batch_index < num_batches:
                for tab_idx in range(concurrency):
                    if batch_index >= num_batches:
                        break
                    to_create = min(batch_size, needed - batch_index * batch_size)
                    batches_per_tab[tab_idx].append(to_create)
                    batch_index += 1

            for tab_idx, batches in enumerate(batches_per_tab):
                if batches:
                    tasks.append(create_batch(tab_idx, batches))

            await asyncio.gather(*tasks)

            # Close creation tabs
            for i in range(concurrency - 1, -1, -1):
                try:
                    await creation_tabs[i].close()
                except:
                    pass

            # Refetch macros after creation
            await go_to_url(browser, 0, report_url)
            await browser.tabs[0].sleep(5)
            for attempt in range(3):
                try:
                    macros_urls_exists = await get_macros(browser, str(report_id), [{'macroid': 0}], browsers_num)
                    print(f"{datetime.now()} Step 2: fetched {len(macros_urls_exists)} macros after creation")
                    break
                except Exception as e:
                    print(f"{datetime.now()} Step 2: refetch attempt {attempt+1} failed: {str(e)}")
                    await browser.tabs[0].reload()
                    await browser.tabs[0].sleep(2)
            if attempt == 2:
                raise Exception("Failed to refetch macros after creation")

        else:
            print(f"{datetime.now()} Step 1: Assets already equal, no creation needed")

        if len(macros_urls_exists) < num_assets:
            raise Exception("Insufficient assets")

        # Step 3: map assets to macros
        macros_data_urls = list(zip(assets_data, macros_urls_exists[:num_assets]))

        # Pre-create tabs for editing
        for _ in range(browsers_num):
            await browser.get("", new_tab=True)
        print(f"{datetime.now()} Step 3: pre-created {len(browser.tabs)} tabs total for editing")

        # Edit in parallel with robust retries
        b = browsers_num // 2
        bb = b + browsers_num % 2
        semaphore = asyncio.Semaphore(bb)
        empty_indexes = [1 for _ in range(bb)]
        successes = 0
        failures = 0

        async def limited_edit_task(data_row, url):
            nonlocal successes, failures
            async with semaphore:
                async with lock1:
                    idx = await get_empty_index(empty_indexes) + bb
                    empty_indexes[idx - bb] = 0
                macro_id = url.split("/")[-2]
                print(f"{datetime.now()} Step 3: editing macro {macro_id} on tab {idx}")
                for retry in range(3):
                    try:
                        await edit_macro(browser, idx, data_row, str(report_id), macro_id, browsers_num)
                        successes += 1
                        print(f"{datetime.now()} Step 3: macro {macro_id} edited successfully")
                        break
                    except Exception as e:
                        print(f"{datetime.now()} Step 3: macro {macro_id} retry {retry+1} failed: {str(e)}")
                        if retry < 2:
                            await browser.tabs[idx].reload()
                            await browser.tabs[idx].sleep(2)
                        else:
                            failures += 1
                empty_indexes[idx - bb] = 1

        edit_tasks = [limited_edit_task(d, u) for d, u in macros_data_urls]
        await asyncio.gather(*edit_tasks)

        # Close tabs and browser
        for i in range(len(browser.tabs) - 1, -1, -1):
            try:
                await browser.tabs[i].close()
            except:
                pass
        try:
            await browser.stop()
        except:
            pass

        return {"success": True, "processed": len(macros_data_urls), "successes": successes, "failures": failures}

    finally:
        try:
            if browser is not None:
                await browser.stop()
        except:
            pass
        try:
            conn.close()
        except Exception:
            pass

async def delete_macro(browser, index, macro_id):
    await go_to_url(browser, index, f"https://qima.taqeem.sa/report/macro/{macro_id}/delete")
    # page = await browser.get(f"https://qima.taqeem.sa/report/macro/{macro_id}/delete")

async def delete_report(report_id):
    # conn = sqlite3.connect("scripts/report_submit_db.db")
    cursor = conn.cursor()
    assets_data = fetch_table_from_db(conn, "assets")
    # reports = fetch_table_from_db(conn, "reports")
    semaphore = asyncio.Semaphore(browsers_num)
    
    if int(report_id) == 0:
        return

    browser = await uc.start(
        user_data_dir="user_data",
        no_sandbox=True,
    )

    page = await login(browser)
    
    page = await browser.get(f"https://qima.taqeem.sa/report/{report_id}")
    await page.sleep(2)
    do_delete = await page.find("//div[@class='d-flex pt-sm fs-xs']/b[text()='مسودة']", timeout=120)

    if do_delete is None:
        print("Not allowed to delete.")
        return

    try:
        await (await page.select('button[id="delete_report"]')).click()
    except:
        ...

    # for report in reports:
    #     # if report["id"] == report_line_id:
    #     if report["report_id"] == int(report_id):
    #         # report_id = report["report_id"]
    #         report_line_id = report["id"]
    #         break
    # else:
    #     return
    
    # assosiated_assets = [
    #     asset
    #     for asset in assets
    #     if int(asset["pageno"]) == int(report_line_id)
    # ]

    assets_urls = await get_macros(browser, report_id, assets_data,browsers_num)

    # if len(assosiated_assets):
    #     for i, asset in enumerate(assosiated_assets):
    #         if int(asset["submitState"]) == 1:
    #             asset_to_keep = assosiated_assets.pop(i)
    #             break
    #     else:
    #         # asset_to_keep = assosiated_assets.pop(0)
    if not len(assets_urls):
        await create_asset(browser, 0, 1, report_id)
        assets_urls = await get_macros(browser, report_id, assets_data,browsers_num)

    asset_to_keep = {
            'macroid': assets_urls[0].split("/")[-2],
            'asset_type': 'طفاية',
            'asset_name': 'Fire Extinguisher',
            'asset_usage_id': '42',
            'value_base': '1',
            'inspection_date': '2024-03-06',
            'final_value': '150',
            'production_capacity': '0',
            'production_capacity_measuring_unit': '0',
            'owner_name': '0',
            'product_type': '0',
            'market_approach': '1',
            'market_approach_value': '150',
            'cost_approach': '1',
            'cost_approach_value': '150',
            'country': 'المملكة العربية السعودية',
            'region': 'منطقة الرياض',
            'city': 'الرياض',
        }
    
    macroid = assets_urls[0].split("/")[-2]

    for _ in range(browsers_num):
        page = await browser.get("", new_tab=True)
    
    b = browsers_num // 2
    index = (browsers_num % (b + browsers_num % 2)) + b + 1
    await edit_macro(browser, index, asset_to_keep, report_id, macroid , browsers_num)

    # for i in range(browsers_num, 0, -1):
    #     # await browser.tabs[i].sleep(.1)
    #     await browser.tabs[i].close()

# TODO
# files = {
#     '_method': (None, 'PUT'),
#     '_token': (None, '0Ti1bbECNQ1KFVBcBbjMzqHyBXQZfLmGwEzXpvtB'),
#     'confirmed_by': (None, '144'),
#     'delete': (None, 'حذف التقرير'),
# }

# response = requests.post('https://qima.taqeem.sa/report/1314649', cookies=cookies, headers=headers, files=files)

    # if int(data_row["microid"]) != 0:
    #     micros_urls = [f'https://qima.taqeem.sa/report/micro/{data_row["microid"]}/edit']
    # else:
    #     micros_urls = await get_micros(browser, index)

    #     if len(micros_urls) == 0:
    #         await create_micro_asset(browser, index, data_row, macro_id, report_id)
    #         await browser.tabs[index].sleep(2)

    #     micros_urls = await get_micros(browser, index)

    # print(micros_urls)
    
    # micro_id = micros_urls[0].split("/")[-2]
    # await edit_micro_asset(browser, index, data_row, report_id, macro_id, micro_id)

    empty_indexes = [1 for i in range(browsers_num)]

    async def limited_task(macroid):
        async with semaphore:
            async with lock1:
                index = await get_empty_index(empty_indexes) + 1
                empty_indexes[index - 1] = 0

            await delete_macro(browser, index, macroid)
            await browser.tabs[index].sleep(1)

            cursor.execute("DELETE FROM assets WHERE macroid = ?", (macroid,))
            conn.commit()

            empty_indexes[index - 1] = 1

    # for i in range(browsers_num):
    #     page = await browser.get("", new_tab=True)
    
    tasks = []
    for i, url in enumerate(assets_urls[1:]): # skip the first full macri to allow report removal
        macroid = url.split("/")[-2]
        tasks.append(limited_task(macroid))
        
        # if len(tasks) == browsers_num:
        #     await asyncio.gather(*tasks)
        #     tasks = []

    # if len(tasks):
    await asyncio.gather(*tasks)
    
    for j in range(browsers_num, 0, -1):
        await browser.tabs[j].close()


    page = await browser.get(f"https://qima.taqeem.sa/report/{report_id}")
    await page.sleep(2)
    await (await page.select('button[id="delete_report"]')).click()

    browser.stop()
    print("Finished")

    cursor.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
    conn.commit()

    return True

async def check_final_values(report_id, browsers_num=5):
    """
    Check and sum the 'Final Value' (الرأي النهائي في القيمة) for all macros in a specific report,
    then export the results to an Excel file.
    
    Args:
        report_id (str): The ID of the report to check (e.g., '1354661').
        browsers_num (int): Number of browser tabs to use for parallel processing (default: 5).
    
    Returns:
        dict: A dictionary containing:
            - total_final_value (float): The sum of all final values.
            - final_values (list): A list of dictionaries with macroid and their final values.
            - excel_file (str): Path to the exported Excel file.
            - error (str): Any error message if the process fails.
    """
    global account_data

    # Load account data if not already loaded
    if account_data is None:
        with open("scripts/account.json", "r") as f:
            account_data = json.load(f)

    # Initialize variables
    total_final_value = 0.0
    final_values_list = []  # To store macroid and final value pairs
    error_message = None
    excel_file_path = None

    # Create a new connection for this request
    conn = sqlite3.connect("scripts/report_submit_db.db", check_same_thread=True)
    browser = None

    print(f"{datetime.now()} Starting browser for report_id {report_id}... (browsers_num={browsers_num})")
    browser = await uc.start(user_data_dir="scripts/browser_data")
    try:
        # Log in to the website
        print(f"{datetime.now()} Attempting login for report_id {report_id}...")
        await login(browser)
        cookies = await get_cookies(browser)
        if not cookies:
            raise Exception("No cookies retrieved after login")
        print(f"{datetime.now()} Logged in successfully, cookies retrieved: {len(cookies)} cookies.")

        # Pre-create browser tabs
        current_tabs = len(browser.tabs)
        target_tabs = browsers_num + 1
        print(f"{datetime.now()} Current tabs: {current_tabs}, Target tabs: {target_tabs}")
        while len(browser.tabs) < target_tabs:
            await browser.get("", new_tab=True)
        print(f"{datetime.now()} Pre-created {len(browser.tabs)} tabs")

        # Navigate to the report page
        report_url = f"https://qima.taqeem.sa/report/{report_id}"
        print(f"{datetime.now()} Navigating to report page: {report_url}")
        await go_to_url(browser, 0, report_url)
        await browser.tabs[0].sleep(1)
        print(f"{datetime.now()} Report page loaded.")

        # Get the total number of pages
        pages_num = await get_macro_pages_num(browser, report_id)
        print(f"{datetime.now()} Total pages in report {report_id}: {pages_num}")

        # Collect all macro URLs across all pages
        macros_urls = []
        semaphore = asyncio.Semaphore(browsers_num)
        empty_indexes = [1 for _ in range(browsers_num)]

        async def fetch_macros_from_page(page_no):
            async with semaphore:
                async with lock1:
                    index = await get_empty_index(empty_indexes)
                    if index >= browsers_num:
                        index = 0
                    empty_indexes[index] = 0

                page_url = f"https://qima.taqeem.sa/report/{report_id}?page={page_no}"
                print(f"{datetime.now()} Fetching macros from page {page_no} (URL: {page_url}) on tab {index + 1}")
                retry_count = 0
                while retry_count < 3:
                    try:
                        await go_to_url(browser, index + 1, page_url)
                        page_macros = await get_macros_from_page(browser, index + 1)
                        print(f"{datetime.now()} Found {len(page_macros)} macros on page {page_no}")
                        macros_urls.extend(page_macros)
                        break
                    except Exception as e:
                        retry_count += 1
                        print(f"{datetime.now()} Retry {retry_count} for page {page_no}: {str(e)}")
                        await browser.tabs[index + 1].reload()
                        await asyncio.sleep(0.2)
                else:
                    print(f"{datetime.now()} Failed to fetch macros from page {page_no} after 3 retries")

                empty_indexes[index] = 1

        print(f"{datetime.now()} Collecting macro URLs in parallel across {pages_num} pages...")
        tasks = [fetch_macros_from_page(page_no) for page_no in range(1, pages_num + 1)]
        await asyncio.gather(*tasks)
        macros_urls = list(set(macros_urls))  # Remove duplicates
        print(f"{datetime.now()} Found {len(macros_urls)} unique macro URLs for report {report_id}.")

        # Process each macro to extract the final value
        async def extract_final_value(macro_url):
            async with semaphore:
                async with lock1:
                    index = await get_empty_index(empty_indexes)
                    if index >= browsers_num:
                        index = 0
                    empty_indexes[index] = 0

                macro_id = macro_url.split('/')[-2]
                show_url = macro_url.replace("edit", "show")
                print(f"{datetime.now()} Extracting final value for macro {macro_id} (URL: {show_url}) on tab {index + 1}")
                retry_count = 0
                final_value = 0.0
                while retry_count < 3:
                    try:
                        # Navigate to the macro's show page to extract the final value
                        await go_to_url(browser, index + 1, show_url)
                        await browser.tabs[index + 1].sleep(0.5)

                        # Extract the final value from the page
                        html_content = await browser.tabs[index + 1].get_content()
                        if html_content is None:
                            raise Exception("Content is None")

                        # Try the table structure first
                        table_pattern = r'<table[^>]*class="table"[^>]*>.*?<thead>.*?<th[^>]*>الرأي النهائي</th>.*?<tbody>(.*?)</tbody>'
                        table_match = re.search(table_pattern, html_content, re.DOTALL | re.UNICODE)
                        if table_match:
                            tbody_content = table_match.group(1)
                            print(f"{datetime.now()} Macro {macro_id} - Matched table tbody: {tbody_content[:500]}")
                            # Extract the value from the 4th column
                            row_pattern = r'<tr[^>]*>.*?(?:<td[^>]*>.*?</td>){3}<td[^>]*>\s*(\d+\.?\d*)\s*</td>.*?</tr>'
                            matches = re.findall(row_pattern, tbody_content, re.DOTALL | re.UNICODE)
                            if matches:
                                print(f"{datetime.now()} Macro {macro_id} - Found final values in table: {matches}")
                                for value in matches:
                                    final_value = float(value)
                                    if final_value != 0.0:
                                        break
                                print(f"{datetime.now()} Macro {macro_id} - Selected final value from table: {final_value}")
                                final_values_list.append({"macroid": macro_id, "final_value": final_value})
                                break

                        # Try the full label anywhere in the HTML
                        full_label_pattern = r'الرأي النهائي في القيمة.*?(?:<td[^>]*>|<div[^>]*class="col-md-6"[^>]*>)\s*(\d+\.?\d*)\s*(?:</td>|</div>)'
                        matches = re.findall(full_label_pattern, html_content, re.DOTALL | re.UNICODE)
                        if matches:
                            print(f"{datetime.now()} Macro {macro_id} - Found final values with full label: {matches}")
                            for value in matches:
                                final_value = float(value)
                                if final_value != 0.0:
                                    break
                            print(f"{datetime.now()} Macro {macro_id} - Selected final value with full label: {final_value}")
                            final_values_list.append({"macroid": macro_id, "final_value": final_value})
                            break

                        # If no value is found, log a snippet of the HTML for debugging
                        print(f"{datetime.now()} Final value not found for macro {macro_id}, defaulting to 0.0")
                        html_snippet = html_content[:1000]  # First 1000 characters
                        print(f"{datetime.now()} HTML snippet for macro {macro_id}: {html_snippet}")
                        final_value = 0.0
                        final_values_list.append({"macroid": macro_id, "final_value": final_value})
                        break

                    except Exception as e:
                        retry_count += 1
                        print(f"{datetime.now()} Retry {retry_count} for macro {macro_id}: {str(e)}")
                        await browser.tabs[index + 1].reload()
                        await asyncio.sleep(0.2)
                else:
                    print(f"{datetime.now()} Failed to extract final value for macro {macro_id} after 3 retries, defaulting to 0.0")
                    final_values_list.append({"macroid": macro_id, "final_value": 0.0})

                empty_indexes[index] = 1

        print(f"{datetime.now()} Extracting final values for {len(macros_urls)} macros in parallel...")
        tasks = [extract_final_value(url) for url in macros_urls]
        await asyncio.gather(*tasks)

        # Sum all final values
        total_final_value = sum(item["final_value"] for item in final_values_list)
        print(f"{datetime.now()} Total final value for report {report_id}: {total_final_value}")

        # Export to Excel
        if final_values_list:
            df = pd.DataFrame(final_values_list)
            excel_file_path = f"scripts/report_{report_id}_final_values.xlsx"
            df.to_excel(excel_file_path, index=False)
            print(f"{datetime.now()} Exported final values to {excel_file_path}")

    except Exception as e:
        error_message = str(e)
        print(f"{datetime.now()} Error in check_final_values for report {report_id}: {error_message}")

    finally:
        # Clean up browser and database connection
        if browser is not None:
            for i in range(len(browser.tabs) - 1, -1, -1):
                try:
                    await browser.tabs[i].close()
                except:
                    pass
            try:
                await browser.stop()
            except:
                print(f"{datetime.now()} Warning: Failed to stop browser cleanly")
        conn.close()
        print(f"{datetime.now()} Browser stopped and database connection closed.")

    return {
        "total_final_value": total_final_value,
        "final_values": final_values_list,
        "excel_file": excel_file_path,
        "error": error_message
    }

async def check_incomplete_assets(report_id, browsers_num):
    global account_data

    if account_data is None:
        with open("scripts/account.json", "r") as f:
            account_data = json.load(f)

    macro_count = 0
    micro_count = 0
    both_count = 0

    # Create a new connection for this request
    conn = sqlite3.connect("scripts/report_submit_db.db", check_same_thread=True)
    browser = None  # Initialize browser as None to avoid unbound variable issues

    print(f"{datetime.now()} Starting browser... (browsers_num={browsers_num})")
    browser = await uc.start(user_data_dir="scripts/browser_data")
    try:
        print(f"{datetime.now()} Attempting login...")
        await login(browser)
        cookies = await get_cookies(browser)
        if not cookies:
            raise Exception("No cookies retrieved after login")
        print(f"{datetime.now()} Logged in, cookies retrieved: {len(cookies)} cookies.")

        current_tabs = len(browser.tabs)
        target_tabs = browsers_num + 1
        print(f"{datetime.now()} Current tabs: {current_tabs}, Target tabs: {target_tabs}")
        while len(browser.tabs) < target_tabs:
            await browser.get("", new_tab=True)
        print(f"{datetime.now()} Pre-created {len(browser.tabs)} tabs")

        print(f"{datetime.now()} Navigating to report page: https://qima.taqeem.sa/report/{report_id}")
        await go_to_url(browser, 0, f"https://qima.taqeem.sa/report/{report_id}")
        await browser.tabs[0].sleep(1)
        print(f"{datetime.now()} Report page loaded.")

        pages_num = await get_macro_pages_num(browser, report_id)
        print(f"{datetime.now()} Total pages: {pages_num}")

        macros_urls = []
        semaphore = asyncio.Semaphore(browsers_num)
        empty_indexes = [1 for _ in range(browsers_num)]

        async def fetch_macros_from_page(page_no):
            async with semaphore:
                async with lock1:
                    index = await get_empty_index(empty_indexes)
                    if index >= browsers_num:
                        index = 0
                    empty_indexes[index] = 0

                print(f"{datetime.now()} Fetching macros from page {page_no} on tab {index + 1}")
                retry_count = 0
                while retry_count < 3:
                    try:
                        await go_to_url(browser, index + 1, f"https://qima.taqeem.sa/report/{report_id}?page={page_no}")
                        page_macros = await get_macros_from_page(browser, index + 1)
                        macros_urls.extend(page_macros)
                        break
                    except Exception as e:
                        retry_count += 1
                        print(f"{datetime.now()} Retry {retry_count} for page {page_no}: {str(e)}")
                        await browser.tabs[index + 1].reload()
                        await asyncio.sleep(0.2)
                else:
                    print(f"{datetime.now()} Failed to fetch macros from page {page_no} after 3 retries")

                empty_indexes[index] = 1

        print(f"{datetime.now()} Collecting macro URLs in parallel...")
        tasks = [fetch_macros_from_page(page_no) for page_no in range(1, pages_num + 1)]
        await asyncio.gather(*tasks)
        macros_urls = list(set(macros_urls))
        print(f"{datetime.now()} Found {len(macros_urls)} unique macro URLs.")

        async def check_macro(macro_url):
            nonlocal macro_count, micro_count, both_count
            async with semaphore:
                async with lock1:
                    index = await get_empty_index(empty_indexes)
                    if index >= browsers_num:
                        index = 0
                    empty_indexes[index] = 0

                macro_id = macro_url.split('/')[-2]
                show_url = macro_url.replace("edit", "show")
                print(f"{datetime.now()} Checking macro {macro_id} on tab {index + 1}")
                retry_count = 0
                while retry_count < 3:
                    try:
                        await go_to_url(browser, index + 1, show_url)
                        await browser.tabs[index + 1].sleep(0.5)
                        html_content = await browser.tabs[index + 1].get_content()
                        if html_content is None:
                            raise Exception("Content is None")
                        incomplete_count = html_content.count("غير مكتملة")

                        if incomplete_count >= 2:
                            macro_count += 1
                            micro_count += 1
                            both_count += 1
                        elif incomplete_count == 1:
                            print(f"{datetime.now()} Fetching micros for macro {macro_id}")
                            micro_urls = await get_micros(browser, index + 1)
                            if not micro_urls:
                                print(f"{datetime.now()} No micro URLs for macro {macro_id}")
                                macro_count += 1
                            elif micro_urls[0]:
                                micro_url = micro_urls[0].replace("edit", "show")
                                await go_to_url(browser, index + 1, micro_url)
                                await browser.tabs[index + 1].sleep(0.5)
                                micro_content = await browser.tabs[index + 1].get_content()
                                if micro_content is None:
                                    raise Exception("Micro content is None")
                                if "غير مكتملة" in micro_content:
                                    micro_count += 1
                                elif "مكتملة" in micro_content:
                                    macro_count += 1
                            else:
                                macro_count += 1

                        cursor = conn.cursor()
                        cursor.execute("UPDATE assets SET submitState = ? WHERE macroid = ?", 
                                       (1 if incomplete_count == 0 else 0, macro_id))
                        conn.commit()
                        break
                    except Exception as e:
                        retry_count += 1
                        print(f"{datetime.now()} Retry {retry_count} for macro {macro_id}: {str(e)}")
                        await browser.tabs[index + 1].reload()
                        await asyncio.sleep(0.2)
                else:
                    print(f"{datetime.now()} Failed to check macro {macro_id} after 3 retries")

                empty_indexes[index] = 1

        print(f"{datetime.now()} Checking macros in parallel...")
        tasks = [check_macro(url) for url in macros_urls]
        await asyncio.gather(*tasks)

        cursor = conn.cursor()
        submit_state = 1 if macro_count == 0 and micro_count == 0 and both_count == 0 else 0
        cursor.execute("""
            UPDATE reports 
            SET macro_count = ?, micro_count = ?, both_count = ?, submitState = ?
            WHERE report_id = ?
        """, (macro_count, micro_count, both_count, submit_state, report_id))
        conn.commit()
        print(f"{datetime.now()} Database updated: macro_count={macro_count}, micro_count={micro_count}, both_count={both_count}, submitState={submit_state}")

    except Exception as e:
        print(f"{datetime.now()} Error in check_incomplete_assets: {str(e)}")
        # Return a default result instead of raising to ensure views.py gets a response
        return {"macro_count": macro_count, "micro_count": micro_count, "both_count": both_count}
    finally:
        if browser is not None:  # Check if browser is valid before operating on it
            for i in range(len(browser.tabs) - 1, -1, -1):
                try:
                    await browser.tabs[i].close()
                except:
                    pass
            try:
                await browser.stop()
            except:
                print(f"{datetime.now()} Warning: Failed to stop browser cleanly")
        conn.close()  # Close the connection
        print(f"{datetime.now()} Browser stopped and connection closed.")

    return {"macro_count": macro_count, "micro_count": micro_count, "both_count": both_count}

async def proceed_to_next_page(browser, index, selector, asyncfunc=None):

    for attempt in range(5):
        # AscendingRetry(attempt + 1):  # Removed undefined reference
        try:
            # Wait for the selector to be present
            await browser.tabs[index].select(selector, timeout=60)
            if asyncfunc is not None:
                await asyncfunc
            # Try to find and click the submit button with retries
            for retry in range(3):
                try:
                    submit_button = await browser.tabs[index].select('input[type="submit"]', timeout=20)  # Increased timeout
                    if submit_button is None:
                        raise Exception("Submit button not found")
                    await submit_button.click()
                    await browser.tabs[index].sleep(5)  # Increased sleep time
                    current_url = await get_tab_url(browser, index)
                    print(f"{datetime.now()} Attempt {attempt + 1}: Page transitioned to {current_url}")
                    return
                except Exception as e:
                    print(f"{datetime.now()} Retry {retry + 1} for submit button: {str(e)}")
                    await browser.tabs[index].reload()
                    await asyncio.sleep(2)
            raise Exception("Failed to proceed to next page after retries")
        except Exception as e:
            print(f"{datetime.now()} Attempt {attempt + 1} failed: {str(e)}")
            await browser.tabs[index].reload()
            await asyncio.sleep(2)
    raise Exception("Failed to proceed to next page after 5 attempts")

async def resubmit_assets(report_id, browsers_num=6):  # Reduced to 6 to lower resource usage
    global account_data

    # Load account data if not already loaded
    if account_data is None:
        with open("scripts/account.json", "r") as f:
            account_data = json.load(f)

    # Create a new database connection
    conn = sqlite3.connect("scripts/report_submit_db.db", check_same_thread=True)
    cursor = conn.cursor()

    # Fetch assets with submitState = 0 for the given report_id
    cursor.execute("""
        SELECT * FROM assets 
        WHERE submitState = 0 AND report_id = (SELECT report_id FROM reports WHERE report_id = ?)
    """, (report_id,))
    columns = [desc[0] for desc in cursor.description]
    assets_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

    if not assets_data:
        print(f"{datetime.now()} No assets with submitState = 0 found for report_id {report_id}")
        conn.close()
        return {"processed": 0, "success": 0, "failed": 0}

    print(f"{datetime.now()} Found {len(assets_data)} assets to resubmit for report_id {report_id}")
    print(f"{datetime.now()} Assets to process: {[asset['id'] for asset in assets_data]}")

    # Calculate tab allocation
    macro_tabs_count = browsers_num // 2
    json_tabs_count = browsers_num - macro_tabs_count
    json_tab_base_index = macro_tabs_count + 1  # JSON tabs start after macro tabs
    print(f"{datetime.now()} Tab allocation: {macro_tabs_count} macro tabs, {json_tabs_count} JSON tabs")

    # Semaphore and lock for JSON tabs
    json_semaphore = asyncio.Semaphore(json_tabs_count)
    json_empty_indexes = [1 for _ in range(json_tabs_count)]
    json_lock = asyncio.Lock()

    async def get_json_tab_index():
        async with json_lock:
            for i, val in enumerate(json_empty_indexes):
                if val == 1:
                    json_empty_indexes[i] = 0
                    return i + json_tab_base_index
            await asyncio.sleep(0.1)
            return await get_json_tab_index()

    # Initialize counters
    processed_count = 0
    success_count = 0
    failed_count = 0

    # Configure browser with user-agent and headers to avoid Cloudflare blocking
    browser_config = {
        "no_sandbox": True,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "headless": False,  # Set to True if you don't need to see the browser
    }
    browser = await uc.start(**browser_config)
    try:
        # Log in using main tab (tab 0)
        print(f"{datetime.now()} Attempting login...")
        await login(browser)
        cookies = await get_cookies(browser)
        if not cookies:
            raise Exception("No cookies retrieved after login")
        print(f"{datetime.now()} Logged in, cookies retrieved: {len(cookies)} cookies.")

        # Pre-create tabs based on browsers_num
        target_tabs = browsers_num + 1  # +1 for the main tab (tab 0)
        while len(browser.tabs) < target_tabs:
            await browser.get("", new_tab=True)
            await asyncio.sleep(0.5)  # Increased delay to avoid overwhelming the browser
        print(f"{datetime.now()} Pre-created {len(browser.tabs)} tabs")

        # Fetch existing macros for the report
        macros_urls_exists = await get_macros(browser, report_id, assets_data, browsers_num)
        print(f"{datetime.now()} Fetched {len(macros_urls_exists)} existing macros")

        # Map assets to macros
        macros_data_urls = []
        used_macro_ids = set()
        for d in assets_data:
            if not macros_urls_exists:
                print(f"{datetime.now()} Creating new macro for asset {d['id']}")
                await create_asset(browser, 0, 1, report_id)
                macros_urls_exists = await get_macros(browser, report_id, assets_data, browsers_num)
                print(f"{datetime.now()} After creation, fetched {len(macros_urls_exists)} macros")
            if not macros_urls_exists:
                print(f"{datetime.now()} Error: No macro available for asset {d['id']}")
                continue
            new_macro_id = macros_urls_exists[0].split("/")[-2]
            while new_macro_id in used_macro_ids and macros_urls_exists:
                macros_urls_exists.pop(0)
                new_macro_id = macros_urls_exists[0].split("/")[-2] if macros_urls_exists else None
            if new_macro_id:
                used_macro_ids.add(new_macro_id)
                macros_urls_exists.pop(0)
                if int(d['macroid']) == 0:
                    cursor.execute("UPDATE assets SET macroid = ? WHERE id = ?", (new_macro_id, d['id']))
                    conn.commit()
                    print(f"{datetime.now()} Assigned macro_id {new_macro_id} to asset {d['id']}")
                macros_data_urls.append((d, f'https://qima.taqeem.sa/report/macro/{new_macro_id}/edit'))
            else:
                print(f"{datetime.now()} Error: No macro available for asset {d['id']} after filtering")

        # Process assets in batches
        semaphore = asyncio.Semaphore(macro_tabs_count)
        empty_indexes = [1 for _ in range(macro_tabs_count)]
        processed_assets = set()
        total_assets = len(macros_data_urls)
        batch_size = macro_tabs_count

        async def recover_tab(tab_index):
            print(f"{datetime.now()} Recovering tab {tab_index} due to failure...")
            try:
                await browser.tabs[tab_index].close()
            except:
                pass
            await browser.get("", new_tab=True, target_tab_index=tab_index)
            print(f"{datetime.now()} Tab {tab_index} recovered successfully")

        async def recover_json_tab(json_tab_index):
            print(f"{datetime.now()} Recovering JSON tab {json_tab_index} due to failure...")
            try:
                await browser.tabs[json_tab_index].close()
            except:
                pass
            await browser.get("", new_tab=True, target_tab_index=json_tab_index)
            async with json_lock:
                json_empty_indexes[json_tab_index - json_tab_base_index] = 1
            print(f"{datetime.now()} JSON tab {json_tab_index} recovered successfully")

        async def try_or_reload_page_limited(browser, tab_index, selector, max_attempts=3):
            for attempt in range(max_attempts):
                try:
                    element = await browser.tabs[tab_index].select(selector, timeout=30)
                    if element:
                        return element
                    print(f"{datetime.now()} Tab {tab_index}: Attempt {attempt + 1}/{max_attempts} - Element {selector} not found, reloading...")
                    await browser.tabs[tab_index].reload()
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"{datetime.now()} Tab {tab_index}: Attempt {attempt + 1}/{max_attempts} failed - {str(e)}, reloading...")
                    await browser.tabs[tab_index].reload()
                    await asyncio.sleep(1)
            raise Exception(f"Failed to find element {selector} after {max_attempts} attempts")

        async def process_asset_task(data_row, url, tab_index_ref):
            nonlocal processed_count, success_count, failed_count
            if data_row['id'] in processed_assets:
                print(f"{datetime.now()} Skipping already processed asset {data_row['id']}")
                return
            retries = 0
            max_retries = 3
            tab_index = None
            try:
                async with semaphore:
                    async with lock1:
                        index = await get_empty_index(empty_indexes)
                        if index >= macro_tabs_count:
                            print(f"{datetime.now()} Error: Invalid index {index}")
                            return
                        tab_index = index + 1
                        tab_index_ref['index'] = tab_index
                        empty_indexes[index] = 0
                        print(f"{datetime.now()} Tab {tab_index}: Selected for asset {data_row['id']}")

                macro_id = url.split("/")[-2]
                print(f"{datetime.now()} Tab {tab_index}: Processing macro {macro_id} for asset {data_row['id']}")

                # Timeout for the entire macro editing process
                try:
                    async with asyncio.timeout(300):  # 5-minute timeout for the entire operation
                        # Step 1: Edit macro with improved error handling
                        try:
                            await asyncio.wait_for(
                                go_to_url(browser, tab_index, url),
                                timeout=30
                            )
                            print(f"{datetime.now()} Tab {tab_index}: Navigated to macro edit page {url}")
                        except asyncio.TimeoutError:
                            raise Exception(f"Timeout navigating to macro edit page {url}")

                        # Random delay to avoid rate limiting
                        await asyncio.sleep(random.uniform(1, 3))

                        try:
                            await asyncio.wait_for(
                                browser.tabs[tab_index].select("input[id='asset_type']", timeout=60),
                                timeout=60
                            )
                            print(f"{datetime.now()} Tab {tab_index}: Found asset_type input for macro {macro_id}")
                        except asyncio.TimeoutError:
                            raise Exception(f"Timeout finding asset_type input for macro {macro_id}")

                        csrf = await try_or_reload_page_limited(
                            browser, tab_index,
                            "form[id='macro_update'] input[name='_token']",
                            max_attempts=3
                        )
                        form_element = await browser.tabs[tab_index].select("form[id='macro_update']", timeout=60)
                        if form_element is None:
                            raise Exception(f"Form 'macro_update' not found for macro {macro_id}")

                        # Fetch country, region, and city IDs
                        country = data_row['country']
                        region = data_row['region']
                        city = data_row['city']

                        page_content = await browser.tabs[tab_index].get_content()
                        if not page_content:
                            raise Exception(f"Failed to get page content for macro {macro_id}")
                        country_matches = re.findall(f'value="(\\d+)".*?>{country}<', page_content)
                        if not country_matches:
                            raise Exception(f"Country '{country}' not found in page content for macro {macro_id}")
                        country_v = int(country_matches[0])

                        async with json_semaphore:
                            json_tab_index = await get_json_tab_index()
                            try:
                                try:
                                    await asyncio.wait_for(
                                        browser.tabs[json_tab_index].get(f"https://qima.taqeem.sa/common/regions?country_id={country_v}"),
                                        timeout=30
                                    )
                                except asyncio.TimeoutError:
                                    raise Exception(f"Timeout fetching regions for country ID {country_v}")
                                # Random delay to avoid rate limiting
                                await asyncio.sleep(random.uniform(1, 3))
                                pre_element = await asyncio.wait_for(
                                    browser.tabs[json_tab_index].select("pre", timeout=60),
                                    timeout=60
                                )
                                json_data = json.loads((await pre_element.get_html())[5:-6])
                                region_v = next((int(k) for k, v in json_data.items() if v == region), None)
                                if region_v is None:
                                    raise Exception(f"Region '{region}' not found for country ID {country_v}")
                            except Exception as e:
                                await recover_json_tab(json_tab_index)
                                raise Exception(f"Failed to fetch regions: {str(e)}")
                            finally:
                                async with json_lock:
                                    json_empty_indexes[json_tab_index - json_tab_base_index] = 1

                        async with json_semaphore:
                            json_tab_index = await get_json_tab_index()
                            try:
                                try:
                                    await asyncio.wait_for(
                                        browser.tabs[json_tab_index].get(f"https://qima.taqeem.sa/common/cities?region_id={region_v}"),
                                        timeout=30
                                    )
                                except asyncio.TimeoutError:
                                    raise Exception(f"Timeout fetching cities for region ID {region_v}")
                                # Random delay to avoid rate limiting
                                await asyncio.sleep(random.uniform(1, 3))
                                pre_element = await asyncio.wait_for(
                                    browser.tabs[json_tab_index].select("pre", timeout=60),
                                    timeout=60
                                )
                                json_data = json.loads((await pre_element.get_html())[5:-6])
                                city_v = next((int(k) for k, v in json_data.items() if v == city), None)
                                if city_v is None:
                                    raise Exception(f"City '{city}' not found for region ID {region_v}")
                            except Exception as e:
                                await recover_json_tab(json_tab_index)
                                raise Exception(f"Failed to fetch cities: {str(e)}")
                            finally:
                                async with json_lock:
                                    json_empty_indexes[json_tab_index - json_tab_base_index] = 1

                        print(f"{datetime.now()} Tab {tab_index}: Retrieved IDs - country={country_v}, region={region_v}, city={city_v}")

                        # Fill and submit macro form
                        await form_element.apply("""
                            (elem) => {
                                elem.innerHTML = `
<input id='asset_type' name='asset_type' value='""" + str(data_row["asset_type"]) + """' />
<input id='asset_name' name='asset_name' value='""" + str(data_row["asset_name"]) + """' />
<input id='asset_usage_id' name='asset_usage_id' value='""" + str(data_row["asset_usage_id"]) + """' />
<input id='value_base_id' name='value_base_id' value='""" + str(data_row["value_base"]) + """' />
<input id='inspected_at' name='inspected_at' value='""" + "-".join(str(data_row["inspection_date"]).split("-")[::-1]) + """' />
<input id='value' name='value' value='""" + str(data_row["final_value"]) + """' />
<input id='production_capacity' name='production_capacity' value='""" + str(data_row["production_capacity"]) + """' />
<input id='production_capacity_measuring_unit' name='production_capacity_measuring_unit' value='""" + str(data_row["production_capacity_measuring_unit"]) + """' />
<input id='owner_name' name='owner_name' value='""" + str(data_row['owner_name']) + """' />
<input id='product_type' name='product_type' value='""" + str(data_row['product_type']) + """' />
<input id='approach' name='approach[1][is_primary]' value='""" + str(data_row['market_approach']) + """' />
<input id='approach' name='approach[1][value]' value='""" + str(data_row['market_approach_value']) + """' />
<input id='approach' name='approach[3][is_primary]' value='""" + str(data_row['cost_approach']) + """' />
<input id='approach' name='approach[3][value]' value='""" + str(data_row['cost_approach_value']) + """' />
<input id='country_id' name='country_id' value='""" + str(country_v) + """' />
<input id='region_id' name='region_id' value='""" + str(region_v) + """' />
<input id='city_id' name='city_id' value='""" + str(city_v) + """' />
<input id='report_id' name='report_id' value='""" + str(report_id) + """' />
<input id="save" class="btn btn-primary" name="update" type="submit" value="حفظ">
""" + await csrf.get_html() + """`;
                            }
                        """)
                        await proceed_to_next_page(browser, tab_index, 'input[name="asset_type"]')
                        print(f"{datetime.now()} Tab {tab_index}: Macro {macro_id} edited successfully")

                        # Step 2: Handle micro
                        micro_id = data_row["microid"] if data_row["microid"] != "0" else None
                        if not micro_id:
                            await create_micro_asset(browser, tab_index, data_row, macro_id, report_id)
                            micros_urls = await get_micros(browser, tab_index)
                            if not micros_urls:
                                raise Exception(f"No micro URLs found for macro {macro_id}")
                            micro_url = micros_urls[0]
                            micro_id = micro_url.split("/")[-2]
                            cursor.execute("UPDATE assets SET microid = ?, micro_url = ? WHERE id = ?",
                                           (micro_id, micro_url, data_row["id"]))
                            conn.commit()
                            print(f"{datetime.now()} Tab {tab_index}: Created micro {micro_id}")
                        else:
                            micro_url = f"https://qima.taqeem.sa/report/micro/{micro_id}/edit"

                        # Edit micro
                        await go_to_url(browser, tab_index, micro_url)
                        await edit_micro_asset(browser, tab_index, data_row, report_id, macro_id, micro_id)
                        print(f"{datetime.now()} Tab {tab_index}: Micro {micro_id} edited successfully")

                        # Update database
                        cursor.execute("UPDATE assets SET submitState = 1 WHERE id = ?", (data_row["id"],))
                        conn.commit()
                        async with lock1:
                            processed_assets.add(data_row['id'])
                            processed_count += 1
                            success_count += 1
                        print(f"{datetime.now()} Tab {tab_index}: Successfully resubmitted asset {data_row['id']}")
                        return  # Success, exit the retry loop

                except asyncio.TimeoutError:
                    raise Exception(f"Overall timeout (5 minutes) exceeded while processing macro {macro_id}")

            except Exception as e:
                retries += 1
                print(f"{datetime.now()} Tab {tab_index}: Retry {retries}/{max_retries} failed for asset {data_row['id']}: {str(e)}")
                if retries >= max_retries:
                    async with lock1:
                        processed_count += 1
                        failed_count += 1
                        processed_assets.add(data_row['id'])
                    print(f"{datetime.now()} Tab {tab_index}: Max retries reached for asset {data_row['id']}")
                    await recover_tab(tab_index)
                else:
                    await browser.tabs[tab_index].reload()
                    await asyncio.sleep(0.2)

            finally:
                if tab_index is not None:
                    async with lock1:
                        empty_indexes[tab_index - 1] = 1

        # Process assets in batches with browser restart on freeze
        for batch_start in range(0, total_assets, batch_size):
            batch_end = min(batch_start + batch_size, total_assets)
            batch_tasks = []
            tab_indices = []

            for i, (data_row, url) in enumerate(macros_data_urls[batch_start:batch_end]):
                if data_row['id'] in processed_assets:
                    continue
                tab_index_ref = {'index': None}
                task = process_asset_task(data_row, url, tab_index_ref)
                batch_tasks.append(task)
                tab_indices.append(tab_index_ref)

            if not batch_tasks:
                print(f"{datetime.now()} No more assets to process in batch starting at index {batch_start}")
                continue

            print(f"{datetime.now()} Processing batch {batch_start} to {batch_end} with {len(batch_tasks)} tasks")
            try:
                await asyncio.gather(*batch_tasks)
            except Exception as e:
                print(f"{datetime.now()} Batch {batch_start} to {batch_end} encountered an error: {str(e)}")
                # Check if browser is frozen by attempting a simple operation
                try:
                    await browser.tabs[0].get("about:blank", timeout=10)
                except asyncio.TimeoutError:
                    print(f"{datetime.now()} Browser appears to be frozen, restarting...")
                    for i in range(len(browser.tabs) - 1, -1, -1):
                        try:
                            await browser.tabs[i].close()
                        except:
                            pass
                    await browser.stop()
                    browser = await uc.start(**browser_config)
                    # Re-login
                    await login(browser)
                    cookies = await get_cookies(browser)
                    if not cookies:
                        raise Exception("No cookies retrieved after login on browser restart")
                    # Recreate tabs
                    while len(browser.tabs) < target_tabs:
                        await browser.get("", new_tab=True)
                        await asyncio.sleep(0.5)
                    print(f"{datetime.now()} Browser restarted and {len(browser.tabs)} tabs recreated")
                # Recover any stuck tabs
                for tab_index_ref in tab_indices:
                    if tab_index_ref['index'] is not None:
                        await recover_tab(tab_index_ref['index'])
            print(f"{datetime.now()} Completed batch {batch_start} to {batch_end}")

        # Verify all assets have been processed
        unprocessed_assets = [data_row['id'] for data_row, _ in macros_data_urls if data_row['id'] not in processed_assets]
        if unprocessed_assets:
            print(f"{datetime.now()} Warning: {len(unprocessed_assets)} assets were not processed: {unprocessed_assets}")

        # Update report status
        cursor.execute("SELECT COUNT(*) FROM assets WHERE submitState = 0 AND report_id = ?", (report_id,))
        remaining = cursor.fetchone()[0]
        if remaining == 0 and failed_count == 0:
            cursor.execute("""
                UPDATE reports 
                SET submitState = 1, macro_count = 0, micro_count = 0, both_count = 0
                WHERE report_id = ?
            """, (report_id,))
            conn.commit()
            print(f"{datetime.now()} All assets successfully submitted for report {report_id}")

    finally:
        for i in range(len(browser.tabs) - 1, -1, -1):
            try:
                await browser.tabs[i].close()
            except:
                pass
        try:
            await browser.stop()
        except:
            print(f"{datetime.now()} Warning: Failed to stop browser cleanly")
        conn.close()
        print(f"{datetime.now()} Browser stopped and connection closed.")

    print(f"{datetime.now()} Final result: processed={processed_count}, success={success_count}, failed={failed_count}")
    return {
        "processed": processed_count,
        "success": success_count,
        "failed": failed_count
    }

async def resume_asset_submission(report_internal_id, conn=None, browsers_num=5):
    global account_data
    if account_data is None:
        with open("scripts/account.json", "r") as f:
            account_data = json.load(f)

    if conn is None:
        conn = sqlite3.connect("scripts/report_submit_db.db")
        close_conn = True
    else:
        close_conn = False

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE id = ?", (report_internal_id,))
    report_row = cursor.fetchone()
    if not report_row:
        if close_conn:
            conn.close()
        raise ValueError(f"No report found with internal ID {report_internal_id}")
    report_data = dict(zip([desc[0] for desc in cursor.description], report_row))

    # Fetch all assets with microid=0 for the given report_id
    cursor.execute("SELECT * FROM assets WHERE report_id = ? AND microid = 0", (report_data['report_id'],))
    assets_data = [dict(zip([desc[0] for desc in cursor.description], row)) for row in cursor.fetchall()]
    if not assets_data:
        print(f"{datetime.now()} No assets with microid=0 found for report_id {report_data['report_id']}")
        if close_conn:
            conn.close()
        return False

    print(f"{datetime.now()} Found {len(assets_data)} assets with microid=0 to process for report_id {report_data['report_id']}")

    # Calculate tab allocation
    json_tabs_count = browsers_num // 2 + browsers_num % 2  # Round up for odd browsers_num
    macro_tabs_count = browsers_num - json_tabs_count
    json_tab_base_index = macro_tabs_count + 1  # JSON tabs start after macro tabs

    # Semaphore and lock for JSON tabs
    json_semaphore = asyncio.Semaphore(json_tabs_count)
    json_empty_indexes = [1 for _ in range(json_tabs_count)]
    json_lock = asyncio.Lock()

    async def get_json_tab_index():
        async with json_lock:
            for i, val in enumerate(json_empty_indexes):
                if val == 1:
                    json_empty_indexes[i] = 0
                    return i + json_tab_base_index
            await asyncio.sleep(0.1)
            return await get_json_tab_index()

    browser = None
    try:
        browser = await uc.start(no_sandbox=True)
        print(f"{datetime.now()} Starting resume submission for report_internal_id {report_internal_id}")

        # Log in using main tab (tab 0)
        await login(browser)
        cookies = await get_cookies(browser)
        if not cookies:
            raise Exception("No cookies retrieved after login")
        print(f"{datetime.now()} Logged in successfully")

        # Create tabs dynamically after login based on browsers_num
        target_tabs = browsers_num + 1  # Main tab (0) + worker tabs
        while len(browser.tabs) < target_tabs:
            try:
                await browser.get("", new_tab=True)
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"{datetime.now()} Error creating tab: {str(e)}")
                raise
        print(f"{datetime.now()} Created {len(browser.tabs) - 1} worker tabs after login (expected {browsers_num})")

        # Activate tab 0
        await browser.tabs[0].activate()
        await browser.tabs[0].sleep(1)
        print(f"{datetime.now()} Tab 0 activated for resume processing")

        # Navigate to report page
        report_id = report_data['report_id']
        await go_to_url(browser, 0, f"https://qima.taqeem.sa/report/{report_id}")
        await browser.tabs[0].sleep(1)
        print(f"{datetime.now()} Navigated to report page: https://qima.taqeem.sa/report/{report_id}")

        # Fetch existing macros
        macros_urls_exists = await get_macros(browser, report_id, assets_data, browsers_num)
        print(f"{datetime.now()} Fetched {len(macros_urls_exists)} existing macros")

        # Create additional macros if necessary
        if len(macros_urls_exists) < len(assets_data):
            num_macros_to_create = len(assets_data) - len(macros_urls_exists)
            print(f"{datetime.now()} Need {num_macros_to_create} additional macros")
            await create_asset(browser, 0, num_macros_to_create, report_id)
            macros_urls_exists = await get_macros(browser, report_id, assets_data, browsers_num)
            print(f"{datetime.now()} After creation, fetched {len(macros_urls_exists)} macros")

        if len(macros_urls_exists) < len(assets_data):
            raise Exception(f"Insufficient macros: Found {len(macros_urls_exists)} but need {len(assets_data)} for report_id {report_id}")

        # Map assets to macros
        macros_data_urls = []
        used_macro_ids = set()
        for d in assets_data:
            if not macros_urls_exists:
                print(f"{datetime.now()} Error: No macro available for asset {d['id']}")
                continue
            new_macro_id = macros_urls_exists[0].split("/")[-2]
            while new_macro_id in used_macro_ids and macros_urls_exists:
                macros_urls_exists.pop(0)
                new_macro_id = macros_urls_exists[0].split("/")[-2] if macros_urls_exists else None
            if new_macro_id:
                used_macro_ids.add(new_macro_id)
                macros_urls_exists.pop(0)
                if int(d['macroid']) == 0:
                    cursor.execute("UPDATE assets SET macroid = ? WHERE id = ?", (new_macro_id, d['id']))
                    conn.commit()
                    print(f"{datetime.now()} Assigned macro_id {new_macro_id} to asset {d['id']}")
                macros_data_urls.append((d, f'https://qima.taqeem.sa/report/macro/{new_macro_id}/edit'))
            else:
                print(f"{datetime.now()} Error: No macro available for asset {d['id']} after filtering")

        # Process assets in batches
        semaphore = asyncio.Semaphore(macro_tabs_count)
        empty_indexes = [1 for _ in range(macro_tabs_count)]
        processed_assets = set()
        batch_size = macro_tabs_count  # Match batch size to number of macro tabs
        total_assets = len(macros_data_urls)

        async def validate_tab(tab_index):
            """Check if a tab is responsive."""
            try:
                await browser.tabs[tab_index].select("html", timeout=10)
                return True
            except Exception as e:
                print(f"{datetime.now()} Tab {tab_index} is unresponsive: {str(e)}")
                return False

        async def recreate_tab(tab_index):
            """Close and recreate a tab if it’s unresponsive."""
            try:
                await browser.tabs[tab_index].close()
                print(f"{datetime.now()} Closed unresponsive tab {tab_index}")
            except:
                pass
            await browser.get("", new_tab=True)
            await asyncio.sleep(0.1)
            print(f"{datetime.now()} Recreated tab {tab_index}")

        async def process_macro_task(data_row, url):
            if data_row['id'] in processed_assets:
                print(f"{datetime.now()} Skipping already processed asset {data_row['id']}")
                return
            retries = 0
            max_retries = 3
            tab_index = None
            while retries < max_retries:
                async with semaphore:
                    async with lock1:
                        if not browser.tabs:
                            print(f"{datetime.now()} Error: No tabs available, cannot process asset {data_row['id']}")
                            return
                        index = await get_empty_index(empty_indexes)
                        if index >= macro_tabs_count:
                            print(f"{datetime.now()} Error: Invalid index {index} (max {macro_tabs_count - 1}), empty_indexes={empty_indexes}")
                            return
                        tab_index = index + 1
                        empty_indexes[index] = 0
                        print(f"{datetime.now()} Tab {tab_index}: Selected index {index} for asset {data_row['id']}, empty_indexes={empty_indexes}")

                macro_id = url.split("/")[-2]
                print(f"{datetime.now()} Tab {tab_index}: Processing macro {macro_id} for asset {data_row['id']}")
                try:
                    # Validate tab responsiveness
                    if not await validate_tab(tab_index):
                        await recreate_tab(tab_index)
                        if tab_index >= len(browser.tabs):
                            raise Exception(f"Tab {tab_index} does not exist after recreation")

                    # Step 1: Navigate to macro edit page
                    print(f"{datetime.now()} Tab {tab_index}: Navigating to macro edit page {url}")
                    await go_to_url(browser, tab_index, url)
                    await browser.tabs[tab_index].select("input[id='asset_type']", timeout=200)

                    # Fetch CSRF token and form element
                    csrf = await try_or_reload_page(
                        browser, tab_index,
                        "form[id='macro_update'] input[name='_token']",
                        2
                    )
                    form_element = await browser.tabs[tab_index].select("form[id='macro_update']", timeout=60)
                    if form_element is None:
                        raise Exception(f"Form 'macro_update' not found on page for macro {macro_id}")

                    # Fetch country, region, and city IDs
                    country = data_row['country']
                    region = data_row['region']
                    city = data_row['city']

                    # Get country ID
                    page_content = await browser.tabs[tab_index].get_content()
                    try:
                        country_v = int(re.findall(
                            f'value="(\\d+)".*?>{country}<',
                            page_content
                        )[0])
                    except IndexError:
                        raise Exception(f"Country '{country}' not found in page content")

                    # Fetch region ID
                    async with json_semaphore:
                        json_tab_index = await get_json_tab_index()
                        try:
                            print(f"{datetime.now()} Tab {json_tab_index} fetching regions for country ID {country_v}")
                            page2 = await browser.tabs[json_tab_index].get(f"https://qima.taqeem.sa/common/regions?country_id={country_v}")
                            json_data = json.loads(
                                (await (await browser.tabs[json_tab_index].select("pre", timeout=100)).get_html())[5:-6]
                            )
                            region_v = None
                            for k, v in json_data.items():
                                if v == region:
                                    region_v = int(k)
                                    break
                            if region_v is None:
                                raise Exception(f"Region '{region}' not found for country ID {country_v}")
                        finally:
                            async with json_lock:
                                json_empty_indexes[json_tab_index - json_tab_base_index] = 1

                    # Fetch city ID
                    async with json_semaphore:
                        json_tab_index = await get_json_tab_index()
                        try:
                            print(f"{datetime.now()} Tab {json_tab_index} fetching cities for region ID {region_v}")
                            page2 = await browser.tabs[json_tab_index].get(f"https://qima.taqeem.sa/common/cities?region_id={region_v}")
                            json_data = json.loads(
                                (await (await browser.tabs[json_tab_index].select("pre", timeout=100)).get_html())[5:-6]
                            )
                            city_v = None
                            for k, v in json_data.items():
                                if v == city:
                                    city_v = int(k)
                                    break
                            if city_v is None:
                                raise Exception(f"City '{city}' not found for region ID {region_v}")
                        finally:
                            async with json_lock:
                                json_empty_indexes[json_tab_index - json_tab_base_index] = 1

                    print(f"{datetime.now()} Tab {tab_index} retrieved IDs: country={country_v}, region={region_v}, city={city_v}")

                    # Fill macro form
                    await form_element.apply("""
                        (elem) => {
                            elem.innerHTML = `
<input id='asset_type' name='asset_type' value='""" + str(data_row["asset_type"]) + """' />
<input id='asset_name' name='asset_name' value='""" + str(data_row["asset_name"]) + """' />
<input id='asset_usage_id' name='asset_usage_id' value='""" + str(data_row["asset_usage_id"]) + """' />
<input id='value_base_id' name='value_base_id' value='""" + str(data_row["value_base"]) + """' />
<input id='inspected_at' name='inspected_at' value='""" + "-".join(str(data_row["inspection_date"]).split("-")[::-1]) + """' />
<input id='value' name='value' value='""" + str(data_row["final_value"]) + """' />
<input id='production_capacity' name='production_capacity' value='""" + str(data_row["production_capacity"]) + """' />
<input id='production_capacity_measuring_unit' name='production_capacity_measuring_unit' value='""" + str(data_row["production_capacity_measuring_unit"]) + """' />
<input id='owner_name' name='owner_name' value='""" + str(data_row['owner_name']) + """' />
<input id='product_type' name='product_type' value='""" + str(data_row['product_type']) + """' />
<input id='approach' name='approach[1][is_primary]' value='""" + str(data_row['market_approach']) + """' />
<input id='approach' name='approach[1][value]' value='""" + str(data_row['market_approach_value']) + """' />
<input id='approach' name='approach[3][is_primary]' value='""" + str(data_row['cost_approach']) + """' />
<input id='approach' name='approach[3][value]' value='""" + str(data_row['cost_approach_value']) + """' />
<input id='country_id' name='country_id' value='""" + str(country_v) + """' />
<input id='region_id' name='region_id' value='""" + str(region_v) + """' />
<input id='city_id' name='city_id' value='""" + str(city_v) + """' />
<input id='report_id' name='report_id' value='""" + str(report_id) + """' />
<input id="save" class="btn btn-primary" name="update" type="submit" value="حفظ">
""" + await csrf.get_html() + """`;
                        }
                    """)

                    # Submit macro form
                    print(f"{datetime.now()} Tab {tab_index} submitting macro form for macro {macro_id}")
                    await proceed_to_next_page(browser, tab_index, 'input[name="asset_type"]')
                    print(f"{datetime.now()} Tab {tab_index} macro {macro_id} form submitted successfully")

                    # Step 2: Create micro asset
                    micro_create_url = f"https://qima.taqeem.sa/report/macro_asset/create/{report_id}/{macro_id}"
                    print(f"{datetime.now()} Tab {tab_index} navigating to micro creation page: {micro_create_url}")
                    await go_to_url(browser, tab_index, micro_create_url)
                    await browser.tabs[tab_index].sleep(0.3)

                    await create_micro_asset(browser, tab_index, data_row, macro_id, report_id)
                    print(f"{datetime.now()} Tab {tab_index} micro created for macro {macro_id}")

                    # Fetch micro URLs
                    micros_urls = await get_micros(browser, tab_index)
                    if not micros_urls:
                        raise Exception(f"No micro URLs found for macro {macro_id} after creation")
                    micro_url = micros_urls[0]
                    micro_id = micro_url.split("/")[-2]
                    print(f"{datetime.now()} Tab {tab_index} created micro {micro_id} for macro {macro_id}")

                    # Step 3: Edit micro asset
                    print(f"{datetime.now()} Tab {tab_index} navigating to micro edit page: {micro_url}")
                    await go_to_url(browser, tab_index, micro_url)
                    await browser.tabs[tab_index].sleep(0.3)
                    await edit_micro_asset(browser, tab_index, data_row, report_id, macro_id, micro_id)
                    print(f"{datetime.now()} Tab {tab_index} micro {micro_id} edited for macro {macro_id}")

                    # Step 4: Update database
                    cursor.execute("UPDATE assets SET submitState = '1', micro_url = ?, microid = ? WHERE id = ?",
                                  (micro_url, micro_id, data_row['id']))
                    conn.commit()
                    print(f"{datetime.now()} Tab {tab_index} saved micro {micro_id} for asset {data_row['id']}")
                    async with lock1:
                        processed_assets.add(data_row['id'])
                    break

                except Exception as e:
                    retries += 1
                    print(f"{datetime.now()} Tab {tab_index}: Retry {retries}/{max_retries} failed for macro {macro_id}, asset {data_row['id']}: {str(e)}")
                    if retries >= max_retries:
                        print(f"{datetime.now()} Tab {tab_index}: Max retries reached for macro {macro_id}, asset {data_row['id']}")
                        async with lock1:
                            empty_indexes[index] = 1
                        return
                    await asyncio.sleep(0.3)
                    await recreate_tab(tab_index)

                finally:
                    if tab_index is not None:
                        async with lock1:
                            empty_indexes[index] = 1
                            print(f"{datetime.now()} Tab {tab_index}: Released index {index}, empty_indexes={empty_indexes}")

        # Process assets in batches
        for batch_start in range(0, total_assets, batch_size):
            batch_end = min(batch_start + batch_size, total_assets)
            print(f"{datetime.now()} Processing batch {batch_start} to {batch_end} of {total_assets} assets")
            tasks = [process_macro_task(data_row, url) for data_row, url in macros_data_urls[batch_start:batch_end]]
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result, (data_row, _) in zip(results, macros_data_urls[batch_start:batch_end]):
                    if isinstance(result, Exception):
                        print(f"{datetime.now()} Failed to process asset {data_row['id']}: {str(result)}")
            except Exception as e:
                print(f"{datetime.now()} Error in batch {batch_start}-{batch_end}: {str(e)}")
                raise

            # Periodically check and recreate unresponsive tabs
            for i in range(1, browsers_num + 1):
                if not await validate_tab(i):
                    await recreate_tab(i)

        # Verify all assets processed
        cursor.execute("SELECT COUNT(*) FROM assets WHERE report_id = ? AND microid = 0", (report_data['report_id'],))
        remaining = cursor.fetchone()[0]
        print(f"{datetime.now()} Processed {len(processed_assets)} assets, {remaining} assets with microid=0 remain")
        if remaining > 0:
            print(f"{datetime.now()} Warning: {remaining} assets unprocessed. Check macro assignments or network issues")
        else:
            print(f"{datetime.now()} All assets with microid=0 processed successfully")

        return True

    except Exception as e:
        print(f"{datetime.now()} Error in resume_asset_submission: {str(e)}")
        raise

    finally:
        if browser is not None:
            try:
                async def close_tabs():
                    for i in range(len(browser.tabs) - 1, -1, -1):
                        try:
                            print(f"{datetime.now()} Closing tab {i}")
                            await browser.tabs[i].close()
                            await asyncio.sleep(0.1)
                        except Exception as e:
                            print(f"{datetime.now()} Failed to close tab {i}: {str(e)}")

                await asyncio.wait_for(close_tabs(), timeout=10)
                print(f"{datetime.now()} Stopping browser")
                browser.stop()
                print(f"{datetime.now()} Browser stopped successfully")
            except asyncio.TimeoutError:
                print(f"{datetime.now()} Timeout during browser cleanup; forcing browser stop")
                browser.stop()
            except Exception as e:
                print(f"{datetime.now()} Error during browser cleanup: {str(e)}")
                browser.stop()

        if close_conn:
            try:
                conn.close()
                print(f"{datetime.now()} Database connection closed")
            except Exception as e:
                print(f"{datetime.now()} Error closing database connection: {str(e)}")

        print(f"{datetime.now()} Browser stopped and connection closed")

async def main(assets_excel_file_df, reports_excel_file_df):
    global conn, account_data 
    account_data = json.load(open("scripts/account.json"))

    conn = sqlite3.connect("scripts/report_submit_db.db")
    cursor = conn.cursor()

    if assets_excel_file_df is not None:
        # cursor.execute('DELETE FROM assets')
        assets_excel_file_df.to_sql('assets', conn, if_exists='append', index=False)
        conn.commit()
    
    if reports_excel_file_df is not None:
        # cursor.execute('DELETE FROM reports')
        reports_excel_file_df.to_sql('reports', conn, if_exists='append', index=False)
        conn.commit()

async def select_select2_option_simple(page, selector, value):
    try:
        element = await page.find(selector)
        if not element:
            print(f"No Select2 element found for {selector}")
            return False

        await element.apply("""
        el => {
            const evt = new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window });
            el.dispatchEvent(evt);
        }
        """)

        search_input = await wait_for_element(page, "input.select2-search__field", timeout=5)
        if not search_input:
            print("No search input found")
            return False

        await search_input.click()
        await search_input.clear_input() 
        await search_input.send_keys(value)
        await asyncio.sleep(0.5)
        await search_input.apply("""
        el => {
            const evt = new KeyboardEvent('keydown', {
                key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
                bubbles: true, cancelable: true, view: window
            });
            el.dispatchEvent(evt);
        }
        """)
        await asyncio.sleep(0.5)
        return True
    except Exception as e:
        print(f"Select2 selection failed: {e}")
        return False

if __name__ == '__main__':
    account_data = json.load(open("scripts/account.json"))
    
    conn = sqlite3.connect("scripts/report_submit_db.db")
    cursor = conn.cursor()
    
    browsers_num = int(input("Enter num of browsers: "))
    assets_excel_file_path = input("Enter assets Excel file path: ")
    reports_excel_file_path = input("Enter reports Excel file path: ")

    if os.path.exists(assets_excel_file_path):
        df = pd.read_excel(assets_excel_file_path)
        df.to_sql('assets', conn, if_exists='append', index=False)
        conn.commit()
    
    if os.path.exists(reports_excel_file_path):
        df = pd.read_excel(reports_excel_file_path)
        df.to_sql('reports', conn, if_exists='append', index=False)
        conn.commit()

    while True:
        if asyncio.run(submit_reports()):
            break
        print("Retrying submission...")
    
    conn.close()