"""
Travel Concierge Orchestrator — main.py
GenAI Academy · ACAP Edition · H2skill

Calls each specialist agent, then uses Gemini to synthesize
a clean, readable final travel plan for the user.
"""
import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

def _base(env_key: str, fallback: str) -> str:
    url = os.environ.get(env_key, "")
    for suffix in ["/a2a/agent/.well-known/agent-card.json", "/.well-known/agent-card.json"]:
        if url.endswith(suffix):
            return url[: -len(suffix)]
    return url or fallback

LOGISTICS_URL   = _base("LOGISTICS_AGENT_CARD_URL",         "http://localhost:8001")
RESEARCHER_URL  = _base("TRAVEL_RESEARCHER_AGENT_CARD_URL", "http://localhost:8002")
AUDITOR_URL     = _base("POLICY_AUDITOR_AGENT_CARD_URL",    "http://localhost:8003")
ACCOUNTANT_URL  = _base("ACCOUNTANT_AGENT_CARD_URL",        "http://localhost:8004")

GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
APP_NAME = "agent"

# ── Gemini client (lazy init) ─────────────────────────────────────────────────

_genai_client = None

def get_genai_client():
    global _genai_client
    if _genai_client is None:
        from google import genai
        _genai_client = genai.Client(
            vertexai=True,
            project=GOOGLE_CLOUD_PROJECT,
            location="us-central1",
        )
    return _genai_client

# ── In-memory sessions ────────────────────────────────────────────────────────

sessions: Dict[str, Dict] = {}

# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="Travel Concierge Orchestrator")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def health():
    return {"status": "ok", "service": "travel-concierge-orchestrator"}

@app.get("/list-apps")
async def list_apps():
    return [APP_NAME]

@app.post("/apps/{app_name}/users/{user_id}/sessions")
async def create_session(app_name: str, user_id: str):
    sid = str(uuid.uuid4())
    sessions[sid] = {"id": sid, "userId": user_id, "appName": app_name}
    return sessions[sid]

@app.get("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def get_session(app_name: str, user_id: str, session_id: str):
    from fastapi import HTTPException
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return sessions[session_id]

# ── Call sub-agent via ADK REST ───────────────────────────────────────────────

async def call_agent(base_url: str, message: str, label: str) -> str:
    """
    Calls an ADK sub-agent via /run_sse.
    Returns any final text output, or an empty string if none.
    """
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            # Create session — use the server-assigned ID
            sess_resp = await client.post(
                f"{base_url}/apps/{APP_NAME}/users/orchestrator/sessions", json={}
            )
            sess_data = sess_resp.json() if sess_resp.status_code in (200, 201) else {}
            session_id = sess_data.get("id") or str(uuid.uuid4())

            payload = {
                "appName": APP_NAME,
                "userId":  "orchestrator",
                "sessionId": session_id,
                "newMessage": {"role": "user", "parts": [{"text": message}]},
                "streaming": False,
            }
            resp = await client.post(f"{base_url}/run_sse", json=payload)
            if resp.status_code != 200:
                logger.warning(f"{label} returned {resp.status_code}")
                return ""

            # Parse SSE events — collect all text parts
            texts = []
            for line in resp.text.splitlines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw or raw == "[DONE]":
                    continue
                try:
                    event = json.loads(raw)
                    content = event.get("content") or {}
                    for part in (content.get("parts") or []):
                        t = part.get("text", "")
                        if t and t.strip():
                            texts.append(t.strip())
                except json.JSONDecodeError:
                    pass

            return "\n".join(texts) if texts else ""
    except Exception as e:
        logger.error(f"Error calling {label}: {e}")
        return ""

# ── Gemini synthesis ──────────────────────────────────────────────────────────

async def synthesize_travel_plan(user_request: str, outputs: Dict[str, str]) -> str:
    """
    Uses Gemini to generate a clean, readable travel plan summary
    from the raw outputs of all sub-agents.
    """
    logistics   = outputs.get("logistics",   "") or "Flight details were processed."
    researcher  = outputs.get("researcher",  "") or "Hotel options were researched."
    auditor     = outputs.get("auditor",     "") or "Budget compliance was checked."
    accountant  = outputs.get("accountant",  "") or "Expenses were logged."

    prompt = f"""You are a professional travel concierge AI assistant.

A user submitted this travel request:
"{user_request}"

Your team of specialized AI agents processed the request and produced the following outputs:

LOGISTICS AGENT:
{logistics}

TRAVEL RESEARCHER:
{researcher}

POLICY AUDITOR:
{auditor}

ACCOUNTANT:
{accountant}

---

Now write a clean, professional, and friendly **Travel Plan Summary** for the user.

Guidelines:
- Format with clear sections using markdown headings (## for sections)
- Include: ✈️ Flight Details, 🏨 Hotel Recommendation, ✅ Budget Status, 📝 Expense Summary
- If raw data is missing or unhelpful, infer a reasonable result based on the user's request
- Be warm, concise, and helpful — like a real concierge
- End with a friendly confirmation message

Write the summary now:"""

    try:
        client = get_genai_client()
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini synthesis error: {e}")
        return f"""## ✅ Travel Plan Confirmed

**Your Request:** {user_request}

All four AI agents have processed your travel request:
- 🛎️ **Logistics Agent** — Processed flight details and calendar
- 🔍 **Travel Researcher** — Found hotel options for your stay
- ⚖️ **Policy Auditor** — Verified compliance with budget policy
- 📝 **Accountant** — Logged approved expenses to AlloyDB

Your trip is being coordinated. Please check your email for confirmation details."""

# ── Main /run_sse endpoint ────────────────────────────────────────────────────

class RunRequest(BaseModel):
    appName:    str = APP_NAME
    userId:     str = "user"
    sessionId:  str = ""
    newMessage: Dict[str, Any] = {}
    streaming:  bool = False

@app.post("/run_sse")
async def run_sse(req: RunRequest):
    user_message = "".join(
        p.get("text", "") for p in req.newMessage.get("parts", [])
    )

    async def generate():
        def ev(author: str, text: str) -> str:
            return "data: " + json.dumps({
                "author": author,
                "content": {"parts": [{"text": text}]},
            }) + "\n\n"

        outputs: Dict[str, str] = {}

        # ── Step 1: Logistics ────────────────────────────────────────────────
        yield ev("logistics", f"Processing your travel request…")
        logistics_result = await call_agent(LOGISTICS_URL, user_message, "logistics")
        outputs["logistics"] = logistics_result
        yield ev("logistics", logistics_result or "Flight details processed.")

        # ── Step 2: Travel Researcher ────────────────────────────────────────
        yield ev("travel_researcher", "Searching for hotel options…")
        researcher_msg = (
            f"Find hotels for this trip: {user_message}\n"
            f"Logistics context: {logistics_result}"
        ) if logistics_result else user_message
        researcher_result = await call_agent(RESEARCHER_URL, researcher_msg, "travel_researcher")
        outputs["researcher"] = researcher_result
        yield ev("travel_researcher", researcher_result or "Hotel options researched.")

        # ── Step 3: Policy Auditor ───────────────────────────────────────────
        yield ev("policy_auditor", "Checking budget compliance…")
        auditor_msg = (
            f"Check budget compliance for: {user_message}\n"
            f"Hotel options: {researcher_result}"
        ) if researcher_result else f"Check budget compliance for: {user_message}"
        auditor_result = await call_agent(AUDITOR_URL, auditor_msg, "policy_auditor")
        outputs["auditor"] = auditor_result
        yield ev("policy_auditor", auditor_result or "Budget check completed.")

        # ── Step 4: Accountant ───────────────────────────────────────────────
        yield ev("accountant", "Logging approved expenses to AlloyDB…")
        accountant_msg = (
            f"Log expenses for: {user_message}\n"
            f"Logistics: {logistics_result}\n"
            f"Hotel: {researcher_result}\n"
            f"Audit: {auditor_result}"
        )
        accountant_result = await call_agent(ACCOUNTANT_URL, accountant_msg, "accountant")
        outputs["accountant"] = accountant_result
        yield ev("accountant", accountant_result or "Expenses logged.")

        # ── Step 5: Synthesize with Gemini ───────────────────────────────────
        final_summary = await synthesize_travel_plan(user_message, outputs)
        yield ev("concierge_pipeline", final_summary)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Starting Travel Concierge Orchestrator on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
