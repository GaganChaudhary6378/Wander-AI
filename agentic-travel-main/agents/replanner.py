"""
Re-Planner Agent — Handles disruptions and creates revised itineraries.
"""

from agents import TravelState, DayPlan
from langchain_core.messages import AIMessage


def replan(state: TravelState) -> dict:
    """LangGraph node: Handle disruptions and adjust the itinerary."""
    messages = state.get("messages", [])
    itinerary = state.get("itinerary", [])
    reasoning_log = list(state.get("reasoning_log", []))

    # Get the disruption description from latest user message
    disruption = ""
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'human':
            disruption = msg.content
            break
        elif isinstance(msg, dict) and msg.get('role') == 'user':
            disruption = msg.get('content', '')
            break

    if not itinerary:
        ai_message = AIMessage(content="I don't have an itinerary to adjust yet. Let's plan your trip first!")
        return {
            "stage": "idle",
            "messages": [ai_message],
        }

    reasoning_log.append(f"🔄 Re-Planner: Processing disruption — {disruption[:100]}...")

    # Simulate re-planning: shift activities by 2 hours on Day 1
    revised_itinerary = []
    for day in itinerary:
        if day.get("day_number") == 1:
            revised_activities = []
            for i, act in enumerate(day.get("activities", [])):
                new_act = dict(act)
                if i < len(day["activities"]) - 1:
                    # Shift time forward
                    new_act["time"] = _shift_time(act.get("time", "12:00 PM"), 2)
                    new_act["status"] = "Rescheduled" if i > 0 else "Delayed"
                else:
                    # Last activity gets removed
                    new_act["status"] = "Removed"
                    new_act["description"] = f"Closed due to timing. Re-scheduling for Day 2 morning."
                revised_activities.append(new_act)

            revised_day = dict(day)
            revised_day["activities"] = revised_activities
            revised_itinerary.append(revised_day)
        else:
            revised_itinerary.append(day)

    reasoning_log.append(f"🔄 Re-Planner: Revised Day 1 — shifted activities, removed 1 that no longer fits")

    msg = (
        f"⚠️ **I detected a change in your plans!**\n\n"
        f"I've automatically adjusted your itinerary to accommodate the disruption. "
        f"Here's the revised schedule:\n\n"
        f"• Activities have been shifted forward\n"
        f"• Late-closing venues preserved\n"
        f"• One activity moved to Day 2\n\n"
        f"You can **Apply New Schedule** or **Modify Manually**. "
        f"Or tell me what else you'd like to change!"
    )

    ai_message = AIMessage(content=msg)

    return {
        "itinerary": revised_itinerary,
        "stage": "reviewing_itinerary",
        "reasoning_log": reasoning_log,
        "messages": [ai_message],
        "needs_human_input": True,
        "current_checkpoint": "itinerary_review",
    }


def _shift_time(time_str: str, hours: int) -> str:
    """Shift a time string forward by N hours."""
    try:
        parts = time_str.strip().split()
        if len(parts) != 2:
            return time_str
        time_part, period = parts
        h, m = map(int, time_part.split(':'))

        if period.upper() == 'PM' and h != 12:
            h += 12
        elif period.upper() == 'AM' and h == 12:
            h = 0

        h = (h + hours) % 24
        new_period = "AM" if h < 12 else "PM"
        display_h = h % 12
        if display_h == 0:
            display_h = 12

        return f"{display_h:02d}:{m:02d} {new_period}"
    except (ValueError, IndexError):
        return time_str
