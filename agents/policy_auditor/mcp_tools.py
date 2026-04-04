import os
import httpx
from typing import Optional

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:9000")

def mcp_invoke(tool_name: str, args: dict) -> str:
    """Invokes a hypothetical real MCP server endpoint."""
    try:
        # We attempt to call the real MCP server
        response = httpx.post(f"{MCP_SERVER_URL}/v1/tools/{tool_name}", json=args, timeout=5.0)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        # If no MCP server is actually running, we fallback to a smart mock response
        pass

    # Mocks based on tool name
    if tool_name == "gmail.read":
        return f"Found 1 email: Flight confirmed on next Monday, flying to Paris. 2 night stay."
    elif tool_name == "calendar.create":
        return f"Successfully created calendar event for Paris trip."
    elif tool_name == "maps.search":
        return f"Found nearby hotels: 1) Le Meurice ($250/night), 2) Hampton Inn Paris ($95/night, 4-star)."
    
    return f"Executed {tool_name} successfully."

def gmail_read(query: str) -> str:
    """Reads recent emails matching the query."""
    return mcp_invoke("gmail.read", {"query": query})

def calendar_create(title: str, start_time: str, end_time: str, location: str) -> str:
    """Creates a calendar event."""
    return mcp_invoke("calendar.create", {
        "title": title,
        "start_time": start_time,
        "end_time": end_time,
        "location": location
    })

def maps_search(query: str, location: str) -> str:
    """Searches Google Maps for places matching the query near the location."""
    return mcp_invoke("maps.search", {"query": query, "location": location})

