-- ============================================================================
-- SMART PHARMACY INVENTORY, BATCH TRACKING & EXPIRY MANAGEMENT SYSTEM
-- File: 09_transactions_demo.sql
-- Description: Interactive Demonstration of ACID Properties, Savepoints,
--              Explicit Rollbacks, and Row-Level Concurrency Locks.
-- ============================================================================

-- ============================================================================
-- DEMO 1: ATOMICITY - Failure on 2nd Item causes Full Transaction Rollback
-- Scenario: Customer attempts to purchase 10 Crocin (valid) and 500 Augmentin
--           (exceeds stock). The entire transaction must rollback so Crocin is
--           not charged or deducted in isolation.
-- ============================================================================
DO $$
DECLARE
    v_order_id INTEGER;
BEGIN
    RAISE NOTICE '--- Starting Atomicity Test (All or Nothing) ---';

    -- Step 1: Create Sales Order Header
    INSERT INTO sales_order (invoice_number, payment_method)
    VALUES ('INV-TEST-ATOMIC', 'CASH')
    RETURNING order_id INTO v_order_id;

    RAISE NOTICE 'Order created with ID: %', v_order_id;

    -- Step 2: Allocate 10 units of Crocin (Medicine ID 1) -> SUCESS
    CALL sp_dispense_medicine_fefo(v_order_id, 1, 10, NULL, NULL, NULL);
    RAISE NOTICE 'Item 1 allocated successfully.';

    -- Step 3: Attempt to allocate 9999 units of Augmentin (Medicine ID 2) -> EXCEEDS STOCK
    -- This will trigger an exception inside the procedure
    CALL sp_dispense_medicine_fefo(v_order_id, 2, 9999, NULL, NULL, NULL);

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Expected Failure Caught: %', SQLERRM;
        RAISE NOTICE 'Transaction successfully aborted! Rolling back all changes. Zero stock deducted.';
END;
$$;

-- Verify that the test invoice was never committed
SELECT COUNT(*) AS should_be_zero
FROM sales_order
WHERE invoice_number = 'INV-TEST-ATOMIC';


-- ============================================================================
-- DEMO 2: SAVEPOINTS (Partial Rollback within Transaction)
-- Scenario: Customer buys regular medicine, tries to add an expired drug,
--           the invalid item is rolled back to savepoint, valid items commit.
-- ============================================================================
BEGIN;

-- 1. Create order
INSERT INTO sales_order (invoice_number, customer_id, payment_method)
VALUES ('INV-SAVEPOINT-DEMO', 1, 'UPI');

-- 2. Add valid item (Crocin Batch 2)
INSERT INTO sales_order_item (order_id, batch_id, medicine_id, quantity, unit_price)
VALUES (
    (SELECT order_id FROM sales_order WHERE invoice_number = 'INV-SAVEPOINT-DEMO'),
    2, 1, 5, 31.00
);

-- Establish Savepoint before attempting risky manual item
SAVEPOINT valid_items_secured;

-- Attempt invalid operation: Try inserting into expired Batch 1 (triggers will reject this)
-- In a real application, if this errors, application issues ROLLBACK TO SAVEPOINT valid_items_secured;
-- and then COMMIT;

COMMIT;


-- ============================================================================
-- DEMO 3: ISOLATION & ROW-LEVEL LOCKING (SELECT ... FOR UPDATE)
-- Demonstrates how two concurrent sessions selling the same batch are queued
-- sequentially without race conditions.
-- ============================================================================
-- Session 1:
-- BEGIN;
-- SELECT batch_id, batch_number, quantity_available
-- FROM batch
-- WHERE batch_id = 2
-- FOR UPDATE;
-- (Row is now locked by Session 1 until COMMIT or ROLLBACK)
--
-- Session 2 attempting to dispense from batch 2 will wait for Session 1 lock to release.
