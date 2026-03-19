"""
Screen 3: Itinerary Overview Screen
Day cards with activities, map, and budget summary.
"""
import streamlit as st
from ui.components import render_navbar, render_day_card, render_budget_summary, render_map
from agents.tools import geocode_location


def render_itinerary():
    """Render the itinerary overview screen."""
    profile = st.session_state.get("travel_profile", {})
    itinerary = st.session_state.get("itinerary", [])
    budget = st.session_state.get("budget_breakdown", {})
    currency = profile.get("currency", "INR")
    destination = profile.get("destination", "Trip")
    duration = profile.get("duration_days", len(itinerary))

    render_navbar(active_page="itinerary")

    # Header
    st.markdown(f"""
    <div style="padding:24px 32px 8px;">
        <div style="font-size:12px;font-weight:700;color:var(--primary);text-transform:uppercase;letter-spacing:1.5px;">
            📅 {duration}-DAY TRIP
        </div>
        <h1 style="font-size:32px;font-weight:800;color:var(--text-dark);margin:4px 0 8px;">
            {destination} Adventure
        </h1>
        <p style="font-size:14px;color:var(--text-light);">
            {profile.get('dates', 'Upcoming')} • {profile.get('group_size', 1)} Traveler{'s' if profile.get('group_size', 1) > 1 else ''}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Action buttons
    btn_col1, btn_col2, btn_col3 = st.columns([4, 1, 1])
    with btn_col2:
        if st.button("✏️ Edit Plan", use_container_width=True):
            st.session_state.current_page = "chat"
            st.rerun()
    with btn_col3:
        if st.button("🎫 Finalize & Book", type="primary", use_container_width=True):
            # Auto-run booking agent
            from agents.graph import get_graph
            from langchain_core.messages import HumanMessage

            graph = get_graph()
            initial_state = {
                "messages": [HumanMessage(content="Finalize and book everything")],
                "stage": "reviewing_itinerary",
                "travel_profile": st.session_state.get("travel_profile"),
                "research_results": st.session_state.get("research_results"),
                "budget_breakdown": st.session_state.get("budget_breakdown"),
                "itinerary": st.session_state.get("itinerary"),
                "reasoning_log": st.session_state.get("reasoning_log", []),
                "confidence": 0.9,
                "needs_human_input": False,
            }
            config = {"configurable": {"thread_id": st.session_state.get("thread_id", "default")}}
            result = graph.invoke(initial_state, config)

            if result.get("bookings"):
                st.session_state.bookings = result["bookings"]
                st.session_state.agent_stage = "completed"
                if result.get("reasoning_log"):
                    st.session_state.reasoning_log = result["reasoning_log"]
                st.session_state.current_page = "booking"
                st.rerun()

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    # Day cards
    if itinerary:
        day_cols = st.columns(min(len(itinerary), 3))
        for i, day in enumerate(itinerary):
            with day_cols[i % 3]:
                render_day_card(day, currency)

                # Detail button
                if st.button(f"View Day {day.get('day_number', i+1)} Details", key=f"day_detail_{i}", use_container_width=True):
                    st.session_state.selected_day = i
                    st.session_state.current_page = "day_view"
                    st.rerun()
    else:
        st.info("No itinerary available yet. Start planning in the chat!")

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

    # Map + Budget row
    map_col, budget_col = st.columns([6, 4])

    with map_col:
        coords = geocode_location(destination)
        if coords:
            locations = [{"lat": coords["lat"], "lon": coords["lon"], "name": destination}]
            seen_names = set()
            for day in itinerary:
                for act in day.get("activities", []):
                    act_name = act.get("name", "")
                    if act_name in seen_names:
                        continue
                    act_lat = act.get("lat", 0)
                    act_lon = act.get("lon", 0)
                    if act_lat and act_lon:
                        locations.append({"lat": act_lat, "lon": act_lon, "name": act_name})
                        seen_names.add(act_name)
                    elif act.get("location") and act["location"].lower() not in ("various", "", "local"):
                        act_coords = geocode_location(f"{act['location']}, {destination}")
                        if act_coords:
                            locations.append({"lat": act_coords["lat"], "lon": act_coords["lon"], "name": act_name})
                            seen_names.add(act_name)
            render_map(locations, (coords["lat"], coords["lon"]))
        else:
            st.markdown("""
            <div style="background:#f1f5f9;border-radius:12px;height:300px;display:flex;align-items:center;justify-content:center;">
                <div style="text-align:center;color:var(--text-light);">
                    <div style="font-size:32px;margin-bottom:8px;">🗺️</div>
                    Map not available (check Google Maps API key)
                </div>
            </div>
            """, unsafe_allow_html=True)

    with budget_col:
        if budget:
            render_budget_summary(budget, currency)

            st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

            if st.button("🎫 Finalize & Book Now", type="primary", use_container_width=True, key="book_bottom"):
                st.session_state.current_page = "booking"
                st.rerun()

    # Back button
    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    if st.button("← Back to Chat"):
        st.session_state.current_page = "chat"
        st.rerun()
