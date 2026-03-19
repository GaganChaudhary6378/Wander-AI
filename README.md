# ✦ WanderAI — AI Travel Planning & Booking Agent

An intelligent multi-agent travel planner built with **LangGraph**, **LangChain**, and **Streamlit**. WanderAI uses specialized AI agents to research destinations, optimize budgets, create day-by-day itineraries, coordinate bookings, and dynamically re-plan when disruptions occur — all through a premium conversational interface.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31+-red)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green)

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Streamlit Frontend                  │
│  Home │ Chat │ Itinerary │ Day View │ Booking │ Replan│
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│              LangGraph Orchestration Engine           │
│                                                       │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌─────────┐ │
│  │ Intent  │→ │ Research │→ │ Budget │→ │  Route  │ │
│  │ Parser  │  │  Agent   │  │Optimizer│  │ Planner │ │
│  └─────────┘  └──────────┘  └────────┘  └─────────┘ │
│       ↕            ↕             ↕            ↕       │
│  Human-in-the-Loop Checkpoints (approve/reject)      │
│                                                       │
│  ┌──────────┐  ┌───────────┐                         │
│  │ Booking  │  │ Re-Planner│  ← Dynamic disruption   │
│  │Coordinator│  │   Agent   │    handling              │
│  └──────────┘  └───────────┘                         │
└──────────────────────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│              External APIs / Mock Data               │
│  SerpAPI │ Google Places │ OpenWeatherMap │ Maps     │
└──────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
trip_planner/
├── app.py                  # Main Streamlit entry point
├── config.py               # Configuration & API key management
├── requirements.txt        # Python dependencies
├── .env.example            # API key template
│
├── agents/                 # LangGraph agents (backend)
│   ├── __init__.py         # TravelState schema definitions
│   ├── state.py            # State re-exports
│   ├── graph.py            # LangGraph StateGraph + routing
│   ├── intent_parser.py    # Extracts travel preferences from NL
│   ├── researcher.py       # Fetches flights, hotels, activities
│   ├── budget_optimizer.py # Allocates budget across categories
│   ├── route_planner.py    # Creates day-by-day itinerary
│   ├── booking_coordinator.py # Generates booking confirmations
│   └── replanner.py        # Handles disruptions & re-planning
│
├── ui/                     # Streamlit frontend screens
│   ├── __init__.py
│   ├── styles.py           # CSS design system
│   ├── components.py       # Shared UI components
│   ├── home.py             # Screen 1: Welcome page
│   ├── chat.py             # Screen 2: Chat + live sidebar
│   ├── itinerary.py        # Screen 3: Itinerary overview
│   ├── day_view.py         # Screen 4: Detailed day view
│   ├── booking.py          # Screen 6: Booking confirmation
│   └── replan.py           # Screen 7: Re-planning recovery
│
├── data/                   # Data & prompts
│   ├── __init__.py
│   ├── mock_data.py        # Demo data (flights, hotels, etc.)
│   └── prompts.py          # LLM system prompts per agent
│
├── diagram.txt             # Architecture diagram (Mermaid)
├── problem.txt             # Problem statement
└── stitch_generated_screen/ # UI design mockups (reference)
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** installed
- **pip** package manager

### 1. Install Dependencies

```bash
cd /path/to/trip_planner
pip install -r requirements.txt
```

### 2. Configure API Keys (Optional)

Copy the example env file and add your keys:

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```env
OPENAI_API_KEY=sk-...          # For LLM-powered agents
SERPAPI_API_KEY=...             # For live flight/hotel search
GOOGLE_PLACES_API_KEY=...      # For activity/restaurant data
OPENWEATHERMAP_API_KEY=...     # For weather forecasts
```

> **Note:** The app works fully in **Demo Mode** without any API keys! It uses realistic mock data for Rishikesh, Goa, and Tokyo.

### 3. Run the Application

See the **Running the Application** section below for detailed backend + frontend instructions.

---

## ▶️ Running the Application

### Architecture Note

This application has two layers:

| Layer | Technology | What it does |
|-------|-----------|--------------|
| **Backend** | LangGraph + LangChain (Python) | Agent orchestration, state management, API calls |
| **Frontend** | Streamlit (Python) | Chat UI, itinerary views, maps, booking screens |

By default, both layers run **together in a single process** when you launch Streamlit. There is no separate backend server to start — the LangGraph engine is invoked directly from the Streamlit frontend.

---

### Option A: Run Everything Together (Recommended)

This starts both the backend (LangGraph agents) and frontend (Streamlit UI) in one command:

```bash
cd /path/to/trip_planner
streamlit run app.py
```

The app will open in your browser at **http://localhost:8501**.

To customize the port or host:

```bash
streamlit run app.py --server.port 8080 --server.address 0.0.0.0
```

---

### Option B: Test the Backend (LangGraph Engine) Independently

You can run and test the LangGraph agent pipeline **without** the Streamlit frontend. This is useful for debugging, scripting, or integrating with other frontends.

#### Quick Test Script

Create a file `test_backend.py`:

```python
"""Test the LangGraph backend independently."""
from agents.graph import get_graph
from langchain_core.messages import HumanMessage

# Build the graph
graph = get_graph()

# Simulate a user request
initial_state = {
    "messages": [HumanMessage(content=(
        "Plan a 4-day solo backpacking trip to Rishikesh under ₹15,000. "
        "I love adventure sports and spiritual experiences. Traveling from Delhi."
    ))],
    "stage": "idle",
    "reasoning_log": [],
    "confidence": 0.5,
    "needs_human_input": False,
}

config = {"configurable": {"thread_id": "test-001"}}

# Run the agent pipeline
result = graph.invoke(initial_state, config)

# Print results
print("=== TRAVEL PROFILE ===")
print(result.get("travel_profile"))

print("\n=== STAGE ===")
print(result.get("stage"))

print("\n=== AI MESSAGES ===")
for msg in result.get("messages", []):
    if hasattr(msg, "type") and msg.type == "ai":
        print(msg.content[:200], "...")

print("\n=== REASONING LOG ===")
for log in result.get("reasoning_log", []):
    print(f"  {log}")
```

Run it with:

```bash
cd /path/to/trip_planner
python test_backend.py
```

#### Continue the Pipeline (Simulate Approval)

After the first run pauses at a checkpoint, resume by changing the `stage`:

```python
# After intent confirmation, advance to research:
result2 = graph.invoke({
    "messages": [HumanMessage(content="Looks good, go ahead!")],
    "stage": "confirming_intent",
    "travel_profile": result["travel_profile"],
    "reasoning_log": result.get("reasoning_log", []),
    "confidence": 0.9,
    "needs_human_input": False,
}, config)

print(result2.get("research_results"))
print(result2.get("budget_breakdown"))
print(result2.get("itinerary"))
```

#### Test Individual Agents

You can also test agents in isolation:

```python
from agents.intent_parser import parse_intent
from agents.researcher import research
from agents.budget_optimizer import optimize_budget
from agents.route_planner import plan_route
from agents.booking_coordinator import coordinate_booking
from agents.replanner import replan

# Test intent parsing
from langchain_core.messages import HumanMessage
state = {
    "messages": [HumanMessage(content="3 day trip to Goa under 20000 for couple from Mumbai")],
    "reasoning_log": [],
}
result = parse_intent(state)
print(result["travel_profile"])
```

---

### Option C: Run Frontend Only (Hot Reload)

During UI development you can work on just the frontend screens. Streamlit supports **hot reload** — save any `.py` file and the app refreshes automatically:

```bash
streamlit run app.py
```

Edit files in `ui/` (e.g., `ui/home.py`, `ui/chat.py`) and the browser updates live.

---

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEMO_MODE` | No | `true` | Use mock data (no API keys needed) |
| `LLM_PROVIDER` | No | `openai` | `openai` or `anthropic` |
| `LLM_MODEL` | No | `gpt-4o-mini` | LLM model name |
| `OPENAI_API_KEY` | For live mode | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | For live mode | — | Anthropic API key |
| `SERPAPI_API_KEY` | For live flights/hotels | — | SerpAPI key |
| `GOOGLE_PLACES_API_KEY` | For live activities | — | Google Places key |
| `OPENWEATHERMAP_API_KEY` | For live weather | — | OpenWeatherMap key |
| `RAPIDAPI_KEY` | Flights (Booking.com), trains (IRCTC) | — | RapidAPI key |
| `RAILRADAR_API_KEY` | Trains (optional; avoids IRCTC rate limits) | — | RailRadar API key ([railradar.in](https://railradar.in/docs)) |

---

## 🖥️ Screens & User Flow

| # | Screen | Description |
|---|--------|-------------|
| 1 | **Home** | Welcome page with prompt input and example trip cards |
| 2 | **Chat** | Conversational AI with live itinerary sidebar + map |
| 3 | **Itinerary** | Day cards overview, interactive map, budget summary |
| 4 | **Day View** | Detailed timeline, smart alternatives, route map |
| 5 | **Approval** | Human-in-the-loop confirmation (budget, itinerary) |
| 6 | **Booking** | Flight + hotel confirmation cards, remaining budget |
| 7 | **Re-plan** | Disruption alert, revised schedule with status badges |

### Typical Flow

```
Home → Enter prompt → Chat (AI plans) → Approve intent
→ Research results → Approve budget → Itinerary review
→ Approve itinerary → Booking confirmation → Done!
```

For re-planning, click **"Simulate Delay"** on the Booking screen.

---

## 🤖 Agent Pipeline (Backend)

The LangGraph engine runs 6 specialized agents in sequence:

| Agent | Role | Key Logic |
|-------|------|-----------|
| **Intent Parser** | Extract travel preferences | Regex + keyword matching (demo) / LLM (live) |
| **Researcher** | Find flights, hotels, activities | SerpAPI + Google Places (or mock data) |
| **Budget Optimizer** | Allocate budget by category | Style-based % allocation + validation |
| **Route Planner** | Create day-by-day itinerary | Activity distribution + weather awareness |
| **Booking Coordinator** | Generate booking details | Reference codes, pricing, seat assignment |
| **Re-Planner** | Handle disruptions | Time-shifting, activity removal/deferral |

Human-in-the-loop checkpoints pause the pipeline at:
- ✅ Intent confirmation
- ✅ Budget approval
- ✅ Itinerary review
- ✅ Booking confirmation

---

## 🎨 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Orchestration** | LangGraph (StateGraph + MemorySaver) |
| **LLM Framework** | LangChain |
| **LLM** | GPT-4o-mini (configurable) / Demo mode |
| **Frontend** | Streamlit |
| **Maps** | Folium + streamlit-folium |
| **External APIs** | SerpAPI, Google Places, OpenWeatherMap |
| **Styling** | Custom CSS (Inter font, #4dd1c4 primary) |

---

## 🧪 Sample Prompts

Try these in the app:

1. **Budget Backpacking:**
   > "Plan a 4-day solo backpacking trip to Rishikesh under ₹15,000. I love adventure sports and spiritual experiences. Traveling from Delhi next weekend."

2. **Family Vacation:**
   > "Plan a 5-day family trip to Goa for 4 people under ₹80,000. We have 2 kids. We love beaches, water sports, and local food. Traveling from Mumbai."

3. **Couple's Adventure:**
   > "Plan a 7-day Tokyo & Kyoto adventure for 2 people with a budget of $5,000. We love Japanese culture, food, and anime. Flying from New York."

---

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DEMO_MODE` | `true` | Use mock data instead of live APIs |
| `LLM_PROVIDER` | `openai` | LLM provider (`openai` or `anthropic`) |
| `LLM_MODEL` | `gpt-4o-mini` | Model to use for agent reasoning |

---

## 📦 Deliverables

- ✅ Working demo application (Streamlit UI)
- ✅ 3 sample travel plans (solo, family, couple)
- ✅ Architecture diagram (`diagram.txt`)
- ✅ 7 specialized agents with reasoning transparency
- ✅ Human-in-the-loop checkpoints
- ✅ Interactive maps with Folium
- ✅ Budget optimization & breakdown
- ✅ Dynamic re-planning for disruptions
- ✅ Edge case handling (budget too low, vague input, etc.)

---

## 📄 License

Built for **Wander AI #2: Agentic Workflow **.
