"""
WanderAI — AI Travel Planning & Booking Agent
Main Streamlit Application Entry Point

Run with: streamlit run app.py
"""

import streamlit as st

# Page config — must be first Streamlit command
st.set_page_config(
    page_title="WanderAI — AI Travel Planner",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Load custom CSS
from ui.styles import CUSTOM_CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Initialize session state
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"
if "user_prompt" not in st.session_state:
    st.session_state.user_prompt = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "travel_profile" not in st.session_state:
    st.session_state.travel_profile = None
if "research_results" not in st.session_state:
    st.session_state.research_results = None
if "budget_breakdown" not in st.session_state:
    st.session_state.budget_breakdown = None
if "itinerary" not in st.session_state:
    st.session_state.itinerary = None
if "bookings" not in st.session_state:
    st.session_state.bookings = None
if "reasoning_log" not in st.session_state:
    st.session_state.reasoning_log = []
if "agent_stage" not in st.session_state:
    st.session_state.agent_stage = "idle"
if "initial_processed" not in st.session_state:
    st.session_state.initial_processed = False


def main():
    """Route to the appropriate page based on session state."""
    page = st.session_state.current_page

    if page == "home":
        from ui.home import render_home
        render_home()
    elif page == "chat":
        from ui.chat import render_chat
        render_chat()
    elif page == "itinerary":
        from ui.itinerary import render_itinerary
        render_itinerary()
    elif page == "day_view":
        from ui.day_view import render_day_view
        render_day_view()
    elif page == "booking":
        from ui.booking import render_booking
        render_booking()
    elif page == "replan":
        from ui.replan import render_replan
        render_replan()
    else:
        from ui.home import render_home
        render_home()


if __name__ == "__main__":
    main()
