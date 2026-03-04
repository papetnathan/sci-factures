// ─── Sidebar mobile ───────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebar-overlay').classList.toggle('open');
}

document.querySelectorAll('.nav-item').forEach(link => {
  link.addEventListener('click', () => {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebar-overlay').classList.remove('open');
  });
});

// ─── Upload & preview ─────────────────────────────────
const fileInput = document.getElementById('file-input');
const uploadZone = document.getElementById('upload-zone');

if (fileInput) {
  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) handleFile(file);
  });
}

if (uploadZone) {
  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
  });
  uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
  });
  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });
}

function handleFile(file) {
  // Preview
  const reader = new FileReader();
  reader.onload = (e) => {
    document.getElementById('preview-img').src = e.target.result;
    document.getElementById('upload-preview').style.display = 'block';
    document.getElementById('upload-zone').style.display = 'none';
    document.getElementById('btn-analyze').style.display = 'flex';
    // Stocke le base64 pour l'envoi
    document.getElementById('photo-data').value = e.target.result;
  };
  reader.readAsDataURL(file);
}

function removeImage() {
  document.getElementById('preview-img').src = '';
  document.getElementById('upload-preview').style.display = 'none';
  document.getElementById('upload-zone').style.display = 'block';
  document.getElementById('btn-analyze').style.display = 'none';
  document.getElementById('photo-data').value = '';
  document.getElementById('file-input').value = '';
  document.getElementById('ia-badge').style.display = 'none';
  hideExtractError();
}

// ─── Extraction IA ────────────────────────────────────
async function analyzeImage() {
  const fileInput = document.getElementById('file-input');
  const file = fileInput.files[0];
  if (!file) return;

  // UI : état chargement
  document.getElementById('btn-analyze').style.display = 'none';
  document.getElementById('analyzing-state').style.display = 'block';
  hideExtractError();

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch('/api/extract', {
      method: 'POST',
      body: formData,
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || 'Erreur inconnue');
    }

    fillForm(result.data);
    document.getElementById('ia-badge').style.display = 'block';

  } catch (err) {
    showExtractError(err.message);
    document.getElementById('btn-analyze').style.display = 'flex';
  } finally {
    document.getElementById('analyzing-state').style.display = 'none';
  }
}

function fillForm(data) {
  if (data.vendor_name) setValue('vendor_name', data.vendor_name);
  if (data.detail)      setValue('detail',      data.detail);
  if (data.amount_ttc)  setValue('amount_ttc',  data.amount_ttc);
  if (data.amount_ht)   setValue('amount_ht',   data.amount_ht);
  if (data.tva_rate)    setValue('tva_rate',    data.tva_rate);
  if (data.invoice_date) setValue('invoice_date', data.invoice_date);
  checkTva();
}

function setValue(id, value) {
  const el = document.getElementById(id);
  if (el) el.value = value;
}

// ─── Vérification TVA ─────────────────────────────────
function checkTva() {
  const ht  = parseFloat(document.getElementById('amount_ht')?.value);
  const ttc = parseFloat(document.getElementById('amount_ttc')?.value);
  const tva = parseFloat(document.getElementById('tva_rate')?.value);
  const alert = document.getElementById('tva-alert');

  if (!alert) return;

  if (ht && ttc && tva) {
    const expected = ht * (1 + tva / 100);
    const diff = Math.abs(expected - ttc);
    if (diff > 1) {
      alert.style.display = 'flex';
    } else {
      alert.style.display = 'none';
    }
  } else {
    alert.style.display = 'none';
  }
}

function showExtractError(msg) {
  const el = document.getElementById('extract-error');
  const msgEl = document.getElementById('extract-error-msg');
  if (el && msgEl) {
    msgEl.textContent = msg;
    el.style.display = 'flex';
  }
}

function hideExtractError() {
  const el = document.getElementById('extract-error');
  if (el) el.style.display = 'none';
}