from pydantic import BaseModel, Field
from typing import Literal, Optional
from google.adk.agents import Agent

MODEL = "gemini-2.5-pro"


class AuditorFeedback(BaseModel):
    """Structured audit result from the Policy Auditor agent."""
    status: Literal["pass", "fail"] = Field(
        description="'pass' if at least one hotel is within the user's stated budget, else 'fail'."
    )
    budget_per_night: str = Field(
        description="The budget limit extracted from the user's request, e.g. '₹1500'"
    )
    approved_hotel: Optional[str] = Field(
        default=None,
        description="Name of the approved hotel that is within budget. Null if status=fail."
    )
    approved_hotel_address: Optional[str] = Field(
        default=None,
        description="Full address of the approved hotel."
    )
    approved_nightly_rate: Optional[str] = Field(
        default=None,
        description="Nightly rate of the approved hotel, e.g. '₹1390'"
    )
    maps_link: Optional[str] = Field(
        default=None,
        description="Google Maps link to the approved hotel if available."
    )
    feedback: str = Field(
        description="Detailed explanation: which hotel was approved and why, or why all failed and what the cheapest option costs."
    )


policy_auditor = Agent(
    name="policy_auditor",
    model=MODEL,
    description="Evaluates hotel options against the user's stated budget from their travel request.",
    instruction="""
    You are a strict financial auditor for travel expenses.

    You receive:
    - A list of hotel recommendations from the Travel Researcher
    - The user's original travel request which contains their budget per night

    Your job:
    1. Extract the maximum budget per night from the user's request
       (e.g. if they said "budget ₹1500/night", your limit is ₹1500)
       If no budget is stated, use a default of ₹2000/night.
    2. Evaluate each hotel against this budget.
    3. Return a structured AuditorFeedback:
       - status='pass': at least one hotel is AT or BELOW budget
         → set approved_hotel, approved_hotel_address, approved_nightly_rate, maps_link
       - status='fail': ALL hotels exceed budget
         → describe the cheapest option found and by how much it exceeds budget

    Be precise. Real hotel names and real prices from the researcher.
    Do NOT make up hotels or prices.
    """,
    output_schema=AuditorFeedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

root_agent = policy_auditor