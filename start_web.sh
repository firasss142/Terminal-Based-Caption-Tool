#!/bin/bash
# start_web.sh — Launch the RT Caption Generator web UI
# Usage: bash start_web.sh

cd "$(dirname "$0")"

echo ""
echo "  RT Caption Generator  —  Web UI"
echo "  ─────────────────────────────────"
echo "  http://localhost:8765"
echo ""

# Auto-open browser on macOS (non-blocking)
open http://localhost:8765 2>/dev/null &

# Start server (uses the project venv's python3)
.venv/bin/python -m uvicorn web.server:app --host 127.0.0.1 --port 8765
