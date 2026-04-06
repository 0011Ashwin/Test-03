# Travel Concierge Multi-Agent System (APAC Edition)

A distributed multi-agent travel planning system built with Google's **Agent Development Kit (ADK)** and the **Agent-to-Agent (A2A)** protocol. This project demonstrates a production-grade orchestration of specialized microservice agents that collaborate to deliver a personalized, policy-compliant travel plan.

## 🏗️ Architecture

The system follows a sequential orchestration pattern where a central **Orchestrator** coordinates four specialized sub-agents. Each agent is a standalone microservice that exposes an ADK-standard API.

1.  **Frontend (Web App)**: A modern, responsive UI that communicates with the Orchestrator.
2.  **Orchestrator**: The central "brain" that:
    -   Receives the user request from the UI.
    -   Sequentially calls the sub-agents via A2A.
    -   Uses **Gemini 2.5 Pro** to synthesize raw agent outputs into a polished, human-readable travel plan.
    -   Triggers the automated email dispatch.
3.  **Specialized Agents**:
    -   🛎️ **Logistics Agent**: Processes flight details and manages calendar availability.
    -   🔍 **Travel Researcher**: Researches hotel options and itinerary details.
    -   ⚖️ **Policy Auditor**: Validates the proposed plan against corporate budget and travel policies.
    -   📝 **Accountant Agent**: Logs finalized and approved expenses into an **AlloyDB** database for record-keeping.
    -   📧 **Email Sender**: Composes and dispatches the final travel plan directly to the user's Gmail inbox.

## 📂 Project Structure

```text
prai-roadshow-lab-1/
├── agents/                  # Multi-agent microservices
│   ├── orchestrator/        # Central workflow & Gemini synthesis
│   ├── logistics/           # Flight & Calendar integration
│   ├── travel_researcher/   # Hotel & Itinerary research
│   ├── policy_auditor/      # Budget & Policy compliance
│   ├── accountant/          # AlloyDB expense logging
│   └── email_sender/        # Automated Gmail dispatch
├── app/                     # Frontend Web Application
│   └── frontend/            # Static UI assets (HTML/JS/CSS)
├── shared/                  # Shared utilities (ADK app, auth, utils)
└── run_local.sh             # Script to start all services locally
```

## 🛠️ Getting Started

### Prerequisites

-   **Python 3.10+** (managed via `uv`)
-   **Google Cloud Project** with Vertex AI enabled
-   **GCloud SDK** installed and authenticated (`gcloud auth application-default login`)

### Local Setup

1.  **Install dependencies**:
    ```bash
    uv sync
    ```

2.  **Configure environment**:
    Copy `.env.example` to `.env` and fill in your `GOOGLE_CLOUD_PROJECT`.
    ```bash
    cp .env.example .env
    ```

3.  **Run the system**:
    The provided script starts all 5 agent services and the frontend server on separate ports.
    ```bash
    ./run_local.sh
    ```

4.  **Access the application**:
    Open [http://localhost:8000](http://localhost:8000) in your browser.

## 🚀 Deployment

The system is designed to be deployed as a set of individual services on **Google Cloud Run**.

1.  **Deploy sub-agents**: Deploy `logistics`, `researcher`, `auditor`, and `accountant` to Cloud Run.
2.  **Note URLs**: Collect the `agent-card.json` URLs for each deployed service.
3.  **Deploy Orchestrator**: Deploy the `orchestrator` service, providing the sub-agent URLs as environment variables:
    -   `LOGISTICS_AGENT_CARD_URL`
    -   `TRAVEL_RESEARCHER_AGENT_CARD_URL`
    -   `POLICY_AUDITOR_AGENT_CARD_URL`
    -   `ACCOUNTANT_AGENT_CARD_URL`
4.  **Deploy App**: Deploy the `app/` service, pointing it to your Orchestrator's URL via `AGENT_SERVER_URL`.

## 🧪 Technology Stack

-   **Orchestration**: Agent Development Kit (ADK) & A2A protocol.
-   **LLM**: Google Gemini 2.5 Pro (via Vertex AI).
-   **Framework**: FastAPI (Python).
-   **Database**: Google Cloud AlloyDB.
-   **Deployment**: Google Cloud Run & Artifact Registry.
