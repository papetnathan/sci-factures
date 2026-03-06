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
  const previewDiv = document.getElementById('upload-preview');
  const previewImg = document.getElementById('preview-img');
  const pdfCanvas  = document.getElementById('pdf-canvas');

  if (file.type === 'application/pdf') {
    previewImg.style.display = 'none';
    pdfCanvas.style.display = 'block';
    previewDiv.style.maxHeight = 'none';
    previewDiv.style.overflow  = 'visible';
    document.getElementById('photo-data').value = '';

    const reader = new FileReader();
    reader.onload = async (e) => {
      const pdf = await pdfjsLib.getDocument({ data: new Uint8Array(e.target.result) }).promise;
      const page = await pdf.getPage(1);
      const viewport = page.getViewport({ scale: 1.5 });
      pdfCanvas.width  = viewport.width;
      pdfCanvas.height = viewport.height;
      await page.render({ canvasContext: pdfCanvas.getContext('2d'), viewport }).promise;
    };
    reader.readAsArrayBuffer(file);

  } else {
    pdfCanvas.style.display = 'none';
    pdfCanvas.width = 0;
    previewDiv.style.maxHeight = '';
    previewDiv.style.overflow  = '';
    previewImg.style.display = 'block';
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      document.getElementById('photo-data').value = e.target.result;
    };
    reader.readAsDataURL(file);
  }

  previewDiv.style.display = 'block';
  document.getElementById('upload-zone').style.display = 'none';
  document.getElementById('btn-analyze').style.display = 'flex';
}

function removeImage() {
  const previewDiv = document.getElementById('upload-preview');
  const pdfCanvas  = document.getElementById('pdf-canvas');
  pdfCanvas.style.display = 'none';
  pdfCanvas.width = 0;
  previewDiv.style.maxHeight = '';
  previewDiv.style.overflow  = '';
  document.getElementById('preview-img').src = '';
  document.getElementById('preview-img').style.display = 'block';
  previewDiv.style.display = 'none';
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
  if (data.vendor_name)  setValue('vendor_name',  data.vendor_name);
  if (data.detail)       setValue('detail',       data.detail);
  if (data.amount_ttc)   setValue('amount_ttc',   data.amount_ttc);
  if (data.amount_ht)    setValue('amount_ht',    data.amount_ht);
  if (data.tva_rate)     setValue('tva_rate',     data.tva_rate);
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
    alert.style.display = diff > 1 ? 'flex' : 'none';
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

// ─── Lightbox ─────────────────────────────────────────
function openLightbox(src) {
  document.getElementById('lightbox-img').src = src;
  document.getElementById('lightbox').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  document.getElementById('lightbox').classList.remove('open');
  document.body.style.overflow = '';
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeLightbox();
});

// ─── Import PDF Transactions ───────────────────────────
let selectedPdfFile = null;

function closeImportModal() {
  document.getElementById('import-modal').style.display = 'none';
  document.getElementById('import-result').style.display = 'none';
  document.getElementById('import-filename').textContent = 'Cliquez pour sélectionner un PDF';
  document.getElementById('import-btn').disabled = true;
  selectedPdfFile = null;
}

function handlePdfSelect(input) {
  const file = input.files[0];
  if (!file) return;
  selectedPdfFile = file;
  document.getElementById('import-filename').textContent = file.name;
  document.getElementById('import-btn').disabled = false;
  document.getElementById('import-result').style.display = 'none';
}

async function importPdf() {
  if (!selectedPdfFile) return;

  const btn = document.getElementById('import-btn');
  btn.disabled = true;
  btn.textContent = 'Import en cours...';

  const formData = new FormData();
  formData.append('file', selectedPdfFile);

  try {
    const res = await fetch('/transactions/import', {
      method: 'POST',
      body: formData,
    });

    const data = await res.json();
    const resultDiv = document.getElementById('import-result');
    resultDiv.style.display = 'block';

    if (res.ok) {
      resultDiv.style.background = 'var(--green-light)';
      resultDiv.style.border = '1px solid #6EE7B7';
      resultDiv.style.color = '#065F46';
      const dateMin = data.date_min ? data.date_min.split('-').reverse().join('/') : '?';
      const dateMax = data.date_max ? data.date_max.split('-').reverse().join('/') : '?';
      resultDiv.textContent = `✓ ${data.inserted} transaction(s) importée(s) — période ${dateMin} → ${dateMax}`;
      setTimeout(() => window.location.reload(), 1500);
    } else {
      resultDiv.style.background = 'var(--red-light)';
      resultDiv.style.border = '1px solid #FCA5A5';
      resultDiv.style.color = '#991B1B';
      resultDiv.textContent = data.detail;
      btn.disabled = false;
      btn.textContent = 'Importer';
    }
  } catch (err) {
    console.error(err);
    btn.disabled = false;
    btn.textContent = 'Importer';
  }
}

// ─── Type achat/vente ──────────────────────────────────
function setType(type) {
  document.getElementById('type-input').value = type;
  if (type === 'achat') {
    document.getElementById('btn-achat').className = 'btn btn-primary';
    document.getElementById('btn-vente').className = 'btn btn-secondary';
    const cat = document.getElementById('category');
    if (cat && cat.value === 'loyer') cat.value = '';
  } else {
    document.getElementById('btn-achat').className = 'btn btn-secondary';
    document.getElementById('btn-vente').className = 'btn btn-primary';
    const cat = document.getElementById('category');
    if (cat) cat.value = 'loyer';
  }
}