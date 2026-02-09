#!/bin/bash

SERVER_PORT=${BACKEND_PORT:-8000}

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}Starting VoxStore...${NC}"

# Get project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

# Check for .env
if [ ! -f "$PROJECT_ROOT/app/server/.env" ]; then
    echo -e "${RED}No .env file found in app/server/.${NC}"
    echo "Run: cp app/server/.env.sample app/server/.env"
    exit 1
fi

cleanup() {
    echo -e "\n${BLUE}Shutting down...${NC}"
    jobs -p | xargs -r kill 2>/dev/null
    wait
    echo -e "${GREEN}Stopped.${NC}"
    exit 0
}

trap cleanup EXIT INT TERM

# Kill existing process on port
pid=$(lsof -ti:$SERVER_PORT 2>/dev/null)
if [ ! -z "$pid" ]; then
    echo -e "Killing existing process on port $SERVER_PORT..."
    kill -9 $pid 2>/dev/null
    sleep 1
fi

# Start server (serves both API and static frontend)
echo -e "${GREEN}Starting server on port $SERVER_PORT...${NC}"
cd "$PROJECT_ROOT/app/server"
uv run python server.py &

sleep 2

echo -e "${GREEN}VoxStore running at http://localhost:$SERVER_PORT${NC}"
echo -e "${BLUE}API docs: http://localhost:$SERVER_PORT/docs${NC}"
echo ""
echo "Press Ctrl+C to stop"

wait
