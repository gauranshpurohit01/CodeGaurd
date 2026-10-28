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
