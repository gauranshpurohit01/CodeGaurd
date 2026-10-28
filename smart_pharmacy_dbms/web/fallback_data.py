"""
Preloaded pharmaceutical fallback dataset for Smart Pharmacy DBMS.
Author: Gauransh Purohit | CSE Department (DBMS Laboratory Project)
Includes all 20 formulary drugs and 41 comprehensive batch lifecycle records.
"""

OVERVIEW_KPI = {
    "total_medicines": 20,
    "active_batches": 37,
    "total_usable_units": 6485,
    "expired_batches_count": 4,
    "capital_at_risk_inr": 184500.00,
    "total_sales_revenue_inr": 10291.50
}

MEDICINES_LIST = [
    {"medicine_id": 1, "brand_name": "Crocin 650", "generic_name": "Paracetamol", "dosage_form": "Tablet", "strength": "650 mg", "category_name": "Analgesics & Antipyretics", "reorder_level": 100, "target_stock_level": 600},
    {"medicine_id": 2, "brand_name": "Augmentin 625 Duo", "generic_name": "Amoxicillin + Potassium Clavulanate", "dosage_form": "Tablet", "strength": "625 mg", "category_name": "Antibiotics & Antimicrobials", "reorder_level": 80, "target_stock_level": 450},
    {"medicine_id": 3, "brand_name": "Glycomet 500", "generic_name": "Metformin Hydrochloride", "dosage_form": "Tablet", "strength": "500 mg", "category_name": "Antidiabetic Drugs", "reorder_level": 150, "target_stock_level": 800},
    {"medicine_id": 4, "brand_name": "Azee 500", "generic_name": "Azithromycin", "dosage_form": "Tablet", "strength": "500 mg", "category_name": "Antibiotics & Antimicrobials", "reorder_level": 50, "target_stock_level": 300},
    {"medicine_id": 5, "brand_name": "Atorva 20", "generic_name": "Atorvastatin Calcium", "dosage_form": "Tablet", "strength": "20 mg", "category_name": "Cardiovascular & Antihypertensive", "reorder_level": 60, "target_stock_level": 350},
    {"medicine_id": 6, "brand_name": "Pan 40", "generic_name": "Pantoprazole Sodium", "dosage_form": "Tablet", "strength": "40 mg", "category_name": "Gastrointestinal & Antacids", "reorder_level": 100, "target_stock_level": 500},
    {"medicine_id": 7, "brand_name": "Huminsulin N 100IU", "generic_name": "Human Insulin Isophane (NPH)", "dosage_form": "Vial", "strength": "100 IU/ml (10ml)", "category_name": "Cold Chain Biologics & Vaccines", "reorder_level": 30, "target_stock_level": 120},
    {"medicine_id": 8, "brand_name": "Asthalin Inhaler", "generic_name": "Salbutamol Sulphate", "dosage_form": "Inhaler", "strength": "100 mcg (200 doses)", "category_name": "Respiratory & Bronchodilators", "reorder_level": 40, "target_stock_level": 200},
    {"medicine_id": 9, "brand_name": "Ciplox 500", "generic_name": "Ciprofloxacin", "dosage_form": "Tablet", "strength": "500 mg", "category_name": "Antibiotics & Antimicrobials", "reorder_level": 40, "target_stock_level": 250},
    {"medicine_id": 10, "brand_name": "Covaxin", "generic_name": "Inactivated COVID-19 Antigen", "dosage_form": "Vial", "strength": "0.5 ml / dose", "category_name": "Cold Chain Biologics & Vaccines", "reorder_level": 25, "target_stock_level": 100},
    {"medicine_id": 11, "brand_name": "Telma 40", "generic_name": "Telmisartan", "dosage_form": "Tablet", "strength": "40 mg", "category_name": "Cardiovascular & Antihypertensive", "reorder_level": 70, "target_stock_level": 400},
    {"medicine_id": 12, "brand_name": "Cetcip 10", "generic_name": "Cetirizine Hydrochloride", "dosage_form": "Tablet", "strength": "10 mg", "category_name": "Analgesics & Antipyretics", "reorder_level": 80, "target_stock_level": 500},
    {"medicine_id": 13, "brand_name": "Combiflam", "generic_name": "Ibuprofen + Paracetamol", "dosage_form": "Tablet", "strength": "400mg + 325mg", "category_name": "Analgesics & Antipyretics", "reorder_level": 90, "target_stock_level": 600},
    {"medicine_id": 14, "brand_name": "Omez 20", "generic_name": "Omeprazole", "dosage_form": "Capsule", "strength": "20 mg", "category_name": "Gastrointestinal & Antacids", "reorder_level": 60, "target_stock_level": 350},
    {"medicine_id": 15, "brand_name": "Montair LC", "generic_name": "Montelukast + Levocetirizine", "dosage_form": "Tablet", "strength": "10mg + 5mg", "category_name": "Respiratory & Bronchodilators", "reorder_level": 50, "target_stock_level": 300},
    {"medicine_id": 16, "brand_name": "Razo-D", "generic_name": "Rabeprazole + Domperidone", "dosage_form": "Capsule", "strength": "20mg + 30mg", "category_name": "Gastrointestinal & Antacids", "reorder_level": 70, "target_stock_level": 400},
    {"medicine_id": 17, "brand_name": "Amaryl 2mg", "generic_name": "Glimepiride", "dosage_form": "Tablet", "strength": "2 mg", "category_name": "Antidiabetic Drugs", "reorder_level": 60, "target_stock_level": 300},
    {"medicine_id": 18, "brand_name": "Clopilet 75", "generic_name": "Clopidogrel", "dosage_form": "Tablet", "strength": "75 mg", "category_name": "Cardiovascular & Antihypertensive", "reorder_level": 50, "target_stock_level": 250},
    {"medicine_id": 19, "brand_name": "Budecort 0.5mg", "generic_name": "Budecort Respules", "dosage_form": "Respule", "strength": "0.5 mg / 2ml", "category_name": "Respiratory & Bronchodilators", "reorder_level": 30, "target_stock_level": 150},
    {"medicine_id": 20, "brand_name": "GeneVac-B", "generic_name": "Hepatitis B Recombinant Vaccine", "dosage_form": "Vial", "strength": "1.0 ml", "category_name": "Cold Chain Biologics & Vaccines", "reorder_level": 20, "target_stock_level": 80}
]

CUSTOMERS_LIST = [
    {"customer_id": 1, "full_name": "Rahul Deshmukh", "phone": "+91-9821098765"},
    {"customer_id": 2, "full_name": "Sunita Kulkarni", "phone": "+91-9876543210"},
    {"customer_id": 3, "full_name": "Amitabh Sen", "phone": "+91-9123456789"},
    {"customer_id": 4, "full_name": "Deepika Nair", "phone": "+91-9988776655"},
    {"customer_id": 5, "full_name": "Vikram Singhania", "phone": "+91-9810012345"},
    {"customer_id": 6, "full_name": "Pooja Agarwal", "phone": "+91-9820054321"},
    {"customer_id": 7, "full_name": "Mohammad Farooq", "phone": "+91-9845011223"},
    {"customer_id": 8, "full_name": "Kavita Iyer", "phone": "+91-9884033445"},
    {"customer_id": 9, "full_name": "Gurpreet Singh", "phone": "+91-9814055667"},
    {"customer_id": 10, "full_name": "Ananya Chatterjee", "phone": "+91-9830077889"}
]

ALL_BATCHES_DATA = [
    # 1. Crocin 650
    {"batch_id": 1, "medicine_id": 1, "batch_number": "B-CRO-EX1", "brand_name": "Crocin 650", "generic_name": "Paracetamol", "expiry_date": "2026-08-10", "days_remaining": -72, "days_until_expiry": -72, "quantity_available": 60, "quantity_received": 300, "purchase_cost": 17.50, "selling_price": 30.00, "mrp": 32.00, "rack_location": "A-R-01 (S-01)", "status": "EXPIRED", "risk_urgency_tier": "CRITICAL: ALREADY EXPIRED (QUARANTINE IMMEDIATELY)", "capital_at_risk_inr": 1050.00},
    {"batch_id": 2, "medicine_id": 1, "batch_number": "B-CRO-02", "brand_name": "Crocin 650", "generic_name": "Paracetamol", "expiry_date": "2026-11-05", "days_remaining": 15, "days_until_expiry": 15, "quantity_available": 75, "quantity_received": 400, "purchase_cost": 19.00, "selling_price": 31.00, "mrp": 33.00, "rack_location": "A-R-01 (S-01)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "URGENT: EXPIRES IN <30 DAYS (DISCOUNT / FEFO PRIORITIZE)", "capital_at_risk_inr": 1425.00},
    {"batch_id": 3, "medicine_id": 1, "batch_number": "B-CRO-03", "brand_name": "Crocin 650", "generic_name": "Paracetamol", "expiry_date": "2027-04-15", "days_remaining": 541, "days_until_expiry": 541, "quantity_available": 420, "quantity_received": 500, "purchase_cost": 20.00, "selling_price": 32.50, "mrp": 35.00, "rack_location": "A-R-01 (S-02)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},
    {"batch_id": 4, "medicine_id": 1, "batch_number": "B-CRO-04", "brand_name": "Crocin 650", "generic_name": "Paracetamol", "expiry_date": "2028-01-10", "days_remaining": 811, "days_until_expiry": 811, "quantity_available": 590, "quantity_received": 600, "purchase_cost": 21.00, "selling_price": 33.00, "mrp": 36.00, "rack_location": "A-R-01 (S-02)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 2. Augmentin 625 Duo
    {"batch_id": 5, "medicine_id": 2, "batch_number": "B-AUG-01", "brand_name": "Augmentin 625 Duo", "generic_name": "Amoxicillin + Clavulanate", "expiry_date": "2026-11-12", "days_remaining": 22, "days_until_expiry": 22, "quantity_available": 35, "quantity_received": 200, "purchase_cost": 120.00, "selling_price": 195.00, "mrp": 210.00, "rack_location": "A-R-02 (S-01)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "URGENT: EXPIRES IN <30 DAYS (DISCOUNT / FEFO PRIORITIZE)", "capital_at_risk_inr": 4200.00},
    {"batch_id": 6, "medicine_id": 2, "batch_number": "B-AUG-02", "brand_name": "Augmentin 625 Duo", "generic_name": "Amoxicillin + Clavulanate", "expiry_date": "2026-12-15", "days_remaining": 55, "days_until_expiry": 55, "quantity_available": 140, "quantity_received": 300, "purchase_cost": 125.00, "selling_price": 205.00, "mrp": 220.00, "rack_location": "A-R-02 (S-01)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "WARNING: EXPIRES IN 31-60 DAYS (MONITOR CLOSELY)", "capital_at_risk_inr": 17500.00},
    {"batch_id": 7, "medicine_id": 2, "batch_number": "B-AUG-03", "brand_name": "Augmentin 625 Duo", "generic_name": "Amoxicillin + Clavulanate", "expiry_date": "2027-09-01", "days_remaining": 314, "days_until_expiry": 314, "quantity_available": 380, "quantity_received": 400, "purchase_cost": 130.00, "selling_price": 210.00, "mrp": 225.00, "rack_location": "A-R-02 (S-02)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 3. Glycomet 500
    {"batch_id": 8, "medicine_id": 3, "batch_number": "B-GLY-EX", "brand_name": "Glycomet 500", "generic_name": "Metformin Hydrochloride", "expiry_date": "2026-09-01", "days_remaining": -50, "days_until_expiry": -50, "quantity_available": 80, "quantity_received": 400, "purchase_cost": 20.00, "selling_price": 38.00, "mrp": 42.00, "rack_location": "B-R-01 (S-01)", "status": "EXPIRED", "risk_urgency_tier": "CRITICAL: ALREADY EXPIRED (QUARANTINE IMMEDIATELY)", "capital_at_risk_inr": 1600.00},
    {"batch_id": 9, "medicine_id": 3, "batch_number": "B-GLY-01", "brand_name": "Glycomet 500", "generic_name": "Metformin Hydrochloride", "expiry_date": "2026-11-20", "days_remaining": 30, "days_until_expiry": 30, "quantity_available": 95, "quantity_received": 600, "purchase_cost": 22.00, "selling_price": 40.00, "mrp": 45.00, "rack_location": "B-R-01 (S-01)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "URGENT: EXPIRES IN <30 DAYS (DISCOUNT / FEFO PRIORITIZE)", "capital_at_risk_inr": 2090.00},
    {"batch_id": 10, "medicine_id": 3, "batch_number": "B-GLY-02", "brand_name": "Glycomet 500", "generic_name": "Metformin Hydrochloride", "expiry_date": "2027-06-15", "days_remaining": 237, "days_until_expiry": 237, "quantity_available": 650, "quantity_received": 800, "purchase_cost": 23.00, "selling_price": 42.00, "mrp": 46.00, "rack_location": "B-R-01 (S-02)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},
    {"batch_id": 11, "medicine_id": 3, "batch_number": "B-GLY-03", "brand_name": "Glycomet 500", "generic_name": "Metformin Hydrochloride", "expiry_date": "2028-02-10", "days_remaining": 477, "days_until_expiry": 477, "quantity_available": 780, "quantity_received": 800, "purchase_cost": 24.00, "selling_price": 44.00, "mrp": 48.00, "rack_location": "B-R-01 (S-02)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 4. Azee 500
    {"batch_id": 12, "medicine_id": 4, "batch_number": "B-AZE-01", "brand_name": "Azee 500", "generic_name": "Azithromycin", "expiry_date": "2026-11-28", "days_remaining": 38, "days_until_expiry": 38, "quantity_available": 20, "quantity_received": 200, "purchase_cost": 75.00, "selling_price": 125.00, "mrp": 135.00, "rack_location": "A-R-01 (S-02)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "WARNING: EXPIRES IN 31-60 DAYS (MONITOR CLOSELY)", "capital_at_risk_inr": 1500.00},
    {"batch_id": 13, "medicine_id": 4, "batch_number": "B-AZE-02", "brand_name": "Azee 500", "generic_name": "Azithromycin", "expiry_date": "2027-09-10", "days_remaining": 324, "days_until_expiry": 324, "quantity_available": 22, "quantity_received": 250, "purchase_cost": 78.00, "selling_price": 130.00, "mrp": 140.00, "rack_location": "A-R-01 (S-02)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 5. Atorva 20
    {"batch_id": 14, "medicine_id": 5, "batch_number": "B-ATO-01", "brand_name": "Atorva 20", "generic_name": "Atorvastatin Calcium", "expiry_date": "2026-12-10", "days_remaining": 50, "days_until_expiry": 50, "quantity_available": 110, "quantity_received": 300, "purchase_cost": 95.00, "selling_price": 165.00, "mrp": 180.00, "rack_location": "B-R-02 (S-01)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "WARNING: EXPIRES IN 31-60 DAYS (MONITOR CLOSELY)", "capital_at_risk_inr": 10450.00},
    {"batch_id": 15, "medicine_id": 5, "batch_number": "B-ATO-02", "brand_name": "Atorva 20", "generic_name": "Atorvastatin Calcium", "expiry_date": "2028-01-20", "days_remaining": 456, "days_until_expiry": 456, "quantity_available": 380, "quantity_received": 400, "purchase_cost": 98.00, "selling_price": 170.00, "mrp": 185.00, "rack_location": "B-R-02 (S-01)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 6. Pan 40
    {"batch_id": 16, "medicine_id": 6, "batch_number": "B-PAN-01", "brand_name": "Pan 40", "generic_name": "Pantoprazole Sodium", "expiry_date": "2026-11-18", "days_remaining": 28, "days_until_expiry": 28, "quantity_available": 85, "quantity_received": 400, "purchase_cost": 55.00, "selling_price": 98.00, "mrp": 110.00, "rack_location": "A-R-01 (S-01)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "URGENT: EXPIRES IN <30 DAYS (DISCOUNT / FEFO PRIORITIZE)", "capital_at_risk_inr": 4675.00},
    {"batch_id": 17, "medicine_id": 6, "batch_number": "B-PAN-02", "brand_name": "Pan 40", "generic_name": "Pantoprazole Sodium", "expiry_date": "2027-08-15", "days_remaining": 298, "days_until_expiry": 298, "quantity_available": 460, "quantity_received": 500, "purchase_cost": 58.00, "selling_price": 102.00, "mrp": 115.00, "rack_location": "A-R-01 (S-01)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 7. Huminsulin N 100IU
    {"batch_id": 18, "medicine_id": 7, "batch_number": "B-INS-01", "brand_name": "Huminsulin N 100IU", "generic_name": "Human Insulin Isophane", "expiry_date": "2026-11-08", "days_remaining": 18, "days_until_expiry": 18, "quantity_available": 10, "quantity_received": 60, "purchase_cost": 210.00, "selling_price": 350.00, "mrp": 380.00, "rack_location": "COLD-FRIDGE-01 (TOP)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "URGENT: EXPIRES IN <30 DAYS (DISCOUNT / FEFO PRIORITIZE)", "capital_at_risk_inr": 2100.00},
    {"batch_id": 19, "medicine_id": 7, "batch_number": "B-INS-02", "brand_name": "Huminsulin N 100IU", "generic_name": "Human Insulin Isophane", "expiry_date": "2027-04-10", "days_remaining": 171, "days_until_expiry": 171, "quantity_available": 88, "quantity_received": 100, "purchase_cost": 215.00, "selling_price": 360.00, "mrp": 390.00, "rack_location": "COLD-FRIDGE-01 (TOP)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 8. Asthalin Inhaler
    {"batch_id": 20, "medicine_id": 8, "batch_number": "B-AST-01", "brand_name": "Asthalin Inhaler", "generic_name": "Salbutamol Sulphate", "expiry_date": "2026-12-01", "days_remaining": 41, "days_until_expiry": 41, "quantity_available": 30, "quantity_received": 120, "purchase_cost": 85.00, "selling_price": 150.00, "mrp": 165.00, "rack_location": "A-R-02 (S-01)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "WARNING: EXPIRES IN 31-60 DAYS (MONITOR CLOSELY)", "capital_at_risk_inr": 2550.00},
    {"batch_id": 21, "medicine_id": 8, "batch_number": "B-AST-02", "brand_name": "Asthalin Inhaler", "generic_name": "Salbutamol Sulphate", "expiry_date": "2027-07-15", "days_remaining": 267, "days_until_expiry": 267, "quantity_available": 175, "quantity_received": 200, "purchase_cost": 88.00, "selling_price": 155.00, "mrp": 170.00, "rack_location": "A-R-02 (S-01)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 9. Ciplox 500
    {"batch_id": 22, "medicine_id": 9, "batch_number": "B-CIP-EX", "brand_name": "Ciplox 500", "generic_name": "Ciprofloxacin", "expiry_date": "2026-05-01", "days_remaining": -173, "days_until_expiry": -173, "quantity_available": 70, "quantity_received": 200, "purchase_cost": 30.00, "selling_price": 52.00, "mrp": 60.00, "rack_location": "A-R-02 (S-02)", "status": "EXPIRED", "risk_urgency_tier": "CRITICAL: ALREADY EXPIRED (QUARANTINE IMMEDIATELY)", "capital_at_risk_inr": 2100.00},
    {"batch_id": 23, "medicine_id": 9, "batch_number": "B-CIP-01", "brand_name": "Ciplox 500", "generic_name": "Ciprofloxacin", "expiry_date": "2027-08-10", "days_remaining": 293, "days_until_expiry": 293, "quantity_available": 240, "quantity_received": 300, "purchase_cost": 32.00, "selling_price": 55.00, "mrp": 62.00, "rack_location": "A-R-02 (S-02)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 10. Covaxin
    {"batch_id": 24, "medicine_id": 10, "batch_number": "B-COV-EX", "brand_name": "Covaxin", "generic_name": "Inactivated COVID-19 Antigen", "expiry_date": "2026-07-10", "days_remaining": -103, "days_until_expiry": -103, "quantity_available": 15, "quantity_received": 50, "purchase_cost": 440.00, "selling_price": 750.00, "mrp": 800.00, "rack_location": "COLD-FRIDGE-01 (MID)", "status": "EXPIRED", "risk_urgency_tier": "CRITICAL: ALREADY EXPIRED (QUARANTINE IMMEDIATELY)", "capital_at_risk_inr": 6600.00},
    {"batch_id": 25, "medicine_id": 10, "batch_number": "B-COV-01", "brand_name": "Covaxin", "generic_name": "Inactivated COVID-19 Antigen", "expiry_date": "2027-02-15", "days_remaining": 117, "days_until_expiry": 117, "quantity_available": 48, "quantity_received": 60, "purchase_cost": 450.00, "selling_price": 750.00, "mrp": 800.00, "rack_location": "COLD-FRIDGE-01 (MID)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 11. Telma 40
    {"batch_id": 26, "medicine_id": 11, "batch_number": "B-TEL-01", "brand_name": "Telma 40", "generic_name": "Telmisartan", "expiry_date": "2026-11-25", "days_remaining": 35, "days_until_expiry": 35, "quantity_available": 45, "quantity_received": 300, "purchase_cost": 62.00, "selling_price": 108.00, "mrp": 120.00, "rack_location": "B-R-01 (S-01)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "WARNING: EXPIRES IN 31-60 DAYS (MONITOR CLOSELY)", "capital_at_risk_inr": 2790.00},
    {"batch_id": 27, "medicine_id": 11, "batch_number": "B-TEL-02", "brand_name": "Telma 40", "generic_name": "Telmisartan", "expiry_date": "2028-01-05", "days_remaining": 441, "days_until_expiry": 441, "quantity_available": 370, "quantity_received": 400, "purchase_cost": 65.00, "selling_price": 112.00, "mrp": 125.00, "rack_location": "B-R-01 (S-01)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 12. Cetcip 10
    {"batch_id": 28, "medicine_id": 12, "batch_number": "B-CET-01", "brand_name": "Cetcip 10", "generic_name": "Cetirizine Hydrochloride", "expiry_date": "2027-03-15", "days_remaining": 145, "days_until_expiry": 145, "quantity_available": 410, "quantity_received": 500, "purchase_cost": 12.00, "selling_price": 22.00, "mrp": 25.00, "rack_location": "A-R-01 (S-02)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 13. Combiflam
    {"batch_id": 29, "medicine_id": 13, "batch_number": "B-COM-01", "brand_name": "Combiflam", "generic_name": "Ibuprofen + Paracetamol", "expiry_date": "2026-11-15", "days_remaining": 25, "days_until_expiry": 25, "quantity_available": 80, "quantity_received": 500, "purchase_cost": 25.00, "selling_price": 44.00, "mrp": 48.00, "rack_location": "A-R-01 (S-01)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "URGENT: EXPIRES IN <30 DAYS (DISCOUNT / FEFO PRIORITIZE)", "capital_at_risk_inr": 2000.00},
    {"batch_id": 30, "medicine_id": 13, "batch_number": "B-COM-02", "brand_name": "Combiflam", "generic_name": "Ibuprofen + Paracetamol", "expiry_date": "2028-02-01", "days_remaining": 468, "days_until_expiry": 468, "quantity_available": 540, "quantity_received": 600, "purchase_cost": 27.00, "selling_price": 47.00, "mrp": 52.00, "rack_location": "A-R-01 (S-01)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 14. Omez 20
    {"batch_id": 31, "medicine_id": 14, "batch_number": "B-OMZ-01", "brand_name": "Omez 20", "generic_name": "Omeprazole", "expiry_date": "2027-05-10", "days_remaining": 201, "days_until_expiry": 201, "quantity_available": 290, "quantity_received": 350, "purchase_cost": 40.00, "selling_price": 72.00, "mrp": 80.00, "rack_location": "A-R-01 (S-02)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 15. Montair LC
    {"batch_id": 32, "medicine_id": 15, "batch_number": "B-MLC-01", "brand_name": "Montair LC", "generic_name": "Montelukast + Levocetirizine", "expiry_date": "2026-12-20", "days_remaining": 60, "days_until_expiry": 60, "quantity_available": 65, "quantity_received": 250, "purchase_cost": 110.00, "selling_price": 190.00, "mrp": 210.00, "rack_location": "A-R-02 (S-01)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "WARNING: EXPIRES IN 31-60 DAYS (MONITOR CLOSELY)", "capital_at_risk_inr": 7150.00},
    {"batch_id": 33, "medicine_id": 15, "batch_number": "B-MLC-02", "brand_name": "Montair LC", "generic_name": "Montelukast + Levocetirizine", "expiry_date": "2028-03-10", "days_remaining": 506, "days_until_expiry": 506, "quantity_available": 280, "quantity_received": 300, "purchase_cost": 115.00, "selling_price": 198.00, "mrp": 218.00, "rack_location": "A-R-02 (S-01)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 16. Razo-D
    {"batch_id": 34, "medicine_id": 16, "batch_number": "B-RZD-01", "brand_name": "Razo-D", "generic_name": "Rabeprazole + Domperidone", "expiry_date": "2027-09-01", "days_remaining": 315, "days_until_expiry": 315, "quantity_available": 240, "quantity_received": 300, "purchase_cost": 105.00, "selling_price": 180.00, "mrp": 198.00, "rack_location": "B-R-02 (S-01)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 17. Amaryl 2mg
    {"batch_id": 35, "medicine_id": 17, "batch_number": "B-AMY-01", "brand_name": "Amaryl 2mg", "generic_name": "Glimepiride", "expiry_date": "2026-12-05", "days_remaining": 45, "days_until_expiry": 45, "quantity_available": 40, "quantity_received": 200, "purchase_cost": 85.00, "selling_price": 145.00, "mrp": 160.00, "rack_location": "B-R-01 (S-02)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "WARNING: EXPIRES IN 31-60 DAYS (MONITOR CLOSELY)", "capital_at_risk_inr": 3400.00},
    {"batch_id": 36, "medicine_id": 17, "batch_number": "B-AMY-02", "brand_name": "Amaryl 2mg", "generic_name": "Glimepiride", "expiry_date": "2028-02-15", "days_remaining": 482, "days_until_expiry": 482, "quantity_available": 275, "quantity_received": 300, "purchase_cost": 88.00, "selling_price": 150.00, "mrp": 165.00, "rack_location": "B-R-01 (S-02)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 18. Clopilet 75
    {"batch_id": 37, "medicine_id": 18, "batch_number": "B-CLO-01", "brand_name": "Clopilet 75", "generic_name": "Clopidogrel", "expiry_date": "2027-04-01", "days_remaining": 162, "days_until_expiry": 162, "quantity_available": 180, "quantity_received": 250, "purchase_cost": 70.00, "selling_price": 122.00, "mrp": 135.00, "rack_location": "B-R-02 (S-01)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 19. Budecort 0.5mg
    {"batch_id": 38, "medicine_id": 19, "batch_number": "B-BUD-01", "brand_name": "Budecort 0.5mg", "generic_name": "Budecort Respules", "expiry_date": "2026-11-20", "days_remaining": 30, "days_until_expiry": 30, "quantity_available": 25, "quantity_received": 150, "purchase_cost": 45.00, "selling_price": 78.00, "mrp": 85.00, "rack_location": "A-R-02 (S-01)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "URGENT: EXPIRES IN <30 DAYS (DISCOUNT / FEFO PRIORITIZE)", "capital_at_risk_inr": 1125.00},
    {"batch_id": 39, "medicine_id": 19, "batch_number": "B-BUD-02", "brand_name": "Budecort 0.5mg", "generic_name": "Budecort Respules", "expiry_date": "2027-07-20", "days_remaining": 272, "days_until_expiry": 272, "quantity_available": 185, "quantity_received": 200, "purchase_cost": 48.00, "selling_price": 82.00, "mrp": 90.00, "rack_location": "A-R-02 (S-01)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00},

    # 20. GeneVac-B
    {"batch_id": 40, "medicine_id": 20, "batch_number": "B-HVB-01", "brand_name": "GeneVac-B", "generic_name": "Hepatitis B Vaccine", "expiry_date": "2026-11-15", "days_remaining": 25, "days_until_expiry": 25, "quantity_available": 12, "quantity_received": 60, "purchase_cost": 180.00, "selling_price": 290.00, "mrp": 320.00, "rack_location": "COLD-FRIDGE-01 (BOTTOM)", "status": "NEAR_EXPIRY", "risk_urgency_tier": "URGENT: EXPIRES IN <30 DAYS (DISCOUNT / FEFO PRIORITIZE)", "capital_at_risk_inr": 2160.00},
    {"batch_id": 41, "medicine_id": 20, "batch_number": "B-HVB-02", "brand_name": "GeneVac-B", "generic_name": "Hepatitis B Vaccine", "expiry_date": "2027-07-10", "days_remaining": 262, "days_until_expiry": 262, "quantity_available": 72, "quantity_received": 80, "purchase_cost": 190.00, "selling_price": 305.00, "mrp": 335.00, "rack_location": "COLD-FRIDGE-01 (BOTTOM)", "status": "ACTIVE", "risk_urgency_tier": "SAFE: EXPIRES IN >90 DAYS", "capital_at_risk_inr": 0.00}
]

# Radar dataset includes all batches that are Expired or Expiring soon, sorted by expiry date
EXPIRY_RADAR_DATA = [
    b for b in ALL_BATCHES_DATA if b["days_remaining"] <= 90
]
EXPIRY_RADAR_DATA.sort(key=lambda x: x["days_remaining"])

INVENTORY_OVERVIEW_DATA = [
    {"medicine_id": 1, "brand_name": "Crocin 650", "generic_name": "Paracetamol", "category_name": "Analgesics & Antipyretics", "dosage_form": "Tablet", "strength": "650 mg", "total_usable_stock": 1085, "expired_stock_on_shelf": 60, "active_batch_count": 3, "next_expiring_batch_date": "2026-11-05", "stock_status": "ADEQUATE", "reorder_level": 100, "target_stock_level": 600},
    {"medicine_id": 2, "brand_name": "Augmentin 625 Duo", "generic_name": "Amoxicillin + Clavulanate", "category_name": "Antibiotics & Antimicrobials", "dosage_form": "Tablet", "strength": "625 mg", "total_usable_stock": 555, "expired_stock_on_shelf": 0, "active_batch_count": 3, "next_expiring_batch_date": "2026-11-12", "stock_status": "ADEQUATE", "reorder_level": 80, "target_stock_level": 450},
    {"medicine_id": 3, "brand_name": "Glycomet 500", "generic_name": "Metformin Hydrochloride", "category_name": "Antidiabetic Drugs", "dosage_form": "Tablet", "strength": "500 mg", "total_usable_stock": 1525, "expired_stock_on_shelf": 80, "active_batch_count": 3, "next_expiring_batch_date": "2026-11-20", "stock_status": "ADEQUATE", "reorder_level": 150, "target_stock_level": 800},
    {"medicine_id": 4, "brand_name": "Azee 500", "generic_name": "Azithromycin", "category_name": "Antibiotics & Antimicrobials", "dosage_form": "Tablet", "strength": "500 mg", "total_usable_stock": 42, "expired_stock_on_shelf": 0, "active_batch_count": 2, "next_expiring_batch_date": "2026-11-28", "stock_status": "REORDER_REQUIRED", "reorder_level": 50, "target_stock_level": 300},
    {"medicine_id": 5, "brand_name": "Atorva 20", "generic_name": "Atorvastatin Calcium", "category_name": "Cardiovascular & Antihypertensive", "dosage_form": "Tablet", "strength": "20 mg", "total_usable_stock": 490, "expired_stock_on_shelf": 0, "active_batch_count": 2, "next_expiring_batch_date": "2026-12-10", "stock_status": "ADEQUATE", "reorder_level": 60, "target_stock_level": 350},
    {"medicine_id": 6, "brand_name": "Pan 40", "generic_name": "Pantoprazole Sodium", "category_name": "Gastrointestinal & Antacids", "dosage_form": "Tablet", "strength": "40 mg", "total_usable_stock": 545, "expired_stock_on_shelf": 0, "active_batch_count": 2, "next_expiring_batch_date": "2026-11-18", "stock_status": "ADEQUATE", "reorder_level": 100, "target_stock_level": 500},
    {"medicine_id": 7, "brand_name": "Huminsulin N 100IU", "generic_name": "Human Insulin Isophane", "category_name": "Cold Chain Biologics & Vaccines", "dosage_form": "Vial", "strength": "100 IU/ml", "total_usable_stock": 98, "expired_stock_on_shelf": 0, "active_batch_count": 2, "next_expiring_batch_date": "2026-11-08", "stock_status": "ADEQUATE", "reorder_level": 30, "target_stock_level": 120},
    {"medicine_id": 8, "brand_name": "Asthalin Inhaler", "generic_name": "Salbutamol Sulphate", "category_name": "Respiratory & Bronchodilators", "dosage_form": "Inhaler", "strength": "100 mcg", "total_usable_stock": 205, "expired_stock_on_shelf": 0, "active_batch_count": 2, "next_expiring_batch_date": "2026-12-01", "stock_status": "ADEQUATE", "reorder_level": 40, "target_stock_level": 200},
    {"medicine_id": 9, "brand_name": "Ciplox 500", "generic_name": "Ciprofloxacin", "category_name": "Antibiotics & Antimicrobials", "dosage_form": "Tablet", "strength": "500 mg", "total_usable_stock": 240, "expired_stock_on_shelf": 70, "active_batch_count": 1, "next_expiring_batch_date": "2027-08-10", "stock_status": "ADEQUATE", "reorder_level": 40, "target_stock_level": 250},
    {"medicine_id": 10, "brand_name": "Covaxin", "generic_name": "Inactivated COVID-19 Antigen", "category_name": "Cold Chain Biologics & Vaccines", "dosage_form": "Vial", "strength": "0.5 ml", "total_usable_stock": 48, "expired_stock_on_shelf": 15, "active_batch_count": 1, "next_expiring_batch_date": "2027-02-15", "stock_status": "ADEQUATE", "reorder_level": 25, "target_stock_level": 100},
    {"medicine_id": 11, "brand_name": "Telma 40", "generic_name": "Telmisartan", "category_name": "Cardiovascular & Antihypertensive", "dosage_form": "Tablet", "strength": "40 mg", "total_usable_stock": 415, "expired_stock_on_shelf": 0, "active_batch_count": 2, "next_expiring_batch_date": "2026-11-25", "stock_status": "ADEQUATE", "reorder_level": 70, "target_stock_level": 400},
    {"medicine_id": 12, "brand_name": "Cetcip 10", "generic_name": "Cetirizine Hydrochloride", "category_name": "Analgesics & Antipyretics", "dosage_form": "Tablet", "strength": "10 mg", "total_usable_stock": 410, "expired_stock_on_shelf": 0, "active_batch_count": 1, "next_expiring_batch_date": "2027-03-15", "stock_status": "ADEQUATE", "reorder_level": 80, "target_stock_level": 500},
    {"medicine_id": 13, "brand_name": "Combiflam", "generic_name": "Ibuprofen + Paracetamol", "category_name": "Analgesics & Antipyretics", "dosage_form": "Tablet", "strength": "400mg + 325mg", "total_usable_stock": 620, "expired_stock_on_shelf": 0, "active_batch_count": 2, "next_expiring_batch_date": "2026-11-15", "stock_status": "ADEQUATE", "reorder_level": 90, "target_stock_level": 600},
    {"medicine_id": 14, "brand_name": "Omez 20", "generic_name": "Omeprazole", "category_name": "Gastrointestinal & Antacids", "dosage_form": "Capsule", "strength": "20 mg", "total_usable_stock": 290, "expired_stock_on_shelf": 0, "active_batch_count": 1, "next_expiring_batch_date": "2027-05-10", "stock_status": "ADEQUATE", "reorder_level": 60, "target_stock_level": 350},
    {"medicine_id": 15, "brand_name": "Montair LC", "generic_name": "Montelukast + Levocetirizine", "category_name": "Respiratory & Bronchodilators", "dosage_form": "Tablet", "strength": "10mg + 5mg", "total_usable_stock": 345, "expired_stock_on_shelf": 0, "active_batch_count": 2, "next_expiring_batch_date": "2026-12-20", "stock_status": "ADEQUATE", "reorder_level": 50, "target_stock_level": 300},
    {"medicine_id": 16, "brand_name": "Razo-D", "generic_name": "Rabeprazole + Domperidone", "category_name": "Gastrointestinal & Antacids", "dosage_form": "Capsule", "strength": "20mg + 30mg", "total_usable_stock": 240, "expired_stock_on_shelf": 0, "active_batch_count": 1, "next_expiring_batch_date": "2027-09-01", "stock_status": "ADEQUATE", "reorder_level": 70, "target_stock_level": 400},
    {"medicine_id": 17, "brand_name": "Amaryl 2mg", "generic_name": "Glimepiride", "category_name": "Antidiabetic Drugs", "dosage_form": "Tablet", "strength": "2 mg", "total_usable_stock": 315, "expired_stock_on_shelf": 0, "active_batch_count": 2, "next_expiring_batch_date": "2026-12-05", "stock_status": "ADEQUATE", "reorder_level": 60, "target_stock_level": 300},
    {"medicine_id": 18, "brand_name": "Clopilet 75", "generic_name": "Clopidogrel", "category_name": "Cardiovascular & Antihypertensive", "dosage_form": "Tablet", "strength": "75 mg", "total_usable_stock": 180, "expired_stock_on_shelf": 0, "active_batch_count": 1, "next_expiring_batch_date": "2027-04-01", "stock_status": "ADEQUATE", "reorder_level": 50, "target_stock_level": 250},
    {"medicine_id": 19, "brand_name": "Budecort 0.5mg", "generic_name": "Budecort Respules", "category_name": "Respiratory & Bronchodilators", "dosage_form": "Respule", "strength": "0.5 mg / 2ml", "total_usable_stock": 210, "expired_stock_on_shelf": 0, "active_batch_count": 2, "next_expiring_batch_date": "2026-11-20", "stock_status": "ADEQUATE", "reorder_level": 30, "target_stock_level": 150},
    {"medicine_id": 20, "brand_name": "GeneVac-B", "generic_name": "Hepatitis B Recombinant Vaccine", "category_name": "Cold Chain Biologics & Vaccines", "dosage_form": "Vial", "strength": "1.0 ml", "total_usable_stock": 84, "expired_stock_on_shelf": 0, "active_batch_count": 2, "next_expiring_batch_date": "2026-11-15", "stock_status": "ADEQUATE", "reorder_level": 20, "target_stock_level": 80}
]

REORDER_SHORTFALL_DATA = [
    {
        "medicine_id": 4, "brand_name": "Azee 500", "generic_name": "Azithromycin",
        "current_active_stock": 42, "reorder_level": 50, "target_stock_level": 300,
        "units_to_order": 258, "preferred_supplier": "MedPlus Wholesale Corp", "estimated_cost_inr": 19350.00
    },
    {
        "medicine_id": 19, "brand_name": "Budecort 0.5mg", "generic_name": "Budecort Respules",
        "current_active_stock": 25, "reorder_level": 30, "target_stock_level": 150,
        "units_to_order": 125, "preferred_supplier": "Apex Healthcare Distributors", "estimated_cost_inr": 5625.00
    },
    {
        "medicine_id": 20, "brand_name": "GeneVac-B", "generic_name": "Hepatitis B Recombinant Vaccine",
        "current_active_stock": 12, "reorder_level": 20, "target_stock_level": 80,
        "units_to_order": 68, "preferred_supplier": "Zenith Cold Chain Solutions", "estimated_cost_inr": 12240.00
    }
]

FINANCIALS_MV_DATA = [
    {
        "financial_month": "2026-10-01", "total_invoices": 5, "units_sold": 90,
        "gross_sales_inr": 10180.00, "cogs_inr": 6245.00, "gross_profit_inr": 3935.00,
        "gross_margin_percentage": 38.65, "units_expired": 50, "expiry_write_off_inr": 950.00,
        "net_operational_margin_inr": 2985.00
    },
    {
        "financial_month": "2026-09-01", "total_invoices": 18, "units_sold": 410,
        "gross_sales_inr": 48200.00, "cogs_inr": 29800.00, "gross_profit_inr": 18400.00,
        "gross_margin_percentage": 38.17, "units_expired": 30, "expiry_write_off_inr": 600.00,
        "net_operational_margin_inr": 17800.00
    }
]

AUDIT_TRAIL_DATA = [
    {"transaction_id": 105, "transaction_time": "2026-10-21T09:15:00Z", "transaction_type": "SALE_DISPENSE", "brand_name": "Asthalin Inhaler", "batch_number": "B-AST-01", "quantity_change": -2, "balance_after": 30, "reference_code": "INV-2026-0005", "remarks": "Dispensed via Point of Sale"},
    {"transaction_id": 104, "transaction_time": "2026-10-20T19:25:00Z", "transaction_type": "SALE_DISPENSE", "brand_name": "Telma 40", "batch_number": "B-TEL-01", "quantity_change": -30, "balance_after": 45, "reference_code": "INV-2026-0004", "remarks": "Dispensed via Point of Sale"},
    {"transaction_id": 103, "transaction_time": "2026-10-20T19:25:00Z", "transaction_type": "SALE_DISPENSE", "brand_name": "Atorva 20", "batch_number": "B-ATO-01", "quantity_change": -10, "balance_after": 110, "reference_code": "INV-2026-0004", "remarks": "Dispensed via Point of Sale"},
    {"transaction_id": 102, "transaction_time": "2026-10-20T18:10:00Z", "transaction_type": "SALE_DISPENSE", "brand_name": "Crocin 650", "batch_number": "B-CRO-02", "quantity_change": -10, "balance_after": 75, "reference_code": "INV-2026-0003", "remarks": "Dispensed via Point of Sale"},
    {"transaction_id": 101, "transaction_time": "2026-10-19T16:45:00Z", "transaction_type": "SALE_DISPENSE", "brand_name": "Augmentin 625 Duo", "batch_number": "B-AUG-01", "quantity_change": -14, "balance_after": 35, "reference_code": "INV-2026-0002", "remarks": "Dispensed via Point of Sale"},
    {"transaction_id": 100, "transaction_time": "2026-10-05T14:30:00Z", "transaction_type": "EXPIRED_DISPOSAL", "brand_name": "Glycomet 500", "batch_number": "B-GLY-EX", "quantity_change": -30, "balance_after": 80, "reference_code": "DISP-20261005-08", "remarks": "Chemical Neutralization by Dr. Sarah Mehta"}
]
