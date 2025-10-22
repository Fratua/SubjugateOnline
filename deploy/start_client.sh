#!/bin/bash
# Start Subjugate Online Client

set -e

echo "=== Starting Subjugate Online Client ==="

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found. Run install.sh first."
    exit 1
fi

# Start client
python -m subjugate_online.client.client
