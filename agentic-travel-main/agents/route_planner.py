"""
Route Planner Agent — Creates day-by-day itinerary using LLM or rule-based logic.
"""

import json
from agents import TravelState, DayPlan, ActivityItem
from langchain_core.messages import AIMessage
from config import config


def _llm_plan_route(profile: dict, activities: list, weather: dict, budget: dict, selected_context: dict = None) -> list | None:
    """Use LLM to create a smart day-by-day itinerary."""
    if not config.OPENAI_API_KEY:
        return None

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=config.LLM_MODEL,
            api_key=config.OPENAI_API_KEY,
            temperature=0.3,
        )

        activities_str = json.dumps([{
            "name": a.get("name"),
            "description": a.get("description", "")[:100],
            "cost": a.get("cost", 0),
            "location": a.get("location", ""),
            "category": a.get("category", "activity"),
            "rating": a.get("rating", 0),
            "duration_mins": a.get("duration_mins", 60),
        } for a in activities[:15]], indent=2)

        weather_str = json.dumps(weather.get("forecast", [])[:7], indent=2)

        prompt = f"""Create a {profile.get('duration_days', 4)}-day travel itinerary for {profile.get('destination')}.

Traveler info:
- Style: {profile.get('travel_style')}
- Interests: {', '.join(profile.get('interests', []))}
- Budget: {profile.get('currency')} {profile.get('budget')}
- Group size: {profile.get('group_size')}

Available activities:
{activities_str}

Weather forecast:
{weather_str}

Selected transport & accommodation (MUST incorporate into Day 1):
- Transport: {(selected_context or {}).get('transport_note', 'Arriving by personal transport')}
- Hotel: {(selected_context or {}).get('hotel_note', 'Accommodation arranged')}

Rules:
1. Each day needs 3-5 activities with realistic timings
2. Group nearby activities together
3. Include meal breaks (breakfast, lunch, dinner)
4. Don't schedule outdoor activities during rain
5. Day 1 MUST start with arrival/transport activity, then hotel check-in
6. Last day should be lighter (departure)
7. Give each day a creative theme

Return ONLY valid JSON array:
[
  {{
    "day_number": 1,
    "theme": "Arrival & First Impressions",
    "activities": [
      {{
        "time": "09:00 AM",
        "name": "Activity name",
        "description": "Brief description",
        "cost": 500,
        "location": "Location name",
        "category": "activity|food|transport|rest",
        "duration_mins": 60
      }}
    ]
  }}
]"""

        response = llm.invoke(prompt)
        content = response.content.strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        return json.loads(content)
    except Exception as e:
        print(f"LLM route planning error: {e}")
        return None


def _rule_based_plan(activities: list, duration: int, weather_forecast: list) -> list:
    """Rule-based itinerary planner as fallback."""
    import random
    days = []
    activity_pool = list(activities)
    random.shuffle(activity_pool)

    time_slots = ["09:00 AM", "12:30 PM", "02:00 PM", "04:00 PM", "06:30 PM"]
    themes = ["Arrival & Exploration", "Culture & Discovery", "Adventure Day",
              "Nature & Relaxation", "Local Immersion", "Food & Markets", "Departure Day"]

    for day_num in range(1, duration + 1):
        day_activities = []
        num_activities = min(random.randint(3, 5), len(activity_pool) + 1)

        for slot_idx in range(num_activities):
            if activity_pool:
                act = activity_pool.pop(0)
                day_activities.append(ActivityItem(
                    time=time_slots[slot_idx % len(time_slots)],
                    name=act.get("name", "Activity"),
                    description=act.get("description", ""),
                    cost=act.get("cost", 0),
                    location=act.get("location", ""),
                    category=act.get("category", "activity"),
                    image_url=act.get("image_url", ""),
                    booking_url=act.get("booking_url", ""),
                    rating=act.get("rating", 0),
                    duration_mins=act.get("duration_mins", 60),
                ))
            else:
                day_activities.append(ActivityItem(
                    time=time_slots[slot_idx % len(time_slots)],
                    name="Free time to explore",
                    description="Discover hidden gems at your own pace",
                    cost=0, location="Various", category="sightseeing",
                    image_url="", booking_url="", rating=0, duration_mins=90,
                ))

        weather_str = "Sunny"
        weather_temp = "25°C"
        if weather_forecast and day_num <= len(weather_forecast):
            w = weather_forecast[day_num - 1]
            weather_str = w.get("condition", "Sunny")
            weather_temp = w.get("temp", "25°C")

        estimated_cost = sum(a.get("cost", 0) for a in day_activities)
        days.append(DayPlan(
            day_number=day_num, date=f"Day {day_num}",
            theme=themes[(day_num - 1) % len(themes)],
            activities=day_activities, estimated_cost=estimated_cost,
            weather=weather_str, weather_temp=weather_temp,
        ))

    return days


def plan_route(state: TravelState) -> dict:
    """LangGraph node: Create day-by-day itinerary from research results."""
    profile = state.get("travel_profile", {})
    research = state.get("research_results", {})
    budget = state.get("budget_breakdown", {})
    selected_transport = state.get("selected_transport")
    selected_hotel = state.get("selected_hotel")
    reasoning_log = list(state.get("reasoning_log", []))

    destination = profile.get("destination", "Rishikesh")
    duration = profile.get("duration_days", 4)
    currency = profile.get("currency", "INR")

    activities = research.get("activities", [])
    weather = research.get("weather", {})
    weather_forecast = weather.get("forecast", [])

    # Build extra context for LLM — include selected transport/hotel
    selected_context = {}
    if selected_transport:
        mode = selected_transport.get("mode", "transport")
        if mode == "flight":
            selected_context["transport_note"] = (
                f"Day 1 morning: Arrive by {selected_transport.get('airline', 'flight')} "
                f"{selected_transport.get('flight_number', '')} departing {selected_transport.get('departure', '')}. "
                f"Plan lighter activities on arrival day."
            )
        elif mode == "train":
            selected_context["transport_note"] = (
                f"Day 1: Arrive by {selected_transport.get('name', 'train')} "
                f"departing {selected_transport.get('departure_time', '')}. "
                f"Plan lighter activities on arrival day."
            )
        else:
            selected_context["transport_note"] = f"Day 1: Arriving by {mode}. Plan lighter activities on arrival day."

    if selected_hotel:
        selected_context["hotel_note"] = (
            f"Staying at {selected_hotel.get('name', 'hotel')} located at "
            f"{selected_hotel.get('location', destination)}. "
            f"Include check-in on Day 1."
        )

    # Try LLM first
    llm_result = _llm_plan_route(profile, activities, weather, budget, selected_context)


    if llm_result:
        reasoning_log.append("🤖 Route Planner: Used GPT-4o-mini to create smart itinerary")
        itinerary = []
        for day_data in llm_result:
            day_activities = []
            for act in day_data.get("activities", []):
                # Try to find matching image from research data
                image_url = ""
                for ra in activities:
                    if ra.get("name", "").lower() in act.get("name", "").lower() or act.get("name", "").lower() in ra.get("name", "").lower():
                        image_url = ra.get("image_url", "")
                        break

                day_activities.append(ActivityItem(
                    time=act.get("time", "09:00 AM"),
                    name=act.get("name", "Activity"),
                    description=act.get("description", ""),
                    cost=act.get("cost", 0),
                    location=act.get("location", destination),
                    category=act.get("category", "activity"),
                    image_url=image_url,
                    booking_url="",
                    rating=0,
                    duration_mins=act.get("duration_mins", 60),
                ))

            est_cost = sum(a.get("cost", 0) for a in day_activities)
            w_str = "Sunny"
            w_temp = "25°C"
            if weather_forecast and day_data.get("day_number", 1) <= len(weather_forecast):
                wf = weather_forecast[day_data["day_number"] - 1]
                w_str = wf.get("condition", "Sunny")
                w_temp = wf.get("temp", "25°C")

            itinerary.append(DayPlan(
                day_number=day_data.get("day_number", 1),
                date=f"Day {day_data.get('day_number', 1)}",
                theme=day_data.get("theme", "Exploration"),
                activities=day_activities,
                estimated_cost=est_cost,
                weather=w_str,
                weather_temp=w_temp,
            ))
    else:
        reasoning_log.append("🔤 Route Planner: Using rule-based planner (no LLM)")
        itinerary = _rule_based_plan(activities, duration, weather_forecast)

    total_cost = sum(day.get("estimated_cost", 0) for day in itinerary)
    total_activities = sum(len(day.get("activities", [])) for day in itinerary)

    reasoning_log.append(
        f"🗓️ Route Planner: Created {duration}-day itinerary with {total_activities} activities, "
        f"estimated cost {currency} {total_cost:,.0f}"
    )

    # Build summary message
    msg_parts = [f"Here's your **{duration}-day itinerary** for {destination}! 🎉\n"]
    for day in itinerary:
        day_num = day.get("day_number", 0)
        theme = day.get("theme", "")
        weather_str = day.get("weather", "")
        acts = day.get("activities", [])
        msg_parts.append(f"\n**Day {day_num}: {theme}** — {weather_str}")
        for act in acts[:3]:
            cost_str = f"{currency} {act['cost']:,.0f}" if act.get("cost", 0) > 0 else "Free"
            msg_parts.append(f"  • {act['time']} — {act['name']} ({cost_str})")
        if len(acts) > 3:
            msg_parts.append(f"  • ...and {len(acts) - 3} more activities")

    msg_parts.append(f"\n💰 **Estimated Total:** {currency} {total_cost:,.0f}")
    msg_parts.append("\nPlease review! I can adjust timings, swap activities, or add more. Ready to finalize?")

    ai_message = AIMessage(content="\n".join(msg_parts))

    return {
        "itinerary": itinerary,
        "stage": "reviewing_itinerary",
        "reasoning_log": reasoning_log,
        "messages": [ai_message],
        "needs_human_input": True,
        "current_checkpoint": "itinerary_review",
    }
