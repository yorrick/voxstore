#!/bin/bash

AUTOPILOT_PORT=${PORT:-8002}

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Starting VoxStore Autopilot...${NC}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"
AUTOPILOT_DIR="$PROJECT_ROOT/autopilot"
LOG_DIR="$AUTOPILOT_DIR/logs"

# Check for .env
if [ ! -f "$AUTOPILOT_DIR/.env" ]; then
    echo -e "${RED}No .env file found in autopilot/.${NC}"
    echo "Run: cp autopilot/.env.sample autopilot/.env"
    exit 1
fi

mkdir -p "$LOG_DIR"

cleanup() {
    echo -e "\n${BLUE}Shutting down autopilot...${NC}"
    jobs -p | xargs -r kill 2>/dev/null
    wait
    echo -e "${GREEN}Stopped.${NC}"
    exit 0
}

trap cleanup EXIT INT TERM

# Kill existing process on port
pid=$(lsof -ti:$AUTOPILOT_PORT 2>/dev/null)
if [ ! -z "$pid" ]; then
    echo -e "Killing existing process on port $AUTOPILOT_PORT..."
    kill -9 $pid 2>/dev/null
    sleep 1
fi

# Start autopilot webhook server (no hot reload — reload kills running agent processes)
cd "$AUTOPILOT_DIR"
.venv/bin/uvicorn autopilot.webhook_server:app \
    --host 0.0.0.0 \
    --port $AUTOPILOT_PORT \
    --app-dir "$PROJECT_ROOT" \
    2>&1 | tee "$LOG_DIR/autopilot.log" &

sleep 2

echo -e "${GREEN}Autopilot running on port $AUTOPILOT_PORT${NC}"
echo -e "${BLUE}Sentry webhook: POST http://localhost:$AUTOPILOT_PORT/webhook/sentry${NC}"
echo -e "${BLUE}GitHub webhook:  POST http://localhost:$AUTOPILOT_PORT/webhook/github${NC}"
echo -e "${BLUE}Health check:    GET  http://localhost:$AUTOPILOT_PORT/health${NC}"
echo -e "${BLUE}Logs:            $LOG_DIR/autopilot.log${NC}"
echo ""
echo "Press Ctrl+C to stop"

wait
