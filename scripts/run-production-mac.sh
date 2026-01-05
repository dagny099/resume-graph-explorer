#!/bin/bash

#######################################
# Resume Explorer - Production Launcher
# Starts Flask backend in production mode
#######################################

# Get absolute path to project root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting Resume Explorer (Production Mode)..."
echo "Project root: $PROJECT_ROOT"

# Navigate to backend directory
cd "$PROJECT_ROOT/backend"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "Virtual environment activated"
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Virtual environment activated"
else
    echo "ERROR: Virtual environment not found at $PROJECT_ROOT/backend/.venv or $PROJECT_ROOT/backend/venv"
    exit 1
fi

# Set Flask environment variables
export FLASK_ENV=production
export FLASK_DEBUG=0

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found. LLM features may not work."
fi

# Start Flask application
echo "Starting Flask server on port 5005..."
python -m resume_explorer.api.app --port 5005
