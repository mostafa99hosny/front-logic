field_map_1 = {
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

field_types_1 = {
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
    "Report Asset File": "file",
    "Client Name": "text",
    "Telephone Number": "text",
    "E-mail Address": "text",
    "The report has other users": "checkbox",
    "Report User": "text",
    "Valuer Name": "select",
    "Contribution Percentage": "select",
}

field_map_2 = {
    "Type of Asset Being Valued": "[name='asset_type_id']",
    "Inspection Date": "[name='inspected_at']",
    "Final Value": "[name='value']",
    "Asset Being Valued Usage\\Sector": "[name='asset_usage_id']",

    "Market Approach": "[id='approach1']",
    "Comparable Transactions Method": "[name='approach[1][method][1][value]']",

    "Income Approach": "[id='approach2']",
    "Profit Method": "[name='approach[2][method][5][value]']",

    "Cost Approach": "[id='approach3']",
    "Summation Method": "[name='approach[3][method][11][value]']",

    "Country": "[name='country_id'] + .select2-container .select2-selection",
    "Region": "[name='region_id'] + .select2-container .select2-selection",
    "City": "[name='city_id'] + .select2-container .select2-selection",

    "Longitude": "[name='longitude']",
    "Latitude": "[name='latitude']",
}

field_types_2 = {
    "Type of Asset Being Valued": "select",
    "Asset Being Valued Usage\\Sector": "select",
    "Inspection Date": "text",
    "Final Value": "text",

    "Market Approach": "select",
    "Comparable Transactions Method": "text",

    "Income Approach": "select",
    "Profit Method": "text",

    "Cost Approach": "select",
    "Summation Method": "text",

    "Country": "location",
    "Region": "location",
    "City": "location",
    
    "Latitude": "text",
    "Longitude": "text",
}

field_map_3 = {
    "Block Number": "[name='attribute[1]']",
    "Property Number": "[name='attribute[2]']",
    "Certificate Number": "[name='attribute[3]']",
    "Ownership Type": "[name='attribute[4]']",
    "Ownership pecentage": "[name='attribute[5]']",
    "Rental duration": "[name='attribute[6]']",
    "Rental end date": "[name='attribute[7]']",
    "Street facing fronts": "[name='attribute[8]']",
    "Distance from City Center": "[name='attribute[9]']",
    "Facilities": "[name='attribute[10][]']",
    "Land Area": "[name='attribute[11]']",
    "Building Area": "[name='attribute[12]']",
    "Authorized Land Cover Percentage": "[name='attribute[13]']",
    "Authorized height": "[name='attribute[14]']",
    "The land of this building is leased": "[id='15']",
    "Building Status": "[name='attribute[16]']",
    "Finishing Status": "[name='attribute[17]']",
    "Furnishing Status": "[name='attribute[18]']",
    "Air Conditioning": "[name='attribute[19]']",
    "Building Type": "[name='attribute[20]']",
    "Other Features": "[name='attribute[21][]']",
    "The current use is considered the best use": "[name='attribute[27]']",
    "Asset Age": "[name='attribute[28]']",
    "Street width": "[name='attribute[31]']",
}

field_types_3 = {
    "Block Number": "text",
    "Property Number": "text",
    "Certificate Number": "text",
    "Ownership Type": "select",
    "Ownership pecentage": "text",
    "Rental duration": "text",
    "Rental end date": "text",
    "Street facing fronts": "select",
    "Distance from City Center": "text",
    "Facilities": "checkbox",
    "Land Area": "text",
    "Building Area": "text",
    "Authorized Land Cover Percentage": "text",
    "Authorized height": "text",
    "The land of this building is leased": "radio",

    "Building Status": "select",
    "Finishing Status": "select",
    "Furnishing Status": "select",
    "Air Conditioning": "select",
    "Building Type": "select",
    
    "Other Features": "checkbox",
    "The current use is considered the best use": "radio",
    "Asset Age": "text",
    "Street width": "text"
}

form_steps = [
    {"field_map": field_map_1, "field_types": field_types_1},
    {"field_map": field_map_2, "field_types": field_types_2},
    {"field_map": field_map_3, "field_types": field_types_3},
]