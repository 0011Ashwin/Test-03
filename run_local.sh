#!/bin/bash

# Kill any existing processes on these ports
echo "Stopping any existing processes on ports 8000-8005..."
lsof -ti:8000,8001,8002,8003,8004,8005 | xargs kill -9 2>/dev/null

# Set common environment variables for local development
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI="True" # Use Gemini API locally
export MCP_SERVER_URL="http://localhost:9000" # Local Mock/Real MCP Server

echo "Starting Logistics Agent on port 8001..."
pushd agents/logistics
uv run adk_app.py --host 0.0.0.0 --port 8001 --a2a . &
LOGISTICS_PID=$!
popd

echo "Starting Travel Researcher Agent on port 8002..."
pushd agents/travel_researcher
uv run adk_app.py --host 0.0.0.0 --port 8002 --a2a . &
TRAVEL_RESEARCHER_PID=$!
popd

echo "Starting Policy Auditor Agent on port 8003..."
pushd agents/policy_auditor
uv run adk_app.py --host 0.0.0.0 --port 8003 --a2a . &
POLICY_AUDITOR_PID=$!
popd

echo "Starting Accountant Agent on port 8004..."
pushd agents/accountant
uv run adk_app.py --host 0.0.0.0 --port 8004 --a2a . &
ACCOUNTANT_PID=$!
popd

export LOGISTICS_AGENT_CARD_URL=http://localhost:8001/a2a/agent/.well-known/agent-card.json
export TRAVEL_RESEARCHER_AGENT_CARD_URL=http://localhost:8002/a2a/agent/.well-known/agent-card.json
export POLICY_AUDITOR_AGENT_CARD_URL=http://localhost:8003/a2a/agent/.well-known/agent-card.json
export ACCOUNTANT_AGENT_CARD_URL=http://localhost:8004/a2a/agent/.well-known/agent-card.json

echo "Starting Orchestrator Agent on port 8005..."
pushd agents/orchestrator
uv run adk_app.py --host 0.0.0.0 --port 8005 . &
ORCHESTRATOR_PID=$!
popd

# Wait a bit for them to start up
sleep 5

echo "Starting App Server on port 8000..."
pushd app
export AGENT_SERVER_URL=http://localhost:8005
uv run uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
popd

echo "All agents started!"
echo "Logistics: http://localhost:8001"
echo "Travel Researcher: http://localhost:8002"
echo "Policy Auditor: http://localhost:8003"
echo "Accountant: http://localhost:8004"
echo "Orchestrator: http://localhost:8005"
echo "App Server (Frontend): http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop all agents."

# Wait for all processes
trap "kill $LOGISTICS_PID $TRAVEL_RESEARCHER_PID $POLICY_AUDITOR_PID $ACCOUNTANT_PID $ORCHESTRATOR_PID $BACKEND_PID; exit" INT
wait
