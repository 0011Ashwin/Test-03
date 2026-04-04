#!/bin/bash

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "${SCRIPT_DIR}"

if [ -f ".env" ]; then
  source .env
fi

if [[ "${GOOGLE_CLOUD_PROJECT}" == "" ]]; then
  GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project -q)
fi
if [[ "${GOOGLE_CLOUD_PROJECT}" == "" ]]; then
  echo "ERROR: Run 'gcloud config set project' command to set active project, or set GOOGLE_CLOUD_PROJECT environment variable."
  exit 1
fi

REGION="${GOOGLE_CLOUD_LOCATION}"
if [[ "${REGION}" == "global" ]]; then
  echo "GOOGLE_CLOUD_LOCATION is set to 'global'. Getting a default location for Cloud Run."
  REGION=""
fi

if [[ "${REGION}" == "" ]]; then
  REGION=$(gcloud config get-value compute/region -q)
  if [[ "${REGION}" == "" ]]; then
    REGION="us-central1"
    echo "WARNING: Cannot get a configured compute region. Defaulting to ${REGION}."
  fi
fi
echo "Using project ${GOOGLE_CLOUD_PROJECT}."
echo "Using compute region ${REGION}."

gcloud run deploy logistics \
  --source agents/logistics \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --allow-unauthenticated \
  --labels dev-tutorial=prod-ready-1 \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true"
LOGISTICS_URL=$(gcloud run services describe logistics --region $REGION --format='value(status.url)')

gcloud run deploy travel-researcher \
  --source agents/travel_researcher \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --allow-unauthenticated \
  --labels dev-tutorial=prod-ready-1 \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true"
TRAVEL_RESEARCHER_URL=$(gcloud run services describe travel-researcher --region $REGION --format='value(status.url)')

gcloud run deploy policy-auditor \
  --source agents/policy_auditor \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --allow-unauthenticated \
  --labels dev-tutorial=prod-ready-1 \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true"
POLICY_AUDITOR_URL=$(gcloud run services describe policy-auditor --region $REGION --format='value(status.url)')

gcloud run deploy accountant \
  --source agents/accountant \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --allow-unauthenticated \
  --labels dev-tutorial=prod-ready-1 \
  --set-env-vars DB_HOST="10.221.0.2",DB_PASS="SuperSecretPassword123" \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true"
ACCOUNTANT_URL=$(gcloud run services describe accountant --region $REGION --format='value(status.url)')

gcloud run deploy orchestrator \
  --source agents/orchestrator \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --allow-unauthenticated \
  --labels dev-tutorial=prod-ready-1 \
  --set-env-vars LOGISTICS_AGENT_CARD_URL=$LOGISTICS_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars TRAVEL_RESEARCHER_AGENT_CARD_URL=$TRAVEL_RESEARCHER_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars POLICY_AUDITOR_AGENT_CARD_URL=$POLICY_AUDITOR_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars ACCOUNTANT_AGENT_CARD_URL=$ACCOUNTANT_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true"
ORCHESTRATOR_URL=$(gcloud run services describe orchestrator --region $REGION --format='value(status.url)')
echo "Orchestrator URL: $ORCHESTRATOR_URL"

gcloud run deploy course-creator \
  --source app \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --allow-unauthenticated \
  --labels dev-tutorial=prod-ready-1 \
  --set-env-vars AGENT_SERVER_URL=$ORCHESTRATOR_URL \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}"
