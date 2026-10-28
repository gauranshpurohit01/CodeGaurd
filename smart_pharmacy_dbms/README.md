# Smart Pharmacy Inventory, Batch Tracking & Expiry Management System
A Comprehensive Database-Centric Management System Built on PostgreSQL 16+.

Designed for DBMS Academic Projects, Laboratory Evaluations, and Viva Voce Presentations.

---

## 📁 Project Structure

```
smart_pharmacy_dbms/
├── sql/
│   ├── 01_schema.sql               # Tables, PK/FK constraints, custom ENUMs, 3NF/BCNF
│   ├── 02_triggers.sql             # Business rule validation, audit logs, stock sync
│   ├── 03_procedures.sql           # FEFO dispensing engine, quarantine disposal, reorder
│   ├── 04_views.sql                # Expiry risk radar, stock views, Materialized View
│   ├── 05_indexes.sql              # B-Tree, partial composite FEFO indexes, GIN index
│   ├── 06_seed_data.sql            # Realistic medications, multi-tier batches, orders
│   ├── 07_analytical_queries.sql   # 7 advanced DBMS queries (Window functions, CTEs, ROLLUP)
│   ├── 08_rbac_security.sql        # Roles, grants, and Column-Level Security (CLS)
│   └── 09_transactions_demo.sql    # ACID transaction verification and savepoints
├── init_all.sql                    # Master SQL bootstrap file
├── docker-compose.yml              # PostgreSQL 16 container definition with auto-init
├── setup.sh                        # One-click startup & verification script
├── demo_runner.py                  # Interactive CLI demonstration tool for Viva
├── DBMS_PROJECT_REPORT.md          # Full academic documentation with ER Diagram & proofs
├── VIVA_DEFENSE_GUIDE.md           # Frequently asked professor questions & technical answers
└── README.md                       # This file
```

---

## 🚀 Quick Start Guide

### Option 1: Running with Docker (Recommended)
1. Start Docker Desktop on your machine.
2. From this directory, start the PostgreSQL container:
   ```bash
   ./setup.sh
   # or manually:
   docker-compose up -d
   ```
   PostgreSQL will automatically load and initialize all files in `sql/` in proper alphabetical order (`01_` through `08_`).

3. Open the interactive demonstration CLI:
   ```bash
   python3 demo_runner.py
   ```

4. Or connect directly to PostgreSQL shell:
   ```bash
   docker exec -it pharmacy_dbms_pg psql -U postgres -d pharmacy_db
   ```

---

### Option 2: Running with Local or Cloud PostgreSQL (psql / pgAdmin)
If you already have PostgreSQL installed locally or on cloud (e.g. Neon, Supabase, AWS RDS):
1. Create a database:
   ```sql
   CREATE DATABASE pharmacy_db;
   ```
2. Run the master initialization script:
   ```bash
   psql -U <your_username> -d pharmacy_db -f init_all.sql
   ```
3. Run the analytical queries:
   ```bash
   psql -U <your_username> -d pharmacy_db -f sql/07_analytical_queries.sql
   ```

---

## 🎯 Key Academic Highlights to Show Your Professor

1. **FEFO (First-Expired, First-Out) Dispensing Algorithm**:
   - Implemented in PL/pgSQL (`sp_dispense_medicine_fefo`).
   - Automatically prioritizes batches with the closest expiry date.
   - Solves the split-batch fulfillment problem and uses `SELECT ... FOR UPDATE` row locks to prevent race conditions.

2. **Patient Safety Triggers**:
   - `trg_prevent_expired_dispense`: Aborts transaction immediately if an expired or quarantined batch is selected for checkout.
   - `trg_auto_deduct_batch_stock`: Synchronously decrements stock and appends immutable audit records into `inventory_transaction`.
   - `trg_recalculate_order_totals`: Recalculates subtotal, 5% GST, and net total dynamically.

3. **Multi-Tier Expiry Risk Radar (`v_expiry_risk_radar`)**:
   - Classifies drugs into Critical ($\le 0$ days), Urgent ($<30$ days), Warning ($31-60$ days), Attention ($61-90$ days), and Safe ($>90$ days).

4. **Performance Tuning & Partial Indexing**:
   - Uses a filtered partial index:
     `CREATE INDEX idx_batch_fefo_active ON batch (...) WHERE quantity_available > 0 AND status IN ('ACTIVE', 'NEAR_EXPIRY');`
   - Keeps the index compact and resident in RAM buffer cache for $O(\log N)$ point-of-sale response.

5. **Materialized View with Non-Blocking Refresh**:
   - `mv_monthly_pharmacy_financials` caches revenue, COGS, and write-off losses.
   - Refreshed concurrently via `sp_refresh_financial_analytics()`.

6. **Column-Level Security (CLS)**:
   - Cashiers can view retail selling prices and MRPs, but cannot see sensitive wholesale purchase costs (`purchase_cost`).

---

## 📚 Documentation & Viva Preparation
- Read [`DBMS_PROJECT_REPORT.md`](file:///Users/gauranshpurohit/Downloads/cdproj/smart_pharmacy_dbms/DBMS_PROJECT_REPORT.md) for the ER diagram, schema details, and normalization proofs.
- Read [`VIVA_DEFENSE_GUIDE.md`](file:///Users/gauranshpurohit/Downloads/cdproj/smart_pharmacy_dbms/VIVA_DEFENSE_GUIDE.md) for expected viva questions and answers.
