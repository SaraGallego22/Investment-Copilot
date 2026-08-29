#!/usr/bin/env bash
# Deploy the JUSARA agent + web UI to Cloud Run.
# Scale-to-zero with an instance ceiling, per the hackathon's cost guidance.
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"

# NOTE: two different locations, deliberately.
#   GOOGLE_CLOUD_LOCATION = "global"  -> Vertex endpoint serving Gemini 3.5
#                                        (the models 404 in every region).
#   CLOUD_RUN_REGION      = a real region -> where the container runs.
# "global" is not a valid Cloud Run region, so these must not be conflated.
: "${CLOUD_RUN_REGION:=us-central1}"
: "${GOOGLE_CLOUD_LOCATION:=global}"
: "${MARKET_API_URL:?Set MARKET_API_URL (deploy market_api first)}"
: "${MARKET_API_KEY:?Set MARKET_API_KEY}"

SERVICE_NAME="jusara-agent"

gcloud run deploy "$SERVICE_NAME" \
  --source "$(dirname "$0")/.." \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$CLOUD_RUN_REGION" \
  --min-instances 0 \
  --max-instances 3 \
  --memory 1Gi \
  --cpu 1 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars "GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION}" \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=true" \
  --set-env-vars "MODEL_DEFAULT=${MODEL_DEFAULT:-gemini-3.5-flash}" \
  --set-env-vars "MODEL_COMPLEX_REASONING=${MODEL_COMPLEX_REASONING:-gemini-3.5-flash}" \
  --set-env-vars "MEMORY_BACKEND=${MEMORY_BACKEND:-firestore}" \
  --set-env-vars "MARKET_API_URL=${MARKET_API_URL}" \
  --set-env-vars "MARKET_API_KEY=${MARKET_API_KEY}" \
  --allow-unauthenticated

echo
echo "Deployed. URL:"
gcloud run services describe "$SERVICE_NAME" \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$CLOUD_RUN_REGION" \
  --format 'value(status.url)'
