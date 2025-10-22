#!/bin/bash
# Stop all Subjugate Online servers

echo "=== Stopping Subjugate Online Servers ==="

# Stop login server
if [ -f "logs/login_server.pid" ]; then
    LOGIN_PID=$(cat logs/login_server.pid)
    echo "Stopping Login Server (PID: $LOGIN_PID)..."
    kill $LOGIN_PID 2>/dev/null || echo "Login server already stopped"
    rm -f logs/login_server.pid
else
    echo "Login server not running"
fi

# Stop game server
if [ -f "logs/game_server.pid" ]; then
    GAME_PID=$(cat logs/game_server.pid)
    echo "Stopping Game Server (PID: $GAME_PID)..."
    kill $GAME_PID 2>/dev/null || echo "Game server already stopped"
    rm -f logs/game_server.pid
else
    echo "Game server not running"
fi

echo ""
echo "=== Servers Stopped ==="
