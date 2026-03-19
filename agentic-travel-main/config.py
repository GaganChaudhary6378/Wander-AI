"""
WanderAI Configuration
Reads environment variables and provides app-wide settings.
Automatically enables DEMO_MODE when API keys are missing.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # LLM Settings
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # External API Keys
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
    GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
    OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    EXA_API_KEY = os.getenv("EXA_API_KEY", "")
    RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
    RAILRADAR_API_KEY = os.getenv("RAILRADAR_API_KEY", "")

    # Demo mode: auto-enable only if no LLM key is provided
    _demo_env = os.getenv("DEMO_MODE", "auto").lower()

    @classmethod
    def has_llm_key(cls):
        return bool(cls.OPENAI_API_KEY) or bool(cls.ANTHROPIC_API_KEY)

    @classmethod
    def is_demo(cls):
        if cls._demo_env == "true":
            return True
        if cls._demo_env == "false":
            return False
        # auto: demo only if no LLM key
        return not cls.has_llm_key()


config = Config()
