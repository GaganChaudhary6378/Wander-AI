"""
Booking Coordinator Agent — Generates booking details for the finalized itinerary.
"""

import random
import string
from agents import TravelState, BookingItem
from langchain_core.messages import AIMessage


def _generate_ref():
    """Generate a realistic-looking booking reference."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def coordinate_booking(state: TravelState) -> dict:
    """LangGraph node: Create booking details for flights, hotel, and activities."""
    profile = state.get("travel_profile", {})
    research = state.get("research_results", {})
    itinerary = state.get("itinerary", [])
    budget = state.get("budget_breakdown", {})
    selected_transport = state.get("selected_transport") or {}
    selected_hotel = state.get("selected_hotel") or {}
    reasoning_log = list(state.get("reasoning_log", []))

    currency = profile.get("currency", "INR")
    destination = profile.get("destination", "Rishikesh")
    duration = profile.get("duration_days", 4)

    bookings: list[BookingItem] = []

    # Book the selected transport (respects bus/train/cab choices)
    mode = (selected_transport.get("mode") or "").lower()
    if mode == "flight":
        flight = selected_transport
        bookings.append(BookingItem(
            type="flight",
            name=f"{flight.get('airline', 'Flight')} {flight.get('flight_number', '')}".strip(),
            status="confirmed",
            reference=_generate_ref(),
            details={
                "airline": flight.get("airline", ""),
                "flight_number": flight.get("flight_number", ""),
                "departure": flight.get("departure", ""),
                "arrival": flight.get("arrival", ""),
                "duration": flight.get("duration", ""),
                "price": flight.get("price", 0),
                "currency": flight.get("currency", currency),
                "class": flight.get("class", "Economy"),
                "origin": profile.get("origin", ""),
                "destination": destination,
                "seat": f"{random.randint(1, 30)}{random.choice('ABCDEF')} ({random.choice(['Window', 'Middle', 'Aisle'])})",
            },
            image_url="https://images.unsplash.com/photo-1436491865332-7a61a109db05?w=400",
        ))
    elif mode in ("bus", "train", "cab"):
        icon = "🚌" if mode == "bus" else ("🚆" if mode == "train" else "🚗")
        cost = selected_transport.get("estimated_cost", 0)
        bookings.append(BookingItem(
            type="transport",
            name=f"{icon} {selected_transport.get('name', mode.title())}".strip(),
            status="reserved",
            reference=_generate_ref(),
            details={
                "mode": mode,
                "origin": profile.get("origin", ""),
                "destination": destination,
                "duration": selected_transport.get("duration", ""),
                "distance": selected_transport.get("distance", ""),
                "estimated_cost": cost,
                "currency": currency,
                "booking_tip": selected_transport.get("booking_tip", ""),
            },
            image_url="https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=400&q=80",
        ))
    else:
        # Fallback to cheapest available flight if nothing selected
        flights = research.get("flights", [])
        if flights:
            flight = min(flights, key=lambda f: f.get("price", 0))
            bookings.append(BookingItem(
                type="flight",
                name=f"{flight.get('airline', 'Flight')} {flight.get('flight_number', '')}".strip(),
                status="confirmed",
                reference=_generate_ref(),
                details={
                    "airline": flight.get("airline", ""),
                    "flight_number": flight.get("flight_number", ""),
                    "departure": flight.get("departure", ""),
                    "arrival": flight.get("arrival", ""),
                    "duration": flight.get("duration", ""),
                    "price": flight.get("price", 0),
                    "currency": flight.get("currency", currency),
                    "class": flight.get("class", "Economy"),
                    "origin": profile.get("origin", ""),
                    "destination": destination,
                    "seat": f"{random.randint(1, 30)}{random.choice('ABCDEF')} ({random.choice(['Window', 'Middle', 'Aisle'])})",
                },
                image_url="https://images.unsplash.com/photo-1436491865332-7a61a109db05?w=400",
            ))

    # Book the selected hotel (fallback: best value)
    hotels = research.get("hotels", [])
    hotel = selected_hotel or None
    if not hotel and hotels:
        hotel = max(hotels, key=lambda h: h.get("rating", 0) / max(h.get("price_per_night", 1), 1))
    if hotel:
        total_hotel = hotel.get("price_per_night", 0) * duration
        bookings.append(BookingItem(
            type="hotel",
            name=hotel["name"],
            status="reserved",
            reference=_generate_ref(),
            details={
                "hotel_name": hotel["name"],
                "room_type": hotel.get("type", "Standard Room"),
                "location": hotel["location"],
                "check_in": "Day 1, 2:00 PM",
                "check_out": f"Day {duration}, 11:00 AM",
                "nights": duration,
                "price_per_night": hotel.get("price_per_night", 0),
                "total_price": total_hotel,
                "currency": hotel["currency"],
                "rating": hotel["rating"],
                "amenities": hotel.get("amenities", []),
            },
            image_url=hotel.get("image_url", ""),
        ))

    # Calculate totals
    total_booked = 0
    for b in bookings:
        if b.get("type") == "flight":
            total_booked += b.get("details", {}).get("price", 0)
        elif b.get("type") == "hotel":
            total_booked += b.get("details", {}).get("total_price", 0)
        elif b.get("type") == "transport":
            total_booked += b.get("details", {}).get("estimated_cost", 0)
    total_budget = profile.get("budget", 15000)
    remaining = total_budget - total_booked

    reasoning_log.append(
        f"🎫 Booking Coordinator: Booked {len(bookings)} items, "
        f"total {currency} {total_booked:,.0f}, remaining {currency} {remaining:,.0f}"
    )

    # Build confirmation message
    msg_parts = [f"🎉 **Trip Locked In!** Your {destination} adventure is ready!\n"]

    for b in bookings:
        if b["type"] == "flight":
            d = b["details"]
            msg_parts.append(
                f"✈️ **{b['name']}** — CONFIRMED\n"
                f"   {d['origin']} → {d['destination']} | {d['departure']} → {d['arrival']}\n"
                f"   Seat: {d['seat']} | PNR: {b['reference']}\n"
                f"   💰 {d['currency']} {d['price']:,}"
            )
        elif b["type"] == "hotel":
            d = b["details"]
            msg_parts.append(
                f"🏨 **{d['hotel_name']}** — RESERVED\n"
                f"   {d['room_type']} | {d['location']}\n"
                f"   Check-in: {d['check_in']} | {d['nights']} nights\n"
                f"   REF: {b['reference']}\n"
                f"   💰 {d['currency']} {d['total_price']:,}"
            )

    msg_parts.append(
        f"\n💰 **Budget Summary:**\n"
        f"   Total Budget: {currency} {total_budget:,.0f}\n"
        f"   Booked: {currency} {total_booked:,.0f}\n"
        f"   **Remaining for Food & Fun: {currency} {remaining:,.0f}**"
    )

    msg_parts.append("\nAll confirmation details have been saved. Need any changes? Chat with me!")

    ai_message = AIMessage(content="\n".join(msg_parts))

    return {
        "bookings": bookings,
        "stage": "completed",
        "reasoning_log": reasoning_log,
        "messages": [ai_message],
        "needs_human_input": False,
        "current_checkpoint": None,
    }
