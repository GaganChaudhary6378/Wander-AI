"""
Screen 6: Booking Confirmation Screen
"Trip Locked In!" success state with flight + hotel cards and remaining budget.
"""
import streamlit as st
from ui.components import render_navbar, render_booking_card, render_budget_summary


def render_booking():
    """Render the booking confirmation screen."""
    bookings = st.session_state.get("bookings") or []
    itinerary = st.session_state.get("itinerary") or []
    profile = st.session_state.get("travel_profile") or {}
    budget = st.session_state.get("budget_breakdown") or {}
    currency = profile.get("currency", "INR")
    destination = profile.get("destination", "Trip")

    render_navbar(active_page="itinerary")

    # Success header
    st.markdown(f"""
    <div style="text-align:center;padding:40px 20px 20px;">
        <div class="success-icon">✓</div>
        <h1 class="success-title">Trip Locked In! 🎉</h1>
        <p style="font-size:16px;color:var(--text-medium);margin:0 0 24px;">
            Your {destination} adventure is officially confirmed. Pack your bags!
        </p>
    </div>
    """, unsafe_allow_html=True)



    # Booking cards
    main_col = st.columns([1, 6, 1])[1]
    with main_col:
        for booking in bookings:
            render_booking_card(booking)

        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

        # Budget remaining summary
        if budget and bookings:
            total_budget = profile.get("budget", 0)
            total_booked = 0
            for b in bookings:
                d = b.get("details", {})
                if b.get("type") == "flight":
                    total_booked += d.get("price", 0)
                elif b.get("type") == "hotel":
                    total_booked += d.get("total_price", 0)
            remaining = total_budget - total_booked

            st.markdown(f"""
            <div class="budget-summary">
                <h3 style="font-size:18px;font-weight:700;margin:0 0 16px;">💰 Remaining Budget Summary</h3>
                <div class="budget-row">
                    <span class="budget-label">Total Trip Budget</span>
                    <span class="budget-value">{currency} {total_budget:,.2f}</span>
                </div>
                <div class="budget-row">
                    <span class="budget-label">Booked (Flight + Hotel)</span>
                    <span style="font-weight:600;color:#ef4444;">-{currency} {total_booked:,.2f}</span>
                </div>
                <div class="budget-total">
                    <div>
                        <div class="budget-total-label" style="font-weight:700;">Remaining for Food & Fun</div>
                    </div>
                    <div class="budget-total-value">{currency} {remaining:,.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

        # Chat link
        st.markdown(f"""
        <div style="text-align:center;padding:16px 0;">
            <p style="font-size:14px;color:var(--primary);font-weight:600;cursor:pointer;">
                💬 Need changes? Chat with me
            </p>
            <p style="font-size:12px;color:var(--text-light);margin-top:4px;">
                All confirmation details have been sent to your email.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Navigation
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    nav_cols = st.columns(3)
    with nav_cols[0]:
        if st.button("← Back to Chat"):
            st.session_state.current_page = "chat"
            st.rerun()
    with nav_cols[1]:
        if st.button("📋 View Itinerary"):
            st.session_state.current_page = "itinerary"
            st.rerun()
    with nav_cols[2]:
        if st.button("🔄 Simulate Delay"):
            st.session_state.current_page = "replan"
            st.rerun()

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

    # Action buttons (PDF and Calendar)
    btn_spacer1, btn1, btn2, btn_spacer2 = st.columns([1, 1.5, 1.5, 1])
    with btn1:
        if st.button("📅 Add to Calendar", use_container_width=True):
            st.toast("Calendar event created! 📅")
    with btn2:
        from utils.pdf_generator import generate_itinerary_pdf
        pdf_data = generate_itinerary_pdf(profile, itinerary, bookings, budget, currency)
        st.download_button(
            label="📄 Save PDF",
            data=pdf_data,
            file_name=f"Trip_to_{destination}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
