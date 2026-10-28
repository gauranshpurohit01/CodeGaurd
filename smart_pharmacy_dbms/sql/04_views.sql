-- ============================================================================
-- SMART PHARMACY INVENTORY, BATCH TRACKING & EXPIRY MANAGEMENT SYSTEM
-- File: 04_views.sql
-- Description: Standard Views, Secure Views, and PostgreSQL Materialized View
--              for Dashboard Analytics, Expiry Risk Radar, and Financials.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- VIEW 1: Detailed Batch Inventory with Real-Time Aging and Physical Location
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_batch_inventory_details AS
SELECT
    b.batch_id,
    b.batch_number,
    m.medicine_id,
    m.brand_name,
    m.generic_name,
    m.dosage_form,
    m.strength,
    c.category_name,
    s.supplier_name,
    r.zone || '-' || r.rack_number || '-' || r.shelf_number AS physical_shelf,
    r.temp_zone,
    b.mfg_date,
    b.expiry_date,
    (b.expiry_date - CURRENT_DATE) AS days_until_expiry,
    b.quantity_received,
    b.quantity_available,
    ROUND((b.quantity_available::NUMERIC / b.quantity_received::NUMERIC) * 100, 1) AS stock_retention_pct,
    b.purchase_cost,
    b.selling_price,
    ROUND(b.quantity_available * b.purchase_cost, 2) AS inventory_value_at_cost,
    ROUND(b.quantity_available * b.selling_price, 2) AS potential_retail_value,
    b.status
FROM batch b
JOIN medicine m ON b.medicine_id = m.medicine_id
JOIN category c ON m.category_id = c.category_id
JOIN supplier s ON b.supplier_id = s.supplier_id
JOIN rack_location r ON b.rack_id = r.rack_id;


-- ----------------------------------------------------------------------------
-- VIEW 2: Expiry Risk Radar (Multi-Tier Urgency Matrix for Pharmacists)
-- Identifies batches at immediate risk of financial loss or clinical danger.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_expiry_risk_radar AS
SELECT
    b.batch_id,
    b.batch_number,
    m.brand_name,
    m.generic_name,
    b.expiry_date,
    (b.expiry_date - CURRENT_DATE) AS days_remaining,
    b.quantity_available,
    ROUND(b.quantity_available * b.purchase_cost, 2) AS capital_at_risk_inr,
    CASE
        WHEN b.expiry_date <= CURRENT_DATE THEN 'CRITICAL: ALREADY EXPIRED (QUARANTINE IMMEDIATELY)'
        WHEN b.expiry_date <= CURRENT_DATE + INTERVAL '30 days' THEN 'URGENT: EXPIRES IN <30 DAYS (DISCOUNT / FEFO PRIORITIZE)'
        WHEN b.expiry_date <= CURRENT_DATE + INTERVAL '60 days' THEN 'WARNING: EXPIRES IN 31-60 DAYS (MONITOR CLOSELY)'
        WHEN b.expiry_date <= CURRENT_DATE + INTERVAL '90 days' THEN 'ATTENTION: EXPIRES IN 61-90 DAYS'
        ELSE 'NORMAL: STABLE SHELF LIFE (>90 DAYS)'
    END AS risk_urgency_tier,
    r.zone || '-' || r.rack_number AS rack_location,
    s.supplier_name
FROM batch b
JOIN medicine m ON b.medicine_id = m.medicine_id
JOIN rack_location r ON b.rack_id = r.rack_id
JOIN supplier s ON b.supplier_id = s.supplier_id
WHERE b.quantity_available > 0 OR b.status = 'EXPIRED'
ORDER BY b.expiry_date ASC;


-- ----------------------------------------------------------------------------
-- VIEW 3: Medicine Formulary Consolidated Stock Overview
-- Aggregates stock across batches, computes earliest expiry, and checks reorders.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_medicine_stock_overview AS
SELECT
    m.medicine_id,
    m.brand_name,
    m.generic_name,
    c.category_name,
    m.dosage_form,
    m.strength,
    m.reorder_level,
    m.target_stock_level,
    COALESCE(SUM(b.quantity_available) FILTER (WHERE b.expiry_date > CURRENT_DATE AND b.status IN ('ACTIVE', 'NEAR_EXPIRY')), 0) AS total_usable_stock,
    COALESCE(SUM(b.quantity_available) FILTER (WHERE b.expiry_date <= CURRENT_DATE), 0) AS expired_stock_on_shelf,
    COUNT(b.batch_id) FILTER (WHERE b.quantity_available > 0 AND b.expiry_date > CURRENT_DATE) AS active_batch_count,
    MIN(b.expiry_date) FILTER (WHERE b.quantity_available > 0 AND b.expiry_date > CURRENT_DATE) AS next_expiring_batch_date,
    CASE
        WHEN COALESCE(SUM(b.quantity_available) FILTER (WHERE b.expiry_date > CURRENT_DATE), 0) = 0 THEN 'OUT_OF_STOCK'
        WHEN COALESCE(SUM(b.quantity_available) FILTER (WHERE b.expiry_date > CURRENT_DATE), 0) <= m.reorder_level THEN 'REORDER_REQUIRED'
        WHEN COALESCE(SUM(b.quantity_available) FILTER (WHERE b.expiry_date > CURRENT_DATE), 0) > m.target_stock_level THEN 'OVERSTOCKED'
        ELSE 'ADEQUATE'
    END AS stock_status
FROM medicine m
JOIN category c ON m.category_id = c.category_id
LEFT JOIN batch b ON m.medicine_id = b.medicine_id
GROUP BY m.medicine_id, m.brand_name, m.generic_name, c.category_name, m.dosage_form, m.strength, m.reorder_level, m.target_stock_level;


-- ----------------------------------------------------------------------------
-- VIEW 4: Full Audit Trail of Drug Movements (Sales, Receipts, Disposals)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_inventory_audit_trail AS
SELECT
    it.transaction_id,
    it.transaction_time,
    it.transaction_type,
    m.brand_name,
    m.generic_name,
    b.batch_number,
    b.expiry_date,
    it.quantity_change,
    it.balance_after,
    it.reference_code,
    it.performed_by,
    it.remarks
FROM inventory_transaction it
JOIN medicine m ON it.medicine_id = m.medicine_id
JOIN batch b ON it.batch_id = b.batch_id
ORDER BY it.transaction_id DESC;


-- ----------------------------------------------------------------------------
-- MATERIALIZED VIEW: Monthly Sales, Revenue, COGS, and Expiry Loss Analytics
-- Demonstrates PostgreSQL OLAP capabilities & performance acceleration.
-- ----------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_monthly_pharmacy_financials;
CREATE MATERIALIZED VIEW mv_monthly_pharmacy_financials AS
WITH monthly_sales AS (
    SELECT
        DATE_TRUNC('month', so.sale_timestamp)::DATE AS sales_month,
        COUNT(DISTINCT so.order_id)                   AS total_invoices_issued,
        SUM(soi.quantity)                             AS total_units_sold,
        SUM(soi.line_total)                           AS gross_sales_revenue,
        SUM(soi.quantity * b.purchase_cost)           AS total_cogs,
        SUM(so.tax_amount)                            AS total_gst_collected,
        SUM(so.discount_amount)                       AS total_discounts_granted,
        SUM(so.total_amount)                          AS net_revenue_received
    FROM sales_order so
    JOIN sales_order_item soi ON so.order_id = soi.order_id
    JOIN batch b ON soi.batch_id = b.batch_id
    GROUP BY DATE_TRUNC('month', so.sale_timestamp)::DATE
),
monthly_expiry_losses AS (
    SELECT
        DATE_TRUNC('month', disposal_date)::DATE AS disposal_month,
        COUNT(disposal_id)                       AS disposal_events,
        SUM(disposed_quantity)                   AS expired_units_destroyed,
        SUM(loss_amount_inr)                     AS total_expiry_loss_inr
    FROM quarantine_disposal_log
    GROUP BY DATE_TRUNC('month', disposal_date)::DATE
)
SELECT
    COALESCE(ms.sales_month, mel.disposal_month) AS financial_month,
    COALESCE(ms.total_invoices_issued, 0)        AS total_invoices,
    COALESCE(ms.total_units_sold, 0)             AS units_sold,
    COALESCE(ms.gross_sales_revenue, 0.00)       AS gross_sales_inr,
    COALESCE(ms.total_cogs, 0.00)                AS cogs_inr,
    ROUND(COALESCE(ms.gross_sales_revenue, 0.00) - COALESCE(ms.total_cogs, 0.00), 2) AS gross_profit_inr,
    CASE
        WHEN COALESCE(ms.gross_sales_revenue, 0) > 0
        THEN ROUND(((ms.gross_sales_revenue - ms.total_cogs) / ms.gross_sales_revenue) * 100, 2)
        ELSE 0.00
    END AS gross_margin_percentage,
    COALESCE(mel.expired_units_destroyed, 0)     AS units_expired,
    COALESCE(mel.total_expiry_loss_inr, 0.00)    AS expiry_write_off_inr,
    ROUND(
        (COALESCE(ms.gross_sales_revenue, 0.00) - COALESCE(ms.total_cogs, 0.00)) - COALESCE(mel.total_expiry_loss_inr, 0.00),
        2
    ) AS net_operational_margin_inr
FROM monthly_sales ms
FULL OUTER JOIN monthly_expiry_losses mel ON ms.sales_month = mel.disposal_month
ORDER BY financial_month DESC;

-- Unique index required to enable CONCURRENT refresh of the materialized view
CREATE UNIQUE INDEX idx_mv_monthly_fin_month ON mv_monthly_pharmacy_financials(financial_month);

-- Stored procedure to refresh the materialized view
CREATE OR REPLACE PROCEDURE sp_refresh_financial_analytics()
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_pharmacy_financials;
    RAISE NOTICE 'Materialized view mv_monthly_pharmacy_financials successfully refreshed.';
END;
$$ LANGUAGE plpgsql;
