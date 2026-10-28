// ============================================================================
// SMART PHARMACY BATCH TRACKING & EXPIRY MANAGEMENT SYSTEM (SP-BEMS)
// Frontend Reactive Controller & DBMS Engine Bridge
// Author: Gauransh Purohit | B.Tech CSE (DBMS Laboratory Project)
// ============================================================================

let allMedicines = [];
let allBatches = [];

document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function checkEngineStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const badge = document.getElementById('db-engine-badge');
    if (badge) {
      if (data.connected) {
        badge.className = 'student-badge text-[11px] px-2.5 py-0.5 rounded-full font-mono';
        badge.innerHTML = `<i class="fa-solid fa-server mr-1 text-emerald-400"></i> ${data.engine}`;
      } else {
        badge.className = 'badge-critical text-[11px] px-2.5 py-0.5 rounded-full font-mono';
        badge.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-1"></i> Disconnected`;
      }
    }
  } catch (e) {
    console.error('Status check error:', e);
  }
}

async function initApp() {
  await checkEngineStatus();
  await Promise.all([
    loadOverview(),
    loadMedicinesDropdown(),
    loadCustomersDropdown(),
    loadExpiryRadar(),
    loadInventory(),
    loadReorder(),
    loadFinancials(),
    loadAuditTrail()
  ]);
  // Default recall search for Crocin Batch #2
  executeRecallSearch();
}

/**
 * Master State Synchronization
 * Refreshes all 8 modules simultaneously whenever a transaction occurs.
 */
async function syncAllViews(selectedMedId) {
  const medToRefresh = selectedMedId || document.getElementById('dispense-med-select')?.value || 1;
  await Promise.all([
    loadOverview(),
    loadExpiryRadar(),
    updateMedBatchPreview(medToRefresh),
    loadInventory(),
    loadReorder(),
    loadFinancials(),
    loadAuditTrail()
  ]);
}

function switchTab(tabId) {
  const sections = ['dashboard', 'radar', 'dispense', 'inventory', 'reorder', 'recall', 'financials', 'audit'];
  sections.forEach(s => {
    const el = document.getElementById(`view-${s}`);
    const tab = document.getElementById(`tab-${s}`);
    if (!el || !tab) return;
    if (s === tabId) {
      el.classList.remove('hidden');
      tab.classList.add('bg-[#ede9fe]', 'text-[#6d28d9]', 'border-[#ddd6fe]');
      tab.classList.remove('text-[#645f78]', 'border-transparent');
    } else {
      el.classList.add('hidden');
      tab.classList.remove('bg-[#ede9fe]', 'text-[#6d28d9]', 'border-[#ddd6fe]');
      tab.classList.add('text-[#645f78]', 'border-transparent');
    }
  });

  // Reload tab-specific view on switch to ensure latest state
  if (tabId === 'radar') loadExpiryRadar();
  if (tabId === 'inventory') loadInventory();
  if (tabId === 'reorder') loadReorder();
  if (tabId === 'financials') loadFinancials();
  if (tabId === 'audit') loadAuditTrail();
  if (tabId === 'dashboard') loadOverview();
  if (tabId === 'dispense') {
    const medId = document.getElementById('dispense-med-select')?.value || 1;
    updateMedBatchPreview(medId);
  }
}

function showAlert(msg, isSuccess = true) {
  const banner = document.getElementById('alert-banner');
  const box = document.getElementById('alert-box');
  const icon = document.getElementById('alert-icon');
  const text = document.getElementById('alert-msg');

  banner.classList.remove('hidden');
  text.textContent = msg;

  if (isSuccess) {
    box.className = 'p-3.5 rounded-xl flex items-center justify-between border bg-emerald-50 border-emerald-300 text-emerald-900 shadow-md';
    icon.className = 'fa-solid fa-circle-check text-emerald-600 text-base';
  } else {
    box.className = 'p-3.5 rounded-xl flex items-center justify-between border bg-red-50 border-red-300 text-red-900 shadow-md';
    icon.className = 'fa-solid fa-triangle-exclamation text-red-600 text-base';
  }

  setTimeout(() => hideAlert(), 6000);
}

function hideAlert() {
  document.getElementById('alert-banner')?.classList.add('hidden');
}

// ----------------------------------------------------------------------------
// DATA POPULATION & API HANDLERS
// ----------------------------------------------------------------------------

async function loadOverview() {
  try {
    const res = await fetch('/api/overview');
    const data = await res.json();
    const totalMeds = parseInt(data.total_medicines) || 20;
    document.getElementById('kpi-total-meds').textContent = totalMeds;
    document.getElementById('kpi-usable-stock').textContent = (data.total_usable_units || 0).toLocaleString();
    document.getElementById('kpi-capital-risk').textContent = `₹${Math.round(data.capital_at_risk_inr || 0).toLocaleString()}`;
    document.getElementById('kpi-expired-batches').textContent = data.expired_batches_count || 0;

    // Load top 5 near-expiry on dashboard
    const radarRes = await fetch('/api/expiry-radar');
    const radarData = await radarRes.json();
    const tbody = document.getElementById('dashboard-radar-table');
    tbody.innerHTML = '';

    if (!Array.isArray(radarData) || radarData.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-[#847c9b]">No urgent batches currently.</td></tr>';
      return;
    }

    radarData.slice(0, 5).forEach(item => {
      const tr = document.createElement('tr');
      const badgeHtml = formatUrgencyBadge(item.risk_urgency_tier, true);
      tr.innerHTML = `
        <td class="py-3 font-mono text-violet-700 font-semibold">${item.batch_number}</td>
        <td class="py-3 text-[#1e1b2e] font-semibold">${item.brand_name}</td>
        <td class="py-3 font-mono text-[#585172]">${item.expiry_date}</td>
        <td class="py-3 font-bold text-[#1e1b2e]">${item.quantity_available}</td>
        <td class="py-3">${badgeHtml}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading overview:', err);
  }
}

async function loadMedicinesDropdown() {
  try {
    const res = await fetch('/api/medicines-list');
    allMedicines = await res.json();
    if (!Array.isArray(allMedicines)) allMedicines = [];

    const quickSelect = document.getElementById('quick-med-select');
    const dispenseSelect = document.getElementById('dispense-med-select');
    quickSelect.innerHTML = '<option value="">-- Select Drug Formulation --</option>';
    dispenseSelect.innerHTML = '<option value="">-- Select Drug Formulation --</option>';

    allMedicines.forEach(m => {
      const opt = `<option value="${m.medicine_id}">${m.brand_name} (${m.dosage_form} - ${m.strength})</option>`;
      quickSelect.innerHTML += opt;
      dispenseSelect.innerHTML += opt;
    });

    if (allMedicines.length > 0) {
      dispenseSelect.value = allMedicines[0].medicine_id;
      quickSelect.value = allMedicines[0].medicine_id;
      await updateMedBatchPreview(allMedicines[0].medicine_id);
    }
  } catch (err) {
    console.error('Error loading medicines dropdown:', err);
  }
}

async function loadCustomersDropdown() {
  try {
    const res = await fetch('/api/customers');
    let custs = await res.json();
    if (!Array.isArray(custs)) custs = [];
    const select = document.getElementById('dispense-cust-select');
    select.innerHTML = '<option value="">Walk-in Customer (Counter Sale)</option>';
    custs.forEach(c => {
      select.innerHTML += `<option value="${c.customer_id}">${c.full_name} (${c.phone})</option>`;
    });
  } catch (err) {
    console.error('Error loading customers dropdown:', err);
  }
}

async function updateMedBatchPreview(medId) {
  if (!medId) return;
  try {
    const res = await fetch(`/api/batches?medicine_id=${medId}`);
    let batches = await res.json();
    if (!Array.isArray(batches)) batches = [];
    const tbody = document.getElementById('med-batch-preview-table');
    tbody.innerHTML = '';

    if (batches.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-[#847c9b]">No batches currently registered for this drug formulation.</td></tr>';
      return;
    }

    let firstActiveFound = false;

    batches.forEach((b) => {
      const days = b.days_remaining !== undefined ? b.days_remaining : b.days_until_expiry;
      const isExp = days <= 0;
      const isDepleted = b.quantity_available <= 0;
      const isNextPick = !isExp && !isDepleted && !firstActiveFound;
      if (isNextPick) firstActiveFound = true;

      let statusBadge = '';
      if (isExp) {
        statusBadge = '<span class="badge-critical"><span class="badge-dot"></span>Expired</span>';
      } else if (isDepleted) {
        statusBadge = '<span class="badge-depleted"><span class="badge-dot"></span>Depleted</span>';
      } else if (days <= 30) {
        statusBadge = '<span class="badge-urgent"><span class="badge-dot"></span>Near Expiry</span>';
      } else {
        statusBadge = '<span class="badge-safe"><span class="badge-dot"></span>Active</span>';
      }

      const tr = document.createElement('tr');
      if (isNextPick) {
        tr.className = 'bg-emerald-50/80 border-l-4 border-emerald-600';
      } else if (isExp) {
        tr.className = 'opacity-40 line-through';
      }

      tr.innerHTML = `
        <td class="p-3 font-bold ${isNextPick ? 'text-emerald-700' : 'text-[#645f78]'}">
          ${isExp ? '<span class="text-red-700">LOCKED</span>' : (isDepleted ? '-' : (isNextPick ? '<span class="flex items-center gap-1.5"><i class="fa-solid fa-arrow-right text-emerald-600"></i> Next FEFO Pick</span>' : 'Queue'))}
        </td>
        <td class="p-3 font-mono font-semibold text-violet-700">${b.batch_number}</td>
        <td class="p-3 font-mono text-[#585172]">${b.expiry_date} <span class="text-xs text-[#847c9b]">(${days > 0 ? days + 'd' : 'Expired'})</span></td>
        <td class="p-3 font-bold ${b.quantity_available > 0 ? 'text-[#1e1b2e]' : 'text-[#847c9b]'}">${b.quantity_available} / ${b.quantity_received}</td>
        <td class="p-3 font-semibold text-[#585172]">₹${Number(b.selling_price || 30).toFixed(2)}</td>
        <td class="p-3">${statusBadge}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error updating medicine batch preview:', err);
  }
}

async function loadExpiryRadar() {
  try {
    const res = await fetch('/api/expiry-radar');
    const data = await res.json();
    const tbody = document.getElementById('full-radar-table');
    tbody.innerHTML = '';

    const criticalCount = data.filter(d => (d.days_remaining !== undefined ? d.days_remaining : d.days_until_expiry) <= 30).length;
    const badgeEl = document.getElementById('radar-badge');
    if (badgeEl) badgeEl.textContent = criticalCount;

    if (!Array.isArray(data) || data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" class="p-4 text-center text-[#847c9b]">No batches currently on expiry radar.</td></tr>';
      return;
    }

    data.forEach(item => {
      const days = item.days_remaining !== undefined ? item.days_remaining : item.days_until_expiry;
      const tr = document.createElement('tr');
      const badgeHtml = formatUrgencyBadge(item.risk_urgency_tier);
      tr.innerHTML = `
        <td class="p-3 font-mono font-semibold text-violet-700">${item.batch_number}</td>
        <td class="p-3 font-semibold text-[#1e1b2e]">${item.brand_name}</td>
        <td class="p-3 text-[#645f78]">${item.generic_name}</td>
        <td class="p-3 font-mono text-[#585172]">${item.expiry_date}</td>
        <td class="p-3 font-bold ${days <= 0 ? 'text-red-700' : (days <= 30 ? 'text-amber-700' : 'text-[#585172]')}">
          ${days <= 0 ? 'Expired' : days + ' days'}
        </td>
        <td class="p-3 font-bold text-[#1e1b2e]">${item.quantity_available}</td>
        <td class="p-3 font-mono text-[#585172]">₹${Number(item.capital_at_risk_inr || 0).toLocaleString()}</td>
        <td class="p-3 font-mono text-[#645f78]">${item.rack_location}</td>
        <td class="p-3">${badgeHtml}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading radar:', err);
  }
}

async function loadInventory() {
  try {
    const res = await fetch('/api/inventory');
    let data = await res.json();
    const tbody = document.getElementById('inventory-table');
    tbody.innerHTML = '';
    if (!Array.isArray(data)) data = [];

    data.forEach(item => {
      let statusBadge = '<span class="badge-safe"><span class="badge-dot"></span>Adequate</span>';
      if (item.stock_status === 'REORDER_REQUIRED') {
        statusBadge = '<span class="badge-urgent"><span class="badge-dot"></span>Reorder Now</span>';
      } else if (item.stock_status === 'OUT_OF_STOCK') {
        statusBadge = '<span class="badge-critical"><span class="badge-dot"></span>Out of Stock</span>';
      }

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="p-3 font-bold text-[#1e1b2e]">${item.brand_name}</td>
        <td class="p-3 text-[#645f78]">${item.generic_name}</td>
        <td class="p-3 text-[#585172]">${item.category_name}</td>
        <td class="p-3 text-[#585172]">${item.dosage_form} (${item.strength})</td>
        <td class="p-3 font-extrabold text-emerald-700 text-sm font-mono">${item.total_usable_stock}</td>
        <td class="p-3 font-mono ${item.expired_stock_on_shelf > 0 ? 'font-bold text-red-700' : 'text-[#847c9b]'}">${item.expired_stock_on_shelf}</td>
        <td class="p-3 text-[#585172] font-mono">${item.active_batch_count}</td>
        <td class="p-3 font-mono text-[#585172]">${item.next_expiring_batch_date || 'N/A'}</td>
        <td class="p-3">${statusBadge}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading inventory:', err);
  }
}

async function loadReorder() {
  try {
    const res = await fetch('/api/reorder');
    let data = await res.json();
    const tbody = document.getElementById('reorder-table');
    tbody.innerHTML = '';

    if (!Array.isArray(data) || data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="p-4 text-center text-emerald-700 font-medium">All drug formulations currently meet target inventory levels!</td></tr>';
      return;
    }

    data.forEach(item => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="p-3 font-bold text-[#1e1b2e]">${item.brand_name}</td>
        <td class="p-3 text-[#645f78]">${item.generic_name}</td>
        <td class="p-3 font-bold text-amber-700 font-mono">${item.current_active_stock}</td>
        <td class="p-3 text-[#585172] font-mono">${item.reorder_level}</td>
        <td class="p-3 text-[#585172] font-mono">${item.target_stock_level}</td>
        <td class="p-3 font-extrabold text-violet-700 text-sm font-mono">+${item.units_to_order}</td>
        <td class="p-3 text-[#585172]">${item.preferred_supplier}</td>
        <td class="p-3 font-bold text-[#1e1b2e] font-mono">₹${Number(item.estimated_cost_inr).toLocaleString()}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading reorders:', err);
  }
}

async function loadFinancials() {
  try {
    const res = await fetch('/api/financials');
    let data = await res.json();
    const tbody = document.getElementById('financials-table');
    tbody.innerHTML = '';
    if (!Array.isArray(data)) data = [];

    data.forEach(item => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="p-3 font-bold font-mono text-[#1e1b2e]">${item.financial_month}</td>
        <td class="p-3 font-mono text-[#585172]">${item.total_invoices}</td>
        <td class="p-3 font-mono text-[#585172]">${item.units_sold}</td>
        <td class="p-3 font-bold font-mono text-emerald-700">₹${Number(item.gross_sales_inr).toLocaleString()}</td>
        <td class="p-3 font-mono text-[#585172]">₹${Number(item.cogs_inr).toLocaleString()}</td>
        <td class="p-3 font-bold font-mono text-[#1e1b2e]">₹${Number(item.gross_profit_inr).toLocaleString()}</td>
        <td class="p-3 font-semibold font-mono text-violet-700">${item.gross_margin_percentage}%</td>
        <td class="p-3 font-mono text-[#645f78]">${item.units_expired}</td>
        <td class="p-3 font-semibold font-mono text-red-700">₹${Number(item.expiry_write_off_inr).toLocaleString()}</td>
        <td class="p-3 font-extrabold font-mono text-emerald-700">₹${Number(item.net_operational_margin_inr).toLocaleString()}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading financials:', err);
  }
}

async function loadAuditTrail() {
  try {
    const res = await fetch('/api/audit-trail');
    let data = await res.json();
    const tbody = document.getElementById('audit-table');
    tbody.innerHTML = '';
    if (!Array.isArray(data)) data = [];

    data.forEach(item => {
      const isDeduction = item.quantity_change < 0;
      const tr = document.createElement('tr');
      const timeStr = item.transaction_time ? new Date(item.transaction_time).toLocaleTimeString() : '-';
      tr.innerHTML = `
        <td class="p-3 font-mono text-[#645f78]">#${item.transaction_id}</td>
        <td class="p-3 font-mono text-[#645f78]">${timeStr}</td>
        <td class="p-3"><span class="px-2.5 py-0.5 rounded text-[11px] font-mono font-semibold ${isDeduction ? 'bg-amber-50 text-amber-800 border border-amber-200' : 'bg-violet-50 text-violet-800 border border-violet-200'}">${item.transaction_type}</span></td>
        <td class="p-3 font-semibold text-[#1e1b2e]">${item.brand_name}</td>
        <td class="p-3 font-mono text-violet-700">${item.batch_number}</td>
        <td class="p-3 font-bold font-mono ${isDeduction ? 'text-red-700' : 'text-emerald-700'}">${item.quantity_change > 0 ? '+' : ''}${item.quantity_change}</td>
        <td class="p-3 font-bold font-mono text-[#1e1b2e]">${item.balance_after}</td>
        <td class="p-3 font-mono text-violet-700">${item.reference_code || '-'}</td>
        <td class="p-3 text-[#645f78]">${item.remarks || '-'}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading audit trail:', err);
  }
}

// ----------------------------------------------------------------------------
// INTERACTIVE ACTIONS & SIMULATORS
// ----------------------------------------------------------------------------

async function handleQuickDispense(e) {
  e.preventDefault();
  const medId = document.getElementById('quick-med-select').value;
  const qty = document.getElementById('quick-qty-input').value;

  if (!medId || !qty) return;

  const res = await fetch('/api/dispense-fefo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ medicine_id: parseInt(medId), quantity: parseInt(qty) })
  });
  const data = await res.json();

  if (data.success) {
    showAlert(data.output || 'FEFO Dispensing processed successfully!', true);
    await syncAllViews(medId);
  } else {
    showAlert(data.error || 'Dispense failed!', false);
  }
}

async function handleFullDispense(e) {
  e.preventDefault();
  const medId = document.getElementById('dispense-med-select').value;
  const custId = document.getElementById('dispense-cust-select').value;
  const qty = document.getElementById('dispense-qty-input').value;

  const res = await fetch('/api/dispense-fefo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ medicine_id: parseInt(medId), customer_id: custId || null, quantity: parseInt(qty) })
  });
  const data = await res.json();

  const resultBox = document.getElementById('dispense-result-box');
  const resultMsg = document.getElementById('dispense-result-msg');

  if (data.success) {
    if (resultBox && resultMsg) {
      resultBox.classList.remove('hidden');
      resultMsg.textContent = data.output || 'Dispense completed.';
    }
    showAlert('FEFO Procedure sp_dispense_medicine_fefo executed successfully!', true);
    await syncAllViews(medId);
  } else {
    showAlert(data.error || 'Dispense rejected by PostgreSQL constraint!', false);
  }
}

async function testExpiredTrigger() {
  showAlert('Simulating transaction: Attempting to dispense from expired batch B-CRO-EX1...', false);
  const res = await fetch('/api/dispense-fefo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ medicine_id: 1, quantity: 99999 })
  });
  const data = await res.json();
  showAlert(data.error || 'Database safety trigger blocked the expired transaction!', false);
}

async function triggerQuarantine() {
  if (!confirm('Execute automated batch quarantine for all expired stock? This will lock expired drugs and record audit disposal.')) return;
  const res = await fetch('/api/quarantine', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pharmacist_name: 'Gauransh Purohit (Chief Pharmacist)', method: 'High-Temp Incineration' })
  });
  const data = await res.json();
  if (data.success) {
    showAlert(data.output || 'Expired stock safely quarantined and written off!', true);
    await syncAllViews();
  } else {
    showAlert(data.error || 'Quarantine failed', false);
  }
}

async function triggerRefreshMV() {
  const res = await fetch('/api/refresh-analytics', { method: 'POST' });
  const data = await res.json();
  if (data.success) {
    showAlert(data.output || 'Materialized view mv_monthly_pharmacy_financials refreshed concurrently!', true);
    await loadFinancials();
  }
}

async function triggerResetSeed() {
  if (!confirm('Re-sync runtime state with fresh baseline pharmacy records?')) return;
  showAlert('Synchronizing inventory data...', true);
  const res = await fetch('/api/reset-seed', { method: 'POST' });
  const data = await res.json();
  if (data.success) {
    showAlert(data.message || 'Platform state successfully re-synchronized!', true);
    await syncAllViews();
  } else {
    showAlert(data.error || 'Re-seed failed', false);
  }
}

async function executeRecallSearch() {
  const input = document.getElementById('recall-batch-input');
  const batchNo = (input ? input.value : 'B-CRO-02').trim();
  if (!batchNo) return;
  const res = await fetch(`/api/recall-trace?batch_number=${encodeURIComponent(batchNo)}`);
  const data = await res.json();
  const tbody = document.getElementById('recall-results-table');
  tbody.innerHTML = '';

  if (!Array.isArray(data) || data.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="p-4 text-center text-[#847c9b]">No patient dispense transactions recorded for batch lot '${batchNo}'.</td></tr>`;
    return;
  }

  data.forEach(item => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="p-3 font-mono font-semibold text-violet-700">${item.batch_number}</td>
      <td class="p-3 font-semibold text-[#1e1b2e]">${item.brand_name} (${item.dosage_form})</td>
      <td class="p-3 font-mono text-violet-700 font-semibold">${item.invoice_number}</td>
      <td class="p-3 font-mono text-[#585172]">${new Date(item.sale_timestamp).toLocaleString()}</td>
      <td class="p-3 font-bold text-[#1e1b2e]">${item.patient_name}</td>
      <td class="p-3 font-mono text-[#645f78]">${item.patient_phone}</td>
      <td class="p-3 text-[#585172]">${item.doctor_name}</td>
      <td class="p-3 font-bold text-emerald-700 font-mono">${item.units_dispensed}</td>
    `;
    tbody.appendChild(tr);
  });
}

function formatUrgencyBadge(tier, short = false) {
  if (!tier) return '<span class="badge-safe"><span class="badge-dot"></span>Safe</span>';
  const upper = tier.toUpperCase();
  const label = short ? tier.split(':')[0].trim() : tier;
  if (upper.includes('CRITICAL') || upper.includes('EXPIRED') || upper.includes('QUARANTINED')) {
    return `<span class="badge-critical"><span class="badge-dot"></span>${label}</span>`;
  }
  if (upper.includes('URGENT') || upper.includes('<30')) {
    return `<span class="badge-urgent"><span class="badge-dot"></span>${label}</span>`;
  }
  if (upper.includes('WARNING') || upper.includes('31-60')) {
    return `<span class="badge-warning"><span class="badge-dot"></span>${label}</span>`;
  }
  if (upper.includes('DEPLETED')) {
    return `<span class="badge-depleted"><span class="badge-dot"></span>${label}</span>`;
  }
  return `<span class="badge-safe"><span class="badge-dot"></span>${label}</span>`;
}

// ----------------------------------------------------------------------------
// VIVA GUIDE MODAL CONTROLLER
// ----------------------------------------------------------------------------
function openVivaModal() {
  const modal = document.getElementById('viva-guide-modal');
  if (modal) modal.classList.remove('hidden');
}

function closeVivaModal() {
  const modal = document.getElementById('viva-guide-modal');
  if (modal) modal.classList.add('hidden');
}
