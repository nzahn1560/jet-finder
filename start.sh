#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/backend"

if [ ! -f "${SCRIPT_DIR}/.env" ]; then
  cat <<'EOF' > "${SCRIPT_DIR}/.env"
DATABASE_URL=sqlite:///../database/jetfinder.db
FRONTEND_ORIGIN=http://localhost:5173
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=Passw0rd!
EOF
  echo "Generated default .env file."
fi

pushd backend >/dev/null
python -m pip install --upgrade pip
pip install -r requirements.txt
alembic upgrade head
popd >/dev/null

PYTHONPATH="${SCRIPT_DIR}/backend" python database/seed.py

echo "Starting Docker services..."
docker-compose up --build

