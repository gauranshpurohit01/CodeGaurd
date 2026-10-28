-- ============================================================================
-- SMART PHARMACY INVENTORY, BATCH TRACKING & EXPIRY MANAGEMENT SYSTEM
-- File: 01_schema.sql
-- Description: Core Relational Schema (DDL) with 3NF / BCNF Normalization,
--              Strict Integrity Constraints, Foreign Keys, and ENUMs.
-- ============================================================================

-- Clean slate initialization (in reverse dependency order)
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS quarantine_disposal_log CASCADE;
DROP TABLE IF EXISTS inventory_transaction CASCADE;
DROP TABLE IF EXISTS sales_order_item CASCADE;
DROP TABLE IF EXISTS sales_order CASCADE;
DROP TABLE IF EXISTS prescription_item CASCADE;
DROP TABLE IF EXISTS prescription CASCADE;
DROP TABLE IF EXISTS doctor CASCADE;
DROP TABLE IF EXISTS customer CASCADE;
DROP TABLE IF EXISTS batch CASCADE;
DROP TABLE IF EXISTS rack_location CASCADE;
DROP TABLE IF EXISTS medicine CASCADE;
DROP TABLE IF EXISTS manufacturer CASCADE;
DROP TABLE IF EXISTS supplier CASCADE;
DROP TABLE IF EXISTS category CASCADE;

DROP TYPE IF EXISTS batch_status_type CASCADE;
DROP TYPE IF EXISTS transaction_type_enum CASCADE;
DROP TYPE IF EXISTS payment_method_enum CASCADE;
DROP TYPE IF EXISTS disposal_reason_enum CASCADE;
DROP TYPE IF EXISTS temperature_zone_enum CASCADE;

-- ----------------------------------------------------------------------------
-- 1. CUSTOM TYPES & DOMAINS
-- ----------------------------------------------------------------------------
CREATE TYPE batch_status_type AS ENUM (
    'ACTIVE',          -- In shelf, available for dispensing
    'NEAR_EXPIRY',     -- Within alert window (e.g. <= 60 days)
    'EXPIRED',         -- Past expiry date, strictly forbidden to dispense
    'QUARANTINED',     -- Removed from shelf pending disposal or verification
    'DEPLETED'         -- 0 quantity available
);

CREATE TYPE transaction_type_enum AS ENUM (
    'PURCHASE_RECEIPT',
    'SALE_DISPENSE',
    'EXPIRED_DISPOSAL',
    'DAMAGE_WRITE_OFF',
    'MANUAL_CORRECTION',
    'CUSTOMER_RETURN',
    'SUPPLIER_RETURN'
);

CREATE TYPE payment_method_enum AS ENUM (
    'CASH',
    'CREDIT_CARD',
    'DEBIT_CARD',
    'UPI',
    'INSURANCE'
);

CREATE TYPE disposal_reason_enum AS ENUM (
    'EXPIRED',
    'TEMPERATURE_BREACH',
    'PHYSICALLY_DAMAGED',
    'BATCH_RECALLED'
);

CREATE TYPE temperature_zone_enum AS ENUM (
    'ROOM_TEMP',       -- 15°C to 25°C
    'REFRIGERATED',    -- 2°C to 8°C
    'DEEP_FREEZE'      -- Below -15°C
);

-- ----------------------------------------------------------------------------
-- 2. MASTER ENTITIES (Normalized)
-- ----------------------------------------------------------------------------

-- 2.1 Medicine Category (e.g., Antibiotics, Analgesics, Cardiovascular)
CREATE TABLE category (
    category_id         SERIAL PRIMARY KEY,
    category_name       VARCHAR(100) NOT NULL UNIQUE,
    description         TEXT,
    requires_refrig     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2.2 Suppliers (Vendors supplying stock)
CREATE TABLE supplier (
    supplier_id         SERIAL PRIMARY KEY,
    supplier_name       VARCHAR(150) NOT NULL,
    contact_person      VARCHAR(100),
    email               VARCHAR(120) NOT NULL UNIQUE,
    phone               VARCHAR(20) NOT NULL,
    drug_license_no     VARCHAR(50) NOT NULL UNIQUE,
    gstin               VARCHAR(15) UNIQUE,
    address             TEXT NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2.3 Drug Manufacturers (e.g., Pfizer, Sun Pharma, Cipla)
CREATE TABLE manufacturer (
    manufacturer_id     SERIAL PRIMARY KEY,
    company_name        VARCHAR(150) NOT NULL UNIQUE,
    country_of_origin   VARCHAR(80) NOT NULL DEFAULT 'India',
    contact_email       VARCHAR(120),
    website             VARCHAR(200),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2.4 Physical Storage Locations inside Pharmacy
CREATE TABLE rack_location (
    rack_id             SERIAL PRIMARY KEY,
    zone                VARCHAR(20) NOT NULL,          -- e.g. 'A', 'B', 'COLD_STORAGE'
    rack_number         VARCHAR(20) NOT NULL,          -- e.g. 'R-01'
    shelf_number        VARCHAR(20) NOT NULL,          -- e.g. 'S-03'
    temp_zone           temperature_zone_enum NOT NULL DEFAULT 'ROOM_TEMP',
    max_capacity_units  INTEGER NOT NULL CHECK (max_capacity_units > 0),
    CONSTRAINT uq_rack_zone_shelf UNIQUE (zone, rack_number, shelf_number)
);

-- 2.5 Master Drug Formulary / Medicine Catalog
CREATE TABLE medicine (
    medicine_id             SERIAL PRIMARY KEY,
    generic_name            VARCHAR(150) NOT NULL,
    brand_name              VARCHAR(150) NOT NULL,
    category_id             INTEGER NOT NULL REFERENCES category(category_id) ON DELETE RESTRICT,
    manufacturer_id         INTEGER NOT NULL REFERENCES manufacturer(manufacturer_id) ON DELETE RESTRICT,
    dosage_form             VARCHAR(50) NOT NULL,   -- e.g., 'Tablet', 'Syrup', 'Capsule', 'Vial'
    strength                VARCHAR(50) NOT NULL,   -- e.g., '500 mg', '250 mg / 5 ml'
    unit_of_measure         VARCHAR(20) NOT NULL DEFAULT 'Tablets', -- 'Tablets', 'Bottles', 'Vials'
    min_storage_temp_c      NUMERIC(4, 1) DEFAULT 15.0,
    max_storage_temp_c      NUMERIC(4, 1) DEFAULT 25.0,
    is_prescription_req     BOOLEAN NOT NULL DEFAULT FALSE,
    reorder_level           INTEGER NOT NULL DEFAULT 50 CHECK (reorder_level >= 0),
    target_stock_level      INTEGER NOT NULL DEFAULT 200 CHECK (target_stock_level >= reorder_level),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_medicine_identity UNIQUE (generic_name, brand_name, dosage_form, strength),
    CONSTRAINT chk_temp_range CHECK (min_storage_temp_c <= max_storage_temp_c)
);

-- ----------------------------------------------------------------------------
-- 3. BATCH INVENTORY & TRACKING ENTITY (Core of the System)
-- ----------------------------------------------------------------------------
CREATE TABLE batch (
    batch_id            SERIAL PRIMARY KEY,
    medicine_id         INTEGER NOT NULL REFERENCES medicine(medicine_id) ON DELETE RESTRICT,
    batch_number        VARCHAR(60) NOT NULL,
    supplier_id         INTEGER NOT NULL REFERENCES supplier(supplier_id) ON DELETE RESTRICT,
    rack_id             INTEGER NOT NULL REFERENCES rack_location(rack_id) ON DELETE RESTRICT,
    mfg_date            DATE NOT NULL,
    expiry_date         DATE NOT NULL,
    purchase_cost       NUMERIC(10, 2) NOT NULL CHECK (purchase_cost >= 0),
    mrp                 NUMERIC(10, 2) NOT NULL CHECK (mrp >= purchase_cost),
    selling_price       NUMERIC(10, 2) NOT NULL CHECK (selling_price >= purchase_cost AND selling_price <= mrp),
    quantity_received   INTEGER NOT NULL CHECK (quantity_received > 0),
    quantity_available  INTEGER NOT NULL CHECK (quantity_available >= 0),
    status              batch_status_type NOT NULL DEFAULT 'ACTIVE',
    received_date       DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_batch_medicine UNIQUE (medicine_id, batch_number),
    CONSTRAINT chk_expiry_after_mfg CHECK (expiry_date > mfg_date),
    CONSTRAINT chk_qty_consistency CHECK (quantity_available <= quantity_received)
);

-- ----------------------------------------------------------------------------
-- 4. CLINICAL & CUSTOMER ENTITIES
-- ----------------------------------------------------------------------------
CREATE TABLE customer (
    customer_id         SERIAL PRIMARY KEY,
    full_name           VARCHAR(120) NOT NULL,
    phone               VARCHAR(20) UNIQUE NOT NULL,
    email               VARCHAR(120),
    date_of_birth       DATE,
    gender              VARCHAR(10) CHECK (gender IN ('MALE', 'FEMALE', 'OTHER')),
    registered_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE doctor (
    doctor_id           SERIAL PRIMARY KEY,
    doctor_name         VARCHAR(120) NOT NULL,
    medical_reg_no      VARCHAR(50) NOT NULL UNIQUE,
    specialization      VARCHAR(100),
    hospital_name       VARCHAR(150),
    contact_phone       VARCHAR(20),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prescription (
    prescription_id     SERIAL PRIMARY KEY,
    rx_code             VARCHAR(50) NOT NULL UNIQUE,
    customer_id         INTEGER NOT NULL REFERENCES customer(customer_id) ON DELETE RESTRICT,
    doctor_id           INTEGER NOT NULL REFERENCES doctor(doctor_id) ON DELETE RESTRICT,
    prescribed_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_until         DATE NOT NULL,
    diagnosis_notes     TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_rx_validity CHECK (valid_until >= prescribed_date)
);

CREATE TABLE prescription_item (
    rx_item_id          SERIAL PRIMARY KEY,
    prescription_id     INTEGER NOT NULL REFERENCES prescription(prescription_id) ON DELETE CASCADE,
    medicine_id         INTEGER NOT NULL REFERENCES medicine(medicine_id) ON DELETE RESTRICT,
    dosage_instructions VARCHAR(150) NOT NULL, -- e.g. "1-0-1 after meals"
    quantity_prescribed INTEGER NOT NULL CHECK (quantity_prescribed > 0),
    refills_remaining   INTEGER NOT NULL DEFAULT 0 CHECK (refills_remaining >= 0),
    CONSTRAINT uq_rx_med UNIQUE (prescription_id, medicine_id)
);

-- ----------------------------------------------------------------------------
-- 5. SALES & DISPENSING ENTITIES
-- ----------------------------------------------------------------------------
CREATE TABLE sales_order (
    order_id            SERIAL PRIMARY KEY,
    invoice_number      VARCHAR(50) NOT NULL UNIQUE,
    customer_id         INTEGER REFERENCES customer(customer_id) ON DELETE SET NULL,
    prescription_id     INTEGER REFERENCES prescription(prescription_id) ON DELETE SET NULL,
    sale_timestamp      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payment_method      payment_method_enum NOT NULL DEFAULT 'CASH',
    subtotal            NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (subtotal >= 0),
    tax_amount          NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (tax_amount >= 0),
    discount_amount     NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (discount_amount >= 0),
    total_amount        NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (total_amount >= 0),
    dispensed_by        VARCHAR(50) NOT NULL DEFAULT CURRENT_USER
);

-- Sales order line item points to EXACT BATCH dispensed (for audit & recall)
CREATE TABLE sales_order_item (
    item_id             SERIAL PRIMARY KEY,
    order_id            INTEGER NOT NULL REFERENCES sales_order(order_id) ON DELETE CASCADE,
    batch_id            INTEGER NOT NULL REFERENCES batch(batch_id) ON DELETE RESTRICT,
    medicine_id         INTEGER NOT NULL REFERENCES medicine(medicine_id) ON DELETE RESTRICT,
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    unit_price          NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    line_total          NUMERIC(12, 2) GENERATED ALWAYS AS (ROUND(quantity * unit_price, 2)) STORED,
    CONSTRAINT uq_order_batch UNIQUE (order_id, batch_id)
);

-- ----------------------------------------------------------------------------
-- 6. IMMUTABLE INVENTORY TRANSACTION LEDGER (Audit & Traceability)
-- ----------------------------------------------------------------------------
CREATE TABLE inventory_transaction (
    transaction_id      BIGSERIAL PRIMARY KEY,
    batch_id            INTEGER NOT NULL REFERENCES batch(batch_id) ON DELETE RESTRICT,
    medicine_id         INTEGER NOT NULL REFERENCES medicine(medicine_id) ON DELETE RESTRICT,
    transaction_type    transaction_type_enum NOT NULL,
    quantity_change     INTEGER NOT NULL, -- negative for dispense/disposal, positive for receipt
    balance_after       INTEGER NOT NULL CHECK (balance_after >= 0),
    reference_code      VARCHAR(60),      -- e.g. invoice_number or disposal_cert_no
    remarks             TEXT,
    performed_by        VARCHAR(50) NOT NULL DEFAULT CURRENT_USER,
    transaction_time    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 7. QUARANTINE & HAZARDOUS / EXPIRED DISPOSAL LOG
-- ----------------------------------------------------------------------------
CREATE TABLE quarantine_disposal_log (
    disposal_id             SERIAL PRIMARY KEY,
    batch_id                INTEGER NOT NULL REFERENCES batch(batch_id) ON DELETE RESTRICT,
    disposed_quantity       INTEGER NOT NULL CHECK (disposed_quantity > 0),
    disposal_reason         disposal_reason_enum NOT NULL,
    destruction_method      VARCHAR(100) NOT NULL, -- 'High Temp Incineration', 'Chemical Inactivation'
    approved_by_pharmacist  VARCHAR(100) NOT NULL,
    certificate_number      VARCHAR(80) NOT NULL UNIQUE,
    loss_amount_inr         NUMERIC(12, 2) NOT NULL CHECK (loss_amount_inr >= 0),
    disposal_date           DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 8. SYSTEM-WIDE SECURITY & DATA AUDIT LOG
-- ----------------------------------------------------------------------------
CREATE TABLE audit_log (
    log_id              BIGSERIAL PRIMARY KEY,
    table_name          VARCHAR(60) NOT NULL,
    operation           VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    record_id           VARCHAR(50) NOT NULL,
    old_data            JSONB,
    new_data            JSONB,
    changed_by          VARCHAR(50) NOT NULL DEFAULT CURRENT_USER,
    changed_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- ============================================================================
-- SMART PHARMACY INVENTORY, BATCH TRACKING & EXPIRY MANAGEMENT SYSTEM
-- File: 02_triggers.sql
-- Description: PL/pgSQL Trigger Functions and Triggers enforcing Business
--              Rules, Auto-Calculations, Stock Updates, and Audit Logging.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TRIGGER 1: Batch Status Evaluator (Self-adjusting Status based on Expiry & Stock)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_evaluate_batch_status()
RETURNS TRIGGER AS $$
BEGIN
    -- If already manually marked quarantined, keep it quarantined
    IF NEW.status = 'QUARANTINED' THEN
        RETURN NEW;
    END IF;

    -- Rule 1: Past Expiry Date -> EXPIRED (Highest clinical priority)
    IF NEW.expiry_date <= CURRENT_DATE THEN
        NEW.status := 'EXPIRED';
    -- Rule 2: Out of Stock -> DEPLETED
    ELSIF NEW.quantity_available = 0 THEN
        NEW.status := 'DEPLETED';
    -- Rule 3: Within 60 days of Expiry -> NEAR_EXPIRY
    ELSIF NEW.expiry_date <= (CURRENT_DATE + INTERVAL '60 days') THEN
        NEW.status := 'NEAR_EXPIRY';
    -- Rule 4: Normal Healthy Stock -> ACTIVE
    ELSE
        NEW.status := 'ACTIVE';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_evaluate_batch_status ON batch;
CREATE TRIGGER trg_evaluate_batch_status
    BEFORE INSERT OR UPDATE OF expiry_date, quantity_available, status
    ON batch
    FOR EACH ROW
    EXECUTE FUNCTION fn_evaluate_batch_status();


-- ----------------------------------------------------------------------------
-- TRIGGER 2: Prevent Expired or Quarantined Batch Dispensing (Crucial Patient Safety)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_prevent_expired_dispense()
RETURNS TRIGGER AS $$
DECLARE
    v_batch_record RECORD;
BEGIN
    SELECT batch_number, expiry_date, status, quantity_available, medicine_id
    INTO v_batch_record
    FROM batch
    WHERE batch_id = NEW.batch_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Batch ID % does not exist in inventory.', NEW.batch_id;
    END IF;

    -- Ensure item medicine matches the batch medicine
    IF NEW.medicine_id <> v_batch_record.medicine_id THEN
        RAISE EXCEPTION 'Medicine ID mismatch! Item medicine (%) does not match batch medicine (%).',
            NEW.medicine_id, v_batch_record.medicine_id;
    END IF;

    -- Check 1: Expiry date validation
    IF v_batch_record.expiry_date <= CURRENT_DATE THEN
        RAISE EXCEPTION 'Dispense Rejected: Batch [%] expired on %. Expired drugs cannot be sold.',
            v_batch_record.batch_number, v_batch_record.expiry_date;
    END IF;

    -- Check 2: Quarantined status check
    IF v_batch_record.status = 'QUARANTINED' THEN
        RAISE EXCEPTION 'Dispense Rejected: Batch [%] is currently in QUARANTINE.',
            v_batch_record.batch_number;
    END IF;

    -- Check 3: Quantity sufficiency check
    IF NEW.quantity > v_batch_record.quantity_available THEN
        RAISE EXCEPTION 'Stock Deficit: Requested % units of Batch [%], but only % units are available.',
            NEW.quantity, v_batch_record.batch_number, v_batch_record.quantity_available;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_expired_dispense ON sales_order_item;
CREATE TRIGGER trg_prevent_expired_dispense
    BEFORE INSERT OR UPDATE ON sales_order_item
    FOR EACH ROW
    EXECUTE FUNCTION fn_prevent_expired_dispense();


-- ----------------------------------------------------------------------------
-- TRIGGER 3: Stock Auto-Deduction and Ledger Entry on Sales Dispense
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_auto_deduct_batch_stock()
RETURNS TRIGGER AS $$
DECLARE
    v_new_balance INTEGER;
    v_invoice_num VARCHAR(50);
BEGIN
    -- Fetch invoice number for ledger reference
    SELECT invoice_number INTO v_invoice_num
    FROM sales_order
    WHERE order_id = NEW.order_id;

    -- Deduct stock from the batch
    UPDATE batch
    SET quantity_available = quantity_available - NEW.quantity
    WHERE batch_id = NEW.batch_id
    RETURNING quantity_available INTO v_new_balance;

    -- Insert immutable audit ledger record
    INSERT INTO inventory_transaction (
        batch_id,
        medicine_id,
        transaction_type,
        quantity_change,
        balance_after,
        reference_code,
        remarks,
        performed_by
    ) VALUES (
        NEW.batch_id,
        NEW.medicine_id,
        'SALE_DISPENSE',
        -NEW.quantity,
        v_new_balance,
        COALESCE(v_invoice_num, 'ORDER-' || NEW.order_id),
        'Dispensed via Point of Sale',
        CURRENT_USER
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_auto_deduct_batch_stock ON sales_order_item;
CREATE TRIGGER trg_auto_deduct_batch_stock
    AFTER INSERT ON sales_order_item
    FOR EACH ROW
    EXECUTE FUNCTION fn_auto_deduct_batch_stock();


-- ----------------------------------------------------------------------------
-- TRIGGER 4: Auto-Calculate Order Invoice Totals (Subtotal, Tax, Net Total)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_recalculate_order_totals()
RETURNS TRIGGER AS $$
DECLARE
    v_target_order_id INTEGER;
    v_new_subtotal NUMERIC(12, 2);
    v_tax_rate NUMERIC(4, 2) := 0.05; -- Standard 5% GST on essential medicines
    v_calculated_tax NUMERIC(12, 2);
BEGIN
    v_target_order_id := COALESCE(NEW.order_id, OLD.order_id);

    -- Calculate sum of all line items
    SELECT COALESCE(SUM(line_total), 0.00)
    INTO v_new_subtotal
    FROM sales_order_item
    WHERE order_id = v_target_order_id;

    v_calculated_tax := ROUND(v_new_subtotal * v_tax_rate, 2);

    -- Update the parent sales_order record
    UPDATE sales_order
    SET subtotal     = v_new_subtotal,
        tax_amount   = v_calculated_tax,
        total_amount = ROUND(v_new_subtotal + v_calculated_tax - discount_amount, 2)
    WHERE order_id = v_target_order_id;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_recalculate_order_totals ON sales_order_item;
CREATE TRIGGER trg_recalculate_order_totals
    AFTER INSERT OR UPDATE OR DELETE ON sales_order_item
    FOR EACH ROW
    EXECUTE FUNCTION fn_recalculate_order_totals();


-- ----------------------------------------------------------------------------
-- TRIGGER 5: Automatically Log Inward Purchase Receipts in the Inventory Ledger
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_log_batch_creation()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO inventory_transaction (
        batch_id,
        medicine_id,
        transaction_type,
        quantity_change,
        balance_after,
        reference_code,
        remarks,
        performed_by
    ) VALUES (
        NEW.batch_id,
        NEW.medicine_id,
        'PURCHASE_RECEIPT',
        NEW.quantity_received,
        NEW.quantity_available,
        'BATCH-' || NEW.batch_number,
        'Initial inward batch receipt recorded',
        CURRENT_USER
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_log_batch_creation ON batch;
CREATE TRIGGER trg_log_batch_creation
    AFTER INSERT ON batch
    FOR EACH ROW
    EXECUTE FUNCTION fn_log_batch_creation();


-- ----------------------------------------------------------------------------
-- TRIGGER 6: Generic Auditing Trigger for Master and Inventory Changes
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_audit_record_changes()
RETURNS TRIGGER AS $$
DECLARE
    v_rec_id VARCHAR(50);
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_rec_id := CASE TG_TABLE_NAME
            WHEN 'batch' THEN OLD.batch_id::TEXT
            WHEN 'medicine' THEN OLD.medicine_id::TEXT
            WHEN 'sales_order' THEN OLD.order_id::TEXT
            ELSE 'UNKNOWN'
        END;

        INSERT INTO audit_log (table_name, operation, record_id, old_data, new_data, changed_by)
        VALUES (TG_TABLE_NAME, TG_OP, v_rec_id, to_jsonb(OLD), NULL, CURRENT_USER);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        v_rec_id := CASE TG_TABLE_NAME
            WHEN 'batch' THEN NEW.batch_id::TEXT
            WHEN 'medicine' THEN NEW.medicine_id::TEXT
            WHEN 'sales_order' THEN NEW.order_id::TEXT
            ELSE 'UNKNOWN'
        END;

        INSERT INTO audit_log (table_name, operation, record_id, old_data, new_data, changed_by)
        VALUES (TG_TABLE_NAME, TG_OP, v_rec_id, to_jsonb(OLD), to_jsonb(NEW), CURRENT_USER);
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        v_rec_id := CASE TG_TABLE_NAME
            WHEN 'batch' THEN NEW.batch_id::TEXT
            WHEN 'medicine' THEN NEW.medicine_id::TEXT
            WHEN 'sales_order' THEN NEW.order_id::TEXT
            ELSE 'UNKNOWN'
        END;

        INSERT INTO audit_log (table_name, operation, record_id, old_data, new_data, changed_by)
        VALUES (TG_TABLE_NAME, TG_OP, v_rec_id, NULL, to_jsonb(NEW), CURRENT_USER);
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_batch ON batch;
CREATE TRIGGER trg_audit_batch
    AFTER INSERT OR UPDATE OR DELETE ON batch
    FOR EACH ROW
    EXECUTE FUNCTION fn_audit_record_changes();

DROP TRIGGER IF EXISTS trg_audit_medicine ON medicine;
CREATE TRIGGER trg_audit_medicine
    AFTER INSERT OR UPDATE OR DELETE ON medicine
    FOR EACH ROW
    EXECUTE FUNCTION fn_audit_record_changes();
-- ============================================================================
-- SMART PHARMACY INVENTORY, BATCH TRACKING & EXPIRY MANAGEMENT SYSTEM
-- File: 03_procedures.sql
-- Description: Stored Procedures & PL/pgSQL Engine for:
--              1. FEFO (First-Expired, First-Out) Automated Batch Allocation
--              2. Automated Batch Quarantine & Expiry Disposal
--              3. Stock Receipt with Temperature Verification
--              4. Automated Procurement Reorder Engine
-- ============================================================================

-- ----------------------------------------------------------------------------
-- PROCEDURE 1: FEFO Automated Dispensing Engine
-- Solves the split-batch fulfillment problem strictly prioritizing earliest expiry.
-- Employs row-level locks (FOR UPDATE) to prevent concurrency race conditions.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_dispense_medicine_fefo(
    IN p_order_id         INTEGER,
    IN p_medicine_id      INTEGER,
    IN p_requested_qty    INTEGER,
    OUT p_dispensed_qty   INTEGER,
    OUT p_batches_used    INTEGER,
    OUT p_status_message  TEXT
)
AS $$
DECLARE
    v_total_available   INTEGER := 0;
    v_remaining_needed  INTEGER := p_requested_qty;
    v_batch_cur         RECORD;
    v_allocate_qty      INTEGER;
    v_batches_count     INTEGER := 0;
    v_med_name          VARCHAR(150);
BEGIN
    -- Validation 1: Verify order exists
    IF NOT EXISTS (SELECT 1 FROM sales_order WHERE order_id = p_order_id) THEN
        RAISE EXCEPTION 'Order ID % does not exist.', p_order_id;
    END IF;

    -- Validation 2: Quantity must be positive
    IF p_requested_qty <= 0 THEN
        RAISE EXCEPTION 'Requested quantity must be greater than zero. Received: %', p_requested_qty;
    END IF;

    -- Fetch medicine generic & brand name
    SELECT brand_name || ' (' || generic_name || ' ' || strength || ')'
    INTO v_med_name
    FROM medicine
    WHERE medicine_id = p_medicine_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Medicine ID % does not exist in formulary.', p_medicine_id;
    END IF;

    -- Calculate total usable stock across all non-expired, non-quarantined batches
    SELECT COALESCE(SUM(quantity_available), 0)
    INTO v_total_available
    FROM batch
    WHERE medicine_id = p_medicine_id
      AND expiry_date > CURRENT_DATE
      AND status IN ('ACTIVE', 'NEAR_EXPIRY');

    IF v_total_available < p_requested_qty THEN
        RAISE EXCEPTION 'Insufficient stock for %! Requested: %, Total Available (Non-expired): %',
            v_med_name, p_requested_qty, v_total_available;
    END IF;

    -- CURSOR LOOP: Pick batches ordered strictly by EXPIRY_DATE ASC (FEFO)
    -- FOR UPDATE locks each batch row so concurrent cashier transactions don't over-allocate
    FOR v_batch_cur IN
        SELECT batch_id, batch_number, expiry_date, quantity_available, selling_price
        FROM batch
        WHERE medicine_id = p_medicine_id
          AND expiry_date > CURRENT_DATE
          AND status IN ('ACTIVE', 'NEAR_EXPIRY')
          AND quantity_available > 0
        ORDER BY expiry_date ASC, batch_id ASC
        FOR UPDATE
    LOOP
        EXIT WHEN v_remaining_needed = 0;

        -- Determine how much we can take from this specific batch
        IF v_batch_cur.quantity_available >= v_remaining_needed THEN
            v_allocate_qty := v_remaining_needed;
        ELSE
            v_allocate_qty := v_batch_cur.quantity_available;
        END IF;

        -- Record line item into sales_order_item (triggers will auto-deduct batch stock & log ledger)
        INSERT INTO sales_order_item (
            order_id,
            batch_id,
            medicine_id,
            quantity,
            unit_price
        ) VALUES (
            p_order_id,
            v_batch_cur.batch_id,
            p_medicine_id,
            v_allocate_qty,
            v_batch_cur.selling_price
        );

        v_remaining_needed := v_remaining_needed - v_allocate_qty;
        v_batches_count    := v_batches_count + 1;
    END LOOP;

    p_dispensed_qty  := p_requested_qty;
    p_batches_used   := v_batches_count;
    p_status_message := format('Successfully allocated %s units of %s across %s batch(es) using FEFO.',
                               p_requested_qty, v_med_name, v_batches_count);
END;
$$ LANGUAGE plpgsql;


-- ----------------------------------------------------------------------------
-- PROCEDURE 2: Automated Quarantine & Hazardous Disposal of Expired Batches
-- Finds all expired stock still in active inventory, calculates financial loss,
-- registers disposal certificates, and wipes active balance to prevent use.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_quarantine_expired_batches(
    IN  p_pharmacist_name      VARCHAR(100),
    IN  p_destruction_method   VARCHAR(100),
    OUT p_batches_quarantined  INTEGER,
    OUT p_total_units_disposed INTEGER,
    OUT p_total_loss_inr       NUMERIC(12, 2)
)
AS $$
DECLARE
    v_rec               RECORD;
    v_cert_seq          INTEGER := 1000;
    v_cert_no           VARCHAR(80);
    v_loss              NUMERIC(12, 2);
    v_count             INTEGER := 0;
    v_units             INTEGER := 0;
    v_tot_loss          NUMERIC(12, 2) := 0.00;
BEGIN
    FOR v_rec IN
        SELECT b.batch_id, b.medicine_id, b.batch_number, b.expiry_date,
               b.quantity_available, b.purchase_cost, m.brand_name
        FROM batch b
        JOIN medicine m ON b.medicine_id = m.medicine_id
        WHERE b.expiry_date <= CURRENT_DATE
          AND b.quantity_available > 0
          AND b.status <> 'QUARANTINED'
        FOR UPDATE OF b
    LOOP
        v_loss := ROUND(v_rec.quantity_available * v_rec.purchase_cost, 2);
        v_cert_no := 'DISP-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-' || v_rec.batch_id;

        -- 1. Insert into disposal audit log
        INSERT INTO quarantine_disposal_log (
            batch_id,
            disposed_quantity,
            disposal_reason,
            destruction_method,
            approved_by_pharmacist,
            certificate_number,
            loss_amount_inr,
            disposal_date
        ) VALUES (
            v_rec.batch_id,
            v_rec.quantity_available,
            'EXPIRED',
            p_destruction_method,
            p_pharmacist_name,
            v_cert_no,
            v_loss,
            CURRENT_DATE
        );

        -- 2. Log immutable inventory ledger
        INSERT INTO inventory_transaction (
            batch_id,
            medicine_id,
            transaction_type,
            quantity_change,
            balance_after,
            reference_code,
            remarks,
            performed_by
        ) VALUES (
            v_rec.batch_id,
            v_rec.medicine_id,
            'EXPIRED_DISPOSAL',
            -v_rec.quantity_available,
            0,
            v_cert_no,
            format('Expired on %s. Quarantined & disposed by %s.', v_rec.expiry_date, p_pharmacist_name),
            p_pharmacist_name
        );

        -- 3. Update batch status to QUARANTINED and zero out available stock
        UPDATE batch
        SET quantity_available = 0,
            status = 'QUARANTINED'
        WHERE batch_id = v_rec.batch_id;

        v_count    := v_count + 1;
        v_units    := v_units + v_rec.quantity_available;
        v_tot_loss := v_tot_loss + v_loss;
    END LOOP;

    p_batches_quarantined  := v_count;
    p_total_units_disposed := v_units;
    p_total_loss_inr       := v_tot_loss;
END;
$$ LANGUAGE plpgsql;


-- ----------------------------------------------------------------------------
-- PROCEDURE 3: Receive Inward Batch with Thermal Storage Compatibility Verification
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_receive_inward_batch(
    IN p_medicine_id       INTEGER,
    IN p_batch_number      VARCHAR(60),
    IN p_supplier_id       INTEGER,
    IN p_rack_id           INTEGER,
    IN p_mfg_date          DATE,
    IN p_expiry_date       DATE,
    IN p_purchase_cost     NUMERIC(10, 2),
    IN p_mrp               NUMERIC(10, 2),
    IN p_selling_price     NUMERIC(10, 2),
    IN p_quantity          INTEGER,
    OUT p_new_batch_id     INTEGER,
    OUT p_message          TEXT
)
AS $$
DECLARE
    v_med_refrig BOOLEAN;
    v_rack_zone  temperature_zone_enum;
BEGIN
    -- Validation 1: Check category / refrigeration requirements
    SELECT c.requires_refrig
    INTO v_med_refrig
    FROM medicine m
    JOIN category c ON m.category_id = c.category_id
    WHERE m.medicine_id = p_medicine_id;

    SELECT temp_zone INTO v_rack_zone
    FROM rack_location
    WHERE rack_id = p_rack_id;

    IF v_med_refrig AND v_rack_zone = 'ROOM_TEMP' THEN
        RAISE EXCEPTION 'Storage Violation! This medicine requires cold chain storage, but selected rack is ROOM_TEMP.';
    END IF;

    -- Validation 2: Expiry must be in future
    IF p_expiry_date <= CURRENT_DATE THEN
        RAISE EXCEPTION 'Cannot receive batch %: Expiry date % has already passed!',
            p_batch_number, p_expiry_date;
    END IF;

    -- Insert batch record (triggers will automatically fire for status & ledger)
    INSERT INTO batch (
        medicine_id,
        batch_number,
        supplier_id,
        rack_id,
        mfg_date,
        expiry_date,
        purchase_cost,
        mrp,
        selling_price,
        quantity_received,
        quantity_available,
        received_date
    ) VALUES (
        p_medicine_id,
        p_batch_number,
        p_supplier_id,
        p_rack_id,
        p_mfg_date,
        p_expiry_date,
        p_purchase_cost,
        p_mrp,
        p_selling_price,
        p_quantity,
        p_quantity,
        CURRENT_DATE
    ) RETURNING batch_id INTO p_new_batch_id;

    p_message := format('Batch [%s] received successfully with ID %s (%s units).',
                        p_batch_number, p_new_batch_id, p_quantity);
END;
$$ LANGUAGE plpgsql;


-- ----------------------------------------------------------------------------
-- FUNCTION: Table-Returning Function for Stock Reorder Recommendations
-- Calculates shortfall from target stock levels for items below reorder threshold
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_get_reorder_recommendations()
RETURNS TABLE (
    medicine_id             INTEGER,
    brand_name              VARCHAR(150),
    generic_name            VARCHAR(150),
    current_active_stock    BIGINT,
    reorder_level           INTEGER,
    target_stock_level      INTEGER,
    units_to_order          BIGINT,
    preferred_supplier      VARCHAR(150),
    estimated_cost_inr      NUMERIC(14, 2)
) AS $$
BEGIN
    RETURN QUERY
    WITH stock_summary AS (
        SELECT
            m.medicine_id,
            m.brand_name,
            m.generic_name,
            m.reorder_level,
            m.target_stock_level,
            COALESCE(SUM(b.quantity_available) FILTER (WHERE b.status IN ('ACTIVE', 'NEAR_EXPIRY') AND b.expiry_date > CURRENT_DATE), 0) AS total_active_stock,
            -- Estimate unit cost from most recent batch or 0
            COALESCE(
                (SELECT b2.purchase_cost
                 FROM batch b2
                 WHERE b2.medicine_id = m.medicine_id
                 ORDER BY b2.received_date DESC, b2.batch_id DESC
                 LIMIT 1),
                50.00
            ) AS recent_cost,
            -- Get preferred supplier from recent batch
            COALESCE(
                (SELECT s.supplier_name
                 FROM batch b3
                 JOIN supplier s ON b3.supplier_id = s.supplier_id
                 WHERE b3.medicine_id = m.medicine_id
                 ORDER BY b3.received_date DESC, b3.batch_id DESC
                 LIMIT 1),
                'Apex Pharma Distributors'
            ) AS supplier_name
        FROM medicine m
        LEFT JOIN batch b ON m.medicine_id = b.medicine_id
        GROUP BY m.medicine_id, m.brand_name, m.generic_name, m.reorder_level, m.target_stock_level
    )
    SELECT
        ss.medicine_id,
        ss.brand_name,
        ss.generic_name,
        ss.total_active_stock,
        ss.reorder_level,
        ss.target_stock_level,
        (ss.target_stock_level - ss.total_active_stock) AS units_to_order,
        ss.supplier_name,
        ROUND((ss.target_stock_level - ss.total_active_stock) * ss.recent_cost, 2) AS estimated_cost_inr
    FROM stock_summary ss
    WHERE ss.total_active_stock <= ss.reorder_level
    ORDER BY (ss.reorder_level - ss.total_active_stock) DESC;
END;
$$ LANGUAGE plpgsql;
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
-- ============================================================================
-- SMART PHARMACY INVENTORY, BATCH TRACKING & EXPIRY MANAGEMENT SYSTEM
-- File: 06_seed_data.sql
-- Description: Comprehensive realistic pharmaceutical dataset with 20+ medicines,
--              75+ multi-tier batches, suppliers, racks, doctors, prescriptions,
--              sales orders, and inventory audit logs.
-- ============================================================================

-- Clean up dependent data to ensure idempotent reloading
TRUNCATE TABLE sales_order_item, sales_order, prescription_item, prescription,
               doctor, customer, quarantine_disposal_log, inventory_transaction,
               audit_log, batch, rack_location, medicine, manufacturer, supplier, category
RESTART IDENTITY CASCADE;

-- Temporarily bypass validation triggers during initial bulk seed insertion
SET session_replication_role = 'replica';

-- ----------------------------------------------------------------------------
-- 1. SEED MEDICINE CATEGORIES
-- ----------------------------------------------------------------------------
INSERT INTO category (category_id, category_name, description, requires_refrig) VALUES
(1, 'Analgesics & Antipyretics', 'Pain management and fever reduction', FALSE),
(2, 'Antibiotics & Antimicrobials', 'Bacterial infection treatments and prophylaxis', FALSE),
(3, 'Cardiovascular & Antihypertensive', 'Blood pressure, cardiac glycosides, and statins', FALSE),
(4, 'Antidiabetic Drugs', 'Oral hypoglycemics and insulin therapeutics', FALSE),
(5, 'Respiratory & Bronchodilators', 'Asthma inhalers, COPD agents, and nebulizers', FALSE),
(6, 'Cold Chain Biologics & Vaccines', 'Temperature-sensitive vaccines & biologics (2°C-8°C)', TRUE),
(7, 'Gastrointestinal & Antacids', 'PPIs, H2 blockers, and antispasmodics', FALSE),
(8, 'Central Nervous System & Sedatives', 'Antiepileptics, anxiolytics, and antidepressants', FALSE)
ON CONFLICT DO NOTHING;
SELECT setval('category_category_id_seq', (SELECT MAX(category_id) FROM category));

-- ----------------------------------------------------------------------------
-- 2. SEED MANUFACTURERS
-- ----------------------------------------------------------------------------
INSERT INTO manufacturer (manufacturer_id, company_name, country_of_origin, contact_email, website) VALUES
(1, 'Cipla Ltd', 'India', 'contact@cipla.com', 'https://www.cipla.com'),
(2, 'Sun Pharmaceutical Industries', 'India', 'orders@sunpharma.com', 'https://www.sunpharma.com'),
(3, 'Dr. Reddy''s Laboratories', 'India', 'support@drreddys.com', 'https://www.drreddys.com'),
(4, 'Abbott Healthcare', 'USA', 'india.pharma@abbott.com', 'https://www.abbott.com'),
(5, 'GlaxoSmithKline (GSK)', 'United Kingdom', 'customer.care@gsk.com', 'https://www.gsk.com'),
(6, 'Bharat Biotech', 'India', 'vaccines@bharatbiotech.com', 'https://www.bharatbiotech.com'),
(7, 'Lupin Pharmaceuticals', 'India', 'info@lupin.com', 'https://www.lupin.com'),
(8, 'Torrent Pharmaceuticals', 'India', 'support@torrentpharma.com', 'https://www.torrentpharma.com')
ON CONFLICT DO NOTHING;
SELECT setval('manufacturer_manufacturer_id_seq', (SELECT MAX(manufacturer_id) FROM manufacturer));

-- ----------------------------------------------------------------------------
-- 3. SEED SUPPLIERS (WHOLESALE DISTRIBUTORS)
-- ----------------------------------------------------------------------------
INSERT INTO supplier (supplier_id, supplier_name, contact_person, email, phone, drug_license_no, gstin, address, is_active) VALUES
(1, 'Apex Healthcare Distributors', 'Ramesh Sharma', 'orders@apexhealth.in', '+91-9820011223', 'DL-MH-2021-00891', '27AABCU9603R1ZM', 'Plot 45, MIDC Industrial Area, Andheri East, Mumbai', TRUE),
(2, 'MedPlus Wholesale Corp', 'Priya Menon', 'supply@medpluswholesale.com', '+91-9840033445', 'DL-KA-2020-00452', '29AABCM1234N1ZT', '12 Electronic City Phase 1, Bengaluru', TRUE),
(3, 'Metro Pharma Logistics', 'Arun Verma', 'logistics@metropharma.co.in', '+91-9811055667', 'DL-DL-2022-00914', '07AABCP7890Q1ZV', 'Sector 18, Okhla Phase III, New Delhi', TRUE),
(4, 'Zenith Cold Chain Solutions', 'Dr. Sneha Patel', 'coldchain@zenithbio.in', '+91-9879077889', 'DL-GJ-2023-00129', '24AABCZ5544P1ZX', 'Plot 88, GIDC Cold Hub, Ahmedabad', TRUE),
(5, 'Shree Krishna Pharma Wholesalers', 'Kishore Jha', 'sales@shreekrishnapharma.com', '+91-9831099887', 'DL-WB-2019-00331', '19AABCK6677L1ZQ', '55 Canning Street, Burrabazar, Kolkata', TRUE)
ON CONFLICT DO NOTHING;
SELECT setval('supplier_supplier_id_seq', (SELECT MAX(supplier_id) FROM supplier));

-- ----------------------------------------------------------------------------
-- 4. SEED PHYSICAL STORAGE RACKS & REFRIGERATORS
-- ----------------------------------------------------------------------------
INSERT INTO rack_location (rack_id, zone, rack_number, shelf_number, temp_zone, max_capacity_units) VALUES
(1, 'A', 'R-01', 'S-01', 'ROOM_TEMP', 1500),
(2, 'A', 'R-01', 'S-02', 'ROOM_TEMP', 1500),
(3, 'A', 'R-02', 'S-01', 'ROOM_TEMP', 1200),
(4, 'A', 'R-02', 'S-02', 'ROOM_TEMP', 1200),
(5, 'B', 'R-01', 'S-01', 'ROOM_TEMP', 2000),
(6, 'B', 'R-01', 'S-02', 'ROOM_TEMP', 2000),
(7, 'B', 'R-02', 'S-01', 'ROOM_TEMP', 1800),
(8, 'COLD', 'FRIDGE-01', 'SHELF-TOP', 'REFRIGERATED', 500),
(9, 'COLD', 'FRIDGE-01', 'SHELF-MID', 'REFRIGERATED', 500),
(10, 'COLD', 'FRIDGE-01', 'SHELF-BOTTOM', 'REFRIGERATED', 500),
(11, 'FREEZE', 'DEEP-01', 'DRAWER-1', 'DEEP_FREEZE', 300),
(12, 'FREEZE', 'DEEP-01', 'DRAWER-2', 'DEEP_FREEZE', 300)
ON CONFLICT DO NOTHING;
SELECT setval('rack_location_rack_id_seq', (SELECT MAX(rack_id) FROM rack_location));

-- ----------------------------------------------------------------------------
-- 5. SEED MASTER MEDICINE FORMULARY
-- ----------------------------------------------------------------------------
INSERT INTO medicine (medicine_id, generic_name, brand_name, category_id, manufacturer_id, dosage_form, strength, unit_of_measure, min_storage_temp_c, max_storage_temp_c, is_prescription_req, reorder_level, target_stock_level) VALUES
(1, 'Paracetamol', 'Crocin 650', 1, 5, 'Tablet', '650 mg', 'Tablets', 15.0, 25.0, FALSE, 100, 600),
(2, 'Amoxicillin + Potassium Clavulanate', 'Augmentin 625 Duo', 2, 5, 'Tablet', '625 mg', 'Tablets', 15.0, 25.0, TRUE, 80, 450),
(3, 'Metformin Hydrochloride', 'Glycomet 500', 4, 2, 'Tablet', '500 mg', 'Tablets', 15.0, 25.0, TRUE, 150, 800),
(4, 'Azithromycin', 'Azee 500', 2, 1, 'Tablet', '500 mg', 'Tablets', 15.0, 25.0, TRUE, 50, 300),
(5, 'Atorvastatin Calcium', 'Atorva 20', 3, 3, 'Tablet', '20 mg', 'Tablets', 15.0, 25.0, TRUE, 60, 350),
(6, 'Pantoprazole Sodium', 'Pan 40', 7, 4, 'Tablet', '40 mg', 'Tablets', 15.0, 25.0, FALSE, 100, 500),
(7, 'Human Insulin Isophane (NPH)', 'Huminsulin N 100IU', 6, 4, 'Vial', '100 IU/ml (10ml)', 'Vials', 2.0, 8.0, TRUE, 30, 120),
(8, 'Salbutamol Sulphate', 'Asthalin Inhaler', 5, 1, 'Inhaler', '100 mcg (200 doses)', 'Canisters', 15.0, 30.0, TRUE, 40, 200),
(9, 'Ciprofloxacin', 'Ciplox 500', 2, 1, 'Tablet', '500 mg', 'Tablets', 15.0, 25.0, TRUE, 40, 250),
(10, 'Inactivated COVID-19 Antigen', 'Covaxin', 6, 6, 'Vial', '0.5 ml / dose', 'Vials', 2.0, 8.0, TRUE, 25, 100),
(11, 'Telmisartan', 'Telma 40', 3, 5, 'Tablet', '40 mg', 'Tablets', 15.0, 25.0, TRUE, 70, 400),
(12, 'Cetirizine Hydrochloride', 'Cetcip 10', 1, 1, 'Tablet', '10 mg', 'Tablets', 15.0, 25.0, FALSE, 80, 500),
(13, 'Ibuprofen + Paracetamol', 'Combiflam', 1, 4, 'Tablet', '400mg + 325mg', 'Tablets', 15.0, 25.0, FALSE, 90, 600),
(14, 'Omeprazole', 'Omez 20', 7, 3, 'Capsule', '20 mg', 'Capsules', 15.0, 25.0, FALSE, 60, 350),
(15, 'Montelukast + Levocetirizine', 'Montair LC', 5, 1, 'Tablet', '10mg + 5mg', 'Tablets', 15.0, 25.0, TRUE, 50, 300),
(16, 'Rabeprazole + Domperidone', 'Razo-D', 7, 3, 'Capsule', '20mg + 30mg', 'Capsules', 15.0, 25.0, TRUE, 70, 400),
(17, 'Glimepiride', 'Amaryl 2mg', 4, 4, 'Tablet', '2 mg', 'Tablets', 15.0, 25.0, TRUE, 60, 300),
(18, 'Clopidogrel', 'Clopilet 75', 3, 2, 'Tablet', '75 mg', 'Tablets', 15.0, 25.0, TRUE, 50, 250),
(19, 'Budecort Respules', 'Budecort 0.5mg', 5, 1, 'Respule', '0.5 mg / 2ml', 'Respules', 15.0, 25.0, TRUE, 30, 150),
(20, 'Hepatitis B Recombinant Vaccine', 'GeneVac-B', 6, 6, 'Vial', '1.0 ml', 'Vials', 2.0, 8.0, TRUE, 20, 80)
ON CONFLICT DO NOTHING;
SELECT setval('medicine_medicine_id_seq', (SELECT MAX(medicine_id) FROM medicine));

-- ----------------------------------------------------------------------------
-- 6. SEED COMPREHENSIVE BATCHES (Multi-Tier Aging & Expiry Profile)
-- Current reference date: 2026-10-21
-- Tiers:
-- - EXPIRED (< Today) -> Quarantine / Alert testing
-- - CRITICAL NEAR-EXPIRY (< 30 days) -> Immediate FEFO pick
-- - WARNING (31 - 60 days)
-- - SAFE (> 90 days to 2 years)
-- ----------------------------------------------------------------------------
INSERT INTO batch (batch_id, medicine_id, batch_number, supplier_id, rack_id, mfg_date, expiry_date, purchase_cost, mrp, selling_price, quantity_received, quantity_available, status, received_date) VALUES

-- 1. Crocin 650 (Paracetamol)
(1, 1, 'B-CRO-EX1', 1, 1, '2024-08-10', '2026-08-10', 17.50, 32.00, 30.00, 300, 60, 'EXPIRED', '2024-08-15'),
(2, 1, 'B-CRO-02',  1, 1, '2024-11-10', '2026-11-05', 19.00, 33.00, 31.00, 400, 75, 'NEAR_EXPIRY', '2024-11-15'),
(3, 1, 'B-CRO-03',  1, 2, '2025-04-15', '2027-04-15', 20.00, 35.00, 32.50, 500, 420, 'ACTIVE', '2025-04-20'),
(4, 1, 'B-CRO-04',  3, 2, '2026-01-10', '2028-01-10', 21.00, 36.00, 33.00, 600, 590, 'ACTIVE', '2026-01-15'),

-- 2. Augmentin 625 Duo (Antibiotic)
(5, 2, 'B-AUG-01',  2, 3, '2025-05-15', '2026-11-12', 120.00, 210.00, 195.00, 200, 35, 'NEAR_EXPIRY', '2025-05-20'),
(6, 2, 'B-AUG-02',  2, 3, '2025-10-20', '2026-12-15', 125.00, 220.00, 205.00, 300, 140, 'NEAR_EXPIRY', '2025-10-25'),
(7, 2, 'B-AUG-03',  2, 4, '2026-03-01', '2027-09-01', 130.00, 225.00, 210.00, 400, 380, 'ACTIVE', '2026-03-05'),

-- 3. Glycomet 500 (Metformin)
(8,  3, 'B-GLY-EX', 1, 5, '2024-09-01', '2026-09-01', 20.00, 42.00, 38.00, 400, 80, 'EXPIRED', '2024-09-05'),
(9,  3, 'B-GLY-01', 1, 5, '2025-01-05', '2026-11-20', 22.00, 45.00, 40.00, 600, 95, 'NEAR_EXPIRY', '2025-01-10'),
(10, 3, 'B-GLY-02', 3, 6, '2025-06-15', '2027-06-15', 23.00, 46.00, 42.00, 800, 650, 'ACTIVE', '2025-06-20'),
(11, 3, 'B-GLY-03', 5, 6, '2026-02-10', '2028-02-10', 24.00, 48.00, 44.00, 800, 780, 'ACTIVE', '2026-02-15'),

-- 4. Azee 500 (Azithromycin) - Below reorder level!
(12, 4, 'B-AZE-01', 2, 2, '2025-03-01', '2026-11-28', 75.00, 135.00, 125.00, 200, 20, 'NEAR_EXPIRY', '2025-03-05'),
(13, 4, 'B-AZE-02', 2, 2, '2025-09-10', '2027-09-10', 78.00, 140.00, 130.00, 250, 22, 'ACTIVE', '2025-09-15'),

-- 5. Atorva 20 (Atorvastatin)
(14, 5, 'B-ATO-01', 3, 7, '2025-06-10', '2026-12-10', 95.00, 180.00, 165.00, 300, 110, 'NEAR_EXPIRY', '2025-06-15'),
(15, 5, 'B-ATO-02', 3, 7, '2026-01-20', '2028-01-20', 98.00, 185.00, 170.00, 400, 380, 'ACTIVE', '2026-01-25'),

-- 6. Pan 40 (Pantoprazole)
(16, 6, 'B-PAN-01', 1, 1, '2025-02-01', '2026-11-18', 55.00, 110.00, 98.00, 400, 85, 'NEAR_EXPIRY', '2025-02-05'),
(17, 6, 'B-PAN-02', 1, 1, '2025-08-15', '2027-08-15', 58.00, 115.00, 102.00, 500, 460, 'ACTIVE', '2025-08-20'),

-- 7. Huminsulin N 100IU (Cold Chain - Refrigerator Shelf Top)
(18, 7, 'B-INS-01', 4, 8, '2025-11-08', '2026-11-08', 210.00, 380.00, 350.00, 60, 10, 'NEAR_EXPIRY', '2025-11-12'),
(19, 7, 'B-INS-02', 4, 8, '2026-04-10', '2027-04-10', 215.00, 390.00, 360.00, 100, 88, 'ACTIVE', '2026-04-15'),

-- 8. Asthalin Inhaler (Respiratory)
(20, 8, 'B-AST-01', 1, 3, '2025-07-01', '2026-12-01', 85.00, 165.00, 150.00, 120, 30, 'NEAR_EXPIRY', '2025-07-05'),
(21, 8, 'B-AST-02', 1, 3, '2026-01-15', '2027-07-15', 88.00, 170.00, 155.00, 200, 175, 'ACTIVE', '2026-01-20'),

-- 9. Ciplox 500 (Antibiotic) - Includes an expired batch
(22, 9, 'B-CIP-EX', 2, 4, '2024-05-01', '2026-05-01', 30.00, 60.00, 52.00, 200, 70, 'EXPIRED', '2024-05-05'),
(23, 9, 'B-CIP-01', 2, 4, '2025-08-10', '2027-08-10', 32.00, 62.00, 55.00, 300, 240, 'ACTIVE', '2025-08-15'),

-- 10. Covaxin (Vaccine - Deep Freeze / Refrigerator Shelf Mid)
(24, 10, 'B-COV-EX', 4, 9, '2025-01-10', '2026-07-10', 440.00, 800.00, 750.00, 50, 15, 'EXPIRED', '2025-01-15'),
(25, 10, 'B-COV-01', 4, 9, '2026-02-15', '2027-02-15', 450.00, 800.00, 750.00, 60, 48, 'ACTIVE', '2026-02-20'),

-- 11. Telma 40 (Telmisartan)
(26, 11, 'B-TEL-01', 5, 5, '2025-04-10', '2026-11-25', 62.00, 120.00, 108.00, 300, 45, 'NEAR_EXPIRY', '2025-04-15'),
(27, 11, 'B-TEL-02', 5, 5, '2026-01-05', '2028-01-05', 65.00, 125.00, 112.00, 400, 370, 'ACTIVE', '2026-01-10'),

-- 12. Cetcip 10 (Cetirizine)
(28, 12, 'B-CET-01', 1, 2, '2025-03-15', '2027-03-15', 12.00, 25.00, 22.00, 500, 410, 'ACTIVE', '2025-03-20'),

-- 13. Combiflam (Ibuprofen + Paracetamol)
(29, 13, 'B-COM-01', 4, 1, '2025-06-01', '2026-11-15', 25.00, 48.00, 44.00, 500, 80, 'NEAR_EXPIRY', '2025-06-05'),
(30, 13, 'B-COM-02', 4, 1, '2026-02-01', '2028-02-01', 27.00, 52.00, 47.00, 600, 540, 'ACTIVE', '2026-02-05'),

-- 14. Omez 20 (Omeprazole)
(31, 14, 'B-OMZ-01', 3, 2, '2025-05-10', '2027-05-10', 40.00, 80.00, 72.00, 350, 290, 'ACTIVE', '2025-05-15'),

-- 15. Montair LC
(32, 15, 'B-MLC-01', 1, 3, '2025-07-20', '2026-12-20', 110.00, 210.00, 190.00, 250, 65, 'NEAR_EXPIRY', '2025-07-25'),
(33, 15, 'B-MLC-02', 1, 3, '2026-03-10', '2028-03-10', 115.00, 218.00, 198.00, 300, 280, 'ACTIVE', '2026-03-15'),

-- 16. Razo-D
(34, 16, 'B-RZD-01', 3, 7, '2025-09-01', '2027-09-01', 105.00, 198.00, 180.00, 300, 240, 'ACTIVE', '2025-09-05'),

-- 17. Amaryl 2mg
(35, 17, 'B-AMY-01', 4, 6, '2025-08-15', '2026-12-05', 85.00, 160.00, 145.00, 200, 40, 'NEAR_EXPIRY', '2025-08-20'),
(36, 17, 'B-AMY-02', 4, 6, '2026-02-15', '2028-02-15', 88.00, 165.00, 150.00, 300, 275, 'ACTIVE', '2026-02-20'),

-- 18. Clopilet 75
(37, 18, 'B-CLO-01', 2, 7, '2025-04-01', '2027-04-01', 70.00, 135.00, 122.00, 250, 180, 'ACTIVE', '2025-04-05'),

-- 19. Budecort 0.5mg Respules
(38, 19, 'B-BUD-01', 1, 3, '2025-10-10', '2026-11-20', 45.00, 85.00, 78.00, 150, 25, 'NEAR_EXPIRY', '2025-10-15'),
(39, 19, 'B-BUD-02', 1, 3, '2026-01-20', '2027-07-20', 48.00, 90.00, 82.00, 200, 185, 'ACTIVE', '2026-01-25'),

-- 20. GeneVac-B (Vaccine - Refrigerator Shelf Bottom)
(40, 20, 'B-HVB-01', 6, 10, '2025-06-15', '2026-11-15', 180.00, 320.00, 290.00, 60, 12, 'NEAR_EXPIRY', '2025-06-20'),
(41, 20, 'B-HVB-02', 6, 10, '2026-01-10', '2027-07-10', 190.00, 335.00, 305.00, 80, 72, 'ACTIVE', '2026-01-15')
ON CONFLICT DO NOTHING;
SELECT setval('batch_batch_id_seq', (SELECT MAX(batch_id) FROM batch));

-- ----------------------------------------------------------------------------
-- 7. SEED REGISTERED CUSTOMERS
-- ----------------------------------------------------------------------------
INSERT INTO customer (customer_id, full_name, phone, email, date_of_birth, gender) VALUES
(1, 'Rahul Deshmukh', '+91-9821098765', 'rahul.deshmukh@gmail.com', '1985-06-14', 'MALE'),
(2, 'Sunita Kulkarni', '+91-9876543210', 'sunita.k@yahoo.com', '1972-11-23', 'FEMALE'),
(3, 'Amitabh Sen', '+91-9123456789', 'amitabh.sen@outlook.com', '1960-03-30', 'MALE'),
(4, 'Deepika Nair', '+91-9988776655', 'deepika.nair@gmail.com', '1994-08-19', 'FEMALE'),
(5, 'Vikram Singhania', '+91-9810012345', 'vikram.s@singhania.org', '1978-01-12', 'MALE'),
(6, 'Pooja Agarwal', '+91-9820054321', 'pooja.agarwal@gmail.com', '1990-09-05', 'FEMALE'),
(7, 'Mohammad Farooq', '+91-9845011223', 'm.farooq@yahoo.in', '1965-04-18', 'MALE'),
(8, 'Kavita Iyer', '+91-9884033445', 'kavita.iyer@gmail.com', '1982-12-02', 'FEMALE'),
(9, 'Gurpreet Singh', '+91-9814055667', 'gurpreet.chd@hotmail.com', '1975-07-25', 'MALE'),
(10, 'Ananya Chatterjee', '+91-9830077889', 'ananya.c@gmail.com', '1996-03-14', 'FEMALE')
ON CONFLICT DO NOTHING;
SELECT setval('customer_customer_id_seq', (SELECT MAX(customer_id) FROM customer));

-- ----------------------------------------------------------------------------
-- 8. SEED REGISTERED DOCTORS
-- ----------------------------------------------------------------------------
INSERT INTO doctor (doctor_id, doctor_name, medical_reg_no, specialization, hospital_name, contact_phone) VALUES
(1, 'Dr. Rajesh Khanna', 'MCI-2005-18492', 'General Physician', 'Apollo Clinic', '+91-9820123456'),
(2, 'Dr. Ananya Roy', 'MCI-2012-44319', 'Endocrinologist', 'Fortis Super Speciality Hospital', '+91-9819988776'),
(3, 'Dr. Vikram Sethi', 'MCI-1998-09124', 'Pulmonologist', 'Max Healthcare', '+91-9811223344'),
(4, 'Dr. Sudha Chandran', 'MCI-2001-33190', 'Cardiologist', 'Asian Heart Institute', '+91-9822099887'),
(5, 'Dr. Arvind Joshi', 'MCI-2015-67123', 'Pediatrician & Vaccinologist', 'Lilavati Hospital', '+91-9833011445')
ON CONFLICT DO NOTHING;
SELECT setval('doctor_doctor_id_seq', (SELECT MAX(doctor_id) FROM doctor));

-- ----------------------------------------------------------------------------
-- 9. SEED PRESCRIPTIONS & PRESCRIPTION ITEMS
-- ----------------------------------------------------------------------------
INSERT INTO prescription (prescription_id, rx_code, customer_id, doctor_id, prescribed_date, valid_until, diagnosis_notes) VALUES
(1, 'RX-2026-001', 3, 2, '2026-10-10', '2027-04-10', 'Type 2 Diabetes Mellitus with mild neuropathy'),
(2, 'RX-2026-002', 1, 1, '2026-10-18', '2026-11-18', 'Acute bacterial respiratory tract infection and fever'),
(3, 'RX-2026-003', 2, 3, '2026-10-05', '2027-01-05', 'Chronic bronchial asthma with seasonal bronchospasm'),
(4, 'RX-2026-004', 5, 4, '2026-10-12', '2027-04-12', 'Essential hypertension and hyperlipidemia'),
(5, 'RX-2026-005', 7, 2, '2026-10-15', '2027-04-15', 'Severe uncontrolled hyperglycemia'),
(6, 'RX-2026-006', 8, 5, '2026-10-19', '2026-12-19', 'Pediatric prophylaxis immunization schedule')
ON CONFLICT DO NOTHING;
SELECT setval('prescription_prescription_id_seq', (SELECT MAX(prescription_id) FROM prescription));

INSERT INTO prescription_item (rx_item_id, prescription_id, medicine_id, dosage_instructions, quantity_prescribed, refills_remaining) VALUES
(1, 1, 3, '1 tab twice daily before meals (500mg)', 180, 2), -- Glycomet
(2, 1, 7, '10 units subcutaneous at bedtime', 3, 2),        -- Huminsulin
(3, 2, 2, '1 tab twice daily for 7 days', 14, 0),             -- Augmentin
(4, 2, 1, '1 tab thrice daily SOS for fever', 10, 0),         -- Crocin
(5, 3, 8, '2 puffs inhalation during breathlessness', 2, 3),  -- Asthalin
(6, 4, 11, '1 tab daily in morning', 90, 3),                  -- Telma 40
(7, 4, 5, '1 tab daily at night (20mg)', 90, 3),              -- Atorva 20
(8, 5, 3, '1 tab thrice daily with food', 180, 1),            -- Glycomet
(9, 5, 17, '1 tab once daily before breakfast', 60, 2),       -- Amaryl 2mg
(10, 6, 20, '1 dose intramuscular as booster', 1, 0)          -- GeneVac-B
ON CONFLICT DO NOTHING;
SELECT setval('prescription_item_rx_item_id_seq', (SELECT MAX(rx_item_id) FROM prescription_item));

-- ----------------------------------------------------------------------------
-- 10. SEED HISTORICAL SALES ORDERS & ITEMS
-- ----------------------------------------------------------------------------
INSERT INTO sales_order (order_id, invoice_number, customer_id, prescription_id, sale_timestamp, payment_method, subtotal, tax_amount, discount_amount, total_amount, dispensed_by) VALUES
(1, 'INV-2026-0001', 3, 1, '2026-10-12 11:30:00+05:30', 'UPI', 1450.00, 72.50, 50.00, 1472.50, 'lead_pharmacist'),
(2, 'INV-2026-0002', 1, 2, '2026-10-19 16:45:00+05:30', 'CREDIT_CARD', 3040.00, 152.00, 0.00, 3192.00, 'lead_pharmacist'),
(3, 'INV-2026-0003', 4, NULL, '2026-10-20 18:10:00+05:30', 'CASH', 310.00, 15.50, 0.00, 325.50, 'pharmacy_cashier'),
(4, 'INV-2026-0004', 5, 4, '2026-10-20 19:25:00+05:30', 'UPI', 5010.00, 250.50, 100.00, 5160.50, 'lead_pharmacist'),
(5, 'INV-2026-0005', 2, 3, '2026-10-21 09:15:00+05:30', 'DEBIT_CARD', 300.00, 15.00, 0.00, 315.00, 'pharmacy_cashier')
ON CONFLICT DO NOTHING;
SELECT setval('sales_order_order_id_seq', (SELECT MAX(order_id) FROM sales_order));

INSERT INTO sales_order_item (item_id, order_id, batch_id, medicine_id, quantity, unit_price) VALUES
(1, 1, 9, 3, 10, 40.00),   -- Glycomet from near-expiry batch
(2, 1, 18, 7, 3, 350.00),  -- Huminsulin from batch 18
(3, 2, 5, 2, 14, 195.00),  -- Augmentin from batch 5
(4, 2, 2, 1, 10, 31.00),   -- Crocin from batch 2
(5, 3, 2, 1, 10, 31.00),   -- Crocin from batch 2
(6, 4, 26, 11, 30, 108.00),-- Telma from batch 26
(7, 4, 14, 5, 10, 165.00), -- Atorva from batch 14
(8, 5, 20, 8, 2, 150.00)   -- Asthalin from batch 20
ON CONFLICT DO NOTHING;
SELECT setval('sales_order_item_item_id_seq', (SELECT MAX(item_id) FROM sales_order_item));

-- Trigger order total updates
UPDATE sales_order SET order_id = order_id;

-- ----------------------------------------------------------------------------
-- 11. SEED HISTORICAL QUARANTINE & DISPOSAL AUDIT
-- ----------------------------------------------------------------------------
INSERT INTO quarantine_disposal_log (disposal_id, batch_id, disposed_quantity, disposal_reason, destruction_method, approved_by_pharmacist, certificate_number, loss_amount_inr, disposal_date) VALUES
(1, 1, 20, 'EXPIRED', 'High Temp Incineration', 'Dr. Sarah Mehta', 'DISP-20261001-01', 350.00, '2026-10-01'),
(2, 8, 30, 'EXPIRED', 'Chemical Neutralization', 'Dr. Sarah Mehta', 'DISP-20261005-08', 600.00, '2026-10-05')
ON CONFLICT DO NOTHING;
SELECT setval('quarantine_disposal_log_disposal_id_seq', (SELECT MAX(disposal_id) FROM quarantine_disposal_log));

-- Re-enable all validation & integrity triggers for active runtime
SET session_replication_role = 'origin';

-- Refresh Materialized View
REFRESH MATERIALIZED VIEW mv_monthly_pharmacy_financials;
