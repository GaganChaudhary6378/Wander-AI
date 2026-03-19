"""
Shared UI components for the WanderAI Streamlit frontend.
"""
import streamlit as st


def render_navbar(active_page="home", budget_remaining=None, currency="INR"):
    """Render the top navigation bar."""
    budget_html = ""
    if budget_remaining is not None:
        budget_html = f'<span style="display:inline-flex;align-items:center;gap:8px;background:#e0f7f4;border:1px solid rgba(77,209,196,0.3);border-radius:999px;padding:6px 16px;font-size:12px;font-weight:800;letter-spacing:0.5px;color:#000000;">💰 Budget: {currency} {budget_remaining:,.0f}</span>'

    # Only show right section if there's content
    right_section = f'<div style="display:flex;align-items:center;gap:16px;">{budget_html}</div>' if budget_html else ''

    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 32px;background:white;border-bottom:1px solid #e2e8f0;width:100%;">
        <div style="display:flex;align-items:center;gap:12px;">
            <div style="width:32px;height:32px;background:#4dd1c4;border-radius:8px;display:flex;align-items:center;justify-content:center;color:white;font-size:16px;font-weight:800;">✦</div>
            <h2 style="font-size:20px;font-weight:800;margin:0;letter-spacing:-0.5px;">WanderAI</h2>
        </div>
        {right_section}
    </div>
    """, unsafe_allow_html=True)


def render_chat_message(content: str, is_user: bool = False, name: str = None):
    """Render a single chat message bubble."""
    import re

    # If it's an AI message that contains complex HTML (like cards or summaries),
    # check if it's primarily an HTML component.
    is_html_component = not is_user and ("<div" in content or "<table" in content)
    
    label = name or "Aether"
    if is_user:
        st.markdown(f"""
        <div style="display:flex;gap:12px;max-width:85%;margin-left:auto;flex-direction:row-reverse;margin-bottom:16px;">
            <div style="width:36px;height:36px;border-radius:50%;background:#4dd1c4;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;color:white;">👤</div>
            <div>
                <div style="font-size:11px;color:#525252;font-weight:500;margin-bottom:4px;text-align:right;">You</div>
                <div style="background:#4dd1c4;border-radius:16px 16px 4px 16px;padding:12px 16px;font-size:14px;line-height:1.6;font-weight:600;color:#000000;white-space:pre-wrap;">{content}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif is_html_component:
        # For complex HTML (like cards), don't wrap in a restrictive bubble div.
        # Just provide the avatar and label, then the content.
        st.markdown(f"""
        <div style="display:flex;gap:12px;max-width:98%;margin-bottom:8px;">
            <div style="width:36px;height:36px;border-radius:50%;background:#e0f7f4;border:1px solid rgba(77,209,196,0.3);display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;color:#4dd1c4;">✦</div>
            <div style="flex:1;">
                <div style="font-size:11px;color:#525252;font-weight:500;margin-bottom:4px;">{label}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        # Render the content (mixed Markdown/HTML) separately to ensure block tags work
        st.markdown(content, unsafe_allow_html=True)
    else:
        # Simple text bubble
        html_content = content.replace('\n', '<br>')
        html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
        st.markdown(f"""
        <div style="display:flex;gap:12px;max-width:85%;margin-bottom:16px;">
            <div style="width:36px;height:36px;border-radius:50%;background:#e0f7f4;border:1px solid rgba(77,209,196,0.3);display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;color:#4dd1c4;">✦</div>
            <div>
                <div style="font-size:11px;color:#525252;font-weight:500;margin-bottom:4px;">{label}</div>
                <div style="background:#f1f5f9;border-radius:16px 16px 16px 4px;padding:12px 16px;font-size:14px;line-height:1.6;color:#000000;">{html_content}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_typing_indicator():
    """Render the 'Aether is planning...' typing indicator."""
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;padding:4px 0;">
        <span style="font-size:12px;font-weight:600;font-style:italic;color:#525252;">Aether is planning...</span>
    </div>
    """, unsafe_allow_html=True)


def render_day_card(day: dict, currency: str = "INR"):
    """Render a day card with activities — uses separate st.markdown calls for reliability."""
    day_num = day.get("day_number", 1)
    theme = day.get("theme", "")
    est_cost = day.get("estimated_cost", 0)
    weather = day.get("weather", "")
    weather_temp = day.get("weather_temp", "")
    activities = day.get("activities", [])

    weather_badge = f"☀️ {weather_temp} {weather}" if weather else ""

    # Card header
    st.markdown(f"""
    <div style="background:white;border:1px solid #e2e8f0;border-left:3px solid #4dd1c4;border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.06);margin-bottom:4px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <div>
                <div style="font-size:16px;font-weight:700;color:#000000;">Day {day_num}: {theme}</div>
                <div style="font-size:12px;color:#525252;font-weight:500;margin-top:2px;">{weather_badge}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:12px;color:#525252;font-weight:500;">Day {day_num}</div>
                <div style="font-size:12px;color:#3ab8ac;font-weight:700;">Est. {currency} {est_cost:,.0f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Render each activity as a separate st.markdown call for reliable rendering
    for act in activities:
        cost = act.get("cost", 0)
        cost_str = f"{currency} {cost:,.0f}" if cost > 0 else "Free ✓"
        cost_color = "#4dd1c4" if cost > 0 else "#16a34a"
        name = act.get("name", "Activity")
        time_str = act.get("time", "")
        desc = act.get("description", "")[:80]
        status = act.get("status", "")

        status_html = ""
        if status:
            badge_colors = {
                "Delayed": ("#fef2f2", "#dc2626"),
                "Rescheduled": ("#e0f7f4", "#3ab8ac"),
                "Auto-Adjusted": ("#e0f7f4", "#3ab8ac"),
                "Removed": ("#f1f5f9", "#94a3b8"),
            }
            bg, fg = badge_colors.get(status, ("#f1f5f9", "#94a3b8"))
            status_html = f'<span style="font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;background:{bg};color:{fg};text-transform:uppercase;margin-left:6px;">{status}</span>'

        st.markdown(f"""
        <div style="display:flex;gap:10px;padding:8px 16px;border-left:2px solid #e0f7f4;margin-left:8px;">
            <div style="min-width:60px;">
                <span style="font-size:11px;font-weight:600;color:#4dd1c4;">{time_str}</span>
            </div>
            <div style="flex:1;">
                <div style="display:flex;align-items:center;">
                    <span style="font-size:13px;font-weight:700;color:#000000;">{name}</span>{status_html}
                    <a href="https://www.google.com/maps/search/?api=1&query={name.replace(' ', '+')}" target="_blank" style="margin-left:8px;text-decoration:none;font-size:12px;" title="View on Google Maps">📍</a>
                </div>
                <div style="font-size:11px;color:#1f2937;font-weight:500;margin-top:2px;">{desc}</div>
            </div>
            <div style="font-size:12px;font-weight:700;color:{cost_color};white-space:nowrap;">{cost_str}</div>
        </div>
        """, unsafe_allow_html=True)


def render_budget_summary(budget: dict, currency: str = "INR"):
    """Render the budget summary card using native Streamlit components."""
    st.markdown('<h3 style="color: black; margin-bottom: 16px;">💰 Budget Summary</h3>', unsafe_allow_html=True)

    items = [
        ("🏨 Accommodation", budget.get("accommodation", 0)),
        ("🎯 Activities", budget.get("activities", 0)),
        ("🍽️ Food & Dining", budget.get("food", 0)),
        ("🚗 Transport", budget.get("transport", 0)),
        ("📦 Miscellaneous", budget.get("miscellaneous", 0)),
    ]

    for label, value in items:
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown(f"**{label}**")
        with col2:
            st.markdown(f"**{currency} {value:,.0f}**")

    st.divider()

    total = budget.get("total", 0)
    per_person = budget.get("per_person", 0)
    st.metric(label="Estimated Total", value=f"{currency} {total:,.0f}")
    if per_person and per_person != total:
        st.caption(f"Per person: {currency} {per_person:,.0f}")


def render_booking_card(booking: dict):
    """Render a booking confirmation card."""
    btype = booking.get("type", "")
    details = booking.get("details", {})
    ref = booking.get("reference", "")
    status = booking.get("status", "pending")

    badge_color = "#16a34a" if status == "confirmed" else "#d97706"
    badge_bg = "#dcfce7" if status == "confirmed" else "#fef3c7"

    if btype == "flight":
        origin = details.get("origin", "")
        dest = details.get("destination", "")
        currency = details.get("currency", "INR")
        price = details.get("price", 0)

        st.markdown(f"""
        <div style="background:white;border-radius:16px;padding:20px;box-shadow:0 4px 12px rgba(0,0,0,0.08);margin-bottom:16px;border:1px solid #e2e8f0;">
            <div style="font-size:10px;font-weight:700;color:#4dd1c4;text-transform:uppercase;letter-spacing:1px;">✈️ FLIGHT {details.get('flight_number', '')}</div>
            <div style="display:flex;align-items:center;gap:12px;margin:12px 0;">
                <div style="font-size:24px;font-weight:800;">{origin[:3].upper()}</div>
                <div style="font-size:12px;color:#4dd1c4;">✈ {details.get('duration', '')}</div>
                <div style="font-size:24px;font-weight:800;">{dest[:3].upper()}</div>
                <span style="margin-left:auto;font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;background:{badge_bg};color:{badge_color};text-transform:uppercase;">{status}</span>
            </div>
            <div style="display:flex;gap:24px;font-size:12px;color:#475569;">
                <div>Departure<br><strong>{details.get('departure', '')}</strong></div>
                <div>Seat<br><strong>{details.get('seat', '')}</strong></div>
                <div>PNR<br><strong>{ref}</strong></div>
                <div>Price<br><strong>{currency} {price:,}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif btype == "hotel":
        currency = details.get("currency", "INR")
        total = details.get("total_price", 0)

        st.markdown(f"""
        <div style="background:white;border-radius:16px;padding:20px;box-shadow:0 4px 12px rgba(0,0,0,0.08);margin-bottom:16px;border:1px solid #e2e8f0;">
            <div style="font-size:10px;font-weight:700;color:#4dd1c4;text-transform:uppercase;letter-spacing:1px;">🏨 HOTEL</div>
            <div style="font-size:18px;font-weight:700;margin:8px 0 4px;">{details.get('hotel_name', '')}</div>
            <div style="font-size:13px;color:#475569;margin-bottom:12px;">📍 {details.get('location', '')} · {details.get('room_type', 'Standard Room')}</div>
            <div style="display:flex;gap:24px;font-size:12px;color:#475569;">
                <div>Check-in<br><strong>{details.get('check_in', '')}</strong></div>
                <div>Stay<br><strong>{details.get('nights', '')} Nights</strong></div>
                <div>REF<br><strong>{ref}</strong></div>
                <div>Total<br><strong>{currency} {total:,}</strong></div>
            </div>
            <div style="margin-top:12px;display:flex;align-items:center;gap:12px;">
                <span style="font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;background:{badge_bg};color:{badge_color};text-transform:uppercase;">{status}</span>
                {f'<a href="{details.get("booking_url")}" target="_blank" style="font-size:11px;color:#4dd1c4;text-decoration:none;font-weight:600;">🔗 View Booking</a>' if details.get("booking_url") else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_map(locations: list, center: tuple = None):
    """Render a Folium map with location pins."""
    try:
        import folium
        from streamlit_folium import st_folium

        if not locations:
            st.info("No map data available.")
            return

        if center is None:
            avg_lat = sum(loc.get("lat", 0) for loc in locations) / len(locations)
            avg_lon = sum(loc.get("lon", 0) for loc in locations) / len(locations)
            center = (avg_lat, avg_lon)

        m = folium.Map(location=center, zoom_start=13, tiles="CartoDB positron")

        for i, loc in enumerate(locations):
            name = loc.get("name", "")
            lat = loc.get("lat", 0)
            lon = loc.get("lon", 0)
            maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            popup_html = f'<b>{name}</b><br><a href="{maps_url}" target="_blank">View on Google Maps</a>'
            
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup_html, max_width=200),
                tooltip=name,
                icon=folium.Icon(color="green" if i == 0 else "blue", icon="info-sign"),
            ).add_to(m)

        st_folium(m, width=None, height=300, returned_objects=[])
    except ImportError:
        st.warning("🗺️ Map requires `folium` and `streamlit-folium`. Run: `pip install folium streamlit-folium`")
    except Exception as e:
        print(f"Map render error: {e}")
        st.warning(f"🗺️ Map could not load: {e}")
