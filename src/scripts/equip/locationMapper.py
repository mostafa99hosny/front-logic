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



            