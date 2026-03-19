# External APIs — Detailed Reference

This document describes **every external API** used by WanderAI: how they are called, from where in the codebase, required environment variables, request/response handling, and fallback behavior.

All API keys are read from the environment via `config.py` (from `.env`). See `.env.example` for variable names.

---

## 1. Google APIs (Places, Maps, Geocoding, Directions)

### 1.1 Google Places API (Text Search — Legacy)

| Item | Detail |
|------|--------|
| **Env var** | `GOOGLE_PLACES_API_KEY` |
| **Used in** | `agents/tools.py` → `search_places()` |
| **Endpoint** | `GET https://maps.googleapis.com/maps/api/place/textsearch/json` |
| **Purpose** | Search for places (hotels, attractions, “things to do”) by text query. |

**How it’s called:**

- `search_places(query, location=None, place_type=None, max_results=5)` builds params: `query` (and optionally `query` = `f"{query} in {location}"`), `key=api_key`. No request body; GET with query params.
- Response: JSON with `status` and `results[]`. Each result has `name`, `formatted_address`, `rating`, `geometry.location` (lat/lng), `photos[0].photo_reference`, `price_level` (0–4), `place_id`, `types`, `user_ratings_total`.
- Code maps these to a list of dicts with `name`, `description`, `location`, `lat`, `lon`, `rating`, `price_level`, `image_url` (from Place Photo API using `photo_reference`), `place_id`, `types`.

**Note:** The legacy Text Search API returns only `price_level` (0–4), not actual prices. Real prices for hotels come from **Booking.com (RapidAPI)**; Places is used for activities and as a possible hotel fallback (see tools).

**Fallback:** If `GOOGLE_PLACES_API_KEY` is missing, `search_places` returns `[]`. Downstream code may then use mock data (e.g. activities/hotels from `data/mock_data.py`).

---

### 1.2 Google Maps Geocoding API

| Item | Detail |
|------|--------|
| **Env var** | `GOOGLE_MAPS_API_KEY` |
| **Used in** | `agents/tools.py` → `geocode_location(place_name)` |
| **Endpoint** | `GET https://maps.googleapis.com/maps/api/geocode/json` |
| **Purpose** | Resolve a place name to latitude/longitude. |

**How it’s called:**

- Params: `address=place_name`, `key=api_key`. GET only.
- Response: `status` and `results[]`; first result’s `geometry.location` has `lat` and `lng`.
- Returns `{"lat": ..., "lon": ...}` or `None` on missing key or error.

**Fallback:** Returns `None` if key is missing or request fails; callers must handle missing geocode.

---

### 1.3 Google Maps Directions API

| Item | Detail |
|------|--------|
| **Env var** | `GOOGLE_MAPS_API_KEY` |
| **Used in** | `agents/tools.py` → `_google_maps_route(origin, destination, mode)` |
| **Endpoint** | `GET https://maps.googleapis.com/maps/api/directions/json` |
| **Purpose** | Get route (driving or transit) between two places; used for cab/drive duration and distance, and for transit steps (trains/buses). |

**How it’s called:**

- Params: `origin`, `destination`, `mode` (`driving` or `transit`), `key`, `alternatives=true`. For `transit`, also `transit_routing_preference=fewer_transfers`.
- Response: `routes[0].legs[0]` gives `duration`, `distance`, `start_address`, `end_address`, `steps[]`. For transit, each step can have `transit_details` (line, departure/arrival stop and time, num_stops).
- Code builds a single dict with `duration`, `duration_value`, `distance`, `distance_value`, `summary`, `start_address`, `end_address`, `steps_count`, and for transit a detailed `steps` list. This is used by `search_transport_options()` to fill:
  - **Driving:** `results["driving"]` (plus estimated cab cost from `_estimate_cab_cost(distance_value)`).
  - **Transit:** Parses steps to append to `results["trains"]` or `results["buses"]` (by vehicle type and duration).

**Fallback:** If key is missing or request fails, `_google_maps_route` returns `None`; transport search then has no driving/transit from Maps.

---

## 2. OpenWeatherMap API

| Item | Detail |
|------|--------|
| **Env var** | `OPENWEATHERMAP_API_KEY` |
| **Used in** | `agents/tools.py` → `get_weather(destination)` |
| **Endpoints** | `GET https://api.openweathermap.org/data/2.5/weather` and `GET https://api.openweathermap.org/data/2.5/forecast` |
| **Purpose** | Current weather and multi-day forecast for the destination. |

**How it’s called:**

- Params: `q=destination`, `appid=api_key`, `units=metric`. Same params for both endpoints.
- Current: from `main.temp`, `weather[0].main`, `main.humidity`.
- Forecast: from `list[]` items; code picks one per day (e.g. 12:00) and builds `daily_forecast` with date, temp, condition, humidity, wind.
- Returns a dict: `temperature`, `condition`, `humidity`, `forecast` (list of daily summaries). On missing key or error, returns `{}`.

**Fallback:** In `research_destination()`, if `get_weather()` returns empty, mock weather is used from `MOCK_WEATHER` in `data/mock_data.py` (keyed by destination string).

---

## 3. RapidAPI — Booking.com (Hotels)

| Item | Detail |
|------|--------|
| **Env var** | `RAPIDAPI_KEY` |
| **Used in** | `agents/tools.py` → `_search_booking_destination()`, `_search_hotels_booking_api()`, and `search_hotels()` |
| **Host / endpoints** | `booking-com.p.rapidapi.com`: `/v1/hotels/locations`, `/v1/hotels/search` |
| **Purpose** | Resolve destination name to Booking.com `dest_id`/`dest_type`, then search hotels with **real prices**. |

**How it’s called:**

1. **Locations (resolve destination)**  
   - `_search_booking_destination(destination)`  
   - GET `https://booking-com.p.rapidapi.com/v1/hotels/locations` with headers `X-RapidAPI-Key`, `X-RapidAPI-Host: booking-com.p.rapidapi.com`, params `name=destination`, `locale=en-gb`.  
   - Response: list of items; code takes first with `dest_type` in `["city", "region"]` and caches `{dest_id, dest_type, name}` per destination.

2. **Hotel search**  
   - `_search_hotels_booking_api(destination, checkin_date, checkout_date, currency, adults, max_results)`  
   - GET `https://booking-com.p.rapidapi.com/v1/hotels/search` with same headers; params include `dest_id`, `dest_type`, `checkin_date`, `checkout_date`, `adults_number`, `room_number`, `locale`, `currency`, `units=metric`, `order_by=popularity`, `filter_by_currency`, `page_number`.  
   - Response: `result[]` with `price_breakdown.gross_price`, `hotel_name`, `city`, `address`, `review_score`, `review_nr`, `main_photo_url`/`max_photo_url`, `url`, `latitude`, `longitude`, etc.  
   - Code computes `price_per_night` from gross price and nights, maps to `price_category` (Budget / Inexpensive / Moderate / Expensive / Very Expensive), and returns a list of hotel dicts with `has_real_price: True`.

**Flow:** `search_hotels()` always tries Booking.com first; if dates are missing, it uses default dates (tomorrow + 2 nights). If Booking returns no results, it returns `[]` (there is commented/unreachable fallback to Google Places + Tavily baseline in the same file).

**Fallback:** If `RAPIDAPI_KEY` is missing or calls fail, hotel list is empty; `research_destination()` then uses `MOCK_HOTELS` from `data/mock_data.py`.

---

## 4. RapidAPI — Booking.com Flights

| Item | Detail |
|------|--------|
| **Env var** | `RAPIDAPI_KEY` |
| **Used in** | `agents/tools.py` → `_search_flights_rapidapi()`, called from `search_flights()` |
| **Host / endpoint** | `booking-com15.p.rapidapi.com` → `GET /api/v1/flights/searchFlights` |
| **Purpose** | Search flights with real prices (tried first before SerpAPI/mock). |

**How it’s called:**

- Params: `fromId`, `toId` (IATA airport codes + `.AIRPORT`), `departDate` (YYYY-MM-DD), `stops=none`, `pageNo`, `adults`, `children`, `sort=BEST`, `cabinClass=ECONOMY`, `currency_code=INR`. Headers: `x-rapidapi-host`, `x-rapidapi-key`.
- Origin/destination cities are converted to IATA codes via `_get_airport_code()` (which uses **Tavily** or **Exa** search + regex; see below). Special case: Ooty → `CJB`.
- Response: `data.flightOffers[]`; each offer has `segments[].legs[]`, `priceBreakdown.total` (units + nanos). Code maps to a list of flight dicts (airline, flight_number, departure/arrival times, duration, price, currency, booking_url from token, stops). Prices are converted with `_price_from_units_nanos(units, nanos)`.

**Fallback:** If RapidAPI fails or returns no data, `search_flights()` falls back to **SerpAPI** (Google Flights), then to **mock flights** from `MOCK_FLIGHTS` in `data/mock_data.py`.

---

## 5. SerpAPI (Google Flights)

| Item | Detail |
|------|--------|
| **Env var** | `SERPAPI_API_KEY` |
| **Used in** | `agents/tools.py` → `search_flights()` (after RapidAPI attempt) |
| **Usage** | `serpapi` package: `GoogleSearch(params).get_dict()` with engine `google_flights` |
| **Purpose** | Flight search when RapidAPI Booking.com flights are not used or fail. |

**How it’s called:**

- Params: `engine=google_flights`, `departure_id`, `arrival_id` (IATA from `_get_airport_code()`), `outbound_date`, `currency=INR`, `hl=en`, `api_key`. Same Ooty → CJB override.
- Response: `best_flights` and `other_flights`; each has `flights[]` (per leg) and `price`, `booking_token`. Code flattens into a list of flight objects with `_duration_sec` for filtering.
- Results are filtered and sorted by `_filter_and_sort_flights()` (max duration 6h, max price 80k INR for domestic, etc.). If SerpAPI fails or key is placeholder, mock flights are returned.

**Fallback:** Mock flights from `_get_mock_flights(origin, destination)` (from `MOCK_FLIGHTS`).

---

## 6. RailRadar API (Indian Railways)

| Item | Detail |
|------|--------|
| **Env var** | `RAILRADAR_API_KEY` |
| **Used in** | `agents/tools.py` → `_search_trains_railradar()` |
| **Base URL** | `https://api.railradar.org` (docs: https://railradar.in/docs) |
| **Purpose** | Train search between Indian stations (avoids IRCTC rate limits). |

**How it’s called:**

- Station codes are resolved by `get_station_codes_for_city()` which uses a **one-time-fetched** list from a public JSON URL (Indian Railway station codes), then in-memory lookup by city/station name.
- Several path variants are tried (e.g. `/api/v1/trains/between-stations?from=...&to=...&date=...`) with headers `X-API-Key`, `Accept: application/json`, `User-Agent: WanderAI-Travel/1.0`.
- Response: expects `trains` or `data` or `trainList` (or root as list). Each train has name, number, from/to station, duration, departure/arrival time; fare extracted via `_train_fare_from_api()` (fare/baseFare/price/fares).
- Returns a list of train dicts with `estimated_cost`, `currency=INR`, `booking_tip` (IRCTC). On 400/403/404/401 or parse failure, tries next endpoint or returns `None`.

**Fallback:** If RailRadar is not configured or returns nothing, `search_transport_options()` calls **IRCTC RapidAPI** (`_search_trains_rapidapi`). If that also fails (e.g. 429), train list stays empty.

---

## 7. RapidAPI — IRCTC (Indian Railways)

| Item | Detail |
|------|--------|
| **Env var** | `RAPIDAPI_KEY` |
| **Used in** | `agents/tools.py` → `_search_trains_rapidapi()` |
| **Host / endpoint** | `irctc1.p.rapidapi.com` → `GET /api/v3/trainBetweenStations` |
| **Purpose** | Train search when RailRadar is not used or returns no results. |

**How it’s called:**

- Params: `fromStationCode`, `toStationCode`, `dateOfJourney` (YYYY-MM-DD). Station codes from `get_station_codes_for_city()`. Multiple station pairs are tried (primary + one alternate) if the first returns nothing.
- Response: `data` or `trains` list; same shape as RailRadar for mapping (name, duration, departure/arrival, fare).
- On 429 (rate limit), code prints a message suggesting RailRadar and returns `"NO_DIRECT_TRAINS"` so the graph does not add Google Transit trains as a fallback.

**Fallback:** RailRadar is tried first; if no key or no results, IRCTC is used. If both fail, trains list is empty.

---

## 8. Tavily API (Web Search + AI Answer)

| Item | Detail |
|------|--------|
| **Env var** | `TAVILY_API_KEY` |
| **Used in** | `agents/tools.py` in: `_fetch_airport_code_via_search()`, `_get_hotel_price_baseline()`, `web_search_destination()` |
| **Usage** | `tavily` package: `TavilyClient(api_key=...).search(...)` |
| **Purpose** | (1) Resolve city → IATA code for flights; (2) Hotel price baseline per destination (for estimation when not using Booking.com); (3) Travel knowledge search for destination. |

**How it’s called:**

1. **Airport code:** Query like `"{city} airport IATA code"`, `search_depth="basic"`, `max_results=3`, `include_answer=True`. Answer and result contents are concatenated and scanned with regex for 3-letter IATA codes; result cached in `_airport_code_cache`.
2. **Hotel baseline:** Query like `"average budget hotel price per night in {destination} India INR 2025"`; from answer + snippets, first number in range 500–100000 (INR) is taken and cached in `_hotel_price_baseline_cache`.
3. **Web search:** `web_search_destination(destination, queries)` uses default queries (e.g. “{destination} travel guide tips 2025”, “best time to visit hidden gems…”) and calls `client.search()` with `search_depth="advanced"`, `max_results=4`, `include_answer=True`. Answer becomes one “snippet”; each result item adds title, content slice, source URL. Results are appended to a list used as “web knowledge” and merged into “local tips” in `research_destination()`.

**Fallback:** If key is missing or placeholder (`your_tavily_key_here`), airport lookup returns `None` (then `_get_airport_code()` may use a 3-letter city prefix); hotel baseline returns a default (e.g. 2500); web search adds nothing. Exa and/or LLM are used as additional sources for web knowledge.

---

## 9. Exa API (Neural Web Search)

| Item | Detail |
|------|--------|
| **Env var** | `EXA_API_KEY` |
| **Used in** | `agents/tools.py` → `_fetch_airport_code_via_search()` (if Tavily didn’t yield text), `web_search_destination()` |
| **Usage** | `exa_py` package: `Exa(api_key=...).search_and_contents(...)` |
| **Purpose** | Alternative web search for IATA codes; travel-related web content for destination knowledge. |

**How it’s called:**

- **Airport code:** Same query as Tavily; `search_and_contents` with `num_results=3`, `text={"max_characters": 300}`. Result text/highlights are scanned for IATA codes.
- **Web search:** In `web_search_destination()`, after Tavily, if result count &lt; 5: same destination queries, `search_and_contents` with `num_results=3`, `use_autoprompt=True`, `text={"max_characters": 400}`, `highlights`, `category="travel"`. Each result contributes title, snippet (highlights or text), source host, URL.

**Fallback:** If key is missing or placeholder, Exa is skipped. LLM-based “WanderAI Knowledge” tips can still fill gaps when `OPENAI_API_KEY` is set.

---

## 10. Indian Railway Station List (Public JSON)

| Item | Detail |
|------|--------|
| **Env var** | None (public URL) |
| **Used in** | `agents/tools.py` → `_load_station_list_once()`, `get_station_codes_for_city()` |
| **URL** | `https://raw.githubusercontent.com/mayurrawte/IndianRailApi/master/data/station_codes.json` |
| **Purpose** | Map city/station names to Indian Railway station codes for RailRadar and IRCTC. |

**How it’s called:**

- One-time GET; response is a list containing one dict of “STATION NAME” → “CODE”, or a single dict. Loaded into `_STATION_NAME_TO_CODE` and a word-index `_STATION_WORD_TO_CODES` for fuzzy matching (e.g. “new delhi” → intersection of codes for “new” and “delhi”). Lookup is in-memory only.

**Fallback:** If the fetch fails, `get_station_codes_for_city()` returns `[]` and train search (RailRadar/IRCTC) cannot resolve station codes.

---

## 11. LLM APIs (OpenAI / Anthropic)

| Item | Detail |
|------|--------|
| **Env vars** | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`; `LLM_PROVIDER`, `LLM_MODEL` |
| **Used in** | `agents/intent_parser.py` (OpenAI), `agents/route_planner.py` (OpenAI), `agents/tools.py` → `web_search_destination()` (OpenAI for knowledge tips), `agents/budget_optimizer.py` (if used for LLM), and any other agent that uses LangChain LLM |
| **Purpose** | Intent parsing, itinerary generation, travel tips, and any other LLM-based reasoning. |

**How it’s called:**

- **Intent:** `ChatOpenAI(model=..., api_key=OPENAI_API_KEY, temperature=0).invoke(prompt)` with a structured JSON prompt; response is parsed as JSON into travel_profile fields.
- **Route planning:** Same model used with a long prompt (activities, weather, selected transport/hotel) and asked to return a JSON array of day plans.
- **Web knowledge:** In `web_search_destination()`, if result count &lt; 5 and `OPENAI_API_KEY` is set, a prompt asks for 6 practical insights (best time to visit, customs, safety, budget, food, hidden gems); response is parsed as JSON and appended as “WanderAI Knowledge” snippets.

**Fallback:** If no LLM key, intent parser uses `_keyword_parse_intent()`; route planner uses rule-based itinerary; web knowledge has no LLM branch.

---

## 12. Composite Flow: `research_destination()`

The main aggregation is in `agents/tools.py` → `research_destination(origin, destination, interests, use_mock_fallback, date_from, date_to)`:

1. **Transport:** `search_transport_options(origin, destination, date_from)` → flights (RapidAPI → SerpAPI → mock), trains (RailRadar → IRCTC), driving and transit (Google Directions), buses (from transit or estimated).
2. **Hotels:** `search_hotels(destination, ..., checkin_date, checkout_date)` → Booking.com RapidAPI; if empty and `use_mock_fallback`, use `MOCK_HOTELS`.
3. **Activities:** `search_activities(destination, interests)` → Google Places; if empty and mock fallback, use `MOCK_ACTIVITIES`.
4. **Weather:** `get_weather(destination)` → OpenWeatherMap; if empty and mock fallback, use `MOCK_WEATHER`.
5. **Web knowledge:** `web_search_destination(destination)` → Tavily → Exa → (optional) OpenAI.
6. **Local tips:** From `LOCAL_TIPS` in mock_data plus merged web knowledge snippets.

Return dict: `flights`, `trains`, `buses`, `driving`, `transport_recommendation`, `hotels`, `activities`, `weather`, `local_tips`, `web_knowledge`. This is what the **research** agent sends to the user and stores in `research_results`.

---

## 13. Environment Variables Summary

| Variable | Used for |
|----------|----------|
| `OPENAI_API_KEY` | Intent parsing, route planning, travel knowledge (LLM). |
| `ANTHROPIC_API_KEY` | Alternative LLM (if wired in). |
| `GOOGLE_PLACES_API_KEY` | Places text search (activities, optional hotel fallback). |
| `GOOGLE_MAPS_API_KEY` | Geocoding, Directions (driving + transit). |
| `OPENWEATHERMAP_API_KEY` | Current weather and forecast. |
| `RAPIDAPI_KEY` | Booking.com (hotels + flights), IRCTC trains. |
| `SERPAPI_API_KEY` | Google Flights (fallback after RapidAPI flights). |
| `TAVILY_API_KEY` | Airport IATA lookup, hotel price baseline, web search. |
| `EXA_API_KEY` | IATA lookup fallback, travel web search. |
| `RAILRADAR_API_KEY` | Indian train search (preferred over IRCTC to avoid rate limits). |
| `DEMO_MODE` | `auto` | `true` | `false` — demo when no LLM key. |
| `LLM_PROVIDER` / `LLM_MODEL` | Which LLM to use (e.g. `gpt-4o-mini`). |

All are optional for running the app; missing keys trigger mock data or empty results as described above.
