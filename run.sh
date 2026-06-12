#!/bin/bash
# NIST CSF Tracker Startup Script
cd "$(dirname "$0")"

echo "=========================================="
echo "   NIST CSF 2.0 Maturity Tracker"
echo "=========================================="
echo ""

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
pip install flask flask-compress -q

# Run the application
echo "Starting server on http://localhost:5001"
echo "Press Ctrl+C to stop"
echo ""
python app.py
