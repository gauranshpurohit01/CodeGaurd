-- ============================================================================
-- SMART PHARMACY INVENTORY, BATCH TRACKING & EXPIRY MANAGEMENT SYSTEM
-- File: 05_indexes.sql
-- Description: Query Performance Tuning: Composite B-Tree Indexes,
--              Filtered Partial Indexes, Foreign Key Indexes, and GIN Index.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. FEFO OPTIMIZATION: Partial Composite Index for Batch Dispensing
-- Filters out 0-stock and expired batches so the B-Tree index stays compact
-- and fits directly into buffer cache for O(log N) lookup during checkout.
-- ----------------------------------------------------------------------------
DROP INDEX IF EXISTS idx_batch_fefo_active;
CREATE INDEX idx_batch_fefo_active
    ON batch (medicine_id, expiry_date ASC, batch_id ASC)
    INCLUDE (quantity_available, selling_price)
    WHERE quantity_available > 0 AND status IN ('ACTIVE', 'NEAR_EXPIRY');

-- ----------------------------------------------------------------------------
-- 2. EXPIRY MONITORING: Partial Index for Daily Expiry Audit & Quarantine
-- Evaluates only batches with positive stock to accelerate daily quarantine sweeps.
-- ----------------------------------------------------------------------------
DROP INDEX IF EXISTS idx_batch_expiry_monitoring;
CREATE INDEX idx_batch_expiry_monitoring
    ON batch (expiry_date ASC)
    WHERE quantity_available > 0;

-- ----------------------------------------------------------------------------
-- 3. FOREIGN KEY & JOIN INDEXES (Eliminates Sequential Scans on Relational Joins)
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_batch_supplier_id
    ON batch (supplier_id);

CREATE INDEX IF NOT EXISTS idx_batch_rack_id
    ON batch (rack_id);

CREATE INDEX IF NOT EXISTS idx_medicine_category
    ON medicine (category_id);

CREATE INDEX IF NOT EXISTS idx_medicine_manufacturer
    ON medicine (manufacturer_id);

CREATE INDEX IF NOT EXISTS idx_sales_order_item_order_id
    ON sales_order_item (order_id);

CREATE INDEX IF NOT EXISTS idx_sales_order_item_batch_id
    ON sales_order_item (batch_id);

CREATE INDEX IF NOT EXISTS idx_sales_order_item_medicine_id
    ON sales_order_item (medicine_id);

CREATE INDEX IF NOT EXISTS idx_sales_order_customer_id
    ON sales_order (customer_id);

CREATE INDEX IF NOT EXISTS idx_sales_order_timestamp
    ON sales_order (sale_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_inv_trans_batch_id
    ON inventory_transaction (batch_id);

CREATE INDEX IF NOT EXISTS idx_inv_trans_med_time
    ON inventory_transaction (medicine_id, transaction_time DESC);

CREATE INDEX IF NOT EXISTS idx_prescription_customer
    ON prescription (customer_id);

CREATE INDEX IF NOT EXISTS idx_prescription_doctor
    ON prescription (doctor_id);

-- ----------------------------------------------------------------------------
-- 4. GIN INDEX FOR AUDIT LOG (JSONB Fast Searching)
-- Allows indexing internal keys within the JSON payload of changes.
-- ----------------------------------------------------------------------------
DROP INDEX IF EXISTS idx_audit_log_new_data_gin;
CREATE INDEX idx_audit_log_new_data_gin
    ON audit_log USING GIN (new_data);

DROP INDEX IF EXISTS idx_audit_log_table_time;
CREATE INDEX idx_audit_log_table_time
    ON audit_log (table_name, changed_at DESC);
