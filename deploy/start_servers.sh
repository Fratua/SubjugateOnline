#!/bin/bash
# Start all Subjugate Online servers

set -e

echo "=== Starting Subjugate Online Servers ==="

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found. Run install.sh first."
    exit 1
fi

# Create log directory
mkdir -p logs

# Start login server in background
echo "Starting Login Server..."
python -m subjugate_online.login_server.server > logs/login_server.log 2>&1 &
LOGIN_PID=$!
echo "Login Server started (PID: $LOGIN_PID)"

# Wait a bit for login server to start
sleep 2

# Start game server in background
echo "Starting Game Server..."
python -m subjugate_online.game_server.server > logs/game_server.log 2>&1 &
GAME_PID=$!
echo "Game Server started (PID: $GAME_PID)"

# Save PIDs
echo $LOGIN_PID > logs/login_server.pid
echo $GAME_PID > logs/game_server.pid

echo ""
echo "=== Servers Started Successfully ==="
echo "Login Server PID: $LOGIN_PID"
echo "Game Server PID: $GAME_PID"
echo ""
echo "Logs:"
echo "  Login Server: tail -f logs/login_server.log"
echo "  Game Server: tail -f logs/game_server.log"
echo ""
echo "Stop servers with: ./deploy/stop_servers.sh"
