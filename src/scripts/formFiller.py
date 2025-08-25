import pandas as pd
import json

field_map = {
    "Report Title": "[name='title']",
    "Valuation Purpose": "[name='purpose_id']",
    "Value Premise": "[name='value_premise_id']",
    "Value Base": "[name='value_base_id']",
    "Report Type": "[name='report_type']",
    "Valuation Date": "[name='valued_at']",
    "Report Issuing Date": "[name='submitted_at']",
    "Assumptions": "[name='assumptions']",
    "Special Assumptions": "[name='special_assumptions']",
    "Final Value": "[name='value']",
    "Valuation Currency": "[name='currency_id']",
    "Report Asset File": "[name='report_file']",

    "Client Name": "[name='client[0][name]']",
    "Telephone Number": "[name='client[0][telephone]']",
    "E-mail Address": "[name='client[0][email]']",

    "The report has other users": "[name='has_user']",
    "Report User": "[name='user[0][name]']",
    "Valuer Name": "[name='valuer[0][id]']",
    "Contribution Percentage": "[name='valuer[0][contribution]']",
}

field_types = {
    "Report Title": "text",
    "Valuation Purpose": "select",
    "Value Premise": "select",
    "Value Base": "select",
    "Report Type": "radio",
    "Valuation Date": "text",
    "Report Issuing Date": "text",
    "Assumptions": "text",
    "Special Assumptions": "text",
    "Final Value": "text",
    "Valuation Currency": "select",
    "Report Asset File": "text",

    "Client Name": "text",
    "Telephone Number": "text",
    "E-mail Address": "text",
    "The report has other users": "checkbox",
    "Report User": "text",
    "Valuer Name": "select",
    "Contribution Percentage": "select",
}

async def extractData(file_path):
    try:
        df = pd.read_excel(file_path)
        df = df.fillna("")

        records = df.to_dict(orient="records")
        json_data = json.loads(json.dumps(records, default=str))

        return {"status": "SUCCESS", "data": json_data}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

async def fill_form(page, record, field_map, field_types):
    for key, selector in field_map.items():
        if key not in record:
            continue

        value = str(record[key] or "")
        field_type = field_types.get(key, "text")

        try:
            if field_type == "text":
                element = await page.query_selector(selector)
                if element:
                    if "readonly" in element.attrs:
                        await element.apply("(el) => el.removeAttribute('readonly')")
                    await element.send_keys(value)

            elif field_type == "select":
                select_element = await page.query_selector(selector)
                if not select_element:
                    print(f"Warning: No select element found for selector {selector}")
                    continue

                # Method 1: Iterate through options and find by text
                options = select_element.children
                option_found = False
                
                for option in options:
                    print("option", option)
                    option_text = option.text or ""
                    print("option text", option_text)
                    
                    if option_text.lower() == value.lower():
                        print("messing up while filling")
                        await option.select_option()  # Use the built-in select_option method
                        option_found = True
                        break
                
                # Method 2: If exact match fails, try partial match
                if not option_found:
                    for option in options:
                        option_text = option.text or ""
                        option_text = option_text.strip()
                        
                        if value.lower() in option_text.lower():
                            await option.select_option()
                            option_found = True
                            break
                
                if not option_found:
                    print(f"Warning: Could not find option with text '{value}' in selector {selector}")

            elif field_type == "radio":
                escaped_value = value.replace("'", "\\'").replace('"', '\\"')
                radio_selector = f"{selector}[value='{escaped_value}']"
                element = await page.query_selector(radio_selector)
                if element:
                    await element.click()
                else:
                    print(f"Warning: No radio button found for value '{value}' with selector {selector}")

        except Exception as e:
            print(f"Error filling {key}: {e}")
            continue
