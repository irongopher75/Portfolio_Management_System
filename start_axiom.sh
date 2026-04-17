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

# 3. Start the Public Internet Bridge
echo "🌐 Step 3: Establishing Public Tunnel (Pulse Protocol)..."
# Pulse Protocol: ServerAliveInterval=60 sends a pulse every minute to keep the link alive
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -o ServerAliveCountMax=3 -R 80:localhost:5001 nokey@localhost.run &
TUNNEL_PID=$!

# Cleanup logic to stop everything on Ctrl+C
trap "kill $BACKEND_PID $TUNNEL_PID; echo -e '\n🛑 Axiom Node Deactivated.'; exit" INT

echo "✅ AXIOM NODE IS LIVE."
echo "--------------------------------------------------"
echo "💻 Local Access:  http://127.0.0.1:5001"
echo "📡 Public Access: (Wait for localhost.run to generate URL below)"
echo "--------------------------------------------------"
echo "Press Ctrl+C to terminate the entire node."

wait
