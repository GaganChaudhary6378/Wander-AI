"""
Research Agent — Fetches transport (flights, trains, buses, cabs),
hotels, activities, weather, and web knowledge.
After fetching, presents ALL options to the user with smart category
tags (Cheapest, Best Value, Non-stop, etc.) and pauses for review.
"""

from agents import TravelState, ResearchResult
from agents.tools import research_destination
from langchain_core.messages import AIMessage


def _tag_flights(flights: list, currency: str) -> str:
    """Format flights with smart category tags."""
    if not flights:
        return "✈️ **Flights:** No direct flights found for this route.\n"

    lines = ["✈️ **Flights:**"]
    sorted_flights = sorted(flights, key=lambda f: f.get("price", 0))

    for i, f in enumerate(sorted_flights[:10]):
        tags = []
        if i == 0:
            tags.append("💰 Cheapest")
        if f.get("stops", 1) == 0:
            tags.append("⭐ Non-stop")
        duration = f.get("duration", "")
        try:
            h, m = duration.replace("h", "").replace("m", "").split()
            mins = int(h) * 60 + int(m)
            if i == 0 or (i > 0 and mins < 120):
                tags.append("⏱️ Fast")
        except Exception:
            pass

        tag_str = f" `{'` `'.join(tags)}`" if tags else ""
        source = f.get("_source", "")
        price_label = f"~{currency} {f.get('price', 0):,} *(est.)*" if source == "fast_flights" else f"**{currency} {f.get('price', 0):,}**"
        lines.append(
            f"  {i+1}. {f.get('airline', 'Flight')} {f.get('flight_number', '')} — "
            f"{price_label}{tag_str}  "
            f"({f.get('departure', '')} → {f.get('arrival', '')}), "
            f"{f.get('duration', '')} | {f.get('stops', 0)} stop(s)"
        )
    return "\n".join(lines)


def _tag_trains(trains: list, currency: str) -> str:
    """Format trains with smart category tags."""
    if not trains:
        return "🚆 **Trains:** No direct trains found. Consider bus or cab.\n"

    lines = ["🚆 **Trains:**"]
    sorted_trains = sorted(trains, key=lambda t: t.get("estimated_cost", 9999))

    for i, t in enumerate(sorted_trains[:10]):
        tags = []
        if i == 0:
            tags.append("💰 Cheapest")
        train_type = t.get("name", "").upper()
        if any(k in train_type for k in ["RAJ", "RAJDHANI", "SHATABDI", "VANDE"]):
            tags.append("⭐ Premium")
        elif any(k in train_type for k in ["DRNT", "DURONTO"]):
            tags.append("⚡ Non-stop")

        tag_str = f" `{'` `'.join(tags)}`" if tags else ""
        cost_str = f"~{currency} {t.get('estimated_cost', 0):,} *(est.)*" if t.get("estimated_cost") else "Check IRCTC for fare"
        lines.append(
            f"  {i+1}. {t.get('name', 'Train')} — {cost_str}{tag_str}  "
            f"{t.get('duration', '')} ({t.get('departure_time', '')})"
        )
    return "\n".join(lines)


def _tag_hotels(hotels: list, currency: str, duration: int) -> str:
    """Format stays (hotels/hostels) as rich HTML cards with images and buttons."""
    if not hotels:
        return "🏨 **Stays:** No stays found.\n"

    # Start the container
    html = ['<div style="display: flex; gap: 12px; overflow-x: auto; padding: 10px 0; scrollbar-width: none; -ms-overflow-style: none;">']
    
    sorted_hotels = sorted(hotels, key=lambda h: h.get("price_per_night", 9999))

    for h in sorted_hotels[:5]:
        price = h.get("price_per_night", 0)
        rating = h.get("rating", 0)
        img = h.get("image_url") or "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&q=80&w=400"
        stay_type = h.get("type", "Stay")
        name = h.get("name", stay_type)
        location = h.get("location", "")
        price_range_label = h.get("price_range_label", "")

        # Prefer Google Hotels link → hotel's own website → Google Maps place
        booking_url = (
            h.get("google_hotels_link")
            or h.get("website")
            or h.get("maps_link")
            or h.get("booking_url")
            or "#"
        )

        # Determine tags
        tags_html = ""
        if rating >= 4.5:
            tags_html += '<span style="background:#e0f7f4;color:#3ab8ac;font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;margin-right:4px;">TOP RATED</span>'
        if price <= sorted_hotels[0].get("price_per_night", 9999) * 1.5:
            tags_html += '<span style="background:#fef3c7;color:#d97706;font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;margin-right:4px;">BEST VALUE</span>'

        # Price display — always show as estimated since Places API has no real-time rates
        price_display = f"""
            <span style="font-size:16px;font-weight:800;color:#000000;">~{currency} {price:,}</span>
            <span style="font-size:10px;color:#525252;">/night (est.)</span>"""

        # Show price range label as a subtle subtitle if available
        price_range_html = (
            f'<div style="font-size:10px;color:#8c8c8c;margin-top:2px;">{price_range_label}</div>'
            if price_range_label else ""
        )

        card = f"""<div style="min-width: 220px; max-width: 220px; background: white; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
    <div style="height: 120px; background-image: url('{img}'); background-size: cover; background-position: center; position: relative;">
        <div style="position: absolute; bottom: 8px; left: 8px;">{tags_html}</div>
    </div>
    <div style="padding: 12px;">
        <div style="font-size: 10px; font-weight: 800; letter-spacing: .06em; color: #6b7280; margin-bottom: 4px;">{stay_type.upper()}</div>
        <div style="font-size: 14px; font-weight: 700; color: #000000; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{name}</div>
        <div style="font-size: 11px; color: #525252; margin-bottom: 8px; display: flex; align-items: center; gap: 4px;">
            ⭐ {rating} · {location[:25]}...
        </div>
        <div style="margin-bottom: 12px;">
            <div style="display: flex; align-items: baseline; gap: 4px;">{price_display}</div>
            {price_range_html}
        </div>
        <a href="{booking_url}" target="_blank" style="display: block; text-align: center; background: #000000; color: white; padding: 8px; border-radius: 6px; font-size: 12px; font-weight: 700; text-decoration: none;">Check Prices →</a>
    </div>
</div>"""
        html.append(card)

    html.append('</div>')
    return "".join(html)


def _tag_activities(activities: list, currency: str) -> str:
    """Format activities as rich HTML cards with images."""
    if not activities:
        return "🎯 **Activities:** No activities found.\n"

    html = ['<div style="display: flex; gap: 12px; overflow-x: auto; padding: 10px 0; scrollbar-width: none; -ms-overflow-style: none;">']
    
    for act in activities[:6]:
        rating = act.get("rating", 0)
        img = act.get("image_url") or "https://images.unsplash.com/photo-1533105079780-92b9be482077?auto=format&fit=crop&q=80&w=400"
        name = act.get("name", "Activity")
        cost = act.get("cost", 0)
        cost_str = f"{currency} {cost:,.0f}" if cost > 0 else "Free ✓"
        maps_link = f"https://www.google.com/maps/search/?api=1&query={name.replace(' ', '+')}"
        
        card = f"""<div style="min-width: 180px; max-width: 180px; background: white; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
    <div style="height: 100px; background-image: url('{img}'); background-size: cover; background-position: center;"></div>
    <div style="padding: 10px;">
        <div style="font-size: 13px; font-weight: 700; color: #000000; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{name}</div>
        <div style="font-size: 10px; color: #525252; margin-bottom: 6px;">⭐ {rating} · {cost_str}</div>
        <a href="{maps_link}" target="_blank" style="display: block; text-align: center; background: #e0f7f4; color: #3ab8ac; padding: 6px; border-radius: 6px; font-size: 11px; font-weight: 700; text-decoration: none;">View Map</a>
    </div>
</div>"""
        html.append(card)

    html.append('</div>')
    return "".join(html)


def _tag_rentals(rentals: list, currency: str, group_size: int, dest_type: str) -> str:
    """Format rental options as rich HTML cards with smart recommendations."""
    if not rentals:
        return ""

    headline = rentals[0].get("headline", "")
    dest_label = {
        "hill_station": "hill station",
        "beach": "beach destination",
        "heritage": "heritage city",
        "spiritual": "spiritual destination",
        "city": "city",
    }.get(dest_type, "destination")

    vehicle_types = {r.get("vehicle_type") for r in rentals if r.get("vehicle_type")}
    single_type = len(vehicle_types) == 1

    # Pick top recommendation label only when multiple vehicle types are shown
    companion_hint = "solo traveller" if group_size == 1 else ("couple" if group_size == 2 else "group")
    rec_vehicle = ""
    rec_label = ""
    if not single_type:
        rec_map = {"solo traveller": "solo", "couple": "couple", "group": "friends"}
        rec_key = rec_map.get(companion_hint, "solo")
        rec_vehicle = next(
            (r["vehicle_type"] for r in rentals if rec_key in r.get("best_for", "")),
            rentals[0].get("vehicle_type", "") if rentals else "",
        )
        rec_label = next((r["label"] for r in rentals if r.get("vehicle_type") == rec_vehicle), "")

    header_lines = [f'<div style="margin:8px 0 4px;font-size:13px;color:#374151;">{headline}</div>']
    if not single_type and rec_label:
        header_lines.append(
            f'<div style="font-size:12px;color:#6b7280;margin-bottom:10px;">As a <b>{companion_hint}</b> visiting a {dest_label}, we recommend: <b>{rec_label}</b> 🎯</div>'
        )
    html_parts = [
        *header_lines,
        '<div style="display:flex;gap:12px;overflow-x:auto;padding:6px 0;scrollbar-width:none;-ms-overflow-style:none;">',
    ]

    for r in rentals:
        vehicle = r["vehicle_type"]
        is_recommended = (not single_type) and (vehicle == rec_vehicle)
        border = "2px solid #3ab8ac" if is_recommended else "1px solid #e2e8f0"
        badge = '<span style="background:#3ab8ac;color:white;font-size:9px;font-weight:700;padding:2px 5px;border-radius:3px;margin-left:4px;">RECOMMENDED</span>' if is_recommended else ""

        label = r["label"]
        icon = label.split()[0] if label else "🚗"
        title = label.replace(icon, "", 1).strip() if label else "Rental"
        shop = r["shop_name"]
        shop_rating = r.get("shop_rating", 0)
        rating_str = f"⭐ {shop_rating}" if shop_rating else ""
        price_label = r["price_label"]
        maps_link = r["maps_link"]
        best_for = r.get("best_for", "")
        img = r.get("image_url") or "https://images.unsplash.com/photo-1525609004556-c46c7d6cf023?auto=format&fit=crop&q=80&w=600"

        card = f"""<div style="min-width:200px;max-width:200px;background:white;border-radius:12px;overflow:hidden;border:{border};box-shadow:0 2px 8px rgba(0,0,0,0.08);flex-shrink:0;">
    <div style="height:90px;background-image:url('{img}');background-size:cover;background-position:center;"></div>
    <div style="padding:12px;">
        <div style="font-size:22px;margin-bottom:6px;">{icon}</div>
        <div style="font-size:13px;font-weight:700;color:#111;margin-bottom:2px;">{title}{badge}</div>
        <div style="font-size:11px;color:#525252;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{shop} {rating_str}</div>
        <div style="font-size:14px;font-weight:800;color:#000;margin:6px 0 2px;">{price_label}</div>
        <div style="font-size:10px;color:#8c8c8c;margin-bottom:10px;">{('Best for: ' + best_for) if best_for else ''}</div>
        <a href="{maps_link}" target="_blank" style="display:block;text-align:center;background:#111;color:white;padding:7px;border-radius:6px;font-size:11px;font-weight:700;text-decoration:none;">Find on Maps →</a>
    </div>
</div>"""
        html_parts.append(card)

    html_parts.append("</div>")
    return "".join(html_parts)




def research(state: TravelState) -> dict:
    """LangGraph node: Research all transport, accommodation, activities, and knowledge."""
    profile = state.get("travel_profile", {})
    reasoning_log = list(state.get("reasoning_log", []))

    destination = profile.get("destination", "Rishikesh")
    origin = profile.get("origin", "Delhi")
    interests = profile.get("interests", [])
    currency = profile.get("currency", "INR")
    duration = profile.get("duration_days", 3)
    group_size = profile.get("group_size", 1)
    rental_pref = (profile.get("rental_preference") or "").strip().lower()
    include_rentals = rental_pref not in ("none", "no", "nope", "nah")

    reasoning_log.append(f"🔍 Research Agent: Searching live APIs for {destination}...")

    date_from = profile.get("date_from")
    date_to = profile.get("date_to")
    stay_type = profile.get("stay_type")
    results = research_destination(
        origin,
        destination,
        interests,
        date_from=date_from,
        date_to=date_to,
        include_rentals=include_rentals,
        rental_preference=rental_pref if include_rentals else None,
        stay_type=stay_type,
    )

    flights = results.get("flights", [])
    trains = results.get("trains", [])
    buses = results.get("buses", [])
    driving = results.get("driving")
    transport_rec = results.get("transport_recommendation", "")
    hotels = results.get("hotels", [])
    activities = results.get("activities", [])
    weather = results.get("weather", {})
    tips = results.get("local_tips", [])
    web_knowledge = results.get("web_knowledge", [])
    rentals = results.get("rentals", [])
    dest_type = results.get("destination_type", "city")

    research_results: ResearchResult = {
        "flights": flights,
        "trains": trains,
        "buses": buses,
        "driving": driving,
        "transport_recommendation": transport_rec,
        "hotels": hotels,
        "activities": activities,
        "weather": weather,
        "local_tips": tips,
        "web_knowledge": web_knowledge,
        "rentals": rentals,
        "destination_type": dest_type,
    }

    reasoning_log.append(
        f"🔍 Found: {len(flights)} flights, {len(trains)} trains, "
        f"{len(buses)} buses, {len(hotels)} hotels, {len(activities)} activities, "
        f"{len(rentals)} rental options ({dest_type})"
    )
    if web_knowledge:
        reasoning_log.append(f"🌐 Crawled {len(web_knowledge)} web sources for destination knowledge")
    if driving:
        reasoning_log.append(f"🚗 Driving route: {driving.get('distance', '')} in {driving.get('duration', '')}")

    # ── Build the ALL OPTIONS presentation message ──
    msg_parts = [
        f"I've found all available options for your trip from **{origin}** to **{destination}**! 🔍\n",
        f"*Budget: {currency} {profile.get('budget', 0):,} | Duration: {duration} days | Group: {group_size} person(s)*\n",
        "---",
    ]

    # === TRANSPORT ===
    msg_parts.append("\n**🚀 Transport Options:**\n")
    if trains:
        msg_parts.append(_tag_trains(trains, currency))
    else:
        msg_parts.append(_tag_trains([], currency))
    msg_parts.append("\n" + _tag_flights(flights, currency))

    if buses:
        msg_parts.append("\n🚌 **Buses:**")
        for i, b in enumerate(buses[:3]):
            cost_str = f"~{currency} {b.get('estimated_cost', 0):,} *(est.)*" if b.get("estimated_cost") else "Check RedBus"
            dur = b.get("duration", "")
            if b.get("duration_estimated"):
                dur = f"{dur} *(est.)*"
            msg_parts.append(f"  {i+1}. {b.get('name', 'Bus')} — {cost_str}, {dur}")

    if driving:
        msg_parts.append(
            f"\n🚗 **Cab/Self-Drive:** {driving.get('distance', '')} — "
            f"~{currency} {driving.get('estimated_cost', 0):,} *(est.)*, {driving.get('duration', '')}"
        )

    msg_parts.append(f"\n💡 **Recommendation:** {transport_rec}" if transport_rec else "")

    # === HOTELS ===
    msg_parts.append("\n---")
    msg_parts.append("\n**🏨 Stay Options:**")
    msg_parts.append(_tag_hotels(hotels, currency, duration))

    # === ACTIVITIES ===
    msg_parts.append("\n---")
    msg_parts.append(f"\n**🎯 Activities ({len(activities)} found):**")
    msg_parts.append(_tag_activities(activities, currency))

    # === RENTALS ===
    if rentals:
        msg_parts.append("\n---")
        msg_parts.append("\n**🚗 Vehicle Rentals at Destination:**")
        msg_parts.append(_tag_rentals(rentals, currency, group_size, dest_type))

    # === WEATHER ===
    if weather:
        msg_parts.append(f"\n🌡️ **Weather:** {weather.get('temperature', 'N/A')}, {weather.get('condition', 'N/A')}")

    msg_parts.append(
        "\n> *(est.) = estimated price. Click **Check Prices →** on hotels or flight booking links for live rates.*"
    )

    msg_parts.append(
        "\n---\n"
        "👆 **All options are above!** Say **cheapest**, **fastest**, or **optimize** "
        "to lock in your transport + hotel and generate your itinerary."
    )

    ai_message = AIMessage(content="\n".join(filter(None, msg_parts)))

    return {
        "research_results": research_results,
        "stage": "presenting_options",
        "reasoning_log": reasoning_log,
        "messages": [ai_message],
        "needs_human_input": True,
        "current_checkpoint": "options_review",
    }
