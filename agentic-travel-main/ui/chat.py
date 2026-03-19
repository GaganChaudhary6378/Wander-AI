"""
Screen 2: Active Conversation Screen
Split layout — chat on left (60%), live itinerary + map on right (40%).
"""
import streamlit as st
from ui.components import render_navbar, render_chat_message, render_typing_indicator, render_day_card, render_map
from agents.graph import get_graph
from langchain_core.messages import HumanMessage
import time
import uuid


def _get_thread_id():
    """Get or create a thread ID for the current session."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    return st.session_state.thread_id


def _run_agent(user_message: str):
    """Run the LangGraph agent with the user's message."""
    graph = get_graph()
    thread_id = _get_thread_id()

    # Determine current stage
    current_stage = st.session_state.get("agent_stage", "idle")

    # If user is approving at a checkpoint, the stage stays the same
    # and the entry_router in graph.py will route to the NEXT agent.
    # e.g. "confirming_intent" → entry_router sends to "research"

    # Check for re-planning keywords
    replan_keywords = ["delay", "delayed", "cancel", "change", "reschedule", "adjust", "modify"]
    is_replan = any(k in user_message.lower() for k in replan_keywords) and current_stage == "completed"

    if is_replan:
        current_stage = "replanning"

    config = {"configurable": {"thread_id": thread_id}}

    try:
        initial_state = {
            "messages": [HumanMessage(content=user_message)],
            "stage": current_stage,
            "reasoning_log": list(st.session_state.get("reasoning_log", [])),
            "confidence": 0.5,
            "needs_human_input": False,
        }

        # Preserve existing state
        if st.session_state.get("travel_profile"):
            initial_state["travel_profile"] = st.session_state.travel_profile
        if st.session_state.get("research_results"):
            initial_state["research_results"] = st.session_state.research_results
        if st.session_state.get("budget_breakdown"):
            initial_state["budget_breakdown"] = st.session_state.budget_breakdown
        if st.session_state.get("itinerary"):
            initial_state["itinerary"] = st.session_state.itinerary
        if st.session_state.get("bookings"):
            initial_state["bookings"] = st.session_state.bookings
        if st.session_state.get("selected_transport"):
            initial_state["selected_transport"] = st.session_state.selected_transport
        if st.session_state.get("selected_hotel"):
            initial_state["selected_hotel"] = st.session_state.selected_hotel

        result = graph.invoke(initial_state, config)

        # Update session state from result
        if result.get("travel_profile"):
            st.session_state.travel_profile = result["travel_profile"]
        if result.get("research_results"):
            st.session_state.research_results = result["research_results"]
        if result.get("budget_breakdown"):
            st.session_state.budget_breakdown = result["budget_breakdown"]
        if result.get("itinerary"):
            st.session_state.itinerary = result["itinerary"]
        if result.get("bookings"):
            st.session_state.bookings = result["bookings"]
        if result.get("reasoning_log"):
            st.session_state.reasoning_log = result["reasoning_log"]
        if result.get("selected_transport"):
            st.session_state.selected_transport = result["selected_transport"]
        if result.get("selected_hotel"):
            st.session_state.selected_hotel = result["selected_hotel"]

        st.session_state.agent_stage = result.get("stage", "idle")
        st.session_state.current_checkpoint = result.get("current_checkpoint", "")
        st.session_state.needs_human_input = bool(result.get("needs_human_input", False))

        # Extract only NEW AI messages (skip the user message we passed in)
        messages = result.get("messages", [])
        ai_messages = []
        # Find the last user message we sent, then only take AI messages after it
        last_user_idx = -1
        for i, msg in enumerate(messages):
            if hasattr(msg, 'type') and msg.type == 'human':
                last_user_idx = i

        for msg in messages[last_user_idx + 1:]:
            if hasattr(msg, 'type') and msg.type == 'ai':
                ai_messages.append(msg.content)

        return ai_messages if ai_messages else ["I'm working on your trip plan..."]

    except Exception as e:
        import traceback
        traceback.print_exc()
        return [f"I encountered an issue: {str(e)}. Let me try a different approach!"]


def render_chat():
    """Render the active conversation screen."""
    # Calculate budget remaining
    budget_remaining = None
    currency = "INR"
    if st.session_state.get("travel_profile"):
        currency = st.session_state.travel_profile.get("currency", "INR")
        total_budget = st.session_state.travel_profile.get("budget", 0)
        booked = 0
        if st.session_state.get("bookings"):
            for b in st.session_state.bookings:
                d = b.get("details", {})
                if b.get("type") == "flight":
                    booked += d.get("price", 0)
                elif b.get("type") == "hotel":
                    booked += d.get("total_price", 0)
        budget_remaining = total_budget - booked

    render_navbar(active_page="chat", budget_remaining=budget_remaining, currency=currency)

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Process initial prompt if coming from home
    if st.session_state.get("user_prompt") and not st.session_state.get("initial_processed"):
        prompt = st.session_state.user_prompt
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        ai_responses = _run_agent(prompt)
        for resp in ai_responses:
            st.session_state.chat_history.append({"role": "ai", "content": resp})
        st.session_state.initial_processed = True

    # Main layout: 60/40 split
    chat_col, preview_col = st.columns([6, 4])

    with chat_col:
        # Chat messages
        chat_container = st.container(height=550)
        with chat_container:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    render_chat_message(msg["content"], is_user=True)
                else:
                    render_chat_message(msg["content"], is_user=False)

        # Preference form (one question at a time, no typing)
        stage = st.session_state.get("agent_stage", "idle")
        checkpoint = st.session_state.get("current_checkpoint", "")
        needs_input = bool(st.session_state.get("needs_human_input", False))

        skip_other_inputs = False

        # Quick approval buttons for confirmation step
        if stage == "confirming_intent" and needs_input:
            btn_cols = st.columns([1, 1, 2])
            with btn_cols[0]:
                if st.button("✅ Yes", use_container_width=True):
                    st.session_state.chat_history.append({"role": "user", "content": "yes"})
                    ai_responses = _run_agent("yes")
                    for resp in ai_responses:
                        st.session_state.chat_history.append({"role": "ai", "content": resp})
                    st.rerun()
            with btn_cols[1]:
                if st.button("✏️ Edit", use_container_width=True):
                    st.info("Tell me what you’d like to change (dates, budget, duration, etc.).")

            # Still allow free text edits below
            user_input = st.chat_input("What should I change?")
            if user_input:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                ai_responses = _run_agent(user_input)
                for resp in ai_responses:
                    st.session_state.chat_history.append({"role": "ai", "content": resp})
                st.rerun()
            skip_other_inputs = True

        is_pref_question = stage == "gathering_preferences" and needs_input and checkpoint in {
            "ask_companion",
            "ask_hotel",
            "ask_rental",
        }

        if not skip_other_inputs and is_pref_question:
            profile = st.session_state.get("travel_profile") or {}
            destination = profile.get("destination", "") or ""

            from agents.tools import classify_destination
            dest_type = classify_destination(destination) if destination else "city"

            if checkpoint == "ask_companion":
                options = [
                    ("solo", "🧍 Solo"),
                    ("couple", "💑 Couple"),
                    ("friends", "👯 Friends"),
                    ("family", "👨‍👩‍👧 Family"),
                ]
                prompt = "Who's joining you?"
                button = "Continue"
            elif checkpoint == "ask_hotel":
                options = [
                    ("budget", "🏕️ Budget / Hostel"),
                    ("mid-range", "🏨 Mid-range"),
                    ("luxury", "✨ Luxury"),
                    ("boutique", "🏡 Boutique / Homestay"),
                ]
                prompt = "What's your stay vibe?"
                button = "Continue"
            else:
                # ask_rental
                if dest_type in ("heritage", "spiritual"):
                    options = [
                        ("cycle", "🚲 Cycle"),
                        ("scooter", "🛵 Scooter"),
                        ("car", "🚗 Car"),
                        ("none", "🚶 No rental"),
                    ]
                elif dest_type == "beach":
                    options = [
                        ("scooter", "🛵 Scooter"),
                        ("bike", "🏍️ Bike"),
                        ("car", "🚗 Car"),
                        ("none", "🚶 No rental"),
                    ]
                else:
                    # hill_station + city + fallback
                    options = [
                        ("bike", "🏍️ Bike"),
                        ("scooter", "🛵 Scooter"),
                        ("car", "🚗 Car"),
                        ("none", "🚶 No rental"),
                    ]
                prompt = "Do you want to rent a vehicle?"
                button = "Start researching"

            option_values = [v for v, _ in options]
            option_labels = {v: label for v, label in options}

            with st.form(key=f"pref_form_{checkpoint}"):
                selection = st.radio(
                    label=prompt,
                    options=option_values,
                    format_func=lambda v: option_labels.get(v, v),
                    horizontal=True,
                )
                submitted = st.form_submit_button(button, use_container_width=True)

            if submitted and selection:
                st.session_state.chat_history.append({"role": "user", "content": selection})
                ai_responses = _run_agent(selection)
                for resp in ai_responses:
                    st.session_state.chat_history.append({"role": "ai", "content": resp})
                st.rerun()
        elif not skip_other_inputs:
            # Chat input (free text)
            user_input = st.chat_input("Type a message…")
            if user_input:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                ai_responses = _run_agent(user_input)
                for resp in ai_responses:
                    st.session_state.chat_history.append({"role": "ai", "content": resp})
                st.rerun()

    with preview_col:
        # Live Preview Panel
        st.markdown("""
        <div style="padding:8px 0;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
                <h3 style="font-size:18px;font-weight:700;margin:0;">
                    {title}
                </h3>
                <span class="badge badge-live">LIVE UPDATING</span>
            </div>
        </div>
        """.format(
            title=f"{st.session_state.get('travel_profile', {}).get('destination', 'Trip')} Explorer"
            if st.session_state.get('travel_profile')
            else "Trip Preview"
        ), unsafe_allow_html=True)

        # Show itinerary if available
        if st.session_state.get("itinerary"):
            for day in st.session_state.itinerary[:3]:
                render_day_card(day, currency)
                st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

            # Show map — dynamically geocode destination via Google Maps API
            from agents.tools import geocode_location
            dest = st.session_state.get("travel_profile", {}).get("destination", "")
            if dest:
                coords = geocode_location(dest)
                if coords:
                    locations = [{"lat": coords["lat"], "lon": coords["lon"], "name": dest.title()}]
                    # Geocode EVERY activity location for accurate pins
                    seen_names = set()
                    for day in st.session_state.itinerary:
                        for act in day.get("activities", []):
                            act_name = act.get("name", "")
                            if act_name in seen_names:
                                continue
                            act_lat = act.get("lat", 0)
                            act_lon = act.get("lon", 0)
                            if act_lat and act_lon:
                                locations.append({
                                    "lat": act_lat, "lon": act_lon,
                                    "name": act_name
                                })
                                seen_names.add(act_name)
                            elif act.get("location") and act["location"].lower() not in ("various", "", "local"):
                                act_coords = geocode_location(f"{act['location']}, {dest}")
                                if act_coords:
                                    locations.append({
                                        "lat": act_coords["lat"], "lon": act_coords["lon"],
                                        "name": act_name
                                    })
                                    seen_names.add(act_name)
                    render_map(locations, (coords["lat"], coords["lon"]))

            # Show budget summary as a styled widget in the right panel
            if st.session_state.get("budget_breakdown"):
                from ui.components import render_budget_summary
                st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
                render_budget_summary(st.session_state.budget_breakdown, currency)

        elif st.session_state.get("travel_profile"):
            # Show profile summary while researching
            profile = st.session_state.travel_profile
            st.markdown(f"""
            <div class="day-card" style="text-align:center;padding:32px;">
                <div style="font-size:32px;margin-bottom:12px;">🔍</div>
                <div style="font-size:14px;font-weight:600;color:var(--text-dark);">Researching {profile.get('destination', '')}...</div>
                <div style="font-size:12px;color:var(--text-light);margin-top:4px;">Finding the best options for your trip</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="day-card" style="text-align:center;padding:32px;">
                <div style="font-size:32px;margin-bottom:12px;">✨</div>
                <div style="font-size:14px;font-weight:600;color:var(--text-dark);">Your itinerary will appear here</div>
                <div style="font-size:12px;color:var(--text-light);margin-top:4px;">Start chatting to plan your trip</div>
            </div>
            """, unsafe_allow_html=True)

        # Navigation buttons
        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        btn_cols = st.columns(2)
        with btn_cols[0]:
            if st.session_state.get("itinerary"):
                if st.button("📋 View Full Itinerary", use_container_width=True):
                    st.session_state.current_page = "itinerary"
                    st.rerun()
        with btn_cols[1]:
            if st.session_state.get("bookings"):
                if st.button("🎫 View Bookings", use_container_width=True):
                    st.session_state.current_page = "booking"
                    st.rerun()

        # Reasoning log expander
        if st.session_state.get("reasoning_log"):
            with st.expander("🧠 Agent Reasoning Log"):
                for log in st.session_state.reasoning_log:
                    st.markdown(f"""
                    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px; margin-bottom:8px; color:#000000; font-size:13px; font-weight:500;">
                        {log}
                    </div>
                    """, unsafe_allow_html=True)
