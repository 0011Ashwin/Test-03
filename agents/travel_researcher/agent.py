import os
import json
import httpx
from google.adk.agents import Agent
from google.adk.tools.google_search_tool import google_search

MODEL = "gemini-2.5-pro"


def google_maps_search(query: str, location_bias: str = "") -> str:
    """
    Searches Google Places API (Maps) for hotels, restaurants, or POIs.
    Returns real names, addresses, ratings, and price levels.

    Uses the Google Places API (New) Text Search endpoint.
    Requires GOOGLE_MAPS_API_KEY env var.

    Args:
        query:         e.g. "4-star hotels in Bandra Mumbai under $150 per night"
        location_bias: Optional city or lat,lng to bias results  e.g. "Mumbai, India"
    Returns:
        JSON string with list of places including name, address, rating, price_level.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")

    if not api_key:
        return json.dumps({
            "status": "no_api_key",
            "message": "GOOGLE_MAPS_API_KEY not set. Set this env var to enable real hotel lookup.",
            "fallback": "Use google_search tool instead to find hotels."
        })

    try:
        payload = {
            "textQuery": query,
            "languageCode": "en",
            "maxResultCount": 5,
        }
        if location_bias:
            # Use a simple circle bias around the city
            payload["locationBias"] = {
                "circle": {
                    "center": {"latitude": 0, "longitude": 0},  # LLM should fill via search
                    "radius": 30000.0
                }
            }

        resp = httpx.post(
            "https://places.googleapis.com/v1/places:searchText",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.priceLevel,places.userRatingCount,places.websiteUri,places.googleMapsUri"
            },
            json=payload,
            timeout=15.0
        )
        if resp.status_code == 200:
            data = resp.json()
            places = data.get("places", [])
            results = []
            for p in places:
                results.append({
                    "name":         p.get("displayName", {}).get("text", "Unknown"),
                    "address":      p.get("formattedAddress", "N/A"),
                    "rating":       p.get("rating", "N/A"),
                    "reviews":      p.get("userRatingCount", 0),
                    "price_level":  p.get("priceLevel", "N/A"),
                    "maps_link":    p.get("googleMapsUri", ""),
                    "website":      p.get("websiteUri", ""),
                })
            return json.dumps({"status": "ok", "results": results, "count": len(results)})
        return json.dumps({"status": "error", "code": resp.status_code, "detail": resp.text[:300]})
    except Exception as e:
        return json.dumps({"status": "error", "detail": str(e)})


# ── Agent definition ────────────────────────────────────────────────────────
travel_researcher = Agent(
    name="travel_researcher",
    model=MODEL,
    description="Finds real hotel options using Google Search and Google Maps Places API.",
    instruction="""
    You are a luxury travel researcher. You find REAL hotels with REAL prices.
    Do NOT invent or guess hotel names, prices, or addresses. Use your tools.

    Given the destination city, travel dates, and budget per night:

    Step 1 — Search Google Maps for hotels:
    Use `google_maps_search` with a query like:
      "hotels in [City] [State/Country] under $[budget]/night"
    This returns real hotel names, addresses, and ratings from Google Places.

    Step 2 — Get current pricing from Google Search:
    For each top hotel from Step 1, use `google_search` to find:
      "[Hotel Name] [City] price per night [travel month]"
    This gives real current nightly rates.

    Step 3 — Compile top 3 recommendations:
    Return a structured list like:
    [
      {
        "rank": 1,
        "name": "Actual Hotel Name",
        "address": "Full real address",
        "area": "Neighbourhood / area",
        "nightly_rate": "$XX",
        "total_cost": "$XX for N nights",
        "rating": X.X,
        "within_budget": true/false,
        "maps_link": "https://...",
        "why_recommended": "Brief reason"
      },
      ...
    ]

    Always prefer hotels that are within the user's stated budget.
    If no hotel fits the budget, flag the cheapest option and note the difference.
    """,
    tools=[google_search, google_maps_search],
)

root_agent = travel_researcher
