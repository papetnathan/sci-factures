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
    pdfCanvas.style.display  = 'block';
    previewDiv.style.maxHeight = 'none';
    previewDiv.style.overflow  = 'visible';

    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const pdf = await pdfjsLib.getDocument({ data: new Uint8Array(evt.target.result) }).promise;
        const page = await pdf.getPage(1);
        const viewport = page.getViewport({ scale: 1.2 });
        pdfCanvas.width  = viewport.width;
        pdfCanvas.height = viewport.height;
        await page.render({ canvasContext: pdfCanvas.getContext('2d'), viewport }).promise;

        const dataUrl = pdfCanvas.toDataURL('image/jpeg', 0.85);
        document.getElementById('photo-data').value = dataUrl;
        console.log('[PDF] photo-data prêt, taille ≈', Math.round(dataUrl.length / 1024), 'KB');
      } catch (err) {
        console.error('[PDF] Erreur rendu:', err);
      }
    };
    reader.readAsArrayBuffer(file);

  } else {
    if (pdfCanvas) {
      pdfCanvas.style.display = 'none';
      pdfCanvas.width = 0;
    }
    previewDiv.style.maxHeight = '';
    previewDiv.style.overflow  = '';
    previewImg.style.display = 'block';

    const reader = new FileReader();
    reader.onload = (evt) => {
      const img = new Image();
      img.onload = () => {
        const maxW = 1800;
        let w = img.width;
        let h = img.height;
        if (w > maxW) {
          h = Math.round(h * maxW / w);
          w = maxW;
        }
        const canvas = document.createElement('canvas');
        canvas.width  = w;
        canvas.height = h;
        canvas.getContext('2d').drawImage(img, 0, 0, w, h);
        const compressed = canvas.toDataURL('image/jpeg', 0.85);
        previewImg.src = compressed;
        document.getElementById('photo-data').value = compressed;
        console.log('[IMG] photo-data prêt, taille ≈', Math.round(compressed.length / 1024), 'KB');
      };
      img.src = evt.target.result;
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
  if (pdfCanvas) {
    pdfCanvas.style.display = 'none';
    pdfCanvas.width = 0;
  }
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
    if (!response.ok) throw new Error(result.detail || 'Erreur inconnue');
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
    alert.style.display = Math.abs(expected - ttc) > 1 ? 'flex' : 'none';
  } else {
    alert.style.display = 'none';
  }
}

function showExtractError(msg) {
  const el = document.getElementById('extract-error');
  const msgEl = document.getElementById('extract-error-msg');
  if (el && msgEl) { msgEl.textContent = msg; el.style.display = 'flex'; }
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
    const res = await fetch('/transactions/import', { method: 'POST', body: formData });
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

// ══════════════════════════════════════════════════════
// ─── NOUVELLES FONCTIONNALITÉS ────────────────────────
// ══════════════════════════════════════════════════════

// ─── Toast ────────────────────────────────────────────
(function () {
  const container = document.createElement('div');
  container.className = 'toast-container';
  document.body.appendChild(container);

  window.showToast = function (message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span class="toast-dot"></span>${message}`;
    container.appendChild(toast);
    requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add('toast-show')));
    setTimeout(() => {
      toast.classList.add('toast-hide');
      toast.addEventListener('transitionend', () => toast.remove(), { once: true });
    }, 3000);
  };
})();

// ─── Init DOMContentLoaded ────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

  // Toasts auto depuis attributs data- dans le DOM Jinja
  // Ex : <div data-toast-success="Facture créée" style="display:none"></div>
  const toastSuccess = document.querySelector('[data-toast-success]');
  if (toastSuccess) showToast(toastSuccess.dataset.toastSuccess, 'success');

  const toastError = document.querySelector('[data-toast-error]');
  if (toastError) showToast(toastError.dataset.toastError, 'error');

  const toastInfo = document.querySelector('[data-toast-info]');
  if (toastInfo) showToast(toastInfo.dataset.toastInfo, 'info');

  // ─── Compteurs animés KPIs ───────────────────────────
  function animateCounter(el, target, duration) {
    const start = performance.now();
    const fmt = (v) => v.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
    function step(now) {
      const p = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(ease * target);
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = fmt(target);
    }
    requestAnimationFrame(step);
  }

  document.querySelectorAll('.kpi-value').forEach(el => {
    const raw = el.textContent.trim().replace(/\s/g, '').replace(',', '.').replace('−', '-').replace('€', '');
    const target = parseFloat(raw.replace(/[^\d.\-]/g, ''));
    if (isNaN(target) || target === 0) return;
    const color = el.style.color;
    el.textContent = '0,00 €';
    if (color) el.style.color = color;
    setTimeout(() => animateCounter(el, Math.abs(target), 1100), 150);
  });

});

// ─── Raccourcis clavier ────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeLightbox();
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) return;
  if (e.key === 'n' || e.key === 'N') window.location.href = '/factures/nouvelle';
});