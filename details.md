# 📝 AI Travel Concierge: Technical & Strategic Details

## 🧩 The Problem Statement: Why we build this?
Modern travel planning is a fragmented, time-consuming process. Users often have to manually:
1.  **Extract Details**: Manually parse flight times, hotel names, and locations.
2.  **Verify Prices**: Search separate platforms for real-time nightly rates and availability.
3.  **Cross-Reference Budgets**: Manually check hotel prices against corporate policy or personal budget limits.
4.  **Keep Records**: Log every expense into a database for tracking.
5.  **Notify Others**: Send out formatted trip summaries and set calendar reminders.

This manual chain is prone to errors, budget overruns, and "context switching" fatigue.

---

## 🛠️ The Solution: Autonomous Multi-Agent Orchestration
Our AI Travel Concierge solves this by creating a **Unified Intelligent Layer**. Instead of a single "chatbot", we deploy a **Swarm of Experts** that work sequentially to automate the entire lifecycle of a travel request.

### 🧩 1. The Google Agent Development Kit (ADK)
The core of this system is built on the **Google ADK**. This allows us to:
-   **Define Agency**: Each agent has its own "System Prompt", model, and set of tools.
-   **Structured Communication**: Agents communicate via the **A2A (Agent-to-Agent)** protocol, passing JSON-encoded "cards" that contain structured data and tool outputs.
-   **Task Isolation**: By separating "Logistics" from "Accounting", we ensure high-precision results for each specialized task.

### 🧠 2. Gemini 1.5 Flash: The Orchestrator
We use **Gemini 1.5 Flash** as the global brain. Why Flash? 
-   **Speed**: For a real-time UI, we need millisecond latency, which Flash provides.
-   **Quota Robustness**: Flash has significantly higher rate limits, preventing "Resource Exhausted" errors during heavy hackathon testing.
-   **Synthesis Power**: Flash is excellent at taking 5 separate JSON blocks from 5 agents and synthesizing them into a premium, human-readable travel plan.

---

## 🏗️ Deep Technical Breakdown

### 🛎️ The Logistics Agent
-   **Input**: User prompt (Natural Language).
-   **Tools**: `google_search` (Flight prices), `google_calendar_create` (REST API).
-   **Output**: Structured JSON containing dates, destination, and budget.

### 🔍 The Travel Researcher
-   **Input**: Destination and budget from Logistics.
-   **Tools**: **Google Places API** (Text Search) for real-world hotel IDs and locations.
-   **Output**: A list of real hotels, addresses, and ratings.

### ⚖️ The Policy Auditor
-   **Input**: Researcher's hotel list and the user's budget.
-   **Logic**: A sophisticated Pydantic-based "Strict Auditor" that flags budget failures and identifies the "best fit" option.

### 📝 The Accountant Agent
-   **Input**: The auditor's approval and trip logistics.
-   **Tools**: `pg8000` (PostgreSQL driver) for **AlloyDB**.
-   **Persistence**: Securely saves the trip record for analytics and reporting.

### 📧 The Email Sender (The "Last Mile")
-   **Input**: The final synthesized trip plan.
-   **Tools**: **Gmail API** with OAuth2 authentication.
-   **Impact**: Closes the loop by pushing the digital itinerary into the user's real-world workspace (their inbox).

---

## 🛡️ Security & Scalability
-   **OAuth 2.0**: The system uses Google Identity for secure, scoped access to Calendar and Gmail. No user passwords are ever stored.
-   **Microservices Architecture**: Each agent is deployed as a standalone **Cloud Run** service, allowing them to scale independently.
-   **Cloud Build**: Integrated CI/CD ensures that every change to the agent logic is automatically pushed to the production environment.

---

### 🏛️ GenAI Academy · APAC Edition
**Hosted by Hack2skill**

*This project represents the cutting edge of agentic AI, moving from "Talking AI" to "Action-Oriented AI" using Google's most advanced developer tools.*
