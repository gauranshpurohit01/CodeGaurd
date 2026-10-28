-- ============================================================================
-- SMART PHARMACY INVENTORY, BATCH TRACKING & EXPIRY MANAGEMENT SYSTEM
-- File: 08_rbac_security.sql
-- Description: Role-Based Access Control (RBAC), Column-Level Security (CLS),
--              and Principle of Least Privilege in PostgreSQL.
-- ============================================================================

-- Clean up existing roles if any
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'pharmacy_dba') THEN
        DROP ROLE pharmacy_dba;
    END IF;
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'lead_pharmacist') THEN
        DROP ROLE lead_pharmacist;
    END IF;
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'pharmacy_cashier') THEN
        DROP ROLE pharmacy_cashier;
    END IF;
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'inventory_clerk') THEN
        DROP ROLE inventory_clerk;
    END IF;
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'compliance_auditor') THEN
        DROP ROLE compliance_auditor;
    END IF;
END
$$;

-- ----------------------------------------------------------------------------
-- 1. DEFINE APPLICATION ROLES
-- ----------------------------------------------------------------------------
CREATE ROLE pharmacy_dba WITH LOGIN SUPERUSER PASSWORD 'dba_secure_pass';
CREATE ROLE lead_pharmacist WITH LOGIN PASSWORD 'pharma_secure_pass';
CREATE ROLE pharmacy_cashier WITH LOGIN PASSWORD 'cashier_secure_pass';
CREATE ROLE inventory_clerk WITH LOGIN PASSWORD 'clerk_secure_pass';
CREATE ROLE compliance_auditor WITH LOGIN PASSWORD 'auditor_secure_pass';

-- ----------------------------------------------------------------------------
-- 2. GRANT PRIVILEGES TO LEAD PHARMACIST
-- Can dispense drugs, execute quarantine, add inward batches, manage prescriptions
-- ----------------------------------------------------------------------------
GRANT USAGE ON SCHEMA public TO lead_pharmacist;
GRANT SELECT, INSERT, UPDATE ON medicine, batch, customer, doctor, prescription, prescription_item TO lead_pharmacist;
GRANT SELECT, INSERT ON sales_order, sales_order_item, inventory_transaction, quarantine_disposal_log TO lead_pharmacist;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO lead_pharmacist;
GRANT EXECUTE ON PROCEDURE sp_dispense_medicine_fefo, sp_quarantine_expired_batches, sp_receive_inward_batch TO lead_pharmacist;
GRANT EXECUTE ON FUNCTION fn_get_reorder_recommendations TO lead_pharmacist;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO lead_pharmacist;

-- ----------------------------------------------------------------------------
-- 3. GRANT PRIVILEGES TO CASHIER (Strict Principle of Least Privilege)
-- Cashiers create sales orders and query medicines.
-- They CANNOT change batch stock manually, cannot delete invoices, and
-- CANNOT see wholesale purchase cost (Column-Level Security).
-- ----------------------------------------------------------------------------
GRANT USAGE ON SCHEMA public TO pharmacy_cashier;
-- Table level selects
GRANT SELECT ON medicine, category, rack_location, customer, doctor, prescription, prescription_item TO pharmacy_cashier;
GRANT SELECT, INSERT ON sales_order, sales_order_item TO pharmacy_cashier;
GRANT USAGE, SELECT ON SEQUENCE sales_order_order_id_seq, sales_order_item_item_id_seq TO pharmacy_cashier;

-- Column-Level Security (CLS): Cashier CAN see selling_price & mrp, but NOT purchase_cost!
REVOKE SELECT ON batch FROM pharmacy_cashier;
GRANT SELECT (batch_id, medicine_id, batch_number, expiry_date, mrp, selling_price, quantity_available, status, rack_id)
    ON batch TO pharmacy_cashier;

-- Cashiers execute dispensing procedure
GRANT EXECUTE ON PROCEDURE sp_dispense_medicine_fefo TO pharmacy_cashier;

-- ----------------------------------------------------------------------------
-- 4. GRANT PRIVILEGES TO INVENTORY CLERK
-- Receives physical stock, handles rack allocations, monitors near-expiry
-- ----------------------------------------------------------------------------
GRANT USAGE ON SCHEMA public TO inventory_clerk;
GRANT SELECT ON medicine, category, supplier, manufacturer, rack_location TO inventory_clerk;
GRANT SELECT, INSERT ON batch, inventory_transaction TO inventory_clerk;
GRANT UPDATE (rack_id) ON batch TO inventory_clerk;
GRANT EXECUTE ON PROCEDURE sp_receive_inward_batch TO inventory_clerk;
GRANT USAGE, SELECT ON SEQUENCE batch_batch_id_seq, inventory_transaction_transaction_id_seq TO inventory_clerk;

-- ----------------------------------------------------------------------------
-- 5. GRANT PRIVILEGES TO COMPLIANCE AUDITOR
-- Read-Only auditor role for inspection and regulatory compliance
-- ----------------------------------------------------------------------------
GRANT USAGE ON SCHEMA public TO compliance_auditor;
GRANT SELECT ON audit_log, inventory_transaction, quarantine_disposal_log, v_inventory_audit_trail, v_expiry_risk_radar TO compliance_auditor;
