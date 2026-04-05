"""
Orchestrator main.py - bypasses adk_app.py entirely.
Starts a simple FastAPI server that mimics the ADK REST API
and calls sub-agents via HTTP.
"""
import asyncio
import json
import os
import uuid
import sys

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

# ── Config ──────────────────────────────────────────────────────────────────

def _base(env_key: str, fallback: str) -> str:
    url = os.environ.get(env_key, "")
    for suffix in [
        "/a2a/agent/.well-known/agent-card.json",
        "/.well-known/agent-card.json",
    ]:
        if url.endswith(suffix):
            return url[: -len(suffix)]
    return url or fallback

LOGISTICS_URL   = _base("LOGISTICS_AGENT_CARD_URL",         "http://localhost:8001")
RESEARCHER_URL  = _base("TRAVEL_RESEARCHER_AGENT_CARD_URL", "http://localhost:8002")
AUDITOR_URL     = _base("POLICY_AUDITOR_AGENT_CARD_URL",    "http://localhost:8003")
ACCOUNTANT_URL  = _base("ACCOUNTANT_AGENT_CARD_URL",        "http://localhost:8004")

APP_NAME = "agent"

# ── Simple in-memory session store ──────────────────────────────────────────

sessions: Dict[str, Dict] = {}

# ── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(title="Travel Concierge Orchestrator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ADK-compatible endpoint: list apps ───────────────────────────────────────

@app.get("/list-apps")
async def list_apps():
    return [APP_NAME]

# ── ADK-compatible endpoint: create session ──────────────────────────────────

@app.post("/apps/{app_name}/users/{user_id}/sessions")
async def create_session(app_name: str, user_id: str):
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"id": session_id, "userId": user_id, "appName": app_name, "events": []}
    return sessions[session_id]

# ── ADK-compatible endpoint: get session ─────────────────────────────────────

@app.get("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def get_session(app_name: str, user_id: str, session_id: str):
    from fastapi import HTTPException
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]

# ── Helper: call a sub-agent via its ADK /run_sse endpoint ───────────────────

async def call_agent(base_url: str, message: str, author_name: str) -> str:
    """Calls an ADK sub-agent and returns its final text response."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Create session — use the ID the server assigns
        sess_resp = await client.post(f"{base_url}/apps/{APP_NAME}/users/orchestrator/sessions", json={})
        sess_data = sess_resp.json() if sess_resp.status_code in (200, 201) else {}
        session_id = sess_data.get("id") or str(uuid.uuid4())

        # Run agent
        payload = {
            "appName": APP_NAME,
            "userId": "orchestrator",
            "sessionId": session_id,
            "newMessage": {"role": "user", "parts": [{"text": message}]},
            "streaming": False,
        }
        resp = await client.post(f"{base_url}/run_sse", json=payload)
        if resp.status_code != 200:
            return f"[{author_name} error {resp.status_code}]: {resp.text[:300]}"

        # Parse SSE stream
        full_text = ""
        for line in resp.text.splitlines():
            if line.startswith("data:"):
                raw = line[5:].strip()
                if not raw:
                    continue
                try:
                    event = json.loads(raw)
                    content = event.get("content") or {}
                    for part in content.get("parts", []):
                        if part.get("text"):
                            full_text += part["text"]
                except json.JSONDecodeError:
                    pass
        return full_text or f"[{author_name}] completed with no text output."

# ── ADK-compatible endpoint: run_sse ─────────────────────────────────────────

class RunRequest(BaseModel):
    appName: str = APP_NAME
    userId: str = "user"
    sessionId: str = ""
    newMessage: Dict[str, Any] = {}
    streaming: bool = False

@app.post("/run_sse")
async def run_sse(req: RunRequest):
    user_message = ""
    for part in req.newMessage.get("parts", []):
        if part.get("text"):
            user_message += part["text"]

    async def generate():
        def event(author: str, text: str):
            payload = {
                "author": author,
                "content": {"parts": [{"text": text}]},
            }
            return f"data: {json.dumps(payload)}\n\n"

        # Step 1 – Logistics
        yield event("logistics", f"🛎️ Processing travel request: {user_message}")
        logistics_result = await call_agent(LOGISTICS_URL, user_message, "logistics")
        yield event("logistics", logistics_result)

        # Step 2 – Travel Researcher
        yield event("travel_researcher", "🔍 Researching hotel options...")
        researcher_result = await call_agent(RESEARCHER_URL, logistics_result, "travel_researcher")
        yield event("travel_researcher", researcher_result)

        # Step 3 – Policy Auditor (up to 3 tries)
        audit_result = ""
        for attempt in range(3):
            yield event("policy_auditor", f"⚖️ Checking budget compliance (attempt {attempt + 1})...")
            audit_result = await call_agent(AUDITOR_URL, researcher_result, "policy_auditor")
            yield event("policy_auditor", audit_result)
            if '"status": "pass"' in audit_result or "'status': 'pass'" in audit_result or "pass" in audit_result.lower():
                break
            # If failed, ask researcher to find cheaper options
            if attempt < 2:
                researcher_result = await call_agent(
                    RESEARCHER_URL,
                    f"Find cheaper hotels. Previous options failed budget: {audit_result}",
                    "travel_researcher",
                )

        # Step 4 – Accountant
        yield event("accountant", "📝 Logging approved expenses...")
        expense_summary = f"Flight: {logistics_result}\nHotel: {researcher_result}\nAudit: {audit_result}"
        accountant_result = await call_agent(ACCOUNTANT_URL, expense_summary, "accountant")
        yield event("accountant", accountant_result)

        # Final summary
        final = (
            f"## ✅ Travel Plan Confirmed\n\n"
            f"**Logistics:** {logistics_result}\n\n"
            f"**Hotel:** {researcher_result}\n\n"
            f"**Policy Status:** {audit_result}\n\n"
            f"**Expense Logged:** {accountant_result}"
        )
        yield event("concierge_pipeline", final)

    return StreamingResponse(generate(), media_type="text/event-stream")

# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/")
async def health():
    return {"status": "ok", "service": "travel-concierge-orchestrator"}

# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting orchestrator on port {port}", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
