#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="jet-finder"
BACKEND_SERVICE="backend-service"
FRONTEND_SERVICE="frontend-service"

if ! command -v railway >/dev/null 2>&1; then
  echo "Railway CLI is required. Install from https://railway.app/cli and try again."
  exit 1
fi

railway status >/dev/null 2>&1 || railway login

railway link --project "$PROJECT_NAME"

echo "🔄 Deploying backend..."
railway up --service "$BACKEND_SERVICE"

echo "🚀 Running migrations..."
railway run --service "$BACKEND_SERVICE" "cd /app/database && alembic upgrade head"

echo "🔄 Deploying frontend..."
railway up --service "$FRONTEND_SERVICE"

echo "✅ Deployment triggered. Monitor progress with 'railway logs'."

