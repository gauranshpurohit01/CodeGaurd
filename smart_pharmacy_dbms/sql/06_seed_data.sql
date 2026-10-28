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
