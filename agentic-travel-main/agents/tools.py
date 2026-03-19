"""
Live API tools for WanderAI agents.
Provides real-time data from Google Places, OpenWeatherMap, SerpAPI,
fast_flights (Google Flights scraper), Google Maps Directions (multi-modal transport),
and web search (travel knowledge).
Falls back to mock data when API keys are missing or calls fail.
"""

import json
import re
import requests
from collections import defaultdict
from config import config
from data.mock_data import (
    MOCK_FLIGHTS, MOCK_HOTELS, MOCK_ACTIVITIES, MOCK_WEATHER, LOCAL_TIPS
)

# In-memory cache for Indian Railway station list (one-time fetch from public JSON)
_STATION_NAME_TO_CODE: dict[str, str] | None = None
_STATION_WORD_TO_CODES: dict[str, set[str]] | None = None
_STATION_LIST_URL = (
    "https://raw.githubusercontent.com/mayurrawte/IndianRailApi/master/data/station_codes.json"
)

# In-memory cache for airport IATA codes (city name -> code), filled via Tavily/Exa search
_airport_code_cache: dict[str, str] = {}
# Stoplist: not real IATA codes
_IATA_STOPLIST = frozenset({"THE", "AND", "FOR", "USA", "UK ", "ALL", "NEW", "OLD", "VIA", "AIR", "GET", "CAN", "NOT", "YOU", "ARE", "BUT", "HAS", "HAD", "HOW", "WHO", "WHY", "NOW", "OUT", "DAY", "WAY", "MAY", "RUN", "SEE", "JET", "TOP", "BIG", "LOW", "FAR", "TWO", "ONE", "SIX", "TEN", "NET", "WEB", "API", "KEY", "URL", "COM", "ORG", "INC", "LTD", "EST", "JAN", "FEB", "MAR", "APR", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"})


def _fetch_airport_code_via_search(city: str) -> str | None:
    """Resolve city name to IATA airport code using Tavily or Exa search. Results cached in memory."""
    key = city.lower().strip()
    if not key:
        return None
    if key in _airport_code_cache:
        return _airport_code_cache[key]

    query = f"{city} airport IATA code"
    text_to_scan = ""

    # Try Tavily first
    tavily_key = config.TAVILY_API_KEY
    if tavily_key and tavily_key != "your_tavily_key_here":
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                include_answer=True,
            )
            if response.get("answer"):
                text_to_scan += " " + response["answer"]
            for item in response.get("results", [])[:3]:
                if item.get("content"):
                    text_to_scan += " " + item["content"][:500]
        except Exception as e:
            print(f"Tavily airport lookup error: {e}")

    # Try Exa if no result yet
    if not text_to_scan and config.EXA_API_KEY and config.EXA_API_KEY != "your_exa_key_here":
        try:
            from exa_py import Exa
            exa = Exa(api_key=config.EXA_API_KEY)
            response = exa.search_and_contents(
                query=query,
                num_results=3,
                text={"max_characters": 300},
            )
            for result in response.results:
                if getattr(result, "text", None):
                    text_to_scan += " " + (result.text or "")
                if result.highlights:
                    text_to_scan += " " + " ".join(result.highlights)
        except Exception as e:
            print(f"Exa airport lookup error: {e}")

    if not text_to_scan:
        return None

    # Extract 3-letter IATA code: prefer pattern like "IATA: XXX", "(XXX)", "code XXX"
    text_upper = text_to_scan.upper()
    for pattern in [
        r"IATA\s*[:\-]?\s*([A-Z]{3})\b",
        r"\(([A-Z]{3})\)",
        r"code\s+([A-Z]{3})\b",
        r"airport\s+([A-Z]{3})\b",
        r"\b([A-Z]{3})\s+airport",
        r"\b([A-Z]{3})\b",
    ]:
        for m in re.finditer(pattern, text_upper, re.IGNORECASE):
            code = m.group(1).upper()
            if code not in _IATA_STOPLIST and code.isalpha():
                _airport_code_cache[key] = code
                return code

    return None


def _load_station_list_once() -> bool:
    """Fetch Indian Railway station list (name -> code) once and build word index. Returns True if loaded."""
    global _STATION_NAME_TO_CODE, _STATION_WORD_TO_CODES
    if _STATION_WORD_TO_CODES is not None:
        return True
    try:
        resp = requests.get(_STATION_LIST_URL, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
        # JSON is [{"STATION NAME": "CODE", ...}] (single dict in a list)
        if isinstance(raw, list) and raw:
            name_to_code = raw[0]
        elif isinstance(raw, dict):
            name_to_code = raw
        else:
            return False
        _STATION_NAME_TO_CODE = {k.strip(): v for k, v in name_to_code.items() if k and v}
        word_to_codes: dict[str, set[str]] = defaultdict(set)
        for name, code in _STATION_NAME_TO_CODE.items():
            name_lower = name.lower()
            for word in name_lower.replace("-", " ").split():
                if len(word) >= 2:
                    word_to_codes[word].add(code)
        _STATION_WORD_TO_CODES = dict(word_to_codes)
        return True
    except Exception as e:
        print(f"Station list fetch error: {e}")
        return False


_MAJOR_CITY_STATIONS = {
    "bangalore": ["SBC", "YPR", "SMVB", "BNC", "KJM"],
    "bengaluru": ["SBC", "YPR", "SMVB", "BNC", "KJM"],
    "delhi": ["NDLS", "NZM", "DLI", "ANVT", "DEE"],
    "new delhi": ["NDLS", "NZM", "DLI", "ANVT", "DEE"],
    "mumbai": ["CSMT", "LTT", "BDTS", "BCT", "DR"],
    "chennai": ["MAS", "MS", "TBM", "PER"],
    "kolkata": ["HWH", "SDAH", "KOAA", "SHM"],
    "hyderabad": ["SC", "HYB", "KCG"],
    "secunderabad": ["SC", "HYB", "KCG"],
    "pune": ["PUNE"],
    "ahmedabad": ["ADI"],
    "jaipur": ["JP"],
    "lucknow": ["LKO", "LJN"],
    "chandigarh": ["CDG"],
    "bhubaneswar": ["BBS"],
    "guwahati": ["GHY"],
    "patna": ["PNBE"],
    "bhopal": ["RKMP", "BPL"],
    "indore": ["INDB"],
    "nagpur": ["NGP"],
    "kochi": ["ERS", "ERN"],
    "ernakulam": ["ERS", "ERN"],
    "trivandrum": ["TVC"],
    "thiruvananthapuram": ["TVC"],
    "goa": ["MAO", "VSG", "THVM"],
    "madgaon": ["MAO"],
    "varanasi": ["BSB", "DDU", "BSBS"],
    "agra": ["AGC", "AF"],
    "amritsar": ["ASR"],
    "mysore": ["MYS"],
    "mysuru": ["MYS"],
    "coimbatore": ["CBE"],
    "madurai": ["MDU"],
    "rishikesh": ["YNRK", "RKSH", "HW"],
    "haridwar": ["HW"],
    "dehradun": ["DDN"],
}

def get_station_codes_for_city(city: str) -> list[str]:
    """
    Resolve city/station name to list of station codes from cached Indian Railway data.
    Uses one-time fetched list from public JSON; lookup is in-memory.
    Returns empty list if not loaded or no match.
    """
    city_clean = city.lower().strip()
    if not city_clean:
        return []

    if city_clean in _MAJOR_CITY_STATIONS:
        return _MAJOR_CITY_STATIONS[city_clean]

    if not _load_station_list_once() or not _STATION_WORD_TO_CODES:
        return []
    words = [w for w in city_clean.replace("-", " ").split() if len(w) >= 2]
    if not words:
        return []
    # Exact match on full name
    if _STATION_NAME_TO_CODE:
        for name, code in _STATION_NAME_TO_CODE.items():
            if name.lower() == city_clean:
                return [code]
    # Intersection of codes for all words (e.g. "new delhi" -> codes that have both "new" and "delhi")
    sets = [_STATION_WORD_TO_CODES.get(w, set()) for w in words]
    if not sets:
        return []
    codes = set.intersection(*sets) if len(sets) > 1 else sets[0]
    if codes:
        return list(codes)[:10]  # cap at 10 codes per city
    # Fallback: any word match (e.g. "delhi" alone)
    for w in words:
        if w in _STATION_WORD_TO_CODES:
            return list(_STATION_WORD_TO_CODES[w])[:10]
    return []


# ─── Google Places API ───────────────────────────────────────────────

def search_places(query: str, location: str = None, place_type: str = None, max_results: int = 5) -> list:
    """Search for places using Google Places Text Search API."""
    api_key = config.GOOGLE_PLACES_API_KEY
    if not api_key:
        return []

    try:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": query,
            "key": api_key,
        }
        if location:
            params["query"] = f"{query} in {location}"

        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for place in data.get("results", [])[:max_results]:
            photo_ref = ""
            if place.get("photos"):
                photo_ref = place["photos"][0].get("photo_reference", "")

            photo_url = ""
            if photo_ref:
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_ref}&key={api_key}"

            results.append({
                "name": place.get("name", ""),
                "description": place.get("formatted_address", ""),
                "rating": place.get("rating", 0),
                "location": place.get("formatted_address", ""),
                "lat": place.get("geometry", {}).get("location", {}).get("lat", 0),
                "lon": place.get("geometry", {}).get("location", {}).get("lng", 0),
                "price_level": place.get("price_level", 0),
                "image_url": photo_url,
                "place_id": place.get("place_id", ""),
                "types": place.get("types", []),
                "user_ratings_total": place.get("user_ratings_total", 0),
            })

        return results
    except Exception as e:
        print(f"Google Places API error: {e}")
        return []


# price_level (0-4) → (low_inr, high_inr, label) per night
_HOTEL_PRICE_LEVEL_MAP = {
    0: (500,   1500,  "Under ₹1,500 / night (est.)"),
    1: (1500,  3000,  "₹1,500 – ₹3,000 / night (est.)"),
    2: (3000,  6000,  "₹3,000 – ₹6,000 / night (est.)"),
    3: (6000,  12000, "₹6,000 – ₹12,000 / night (est.)"),
    4: (12000, 30000, "₹12,000+ / night (est.)"),
}


def _infer_price_level(price_level: int | None, rating: float) -> int:
    """
    Google Places often omits price_level for hotels.
    When absent, infer a tier from the hotel's star rating as a proxy for price category.
    """
    if price_level is not None:
        return price_level
    if rating >= 4.5:
        return 4   # luxury / 5-star
    if rating >= 4.0:
        return 3   # upscale / 4-star
    if rating >= 3.5:
        return 2   # mid-range / 3-star
    if rating >= 2.5:
        return 1   # budget
    return 2       # safe default when no rating

PLACES_BASE = "https://maps.googleapis.com/maps/api/place"


def _fetch_hotel_website(place_id: str) -> str:
    """Fetch a hotel's own website URL via the Google Places Details API."""
    api_key = config.GOOGLE_PLACES_API_KEY
    if not api_key or not place_id or place_id.startswith("mock_"):
        return ""
    try:
        resp = requests.get(
            f"{PLACES_BASE}/details/json",
            params={"place_id": place_id, "fields": "website", "key": api_key},
            timeout=8,
        )
        return resp.json().get("result", {}).get("website", "")
    except Exception:
        return ""


def _google_hotels_link(destination: str, check_in: str = "", check_out: str = "") -> str:
    """Build a Google Hotels search URL for the destination."""
    from urllib.parse import quote
    base = f"https://www.google.com/travel/hotels/{quote(destination)}"
    if check_in and check_out:
        base += f"?dates={check_in}/{check_out}"
    return base


def _search_lodging(
    *,
    destination: str,
    query: str,
    stay_type_label: str,
    max_results: int = 6,
    check_in: str = "",
    check_out: str = "",
) -> list:
    """
    Search for lodging (hotels/hostels) using Google Places Text Search API.
    Price is estimated from price_level (0-4) using fixed INR bands.
    Website fetched via Places Details API for top 3 results.
    """
    api_key = config.GOOGLE_PLACES_API_KEY
    google_hotels_url = _google_hotels_link(destination, check_in, check_out)

    if not api_key:
        return []

    try:
        resp = requests.get(
            f"{PLACES_BASE}/textsearch/json",
            params={"query": query, "key": api_key, "type": "lodging"},
            timeout=15,
        )
        data = resp.json()
        if data.get("status") != "OK":
            return []

        raw_results = data.get("results", [])[:max_results]

        # Fetch websites for the top 3 results (keeps latency reasonable)
        top_place_ids = [r.get("place_id", "") for r in raw_results[:3]]
        website_map: dict[str, str] = {}
        for pid in top_place_ids:
            website_map[pid] = _fetch_hotel_website(pid)

        stays = []
        for r in raw_results:
            raw_rating = r.get("rating", 0.0) or 0.0
            price_level = _infer_price_level(r.get("price_level"), raw_rating)
            low, high, label = _HOTEL_PRICE_LEVEL_MAP.get(price_level, _HOTEL_PRICE_LEVEL_MAP[2])
            mid_price = (low + high) // 2
            place_id = r.get("place_id", "")

            photo_ref = ""
            if r.get("photos"):
                photo_ref = r["photos"][0].get("photo_reference", "")
            photo_url = (
                f"{PLACES_BASE}/photo?maxwidth=400&photo_reference={photo_ref}&key={api_key}"
                if photo_ref
                else ""
            )

            stays.append(
                {
                    "name": r.get("name", ""),
                    "location": r.get("formatted_address", r.get("vicinity", "")),
                    "price_per_night": mid_price,
                    "price_range_label": label,
                    "currency": "INR",
                    "rating": raw_rating,
                    "user_ratings_total": r.get("user_ratings_total", 0),
                    "type": stay_type_label,
                    "amenities": ["WiFi", "AC"],
                    "image_url": photo_url,
                    "place_id": place_id,
                    "maps_link": f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                    "website": website_map.get(place_id, ""),
                    "google_hotels_link": google_hotels_url,
                    "lat": r.get("geometry", {}).get("location", {}).get("lat", 0),
                    "lon": r.get("geometry", {}).get("location", {}).get("lng", 0),
                }
            )

        return stays

    except Exception as e:
        print(f"Google Places lodging search error: {e}")
        return []


def search_hotels(destination: str, max_results: int = 6, check_in: str = "", check_out: str = "") -> list:
    """Search for hotels using Google Places."""
    return _search_lodging(
        destination=destination,
        query=f"hotels in {destination}",
        stay_type_label="Hotel",
        max_results=max_results,
        check_in=check_in,
        check_out=check_out,
    )


def search_hostels(destination: str, max_results: int = 6, check_in: str = "", check_out: str = "") -> list:
    """Search for hostels using Google Places."""
    return _search_lodging(
        destination=destination,
        query=f"hostels in {destination}",
        stay_type_label="Hostel",
        max_results=max_results,
        check_in=check_in,
        check_out=check_out,
    )


def search_activities(destination: str, interests: list = None, max_results: int = 8) -> list:
    """Search for activities/attractions using Google Places."""
    queries = [f"things to do in {destination}", f"attractions in {destination}"]
    if interests:
        for interest in interests[:3]:
            queries.append(f"{interest} in {destination}")

    seen_names = set()
    activities = []
    for query in queries:
        places = search_places(query, destination, max_results=4)
        for p in places:
            if p["name"] in seen_names:
                continue
            seen_names.add(p["name"])
            activities.append({
                "name": p["name"],
                "description": p.get("description", f"Popular spot in {destination}"),
                "cost": p.get("price_level", 0) * 300,
                "currency": "INR",
                "location": p.get("location", destination),
                "category": "activity",
                "image_url": p.get("image_url", ""),
                "booking_url": "",
                "rating": p.get("rating", 0),
                "duration_mins": 90,
                "lat": p.get("lat", 0),
                "lon": p.get("lon", 0),
            })
            if len(activities) >= max_results:
                break
        if len(activities) >= max_results:
            break

    return activities


# ─── OpenWeatherMap API ───────────────────────────────────────────────

def get_weather(destination: str) -> dict:
    """Get current weather and forecast from OpenWeatherMap."""
    api_key = config.OPENWEATHERMAP_API_KEY
    if not api_key:
        return {}

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": destination, "appid": api_key, "units": "metric"}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        current = resp.json()

        temp = round(current.get("main", {}).get("temp", 25))
        condition = current.get("weather", [{}])[0].get("main", "Clear")
        humidity = current.get("main", {}).get("humidity", 50)

        forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
        forecast_resp = requests.get(forecast_url, params=params, timeout=10)
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json()

        daily_forecast = []
        seen_dates = set()
        for item in forecast_data.get("list", []):
            dt_txt = item.get("dt_txt", "")
            date = dt_txt.split(" ")[0]
            hour = dt_txt.split(" ")[1] if " " in dt_txt else ""
            if date not in seen_dates and "12:00" in hour:
                seen_dates.add(date)
                daily_forecast.append({
                    "date": date,
                    "temp": f"{round(item['main']['temp'])}°C",
                    "condition": item.get("weather", [{}])[0].get("main", "Clear"),
                    "humidity": item["main"].get("humidity", 50),
                    "wind": round(item.get("wind", {}).get("speed", 0), 1),
                })
            if len(daily_forecast) >= 7:
                break

        return {
            "temperature": f"{temp}°C",
            "condition": condition,
            "humidity": humidity,
            "forecast": daily_forecast,
        }
    except Exception as e:
        print(f"OpenWeatherMap API error: {e}")
        return {}


# ─── Google Maps Geocoding ────────────────────────────────────────────

def geocode_location(place_name: str) -> dict | None:
    """
    Resolve any city or place name to lat/lon using the Google Maps Geocoding API.
    Returns {"lat": ..., "lon": ...} or None.
    """
    api_key = config.GOOGLE_MAPS_API_KEY
    if not api_key:
        return None
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": place_name, "key": api_key}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "OK" and data.get("results"):
            loc = data["results"][0]["geometry"]["location"]
            return {"lat": loc["lat"], "lon": loc["lng"]}
    except Exception as e:
        print(f"Geocoding error for '{place_name}': {e}")
    return None


# ═══════════════════════════════════════════════════════════════════════
# ─── MULTI-MODAL TRANSPORT SEARCH ────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════

def search_transport_options(origin: str, destination: str, date_from: str | None = None) -> dict:
    """
    Search ALL transport modes between two cities:
    1. Flights (SerpAPI / mock)
    2. Driving (Google Maps Directions)
    3. Transit / Train (Google Maps Directions)
    4. Bus estimates
    5. LLM-powered recommendation of best option

    date_from: optional YYYY-MM-DD (from validated profile); defaults to 7 days from now.
    Returns a dict with transport options and a recommendation.
    """
    journey_date = date_from if date_from else _get_next_date(7)
    results = {
        "flights": [],
        "trains": [],
        "buses": [],
        "driving": None,
        "recommendation": "",
    }

    # 1. Flights
    flights = search_flights(origin, destination, depart_date=journey_date)
    results["flights"] = flights

    # 2. Google Maps Directions — driving
    driving = _google_maps_route(origin, destination, mode="driving")
    if driving:
        results["driving"] = {
            "mode": "🚗 Cab / Self-Drive",
            "duration": driving.get("duration", ""),
            "distance": driving.get("distance", ""),
            "estimated_cost": _estimate_cab_cost(driving.get("distance_value", 0)),
            "currency": "INR",
            "route_summary": driving.get("summary", ""),
            "steps_count": driving.get("steps_count", 0),
            "booking_tip": "Book via Ola/Uber for cabs, or Zoomcar for self-drive",
        }

    # 2.5 Trains: try RailRadar first (avoids IRCTC rate limits), then IRCTC RapidAPI
    results["_rapidapi_checked"] = True
    railradar_trains = _search_trains_railradar(origin, destination, journey_date=journey_date)
    if isinstance(railradar_trains, list) and railradar_trains:
        results["trains"] = railradar_trains
    else:
        rapidapi_trains = _search_trains_rapidapi(origin, destination, journey_date=journey_date)
        if rapidapi_trains == "NO_DIRECT_TRAINS":
            results["trains"] = []
            results["_no_direct_trains"] = True
        elif isinstance(rapidapi_trains, list) and rapidapi_trains:
            results["trains"] = rapidapi_trains
        else:
            # RapidAPI returned None (rate limit) or [] (missing key).  
            # We have no conclusive train data, so let Google Maps Directions try.
            results["_rapidapi_checked"] = False
        
    # 3. Google Maps Directions — transit (trains/buses)
    transit = _google_maps_route(origin, destination, mode="transit")
    if transit:
        # Parse transit steps for train/bus details
        for step in transit.get("steps", []):
            travel_mode = step.get("travel_mode", "")
            line = step.get("transit_details", {})

            if travel_mode == "TRANSIT" and line:
                vehicle_type = line.get("line", {}).get("vehicle", {}).get("type", "")
                line_name = line.get("line", {}).get("name", "") or line.get("line", {}).get("short_name", "")
                departure = line.get("departure_stop", {}).get("name", "")
                arrival = line.get("arrival_stop", {}).get("name", "")
                num_stops = line.get("num_stops", 0)
                dep_time = line.get("departure_time", {}).get("text", "")
                arr_time = line.get("arrival_time", {}).get("text", "")

                entry = {
                    "mode": vehicle_type,
                    "name": line_name,
                    "from_station": departure,
                    "to_station": arrival,
                    "departure_time": dep_time,
                    "arrival_time": arr_time,
                    "num_stops": num_stops,
                    "duration": step.get("duration", {}).get("text", ""),
                    "booking_tip": "",
                }

                if vehicle_type in ("HEAVY_RAIL", "COMMUTER_TRAIN", "HIGH_SPEED_TRAIN", "LONG_DISTANCE_TRAIN", "RAIL"):
                    # Only add if we didn't use RapidAPI or if RapidAPI wasn't explicit about no trains
                    if not results.get("_rapidapi_checked", False):
                        entry["booking_tip"] = "Book on IRCTC (irctc.co.in) or via ConfirmTkt"
                        entry["estimated_cost"] = None  # No hardcoded fare; check IRCTC for real price
                        entry["currency"] = "INR"
                        results["trains"].append(entry)
                elif vehicle_type in ("BUS", "INTERCITY_BUS"):
                    # Only add bus if it looks like intercity (duration >= 1 hour), not local transit.
                    # Use overall transit duration/cost to avoid short segment artifacts.
                    step_duration_sec = step.get("duration", {}).get("value", 0)
                    if step_duration_sec >= 3600:
                        entry["booking_tip"] = "Book on RedBus or AbhiBus"
                        total_dist_m = transit.get("distance_value", 0) or (results.get("driving") or {}).get("distance_value", 0) or 0
                        entry["duration"] = transit.get("duration", entry.get("duration", ""))
                        entry["estimated_cost"] = (
                            _estimate_bus_cost(total_dist_m)
                            if total_dist_m
                            else _estimate_bus_cost(step.get("distance", {}).get("value", 0))
                        )
                        entry["currency"] = "INR"
                        entry["duration_estimated"] = True
                        entry["cost_estimated"] = True
                        results["buses"].append(entry)

    # 4. If no intercity bus from transit, add one estimated bus option (always, when we have route distance)
    if not results["buses"] and driving:
        dist_km = driving.get("distance_value", 0) / 1000
        if dist_km > 0:
            results["buses"].append({
                "mode": "BUS",
                "name": f"{origin} to {destination} Bus",
                "from_station": f"{origin} ISBT",
                "to_station": f"{destination} Bus Stand",
                "duration": _estimate_bus_duration(dist_km),
                "estimated_cost": _estimate_bus_cost(driving.get("distance_value", 0)),
                "currency": "INR",
                "booking_tip": "Book on RedBus (redbus.in) or AbhiBus",
                "duration_estimated": True,
                "cost_estimated": True,
            })

    # 5. No hardcoded fallback trains — show only real API results (RailRadar/IRCTC). If none, trains list stays empty.

    # 5.5 Sanity-check buses (fix impossible times / costs)
    _sanitize_bus_options(results)

    # 6. Build smart recommendation
    results["recommendation"] = _build_transport_recommendation(results, origin, destination)

    return results


def _google_maps_route(origin: str, destination: str, mode: str = "driving") -> dict | None:
    """Get route info from Google Maps Directions API."""
    api_key = config.GOOGLE_MAPS_API_KEY
    if not api_key:
        return None

    try:
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "key": api_key,
            "alternatives": "true",
        }
        if mode == "transit":
            params["transit_routing_preference"] = "fewer_transfers"

        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "OK" or not data.get("routes"):
            return None

        route = data["routes"][0]
        leg = route["legs"][0]

        result = {
            "duration": leg.get("duration", {}).get("text", ""),
            "duration_value": leg.get("duration", {}).get("value", 0),
            "distance": leg.get("distance", {}).get("text", ""),
            "distance_value": leg.get("distance", {}).get("value", 0),
            "summary": route.get("summary", ""),
            "start_address": leg.get("start_address", ""),
            "end_address": leg.get("end_address", ""),
            "steps_count": len(leg.get("steps", [])),
            "steps": [],
        }

        # Extract detailed steps for transit
        if mode == "transit":
            for step in leg.get("steps", []):
                step_info = {
                    "travel_mode": step.get("travel_mode", ""),
                    "duration": step.get("duration", {}),
                    "distance": step.get("distance", {}),
                    "instructions": step.get("html_instructions", ""),
                }
                if step.get("transit_details"):
                    td = step["transit_details"]
                    step_info["transit_details"] = {
                        "departure_stop": td.get("departure_stop", {}),
                        "arrival_stop": td.get("arrival_stop", {}),
                        "departure_time": td.get("departure_time", {}),
                        "arrival_time": td.get("arrival_time", {}),
                        "num_stops": td.get("num_stops", 0),
                        "line": td.get("line", {}),
                    }
                result["steps"].append(step_info)

        return result
    except Exception as e:
        print(f"Google Maps Directions API error ({mode}): {e}")
        return None


def _estimate_cab_cost(distance_meters: int) -> int:
    """Estimate cab fare (INR) based on distance."""
    km = distance_meters / 1000
    # ~₹12/km base + ₹150 base fare, typical for Ola/Uber intercity
    return round(150 + km * 12)


def _estimate_bus_cost(distance_meters: int) -> int:
    """Estimate bus fare (INR) — AC bus."""
    km = distance_meters / 1000
    # ~₹1.5/km for AC bus
    return round(km * 1.5)


def _estimate_bus_duration(dist_km: float) -> str:
    """Estimate bus duration."""
    # Average 40 km/h for buses (includes stops / hill-road buffers)
    hours = dist_km / 40 if dist_km > 0 else 0
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m}m"


def _duration_text_to_minutes(text: str) -> int:
    """Parse common duration strings into minutes."""
    if not text:
        return 0
    t = str(text).strip().lower()
    minutes = 0
    try:
        import re
        h = re.search(r"(\d+)\s*h", t)
        m = re.search(r"(\d+)\s*m", t)
        hr = re.search(r"(\d+)\s*hour", t)
        mn = re.search(r"(\d+)\s*min", t)

        if h:
            minutes += int(h.group(1)) * 60
        if m:
            minutes += int(m.group(1))
        if hr:
            minutes = max(minutes, int(hr.group(1)) * 60)
        if mn and not m:
            # if not already captured by 'Xm'
            if "h" in t:
                minutes += int(mn.group(1))
            else:
                minutes = max(minutes, int(mn.group(1)))
    except Exception:
        return 0
    return minutes


def _sanitize_bus_options(results: dict) -> None:
    """
    Fix obviously wrong bus durations/costs coming from transit segment artifacts.
    Uses driving distance when available.
    """
    buses = results.get("buses") or []
    driving = results.get("driving") or {}
    dist_m = driving.get("distance_value", 0) or 0
    dist_km = dist_m / 1000 if dist_m else 0
    if not buses or not dist_km:
        return

    driving_mins = _duration_text_to_minutes(driving.get("duration", ""))
    min_plausible_mins = max(60, int((dist_km / 80) * 60))  # 80 km/h avg is already optimistic
    if driving_mins:
        min_plausible_mins = max(min_plausible_mins, int(driving_mins * 0.75))

    est_duration = _estimate_bus_duration(dist_km)

    for b in buses:
        # Normalize cost using whole-route distance
        if dist_m and (b.get("estimated_cost") is None or b.get("estimated_cost", 0) < 50):
            b["estimated_cost"] = _estimate_bus_cost(dist_m)
            b["currency"] = b.get("currency") or "INR"
            b["cost_estimated"] = True

        mins = _duration_text_to_minutes(b.get("duration", ""))
        if mins < min_plausible_mins:
            b["duration"] = est_duration
            b["duration_estimated"] = True

    # De-dup by name+duration
    seen = set()
    deduped = []
    for b in buses:
        key = (str(b.get("name", "")).strip().lower(), str(b.get("duration", "")).strip().lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(b)
    results["buses"] = deduped


def _build_transport_recommendation(results: dict, origin: str, destination: str) -> str:
    """Use LLM or rules to recommend the best transport option."""
    options = []

    for f in results.get("flights", [])[:2]:
        options.append(f"✈️ Flight: {f.get('airline', '')} {f.get('flight_number', '')} — ₹{f.get('price', 0):,}, {f.get('duration', '')}")

    for t in results.get("trains", [])[:2]:
        options.append(f"🚆 Train: {t.get('name', '')} — ~₹{t.get('estimated_cost', 0):,}, {t.get('duration', '')}")

    for b in results.get("buses", [])[:2]:
        options.append(f"🚌 Bus: {b.get('name', '')} — ~₹{b.get('estimated_cost', 0):,}, {b.get('duration', '')}")

    if results.get("driving"):
        d = results["driving"]
        options.append(f"🚗 Cab: {d.get('distance', '')} — ~₹{d.get('estimated_cost', 0):,}, {d.get('duration', '')}")

    if not options:
        return f"I couldn't find transport options from {origin} to {destination}. Try checking nearby major cities."

    # Neutral: show all options first; user says "cheapest" / "fastest" / "optimize" to pick
    return (
        "Here are all options above. Say **cheapest**, **fastest**, or **optimize** "
        "and I'll pick the best combination for you."
    )


def web_search_destination(destination: str, queries: list = None) -> list:
    """
    Search the web for travel knowledge about a destination.
    Priority:
      1. Tavily (AI-optimized search, best for agents)
      2. Exa (neural web crawler, great for travel blogs)
      3. LLM knowledge (always available with OpenAI key)
    Returns a list of knowledge snippets with sources.
    """
    if queries is None:
        queries = [
            f"{destination} travel guide tips 2025",
            f"{destination} best time to visit hidden gems local tips",
            f"{destination} things to know before visiting budget tips food",
        ]

    results = []

    # ── Method 1: Tavily Search ──────────────────────────────────────────
    tavily_key = config.TAVILY_API_KEY
    if tavily_key and tavily_key != "your_tavily_key_here":
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)

            for query in queries[:2]:
                response = client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=4,
                    include_answer=True,
                    include_raw_content=False,
                )

                # Include the synthesized answer if present
                if response.get("answer"):
                    results.append({
                        "title": f"About {destination}",
                        "snippet": response["answer"],
                        "source": "Tavily AI Search",
                        "url": "",
                        "type": "web_search",
                        "category": "general",
                    })

                # Individual search results
                for item in response.get("results", [])[:3]:
                    if item.get("content"):
                        results.append({
                            "title": item.get("title", ""),
                            "snippet": item["content"][:300],
                            "source": item.get("url", "").split("/")[2] if "/" in item.get("url", "") else item.get("url", ""),
                            "url": item.get("url", ""),
                            "type": "web_search",
                            "category": "general",
                        })

            print(f"✅ Tavily: fetched {len(results)} results for {destination}")
        except ImportError:
            print("Tavily not installed — run: pip install tavily-python")
        except Exception as e:
            print(f"Tavily search error: {e}")

    # ── Method 2: Exa Neural Web Crawler ────────────────────────────────
    exa_key = config.EXA_API_KEY
    if exa_key and exa_key != "your_exa_key_here" and len(results) < 5:
        try:
            from exa_py import Exa
            exa = Exa(api_key=exa_key)

            for query in queries[:2]:
                response = exa.search_and_contents(
                    query=query,
                    num_results=3,
                    use_autoprompt=True,          # Exa auto-optimises query for better results
                    text={"max_characters": 400},
                    highlights={"num_sentences": 2, "highlights_per_url": 1},
                    category="travel",
                )

                for result in response.results:
                    snippet = ""
                    if result.highlights:
                        snippet = " ".join(result.highlights)
                    elif hasattr(result, "text") and result.text:
                        snippet = result.text[:300]

                    if snippet:
                        results.append({
                            "title": result.title or "",
                            "snippet": snippet,
                            "source": result.url.split("/")[2] if result.url else "",
                            "url": result.url or "",
                            "type": "web_search",
                            "category": "general",
                        })

            print(f"✅ Exa: fetched {len(results)} results for {destination}")
        except ImportError:
            print("Exa not installed — run: pip install exa-py")
        except Exception as e:
            print(f"Exa crawler error: {e}")

    # ── Method 3: LLM Knowledge (always works with OpenAI key) ──────────
    if config.OPENAI_API_KEY and len(results) < 5:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=config.LLM_MODEL, api_key=config.OPENAI_API_KEY, temperature=0.3)

            prompt = f"""You are a travel knowledge expert. Provide 6 practical, specific insights about {destination} for a traveler.
Include:
1. Best time to visit & current season tips
2. Local customs / etiquette to respect
3. Safety tips & common scams to avoid
4. Budget tips (how to save money locally)
5. Must-try local food & drinks
6. Hidden gems most tourists miss

Return ONLY valid JSON array:
[{{"title": "short title", "snippet": "2-3 line actionable tip", "category": "safety|food|budget|culture|transport|hidden_gem"}}]"""

            response = llm.invoke(prompt)
            content = response.content.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            llm_tips = json.loads(content)
            for tip in llm_tips:
                results.append({
                    "title": tip.get("title", ""),
                    "snippet": tip.get("snippet", ""),
                    "source": "WanderAI Knowledge",
                    "url": "",
                    "type": "ai_knowledge",
                    "category": tip.get("category", "general"),
                })
        except Exception as e:
            print(f"LLM knowledge error: {e}")

    return results




# ─── RapidAPI (Booking.com Flights) & SerpAPI (Google Flights) ─────────

def _parse_fast_flights_price(raw_price: object, adults: int = 1) -> int | None:
    """
    Convert fast_flights price to per-person INR integer.
    The library returns a total price for all passengers; we divide by adults.
    """
    if raw_price is None:
        return None
    if isinstance(raw_price, (int, float)):
        val = int(round(raw_price))
    else:
        s = str(raw_price).strip().replace(",", "").replace("₹", "").replace(" ", "")
        if not s or s.upper() in ("N/A", "NA"):
            return None
        m = re.search(r"\d+", s)
        if not m:
            return None
        val = int(m.group())
    # Divide by adults when the total looks like a group price
    if adults > 1 and val > 8000 * adults:
        val = int(round(val / adults))
    return val if val > 0 else None


def _fast_flights_route_fallback_price(from_code: str, to_code: str) -> int:
    """Realistic per-ticket INR estimate for common routes when fast_flights returns N/A."""
    route = f"{from_code}-{to_code}".upper()
    intl_india_se_asia = {
        "BOM-HAN", "BOM-SGN", "DEL-HAN", "DEL-SGN", "BLR-HAN", "BLR-SGN",
        "MAA-HAN", "MAA-SGN", "CCU-HAN", "CCU-SGN",
        "HAN-BOM", "SGN-BOM", "HAN-DEL", "SGN-DEL", "HAN-BLR", "SGN-BLR",
        "HAN-MAA", "SGN-MAA", "HAN-CCU", "SGN-CCU",
        "DEL-BKK", "BOM-BKK", "BLR-BKK", "BOM-SIN", "DEL-SIN", "BLR-SIN",
    }
    short_haul_intl = {
        "BOM-DXB", "DEL-DXB", "BLR-DXB", "MAA-DXB",
        "BOM-CMB", "DEL-CMB", "BOM-KTM", "DEL-KTM",
        "DEL-ISB", "DEL-KHI",
    }
    if route in intl_india_se_asia:
        return 17000
    if route in short_haul_intl:
        return 12500
    # Default domestic India
    return 6200


def _search_flights_fast_flights(origin: str, destination: str, depart_date: str | None = None, adults: int = 1) -> list:
    """
    Search Google Flights via the fast_flights scraper library (no API key required).
    Returns results in the same dict format as other flight sources.
    Falls back to an empty list on any error so the caller can try the next source.
    """
    try:
        from fast_flights import FlightData, Passengers, get_flights
    except ImportError:
        return []

    from_code = _get_airport_code(origin)
    to_code = _get_airport_code(destination)
    date = depart_date or _get_next_date(7)

    try:
        result = get_flights(
            flight_data=[FlightData(date=date, from_airport=from_code, to_airport=to_code)],
            trip="one-way",
            seat="economy",
            passengers=Passengers(adults=max(1, adults), children=0, infants_in_seat=0, infants_on_lap=0),
            fetch_mode="fallback",
        )
    except Exception:
        # fast_flights may fail with 401/auth errors depending on Google's bot detection;
        # silently fall through to SerpAPI / mock fallback
        return []

    flights = []
    for f in (result.flights or [])[:8]:
        raw_price = getattr(f, "price", None)
        per_person = _parse_fast_flights_price(raw_price, adults)
        if not per_person:
            per_person = _fast_flights_route_fallback_price(from_code, to_code)

        raw_stops = getattr(f, "stops", 0)
        stops = 0
        if isinstance(raw_stops, int):
            stops = raw_stops
        elif isinstance(raw_stops, str):
            m = re.search(r"\d+", raw_stops)
            stops = int(m.group()) if m else (0 if "non" in raw_stops.lower() else 1)

        airline = (
            getattr(f, "name", None)
            or getattr(f, "carrier", None)
            or getattr(f, "airline", None)
            or "Unknown"
        )
        duration_raw = getattr(f, "duration", "") or ""
        dep_raw = getattr(f, "departure", "") or ""
        arr_raw = getattr(f, "arrival", "") or ""

        # Normalise duration to "Xh Ym"
        dur_sec = _parse_duration_sec(str(duration_raw))
        duration_str = f"{dur_sec // 3600}h {(dur_sec % 3600) // 60}m" if dur_sec else str(duration_raw)

        flights.append({
            "airline": str(airline),
            "flight_number": "",
            "departure": str(dep_raw),
            "arrival": str(arr_raw),
            "duration": duration_str,
            "price": per_person,
            "currency": "INR",
            "class": "Economy",
            "booking_url": f"https://www.google.com/flights#search;f={from_code};t={to_code};d={date}",
            "stops": stops,
            "_duration_sec": dur_sec,
            "_source": "fast_flights",
        })

    return flights


def _search_flights_rapidapi(origin: str, destination: str, depart_date: str | None = None) -> list:
    """Search for flights using Booking.com RapidAPI (booking-com15)."""
    api_key = config.RAPIDAPI_KEY
    if not api_key or api_key == "your_rapidapi_key_here":
        return []

    from_id = _get_airport_code(origin)
    to_id = _get_airport_code(destination)
    if "ooty" in destination.lower():
        to_id = "CJB"
    if "ooty" in origin.lower():
        from_id = "CJB"

    url = "https://booking-com15.p.rapidapi.com/api/v1/flights/searchFlights"
    params = {
        "fromId": f"{from_id}.AIRPORT",
        "toId": f"{to_id}.AIRPORT",
        "departDate": depart_date or _get_next_date(7),
        "stops": "none",
        "pageNo": 1,
        "adults": 1,
        "children": "0,17",
        "sort": "BEST",
        "cabinClass": "ECONOMY",
        "currency_code": "INR",
    }
    headers = {
        "x-rapidapi-host": "booking-com15.p.rapidapi.com",
        "x-rapidapi-key": api_key,
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"RapidAPI Flights error: {e}")
        return []

    if not data.get("status") or not data.get("data"):
        return []

    offers = data.get("data", {}).get("flightOffers", [])
    flights = []
    for offer in offers[:10]:
        segments = offer.get("segments", [])
        if not segments:
            continue
        first_seg = segments[0]
        legs = first_seg.get("legs", [])
        if not legs:
            continue

        # Price: units + nanos / 1e9
        price_breakdown = offer.get("priceBreakdown") or {}
        total = price_breakdown.get("total") or {}
        units = total.get("units")
        nanos = total.get("nanos")
        price = _price_from_units_nanos(units, nanos)
        currency = (total.get("currencyCode") or "INR").strip()

        # Use integer rupees for display when currency is INR
        if currency == "INR" and price >= 1:
            price = round(price)

        dep_time = first_seg.get("departureTime", "")[:16]  # "2023-11-25T01:20"
        arr_time = first_seg.get("arrivalTime", "")[:16]
        dep_display = _format_iso_time(dep_time) if dep_time else ""
        arr_display = _format_iso_time(arr_time) if arr_time else ""

        total_sec = first_seg.get("totalTime") or 0
        duration = f"{total_sec // 3600}h {(total_sec % 3600) // 60}m"

        carrier_data = (legs[0].get("carriersData") or [{}])[0]
        airline = carrier_data.get("name", "Unknown")
        code = carrier_data.get("code", "")
        flight_num = legs[0].get("flightInfo", {}).get("flightNumber", "")
        flight_number = f"{code}-{flight_num}" if code and flight_num else (code or str(flight_num) or "")

        stops = max(0, len(legs) - 1)
        token = offer.get("token", "")
        booking_url = f"https://www.booking.com/flights?token={token}" if token else ""

        flights.append({
            "airline": airline,
            "flight_number": flight_number,
            "departure": dep_display,
            "arrival": arr_display,
            "duration": duration,
            "price": price,
            "currency": currency,
            "class": "Economy",
            "booking_url": booking_url,
            "stops": stops,
            "_duration_sec": total_sec,
        })
        if len(flights) >= 15:
            break

    return flights


def _format_iso_time(iso_str: str) -> str:
    """Format ISO datetime '2023-11-25T01:20:00' to '01:20 AM'."""
    if not iso_str or "T" not in iso_str:
        return iso_str
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%I:%M %p").lstrip("0")
    except Exception:
        part = iso_str.split("T")[-1][:5]
        return part if part else iso_str


def _filter_and_sort_flights(flights: list) -> list:
    """Filter out unreasonable domestic results and sort by price (cheapest first)."""
    if not flights:
        return []
    MAX_DURATION_SEC = 6 * 3600
    MAX_PRICE_INR = 80000
    filtered = [
        f for f in flights
        if f.get("_duration_sec", _parse_duration_sec(f.get("duration", ""))) <= MAX_DURATION_SEC
        and (f.get("currency") != "INR" or f.get("price", 0) <= MAX_PRICE_INR)
    ]
    for f in filtered:
        f.pop("_duration_sec", None)
    if not filtered:
        for f in flights:
            f.pop("_duration_sec", None)
        filtered = flights
    return sorted(filtered, key=lambda x: x.get("price", 0))


def _train_fare_from_api(t: dict) -> int | None:
    """Extract fare/cost from train API object if present. Returns None if not available."""
    if t.get("fare") is not None:
        try:
            return int(t["fare"])
        except (TypeError, ValueError):
            pass
    if t.get("baseFare") is not None:
        try:
            return int(t["baseFare"])
        except (TypeError, ValueError):
            pass
    if t.get("price") is not None:
        try:
            return int(t["price"])
        except (TypeError, ValueError):
            pass
    fares = t.get("fares") or t.get("fareBreakup")
    if isinstance(fares, list) and fares:
        f = fares[0]
        if isinstance(f, dict) and f.get("fare") is not None:
            try:
                return int(f["fare"])
            except (TypeError, ValueError):
                pass
        if isinstance(f, dict) and f.get("Fare") is not None:
            try:
                return int(f["Fare"])
            except (TypeError, ValueError):
                pass
    return None


def _parse_duration_sec(duration_str: str) -> int:
    """Parse '2h 50m' or '26h 52m' to seconds. Returns 0 if unparseable."""
    import re
    try:
        parts = re.findall(r"(\d+)\s*[hm]", duration_str.strip().lower())
        if len(parts) >= 2:
            return int(parts[0]) * 3600 + int(parts[1]) * 60
        if len(parts) == 1:
            return int(parts[0]) * 3600 if "h" in duration_str.lower() else int(parts[0]) * 60
    except Exception:
        pass
    return 0


def search_flights(origin: str, destination: str, depart_date: str | None = None, adults: int = 1) -> list:
    """
    Search for flights with a 4-tier fallback chain:
      1. RapidAPI (Booking.com) — real prices, requires RAPIDAPI_KEY
      2. fast_flights            — Google Flights scraper, no API key needed
      3. SerpAPI                 — Google Flights via SerpAPI, requires SERPAPI_API_KEY
      4. Mock data               — hardcoded fallback
    Returns results filtered and sorted cheapest first.
    """
    # 1. Booking.com via RapidAPI
    rapidapi_flights = _search_flights_rapidapi(origin, destination, depart_date=depart_date)
    if rapidapi_flights:
        return _filter_and_sort_flights(rapidapi_flights)

    # 2. fast_flights (Google Flights scraper — free, no key required)
    fast_results = _search_flights_fast_flights(origin, destination, depart_date=depart_date, adults=adults)
    if fast_results:
        print(f"fast_flights returned {len(fast_results)} results for {origin} → {destination}")
        return _filter_and_sort_flights(fast_results)

    # 3. SerpAPI Google Flights
    api_key = config.SERPAPI_API_KEY
    is_real_key = api_key and api_key != "your_serpapi_key_here"

    if is_real_key:
        try:
            from serpapi import GoogleSearch
            params = {
                "engine": "google_flights",
                "departure_id": _get_airport_code(origin),
                "arrival_id": _get_airport_code(destination),
                "outbound_date": depart_date or _get_next_date(7),
                "currency": "INR",
                "hl": "en",
                "api_key": api_key,
            }

            if "ooty" in destination.lower():
                params["arrival_id"] = "CJB"
            if "ooty" in origin.lower():
                params["departure_id"] = "CJB"

            search = GoogleSearch(params)
            results = search.get_dict()

            flights = []
            for flight_group in results.get("best_flights", []) + results.get("other_flights", []):
                for leg in flight_group.get("flights", []):
                    dur_val = leg.get("duration", 0)
                    duration_str = f"{dur_val // 60}h {dur_val % 60}m"
                    flights.append({
                        "airline": leg.get("airline", "Unknown"),
                        "flight_number": leg.get("flight_number", ""),
                        "departure": leg.get("departure_airport", {}).get("time", ""),
                        "arrival": leg.get("arrival_airport", {}).get("time", ""),
                        "duration": duration_str,
                        "price": flight_group.get("price", 0),
                        "currency": "INR",
                        "class": "Economy",
                        "booking_url": flight_group.get("booking_token", ""),
                        "stops": len(flight_group.get("flights", [])) - 1,
                        "_duration_sec": dur_val * 60 if isinstance(dur_val, (int, float)) else _parse_duration_sec(duration_str),
                    })
                if len(flights) >= 15:
                    break

            if flights:
                return _filter_and_sort_flights(flights)
        except Exception as e:
            print(f"SerpAPI error: {e}")

    # 4. Mock fallback
    mock = _get_mock_flights(origin, destination)
    for f in mock:
        f["_duration_sec"] = _parse_duration_sec(f.get("duration", ""))
    return _filter_and_sort_flights(mock)


def _search_trains_railradar(origin: str, destination: str, journey_date: str | None = None) -> list | None:
    """
    Search for trains between two Indian cities using the RailRadar API.

    RailRadar (railradar.in) is a live-tracking API; it supports departures at a
    station via GET /api/v1/stations/{code}/trains.  We fetch departures at the
    origin station, filter for trains that also stop at the destination, and
    return the matching services.  This avoids the "between-stations" endpoint
    which the API does not support (it only accepts a 5-digit train number).
    """
    api_key = config.RAILRADAR_API_KEY
    if not api_key or api_key == "your_railradar_api_key_here":
        return None

    orig_codes = get_station_codes_for_city(origin)
    dest_codes = get_station_codes_for_city(destination)
    orig_code = orig_codes[0] if orig_codes else ""
    dest_code = dest_codes[0] if dest_codes else ""
    if not orig_code or not dest_code:
        return None

    base = "https://api.railradar.org"
    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json",
        "User-Agent": "WanderAI-Travel/1.0",
    }

    # Fetch trains departing from origin station
    station_endpoints = [
        f"/api/v1/stations/{orig_code}/trains",
        f"/api/v1/station/{orig_code}/trains",
        f"/api/v1/stations/{orig_code}/departures",
    ]

    raw_list = None
    for path in station_endpoints:
        try:
            resp = requests.get(base + path, headers=headers, timeout=15)
            if resp.status_code in (400, 401, 403, 404):
                continue
            resp.raise_for_status()
            data = resp.json()
            candidate = data.get("trains") or data.get("data") or data.get("departures")
            if isinstance(data, list):
                candidate = data
            if isinstance(candidate, list) and candidate:
                raw_list = candidate
                break
        except Exception:
            continue

    if not raw_list:
        return None

    # Filter for trains that also serve the destination station
    dest_code_lower = dest_code.lower()
    matched: list = []
    for t in raw_list:
        route = t.get("route") or t.get("stations") or t.get("stops") or []
        route_codes = [
            (s.get("stationCode") or s.get("code") or s.get("station_code") or "").lower()
            for s in route
            if isinstance(s, dict)
        ]
        if dest_code_lower in route_codes:
            matched.append(t)
        if len(matched) >= 10:
            break

    if not matched:
        return None

    trains = []
    for t in matched:
        duration_raw = t.get("duration", t.get("travelTime", t.get("journeyTime", "")))
        if isinstance(duration_raw, (int, float)):
            duration_str = f"{int(duration_raw // 60)}h {int(duration_raw % 60):02d}m"
        elif duration_raw:
            duration_str = str(duration_raw).replace(":", "h ", 1) + "m" if "h" not in str(duration_raw).lower() else str(duration_raw)
        else:
            duration_str = ""

        fare = _train_fare_from_api(t)
        trains.append({
            "mode": "TRAIN",
            "name": t.get("train_name", t.get("trainName", t.get("name", ""))),
            "train_number": t.get("train_number", t.get("trainNo", t.get("number", ""))),
            "from_station": t.get("from_station_name", t.get("fromStationName", orig_code)),
            "to_station": t.get("to_station_name", t.get("toStationName", dest_code)),
            "duration": duration_str,
            "departure_time": t.get("from_std", t.get("departureTime", t.get("departure", ""))),
            "arrival_time": t.get("to_sta", t.get("arrivalTime", t.get("arrival", ""))),
            "estimated_cost": fare,
            "currency": "INR",
            "booking_tip": "Book on IRCTC (irctc.co.in)",
        })

    return trains if trains else None


def _search_trains_rapidapi(origin: str, destination: str, journey_date: str | None = None) -> list | str:
    """Search for Indian trains using IRCTC RapidAPI. Tries primary station pair, then one alternate if no results."""
    api_key = config.RAPIDAPI_KEY
    if not api_key or api_key == "your_rapidapi_key_here":
        return []

    orig_candidates = get_station_codes_for_city(origin)
    dest_candidates = get_station_codes_for_city(destination)
    if not orig_candidates or not dest_candidates:
        return "NO_DIRECT_TRAINS"

    pairs_to_try = [(orig_candidates[0], dest_candidates[0])]
    if len(orig_candidates) > 1:
        pairs_to_try.append((orig_candidates[1], dest_candidates[0]))
    elif len(dest_candidates) > 1:
        pairs_to_try.append((orig_candidates[0], dest_candidates[1]))

    for orig_code, dest_code in pairs_to_try:
        try:
            url = "https://irctc1.p.rapidapi.com/api/v3/trainBetweenStations"
            querystring = {
                "fromStationCode": orig_code,
                "toStationCode": dest_code,
                "dateOfJourney": journey_date or _get_next_date(7),
            }
            headers = {
                "x-rapidapi-host": "irctc1.p.rapidapi.com",
                "x-rapidapi-key": api_key,
            }
            resp = requests.get(url, headers=headers, params=querystring, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            raw_list = data.get("data") or data.get("trains")
            if not raw_list:
                continue

            trains = []
            for t in (raw_list[:10] if isinstance(raw_list, list) else []):
                duration_str = t.get("duration", t.get("travelTime", "10:00"))
                if isinstance(duration_str, (int, float)):
                    duration_str = f"{int(duration_str // 60)}:{int(duration_str % 60):02d}"
                try:
                    parts = str(duration_str).replace("H", ":").replace("h", ":").strip().split(":")
                    h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
                    dur_display = f"{h}h {m}m"
                except Exception:
                    dur_display = str(duration_str)
                fare = _train_fare_from_api(t)
                trains.append({
                    "mode": "TRAIN",
                    "name": t.get("train_name", t.get("trainName", "")),
                    "train_number": t.get("train_number", t.get("trainNo", "")),
                    "from_station": t.get("from_station_name", t.get("fromStationName", "")),
                    "to_station": t.get("to_station_name", t.get("toStationName", "")),
                    "duration": dur_display,
                    "departure_time": t.get("from_std", t.get("departureTime", "")),
                    "arrival_time": t.get("to_sta", t.get("arrivalTime", "")),
                    "estimated_cost": fare,
                    "currency": "INR",
                    "booking_tip": "Book on IRCTC (irctc.co.in)",
                })
            if trains:
                return trains
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                print("IRCTC RapidAPI rate limited (429). Add RAILRADAR_API_KEY to use RailRadar for trains.")
                return None
            print(f"RapidAPI Train Error ({orig_code}–{dest_code}): {e}")
        except Exception as e:
            print(f"RapidAPI Train Error ({orig_code}–{dest_code}): {e}")

    return "NO_DIRECT_TRAINS"


def _get_mock_flights(origin: str, destination: str) -> list:
    """Get mock flights as fallback."""
    orig = origin.lower().replace(" ", "_")
    dest = destination.lower().replace(" ", "_")
    route = f"{orig}_to_{dest}"
    for key in MOCK_FLIGHTS.keys():
        if route == key or (orig in key and dest in key):
            return MOCK_FLIGHTS[key]
    return list(MOCK_FLIGHTS.values())[0]


def _price_from_units_nanos(units: int | None, nanos: int | None) -> float:
    """Convert API price (units + nanos) to actual decimal price. actual_price = units + (nanos / 1_000_000_000)."""
    u = int(units) if units is not None else 0
    n = int(nanos) if nanos is not None else 0
    return u + (n / 1_000_000_000)


def _get_airport_code(city: str) -> str:
    """Resolve city name to IATA airport code via Tavily/Exa search (cached). No hardcoded list."""
    city_clean = city.strip()
    if not city_clean:
        return "XXX"
    code = _fetch_airport_code_via_search(city_clean)
    if code:
        return code
    # Fallback only when search unavailable or found nothing
    return city_clean[:3].upper() if len(city_clean) >= 3 else "XXX"


def _get_next_date(days_from_now: int = 7) -> str:
    """Get a date N days from now in YYYY-MM-DD format."""
    from datetime import datetime, timedelta
    return (datetime.now() + timedelta(days=days_from_now)).strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════════════════════
# ─── DESTINATION CLASSIFIER & RENTAL OPTIONS ─────────────────────────
# ═══════════════════════════════════════════════════════════════════════

_HILL_STATIONS = {
    "manali", "shimla", "mussoorie", "nainital", "ooty", "kodaikanal",
    "darjeeling", "gangtok", "coorg", "munnar", "leh", "ladakh", "spiti",
    "rishikesh", "haridwar", "mcleod ganj", "dharamsala", "kasol", "kufri",
    "dalhousie", "chamba", "bir billing", "kalpa", "chitkul", "auli",
    "chopta", "kedarnath", "badrinath", "lansdowne", "chakrata", "binsar",
    "lonavala", "mahabaleshwar", "matheran", "panchgani", "amboli",
    "chikmagalur", "sakleshpur", "wayanad", "vagamon", "thekkady",
}
_BEACH_DESTINATIONS = {
    "goa", "pondicherry", "varkala", "kovalam", "kanyakumari", "rameswaram",
    "puri", "digha", "mandarmani", "kashid", "alibaug", "tarkarli",
    "murudeshwar", "gokarna", "karwar", "bekal", "marari", "alappuzha",
    "havelock", "andaman", "lakshadweep", "diu", "daman",
}
_HERITAGE_DESTINATIONS = {
    "jaipur", "jodhpur", "udaipur", "jaisalmer", "agra", "fatehpur sikri",
    "khajuraho", "hampi", "mysore", "madurai", "thanjavur", "mahabalipuram",
    "ajanta", "ellora", "aurangabad", "bidar", "bijapur", "badami",
}
_SPIRITUAL_DESTINATIONS = {
    "varanasi", "rishikesh", "haridwar", "vrindavan", "mathura", "ayodhya",
    "tirupati", "shirdi", "amritsar", "bodh gaya", "puri", "dwarka",
    "somnath", "nashik", "ujjain",
}

# Per-day rental estimates in INR (low, mid, high)
_RENTAL_RATES = {
    "bike":    (300,  600,  1000),   # Royal Enfield / sports bikes
    "scooter": (250,  450,   700),   # Honda Activa / Suzuki Access
    "car":     (1200, 2000, 3500),   # Hatchback / Sedan / SUV
    "cycle":   (100,  200,   350),   # For slow scenic routes
}


def _web_search_rental_shops(destination: str, vehicle_type: str, max_results: int = 5) -> list[dict]:
    """
    Lightweight web fallback for rental shops (Tavily/Exa) when Places isn't available
    or returns nothing. Returns [{shop_name, website, maps_link, rating, image_url}].
    """
    vehicle_type = (vehicle_type or "").strip().lower()
    if vehicle_type not in ("bike", "scooter", "car", "cycle"):
        return []

    # Generic images (keeps UI nice even without Places photos)
    img_map = {
        "bike": "https://images.unsplash.com/photo-1525160354320-d8e92641c563?auto=format&fit=crop&q=80&w=600",
        "scooter": "https://images.unsplash.com/photo-1583258292688-d0213dc5a3a8?auto=format&fit=crop&q=80&w=600",
        "car": "https://images.unsplash.com/photo-1525609004556-c46c7d6cf023?auto=format&fit=crop&q=80&w=600",
        "cycle": "https://images.unsplash.com/photo-1485965120184-e220f721d03e?auto=format&fit=crop&q=80&w=600",
    }

    queries = [
        f"{vehicle_type} rental in {destination} price per day",
        f"best {vehicle_type} rental shop {destination}",
    ]

    shops: list[dict] = []
    seen = set()

    # Tavily
    tavily_key = config.TAVILY_API_KEY
    if tavily_key and tavily_key != "your_tavily_key_here":
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=tavily_key)
            for q in queries[:1]:
                resp = client.search(
                    query=q,
                    search_depth="basic",
                    max_results=max_results,
                    include_answer=False,
                    include_raw_content=False,
                )
                for item in resp.get("results", [])[:max_results]:
                    title = (item.get("title") or "").strip()
                    url = (item.get("url") or "").strip()
                    if not title:
                        continue
                    key = title.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    shops.append({
                        "shop_name": title,
                        "website": url,
                        "maps_link": f"https://www.google.com/maps/search/?api=1&query={title.replace(' ', '+')}+{destination.replace(' ', '+')}",
                        "rating": 0.0,
                        "image_url": img_map.get(vehicle_type, ""),
                        "_from_web": "tavily",
                    })
        except Exception:
            pass

    # Exa
    exa_key = config.EXA_API_KEY
    if exa_key and exa_key != "your_exa_key_here" and len(shops) < max_results:
        try:
            from exa_py import Exa
            exa = Exa(api_key=exa_key)
            resp = exa.search_and_contents(
                query=queries[0],
                num_results=max_results,
                use_autoprompt=True,
                text={"max_characters": 200},
            )
            for r in resp.results[:max_results]:
                title = (r.title or "").strip()
                url = (r.url or "").strip()
                if not title:
                    continue
                key = title.lower()
                if key in seen:
                    continue
                seen.add(key)
                shops.append({
                    "shop_name": title,
                    "website": url,
                    "maps_link": f"https://www.google.com/maps/search/?api=1&query={title.replace(' ', '+')}+{destination.replace(' ', '+')}",
                    "rating": 0.0,
                    "image_url": img_map.get(vehicle_type, ""),
                    "_from_web": "exa",
                })
        except Exception:
            pass

    return shops[:max_results]


def classify_destination(destination: str) -> str:
    """
    Classify destination into one of: hill_station | beach | heritage | spiritual | city.
    Used to drive smart rental recommendations.
    """
    d = destination.strip().lower()
    if any(h in d for h in _HILL_STATIONS):
        return "hill_station"
    if any(b in d for b in _BEACH_DESTINATIONS):
        return "beach"
    if any(h in d for h in _HERITAGE_DESTINATIONS):
        return "heritage"
    if any(s in d for s in _SPIRITUAL_DESTINATIONS):
        return "spiritual"
    return "city"


def get_rental_options(destination: str, dest_type: str | None = None, vehicle_preference: str | None = None) -> list[dict]:
    """
    Return rental options (bike / scooter / car) for the destination.
    Tries Google Places for real rental shops first; falls back to Tavily/Exa web search,
    and finally to estimated rates (no fake shop names).
    """
    if dest_type is None:
        dest_type = classify_destination(destination)

    # Build vehicle list based on destination type
    if dest_type == "hill_station":
        vehicles = ["bike", "scooter", "car"]
        headline = "🏔️ Hill roads here are stunning — renting a vehicle lets you explore at your own pace!"
        top_pick = {"solo": "bike", "couple": "scooter", "friends": "bike", "family": "car"}
    elif dest_type == "beach":
        vehicles = ["scooter", "bike", "cycle"]
        headline = "🏖️ Riding along the coastline is an experience in itself — grab a scooter!"
        top_pick = {"solo": "bike", "couple": "scooter", "friends": "scooter", "family": "car"}
    elif dest_type == "heritage":
        vehicles = ["scooter", "car", "cycle"]
        headline = "🏰 Heritage lanes are best explored slowly — a scooter or cycle lets you stop anywhere."
        top_pick = {"solo": "cycle", "couple": "scooter", "friends": "scooter", "family": "car"}
    elif dest_type == "spiritual":
        vehicles = ["scooter", "car", "cycle"]
        headline = "🕌 Many ghats and temples are spread across the city — a scooter gives you freedom."
        top_pick = {"solo": "scooter", "couple": "scooter", "friends": "scooter", "family": "car"}
    else:
        vehicles = ["car", "scooter"]
        headline = "🚗 A rental cab or self-drive car is the most convenient way to get around."
        top_pick = {"solo": "scooter", "couple": "car", "friends": "car", "family": "car"}

    pref = (vehicle_preference or "").strip().lower()
    if pref in ("bike", "scooter", "car", "cycle"):
        vehicles = [pref]

    # Try Google Places for real rental shop names, locations, and photos
    api_key = config.GOOGLE_PLACES_API_KEY
    rental_shops: list[dict] = []
    if api_key:
        label_queries = {
            "bike": [f"bike rental in {destination}", f"royal enfield rental in {destination}"],
            "scooter": [f"scooter rental in {destination}", f"activa rental in {destination}"],
            "car": [f"car rental in {destination}", f"self drive car rental in {destination}"],
            "cycle": [f"bicycle rental in {destination}", f"cycle rental in {destination}"],
        }
        for vehicle in vehicles:
            query = (label_queries.get(vehicle) or [f"{vehicle} rental in {destination}"])[0]
            try:
                resp = requests.get(
                    f"{PLACES_BASE}/textsearch/json",
                    params={"query": query, "key": api_key},
                    timeout=10,
                )
                data = resp.json()
                for r in data.get("results", [])[:5]:
                    place_id = r.get("place_id", "")
                    photo_ref = ""
                    if r.get("photos"):
                        photo_ref = r["photos"][0].get("photo_reference", "")
                    photo_url = (
                        f"{PLACES_BASE}/photo?maxwidth=500&photo_reference={photo_ref}&key={api_key}"
                        if photo_ref else ""
                    )
                    rental_shops.append({
                        "vehicle_type": vehicle,
                        "shop_name": r.get("name", ""),
                        "address": r.get("formatted_address", r.get("vicinity", "")),
                        "rating": r.get("rating", 0.0),
                        "maps_link": f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                        "image_url": photo_url,
                        "website": "",
                        "_from_places": True,
                    })
            except Exception:
                pass

    # If Places didn't return anything, try web search per vehicle (Tavily/Exa)
    if not rental_shops:
        for vehicle in vehicles:
            for s in _web_search_rental_shops(destination, vehicle, max_results=5):
                rental_shops.append({
                    "vehicle_type": vehicle,
                    "shop_name": s.get("shop_name", ""),
                    "address": "",
                    "rating": s.get("rating", 0.0),
                    "maps_link": s.get("maps_link", ""),
                    "image_url": s.get("image_url", ""),
                    "website": s.get("website", ""),
                    "_from_web": s.get("_from_web", True),
                })

    # Build rental option cards — multiple shops for the chosen vehicle
    label_map = {
        "bike": "🏍️ Bike Rental",
        "scooter": "🛵 Scooter Rental",
        "car": "🚗 Car Rental",
        "cycle": "🚲 Cycle Rental",
    }

    options: list[dict] = []
    for shop in rental_shops:
        vehicle = shop.get("vehicle_type", "")
        low, mid, high = _RENTAL_RATES.get(vehicle, (500, 1000, 2000))
        options.append({
            "vehicle_type": vehicle,
            "label": label_map.get(vehicle, vehicle.title()),
            "shop_name": shop.get("shop_name") or f"{vehicle.title()} rental in {destination}",
            "maps_link": shop.get("maps_link") or f"https://www.google.com/maps/search/{vehicle}+rental+{destination.replace(' ', '+')}/",
            "shop_rating": shop.get("rating", 0.0),
            "image_url": shop.get("image_url", ""),
            "website": shop.get("website", ""),
            "price_per_day_low": low,
            "price_per_day_mid": mid,
            "price_per_day_high": high,
            "price_label": f"~₹{low}–₹{high}/day (est.)",
            "best_for": ", ".join(k for k, v in top_pick.items() if v == vehicle) or "all",
            "headline": headline,
            "destination_type": dest_type,
        })

    # If absolutely nothing was found, return a single estimated option without a fake shop name
    if not options:
        vehicle = vehicles[0] if vehicles else "car"
        low, mid, high = _RENTAL_RATES.get(vehicle, (500, 1000, 2000))
        options = [{
            "vehicle_type": vehicle,
            "label": label_map.get(vehicle, vehicle.title()),
            "shop_name": f"{vehicle.title()} rentals in {destination}",
            "maps_link": f"https://www.google.com/maps/search/{vehicle}+rental+{destination.replace(' ', '+')}/",
            "shop_rating": 0.0,
            "image_url": "",
            "website": "",
            "price_per_day_low": low,
            "price_per_day_mid": mid,
            "price_per_day_high": high,
            "price_label": f"~₹{low}–₹{high}/day (est.)",
            "best_for": ", ".join(k for k, v in top_pick.items() if v == vehicle) or "all",
            "headline": headline,
            "destination_type": dest_type,
        }]

    # Cap results to keep UI fast
    return options[:6]


# ═══════════════════════════════════════════════════════════════════════
# ─── COMPOSITE RESEARCH FUNCTION ─────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════

def research_destination(
    origin: str,
    destination: str,
    interests: list = None,
    use_mock_fallback: bool = True,
    date_from: str | None = None,
    date_to: str | None = None,
    include_rentals: bool = True,
    rental_preference: str | None = None,
    stay_type: str | None = None,
) -> dict:
    """
    Full research for a destination — combines all API calls.
    date_from / date_to: optional YYYY-MM-DD from validated profile; used for flights and trains.
    """
    dest_key = destination.lower().strip()

    # 1. Multi-modal transport search (use validated date when available)
    transport = search_transport_options(origin, destination, date_from=date_from)

    flights = transport.get("flights", [])
    trains = transport.get("trains", [])
    buses = transport.get("buses", [])
    driving = transport.get("driving")
    transport_recommendation = transport.get("recommendation", "")

    # 2. Lodging — Google Places with mock fallback
    stay_type_norm = (stay_type or "").strip().lower()
    if stay_type_norm == "hostel":
        hotels = search_hostels(destination, check_in=date_from or "", check_out=date_to or "")
    else:
        hotels = search_hotels(destination, check_in=date_from or "", check_out=date_to or "")
    if not hotels and use_mock_fallback:
        for key in MOCK_HOTELS:
            if key in dest_key or dest_key in key:
                hotels = MOCK_HOTELS[key]
                break
        if not hotels:
            hotels = list(MOCK_HOTELS.values())[0]

    # 3. Activities — Google Places with mock fallback
    activities = search_activities(destination, interests)
    if not activities and use_mock_fallback:
        for key in MOCK_ACTIVITIES:
            if key in dest_key or dest_key in key:
                activities = MOCK_ACTIVITIES[key]
                break
        if not activities:
            activities = list(MOCK_ACTIVITIES.values())[0]

    # 4. Weather — OpenWeatherMap with mock fallback
    weather = get_weather(destination)
    if not weather and use_mock_fallback:
        for key in MOCK_WEATHER:
            if key in dest_key or dest_key in key:
                weather = MOCK_WEATHER[key]
                break
        if not weather:
            weather = list(MOCK_WEATHER.values())[0]

    # 5. Web knowledge / travel tips
    web_knowledge = web_search_destination(destination)

    # 6. Local tips from mock + web
    tips = []
    for key in LOCAL_TIPS:
        if key in dest_key or dest_key in key:
            tips = LOCAL_TIPS[key]
            break

    # Merge web knowledge into tips
    for item in web_knowledge:
        if item.get("snippet"):
            tips.append(f"🌐 {item.get('title', '')}: {item['snippet']}")

    # 7. Rental options + destination type (optional)
    dest_type = classify_destination(destination)
    rentals = (
        get_rental_options(destination, dest_type, vehicle_preference=rental_preference)
        if include_rentals
        else []
    )

    return {
        "flights": flights,
        "trains": trains,
        "buses": buses,
        "driving": driving,
        "transport_recommendation": transport_recommendation,
        "hotels": hotels,
        "activities": activities,
        "weather": weather,
        "local_tips": tips,
        "web_knowledge": web_knowledge,
        "rentals": rentals,
        "destination_type": dest_type,
    }
