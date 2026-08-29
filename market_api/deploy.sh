#!/usr/bin/env bash
# Deploy the JUSARA market simulator to Cloud Run.
# Scale-to-zero: nothing bills while the demo is not running.
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
: "${MARKET_API_KEY:?Set MARKET_API_KEY (the shared secret the agent will send)}"
: "${CLOUD_RUN_REGION:=us-central1}"

SERVICE_NAME="jusara-market-api"
HERE="$(cd "$(dirname "$0")" && pwd)"

# The build context is market_api/ itself. It is self-contained, which keeps
# the repo's 350 MB .venv and the data/ directory out of the upload, and lets
# gcloud find the Dockerfile at the context root.
gcloud run deploy "$SERVICE_NAME" \
  --source "$HERE" \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$CLOUD_RUN_REGION" \
  --min-instances 0 \
  --max-instances 3 \
  --memory 512Mi \
  --cpu 1 \
  --set-env-vars "MARKET_API_KEY=${MARKET_API_KEY}" \
  --set-env-vars "REQUIRE_AUTH=true" \
  --allow-unauthenticated

echo
echo "Deployed. Set this in your .env as MARKET_API_URL:"
gcloud run services describe "$SERVICE_NAME" \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$CLOUD_RUN_REGION" \
  --format 'value(status.url)'
