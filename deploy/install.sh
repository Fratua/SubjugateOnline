#!/bin/bash
# Installation Script for Subjugate Online

set -e

echo "=== Subjugate Online - Installation ==="
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
REQUIRED_VERSION="3.8"

echo "Checking Python version..."
if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)"
    exit 1
fi
echo "Python version: $PYTHON_VERSION ✓"
echo ""

# Check PostgreSQL
echo "Checking PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "Error: PostgreSQL is not installed"
    echo "Install with: sudo apt-get install postgresql postgresql-contrib"
    exit 1
fi
echo "PostgreSQL installed ✓"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "Virtual environment created ✓"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "Dependencies installed ✓"
echo ""

# Setup database
echo "Setting up database..."
chmod +x deploy/setup_database.sh
./deploy/setup_database.sh
echo ""

# Install package
echo "Installing Subjugate Online..."
pip install -e .
echo "Package installed ✓"
echo ""

# Create directories
echo "Creating required directories..."
mkdir -p logs
mkdir -p subjugate_online/assets/models
mkdir -p subjugate_online/assets/textures
mkdir -p subjugate_online/assets/sounds
mkdir -p subjugate_online/assets/shaders
echo "Directories created ✓"
echo ""

echo "=== Installation Complete! ==="
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Start login server: python -m subjugate_online.login_server.server"
echo "3. Start game server: python -m subjugate_online.game_server.server"
echo "4. Start client: python -m subjugate_online.client.client"
echo ""
echo "Or use the convenience scripts:"
echo "  ./deploy/start_servers.sh"
echo "  ./deploy/start_client.sh"
