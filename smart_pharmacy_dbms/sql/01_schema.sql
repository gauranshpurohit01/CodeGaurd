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
