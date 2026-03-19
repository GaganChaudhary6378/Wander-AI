from agents.tools import search_transport_options
from pprint import pprint

options = search_transport_options("bangalore", "chennai", "2026-03-25")
print(f"Total Trains Found: {len(options.get('trains', []))}")
if options.get("trains"):
    pprint(options["trains"][:2])
else:
    print("No direct trains.")

print("No direct trains flag:", options.get("_no_direct_trains"))
print("RapidAPI Checked flag:", options.get("_rapidapi_checked"))
