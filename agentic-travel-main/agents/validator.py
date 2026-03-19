"""
Validation Agent — Asks user for missing trip details (dates, one-way/return) and validates with Pydantic.
Workflow: Plan (parse_intent) → Validate (this) → Research → Optimize → Execute.
"""

from datetime import date, timedelta

from agents import TravelState, TravelProfile
from agents.schemas import TripRequest, profile_to_trip_request, trip_request_missing_fields
from langchain_core.messages import AIMessage


def _build_validation_questions(missing: list[str]) -> str:
    """Build a short message asking for the missing fields."""
    questions = []
    if "date_from" in missing:
        questions.append("**Travel date (from):** e.g. 2026-03-15 or 'next Friday'")
    if "date_to" in missing:
        questions.append("**Return date (to):** e.g. 2026-03-20")
    if "trip_type" in missing:
        questions.append("**One-way or return trip?**")
    if "origin" in missing:
        questions.append("**From which city** are you travelling?")
    if "destination" in missing:
        questions.append("**Which destination** do you want to visit?")
    if not questions:
        return ""
    return "I need a few details:\n\n" + "\n".join(f"• {q}" for q in questions) + "\n\nReply with the missing info and I'll confirm your plan."


def validate_trip(state: TravelState) -> dict:
    """
    LangGraph node: Validate travel_profile with Pydantic.
    If valid → stage = confirming_intent, show summary and ask "Does this look right?"
    If invalid → stage = validating_trip, ask validation questions for missing fields.
    """
    profile = state.get("travel_profile")
    reasoning_log = list(state.get("reasoning_log", []))

    if not profile:
        return {
            "stage": "parsing_intent",
            "reasoning_log": reasoning_log + ["Validation: No profile to validate"],
            "messages": [AIMessage(content="Tell me where you'd like to go and I'll help you plan. For example: *I want to go from Delhi to Chandigarh with 10k budget for 3 days.*")],
            "needs_human_input": True,
        }

    missing = trip_request_missing_fields(profile)
    trip = profile_to_trip_request(profile)

    if trip is None or missing:
        reasoning_log.append("🔍 Validation: Missing or invalid fields — asking user.")
        question_text = _build_validation_questions(missing)
        if not question_text:
            question_text = (
                "Please confirm your **travel dates** (from and to) and whether you want a **one-way or return** trip. "
                "For example: *March 15 to March 20, return trip.*"
            )
        return {
            "travel_profile": profile,
            "stage": "validating_trip",
            "reasoning_log": reasoning_log,
            "messages": [AIMessage(content=question_text)],
            "needs_human_input": True,
        }

    # Valid: ensure profile has date_from/date_to for downstream (research, flights)
    if isinstance(trip.date_from, date):
        profile["date_from"] = trip.date_from.isoformat()
    if trip.date_to and isinstance(trip.date_to, date):
        profile["date_to"] = trip.date_to.isoformat()
    profile["trip_type"] = trip.trip_type

    reasoning_log.append("✅ Validation: Trip request valid — asking for confirmation.")
    summary = (
        f"Here’s your trip plan:\n\n"
        f"📍 **From:** {trip.origin} → **To:** {trip.destination}\n"
        f"📅 **Departure:** {trip.date_from}\n"
    )
    if trip.trip_type == "return" and trip.date_to:
        summary += f"📅 **Return:** {trip.date_to}\n"
    summary += (
        f"🔄 **Trip type:** {trip.trip_type.replace('_', ' ').title()}\n"
        f"📆 **Duration:** {trip.duration_days} days\n"
        f"💰 **Budget:** {trip.currency} {trip.budget:,.0f}\n"
        f"👥 **Travellers:** {trip.group_size}\n\n"
        f"**Does this look right?** Reply *yes* to start researching options."
    )

    return {
        "travel_profile": profile,
        "stage": "confirming_intent",
        "reasoning_log": reasoning_log,
        "messages": [AIMessage(content=summary)],
        "needs_human_input": True,
    }
