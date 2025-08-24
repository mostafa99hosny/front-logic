import pandas as pd
import json

# Mapping Excel headers → CSS selectors
field_map = {
    "Report Title": "[name='title']",
    "Valuation Purpose": "[name='purpose_id']",
    "Value Premise": "[name='value_premise_id']",
    "Value Base": "[name='value_base_id']",
    "Report Type": "[name='report_type']",
}

field_types = {
    "Report Title": "text",
    "Valuation Purpose": "select",
    "Value Premise": "select",
    "Value Base": "select",
    "Report Type": "radio",
}

async def extractData(file_path):
    try:
        df = pd.read_excel(file_path)

        records = df.to_dict(orient="records")
        json_data = json.loads(json.dumps(records, default=str))

        return {"status": "SUCCESS", "data": json_data}
    except Exception as e:
        return {"status": "FAILED", "error": str(e)}

async def fill_form(page, record, field_map, field_types):
    for key, selector in field_map.items():
        if key not in record:
            continue
        value = str(record[key])
        field_type = field_types.get(key, "text")

        if field_type == "text":
            element = await page.query_selector(selector)
            if element:
                await element.send_keys(value)

        elif field_type == "select":
            element = await page.query_selector(selector)
            if element:
                await element.select_option(value)

        elif field_type == "radio":
            radio_selector = f"{selector}[value='{value}']"
            element = await page.query_selector(radio_selector)
            if element:
                await element.click()
