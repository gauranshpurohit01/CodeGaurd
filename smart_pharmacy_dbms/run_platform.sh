#!/usr/bin/env bash
# ============================================================================
# Smart Pharmacy Inventory & Batch Tracking Platform - One-Click Launcher
# ============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=================================================================="
echo " Starting Smart Pharmacy DBMS Web Platform                       "
echo "=================================================================="

# Detect psql binary
PSQL_CMD=""
for bin in "/opt/homebrew/bin/psql" "/usr/local/bin/psql" "$(which psql 2>/dev/null)"; do
    if [ -x "$bin" ]; then
        PSQL_CMD="$bin"
        break
    fi
done

if [ -n "$PSQL_CMD" ]; then
    echo "[+] Detected local PostgreSQL: $PSQL_CMD"
    # Ensure database exists
    "$PSQL_CMD" -lqt | cut -d \| -f 1 | grep -qw pharmacy_db || createdb pharmacy_db 2>/dev/null || true

    # Seed the database using the self-contained standalone SQL file
    echo "[+] Loading master schema, PL/pgSQL procedures, triggers, and full seed data..."
    "$PSQL_CMD" -d pharmacy_db < standalone_pharmacy_db.sql
    echo "[✓] Database populated with full multi-tier pharmaceutical data!"
fi

echo ""
echo "[+] Starting Web Platform at http://localhost:8080 ..."
echo "[+] Opening platform in your web browser..."

# Open browser in background after 1 second
(sleep 1.5 && (open "http://localhost:8080" 2>/dev/null || xdg-open "http://localhost:8080" 2>/dev/null || true)) &

# Launch python server
python3 web/server.py
