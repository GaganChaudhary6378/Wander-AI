from agents.tools import get_station_codes_for_city, _search_trains_rapidapi, _search_trains_railradar

bengaluru_codes = get_station_codes_for_city("bangalore")
chennai_codes = get_station_codes_for_city("chennai")

print("Bangalore Codes:", bengaluru_codes)
print("Chennai Codes:", chennai_codes)
