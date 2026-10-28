-- ============================================================================
-- SMART PHARMACY INVENTORY, BATCH TRACKING & EXPIRY MANAGEMENT SYSTEM
-- File: 07_analytical_queries.sql
-- Description: Advanced DBMS Queries demonstrating Window Functions, CTEs,
--              ROLLUP / GROUPING SETS, JSONB querying, and Recursive Traceability.
--              (Ready to execute and present in Academic Project Viva).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- QUERY 1: FEFO Priority Matrix with Running Cumulative Balance
-- Demonstrates: WINDOW FUNCTIONS (ROW_NUMBER, SUM() OVER PARTITION BY)
-- Purpose: Shows cashier exactly which batch to pick first, second, and third,
--          and displays cumulative available quantity across batches.
-- ----------------------------------------------------------------------------
SELECT
    m.brand_name,
    m.generic_name,
    b.batch_number,
    b.expiry_date,
    (b.expiry_date - CURRENT_DATE) AS days_to_expiry,
    b.quantity_available AS batch_stock,
    -- FEFO Priority ranking: 1 is the batch that MUST be sold first!
    ROW_NUMBER() OVER (
        PARTITION BY m.medicine_id
        ORDER BY b.expiry_date ASC, b.batch_id ASC
    ) AS fefo_dispense_rank,
    -- Running cumulative sum of available inventory
    SUM(b.quantity_available) OVER (
        PARTITION BY m.medicine_id
        ORDER BY b.expiry_date ASC, b.batch_id ASC
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_stock_available
FROM medicine m
JOIN batch b ON m.medicine_id = b.medicine_id
WHERE b.expiry_date > CURRENT_DATE
  AND b.quantity_available > 0
ORDER BY m.brand_name, fefo_dispense_rank;


-- ----------------------------------------------------------------------------
-- QUERY 2: Regulatory Batch Recall & Patient Traceability (Clinical Safety)
-- Demonstrates: 5-Table INNER JOIN across clinical, sales, and batch entities.
-- Purpose: In case of drug contamination/recall, instantly find all patients,
--          prescribing doctors, and invoice timestamps for a specific batch.
-- ----------------------------------------------------------------------------
SELECT
    b.batch_number,
    m.brand_name,
    m.strength,
    so.invoice_number,
    so.sale_timestamp,
    c.full_name AS patient_name,
    c.phone AS patient_contact,
    d.doctor_name,
    d.hospital_name,
    soi.quantity AS units_consumed
FROM sales_order_item soi
JOIN batch b ON soi.batch_id = b.batch_id
JOIN medicine m ON soi.medicine_id = m.medicine_id
JOIN sales_order so ON soi.order_id = so.order_id
LEFT JOIN customer c ON so.customer_id = c.customer_id
LEFT JOIN prescription p ON so.prescription_id = p.prescription_id
LEFT JOIN doctor d ON p.doctor_id = d.doctor_id
WHERE b.batch_number = 'B-CRO-02' -- Replace with batch to recall
ORDER BY so.sale_timestamp DESC;


-- ----------------------------------------------------------------------------
-- QUERY 3: Supplier Quality & Expiry Loss Scorecard
-- Demonstrates: Common Table Expression (CTE), Aggregations, Percentage metrics
-- Purpose: Evaluates which wholesale suppliers provide stock that ends up expiring,
--          helping procurement negotiate better return policies.
-- ----------------------------------------------------------------------------
WITH supplier_metrics AS (
    SELECT
        s.supplier_id,
        s.supplier_name,
        COUNT(b.batch_id)                                           AS total_batches_supplied,
        SUM(b.quantity_received)                                    AS total_units_supplied,
        SUM(b.quantity_received * b.purchase_cost)                  AS total_procurement_val_inr,
        COALESCE(SUM(b.quantity_available) FILTER (WHERE b.expiry_date <= CURRENT_DATE), 0) AS expired_units_on_hand,
        COALESCE(SUM(b.quantity_available * b.purchase_cost) FILTER (WHERE b.expiry_date <= CURRENT_DATE), 0) AS expired_capital_loss_inr
    FROM supplier s
    LEFT JOIN batch b ON s.supplier_id = b.supplier_id
    GROUP BY s.supplier_id, s.supplier_name
)
SELECT
    supplier_name,
    total_batches_supplied,
    total_units_supplied,
    total_procurement_val_inr,
    expired_units_on_hand,
    expired_capital_loss_inr,
    CASE
        WHEN total_procurement_val_inr > 0
        THEN ROUND((expired_capital_loss_inr / total_procurement_val_inr) * 100, 2)
        ELSE 0.00
    END AS loss_percentage_rate
FROM supplier_metrics
ORDER BY expired_capital_loss_inr DESC;


-- ----------------------------------------------------------------------------
-- QUERY 4: Multidimensional Sales Revenue Aggregation (OLAP Cube/Rollup)
-- Demonstrates: GROUP BY ROLLUP across Category, Manufacturer, and Medicine
-- Purpose: Generates hierarchical subtotals and grand totals for financial reports.
-- ----------------------------------------------------------------------------
SELECT
    COALESCE(c.category_name, '--- ALL CATEGORIES ---')       AS category,
    COALESCE(mf.company_name, '--- ALL MANUFACTURERS ---')   AS manufacturer,
    COALESCE(m.brand_name, '--- ALL MEDICINES ---')          AS medicine,
    SUM(soi.quantity)                                        AS units_sold,
    ROUND(SUM(soi.line_total), 2)                            AS gross_revenue_inr
FROM sales_order_item soi
JOIN medicine m ON soi.medicine_id = m.medicine_id
JOIN category c ON m.category_id = c.category_id
JOIN manufacturer mf ON m.manufacturer_id = mf.manufacturer_id
GROUP BY ROLLUP (c.category_name, mf.company_name, m.brand_name)
ORDER BY c.category_name NULLS LAST, mf.company_name NULLS LAST, gross_revenue_inr DESC;


-- ----------------------------------------------------------------------------
-- QUERY 5: Days of Inventory Remaining (DOIR) & Stockout Forecaster
-- Demonstrates: CTE, Correlated Subqueries, Arithmetic date projecting
-- Purpose: Compares current active stock against daily consumption rate
--          to forecast exact stockout dates for critical antibiotics/drugs.
-- ----------------------------------------------------------------------------
WITH sales_velocity AS (
    SELECT
        soi.medicine_id,
        COALESCE(SUM(soi.quantity)::NUMERIC / 30.0, 1.0) AS avg_daily_burn_rate
    FROM sales_order_item soi
    JOIN sales_order so ON soi.order_id = so.order_id
    WHERE so.sale_timestamp >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY soi.medicine_id
),
active_stocks AS (
    SELECT
        medicine_id,
        SUM(quantity_available) AS total_usable_stock
    FROM batch
    WHERE expiry_date > CURRENT_DATE AND status IN ('ACTIVE', 'NEAR_EXPIRY')
    GROUP BY medicine_id
)
SELECT
    m.brand_name,
    m.generic_name,
    COALESCE(ast.total_usable_stock, 0) AS current_stock,
    ROUND(COALESCE(sv.avg_daily_burn_rate, 0.5), 2) AS units_sold_per_day,
    ROUND(COALESCE(ast.total_usable_stock, 0) / COALESCE(sv.avg_daily_burn_rate, 0.5), 1) AS days_inventory_remaining,
    (CURRENT_DATE + (COALESCE(ast.total_usable_stock, 0) / COALESCE(sv.avg_daily_burn_rate, 0.5))::INT) AS projected_stockout_date
FROM medicine m
LEFT JOIN active_stocks ast ON m.medicine_id = ast.medicine_id
LEFT JOIN sales_velocity sv ON m.medicine_id = sv.medicine_id
ORDER BY days_inventory_remaining ASC;


-- ----------------------------------------------------------------------------
-- QUERY 6: Near-Expiry Markdown & Clearance Revenue Simulator
-- Demonstrates: CASE statements, mathematical business modeling
-- Purpose: Simulates a 20% discount on batches expiring in <45 days.
--          Compares markdown recovery vs 100% total loss if expired unsold.
-- ----------------------------------------------------------------------------
SELECT
    m.brand_name,
    b.batch_number,
    b.expiry_date,
    (b.expiry_date - CURRENT_DATE) AS days_remaining,
    b.quantity_available,
    b.purchase_cost,
    b.selling_price AS regular_price,
    ROUND(b.selling_price * 0.80, 2) AS clearance_price_20pct_off,
    ROUND(b.quantity_available * b.purchase_cost, 2) AS potential_loss_if_expired,
    ROUND(b.quantity_available * (b.selling_price * 0.80), 2) AS clearance_recovery_revenue,
    ROUND((b.quantity_available * (b.selling_price * 0.80)) - (b.quantity_available * b.purchase_cost), 2) AS net_profit_under_clearance
FROM batch b
JOIN medicine m ON b.medicine_id = m.medicine_id
WHERE b.expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '45 days'
  AND b.quantity_available > 0
ORDER BY b.expiry_date ASC;


-- ----------------------------------------------------------------------------
-- QUERY 7: Querying JSONB Audit Logs for Master Data Modification History
-- Demonstrates: PostgreSQL JSONB containment (@>), arrow operators (->>), and filtering
-- Purpose: Extract who changed price or drug parameters and previous values.
-- ----------------------------------------------------------------------------
SELECT
    log_id,
    table_name,
    operation,
    record_id,
    changed_by,
    changed_at,
    old_data->>'batch_number' AS old_batch_number,
    old_data->>'selling_price' AS old_selling_price,
    new_data->>'selling_price' AS new_selling_price
FROM audit_log
WHERE table_name = 'batch'
ORDER BY changed_at DESC
LIMIT 10;
