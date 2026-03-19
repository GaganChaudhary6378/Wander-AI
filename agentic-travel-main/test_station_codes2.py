from agents.tools import get_station_codes_for_city, _load_station_list_once, _STATION_WORD_TO_CODES

_load_station_list_once()
print("SBC codes for 'bengaluru':", get_station_codes_for_city("bengaluru"))

# Look at words matching "bangalore" and "bengaluru"
print("Word 'bangalore':", _STATION_WORD_TO_CODES.get("bangalore", []))
print("Word 'bengaluru':", _STATION_WORD_TO_CODES.get("bengaluru", []))
