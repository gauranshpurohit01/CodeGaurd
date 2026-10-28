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
