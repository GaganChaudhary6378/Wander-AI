"""
WanderAI — Custom CSS Styles
Design system matching the screen mockups: primary #4dd1c4, Inter font, rounded cards, premium aesthetics.
"""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ====== Root Variables ====== */
:root {
    --primary: #4dd1c4;
    --primary-dark: #3ab8ac;
    --primary-light: #e0f7f4;
    --primary-glow: rgba(77, 209, 196, 0.15);
    --bg-main: #f6f8f8;
    --bg-card: #ffffff;
    --bg-chat-ai: #f1f5f9;
    --bg-chat-user: #4dd1c4;
    --text-dark: #000000;
    --text-medium: #1f2937;
    --text-light: #525252;
    --border: #e2e8f0;
    --border-light: rgba(77, 209, 196, 0.15);
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
    --shadow-lg: 0 8px 30px rgba(0,0,0,0.12);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 20px;
}

/* ====== Global Styles ====== */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.stApp {
    background: var(--bg-main) !important;
}

/* Target main content text for black color without breaking UI components */
.stMarkdown p, .stMarkdown li, .stMarkdown div, .stMarkdown span {
    color: #111827 !important; /* Premium dark charcoal instead of pure black */
}

/* Ensure headings in markdown are also dark */
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    color: #000000 !important;
}

/* Hide streamlit default elements */
#MainMenu, header[data-testid="stHeader"], footer {
    display: none !important;
}

div[data-testid="stToolbar"] {
    display: none !important;
}

/* Hide Streamlit dev toolbar and any debug overlays */
div[data-testid="stDecoration"],
div[data-testid="stStatusWidget"],
.stDeployButton,
iframe[title="streamlit_dev_toolbar"],
div[class*="stToolbar"],
div[class*="viewerBadge"] {
    display: none !important;
}

/* Hide any stray debug elements that might appear */
body > div[style*="position: fixed"][style*="z-index"] {
    display: none !important;
}

.block-container {
    padding-top: 0 !important;
    max-width: 100% !important;
}

/* ====== Navbar ====== */
.navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 32px;
    background: white;
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 100;
}

.navbar-brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

.navbar-brand h2 {
    font-size: 20px;
    font-weight: 800;
    color: #000000 !important;
    margin: 0;
    letter-spacing: -0.5px;
}

.navbar-logo {
    width: 32px;
    height: 32px;
    background: var(--primary);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 16px;
    font-weight: 800;
}

.navbar-links {
    display: flex;
    gap: 28px;
    align-items: center;
}

.navbar-links a {
    font-size: 14px;
    font-weight: 500;
    color: var(--text-medium);
    text-decoration: none;
    transition: color 0.2s;
}

.navbar-links a.active {
    color: var(--primary);
}

.budget-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--primary-light);
    border: 1px solid rgba(77, 209, 196, 0.3);
    border-radius: 999px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 700;
    color: var(--text-dark);
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* ====== Hero Section ====== */
.hero-section {
    text-align: center;
    padding: 60px 20px 40px;
    background: linear-gradient(180deg, #e8f6f5 0%, var(--bg-main) 100%);
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
}

.hero-badge {
    display: inline-block;
    font-size: 12px;
    font-weight: 700;
    color: var(--primary);
    border: 1.5px solid var(--primary);
    border-radius: 999px;
    padding: 4px 16px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 16px;
}

.hero-title {
    font-size: 48px;
    font-weight: 800;
    color: var(--text-dark);
    line-height: 1.15;
    margin: 0 auto 16px;
    max-width: 700px;
    text-align: center;
    width: 100%;
}

.hero-title span {
    color: var(--primary);
}

.hero-subtitle {
    font-size: 16px;
    color: var(--text-medium);
    max-width: 500px;
    margin: 0 auto 32px;
    line-height: 1.6;
    text-align: center;
    width: 100%;
}

/* ====== Input Bar ====== */
.input-bar {
    display: flex;
    align-items: center;
    max-width: 600px;
    margin: 0 auto;
    background: white;
    border: 2px solid var(--border);
    border-radius: 16px;
    padding: 4px 4px 4px 16px;
    box-shadow: var(--shadow-md);
    transition: border-color 0.2s;
}

.input-bar:focus-within {
    border-color: var(--primary);
}

.input-bar input {
    flex: 1;
    border: none;
    outline: none;
    font-size: 15px;
    font-family: 'Inter', sans-serif;
    color: var(--text-dark);
    background: transparent;
    padding: 12px 8px;
}

.input-bar input::placeholder {
    color: var(--text-light);
}

.btn-primary {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--primary);
    color: var(--text-dark);
    border: none;
    border-radius: 12px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
    font-family: 'Inter', sans-serif;
}

.btn-primary:hover {
    background: var(--primary-dark);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(77, 209, 196, 0.3);
}

.btn-secondary {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: white;
    color: var(--text-dark);
    border: 1.5px solid var(--border);
    border-radius: 12px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    font-family: 'Inter', sans-serif;
}

.btn-secondary:hover {
    border-color: var(--primary);
    background: var(--primary-light);
}

/* ====== Cards ====== */
.card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
    box-shadow: var(--shadow-sm);
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
}

.card-image {
    width: 100%;
    height: 160px;
    object-fit: cover;
    position: relative;
}

.card-badge {
    position: absolute;
    top: 12px;
    left: 12px;
    font-size: 10px;
    font-weight: 800;
    color: white;
    background: var(--primary);
    padding: 3px 10px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.card-body {
    padding: 16px;
}

.card-title {
    font-size: 15px;
    font-weight: 700;
    color: var(--text-dark);
    margin: 0 0 6px;
}

.card-subtitle {
    font-size: 12px;
    color: var(--text-light);
    display: flex;
    align-items: center;
    gap: 6px;
}

/* ====== Chat Styles ====== */
.chat-container {
    display: flex;
    flex-direction: column;
    gap: 20px;
    padding: 16px 0;
}

.chat-message-ai {
    display: flex;
    gap: 12px;
    max-width: 85%;
}

.chat-message-user {
    display: flex;
    gap: 12px;
    max-width: 85%;
    margin-left: auto;
    flex-direction: row-reverse;
}

.chat-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
}

.chat-avatar-ai {
    background: var(--primary-light);
    border: 1px solid rgba(77, 209, 196, 0.3);
    color: var(--primary);
}

.chat-avatar-user {
    background: var(--primary);
    color: white;
}

.chat-bubble-ai {
    background: var(--bg-chat-ai);
    border-radius: 16px 16px 16px 4px;
    padding: 12px 16px;
    font-size: 14px;
    line-height: 1.6;
    color: var(--text-dark);
}

.chat-bubble-user {
    background: var(--bg-chat-user);
    border-radius: 16px 16px 4px 16px;
    padding: 12px 16px;
    font-size: 14px;
    line-height: 1.6;
    color: var(--text-dark);
    font-weight: 500;
}

.chat-label {
    font-size: 11px;
    color: var(--text-light);
    font-weight: 500;
    margin-bottom: 4px;
}

.typing-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
}

.typing-dots {
    display: flex;
    gap: 4px;
}

.typing-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--primary);
    animation: typing-bounce 1.4s ease infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing-bounce {
    0%, 80%, 100% { transform: scale(0.7); opacity: 0.5; }
    40% { transform: scale(1); opacity: 1; }
}

.typing-text {
    font-size: 12px;
    font-weight: 500;
    font-style: italic;
    color: var(--text-light);
}

/* ====== Day Card ====== */
.day-card {
    background: white;
    border: 1px solid var(--border);
    border-left: 3px solid var(--primary);
    border-radius: var(--radius-md);
    padding: 16px;
    box-shadow: var(--shadow-sm);
}

.day-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.day-card-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--text-dark);
}

.day-card-date {
    font-size: 12px;
    color: var(--text-light);
}

/* ====== Timeline ====== */
.timeline {
    position: relative;
    padding-left: 24px;
}

.timeline::before {
    content: '';
    position: absolute;
    left: 7px;
    top: 0;
    bottom: 0;
    width: 2px;
    background: var(--primary-light);
}

.timeline-item {
    position: relative;
    padding: 12px 0 12px 16px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
}

.timeline-item::before {
    content: '';
    position: absolute;
    left: -20px;
    top: 18px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--primary);
    border: 3px solid white;
    box-shadow: 0 0 0 2px var(--primary-light);
}

.timeline-time {
    font-size: 12px;
    font-weight: 600;
    color: var(--primary);
    min-width: 70px;
}

.timeline-content {
    flex: 1;
}

.timeline-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-dark);
}

.timeline-desc {
    font-size: 12px;
    color: var(--text-medium);
    margin-top: 2px;
}

.timeline-cost {
    font-size: 13px;
    font-weight: 700;
    color: var(--primary);
}

/* ====== Budget Summary ====== */
.budget-summary {
    background: white;
    border-radius: var(--radius-lg);
    padding: 24px;
    border: 1px solid var(--border);
    box-shadow: var(--shadow-sm);
}

.budget-row {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid #f1f5f9;
    font-size: 14px;
}

.budget-row:last-child {
    border-bottom: none;
}

.budget-label {
    color: var(--text-medium);
}

.budget-value {
    font-weight: 600;
    color: var(--text-dark);
}

.budget-total {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding-top: 16px;
    margin-top: 8px;
    border-top: 2px solid var(--primary-light);
}

.budget-total-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-light);
}

.budget-total-value {
    font-size: 28px;
    font-weight: 800;
    color: var(--primary);
}

/* ====== Status Badges ====== */
.badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.badge-delayed { background: #fef2f2; color: #dc2626; }
.badge-rescheduled { background: var(--primary-light); color: var(--primary-dark); }
.badge-auto-adjusted { background: var(--primary-light); color: var(--primary-dark); }
.badge-removed { background: #f1f5f9; color: #94a3b8; }
.badge-confirmed { background: #dcfce7; color: #16a34a; }
.badge-reserved { background: #fef3c7; color: #d97706; }
.badge-live { background: var(--primary-light); color: var(--primary); border: 1px solid rgba(77, 209, 196, 0.3); }
.badge-draft { background: var(--primary-light); color: var(--primary); }
.badge-free { color: #16a34a; font-weight: 700; font-size: 13px; }

/* ====== Alert Banner ====== */
.alert-warning {
    background: #fef3c7;
    border: 1px solid #fde68a;
    border-radius: var(--radius-md);
    padding: 16px 20px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
}

.alert-icon {
    font-size: 20px;
}

.alert-title {
    font-size: 15px;
    font-weight: 700;
    color: #92400e;
    margin: 0 0 4px;
}

.alert-text {
    font-size: 13px;
    color: #a16207;
    line-height: 1.5;
}

/* ====== Booking Card ====== */
.booking-card {
    background: white;
    border-radius: var(--radius-lg);
    overflow: hidden;
    box-shadow: var(--shadow-md);
    display: flex;
    margin-bottom: 16px;
}

.booking-card-image {
    width: 180px;
    min-height: 140px;
    object-fit: cover;
}

.booking-card-body {
    padding: 16px 20px;
    flex: 1;
}

.booking-card-type {
    font-size: 10px;
    font-weight: 700;
    color: var(--primary);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
}

/* ====== Approval Modal ====== */
.modal-overlay {
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 200;
}

.modal-content {
    background: white;
    border-radius: var(--radius-xl);
    max-width: 480px;
    margin: 80px auto;
    padding: 24px;
    box-shadow: var(--shadow-lg);
}

/* ====== Quick Action Pills ====== */
.quick-pills {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.quick-pill {
    font-size: 12px;
    font-weight: 500;
    padding: 6px 14px;
    border-radius: 999px;
    border: 1px solid var(--border);
    color: var(--text-medium);
    background: white;
    cursor: pointer;
    transition: all 0.2s;
}

.quick-pill:hover {
    border-color: var(--primary);
    background: var(--primary-light);
    color: var(--primary-dark);
}

/* ====== Confetti / Success ====== */
.success-icon {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--primary), #2dd4bf);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 16px;
    font-size: 32px;
    color: white;
    box-shadow: 0 8px 24px rgba(77, 209, 196, 0.3);
}

.success-title {
    font-size: 32px;
    font-weight: 800;
    text-align: center;
    color: var(--text-dark);
    margin: 0 0 8px;
}

/* ====== Streamlit Overrides ====== */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
    transition: all 0.2s !important;
}

/* Make preference form (radio) text visible (black) */
div[data-testid="stRadio"] label,
div[data-testid="stRadio"] p,
div[data-testid="stRadio"] span,
div[data-testid="stRadio"] div[role="radiogroup"] * {
    color: #000000 !important;
}

.stButton > button[kind="primary"] {
    background: var(--primary) !important;
    color: var(--text-dark) !important;
    border: none !important;
}

.stButton > button[kind="primary"]:hover {
    background: var(--primary-dark) !important;
    transform: translateY(-1px) !important;
}

.stTextInput > div > div > input {
    font-family: 'Inter', sans-serif !important;
    border-radius: 12px !important;
    border: 1.5px solid var(--border) !important;
    padding: 12px 16px !important;
}

.stTextInput > div > div > input:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px var(--primary-glow) !important;
}

div[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
}

/* ====== Responsive ====== */
@media (max-width: 768px) {
    .hero-title { font-size: 32px; }
    .navbar { padding: 12px 16px; }
}
</style>
"""
