-- ============================================================================
-- SMART PHARMACY INVENTORY, BATCH TRACKING & EXPIRY MANAGEMENT SYSTEM
-- File: init_all.sql
-- Description: Master bootstrap script to initialize the entire database
--              in proper sequence in PostgreSQL.
-- ============================================================================

\echo '---------------------------------------------------------'
\echo 'INITIALIZING SMART PHARMACY DBMS SYSTEM IN POSTGRESQL'
\echo '---------------------------------------------------------'

\echo '1. Executing 01_schema.sql (Tables, PK/FK Constraints, ENUMs)...'
\i sql/01_schema.sql

\echo '2. Executing 02_triggers.sql (Audit, Business Rules, Stock Sync)...'
\i sql/02_triggers.sql

\echo '3. Executing 03_procedures.sql (FEFO Engine, Quarantine, Reorder)...'
\i sql/03_procedures.sql

\echo '4. Executing 04_views.sql (Dashboard, Risk Radar, Materialized View)...'
\i sql/04_views.sql

\echo '5. Executing 05_indexes.sql (B-Tree, Partial FEFO Index, GIN Index)...'
\i sql/05_indexes.sql

\echo '6. Executing 06_seed_data.sql (Realistic Formulations & Batches)...'
\i sql/06_seed_data.sql

\echo '7. Executing 08_rbac_security.sql (Roles, CLS & Grants)...'
\i sql/08_rbac_security.sql

\echo '---------------------------------------------------------'
\echo 'DATABASE INITIALIZATION COMPLETED SUCCESSFULLY!'
\echo '---------------------------------------------------------'
