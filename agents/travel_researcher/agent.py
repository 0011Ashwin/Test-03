from google.adk.agents import Agent
from google.adk.tools.google_search_tool import google_search
from mcp_tools import maps_search

MODEL = "gemini-2.5-pro"

# Define the Travel Researcher Agent
travel_researcher = Agent(
    name="travel_researcher",
    model=MODEL,
    description="Finds accommodations and travel logistics based on location.",
    instruction="""
    You are a luxury travel researcher. Take the destination and dates provided by logistics.
    Use `maps_search` to find 4-star hotels near the city center or meeting location.
    Use `google_search` to find the current nightly rates for these hotels.
    Summarize your top 2 hotel recommendations including their prices.
    If you receive feedback that the hotels are too expensive, search again for cheaper options.
    """,
    tools=[maps_search, google_search],
)

root_agent = travel_researcher
