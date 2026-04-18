#!/bin/bash

# AXIOM Terminal: Unified Boot Sequence
# This script launches the DB, the Backend, and the Public Link.

echo "🚀 Initiating Axiom Institutional Terminal..."

# 1. Start MySQL (Logic for Homebrew/macOS)
echo "📦 Step 1: Syncing Database Ledger..."
brew services start mysql 2>/dev/null || echo "⚠️ MySQL may already be running."

# 2. Start the Flask Backend
echo "📡 Step 2: Initializing Handshake Protocol (Flask)..."
python3 app.py &
BACKEND_PID=$!

# 3. Start the Global Handshake Bridges
echo "🌐 Step 3: Establishing Dual-Pulse Handshake (Ports 5001 & 3306)..."

# Web Bridge (Port 5001)
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -o ServerAliveCountMax=3 -R 80:localhost:5001 nokey@localhost.run &
WEB_TUNNEL_PID=$!

# Database Bridge (Port 3306)
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -o ServerAliveCountMax=3 -R 80:localhost:3306 nokey@localhost.run &
DB_TUNNEL_PID=$!

# Cleanup logic to stop everything on Ctrl+C
trap "kill $BACKEND_PID $WEB_TUNNEL_PID $DB_TUNNEL_PID; echo -e '\n🛑 Axiom Node Deactivated.'; exit" INT

echo "✅ AXIOM DUAL-NODE IS LIVE."
echo "--------------------------------------------------"
echo "💻 Local Access:     http://127.0.0.1:5001"
echo "📡 Terminal Web UI:  (Check first URL below)"
echo "🗄️ Database Node:    (Check second URL below)"
echo "--------------------------------------------------"
echo "Press Ctrl+C to terminate the entire node."

wait
