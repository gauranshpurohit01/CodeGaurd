#!/usr/bin/env python3
"""
Smart Pharmacy Inventory, Batch Tracking and Expiry Management System
Interactive DBMS Demonstration CLI for Academic Viva & Evaluation.
"""

import sys
import subprocess
import shutil

CONTAINER_NAME = "pharmacy_dbms_pg"
DB_NAME = "pharmacy_db"
DB_USER = "postgres"

USE_LOCAL_PSQL = False

def check_db_health():
    """Checks if either local psql or Docker container is available."""
    global USE_LOCAL_PSQL
    # 1. Try local psql first
    if shutil.which("psql"):
        try:
            res = subprocess.run(["psql", "-d", DB_NAME, "-c", "SELECT 1;"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                USE_LOCAL_PSQL = True
                return True
        except Exception:
            pass

    # 2. Try Docker container
    if shutil.which("docker"):
        try:
            res = subprocess.run(["docker", "exec", CONTAINER_NAME, "pg_isready", "-U", DB_USER, "-d", DB_NAME],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                USE_LOCAL_PSQL = False
                return True
        except Exception:
            pass

    return False

def run_query(sql: str, print_output: bool = True) -> str:
    """Executes a SQL statement via local psql or docker exec into PostgreSQL."""
    if USE_LOCAL_PSQL:
        cmd = ["psql", "-d", DB_NAME, "-c", sql]
    else:
        cmd = [
            "docker", "exec", "-i", CONTAINER_NAME,
            "psql", "-U", DB_USER, "-d", DB_NAME, "-c", sql
        ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        if print_output:
            print(res.stdout)
        return res.stdout
    except subprocess.CalledProcessError as e:
        if print_output:
            print("Database Error / Exception Encountered:")
            print(e.stderr or e.stdout)
        return e.stderr or e.stdout
    except FileNotFoundError:
        print("[!] Neither local psql nor Docker is available in PATH.")
        return ""

def show_menu():
    print("\n" + "=" * 70)
    print(" SMART PHARMACY INVENTORY & EXPIRY MANAGEMENT SYSTEM (PostgreSQL)")
    print(" Academic DBMS Project - Demonstration & Viva Console")
    print("=" * 70)
    print(" [1] View Medicine Formulary & Usable Stock (View: v_medicine_stock_overview)")
    print(" [2] View Expiry Risk Radar & Alerts (View: v_expiry_risk_radar)")
    print(" [3] Demonstrate FEFO Dispensing (Procedure: sp_dispense_medicine_fefo)")
    print(" [4] Demonstrate Quarantine & Loss Write-off (Procedure: sp_quarantine_expired_batches)")
    print(" [5] Test Patient Safety Trigger (Attempt Dispensing an Expired Drug)")
    print(" [6] View Monthly Financial Analytics (Materialized View: mv_monthly_pharmacy_financials)")
    print(" [7] Run Procurement Reorder Shortfall Function (Function: fn_get_reorder_recommendations)")
    print(" [8] Run Clinical Batch Recall Query (Trace Patients & Doctors)")
    print(" [9] View System Security Audit Trail (Table: audit_log)")
    print(" [10] Refresh Materialized View (Procedure: sp_refresh_financial_analytics)")
    print(" [0] Exit")
    print("-" * 70)

def demo_fefo_dispense():
    print("\n--- DEMONSTRATING FIRST-EXPIRED, FIRST-OUT (FEFO) DISPENSING ---")
    print("Scenario: A customer needs 60 units of 'Crocin 650' (Medicine ID 1).")
    print("The system will inspect batches and strictly pick the earliest expiring batch first.")
    print("\nCurrent Batches for Crocin 650 before dispense:")
    run_query("""
        SELECT batch_id, batch_number, expiry_date, quantity_available, status
        FROM batch
        WHERE medicine_id = 1
        ORDER BY expiry_date ASC;
    """)

    confirm = input("Execute FEFO dispense for 60 units? (y/n): ").strip().lower()
    if confirm == 'y':
        sql = """
        DO $$
        DECLARE
            v_order_id INTEGER;
            v_dispensed INTEGER;
            v_batches   INTEGER;
            v_msg       TEXT;
        BEGIN
            INSERT INTO sales_order (invoice_number, customer_id, payment_method)
            VALUES ('INV-DEMO-' || TO_CHAR(CLOCK_TIMESTAMP(), 'HH24MISS'), 1, 'UPI')
            RETURNING order_id INTO v_order_id;

            CALL sp_dispense_medicine_fefo(v_order_id, 1, 60, v_dispensed, v_batches, v_msg);
            RAISE NOTICE '%', v_msg;
        END $$;
        """
        run_query(sql)

        print("\nBatches for Crocin 650 AFTER FEFO dispense (Note stock reduction on earliest batch):")
        run_query("""
            SELECT batch_id, batch_number, expiry_date, quantity_available, status
            FROM batch
            WHERE medicine_id = 1
            ORDER BY expiry_date ASC;
        """)

def demo_expired_trigger_rejection():
    print("\n--- DEMONSTRATING PATIENT SAFETY TRIGGER REJECTION ---")
    print("Scenario: A cashier attempts to sell from Batch 1 (B-CRO-01) which expired in September 2026.")
    print("The database engine trigger (trg_prevent_expired_dispense) must abort the operation!")

    sql = """
    INSERT INTO sales_order_item (order_id, batch_id, medicine_id, quantity, unit_price)
    VALUES (1, 1, 1, 5, 30.00);
    """
    run_query(sql)

def demo_quarantine():
    print("\n--- DEMONSTRATING AUTOMATED BATCH QUARANTINE & DISPOSAL ---")
    print("The stored procedure scans all expired batches, removes them from active inventory,")
    print("and generates formal destruction certificates and logs capital write-off.")

    sql = """
    DO $$
    DECLARE
        v_b INTEGER;
        v_u INTEGER;
        v_l NUMERIC(12,2);
    BEGIN
        CALL sp_quarantine_expired_batches('Dr. Sarah Mehta (Chief Pharmacist)', 'High-Temp Incineration', v_b, v_u, v_l);
        RAISE NOTICE 'Quarantine Summary: % batches quarantined, % units destroyed, ₹% total loss logged.',
            v_b, v_u, v_l;
    END $$;
    """
    run_query(sql)

    print("\nDisposal Audit Records:")
    run_query("""
        SELECT disposal_id, certificate_number, batch_id, disposed_quantity, loss_amount_inr, disposal_date
        FROM quarantine_disposal_log;
    """)

def main():
    if not check_db_health():
        print("[!] PostgreSQL container 'pharmacy_dbms_pg' is not responding.")
        print("Please start it first by running:")
        print("   ./setup.sh")
        print("or:")
        print("   docker-compose up -d")
        sys.exit(1)

    while True:
        show_menu()
        choice = input("Enter choice (0-10): ").strip()
        if choice == '1':
            run_query("SELECT medicine_id, brand_name, dosage_form, total_usable_stock, reorder_level, stock_status FROM v_medicine_stock_overview;")
        elif choice == '2':
            run_query("SELECT batch_number, brand_name, expiry_date, days_remaining, quantity_available, risk_urgency_tier FROM v_expiry_risk_radar LIMIT 10;")
        elif choice == '3':
            demo_fefo_dispense()
        elif choice == '4':
            demo_quarantine()
        elif choice == '5':
            demo_expired_trigger_rejection()
        elif choice == '6':
            run_query("SELECT * FROM mv_monthly_pharmacy_financials;")
        elif choice == '7':
            run_query("SELECT * FROM fn_get_reorder_recommendations();")
        elif choice == '8':
            batch_no = input("Enter batch number to trace (default: 'B-CRO-02'): ").strip() or 'B-CRO-02'
            run_query(f"""
                SELECT b.batch_number, m.brand_name, so.invoice_number, so.sale_timestamp,
                       c.full_name AS patient, c.phone, d.doctor_name, soi.quantity
                FROM sales_order_item soi
                JOIN batch b ON soi.batch_id = b.batch_id
                JOIN medicine m ON soi.medicine_id = m.medicine_id
                JOIN sales_order so ON soi.order_id = so.order_id
                LEFT JOIN customer c ON so.customer_id = c.customer_id
                LEFT JOIN prescription p ON so.prescription_id = p.prescription_id
                LEFT JOIN doctor d ON p.doctor_id = d.doctor_id
                WHERE b.batch_number = '{batch_no}';
            """)
        elif choice == '9':
            run_query("SELECT log_id, table_name, operation, record_id, changed_by, changed_at FROM audit_log ORDER BY changed_at DESC LIMIT 10;")
        elif choice == '10':
            run_query("CALL sp_refresh_financial_analytics();")
        elif choice == '0':
            print("Exiting demonstration. Good luck with your Viva!")
            break
        else:
            print("Invalid selection. Please try again.")

if __name__ == '__main__':
    main()
