# WanderAI Documentation

This folder contains documentation for the **WanderAI** (agentic-travel) project: architecture, data flow, and how external APIs are used.

## Contents

| Document | Description |
|----------|-------------|
| **[Architecture](architecture.md)** | High-level architecture: Streamlit app entry, LangGraph state machine, agents (parse intent → validate → gather preferences → research → optimize → plan route → booking → replan), state schema, and key files. |
| **[External APIs](external-apis.md)** | Detailed reference for every external API: Google (Places, Geocoding, Directions), OpenWeatherMap, RapidAPI (Booking.com hotels/flights, IRCTC trains), SerpAPI (Google Flights), RailRadar, Tavily, Exa, Indian Railway station list, and LLM usage. Includes env vars, endpoints, request/response handling, and fallbacks. |

## Quick links

- **Run the app:** From project root, `streamlit run app.py` (ensure `agentic-travel-main` is the app root or adjust path).
- **Config:** Copy `.env.example` to `.env` and set API keys; see [External APIs](external-apis.md#13-environment-variables-summary) for the full list.
- **Demo mode:** With no LLM key, the app runs in demo mode using mock data from `data/mock_data.py`.
