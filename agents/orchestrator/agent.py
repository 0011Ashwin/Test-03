import os
import json
from typing import AsyncGenerator
from google.adk.agents import BaseAgent, LoopAgent, SequentialAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext

from a2a_utils import create_authenticated_client

# --- Callbacks ---
def create_save_output_callback(key: str):
    """Creates a callback to save the agent's final response to session state."""
    def callback(callback_context: CallbackContext, **kwargs) -> None:
        ctx = callback_context
        for event in reversed(ctx.session.events):
            if event.author == ctx.agent_name and event.content and event.content.parts:
                text = event.content.parts[0].text
                if text:
                    if key == "policy_auditor_feedback" and text.strip().startswith("{"):
                        try:
                            ctx.state[key] = json.loads(text)
                        except json.JSONDecodeError:
                            ctx.state[key] = text
                    else:
                        ctx.state[key] = text
                    print(f"[{ctx.agent_name}] Saved output to state['{key}']")
                    return
    return callback

# --- Remote Agents ---

# Connect to Logistics (Localhost port 8001 fallback)
logistics_url = os.environ.get("LOGISTICS_AGENT_CARD_URL", "http://localhost:8001/a2a/agent/.well-known/agent-card.json")
logistics = RemoteA2aAgent(
    name="logistics",
    agent_card=logistics_url,
    description="Understands travel intent, marks calendars, checks flights.",
    after_agent_callback=create_save_output_callback("logistics_output"),
    httpx_client=create_authenticated_client(logistics_url)
)

# Connect to Travel Researcher (Localhost port 8002 fallback)
travel_researcher_url = os.environ.get("TRAVEL_RESEARCHER_AGENT_CARD_URL", "http://localhost:8002/a2a/agent/.well-known/agent-card.json")
travel_researcher = RemoteA2aAgent(
    name="travel_researcher",
    agent_card=travel_researcher_url,
    description="Finds accommodations and travel logistics based on location.",
    after_agent_callback=create_save_output_callback("travel_research_findings"),
    httpx_client=create_authenticated_client(travel_researcher_url)
)

# Connect to Policy Auditor (Localhost port 8003 fallback)
policy_auditor_url = os.environ.get("POLICY_AUDITOR_AGENT_CARD_URL", "http://localhost:8003/a2a/agent/.well-known/agent-card.json")
policy_auditor = RemoteA2aAgent(
    name="policy_auditor",
    agent_card=policy_auditor_url,
    description="Evaluates travel plans against company/personal budgets.",
    after_agent_callback=create_save_output_callback("policy_auditor_feedback"),
    httpx_client=create_authenticated_client(policy_auditor_url)
)

# Accountant (Localhost port 8004 fallback)
accountant_url = os.environ.get("ACCOUNTANT_AGENT_CARD_URL", "http://localhost:8004/a2a/agent/.well-known/agent-card.json")
accountant = RemoteA2aAgent(
    name="accountant",
    agent_card=accountant_url,
    description="Extracts costs and logs them to the SQL database.",
    httpx_client=create_authenticated_client(accountant_url)
)

# --- Escalation Checker ---

class ApprovalChecker(BaseAgent):
    """Checks the auditor's feedback and breaks the loop if it passed."""
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        feedback = ctx.session.state.get("policy_auditor_feedback")
        print(f"[ApprovalChecker] Feedback: {feedback}")

        is_pass = False
        if isinstance(feedback, dict) and feedback.get("status") == "pass":
            is_pass = True
        elif isinstance(feedback, str) and '"status": "pass"' in feedback:
            is_pass = True

        if is_pass:
            yield Event(author=self.name, actions=EventActions(escalate=True)) # Break Loop
        else:
            yield Event(author=self.name) # Continue Loop

approval_checker = ApprovalChecker(name="approval_checker")

# --- Orchestration ---

# The Hotel Search Loop
hotel_search_loop = LoopAgent(
    name="hotel_search_loop",
    description="Iteratively searches for hotels until budget standards are met.",
    sub_agents=[travel_researcher, policy_auditor, approval_checker],
    max_iterations=3,
)

# The Final Concierge Pipeline
root_agent = SequentialAgent(
    name="concierge_pipeline",
    description="A pipeline that logs flights, finds hotels, and records expenses.",
    sub_agents=[logistics, hotel_search_loop, accountant],
)
