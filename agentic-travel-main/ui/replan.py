"""
Screen 7: Re-planning / Recovery Screen
Alert banner, revised itinerary with status badges, and refinement chat.
"""
import streamlit as st
from ui.components import render_navbar


def render_replan():
    """Render the re-planning/recovery screen."""
    profile = st.session_state.get("travel_profile", {})
    itinerary = st.session_state.get("itinerary", [])
    currency = profile.get("currency", "INR")
    destination = profile.get("destination", "Trip")

    render_navbar(active_page="itinerary")

    import random
    from datetime import datetime, timedelta

    # 1. Initialize stable random delay in session state so it doesn't change on every rerun
    if "simulation_data" not in st.session_state:
        # Find booked transport mode
        transport_type = "transport"
        transport_icon = "✈️"
        bookings = st.session_state.get("bookings", [])
        for b in bookings:
            if b.get("type") == "flight":
                # It might technically still be a train or bus stored under the flight key based on logic,
                # but let's check the details mode.
                dt_mode = b.get("details", {}).get("mode", "").lower()
                if dt_mode == "train":
                    transport_type = "train"
                    transport_icon = "🚆"
                elif dt_mode == "bus":
                    transport_type = "bus"
                    transport_icon = "🚌"
                elif dt_mode == "cab":
                    transport_type = "cab"
                    transport_icon = "🚗"
                else:
                    transport_type = "flight"
                    transport_icon = "✈️"
                break
        
        st.session_state.simulation_data = {
            "delay_hours": random.randint(1, 4),
            "transport_type": transport_type,
            "transport_icon": transport_icon,
        }

    sim_data = st.session_state.simulation_data
    delay_hrs = sim_data["delay_hours"]
    trans_type = sim_data["transport_type"]
    trans_icon = sim_data["transport_icon"]

    # Alert Banner
    st.markdown(f"""
    <div class="alert-warning" style="margin:16px 0;">
        <div class="alert-icon">⚠️</div>
        <div>
            <p class="alert-title">We detected a change</p>
            <p class="alert-text">
                Your {trans_type} is delayed by {delay_hrs} hour{'s' if delay_hrs > 1 else ''}. We've automatically prepared a recovery plan to save your afternoon activities.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Revised Itinerary Card
    st.markdown("""
    <div style="background:white;border:1px solid var(--border);border-radius:16px;overflow:hidden;box-shadow:var(--shadow-sm);">
        <div style="padding:16px 20px;border-bottom:1px solid #f1f5f9;display:flex;justify-content:space-between;align-items:center;">
            <h2 style="font-size:20px;font-weight:700;margin:0;">Revised Itinerary</h2>
            <span class="badge badge-draft">DRAFT PROPOSAL</span>
        </div>
    """, unsafe_allow_html=True)

    def _add_hours(time_str: str, hours: int) -> str:
        """Helper to shift time strings e.g. '2:00 PM' to '4:00 PM' or ranges."""
        try:
            if "-" in time_str:
                parts = [p.strip() for p in time_str.split("-")]
                return f"{_add_hours(parts[0], hours)} - {_add_hours(parts[1], hours)}"
            t = datetime.strptime(time_str.strip(), "%I:%M %p")
            t += timedelta(hours=hours)
            return t.strftime("%I:%M %p").lstrip("0")
        except Exception:
            return time_str

    # Get Day 1 activities (or fallback)
    day1_activities = []
    if itinerary:
        day1 = itinerary[0]
        day1_activities = day1.get("activities", [])

    # Simulate revised items
    revised_items = []
    if day1_activities:
        # First item: Delayed
        act = day1_activities[0]
        old_time = act.get("time", "2:00 PM")
        revised_items.append({
            "icon": trans_icon,
            "name": f"Arrive at {destination}",
            "status": "Delayed",
            "old_time": old_time,
            "new_time": _add_hours(old_time, delay_hrs),
            "note": "",
            "highlight": False,
            "removed": False,
        })

        # Process remaining items
        for i, act_iter in enumerate(day1_activities[1:], start=1):
            act_old_time = act_iter.get("time", "")
            
            # If it's the last item and we have more than 2 total events, let's "Remove" it for effect
            if i == len(day1_activities) - 1 and len(day1_activities) > 2:
                revised_items.append({
                    "icon": "🏛️" if i % 2 == 0 else "🌃",
                    "name": act_iter.get("name", "Evening Activity"),
                    "status": "Removed",
                    "old_time": act_old_time,
                    "new_time": "",
                    "note": f"Not enough time after the {delay_hrs}h delay. Re-scheduling to tomorrow.",
                    "highlight": False,
                    "removed": True,
                })
            else:
                new_status = "Rescheduled" if i == 1 else "Auto-Adjusted"
                revised_items.append({
                    "icon": "📍" if "visit" in act_iter.get("name", "").lower() else "🍽️",
                    "name": act_iter.get("name", "Activity"),
                    "status": new_status,
                    "old_time": act_old_time,
                    "new_time": _add_hours(act_old_time, delay_hrs),
                    "note": "Key experience maintained." if new_status == "Rescheduled" else "",
                    "highlight": True,
                    "removed": False,
                })

    else:
        # Fallback demo data
        revised_items = [
            {"icon": trans_icon, "name": "Arrive at Airport", "status": "Delayed", "old_time": "2:00 PM", "new_time": _add_hours("2:00 PM", delay_hrs), "note": "", "highlight": False, "removed": False},
            {"icon": "📍", "name": "City Exploration", "status": "Rescheduled", "old_time": "3:30 PM - 4:30 PM", "new_time": _add_hours("3:30 PM - 4:30 PM", delay_hrs), "note": "Sunset viewing opportunity maintained.", "highlight": True, "removed": False},
            {"icon": "🍽️", "name": "Local Dinner", "status": "Auto-Adjusted", "old_time": "6:00 PM - 7:00 PM", "new_time": _add_hours("6:00 PM - 7:00 PM", delay_hrs), "note": "", "highlight": True, "removed": False},
            {"icon": "🏛️", "name": "Evening Activity", "status": "Removed", "old_time": "", "new_time": "", "note": "Closed after the delay. Re-scheduling for Day 2 morning.", "highlight": False, "removed": True},
        ]

    for item in revised_items:
        badge_map = {
            "Delayed": "badge-delayed",
            "Rescheduled": "badge-rescheduled",
            "Auto-Adjusted": "badge-auto-adjusted",
            "Removed": "badge-removed",
        }
        badge_class = badge_map.get(item["status"], "")
        bg = "background:var(--primary-glow);" if item["highlight"] else ""
        opacity = "opacity:0.5;filter:grayscale(1);" if item["removed"] else ""
        text_decoration = "text-decoration:line-through;" if item["removed"] else ""

        time_html = ""
        if item["old_time"]:
            if item["new_time"]:
                time_html = f'<div style="display:flex;align-items:center;gap:6px;margin-top:4px;"><span style="text-decoration:line-through;color:var(--text-light);font-size:13px;">{item["old_time"]}</span><span style="color:var(--text-light);font-size:12px;">→</span><span style="font-weight:700;color:{"#dc2626" if item["status"] == "Delayed" else "#059669"};font-size:13px;">{item["new_time"]}</span></div>'
            else:
                time_html = f'<div style="font-size:13px;color:var(--text-light);margin-top:4px;">{item["old_time"]}</div>'

        note_html = f'<p style="font-size:12px;font-style:italic;color:var(--text-light);margin:4px 0 0;">{item["note"]}</p>' if item["note"] else ""

        pulse_dot = '<div style="width:8px;height:8px;border-radius:50%;background:var(--primary);animation:pulse 2s infinite;"></div>' if item["highlight"] else ""

        st.markdown(f"""
        <div style="display:flex;gap:12px;padding:16px 20px;border-bottom:1px solid #f8fafc;{bg}{opacity}">
            <div style="width:44px;height:44px;border-radius:10px;background:#f1f5f9;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;">
                {item['icon']}
            </div>
            <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:15px;font-weight:600;{text_decoration}">{item['name']}</span>
                    <span class="badge {badge_class}">{item['status']}</span>
                </div>
                {time_html}
                {note_html}
            </div>
            {pulse_dot}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Action buttons
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("✅ Apply New Schedule", type="primary", use_container_width=True):
            st.toast("New schedule applied! ✅")
            st.session_state.current_page = "itinerary"
            st.rerun()
    with btn_col2:
        if st.button("📝 Modify Manually", use_container_width=True):
            st.session_state.current_page = "chat"
            st.rerun()

    # Refinement chat section
    st.markdown("""
    <div style="margin-top:32px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
            <div style="width:32px;height:32px;border-radius:50%;background:var(--primary-light);display:flex;align-items:center;justify-content:center;">
                ✦
            </div>
            <span style="font-size:14px;font-weight:600;color:var(--text-medium);">Ask WanderAI to refine this</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    refine_input = st.text_input(
        "Refine",
        placeholder="e.g. 'Can we swap dinner for a late-night bar?' or 'Find me a 24h cafe instead'",
        label_visibility="collapsed",
        key="replan_input"
    )

    if refine_input:
        st.session_state.user_prompt = refine_input
        st.session_state.current_page = "chat"
        st.session_state.initial_processed = False
        st.rerun()

    # Quick action pills
    quick_actions = [
        "Skip dinner, I'll eat at airport",
        "Is there a faster train?",
        "Add a rest hour",
    ]

    pill_cols = st.columns(len(quick_actions))
    for i, action in enumerate(quick_actions):
        with pill_cols[i]:
            if st.button(f'"{action}"', key=f"quick_{i}", use_container_width=True):
                st.session_state.user_prompt = action
                st.session_state.current_page = "chat"
                st.session_state.initial_processed = False
                st.rerun()

    # Back
    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    if st.button("← Back to Bookings"):
        st.session_state.current_page = "booking"
        st.rerun()
