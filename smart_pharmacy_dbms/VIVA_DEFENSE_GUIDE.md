# Viva Voce & Professor Defense Guide
**Smart Pharmacy Inventory, Batch Tracking & Expiry Management System**

Use these prepared responses to answer questions during your project presentation and viva evaluation.

---

### Q1: "Why did you build this system inside PostgreSQL instead of writing the logic in Python/Node.js/Java?"
**Answer:**
> "Professor, in healthcare and pharmacy management, inventory integrity and patient safety are zero-tolerance requirements.
> If business logic like FEFO batch selection or expiry checks resides only in an application server:
> 1. A bug or bypassed validation in one client API could allow an expired drug to be dispensed.
> 2. Network latency between the backend and database during multi-step batch allocation can create race conditions under concurrent checkouts.
> 
> By implementing this logic directly in **PL/pgSQL stored procedures (`sp_dispense_medicine_fefo`) and database triggers (`trg_prevent_expired_dispense`)**, the database engine itself guarantees ACID compliance and enforces the invariants regardless of which frontend or microservice connects to the database."

---

### Q2: "What is FEFO, and how does your database engine implement it?"
**Answer:**
> "FEFO stands for **First-Expired, First-Out**. Unlike FIFO (First-In, First-Out) which dispenses the oldest received batch, FEFO dispenses the batch that expires the earliest.
> In our database, this is implemented in `sp_dispense_medicine_fefo`:
> 1. It opens a cursor ordered strictly by `expiry_date ASC` on active batches.
> 2. It uses `SELECT ... FOR UPDATE` row-level locks to prevent dirty reads or concurrent double-allocation.
> 3. If an order requires more units than the earliest batch possesses, the algorithm performs **split-batch fulfillment**: it drains the earliest batch completely (setting it to `DEPLETED`), and allocates the remainder from the subsequent batch."

---

### Q3: "How is your schema normalized? Show me your 3NF or BCNF design."
**Answer:**
> "The schema is fully normalized to **Boyce-Codd Normal Form (BCNF)**:
> - **1NF**: All table columns are strictly atomic (no comma-separated lists of batch numbers or arrays).
> - **2NF**: Every non-key attribute is fully functionally dependent on the entire primary key. In `sales_order_item`, every line item has a surrogate key `item_id` and unique composite key `(order_id, batch_id)`.
> - **3NF**: There are no transitive dependencies ($X \to Y$ and $Y \to Z$). For example, supplier details (contact, drug license, GSTIN) are isolated in the `supplier` table and only referenced by `supplier_id` in `batch`. Storing supplier contact information in `batch` would create update anomalies and violate 3NF.
> - **BCNF**: For every functional dependency $X \to Y$, $X$ is a superkey."

---

### Q4: "What triggers did you write, and what is the difference between BEFORE and AFTER triggers in your system?"
**Answer:**
> "We implemented both `BEFORE` and `AFTER` triggers for distinct, precise purposes:
> 1. **`BEFORE INSERT ON sales_order_item` (`trg_prevent_expired_dispense`)**:
>    - *Validation Trigger*: Validates that `batch.expiry_date > CURRENT_DATE`, `batch.status != 'QUARANTINED'`, and `quantity <= batch.quantity_available`. If any condition fails, it raises an exception to immediately abort the insert before it touches the table.
> 2. **`AFTER INSERT ON sales_order_item` (`trg_auto_deduct_batch_stock`)**:
>    - *Side-Effect Trigger*: Once the row is safely inserted, it decrements `batch.quantity_available` and inserts an immutable ledger entry into `inventory_transaction`.
> 3. **`AFTER INSERT/UPDATE/DELETE ON sales_order_item` (`trg_recalculate_order_totals`)**:
>    - *Aggregation Trigger*: Recalculates subtotal, tax (5% GST), and net invoice total on the parent `sales_order` table."

---

### Q5: "Explain your indexing strategy. Why did you use Partial Indexes?"
**Answer:**
> "In high-throughput pharmacies, the `batch` table accumulates historical, expired, and depleted batches over years.
> If we use a standard B-Tree index on `(medicine_id, expiry_date)`, the index tree grows large and consumes buffer memory indexing batches with 0 stock that can never be sold.
> 
> Therefore, we implemented a **Filtered Partial Index**:
> ```sql
> CREATE INDEX idx_batch_fefo_active
>     ON batch (medicine_id, expiry_date ASC, batch_id ASC)
>     INCLUDE (quantity_available, selling_price)
>     WHERE quantity_available > 0 AND status IN ('ACTIVE', 'NEAR_EXPIRY');
> ```
> This partial index only indexes active, sellable stock. It is extremely compact, stays resident in PostgreSQL's shared buffer RAM, and allows $O(\log N)$ index-only scans during POS checkouts."

---

### Q6: "Why did you use a Materialized View instead of a standard View for monthly financials?"
**Answer:**
> "A standard view runs its underlying query (multi-table joins between `sales_order`, `sales_order_item`, `batch`, and `quarantine_disposal_log`) on every single query invocation. On millions of rows, this produces unacceptable latency.
> A **Materialized View (`mv_monthly_pharmacy_financials`)** physically stores the aggregated results on disk.
> We also added a unique index on `financial_month` which allows us to execute:
> `REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_pharmacy_financials;`
> This refreshes the analytics in the background without acquiring exclusive table locks, meaning cashier sales are never blocked."

---

### Q7: "How did you implement security and authorization?"
**Answer:**
> "We implemented PostgreSQL **Role-Based Access Control (RBAC)** adhering to the Principle of Least Privilege:
> - `lead_pharmacist`: Can dispense, quarantine, and receive batches.
> - `pharmacy_cashier`: Can insert invoices and query available quantities, but cannot edit batches or delete orders.
> - **Column-Level Security (CLS)**: We explicitly revoked access on `batch.purchase_cost` from `pharmacy_cashier` while granting `SELECT` on `batch.selling_price` and `batch.mrp`. This ensures cashiers can bill customers but cannot see confidential wholesale vendor margins."

---

### Q8: "How does the system handle transactions and ACID compliance?"
**Answer:**
> "In script `09_transactions_demo.sql`:
> - **Atomicity**: An invoice selling multiple drugs is wrapped in a transaction block. If the first drug is valid but the second drug fails (e.g., exceeds available stock or has expired), the entire transaction rolls back completely. Zero stock is deducted for either item.
> - **Isolation**: We use `SELECT ... FOR UPDATE` inside the PL/pgSQL FEFO procedure to prevent concurrent dirty reads and ensure serializable batch allocation."
