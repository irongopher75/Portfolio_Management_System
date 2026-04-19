#!/bin/bash

# AXIOM Terminal: Local MySQL Boot Sequence
# This script launches the local MySQL-backed Flask app.

echo "🚀 Initiating Axiom Institutional Terminal..."

# 1. Start MySQL
echo "📦 Step 1: Starting local MySQL service..."
brew services start mysql 2>/dev/null || echo "⚠️ MySQL may already be running."

# 2. Start the Flask backend
echo "📡 Step 2: Starting local application server..."
python3 app.py &
BACKEND_PID=$!

# Cleanup logic to stop everything on Ctrl+C
trap "kill $BACKEND_PID; echo -e '\n🛑 Axiom Node Deactivated.'; exit" INT

echo "✅ AXIOM LOCAL MYSQL NODE IS LIVE."
echo "--------------------------------------------------"
echo "💻 Local Access:     http://127.0.0.1:5001"
echo "--------------------------------------------------"
echo "Press Ctrl+C to terminate the entire node."

wait
