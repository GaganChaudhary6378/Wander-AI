"""
Budget Optimizer Agent — Selects the best transport + hotel combination
from real research data based on user preferences or auto-optimization.

Strategies:
  - "optimize" / "best" → pick best value (rating/price ratio) within budget
  - "cheapest"          → pick lowest cost for each category
  - "comfort"           → pick non-stop flight + highest-rated hotel
  - "flight N"          → pick the Nth listed flight
  - "hotel N"           → pick the Nth listed hotel
"""

import json

from agents import TravelState, BudgetBreakdown
from langchain_core.messages import AIMessage
from config import config


def _llm_parse_change_request(user_message: str) -> dict | None:
    """
    Use the configured OpenAI LLM to classify what the user wants to change
    during the budget approval loop (transport vs stay, hotel vs hostel, etc.).

    Falls back to None when LLM isn't available or parsing fails.
    """
    if not (config.OPENAI_API_KEY and (user_message or "").strip()):
        return None

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=config.LLM_MODEL,
            api_key=config.OPENAI_API_KEY,
            temperature=0,
        )

        prompt = f"""You are a classifier for a travel planning assistant.
Decide what the user is asking to change in their existing plan.

User message: "{user_message}"

Return ONLY valid JSON with these keys:
{{
  "change_transport": true/false,
  "change_stay": true/false,
  "stay_type": "hostel" | "hotel" | "none" | null,
  "transport_type": "flight" | "train" | "bus" | "cab" | "none" | null,
  "hotel_preference": "budget" | "mid-range" | "luxury" | "boutique" | null,
  "rental_preference": "none" | "bike" | "scooter" | "car" | "cycle" | null,
  "companion_type": "solo" | "couple" | "family" | "friends" | null
}}

Rules:
- If the user says hostel/backpacker/dorm/shared room => stay_type="hostel", change_stay=true, hotel_preference="budget".
- If the user says hotel (and not hostel) => stay_type="hotel", change_stay=true.
- "change hotel" / "change to hotel" / "switch to hotel" / "hotel instead" / "hostel to hotel" => stay_type="hotel", change_stay=true.
- "change hostel" / "change to hostel" / "switch to hostel" / "hotel to hostel" => stay_type="hostel", change_stay=true, hotel_preference="budget".
- If the user explicitly says they don't want a hotel/stay/accommodation => stay_type="none", change_stay=true.
- If the user explicitly says they don't want transport => transport_type="none", change_transport=true.
- If the user explicitly asks to remove/cancel their rental or says they don't need a bike/car/rental => rental_preference="none".
- If the user asks for a scooter/bike/car => rental_preference="scooter" | "bike" | "car".
- If the user says "change stay" or "change accommodation" => change_stay=true.
- If the user says change transport / switch to bus/train/flight/cab => change_transport=true.
- Use null only when the user did not imply a value.
"""

        response = llm.invoke(prompt)
        content = (response.content or "").strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return None
        return parsed
    except Exception:
        return None


def _pick_transport(research: dict, user_msg: str, budget: float, currency: str) -> dict | None:
    """Pick the best transport option based on user hint or auto-optimize."""
    flights = research.get("flights", [])
    trains = research.get("trains", [])
    buses = research.get("buses", [])
    driving = research.get("driving")

    user_lower = user_msg.lower()

    # If user said "flight N", pick that specific one
    for i in range(1, 10):
        if f"flight {i}" in user_lower and i <= len(flights):
            f = dict(flights[i - 1])
            f["mode"] = "flight"   # mode must be set AFTER spread
            return f

    # If user said "train N"
    for i in range(1, 10):
        if f"train {i}" in user_lower and i <= len(trains):
            t = dict(trains[i - 1])
            t["mode"] = "train"
            return t

    # If user said "bus N"
    for i in range(1, 10):
        if f"bus {i}" in user_lower and i <= len(buses):
            b = dict(buses[i - 1])
            b["mode"] = "bus"
            return b

    # If user explicitly asks for a mode (not numbered)
    if "bus" in user_lower and buses:
        cheapest_bus = min(buses, key=lambda b: b.get("estimated_cost", 9999))
        b = dict(cheapest_bus)
        b["mode"] = "bus"
        return b
    if "train" in user_lower and trains:
        cheapest_train = min(trains, key=lambda t: t.get("estimated_cost", 9999))
        t = dict(cheapest_train)
        t["mode"] = "train"
        return t
    if "flight" in user_lower and flights:
        cheapest_flight = min(flights, key=lambda f: f.get("price", 9999))
        f = dict(cheapest_flight)
        f["mode"] = "flight"
        return f

    # "cab" or "drive"
    if ("cab" in user_lower or "self-drive" in user_lower or "drive" in user_lower) and driving:
        d = dict(driving)
        d["mode"] = "cab"
        return d

    # Auto-optimize: prefer non-stop flights & best value for money
    # Use 40% of budget for transport (practical for bus/cab heavy routes)
    TRANSPORT_BUDGET = budget * 0.40

    candidates = []

    # Non-stop flights — highest priority
    nonstop = [f for f in flights if f.get("stops", 1) == 0]
    if nonstop:
        cheapest_nonstop = min(nonstop, key=lambda f: f.get("price", 9999))
        if cheapest_nonstop.get("price", 9999) <= TRANSPORT_BUDGET:
            entry = dict(cheapest_nonstop)
            entry["mode"] = "flight"
            entry["_score"] = 4
            candidates.append(entry)

    # Cheapest flight
    if flights:
        cheapest_flight = min(flights, key=lambda f: f.get("price", 9999))
        if cheapest_flight.get("price", 9999) <= TRANSPORT_BUDGET:
            entry = dict(cheapest_flight)
            entry["mode"] = "flight"
            entry["_score"] = 3
            candidates.append(entry)

    # Cheapest train
    if trains:
        cheapest_train = min(trains, key=lambda t: t.get("estimated_cost", 9999))
        if cheapest_train.get("estimated_cost", 9999) <= TRANSPORT_BUDGET:
            entry = dict(cheapest_train)
            entry["mode"] = "train"
            entry["_score"] = 3
            candidates.append(entry)

    # Cheapest bus — always include if exists (buses are cheap)
    if buses:
        cheapest_bus = min(buses, key=lambda b: b.get("estimated_cost", 9999))
        entry = dict(cheapest_bus)
        entry["mode"] = "bus"
        entry["_score"] = 2
        candidates.append(entry)  # Always add bus regardless of budget %

    # Cab / self-drive
    if driving:
        cab_cost = driving.get("estimated_cost", 0)
        entry = dict(driving)
        entry["mode"] = "cab"
        entry["_score"] = 2 if cab_cost <= TRANSPORT_BUDGET else 1
        candidates.append(entry)  # Always add cab as fallback

    if candidates:
        return max(candidates, key=lambda c: c.get("_score", 0))

    # Absolute fallback — pick cheapest of whatever is available
    all_options = []
    for f in flights:
        entry = dict(f); entry["mode"] = "flight"; entry["_cost"] = f.get("price", 9999)
        all_options.append(entry)
    for t in trains:
        entry = dict(t); entry["mode"] = "train"; entry["_cost"] = t.get("estimated_cost", 9999)
        all_options.append(entry)
    for b in buses:
        entry = dict(b); entry["mode"] = "bus"; entry["_cost"] = b.get("estimated_cost", 9999)
        all_options.append(entry)
    if driving:
        entry = dict(driving); entry["mode"] = "cab"; entry["_cost"] = driving.get("estimated_cost", 9999)
        all_options.append(entry)

    if all_options:
        return min(all_options, key=lambda x: x.get("_cost", 9999))

    return None


def _parse_followup_preferences(user_msg: str) -> dict:
    """
    Extract companion type, hotel preference, and rental preference from the
    user's reply to the follow-up questions block.
    Returns a dict with keys: companion_type, hotel_preference, rental_preference.
    """
    msg = user_msg.lower()
    prefs: dict = {}

    # Companion type
    if any(w in msg for w in ["family", "kids", "children", "parents"]):
        prefs["companion_type"] = "family"
    elif any(w in msg for w in ["couple", "partner", "wife", "husband", "girlfriend", "boyfriend", "honeymoon", "romantic"]):
        prefs["companion_type"] = "couple"
    elif any(w in msg for w in ["friends", "group", "gang", "squad", "buddy", "buddies", "mates"]):
        prefs["companion_type"] = "friends"
    elif any(w in msg for w in ["solo", "alone", "myself", "just me", "single"]):
        prefs["companion_type"] = "solo"

    # Hotel preference
    # Note: We check for "hostel" vs "hotel" context to avoid misclassifying
    # "change hostel to hotel" as budget preference
    if any(w in msg for w in ["luxury", "5 star", "five star", "premium", "high end"]):
        prefs["hotel_preference"] = "luxury"
    elif any(w in msg for w in ["boutique", "homestay", "home stay", "airbnb", "villa", "resort"]):
        prefs["hotel_preference"] = "boutique"
    elif any(w in msg for w in ["budget", "dorm", "oyo", "backpacker", "cheap hotel"]):
        prefs["hotel_preference"] = "budget"
    elif "hostel" in msg and "to hotel" not in msg and "hotel instead" not in msg:
        # Only set budget for hostel if user is NOT switching to hotel
        prefs["hotel_preference"] = "budget"
    elif any(w in msg for w in ["mid", "mid-range", "3 star", "three star", "standard", "comfortable"]):
        prefs["hotel_preference"] = "mid-range"

    # Rental preference
    if any(w in msg for w in ["no rental", "no rent", "no bike", "no car", "no scooter", "no vehicle", "no thanks", "no need"]):
        prefs["rental_preference"] = "none"
    elif any(w in msg for w in ["royal enfield", "bullet", "bike rental", "rent a bike", "motorbike"]):
        prefs["rental_preference"] = "bike"
    elif any(w in msg for w in ["scooter", "activa", "scooty"]):
        prefs["rental_preference"] = "scooter"
    elif any(w in msg for w in ["car rental", "rent a car", "self drive", "self-drive", "suv rental"]):
        prefs["rental_preference"] = "car"
    elif any(w in msg for w in ["cycle", "bicycle", "cycling"]):
        prefs["rental_preference"] = "cycle"

    return prefs


def _pick_hotel(research: dict, user_msg: str, budget: float, currency: str, duration: int) -> dict | None:
    """Pick the best hotel based on user hint, hotel_preference, or auto-optimize."""
    hotels = research.get("hotels", [])
    if not hotels:
        return None

    user_lower = user_msg.lower()
    prefs = _parse_followup_preferences(user_msg)
    hotel_pref = prefs.get("hotel_preference", "")
    HOTEL_BUDGET = budget * 0.35

    # Explicit: cheapest hotel
    if any(k in user_lower for k in ["cheapest hotel", "lowest hotel", "cheapest stay", "lowest stay", "cheapest", "lowest"]):
        return min(hotels, key=lambda h: h.get("price_per_night", 999999))

    # If user said "hotel N"
    for i in range(1, 10):
        if f"hotel {i}" in user_lower and i <= len(hotels):
            return hotels[i - 1]

    # Filter by preference tier using inferred price_level
    pref_price_range = {
        "budget":    (0,    2000),
        "mid-range": (2000, 7000),
        "luxury":    (7000, 99999),
        "boutique":  (2000, 12000),
    }
    if hotel_pref and hotel_pref in pref_price_range:
        low_bound, high_bound = pref_price_range[hotel_pref]
        filtered = [h for h in hotels if low_bound <= h.get("price_per_night", 0) <= high_bound]
        if filtered:
            # Best rating within the preferred tier
            return max(filtered, key=lambda h: h.get("rating", 0))

    # Auto-optimize: best rating-to-price ratio within budget
    candidates = []
    for h in hotels:
        total_cost = h.get("price_per_night", 9999) * duration
        if total_cost <= HOTEL_BUDGET:
            rating = h.get("rating", 0)
            price = h.get("price_per_night", 1)
            score = rating / (price / 1000 + 0.1)
            candidates.append({"score": score, **h})

    if candidates:
        return max(candidates, key=lambda h: h.get("score", 0))

    return min(hotels, key=lambda h: h.get("price_per_night", 9999))


def _overbudget_quote(destination: str, over_amount: float, currency: str) -> str:
    """Generate a short, playful line when over budget."""
    over_amount = max(0, float(over_amount or 0))
    # LLM if available
    if config.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=config.LLM_MODEL, api_key=config.OPENAI_API_KEY, temperature=0.7)
            prompt = (
                f"Write ONE short, fun line (max 18 words) to encourage the traveler, "
                f"but mention they're over budget by {currency} {over_amount:,.0f}. "
                f"Destination: {destination}. No emojis."
            )
            resp = llm.invoke(prompt)
            text = (resp.content or "").strip().replace("\n", " ")
            return text[:140]
        except Exception:
            pass

    # Fallback templates
    templates = [
        f"You’re overspending by {currency} {over_amount:,.0f}—comfort costs, but the memories are priceless.",
        f"Over budget by {currency} {over_amount:,.0f}. You can still splurge—just choose where it matters most.",
        f"Budget alert: +{currency} {over_amount:,.0f}. Great trips aren’t always cheap, but we can optimize smartly.",
    ]
    return templates[int(over_amount) % len(templates)]


def _get_transport_cost(transport: dict) -> float:
    """Extract cost from any transport option."""
    if not transport:
        return 0
    mode = transport.get("mode", "")
    if mode == "flight":
        return transport.get("price", 0)
    elif mode in ("train", "bus"):
        return transport.get("estimated_cost", 0)
    elif mode == "cab":
        return transport.get("estimated_cost", 0)
    return 0


def _format_transport(transport: dict, currency: str) -> str:
    """Human-readable transport selection summary."""
    if not transport:
        return "No transport selected"
    mode = transport.get("mode", "")
    cost = _get_transport_cost(transport)
    if mode == "flight":
        stops = transport.get("stops", 0)
        stop_str = "Non-stop" if stops == 0 else f"{stops} stop(s)"
        return (
            f"✈️ {transport.get('airline', 'Flight')} {transport.get('flight_number', '')} "
            f"— **{currency} {cost:,}** | {stop_str} | "
            f"{transport.get('departure', '')} → {transport.get('arrival', '')} | "
            f"{transport.get('duration', '')}"
        )
    elif mode == "train":
        return (
            f"🚆 {transport.get('name', 'Train')} — **{currency} {cost:,}** | "
            f"{transport.get('duration', '')} | Departs {transport.get('departure_time', '')}"
        )
    elif mode == "bus":
        return f"🚌 {transport.get('name', 'Bus')} — **{currency} {cost:,}** | {transport.get('duration', '')}"
    elif mode == "cab":
        return f"🚗 Cab/Self-Drive — **{currency} {cost:,}** | {transport.get('distance', '')} | {transport.get('duration', '')}"
    return f"Transport — {currency} {cost:,}"


def optimize_budget(state: TravelState) -> dict:
    """LangGraph node: Select best transport + hotel from real data and compute budget allocation."""
    profile = state.get("travel_profile", {})
    research = state.get("research_results", {})
    reasoning_log = list(state.get("reasoning_log", []))

    total_budget = profile.get("budget", 15000)
    currency = profile.get("currency", "INR")
    group_size = profile.get("group_size", 1)
    duration = profile.get("duration_days", 3)
    destination = profile.get("destination", "your trip")

    # Get user's latest message to check for preferences
    messages = state.get("messages", [])
    user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            user_msg = msg.content
            break

    reasoning_log.append("💰 Budget Optimizer: Analyzing real options from API data...")

    user_lower = (user_msg or "").strip().lower()
    approved = any(k in user_lower for k in ["looks good", "proceed", "continue", "go ahead", "finalize", "confirm", "yes"])

    # Check if user wants to re-optimize everything
    wants_reoptimize = any(k in user_lower for k in ["optimize", "optimise", "re-optimize", "reoptimize", "refresh", "refetch"])

    # Try LLM classification first (more robust than keywords), then fall back.
    change_req = _llm_parse_change_request(user_msg)
    wants_transport_change = (
        wants_reoptimize or
        (bool(change_req.get("change_transport")) if change_req else
        any(k in user_lower for k in ["change transport", "transport to", "switch transport", "bus", "train", "flight", "cab", "drive", "self-drive", "self drive"]))
    )
    wants_hotel_change = (
        wants_reoptimize or
        (bool(change_req.get("change_stay")) if change_req else
        any(k in user_lower for k in [
            "change hotel", "change hostel", "change stay", "change accommodation",
            "switch hotel", "switch hostel", "switch stay", "switch accommodation",
            "to hotel", "to hostel", "hostel to hotel", "hotel to hostel",
            "use hotel", "use hostel", "prefer hotel", "prefer hostel",
            "want hotel", "want hostel", "hotel instead", "hostel instead",
            "cheapest", "lowest", "budget stay"
        ]))
    )

    # Parse follow-up preferences from the user's reply
    followup_prefs = _parse_followup_preferences(user_msg)
    
    companion_type = followup_prefs.get("companion_type", profile.get("companion_type", ""))
    if change_req and change_req.get("companion_type") is not None:
        companion_type = change_req.get("companion_type")
        
    hotel_preference = followup_prefs.get("hotel_preference", profile.get("hotel_preference", ""))
    
    rental_preference = followup_prefs.get("rental_preference", profile.get("rental_preference", ""))
    if change_req and change_req.get("rental_preference") is not None:
        rental_preference = change_req.get("rental_preference")

    # Store parsed preferences back into profile
    updated_profile = dict(profile)
    if companion_type:
        updated_profile["companion_type"] = companion_type
    if hotel_preference:
        updated_profile["hotel_preference"] = hotel_preference
    if rental_preference:
        updated_profile["rental_preference"] = rental_preference

    # Check if user explicitly wants no stay or no transport
    skip_stay = (change_req and change_req.get("stay_type") == "none") or any(k in user_lower for k in ["no hotel", "no stay", "don't need a hotel", "no accommodation", "without hotel"])
    skip_transport = (change_req and change_req.get("transport_type") == "none") or any(k in user_lower for k in ["no transport", "no flight", "no train", "no bus", "don't need transport", "without transport"])

    if skip_stay:
        wants_hotel_change = True
        updated_profile["stay_type"] = "none"

    if skip_transport:
        wants_transport_change = True
        updated_profile["transport_type"] = "none"

    wants_hotel_specific = any(f"hotel {i}" in user_lower for i in range(1, 10)) or any(f"hostel {i}" in user_lower for i in range(1, 10))
    if wants_hotel_specific:
        wants_hotel_change = True

    # Explicit lodging type override (e.g. "use hostel")
    stay_type = (updated_profile.get("stay_type") or "").strip().lower()
    llm_stay_type = (change_req.get("stay_type") if change_req else None) or None
    llm_hotel_pref = (change_req.get("hotel_preference") if change_req else None) or None

    if llm_hotel_pref and not updated_profile.get("hotel_preference"):
        updated_profile["hotel_preference"] = llm_hotel_pref

    if llm_stay_type in ("hostel", "hotel"):
        stay_type = llm_stay_type
        updated_profile["stay_type"] = llm_stay_type

    # Detect hostel vs hotel from natural language
    # "hostel to hotel" / "change to hotel" / "switch hotel" => wants hotel
    # "hotel to hostel" / "change to hostel" / "switch hostel" => wants hostel
    wants_hotel_type = any(phrase in user_lower for phrase in [
        "to hotel", "change hotel", "switch hotel", "hotel instead",
        "hostel to hotel", "use hotel", "prefer hotel", "want hotel"
    ])
    wants_hostel_type = any(phrase in user_lower for phrase in [
        "to hostel", "change hostel", "switch hostel", "hostel instead",
        "hotel to hostel", "use hostel", "prefer hostel", "want hostel"
    ])
    
    # Check for simple "hostel" or "hotel" mentions (but not in compound phrases already handled)
    if not wants_hotel_type and not wants_hostel_type:
        if "hostel" in user_lower and "hotel" not in user_lower:
            wants_hostel_type = True
        elif "hotel" in user_lower and "hostel" not in user_lower:
            wants_hotel_type = True

    # Apply the detected stay type
    if wants_hostel_type:
        stay_type = "hostel"
        updated_profile["stay_type"] = "hostel"
        updated_profile["hotel_preference"] = "budget"
    elif wants_hotel_type:
        stay_type = "hotel"
        updated_profile["stay_type"] = "hotel"
        # Keep existing hotel_preference or default to mid-range for hotels
        if not updated_profile.get("hotel_preference") or updated_profile.get("hotel_preference") == "budget":
            updated_profile["hotel_preference"] = "mid-range"

    # If user wants hostel, refresh lodging list from Places so we don't reuse cached hotels
    if wants_hotel_change and stay_type == "hostel":
        current = (research.get("hotels") or [])
        already_hostels = bool(current) and all(str(h.get("type", "")).lower() == "hostel" for h in current[:3])
        if not already_hostels:
            try:
                from agents.tools import search_hostels

                refreshed = search_hostels(
                    destination,
                    check_in=updated_profile.get("date_from") or "",
                    check_out=updated_profile.get("date_to") or "",
                )
                if refreshed:
                    research = dict(research)
                    research["hotels"] = refreshed
                    reasoning_log.append(f"🏨 Refreshed lodging: fetched {len(refreshed)} hostel options from Places")
            except Exception:
                pass

    # If user wants hotel (switching from hostel), refresh lodging list with hotels
    if wants_hotel_change and stay_type == "hotel":
        current = (research.get("hotels") or [])
        already_hotels = bool(current) and all(str(h.get("type", "")).lower() == "hotel" for h in current[:3])
        if not already_hotels:
            try:
                from agents.tools import search_hotels

                refreshed = search_hotels(
                    destination,
                    check_in=updated_profile.get("date_from") or "",
                    check_out=updated_profile.get("date_to") or "",
                )
                if refreshed:
                    research = dict(research)
                    research["hotels"] = refreshed
                    reasoning_log.append(f"🏨 Refreshed lodging: fetched {len(refreshed)} hotel options from Places")
            except Exception:
                pass

    # ── Step 1: Pick transport ──
    prior_transport = state.get("selected_transport")
    if skip_transport:
        transport = None
    elif prior_transport and not wants_transport_change:
        transport = prior_transport
    else:
        transport = _pick_transport(research, user_msg, total_budget, currency)
    transport_cost = _get_transport_cost(transport)

    # ── Step 2: Pick hotel ──
    prior_hotel = state.get("selected_hotel")
    if skip_stay:
        hotel = None
    elif prior_hotel and not wants_hotel_change:
        hotel = prior_hotel
    else:
        hotel = _pick_hotel(research, user_msg, total_budget, currency, duration)
    hotel_cost = hotel.get("price_per_night", 0) * duration if hotel else 0

    # ── Step 2b: Pick rental option if requested ──
    rentals = research.get("rentals", [])
    selected_rental = None
    rental_cost = 0
    if rental_preference and rental_preference != "none" and rentals:
        selected_rental = next(
            (r for r in rentals if r.get("vehicle_type") == rental_preference), None
        )
        if not selected_rental and rentals:
            selected_rental = rentals[0]
        if selected_rental:
            rental_cost = selected_rental.get("price_per_day_mid", 0) * duration

    # ── Step 3: Calculate remaining for food, activities, misc ──
    fixed_costs = transport_cost + hotel_cost + rental_cost
    remaining_after_fixed = total_budget - fixed_costs

    if remaining_after_fixed < 0:
        # Over budget — recommend cheapest alternatives
        warning = f"⚠️ Your selected options ({currency} {fixed_costs:,}) exceed the total budget ({currency} {total_budget:,})."
    else:
        warning = None

    # Distribute remaining realistically
    if remaining_after_fixed <= 0:
        food_per_day = 0
        food_total = 0
        activities_budget = 0
        misc = 0
        total_allocated = fixed_costs
    else:
        food_per_day = max(200, remaining_after_fixed * 0.40 / duration)
        food_total = round(food_per_day * duration)
        activities_budget = round(remaining_after_fixed * 0.35)
        misc = round(remaining_after_fixed * 0.10)
        # Recalculate to not exceed and never go negative
        activities_budget = max(0, min(activities_budget, remaining_after_fixed - food_total - misc))
        misc = max(0, min(misc, remaining_after_fixed - food_total - activities_budget))
        total_allocated = transport_cost + hotel_cost + food_total + activities_budget + misc

    breakdown: BudgetBreakdown = {
        "accommodation": hotel_cost,
        "transport": transport_cost,
        "food": food_total,
        "activities": activities_budget,
        "miscellaneous": misc,
        "total": total_allocated,
        "per_person": round(total_allocated / group_size, 2),
        "remaining": round(total_budget - total_allocated, 2),
    }

    reasoning_log.append(
        f"💰 Budget Optimizer: Selected {transport.get('mode', 'transport') if transport else 'no transport'} "
        f"({currency} {transport_cost:,}) + {hotel.get('name', 'hotel') if hotel else 'no hotel'} "
        f"({currency} {hotel_cost:,})"
        + (f" + {selected_rental.get('label', 'rental')} ({currency} {rental_cost:,})" if selected_rental else "")
        + f". Remaining: {currency} {remaining_after_fixed:,}"
    )

    # ── Build the recommendation message ──
    pref_summary_parts = []
    if companion_type:
        pref_summary_parts.append(f"👥 {companion_type.title()}")
    if hotel_preference:
        if stay_type == "hostel":
            pref_summary_parts.append("🛌 Hostel")
        else:
            pref_summary_parts.append(f"🏨 {hotel_preference.title()} hotel")
    if rental_preference and rental_preference != "none":
        pref_summary_parts.append(f"🏍️ {rental_preference.title()} rental")
    pref_summary = " · ".join(pref_summary_parts)

    msg_parts = [f"**🏆 Here's your optimized plan for {duration} days:**\n"]
    if pref_summary:
        msg_parts.append(f"*Your preferences: {pref_summary}*\n")

    if warning:
        over_by = fixed_costs - total_budget
        msg_parts.append(f"<span style=\"color:#dc2626;font-weight:800;\">{warning}</span>\n")
        msg_parts.append(f"<span style=\"color:#111827;\">{_overbudget_quote(destination, over_by, currency)}</span>\n")

    msg_parts.append("**Selected Transport:**")
    msg_parts.append(_format_transport(transport, currency) if transport else "  No transport option selected/found")

    stay_label = (hotel or {}).get("type") or ("Hostel" if stay_type == "hostel" else "Hotel")
    stay_icon = "🛌" if str(stay_label).lower() == "hostel" else "🏨"
    msg_parts.append(f"\n**Selected {stay_label}:**")
    if hotel:
        name = hotel.get('name', 'Hotel')
        location = hotel.get('location', '')
        maps_link = f"https://www.google.com/maps/search/?api=1&query={name.replace(' ', '+')}+{location.replace(' ', '+')}"
        total_hotel_str = f"~{currency} {hotel.get('price_per_night', 0):,}/night (est.) × {duration} = ~{currency} {hotel_cost:,}"
        # For hostels, Google Hotels can be misleading; prefer website/maps first.
        booking_url = hotel.get("website") or hotel.get("maps_link") or hotel.get("google_hotels_link") or maps_link
        msg_parts.append(
            f"{stay_icon} **{name}** — {total_hotel_str}  "
            f"⭐ {hotel.get('rating', 'N/A')} | {location[:40]} | [Check Prices →]({booking_url})"
        )
    else:
        msg_parts.append("  No stay selected/found within budget")

    # ── Display Alternative Options if requested ──
    if wants_hotel_change and not skip_stay and not wants_hotel_specific:
        available_hotels = research.get("hotels", [])[:5]
        if available_hotels:
            msg_parts.append(f"\n**Available Alternative Options ({stay_type.title() if stay_type else 'Hotel'}s):**")
            for i, h in enumerate(available_hotels, 1):
                msg_parts.append(f"{i}. **{h.get('name', '')}** — ~{currency} {h.get('price_per_night', 0):,}/night | ⭐ {h.get('rating', 'N/A')}")
            msg_parts.append("\n*(Reply with 'hotel 2' to select a specific one, or 'optimize' to let me choose the best value)*")

    if selected_rental:
        msg_parts.append("\n**Selected Rental:**")
        msg_parts.append(
            f"{selected_rental.get('label', '🏍️ Rental')} — **{selected_rental.get('price_label', '')}** "
            f"× {duration} days = ~{currency} {rental_cost:,} (est.)  "
            f"| {selected_rental.get('shop_name', '')} | [Find on Maps →]({selected_rental.get('maps_link', '#')})"
        )

    msg_parts.append("\n**Remaining Budget Allocation:**")
    msg_parts.append(f"🍽️ Food & Dining — **{currency} {food_total:,}** (~{currency} {round(food_per_day):,}/day)")
    msg_parts.append(f"🎯 Activities — **{currency} {activities_budget:,}**")
    msg_parts.append(f"📦 Buffer/Misc — **{currency} {misc:,}**")

    msg_parts.append("\n**━━━━━━━━━━━━━━━━━━━━**")
    budget_bar = total_allocated / total_budget * 100
    msg_parts.append(
        f"💰 **Total: {currency} {total_allocated:,.0f}** / {currency} {total_budget:,} budget "
        f"({budget_bar:.0f}% used)"
    )
    if breakdown["remaining"] > 0:
        msg_parts.append(f"✅ **Savings: {currency} {breakdown['remaining']:,.0f}**")

    # Build dynamic instruction based on current stay type
    current_stay = stay_type or "hotel"
    opposite_stay = "hostel" if current_stay == "hotel" else "hotel"
    msg_parts.append(
        f"\nYou can say **\"change transport\"**, **\"change {current_stay}\"**, "
        f"**\"change to {opposite_stay}\"**, **\"optimize\"**, or **\"looks good\"** "
        "to proceed to your day-by-day itinerary!"
    )

    ai_message = AIMessage(content="\n".join(msg_parts))

    # If user approved ("looks good"), auto-chain to route planning by setting needs_human_input=False.
    if approved:
        return {
            "travel_profile": updated_profile,
            "research_results": research,
            "budget_breakdown": breakdown,
            "selected_transport": transport,
            "selected_hotel": hotel,
            "stage": "confirming_budget",
            "reasoning_log": reasoning_log,
            "messages": [],
            "needs_human_input": False,
            "current_checkpoint": "budget_approved",
        }

    return {
        "travel_profile": updated_profile,
        "research_results": research,
        "budget_breakdown": breakdown,
        "selected_transport": transport,
        "selected_hotel": hotel,
        "stage": "confirming_budget",
        "reasoning_log": reasoning_log,
        "messages": [ai_message],
        "needs_human_input": True,
        "current_checkpoint": "budget_approval",
    }
