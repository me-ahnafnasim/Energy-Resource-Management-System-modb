#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs

if pgrep -f "streamlit run src/db_b6/dashboard.py" >/dev/null 2>&1; then
  echo "Dashboard is already running."
  echo "Open http://localhost:8501"
  exit 0
fi

nohup .venv/bin/streamlit run src/db_b6/dashboard.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true \
  --server.fileWatcherType none \
  --browser.gatherUsageStats false \
  > logs/dashboard.log 2>&1 &

echo "Dashboard started."
echo "Open http://localhost:8501"
echo "Logs: logs/dashboard.log"
