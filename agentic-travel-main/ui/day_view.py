"""
Screen 4: Detailed Day View Screen
Hero image with weather, timeline of activities, route map, and smart alternatives.
"""
import streamlit as st
from ui.components import render_navbar, render_map
from data.mock_data import LOCATION_COORDS


def render_day_view():
    """Render the detailed day view screen."""
    itinerary = st.session_state.get("itinerary", [])
    profile = st.session_state.get("travel_profile", {})
    currency = profile.get("currency", "INR")
    day_idx = st.session_state.get("selected_day", 0)

    if not itinerary or day_idx >= len(itinerary):
        st.warning("No day selected to view.")
        if st.button("← Back to Itinerary"):
            st.session_state.current_page = "itinerary"
            st.rerun()
        return

    day = itinerary[day_idx]
    day_num = day.get("day_number", 1)
    theme = day.get("theme", "Exploration")
    weather = day.get("weather", "Sunny")
    weather_temp = day.get("weather_temp", "25°C")
    activities = day.get("activities", [])
    destination = profile.get("destination", "")

    render_navbar(active_page="itinerary")

    # Back button + header
    col_back, col_title, col_nav = st.columns([1, 6, 3])
    with col_back:
        if st.button("←"):
            st.session_state.current_page = "itinerary"
            st.rerun()
    with col_title:
        st.markdown(f"""
        <div>
            <h2 style="margin:0;font-size:22px;font-weight:800;">Day {day_num}: {theme}</h2>
            <p style="margin:2px 0 0;font-size:13px;color:var(--text-light);">{destination}</p>
        </div>
        """, unsafe_allow_html=True)

    # Hero section with weather
    hero_img = ""
    for act in activities:
        if act.get("image_url"):
            hero_img = act["image_url"]
            break

    if hero_img:
        st.markdown(f"""
        <div style="position:relative;border-radius:16px;overflow:hidden;margin:16px 0;height:220px;background:url('{hero_img}') center/cover no-repeat;">
            <div style="position:absolute;inset:0;background:linear-gradient(to top,rgba(0,0,0,0.6),transparent);"></div>
            <div style="position:absolute;bottom:16px;left:20px;">
                <div style="display:inline-flex;align-items:center;gap:6px;background:rgba(0,0,0,0.5);backdrop-filter:blur(4px);border-radius:8px;padding:4px 12px;color:white;font-size:13px;">
                    ☀️ {weather_temp} {weather}
                </div>
                <h2 style="color:white;font-size:24px;font-weight:800;margin:8px 0 0;">
                    {destination} {theme}
                </h2>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Stats bar
    total_cost = sum(a.get("cost", 0) for a in activities)
    total_duration = sum(a.get("duration_mins", 60) for a in activities)

    st.markdown(f"""
    <div style="display:flex;gap:12px;margin:12px 0 24px;">
        <div style="flex:1;background:#f8fafc;border-radius:12px;padding:12px 16px;">
            <div style="font-size:10px;font-weight:700;color:var(--text-light);text-transform:uppercase;letter-spacing:1px;">Activities</div>
            <div style="font-size:20px;font-weight:800;color:var(--text-dark);">{len(activities)}</div>
        </div>
        <div style="flex:1;background:#f8fafc;border-radius:12px;padding:12px 16px;">
            <div style="font-size:10px;font-weight:700;color:var(--text-light);text-transform:uppercase;letter-spacing:1px;">Duration</div>
            <div style="font-size:20px;font-weight:800;color:var(--text-dark);">{total_duration // 60}h {total_duration % 60}m</div>
        </div>
        <div style="flex:1;background:#f8fafc;border-radius:12px;padding:12px 16px;">
            <div style="font-size:10px;font-weight:700;color:var(--text-light);text-transform:uppercase;letter-spacing:1px;">Total</div>
            <div style="font-size:20px;font-weight:800;color:var(--primary);">{currency} {total_cost:,.0f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Activities timeline + Alternatives sidebar
    main_col, side_col = st.columns([6, 4])

    with main_col:
        for i, act in enumerate(activities):
            cost = act.get("cost", 0)
            cost_str = f"{currency} {cost:,.0f}" if cost > 0 else "Free"
            cost_color = "var(--primary)" if cost > 0 else "#16a34a"
            img_url = act.get("image_url", "")

            img_html = ""
            if img_url:
                img_html = f"""
                <div style="display:flex;gap:8px;margin:8px 0;">
                    <img src="{img_url}" style="width:120px;height:80px;border-radius:8px;object-fit:cover;" />
                </div>
                """

            st.markdown(f"""
            <div style="display:flex;gap:16px;padding:16px 0;border-bottom:1px solid #f1f5f9;">
                <div style="display:flex;flex-direction:column;align-items:center;min-width:20px;">
                    <div style="width:12px;height:12px;border-radius:50%;background:var(--primary);border:3px solid white;box-shadow:0 0 0 2px var(--primary-light);"></div>
                    {"<div style='width:2px;flex:1;background:var(--primary-light);'></div>" if i < len(activities) - 1 else ""}
                </div>
                <div style="flex:1;">
                    <div style="font-size:12px;font-weight:600;color:var(--primary);">{act.get('time', '')}</div>
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <h4 style="font-size:16px;font-weight:700;margin:4px 0;">{act.get('name', '')}</h4>
                        <span style="font-size:14px;font-weight:700;color:{cost_color};">{cost_str}</span>
                    </div>
                    <p style="font-size:13px;color:var(--text-medium);margin:4px 0;">{act.get('description', '')}</p>
                    {img_html}
                    <div style="font-size:11px;color:var(--text-light);">📍 {act.get('location', '')} • ⏱ {act.get('duration_mins', 60)} mins</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with side_col:
        # Route Map
        dest = destination.lower()
        if dest in LOCATION_COORDS:
            st.markdown("""
            <div style="margin-bottom:16px;">
                <h4 style="font-size:15px;font-weight:700;margin:0 0 8px;">Today's Route</h4>
            </div>
            """, unsafe_allow_html=True)
            coords = LOCATION_COORDS[dest]
            locations = [{"lat": coords["lat"], "lon": coords["lon"], "name": destination}]
            render_map(locations, (coords["lat"], coords["lon"]))

        # Smart Alternatives
        st.markdown("""
        <div style="margin-top:16px;">
            <h4 style="font-size:13px;font-weight:700;color:var(--text-light);text-transform:uppercase;letter-spacing:1px;margin:0 0 12px;">
                SMART ALTERNATIVES
            </h4>
        </div>
        """, unsafe_allow_html=True)

        alternatives = [
            {"tag": "BETTER EXPERIENCE", "name": "Private Tour Option", "desc": "Get a personal guide for a deeper immersion", "delta": "+₹400", "color": "#8b5cf6"},
            {"tag": "BUDGET CHOICE", "name": "Self-Guided Walk", "desc": "Save money with a free self-guided tour", "delta": "-₹300", "color": "#16a34a"},
            {"tag": "TIME SAVER", "name": "Express Route", "desc": "Skip the queues with early morning entry", "delta": "-25 mins", "color": "#3b82f6"},
        ]

        for alt in alternatives:
            st.markdown(f"""
            <div style="background:white;border:1px solid var(--border);border-radius:12px;padding:14px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <span style="font-size:10px;font-weight:700;color:{alt['color']};text-transform:uppercase;letter-spacing:0.5px;">{alt['tag']}</span>
                    <span style="font-size:12px;font-weight:700;color:{alt['color']};">{alt['delta']}</span>
                </div>
                <div style="font-size:14px;font-weight:600;margin-bottom:4px;">{alt['name']}</div>
                <div style="font-size:12px;color:var(--text-medium);">{alt['desc']}</div>
                <div style="margin-top:8px;font-size:12px;color:var(--primary);font-weight:600;cursor:pointer;">Switch activity →</div>
            </div>
            """, unsafe_allow_html=True)

        # Dinner recommendation
        st.markdown(f"""
        <div style="background:var(--primary);border-radius:12px;padding:16px;margin-top:12px;">
            <div style="font-size:15px;font-weight:700;color:var(--text-dark);">Looking for dinner?</div>
            <div style="font-size:13px;color:var(--text-dark);opacity:0.8;margin:4px 0 12px;">I found 3 great spots near your last stop.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Recommendations", use_container_width=True):
            st.toast("Feature coming soon! 🍽️")
