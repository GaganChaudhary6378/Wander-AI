"""
Preference Collector Agent — Asks 3 short, exciting questions one at a time
right after the user confirms their trip plan (before research starts).

Question flow:
  1. Who's travelling?     → saves companion_type   (solo | couple | friends | family)
  2. What's the hotel vibe? → saves hotel_preference (budget | mid-range | luxury | boutique)
  3. Rent a vehicle?        → saves rental_preference (bike | scooter | car | none)

Checkpoints (stored in current_checkpoint):
  "ask_companion"  → just asked Q1 (or about to)
  "ask_hotel"      → Q1 answered, now asking Q2
  "ask_rental"     → Q2 answered, now asking Q3
  "done"           → all 3 answered → stage = preferences_collected → research starts
"""

from agents import TravelState
from langchain_core.messages import AIMessage


# ── Parsers ────────────────────────────────────────────────────────────────────

def _parse_companion(msg: str) -> str | None:
    m = msg.lower()
    if any(w in m for w in ["family", "kids", "children", "parents", "parent"]):
        return "family"
    if any(w in m for w in ["couple", "partner", "wife", "husband", "girlfriend", "boyfriend", "honeymoon", "romantic", "love"]):
        return "couple"
    if any(w in m for w in ["friends", "group", "gang", "squad", "buddy", "buddies", "mates", "crew", "lads", "girls"]):
        return "friends"
    if any(w in m for w in ["solo", "alone", "myself", "just me", "single", "me only", "1"]):
        return "solo"
    return None


def _parse_hotel(msg: str) -> str | None:
    m = msg.lower()
    if any(w in m for w in ["luxury", "5 star", "five star", "premium", "5star", "high end", "lavish", "splurge"]):
        return "luxury"
    if any(w in m for w in ["boutique", "homestay", "home stay", "airbnb", "villa", "local stay", "unique"]):
        return "boutique"
    if any(w in m for w in ["budget", "hostel", "cheap", "dorm", "oyo", "backpacker", "basic", "1", "2 star", "two star"]):
        return "budget"
    if any(w in m for w in ["mid", "mid-range", "midrange", "3 star", "three star", "standard", "comfortable", "decent", "normal", "good"]):
        return "mid-range"
    return None


def _parse_rental(msg: str) -> str | None:
    m = msg.lower()
    if any(w in m for w in ["none", "no", "nope", "nah", "skip", "don't", "dont", "not", "walk", "without", "no thanks", "no rental", "no rent", "no vehicle"]):
        return "none"
    if any(w in m for w in ["royal enfield", "bullet", "bike", "motorbike", "motorcycle", "two wheel"]):
        return "bike"
    if any(w in m for w in ["scooter", "activa", "scooty", "moped"]):
        return "scooter"
    if any(w in m for w in ["car", "suv", "innova", "swift", "self drive", "self-drive", "four wheel", "4 wheel"]):
        return "car"
    if any(w in m for w in ["cycle", "bicycle", "cycling"]):
        return "cycle"
    return None


# ── Question builders ──────────────────────────────────────────────────────────

def _q1_companion() -> str:
    return """\
🌍 **Awesome, let's make this trip legendary!** First up —

**Who's joining you on this adventure?**

| | |
|---|---|
| 🧍 **Solo** | *"Just me, the road, and the open sky"* |
| 💑 **Couple** | *"Romance mode: ON"* |
| 👯 **Friends** | *"The more, the merrier"* |
| 👨‍👩‍👧 **Family** | *"Making memories together"* |

Select an option below."""


def _q2_hotel() -> str:
    return """\
🛏️ **Love it!** Now — what's your sleeping vibe?

| | |
|---|---|
| 🏕️ **Budget / Hostel** | *"Save money, collect stories"* |
| 🏨 **Mid-range** | *"Comfort without breaking the bank"* |
| ✨ **Luxury** | *"Go big or go home"* |
| 🏡 **Boutique / Homestay** | *"Local is the new luxury"* |

Select an option below."""


def _q3_rental(destination: str, dest_type: str, companion_type: str) -> str:
    dest_name = destination.split(",")[0].strip()

    if dest_type == "hill_station":
        headline = "🏍️ **Last one — Royal Enfield chalaoge?** 🔥"
        subline = (
            f"The {dest_name} mountain roads are calling your name! "
            f"Misty passes, pine forests, hairpin bends — riding through all of it is pure magic. ⛰️"
        )
        options = [
            ("🏍️ **Bike**", '"Born to ride the hills"'),
            ("🛵 **Scooter**", '"Smooth and breezy"'),
            ("🚗 **Car**", '"Comfort & safety first"'),
            ("🚶 **No thanks**", '"I\'ll use local transport"'),
        ]

    elif dest_type == "beach":
        headline = "🛵 **Last one — Scooter pe sawaar ho jaao?** 🌊"
        subline = (
            f"Wind in your hair, ocean on your side — beach hopping on a scooter in {dest_name} "
            f"is an experience you won't forget! 🌴"
        )
        options = [
            ("🛵 **Scooter**", '"Wind. Ocean. Freedom."'),
            ("🏍️ **Bike**", '"Go where the waves take you"'),
            ("🚗 **Car**", '"Beach road trip, AC on"'),
            ("🚶 **No thanks**", '"I\'ll walk the shore"'),
        ]

    elif dest_type == "heritage":
        headline = f"🚲 **Last one — Want to explore {dest_name} on your own wheels?** 🏛️"
        subline = (
            "Heritage lanes, hidden temples, chai stalls in every corner — "
            "a cycle or scooter lets you stop and soak it all in at your own pace. 🛕"
        )
        options = [
            ("🚲 **Cycle**", '"Slow travel, deep experience"'),
            ("🛵 **Scooter**", '"Cover more, miss nothing"'),
            ("🚗 **Car**", '"Family-friendly comfort"'),
            ("🚶 **No thanks**", '"Walking tour for me"'),
        ]

    elif dest_type == "spiritual":
        headline = "🛵 **Last one — Want to explore the ghats & temples freely?** 🕌"
        subline = (
            "Sunrise at the ghats, evening aarti, hidden temples — "
            "a scooter gives you the freedom to catch it all without waiting for autos. 🌅"
        )
        options = [
            ("🛵 **Scooter**", '"Catch every sunrise & aarti"'),
            ("🚲 **Cycle**", '"Peaceful, slow discovery"'),
            ("🚗 **Car**", '"Comfort with the family"'),
            ("🚶 **No thanks**", '"I\'ll walk & take autos"'),
        ]

    else:
        headline = f"🚗 **Last one — Want to rent a vehicle to explore {dest_name} freely?** 🗺️"
        subline = (
            "No more waiting for cabs or auto bargaining — "
            "your own wheels = explore on your own terms, anytime! 🕐"
        )
        options = [
            ("🚗 **Car**", '"Full freedom, AC comfort"'),
            ("🛵 **Scooter**", '"Zip through city lanes"'),
            ("🏍️ **Bike**", '"Biker at heart"'),
            ("🚶 **No thanks**", '"Uber & autos are fine"'),
        ]

    option_rows = "\n".join(f"| {label} | *{desc}* |" for label, desc in options)
    return f"""\
{headline}
{subline}

| | |
|---|---|
{option_rows}

Select an option below."""


# ── Main node ──────────────────────────────────────────────────────────────────

def gather_preferences(state: TravelState) -> dict:
    """
    LangGraph node: Ask companion / hotel / rental questions one at a time.
    Uses current_checkpoint to track which question we're on.
    """
    profile = dict(state.get("travel_profile") or {})
    reasoning_log = list(state.get("reasoning_log", []))
    checkpoint = state.get("current_checkpoint", "")

    # Get latest user message (for parsing their answer to the previous question)
    messages = state.get("messages", [])
    user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            user_msg = msg.content
            break

    destination = profile.get("destination", "")
    group_size = profile.get("group_size", 1)
    # If the user already provided preferences in earlier messages / state, don't ask again.
    # We still ask missing pieces one-by-one so the UI can render as a form.
    existing_companion = (profile.get("companion_type") or "").strip().lower()
    existing_hotel = (profile.get("hotel_preference") or "").strip().lower()
    existing_rental = (profile.get("rental_preference") or "").strip().lower()

    # ── Determine destination type for Q3 ──
    from agents.tools import classify_destination
    dest_type = classify_destination(destination)

    # ── State machine ──────────────────────────────────────────────────────────

    # First call: user just said "yes" to the trip — ask Q1
    if checkpoint not in ("ask_companion", "ask_hotel", "ask_rental"):
        if existing_companion and existing_hotel and existing_rental:
            reasoning_log.append("🎯 Preference Collector: Preferences already present — skipping questions")
            return {
                "travel_profile": profile,
                "stage": "preferences_collected",
                "current_checkpoint": "research_ready",
                "reasoning_log": reasoning_log,
                "messages": [],
                "needs_human_input": False,
            }

        if existing_companion and existing_hotel and not existing_rental:
            reasoning_log.append("🎯 Preference Collector: Starting Q3 — rental preference (Q1/Q2 already set)")
            return {
                "travel_profile": profile,
                "stage": "gathering_preferences",
                "current_checkpoint": "ask_rental",
                "reasoning_log": reasoning_log,
                "messages": [AIMessage(content=_q3_rental(destination, dest_type, existing_companion))],
                "needs_human_input": True,
            }

        if existing_companion and not existing_hotel:
            reasoning_log.append("🎯 Preference Collector: Starting Q2 — hotel preference (Q1 already set)")
            return {
                "travel_profile": profile,
                "stage": "gathering_preferences",
                "current_checkpoint": "ask_hotel",
                "reasoning_log": reasoning_log,
                "messages": [AIMessage(content=_q2_hotel())],
                "needs_human_input": True,
            }

        reasoning_log.append("🎯 Preference Collector: Starting Q1 — companion type")
        return {
            "travel_profile": profile,
            "stage": "gathering_preferences",
            "current_checkpoint": "ask_companion",
            "reasoning_log": reasoning_log,
            "messages": [AIMessage(content=_q1_companion())],
            "needs_human_input": True,
        }

    # Q1 answered → save companion_type, ask Q2
    if checkpoint == "ask_companion":
        companion = _parse_companion(user_msg)
        if companion:
            profile["companion_type"] = companion
            reasoning_log.append(f"🎯 Preference Collector: companion_type = {companion}")
        elif group_size == 1:
            profile.setdefault("companion_type", "solo")
        elif group_size == 2:
            profile.setdefault("companion_type", "couple")
        else:
            profile.setdefault("companion_type", "friends")

        return {
            "travel_profile": profile,
            "stage": "gathering_preferences",
            "current_checkpoint": "ask_hotel",
            "reasoning_log": reasoning_log,
            "messages": [AIMessage(content=_q2_hotel())],
            "needs_human_input": True,
        }

    # Q2 answered → save hotel_preference, ask Q3
    if checkpoint == "ask_hotel":
        hotel_pref = _parse_hotel(user_msg)
        if hotel_pref:
            profile["hotel_preference"] = hotel_pref
            reasoning_log.append(f"🎯 Preference Collector: hotel_preference = {hotel_pref}")
        else:
            profile.setdefault("hotel_preference", "mid-range")

        companion_type = profile.get("companion_type", "solo")
        return {
            "travel_profile": profile,
            "stage": "gathering_preferences",
            "current_checkpoint": "ask_rental",
            "reasoning_log": reasoning_log,
            "messages": [AIMessage(content=_q3_rental(destination, dest_type, companion_type))],
            "needs_human_input": True,
        }

    # Q3 answered → save rental_preference, fire off to research
    if checkpoint == "ask_rental":
        if existing_rental:
            profile.setdefault("rental_preference", existing_rental)
            rental_pref = existing_rental
        else:
            rental_pref = _parse_rental(user_msg)
            if rental_pref:
                profile["rental_preference"] = rental_pref
                reasoning_log.append(f"🎯 Preference Collector: rental_preference = {rental_pref}")
            else:
                profile.setdefault("rental_preference", "none")

        companion = profile.get("companion_type", "solo")
        hotel = profile.get("hotel_preference", "mid-range")
        rental = profile.get("rental_preference", "none")

        rental_emoji = {"bike": "🏍️", "scooter": "🛵", "car": "🚗", "cycle": "🚲", "none": "🚶"}.get(rental, "")
        hotel_emoji = {"budget": "🏕️", "mid-range": "🏨", "luxury": "✨", "boutique": "🏡"}.get(hotel, "🏨")
        companion_emoji = {"solo": "🧍", "couple": "💑", "friends": "👯", "family": "👨‍👩‍👧"}.get(companion, "👤")

        kickoff_msg = (
            f"🔥 **Perfect! Here's your vibe:**\n\n"
            f"> {companion_emoji} **{companion.title()}** · {hotel_emoji} **{hotel.title()} hotel** · "
            f"{rental_emoji} **{rental.title() if rental != 'none' else 'No rental'}**\n\n"
            f"🚀 **Now let me search flights, hotels, trains and everything in {destination}...** "
            f"Hang tight, this takes ~15 seconds! ⏳"
        )

        reasoning_log.append(
            f"✅ Preference Collector: All preferences collected — "
            f"companion={companion}, hotel={hotel}, rental={rental}"
        )
        return {
            "travel_profile": profile,
            "stage": "preferences_collected",
            "current_checkpoint": "research_ready",
            "reasoning_log": reasoning_log,
            "messages": [AIMessage(content=kickoff_msg)],
            "needs_human_input": False,
        }

    # Safety fallback
    return {
        "travel_profile": profile,
        "stage": "preferences_collected",
        "reasoning_log": reasoning_log,
        "messages": [],
        "needs_human_input": False,
    }
