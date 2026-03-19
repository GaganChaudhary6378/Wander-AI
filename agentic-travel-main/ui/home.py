"""
Screen 1: Home / Welcome Screen
Hero section with "Your Adventure, Planned by AI" + prompt input + example cards.
"""
import streamlit as st
from data.mock_data import SAMPLE_PROMPTS
from ui.components import render_navbar


def render_home():
    """Render the home/welcome screen."""
    render_navbar(active_page="home")

    # Hero Section
    st.markdown("""
    <div class="hero-section" style="text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center;">
        <div class="hero-badge">AI-POWERED TRAVEL</div>
        <h1 class="hero-title" style="text-align: center; width: 100%;">Your Adventure, <span>Planned by AI</span></h1>
        <p class="hero-subtitle" style="text-align: center; width: 100%;">
            Skip the hours of research. Get a personalized, multi-day itinerary
            tailored to your budget and interests in seconds.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Input bar
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown('<div style="height: 8px;"></div>', unsafe_allow_html=True)
        user_input = st.text_input(
            "Trip prompt",
            placeholder="✦  Tell me about your dream trip...",
            label_visibility="collapsed",
            key="home_input"
        )
        plan_clicked = st.button("Plan It  ➤", type="primary", use_container_width=True, key="plan_btn")

        if plan_clicked and user_input:
            st.session_state.user_prompt = user_input
            st.session_state.current_page = "chat"
            st.rerun()
        elif plan_clicked and not user_input:
            st.toast("Please describe your dream trip first! ✈️")

    # Spacing
    st.markdown('<div style="height: 40px;"></div>', unsafe_allow_html=True)

    # Example Prompts Section
    st.markdown("""
    <div style="padding: 0 32px;">
        <h3 style="font-size:22px;font-weight:700;color:var(--text-dark);margin:0 0 4px;">Try these prompts</h3>
        <p style="font-size:14px;color:var(--text-light);margin:0 0 24px;">Get inspired by popular itineraries</p>
    </div>
    """, unsafe_allow_html=True)

    # Prompt cards
    cols = st.columns(3)
    for i, prompt in enumerate(SAMPLE_PROMPTS):
        with cols[i]:
            category_colors = {
                "BUDGET": "#4dd1c4",
                "GROUP": "#3b82f6",
                "ROMANTIC": "#ec4899",
            }
            cat_color = category_colors.get(prompt["category"], "#4dd1c4")

            st.markdown(f"""
            <div class="card" style="cursor:pointer;">
                <div style="position:relative;">
                    <img src="{prompt['image_url']}" class="card-image" style="width:100%;height:180px;object-fit:cover;" />
                    <div style="position:absolute;top:12px;left:12px;font-size:10px;font-weight:800;color:white;background:{cat_color};padding:3px 10px;border-radius:4px;text-transform:uppercase;letter-spacing:1px;">
                        {prompt['category']}
                    </div>
                </div>
                <div class="card-body">
                    <p class="card-title">{prompt['title']}</p>
                    <p class="card-subtitle">{prompt['subtitle']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Try this →", key=f"prompt_btn_{i}", use_container_width=True):
                st.session_state.user_prompt = prompt["prompt"]
                st.session_state.current_page = "chat"
                st.rerun()

    # Footer
    st.markdown("""
    <div style="text-align:center;padding:40px 0 20px;border-top:1px solid var(--border);margin-top:40px;">
        <p style="font-size:12px;color:var(--text-light);">© 2024 WanderAI. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)
