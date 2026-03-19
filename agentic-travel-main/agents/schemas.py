"""
Pydantic schemas for trip request validation.
Used in the Plan → Validate → Research → Optimize → Execute workflow.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator


class TripRequest(BaseModel):
    """Validated trip request. All fields required for research except return date (required only when trip_type is return)."""

    origin: str
    destination: str
    date_from: date
    date_to: date | None = None
    trip_type: Literal["one_way", "return"] = "one_way"
    duration_days: int = 1
    budget: float = 10000.0
    currency: str = "INR"
    group_size: int = 1
    travel_style: str = "Not specified"
    interests: list[str] = []

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip() or "Unknown"
        return v

    @field_validator("duration_days", "group_size")
    @classmethod
    def positive_int(cls, v):
        if v is None:
            return 1
        n = int(v)
        return max(1, n)

    @field_validator("budget", mode="before")
    @classmethod
    def positive_budget(cls, v):
        if v is None:
            return 10000.0
        x = float(v)
        return max(0.0, x)

    @field_validator("date_from", mode="before")
    @classmethod
    def parse_date_from(cls, v):
        if v is None:
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, datetime):
            return v.date()
        s = str(v).strip()
        if not s or s.lower() in ("next weekend", "flexible", "tbd", ""):
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s[:10], fmt).date()
            except ValueError:
                continue
        return None

    @field_validator("date_to", mode="before")
    @classmethod
    def parse_date_to(cls, v):
        if v is None:
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, datetime):
            return v.date()
        s = str(v).strip()
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s[:10], fmt).date()
            except ValueError:
                continue
        return None

    @model_validator(mode="after")
    def date_to_required_for_return(self):
        if self.trip_type == "return" and self.date_to is None:
            raise ValueError("date_to is required when trip_type is return")
        return self

    @model_validator(mode="after")
    def date_to_after_date_from(self):
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValueError("date_to must be on or after date_from")
        return self


def trip_request_missing_fields(profile: dict) -> list[str]:
    """Return list of field names that are missing or invalid for TripRequest."""
    missing = []
    if not (profile.get("origin") or "").strip():
        missing.append("origin")
    if not (profile.get("destination") or "").strip():
        missing.append("destination")
    dates = profile.get("date_from") or profile.get("dates")
    if not dates or str(dates).strip().lower() in ("next weekend", "flexible", "tbd", ""):
        missing.append("date_from")
    if profile.get("trip_type") == "return":
        if not profile.get("date_to"):
            missing.append("date_to")
    if profile.get("trip_type") not in ("one_way", "return"):
        missing.append("trip_type")
    return missing


def profile_to_trip_request(profile: dict) -> TripRequest | None:
    """Build TripRequest from travel_profile dict. Returns None if validation fails."""
    from datetime import timedelta

    date_from = profile.get("date_from") or profile.get("dates")
    if not date_from or str(date_from).strip().lower() in ("next weekend", "flexible", "tbd", ""):
        date_from = (date.today() + timedelta(days=7)).isoformat()
    date_to = profile.get("date_to")
    if profile.get("trip_type") == "return" and not date_to and isinstance(date_from, str):
        try:
            from datetime import datetime
            dt = datetime.strptime(date_from[:10], "%Y-%m-%d").date()
            date_to = (dt + timedelta(days=int(profile.get("duration_days", 3)))).isoformat()
        except Exception:
            date_to = None

    try:
        return TripRequest(
            origin=profile.get("origin", "Delhi"),
            destination=profile.get("destination", "Rishikesh"),
            date_from=date_from,
            date_to=date_to,
            trip_type=profile.get("trip_type") or "one_way",
            duration_days=int(profile.get("duration_days") or 3),
            budget=float(profile.get("budget") or 10000),
            currency=profile.get("currency", "INR"),
            group_size=int(profile.get("group_size") or 1),
            travel_style=profile.get("travel_style") or "Not specified",
            interests=profile.get("interests") or [],
        )
    except Exception:
        return None
