"""
LangGraph StateGraph — Main orchestration engine.
Routes between agents based on current stage.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from agents import TravelState
from agents.intent_parser import parse_intent
from agents.validator import validate_trip
from agents.preference_collector import gather_preferences
from agents.researcher import research
from agents.budget_optimizer import optimize_budget
from agents.route_planner import plan_route
from agents.booking_coordinator import coordinate_booking
from agents.replanner import replan


def entry_router(state: TravelState) -> str:
    """Route to the correct agent based on the current stage."""
    stage = state.get("stage", "idle")
    messages = state.get("messages", []) or []
    user_msg = ""
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            user_msg = (msg.content or "").strip().lower()
            break

    def _contains_any(text: str, keywords: list[str]) -> bool:
        return any(k in text for k in keywords)

    is_budget_approval = _contains_any(user_msg, ["looks good", "proceed", "continue", "go ahead", "finalize", "ok", "okay", "yes"])
    wants_transport_change = _contains_any(user_msg, ["change transport", "transport to", "switch transport", "bus", "train", "flight", "cab", "self-drive", "self drive", "drive"])
    wants_hotel_change = _contains_any(
        user_msg,
        ["change hotel", "hotel to", "switch hotel", "stay to", "change stay", "accommodation", "hostel", "hostels"],
    )
    replan_keywords = ["delay", "delayed", "cancel", "change", "reschedule", "adjust", "modify"]
    wants_replan = _contains_any(user_msg, replan_keywords)

    routing = {
        "idle": "parse_intent",
        "parsing_intent": "parse_intent",
        "validating_trip": "parse_intent",
        # After user confirms intent → ask preference questions one by one
        "confirming_intent": "gather_preferences",
        # While collecting answers → stay in gather_preferences
        "gathering_preferences": "gather_preferences",
        # All 3 answers saved → now run research
        "preferences_collected": "research",
        # After user reviews options → run budget optimizer with their preferences
        "presenting_options": "optimize_budget",
        # Budget review loop: allow changes / approval inside optimize_budget
        "confirming_budget": "optimize_budget",
        # Itinerary review loop: allow edits unless user finalizes
        "reviewing_itinerary": "plan_route",
        # Re-planning flow
        "replanning": "replan",
    }

    # Special-case: while reviewing itinerary, allow "finalize/book" to proceed to booking
    if stage == "reviewing_itinerary":
        if _contains_any(user_msg, ["book", "lock", "finalize", "looks good", "confirm", "yes"]):
            return "coordinate_booking"
        if wants_transport_change or wants_hotel_change:
            return "optimize_budget"
        if wants_replan:
            return "replan"
        return "plan_route"

    # Special-case: after budget selection, any "change transport/hotel" stays in budget optimizer
    if stage == "confirming_budget":
        return "optimize_budget"

    return routing.get(stage, "parse_intent")


def auto_chain_after_research(state: TravelState) -> str:
    """After research, always pause for user to review options."""
    return END


def auto_chain_after_budget(state: TravelState) -> str:
    """After budget optimization, check if we should pause for human approval."""
    if state.get("needs_human_input"):
        return END
    return "plan_route"


def auto_chain_after_route(state: TravelState) -> str:
    """After route planning, check if we should pause for human review."""
    if state.get("needs_human_input"):
        return END
    return "coordinate_booking"


def build_graph():
    """Build and compile the LangGraph travel planning graph."""
    graph = StateGraph(TravelState)

    # Add nodes
    graph.add_node("parse_intent", parse_intent)
    graph.add_node("validate_trip", validate_trip)
    graph.add_node("gather_preferences", gather_preferences)
    graph.add_node("research", research)
    graph.add_node("optimize_budget", optimize_budget)
    graph.add_node("plan_route", plan_route)
    graph.add_node("coordinate_booking", coordinate_booking)
    graph.add_node("replan", replan)

    # Entry point — route to the correct agent based on stage
    graph.add_conditional_edges(
        START,
        entry_router,
        {
            "parse_intent": "parse_intent",
            "validate_trip": "validate_trip",
            "gather_preferences": "gather_preferences",
            "research": "research",
            "optimize_budget": "optimize_budget",
            "plan_route": "plan_route",
            "coordinate_booking": "coordinate_booking",
            "replan": "replan",
        }
    )

    # Plan → Validate → (user replies) → parse_intent → validate_trip → END until valid
    graph.add_edge("parse_intent", "validate_trip")
    graph.add_edge("validate_trip", END)

    # Preference collection: pause after each question for user reply
    # When needs_human_input=False (all answers collected), chain straight to research
    graph.add_conditional_edges(
        "gather_preferences",
        lambda s: END if s.get("needs_human_input", True) else "research",
        {END: END, "research": "research"},
    )

    # After research → always pause: user reviews options, then responds
    # Entry router maps presenting_options → optimize_budget on next turn
    graph.add_edge("research", END)

    # After budget → pause for approval OR continue to route planner
    graph.add_conditional_edges(
        "optimize_budget",
        auto_chain_after_budget,
        {"plan_route": "plan_route", END: END}
    )

    # After route planning → pause for review OR continue to booking
    graph.add_conditional_edges(
        "plan_route",
        auto_chain_after_route,
        {"coordinate_booking": "coordinate_booking", END: END}
    )

    # After booking → done
    graph.add_edge("coordinate_booking", END)

    # After replan → done (user reviews)
    graph.add_edge("replan", END)

    # Compile with checkpointing
    memory = MemorySaver()
    compiled = graph.compile(checkpointer=memory)

    return compiled


# Singleton graph instance
_graph = None


def get_graph():
    """Get or create the graph singleton."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
