from google.adk.agents import Agent
from mcp_tools import gmail_read, calendar_create, maps_search
from google.adk.tools.google_search_tool import google_search

MODEL = "gemini-2.5-pro"

# Define the Logistics Agent
logistics = Agent(
    name="logistics",
    model=MODEL,
    description="Manages emails and calendars for travel.",
    instruction="""
    You are an expert travel logistics coordinator. 
    Read the user's latest flight confirmation using the `gmail_read` tool.
    Extract the flight times, dates, and destination city.
    Then, use the `calendar_create` tool to block out these times on the user's calendar.
    Pass the destination city and dates forward for hotel research.
    If the user asks for a flight or train price check, use `google_search` to find current options.
    """,
    tools=[gmail_read, calendar_create, google_search],
)

root_agent = logistics
