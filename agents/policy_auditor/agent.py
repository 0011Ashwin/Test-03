from pydantic import BaseModel, Field
from typing import Literal
from google.adk.agents import Agent

MODEL = "gemini-2.5-pro"

# 1. Define the Schema
class AuditorFeedback(BaseModel):
    """Structured feedback from the Auditor agent."""
    status: Literal["pass", "fail"] = Field(
        description="Whether the hotel fits the budget ('pass') or is too expensive ('fail')."
    )
    feedback: str = Field(
        description="Detailed feedback. e.g., 'Hotel is $300/night, max budget is $200. Find cheaper.' If 'pass', confirm approval."
    )

# 2. Define the Agent
policy_auditor = Agent(
    name="policy_auditor",
    model=MODEL,
    description="Evaluates travel plans against company/personal budgets.",
    instruction="""
    You are a strict financial auditor.
    Evaluate the 'hotel_recommendations' against a maximum budget of $200 per night.
    If the hotels exceed this, return status='fail'.
    If at least one hotel is under budget, return status='pass'.
    """,
    output_schema=AuditorFeedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

root_agent = policy_auditor