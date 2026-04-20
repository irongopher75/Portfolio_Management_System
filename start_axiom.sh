#!/bin/bash

# AXIOM Terminal: Institutional Stabilization & Deployment Sequence
# This script implements the robust startup recommended for the Axiom Node.

set -u

# --- CONFIGURATION ---
PYTHON_BIN="/usr/local/bin/python3"
NPX_BIN="/opt/homebrew/bin/npx"
DEFAULT_PORT=5001
SUBDOMAIN="${LOCALTUNNEL_SUBDOMAIN:-axiom-terminal-stable-viva}"
HEALTH_URL="http://127.0.0.1:$DEFAULT_PORT/healthz"

# Logs
GUNICORN_LOG="gunicorn.log"
TUNNEL_LOG="localtunnel.log"

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

echo "🚀 Initiating Axiom Terminal Stabilization Sequence..."

# 1. Start MySQL
echo "📦 Step 1: Starting local MySQL service..."
brew services start mysql 2>/dev/null || echo "⚠️ MySQL Service: Active"

# 1b. Verify MySQL readiness
echo "⏳ Step 1b: Waiting for local MySQL readiness..."
MYSQL_RETRIES=20
MYSQL_COUNT=0
until mysqladmin -h 127.0.0.1 -P 3306 -u root -p"${MYSQL_PASSWORD:-Achieve@2026}" ping >/dev/null 2>&1; do
    sleep 1
    MYSQL_COUNT=$((MYSQL_COUNT+1))
    if [ "$MYSQL_COUNT" -ge "$MYSQL_RETRIES" ]; then
        echo "❌ Critical Error: MySQL is not reachable on 127.0.0.1:3306."
        exit 1
    fi
done
echo "✅ MySQL Ready"

# 2. Port Cleanup
echo "🧹 Step 2: Clearing Port $DEFAULT_PORT..."
lsof -ti:$DEFAULT_PORT | xargs kill -9 2>/dev/null || echo "✅ Port $DEFAULT_PORT: Clear"

# 3. Start Backend with Logging
echo "📡 Step 3: Launching Gunicorn with institutional logging..."
# Redirecting all app logs to gunicorn.log
"$PYTHON_BIN" -m gunicorn -c gunicorn.conf.py app:app > "$GUNICORN_LOG" 2>&1 &
BACKEND_PID=$!

# 4. Strict Health Check Loop
echo "⏳ Step 4: Waiting for Backend Node (Health Check: $HEALTH_URL)..."
MAX_RETRIES=45
COUNT=0
while true; do
    # Verify the process is still running
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "❌ Critical Error: Gunicorn process (PID: $BACKEND_PID) has crashed."
        echo "   Check $GUNICORN_LOG for stack traces."
        exit 1
    fi

    # Check for 200 OK
    STATUS_CODE=$(curl -o /dev/null -s -w "%{http_code}" "$HEALTH_URL")
    if [ "$STATUS_CODE" -eq 200 ]; then
        echo "✅ Institutional Node Handshake Success (200 OK)"
        break
    fi

    sleep 1
    COUNT=$((COUNT+1))
    if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
        echo "❌ Critical Error: Node failed to reach 'Ready' state within ${MAX_RETRIES}s."
        kill "$BACKEND_PID" 2>/dev/null || true
        exit 1
    fi
done

# 5. Launch Tunnel with Self-Healing Watchdog
echo "🌐 Step 5: Establishing Public Tunnel (subdomain: $SUBDOMAIN)..."
(
    while true; do
        echo "[$(date)] Launching Tunnel Bridge..." >> "$TUNNEL_LOG"
        "$NPX_BIN" localtunnel --port "$DEFAULT_PORT" --subdomain "$SUBDOMAIN" >> "$TUNNEL_LOG" 2>&1
        echo "[$(date)] Tunnel Crashed. Rebooting in 3s..." >> "$TUNNEL_LOG"
        sleep 3
    done
) &
TUNNEL_WATCHDOG_PID=$!

# Cleanup logic
trap "kill $BACKEND_PID $TUNNEL_WATCHDOG_PID 2>/dev/null; echo -e '\n🛑 Axiom Node Deactivated.'; exit" INT TERM

echo "✅ AXIOM INSTITUTIONAL NODE IS DEPLOYED."
echo "--------------------------------------------------"
echo "💻 Local Access:      $HEALTH_URL"
echo "🌍 Global Node:       https://${SUBDOMAIN}.loca.lt"
echo "📝 Logs (Backend):    cat $GUNICORN_LOG"
echo "📝 Logs (Tunnel):     cat $TUNNEL_LOG"
echo "--------------------------------------------------"
echo "Press Ctrl+C to terminate the entire system."

wait
