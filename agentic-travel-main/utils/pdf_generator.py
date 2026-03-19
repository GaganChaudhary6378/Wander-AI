import io
import re
from fpdf import FPDF
from datetime import datetime


def _strip_emojis(text: str) -> str:
    """Remove emojis and other non-ASCII characters from text for PDF compatibility."""
    if not text:
        return ""
    # Remove emojis and other Unicode symbols
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"  # Enclosed characters
        "\U0001F1E0-\U0001F1FF"  # Flags
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub("", text)
    # Also remove any remaining non-ASCII characters that might cause issues
    text = text.encode("ascii", "ignore").decode("ascii")
    return text.strip()


class TripPDF(FPDF):
    def header(self):
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Move to the right
        self.cell(80)
        # Title
        self.cell(30, 10, 'Trip Itinerary', 0, 0, 'C')
        # Line break
        self.ln(20)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

def generate_itinerary_pdf(profile, itinerary, bookings, budget, currency="INR"):
    """
    Generate a PDF bytes object for the trip itinerary.
    """
    pdf = TripPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # Destination Header
    pdf.set_font('Arial', 'B', 24)
    destination = _strip_emojis(profile.get('destination', 'Your Trip'))
    pdf.cell(0, 15, f"{destination} Adventure", ln=True, align='L')
    
    # Trip Details
    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(100, 100, 100)
    dates = _strip_emojis(profile.get('dates', 'Upcoming'))
    group_size = profile.get('group_size', 1)
    ppl_str = "Traveler" if group_size == 1 else "Travelers"
    pdf.cell(0, 8, f"{dates} | {group_size} {ppl_str}", ln=True)
    pdf.ln(10)
    
    # Budget Section
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, "Budget Summary", ln=True)
    pdf.set_font('Arial', '', 11)
    
    budget_items = [
        ("Accommodation", budget.get("accommodation", 0)),
        ("Transport", budget.get("transport", 0)),
        ("Food & Dining", budget.get("food", 0)),
        ("Activities", budget.get("activities", 0)),
        ("Miscellaneous", budget.get("miscellaneous", 0)),
    ]
    
    for label, value in budget_items:
        pdf.cell(100, 8, label, border=0)
        pdf.cell(0, 8, f"{currency} {value:,.0f}", border=0, ln=True, align='R')
    
    pdf.set_font('Arial', 'B', 11)
    pdf.line(pdf.get_x(), pdf.get_y(), 200, pdf.get_y())
    pdf.cell(100, 10, "Estimated Total", border=0)
    pdf.cell(0, 10, f"{currency} {budget.get('total', 0):,.0f}", border=0, ln=True, align='R')
    pdf.ln(10)
    
    # Itinerary Section
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, "Day-by-Day Itinerary", ln=True)
    
    for day in itinerary:
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 14)
        pdf.set_fill_color(240, 240, 240)
        day_num = day.get('day_number', 'X')
        theme = _strip_emojis(day.get('theme', 'Explore'))
        pdf.cell(0, 10, f"Day {day_num}: {theme}", ln=True, fill=True)
        
        pdf.set_font('Arial', '', 11)
        for act in day.get('activities', []):
            time = _strip_emojis(act.get('time', 'N/A'))
            name = _strip_emojis(act.get('name', 'Activity'))
            cost = act.get('cost', 0)
            cost_str = f"({currency} {cost:,.0f})" if cost > 0 else "(Free)"
            
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(25, 8, f"{time}", border=0)
            
            # Destination-based maps link
            maps_link = f"https://www.google.com/maps/search/?api=1&query={name.replace(' ', '+')}"
            
            pdf.set_font('Arial', '', 10)
            # Safety: Calculate exact remaining width to avoid FPDFException
            # Using a slightly larger margin buffer (10) for safety
            footer_safe_w = pdf.w - pdf.r_margin - pdf.get_x() - 5
            if footer_safe_w < 10:
                pdf.ln(8)
                pdf.cell(25, 8, "", border=0)
                footer_safe_w = pdf.w - pdf.r_margin - pdf.get_x() - 5
                
            # Ensure width is at least something reasonable
            final_w = max(footer_safe_w, 40)
            pdf.multi_cell(final_w, 8, f"{name} {cost_str}", link=maps_link)
            
    # Bookings Section
    if bookings:
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, "Booking Confirmations", ln=True)
        pdf.ln(5)
        
        for booking in bookings:
            b_type = _strip_emojis(booking.get('type', 'Booking')).capitalize()
            details = booking.get('details', {})
            name = _strip_emojis(
                details.get('hotel_name') or details.get('airline') or booking.get('name', 'N/A')
            )
            ref = _strip_emojis(booking.get('reference', 'N/A'))
            status = _strip_emojis(booking.get('status', 'Pending'))
            booking_url = details.get('booking_url', '')
            
            pdf.set_font('Arial', 'B', 12)
            # Add link to the booking title
            pdf.cell(0, 8, f"{b_type}: {name}", ln=True, link=booking_url)
            pdf.set_font('Arial', '', 11)
            pdf.cell(0, 6, f"Status: {status}", ln=True)
            pdf.cell(0, 6, f"Reference: {ref}", ln=True)
            if booking_url:
                pdf.set_text_color(0, 0, 255)
                pdf.set_font('Arial', 'U', 10)
                pdf.cell(0, 6, "View Booking Online", ln=True, link=booking_url)
                pdf.set_text_color(0, 0, 0)
            pdf.ln(5)

    # Return PDF as bytes
    # fpdf2's output() returns bytearray, Streamlit needs bytes
    return bytes(pdf.output())
