#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Starting VoxStore Autopilot Poller...${NC}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

# Check for .env
if [ ! -f "$PROJECT_ROOT/autopilot/.env" ]; then
    echo -e "${RED}No .env file found in autopilot/.${NC}"
    echo "Run: cp autopilot/.env.sample autopilot/.env"
    exit 1
fi

cleanup() {
    echo -e "\n${BLUE}Shutting down poller...${NC}"
    jobs -p | xargs -r kill 2>/dev/null
    wait
    echo -e "${GREEN}Stopped.${NC}"
    exit 0
}

trap cleanup EXIT INT TERM

# Start poller
cd "$PROJECT_ROOT"
uv run autopilot/poller.py &

sleep 2

echo -e "${GREEN}Poller running${NC}"
echo -e "${BLUE}Polling Sentry every ${POLL_INTERVAL_SECONDS:-300}s${NC}"
echo ""
echo "Press Ctrl+C to stop"

wait
