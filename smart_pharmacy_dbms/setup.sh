#!/usr/bin/env bash
# ============================================================================
# Smart Pharmacy Inventory & Batch Tracking DBMS - Setup & Verification Script
# ============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo " Smart Pharmacy Inventory & Batch Tracking (PostgreSQL)  "
echo "=========================================================="

if command -v docker >/dev/null 2>&1 && command -v docker-compose >/dev/null 2>&1; then
    echo "[+] Docker & Docker-Compose detected."
    echo "[+] Resetting any existing container state..."
    docker-compose down >/dev/null 2>&1 || true

    echo "[+] Starting PostgreSQL container on port 5433 (host) -> 5432 (container)..."
    docker-compose up -d

    echo "[+] Waiting for PostgreSQL to be ready..."
    until docker exec pharmacy_dbms_pg pg_isready -U postgres -d pharmacy_db > /dev/null 2>&1; do
        sleep 1
    done

    echo "[✓] PostgreSQL is ready and schema has been initialized!"
    echo ""
    echo "To connect to PostgreSQL interactive shell:"
    echo "  docker exec -it pharmacy_dbms_pg psql -U postgres -d pharmacy_db"
    echo ""
    echo "To run analytical queries:"
    echo "  docker exec -i pharmacy_dbms_pg psql -U postgres -d pharmacy_db < sql/07_analytical_queries.sql"
    echo ""
    echo "To launch interactive demo runner:"
    echo "  python3 demo_runner.py"
    echo "=========================================================="
else
    echo "[!] Docker not detected. If you have local PostgreSQL installed:"
    echo "  psql -U postgres -d pharmacy_db -f init_all.sql"
fi
