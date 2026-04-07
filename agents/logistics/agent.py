import os
import json
import httpx
from google.adk.agents import Agent
from google.adk.tools.google_search_tool import google_search

MODEL = "gemini-2.5-pro"

def google_calendar_create(title: str, start_datetime: str, end_datetime: str,
                             location: str, description: str = "",
                             user_oauth_token: str = "") -> str:
    """
    Creates a Real Google Calendar event via the Calendar REST API.

    If user_oauth_token is provided, it uses the user's personal calendar via OAuth.
    Otherwise, it falls back to GOOGLE_CALENDAR_TOKEN or Workload Identity.
    and `GOOGLE_CALENDAR_ID` (defaults to 'primary') set as env vars.
    On Cloud Run this token is obtained from the metadata server or Workload Identity.

    Args:
        title:          Event title  (e.g. "Trip to Mumbai — Hotel Check-in")
        start_datetime: ISO-8601 datetime  e.g. "2025-04-15T14:00:00+05:30"
        end_datetime:   ISO-8601 datetime  e.g. "2025-04-17T12:00:00+05:30"
        location:       Physical location string (hotel address or city)
        description:    Optional extra notes added to the calendar event
    Returns:
        JSON string with the created event id, htmlLink, or an error message.
    """
    # Prioritize user OAuth token if passed by the Orchestrator
    token       = user_oauth_token or os.environ.get("GOOGLE_CALENDAR_TOKEN", "")
    calendar_id = "primary"

    if not token:
        # Attempt to fetch token from GCE metadata (works on Cloud Run automatically)
        try:
            meta = httpx.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                headers={"Metadata-Flavor": "Google"},
                timeout=2.0
            )
            if meta.status_code == 200:
                token = meta.json().get("access_token", "")
        except Exception:
            pass

    if not token:
        # Graceful degradation: return what WOULD be created so the orchestrator
        # can still surface meaningful output to the user.
        return json.dumps({
            "status": "pending_auth",
            "message": "Google Calendar OAuth not configured. Event details ready to add.",
            "event": {
                "title":        title,
                "start":        start_datetime,
                "end":          end_datetime,
                "location":     location,
                "description":  description,
                "instructions": "To enable: set GOOGLE_CALENDAR_TOKEN env var or deploy on Cloud Run with Workload Identity."
            }
        })

    body = {
        "summary":     title,
        "location":    location,
        "description": description,
        "start": {"dateTime": start_datetime, "timeZone": "Asia/Kolkata"},
        "end":   {"dateTime": end_datetime,   "timeZone": "Asia/Kolkata"},
    }
    try:
        resp = httpx.post(
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
            timeout=15.0
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            return json.dumps({
                "status":    "created",
                "event_id":  data.get("id"),
                "htmlLink":  data.get("htmlLink"),
                "title":     data.get("summary"),
                "start":     data.get("start", {}).get("dateTime"),
                "end":       data.get("end",   {}).get("dateTime"),
                "location":  data.get("location"),
            })
        return json.dumps({"status": "error", "code": resp.status_code, "detail": resp.text[:300]})
    except Exception as e:
        return json.dumps({"status": "error", "detail": str(e)})


# ── Agent definition ────────────────────────────────────────────────────────
logistics = Agent(
    name="logistics",
    model=MODEL,
    description="Parses travel requests and manages Google Calendar events.",
    instruction="""
    You are an expert travel logistics coordinator. Do NOT read or send any emails.

    Given the user's travel request text:
    1. Use `google_search` to look up:
       - Approximate flight cost from the user's origin to destination on the stated dates
         (search: "flight price [origin] to [destination] [date]")
       - Current entry/visa requirements if international travel
    2. Extract clearly from the user's request:
       - Destination city and country
       - Travel dates (departure and return)
       - Number of nights
       - Any budget constraints mentioned
    3. Use `google_calendar_create` to create two calendar events:
       - "✈️ Departure – [Destination]" for the departure day
       - "🏨 Stay – [Destination] ([N] nights)" for the full stay period
       **CRITICAL: If the prompt includes a "[SYSTEM] Use this Google Calendar OAuth Token" message, you MUST pass that token precisely into the `user_oauth_token` argument.**
    4. Return a structured JSON-style summary:
       {
         "destination": "...",
         "departure_date": "...",
         "return_date": "...",
         "nights": N,
         "budget_per_night": "₹...",
         "approx_flight_cost": "₹...",
         "calendar_events": ["...", "..."],
         "search_notes": "..."
       }
    """,
    tools=[google_search, google_calendar_create],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

root_agent = logistics
