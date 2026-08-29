#!/usr/bin/env bash
# Deploy a Cloud Run con scale-to-zero y techo de instancias
# (ver hackathon-agentic.md seccion 6, "Pro tips de costos").
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
: "${GOOGLE_CLOUD_LOCATION:=us-central1}"

SERVICE_NAME="collaborative-partner"

gcloud run deploy "$SERVICE_NAME" \
  --source "$(dirname "$0")/.." \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$GOOGLE_CLOUD_LOCATION" \
  --min-instances 0 \
  --max-instances 3 \
  --memory 512Mi \
  --cpu 1 \
  --no-allow-unauthenticated
