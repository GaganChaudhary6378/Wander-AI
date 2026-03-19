"""
TravelState — Shared state schema for the LangGraph orchestration engine.
All agents read from and write to this state.
"""

from typing import TypedDict, Optional, Literal
from langgraph.graph import MessagesState


class TravelProfile(TypedDict, total=False):
    destination: str
    origin: str
    dates: str
    date_from: str  # YYYY-MM-DD
    date_to: str    # YYYY-MM-DD, for return trips
    trip_type: str  # one_way | return
    duration_days: int
    budget: float
    currency: str
    travel_style: str  # backpacking, luxury, family, romantic, adventure
    interests: list[str]
    group_size: int
    constraints: list[str]
    parsed: bool
    # Collected via follow-up questions after research
    companion_type: str   # solo | couple | friends | family
    hotel_preference: str # budget | mid-range | luxury | boutique
    stay_type: str        # hotel | hostel (optional explicit override)
    rental_preference: str  # bike | scooter | car | none


class ActivityItem(TypedDict, total=False):
    time: str
    name: str
    description: str
    cost: float
    location: str
    category: str  # dining, activity, transport, accommodation, sightseeing
    image_url: str
    booking_url: str
    rating: float
    duration_mins: int


class DayPlan(TypedDict, total=False):
    day_number: int
    date: str
    theme: str
    activities: list[ActivityItem]
    estimated_cost: float
    weather: str
    weather_temp: str


class BudgetBreakdown(TypedDict, total=False):
    accommodation: float
    transport: float
    food: float
    activities: float
    miscellaneous: float
    total: float
    per_person: float
    remaining: float


class BookingItem(TypedDict, total=False):
    type: str  # flight, hotel, activity
    name: str
    status: str  # confirmed, reserved, pending
    reference: str
    details: dict
    image_url: str


class ResearchResult(TypedDict, total=False):
    flights: list[dict]
    trains: list[dict]
    buses: list[dict]
    driving: dict
    transport_recommendation: str
    hotels: list[dict]
    activities: list[dict]
    weather: dict
    local_tips: list[str]
    web_knowledge: list[dict]
    rentals: list[dict]          # bike / scooter / car rental options
    destination_type: str        # hill_station | beach | city | heritage | spiritual


class TravelState(MessagesState):
    """Central state shared across all LangGraph nodes."""
    travel_profile: Optional[TravelProfile]
    stage: Literal[
        "idle",
        "parsing_intent",
        "validating_trip",        # asking validation questions (dates, one-way/return)
        "confirming_intent",
        "gathering_preferences",  # asking companion / hotel / rental questions one by one
        "preferences_collected",  # all 3 answers saved → ready to research
        "researching",
        "presenting_options",     # show all fetched options to user
        "optimizing_budget",
        "confirming_budget",
        "planning_route",
        "reviewing_itinerary",
        "booking",
        "confirming_booking",
        "replanning",
        "completed",
    ]
    research_results: Optional[ResearchResult]
    budget_breakdown: Optional[BudgetBreakdown]
    itinerary: Optional[list[DayPlan]]
    bookings: Optional[list[BookingItem]]
    reasoning_log: list[str]
    error_state: Optional[str]
    confidence: float
    needs_human_input: bool
    human_feedback: Optional[str]
    current_checkpoint: Optional[str]
    # NEW: user-selected/optimizer-selected options
    selected_transport: Optional[dict]   # chosen flight/train/bus/cab
    selected_hotel: Optional[dict]       # chosen hotel

