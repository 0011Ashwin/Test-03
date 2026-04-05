"""
Travel Concierge Frontend Server
GenAI Academy · ACAP Edition · H2skill
"""
import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from google.genai import types as genai_types
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────

agent_server_url = os.getenv("AGENT_SERVER_URL", "").rstrip("/")
if not agent_server_url:
    raise ValueError("AGENT_SERVER_URL environment variable must be set")

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="Travel Concierge — GenAI Academy ACAP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared async HTTP client (no auth needed — services are allow-unauthenticated)
_client: Optional[httpx.AsyncClient] = None

async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=180.0)
    return _client

# ── ADK helpers ──────────────────────────────────────────────────────────────

agent_name_cache: Optional[str] = None

async def discover_agent_name() -> str:
    global agent_name_cache
    if agent_name_cache:
        return agent_name_cache
    client = await get_client()
    try:
        resp = await client.get(f"{agent_server_url}/list-apps")
        resp.raise_for_status()
        names = resp.json()
        agent_name_cache = names[0] if names else "agent"
    except Exception:
        agent_name_cache = "agent"
    return agent_name_cache


async def create_session(agent: str, user_id: str) -> Dict[str, Any]:
    client = await get_client()
    resp = await client.post(
        f"{agent_server_url}/apps/{agent}/users/{user_id}/sessions",
        json={},
    )
    resp.raise_for_status()
    return resp.json()


async def get_session(agent: str, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    client = await get_client()
    resp = await client.get(
        f"{agent_server_url}/apps/{agent}/users/{user_id}/sessions/{session_id}"
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


async def stream_agent(
    agent: str, user_id: str, session_id: str, message: str
) -> AsyncGenerator[Dict[str, Any], None]:
    client = await get_client()
    payload = {
        "appName": agent,
        "userId": user_id,
        "sessionId": session_id,
        "newMessage": {"role": "user", "parts": [{"text": message}]},
        "streaming": False,
    }
    async with client.stream("POST", f"{agent_server_url}/run_sse", json=payload) as resp:
        if resp.is_error:
            yield {"author": agent, "content": {"parts": [{"text": f"Error: {resp.status_code}"}]}}
            return
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                raw = line[5:].strip()
                if not raw or raw == "[DONE]":
                    continue
                try:
                    yield json.loads(raw)
                except json.JSONDecodeError:
                    pass

# ── Chat endpoint ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    user_id: str = "user"
    session_id: Optional[str] = None
    calendar_token: Optional[str] = None

@app.post("/api/chat_stream")
async def chat_stream(req: ChatRequest):
    agent = await discover_agent_name()

    # Resolve session
    session = None
    if req.session_id:
        try:
            session = await get_session(agent, req.user_id, req.session_id)
        except Exception:
            pass

    if session is None:
        session = await create_session(agent, req.user_id)

    # Inject token as hidden context so ADK doesn't override it
    msg = req.message
    if req.calendar_token:
        msg += f"\n\n[SYSTEM] The user's Google Calendar OAuth Token is: {req.calendar_token}"

    async def generate():
        last_text = ""
        final_text = ""
        try:
            async for event in stream_agent(agent, req.user_id, session["id"], msg):
                author  = event.get("author", "")
                content = event.get("content") or {}
                parts   = content.get("parts", [])

                # Send progress hint based on author
                progress_map = {
                    "logistics":         "🛎️ Logistics Agent is processing your travel request…",
                    "travel_researcher": "🔍 Travel Researcher is finding hotel options…",
                    "policy_auditor":    "⚖️ Policy Auditor is checking budget constraints…",
                    "accountant":        "📝 Accountant is logging expenses to AlloyDB…",
                }
                if author in progress_map:
                    yield json.dumps({"type": "progress", "text": progress_map[author]}) + "\n"

                # Capture text — prefer the final orchestrator summary
                for part in parts:
                    t = part.get("text", "")
                    if t:
                        last_text = t
                        # If the orchestrator sends a final summary, mark it
                        if author in ("concierge_pipeline", "orchestrator", agent):
                            final_text = t

        except Exception as e:
            logger.error(f"Streaming error: {e}")

        # Use final orchestrator text if available, otherwise last agent text
        result = final_text or last_text or "The travel plan has been processed by all agents."
        yield json.dumps({"type": "result", "text": result.strip()}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "agent_url": agent_server_url}


# ── Static frontend ──────────────────────────────────────────────────────────

frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Travel Concierge frontend on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
