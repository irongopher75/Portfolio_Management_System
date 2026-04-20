#!/bin/bash

# AXIOM Terminal: Institutional Deployment Sequence
# Stable boot: MySQL -> Gunicorn -> LocalTunnel

set -euo pipefail

export PATH="/opt/homebrew/bin:$PATH"

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="$APP_DIR/.axiom-runtime"
mkdir -p "$RUNTIME_DIR"

PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
NPX_BIN="${NPX_BIN:-$(command -v npx)}"
HEALTH_URL="http://127.0.0.1:5001/healthz"
SUBDOMAIN="${LOCALTUNNEL_SUBDOMAIN:-viva-axiom-terminal-v3}"
MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-Achieve@2026}"
DB_BACKEND="${DB_BACKEND:-mysql}"
BACKEND_LOG="$RUNTIME_DIR/gunicorn.log"
TUNNEL_LOG="$RUNTIME_DIR/localtunnel.log"
BACKEND_PID_FILE="$RUNTIME_DIR/gunicorn.pid"
TUNNEL_PID_FILE="$RUNTIME_DIR/localtunnel.pid"

cleanup() {
    if [ -f "$TUNNEL_PID_FILE" ]; then
        kill "$(cat "$TUNNEL_PID_FILE")" 2>/dev/null || true
        rm -f "$TUNNEL_PID_FILE"
    fi
    if [ -f "$BACKEND_PID_FILE" ]; then
        kill "$(cat "$BACKEND_PID_FILE")" 2>/dev/null || true
        rm -f "$BACKEND_PID_FILE"
    fi
}

trap 'cleanup; echo -e "\n🛑 Axiom Node Deactivated."; exit' INT TERM

echo "🚀 Initiating Axiom Institutional Terminal Recovery..."

echo "🧹 Cleaning stale runtime state..."
cleanup
lsof -ti:5001 | xargs kill -9 2>/dev/null || true
pkill -f "localtunnel --port 5001" 2>/dev/null || true
pkill -f "node.*localtunnel" 2>/dev/null || true

echo "📦 Step 1: Starting local MySQL service..."
brew services start mysql 2>/dev/null || echo "⚠️ MySQL Service: Active"

echo "⏳ Step 2: Waiting for local MySQL readiness..."
MYSQL_RETRIES=20
MYSQL_COUNT=0
until mysqladmin -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" ping >/dev/null 2>&1; do
    sleep 1
    MYSQL_COUNT=$((MYSQL_COUNT + 1))
    if [ "$MYSQL_COUNT" -ge "$MYSQL_RETRIES" ]; then
        echo "❌ Critical Error: MySQL is not reachable on ${MYSQL_HOST}:${MYSQL_PORT}."
        echo "   Check the MySQL service and credentials in your environment."
        exit 1
    fi
done
echo "✅ MySQL Ready"

echo "📡 Step 3: Launching Production WSGI Server (Gunicorn)..."
: > "$BACKEND_LOG"
cd "$APP_DIR"
"$PYTHON_BIN" -m gunicorn -c gunicorn.conf.py app:app >>"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$BACKEND_PID_FILE"

echo "⏳ Step 4: Waiting for Node Readiness..."
MAX_RETRIES=30
COUNT=0
while ! curl -fsS "$HEALTH_URL" >/dev/null; do
    sleep 1
    COUNT=$((COUNT + 1))
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "❌ Critical Error: Gunicorn exited before the health check passed."
        echo "   See log: $BACKEND_LOG"
        tail -n 40 "$BACKEND_LOG" || true
        exit 1
    fi
    if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
        echo "❌ Critical Error: Node failed to initialize within 30 seconds."
        echo "   See log: $BACKEND_LOG"
        tail -n 40 "$BACKEND_LOG" || true
        exit 1
    fi
done
echo "✅ Node Ready (Handshake Success)"

echo "🌐 Step 5: Establishing Public Tunnel (LocalTunnel)..."
: > "$TUNNEL_LOG"
# Self-healing Watchdog Loop for LocalTunnel
(
    while true; do
        echo "[$(date)] Launching Tunnel Bridge..." >> "$TUNNEL_LOG"
        "$NPX_BIN" localtunnel --port 5001 --subdomain "$SUBDOMAIN" >>"$TUNNEL_LOG" 2>&1
        echo "[$(date)] Tunnel Crashed. Restarting in 3s..." >> "$TUNNEL_LOG"
        sleep 3
    done
) &
TUNNEL_WATCHDOG_PID=$!
echo "$TUNNEL_WATCHDOG_PID" > "$TUNNEL_PID_FILE"

echo "⏳ Step 6: Finalizing Multi-Node Handshake..."
TUNNEL_RETRIES=20
TUNNEL_COUNT=0
PUBLIC_URL=""
while [ -z "$PUBLIC_URL" ]; do
    sleep 1
    TUNNEL_COUNT=$((TUNNEL_COUNT + 1))
    PUBLIC_URL="$(awk '/your url is: / {print $4}' "$TUNNEL_LOG" | tail -n 1)"
    if [ "$TUNNEL_COUNT" -ge "$TUNNEL_RETRIES" ] && [ -z "$PUBLIC_URL" ]; then
        echo "❌ Critical Error: LocalTunnel did not publish a URL in time."
        tail -n 40 "$TUNNEL_LOG" || true
        exit 1
    fi
done

echo "✅ AXIOM INSTITUTIONAL NODE IS DEPLOYED."
echo "--------------------------------------------------"
echo "💻 Local Access:      http://127.0.0.1:5001"
echo "🌍 Global Node:       $PUBLIC_URL"
echo "📝 Backend Log:       $BACKEND_LOG"
echo "📝 Tunnel Log:        $TUNNEL_LOG"
echo "--------------------------------------------------"
echo "Press Ctrl+C to terminate the entire system."

# ⏳ Step 7: Public Handshake Verification
echo "⏳ Verifying global node connectivity..."
MAX_RETRIES=10
COUNT=0
while [ $COUNT -lt $MAX_RETRIES ]; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://${SUBDOMAIN}.loca.lt)
    if [ "$HTTP_CODE" -eq "200" ] || [ "$HTTP_CODE" -eq "302" ]; then
        echo "✅ Global Handshake SUCCESS (HTTP $HTTP_CODE)"
        break
    fi
    echo "   ... waiting for relay server ($COUNT/$MAX_RETRIES)"
    sleep 3
    COUNT=$((COUNT+1))
done

if [ $COUNT -eq $MAX_RETRIES ]; then
    echo "⚠️  Warning: Global node is taking longer than usual to sync. Check logs/Tunnel."
fi

wait "$BACKEND_PID" "$TUNNEL_WATCHDOG_PID"
