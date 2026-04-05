import os
import json
import httpx
from google.adk.agents import Agent

MODEL = "gemini-2.5-pro"


def _get_base_url(card_url_env: str, default: str) -> str:
    """Extracts base service URL from the agent card URL environment variable."""
    card_url = os.environ.get(card_url_env, "")
    if card_url:
        # Strip the a2a path suffix to get the base URL
        # e.g. https://svc.run.app/a2a/agent/.well-known/agent-card.json -> https://svc.run.app
        for suffix in ["/a2a/agent/.well-known/agent-card.json", "/.well-known/agent-card.json"]:
            if card_url.endswith(suffix):
                return card_url[: -len(suffix)]
        return card_url
    return default


LOGISTICS_BASE = _get_base_url("LOGISTICS_AGENT_CARD_URL", "http://localhost:8001")
TRAVEL_RESEARCHER_BASE = _get_base_url("TRAVEL_RESEARCHER_AGENT_CARD_URL", "http://localhost:8002")
POLICY_AUDITOR_BASE = _get_base_url("POLICY_AUDITOR_AGENT_CARD_URL", "http://localhost:8003")
ACCOUNTANT_BASE = _get_base_url("ACCOUNTANT_AGENT_CARD_URL", "http://localhost:8004")


def _call_agent(base_url: str, message: str, session_id: str = "default") -> str:
    """Generic helper to call an ADK agent via its REST API."""
    try:
        # Step 1: Create or reuse session
        session_url = f"{base_url}/apps/agent/users/orchestrator/sessions/{session_id}"
        httpx.post(session_url, json={}, timeout=10.0)

        # Step 2: Send message and get response
        run_url = f"{base_url}/apps/agent/users/orchestrator/sessions/{session_id}/run"
        resp = httpx.post(
            run_url,
            json={
                "appName": "agent",
                "userId": "orchestrator",
                "sessionId": session_id,
                "newMessage": {
                    "role": "user",
                    "parts": [{"text": message}],
                },
                "streaming": False,
            },
            timeout=120.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Extract the last model response text
            events = data if isinstance(data, list) else data.get("events", [])
            for event in reversed(events):
                content = event.get("content", {})
                parts = content.get("parts", []) if content else []
                for part in parts:
                    if part.get("text"):
                        return part["text"]
        return f"Agent responded with status {resp.status_code}: {resp.text[:500]}"
    except Exception as e:
        return f"Error calling agent at {base_url}: {str(e)}"


def process_travel_logistics(travel_request: str) -> str:
    """
    Call the Logistics agent to parse a travel request email,
    extract flight details, and block calendar slots.

    Args:
        travel_request: The user's travel request or email content to process.
    Returns:
        Logistics summary including flight details and calendar status.
    """
    return _call_agent(LOGISTICS_BASE, travel_request, "logistics-session")


def research_hotels(destination_and_dates: str) -> str:
    """
    Call the Travel Researcher agent to find hotel options near the destination.

    Args:
        destination_and_dates: Description of the destination city and travel dates.
    Returns:
        A list of hotel recommendations with prices.
    """
    return _call_agent(TRAVEL_RESEARCHER_BASE, destination_and_dates, "researcher-session")


def audit_travel_policy(hotel_recommendations: str) -> str:
    """
    Call the Policy Auditor agent to check if hotel options are within budget.

    Args:
        hotel_recommendations: The hotel options to evaluate against budget policy.
    Returns:
        Audit result with status (pass/fail) and feedback.
    """
    return _call_agent(POLICY_AUDITOR_BASE, hotel_recommendations, "auditor-session")


def log_expense(expense_summary: str) -> str:
    """
    Call the Accountant agent to log the approved travel expense to the database.

    Args:
        expense_summary: Summary of approved flight and hotel costs to log.
    Returns:
        Confirmation that expenses were logged to the database.
    """
    return _call_agent(ACCOUNTANT_BASE, expense_summary, "accountant-session")


root_agent = Agent(
    name="concierge_pipeline",
    model=MODEL,
    description="A travel concierge that coordinates logistics, hotel research, budget auditing, and expense logging.",
    instruction="""
    You are a proactive AI travel concierge. You NEVER reference email.
    You NEVER tell the user to "check any app" or "check their email".
    ALL information is shown directly in your response.
    Do NOT invent or guess any data — use only what the agents return.

    When given a travel request, run this pipeline in order:

    1. Call `process_travel_logistics` with the FULL original user request.
       → This returns destination, dates, nights, budget, approx flight cost,
         and Google Calendar event status.

    2. Call `research_hotels` with a message that includes:
       - destination city from step 1
       - number of nights from step 1
       - budget_per_night from step 1
       Format: "Find hotels in [destination] for [N] nights, budget $[X]/night, dates [start] to [end]"

    3. Call `audit_travel_policy` with a message that includes:
       - The hotel list from step 2
       - The user's ORIGINAL request (so it can extract the budget)
       Format: "User budget: $[X]/night. Hotels: [list from step 2]"
       If status='fail', call `research_hotels` again asking for cheaper options.
       Repeat up to 2 more times.

    4. Once status='pass', call `log_expense` with:
       - Approved hotel name
       - Nightly rate × nights (total hotel cost)
       - Destination
       - Approved hotel address
       - Number of nights
       - Departure date
       → This returns a JSON record with expense_id, status, and full details.

    5. Present the FINAL RESULT using EXACTLY this Markdown structure.
       Fill every [placeholder] with REAL data from the agents above.
       Do NOT use placeholders in the output — replace them all.

    ---

    ## ✈️ Trip Summary

    **Destination:** [City, Country]
    **Travel Dates:** [Departure Date] → [Return Date]
    **Duration:** [N] nights

    ---

    ### 🛫 Travel Details
    - **Approx. Flight Cost:** [from logistics search]
    - **Departure:** [date and time if found]
    - **Calendar Events:** [list the event titles that were created, or "Ready to add — OAuth needed"]

    ---

    ### 🏨 Approved Hotel
    | Detail | Info |
    |--------|------|
    | **Hotel Name** | [approved_hotel from auditor] |
    | **Address** | [approved_hotel_address] |
    | **Nightly Rate** | [approved_nightly_rate] |
    | **Total Stay** | [rate × nights] for [N] nights |
    | **Budget Limit** | [budget_per_night from auditor] |
    | **Status** | ✅ Within budget |
    | **Google Maps** | [maps_link as a clickable link, or "N/A"] |

    ---

    ### 💰 Cost Breakdown
    | Item | Cost |
    |------|------|
    | Flight (approx.) | [approx_flight_cost] |
    | Hotel ([N] nights × [rate/night]) | [total hotel cost] |
    | **Estimated Total** | **[sum]** |

    ---

    ### 📋 Expense Logged to AlloyDB
    | Field | Value |
    |-------|-------|
    | **Expense ID** | [expense_id from accountant] |
    | **Hotel** | [merchant from accountant] |
    | **Total Amount** | $[amount] |
    | **Date** | [date] |
    | **Status** | [status — "logged_to_alloydb" or "logged_locally"] |

    ---

    > 💡 **Local Tip:** [One practical tip about transport, weather, or local customs for the destination]
    """,
    tools=[process_travel_logistics, research_hotels, audit_travel_policy, log_expense],
)

