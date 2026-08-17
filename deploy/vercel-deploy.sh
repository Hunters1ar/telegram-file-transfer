#!/usr/bin/env bash
set -euo pipefail

# Non-interactive Vercel deploy script. Requires VERCEL_TOKEN in the environment.
# Usage:
#   export VERCEL_TOKEN="your_token"
#   ./deploy/vercel-deploy.sh

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR/website"

if [ -z "${VERCEL_TOKEN:-}" ]; then
  echo "ERROR: VERCEL_TOKEN not set. Export it and retry."
  exit 1
fi

echo "Installing frontend dependencies..."
npm ci

echo "Deploying to Vercel (production)..."
npx vercel --prod --token "$VERCEL_TOKEN"

echo "Vercel deploy finished."
