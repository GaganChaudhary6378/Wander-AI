"""
Intent Parser Agent — Extracts structured travel preferences using LLM.
Falls back to keyword matching if LLM is unavailable.
"""

import json
import re
from agents import TravelState
from config import config


def _llm_parse_intent(user_message: str) -> dict | None:
    """Parse intent using OpenAI LLM."""
    if not config.OPENAI_API_KEY:
        return None

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=config.LLM_MODEL,
            api_key=config.OPENAI_API_KEY,
            temperature=0,
        )

        prompt = f"""You are a travel intent parser. Extract structured travel preferences from the user's message into the schema below. Fill every field you can infer from the message; use null ONLY when the user did not mention it at all.

User message: "{user_message}"

CRITICAL — "from X to Y" means:
- origin = X (where they leave from)
- destination = Y (where they want to go)
Example: "trip from Delhi to Chandigarh" → origin "Delhi", destination "Chandigarh".

Return ONLY valid JSON with these fields (use null only when not stated):
{{
    "destination": "city/region they want to visit (e.g. after 'to Chandigarh' → Chandigarh)",
    "origin": "departure city (e.g. after 'from Delhi' → Delhi)",
    "dates": "travel dates or 'next weekend'",
    "date_from": "departure date YYYY-MM-DD or null",
    "date_to": "return date YYYY-MM-DD or null (only for return trips)",
    "trip_type": "one_way or return",
    "duration_days": number (e.g. '3 days' → 3),
    "budget": number only (e.g. '10k' or '10000' → 10000),
    "currency": "INR/USD/EUR",
    "travel_style": "backpacking/luxury/family/romantic/adventure/cultural/spiritual",
    "interests": ["list", "of", "interests"],
    "group_size": number,
    "constraints": ["any special requirements"]
}}

Rules:
- Always set origin and destination when user says "from X to Y" or "X to Y".
- "10k" or "10k budget" → budget 10000, currency INR unless $/USD said.
- "3 days" / "for 3 days" → duration_days 3.
- If "return" or "round trip" or "come back", set trip_type "return" and extract date_to if given.
- date_from/date_to as YYYY-MM-DD when possible; e.g. "1 march 2026" → "2026-03-01".
- Use null only for fields the user did not mention."""

        response = llm.invoke(prompt)
        content = response.content.strip()
        # Extract JSON from response (handle markdown code blocks)
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        return json.loads(content)
    except Exception as e:
        print(f"LLM parsing error: {e}")
        return None


def _keyword_parse_intent(user_message: str) -> dict:
    """Simple keyword-based parser as fallback."""
    msg = user_message.lower()

    # Destination detection: explicit list + "to <place>" pattern
    destinations = {
        "rishikesh": "Rishikesh", "goa": "Goa", "tokyo": "Tokyo",
        "kyoto": "Kyoto", "paris": "Paris", "bali": "Bali",
        "london": "London", "europe": "Europe", "manali": "Manali",
        "shimla": "Shimla", "jaipur": "Jaipur", "udaipur": "Udaipur",
        "mumbai": "Mumbai", "bangalore": "Bangalore", "kerala": "Kerala",
        "ladakh": "Ladakh", "kashmir": "Kashmir", "dubai": "Dubai",
        "singapore": "Singapore", "bangkok": "Bangkok", "new york": "New York",
        "chandigarh": "Chandigarh", "amritsar": "Amritsar", "agra": "Agra",
        "varanasi": "Varanasi", "ooty": "Ooty", "coorg": "Coorg",
    }
    destination = None
    for key, val in destinations.items():
        if key in msg:
            destination = val
            break
    # "from X to Y" or "to Y" → Y is destination (capitalize)
    if not destination:
        to_match = re.search(r"\bto\s+([a-z][a-z\s]{1,30}?)(?:\s+with|\s+for|\s+budget|$)", msg)
        if to_match:
            destination = to_match.group(1).strip().title()
    if not destination:
        destination = "Rishikesh"  # fallback only when nothing detected

    # Origin detection: "from X" pattern or known origins list
    origins = {
        "delhi": "Delhi", "mumbai": "Mumbai", "bangalore": "Bangalore",
        "new york": "New York", "chennai": "Chennai", "kolkata": "Kolkata",
        "hyderabad": "Hyderabad", "chandigarh": "Chandigarh",
    }
    origin = None
    from_match = re.search(r"\bfrom\s+([a-z][a-z\s]{1,30}?)(?:\s+to|\s+for|\s+with|$)", msg)
    if from_match:
        raw = from_match.group(1).strip().lower()
        origin = origins.get(raw) or raw.title()
    if not origin:
        for key, val in origins.items():
            if key in msg and (not destination or key not in (destination or "").lower()):
                origin = val
                break
    if not origin:
        origin = "Delhi"  # fallback only when nothing detected

    # Budget
    budget = 15000.0
    currency = "INR"
    budget_match = (
        re.search(r'[₹$€]\s*([0-9,]+)', msg)
        or re.search(r'(\d+)\s*k\s*(?:budget|inr|rs)?', msg)  # 10k, 15k budget
        or re.search(r'(\d{3,})\s*(?:rs|inr|rupees|dollars|usd)?', msg)
    )
    if budget_match:
        raw = budget_match.group(1).replace(',', '')
        num = float(raw)
        budget = num * 1000 if 'k' in msg.lower() and num < 1000 else num
    if '$' in msg or 'usd' in msg or 'dollar' in msg:
        currency = "USD"
    elif '€' in msg or 'eur' in msg:
        currency = "EUR"

    # Duration
    duration = 4
    dur_match = re.search(r'(\d+)\s*(?:day|night)', msg)
    if dur_match:
        duration = int(dur_match.group(1))

    # Group size
    group_size = 1
    if 'solo' in msg:
        group_size = 1
    elif 'couple' in msg or '2 people' in msg:
        group_size = 2
    elif 'family' in msg:
        group_size = 4
    size_match = re.search(r'(\d+)\s*(?:people|person|traveler)', msg)
    if size_match:
        group_size = int(size_match.group(1))

    # Travel style
    style = "backpacking"
    styles = {
        "backpacking": ["backpack", "budget", "cheap", "hostel"],
        "luxury": ["luxury", "premium", "5 star"],
        "family": ["family", "kids", "children"],
        "romantic": ["romantic", "couple", "honeymoon"],
        "adventure": ["adventure", "trek", "rafting"],
        "cultural": ["culture", "museum", "history"],
        "spiritual": ["spiritual", "yoga", "meditation"],
    }
    for s, keywords in styles.items():
        if any(k in msg for k in keywords):
            style = s
            break

    # Interests
    interests = []
    interest_map = {
        "adventure sports": ["adventure", "rafting", "bungee", "trek"],
        "food": ["food", "eat", "cuisine", "dining"],
        "culture": ["culture", "temple", "museum"],
        "nature": ["nature", "beach", "mountain"],
        "spiritual": ["spiritual", "yoga", "meditation"],
        "nightlife": ["nightlife", "bar", "club"],
        "shopping": ["shopping", "market", "mall"],
    }
    for interest, keywords in interest_map.items():
        if any(k in msg for k in keywords):
            interests.append(interest)
    if not interests:
        interests = ["sightseeing", "food"]

    # Trip type and dates
    trip_type = "one_way"
    if any(k in msg for k in ["return", "round trip", "round-trip", "come back", "roundtrip"]):
        trip_type = "return"
    date_from = None
    date_to = None
    from datetime import datetime, timedelta
    # ISO and numeric patterns
    for pat in [r'(\d{4})-(\d{2})-(\d{2})', r'(\d{2})/(\d{2})/(\d{4})', r'(\d{2})-(\d{2})-(\d{4})']:
        m = re.search(pat, msg)
        if m:
            g = m.groups()
            if len(g) == 3:
                try:
                    if len(g[0]) == 4:
                        date_from = f"{g[0]}-{g[1]}-{g[2]}"
                    else:
                        date_from = f"{g[2]}-{g[1]}-{g[0]}"
                    break
                except Exception:
                    pass
    # Natural language: "1 march 2026", "from 1 march 2026", "march 1 2026"
    if not date_from:
        months = "january|february|march|april|may|june|july|august|september|october|november|december"
        nat = re.search(rf"(?:from\s+)?(\d{{1,2}})\s+({months})\s+(\d{{4}})", msg)
        if nat:
            d, mon, y = int(nat.group(1)), nat.group(2).lower()[:3], nat.group(3)
            mon_num = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                       "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}.get(mon[:3], 1)
            try:
                date_from = f"{y}-{mon_num:02d}-{d:02d}"
            except Exception:
                pass
    if not date_from:
        date_from = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    return {
        "destination": destination,
        "origin": origin,
        "dates": "next weekend",
        "date_from": date_from,
        "date_to": date_to,
        "trip_type": trip_type,
        "duration_days": duration,
        "budget": budget,
        "currency": currency,
        "travel_style": style,
        "interests": interests,
        "group_size": group_size,
        "constraints": [],
    }


def parse_intent(state: TravelState) -> dict:
    """LangGraph node: Parse user's travel intent from the latest message."""
    messages = state.get("messages", [])
    reasoning_log = list(state.get("reasoning_log", []))

    # Get the latest user message
    user_message = ""
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'human':
            user_message = msg.content
            break
        elif isinstance(msg, dict) and msg.get('role') == 'user':
            user_message = msg.get('content', '')
            break

    if not user_message:
        return {"error_state": "No user message found to parse", "stage": "idle"}

    # Try LLM first, fall back to keyword parsing
    parsed = _llm_parse_intent(user_message)

    if parsed:
        reasoning_log.append("🤖 Intent Parser: Used GPT-4o-mini for intent extraction")
    else:
        parsed = _keyword_parse_intent(user_message)
        reasoning_log.append("🔤 Intent Parser: Used keyword-based extraction (no LLM key)")

    # Merge with existing profile when we're in validation flow (user answering questions)
    existing = state.get("travel_profile") or {}
    if state.get("stage") == "validating_trip" and existing:
        for key in ("origin", "destination", "dates", "date_from", "date_to", "trip_type",
                    "duration_days", "budget", "currency", "travel_style", "interests", "group_size"):
            if parsed.get(key) is not None and parsed.get(key) != "":
                existing[key] = parsed[key]
        parsed = {**existing, **parsed}

    # Build profile: use only extracted or existing values; do NOT default origin/destination
    # so the validator asks only for fields truly missing from user intent.
    def _str(v):
        if v is None:
            return ""
        s = (v if isinstance(v, str) else str(v)).strip()
        return s if s else ""

    dest = _str(parsed.get("destination") or existing.get("destination"))
    orig = _str(parsed.get("origin") or existing.get("origin"))

    profile = dict(
        destination=dest or None,
        origin=orig or None,
        dates=parsed.get("dates") or existing.get("dates") or "next weekend",
        date_from=parsed.get("date_from") or existing.get("date_from"),
        date_to=parsed.get("date_to") or existing.get("date_to"),
        trip_type=parsed.get("trip_type") or existing.get("trip_type") or "one_way",
        duration_days=parsed.get("duration_days") or existing.get("duration_days") or 4,
        budget=float(parsed.get("budget") or existing.get("budget") or 15000),
        currency=parsed.get("currency") or existing.get("currency") or "INR",
        travel_style=parsed.get("travel_style") or existing.get("travel_style") or "backpacking",
        interests=parsed.get("interests") or existing.get("interests") or ["sightseeing"],
        group_size=parsed.get("group_size") or existing.get("group_size") or 1,
        constraints=parsed.get("constraints") or existing.get("constraints") or [],
        parsed=True,
    )
    # Ensure we don't store empty string for required fields (validator uses get("destination") or "")
    if not profile["destination"]:
        profile["destination"] = None
    if not profile["origin"]:
        profile["origin"] = None

    reasoning_log.append(
        f"🎯 Intent Parser: {profile.get('destination') or '(not set)'} for {profile['duration_days']} days, "
        f"budget {profile['currency']} {profile['budget']}, "
        f"trip_type={profile.get('trip_type', 'one_way')}, "
        f"interests: {', '.join(profile.get('interests', ['sightseeing']))}"
    )

    # Always send to validation node; it will ask questions or confirm
    return {
        "travel_profile": profile,
        "stage": "validating_trip",
        "reasoning_log": reasoning_log,
        "messages": [],
        "confidence": 0.85,
        "needs_human_input": True,
        "current_checkpoint": "validation",
    }
