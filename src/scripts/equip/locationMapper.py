from formFiller import wait_for_element

contry_codes = {
    "المملكة العربية السعودية": "1"
}

region_codes = {
    "منطقة الرياض": "1",
}

city_codes = {
    "الرياض": "3",
}

def get_country_code(country):
    return contry_codes.get(country.strip(), "")

def get_region_code(region):
    return region_codes.get(region.strip(), "")

def get_city_code(city):
    return city_codes.get(city.strip(), "")


def find_location_code(location_selector):
    country_selector = wait_for_element(None, location_selector, timeout=10)
    if country_selector:
        country_options = country_selector.children
        for opt in country_options:
            text = (opt.text or "").strip()
            