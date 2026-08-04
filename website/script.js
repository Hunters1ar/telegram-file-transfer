/* ============================================
   HUNTERSTAR UX 2.0 SCRIPT
   ============================================ */

const tg = window.Telegram?.WebApp;
let isMiniApp = false;
let initData = "";

if (tg) {
  tg.ready();
  tg.expand();
  isMiniApp = tg.platform !== 'unknown' && tg.platform !== undefined;
  if (isMiniApp) {
    document.body.classList.add('tg-miniapp');
    initData = tg.initData;
  }
}

// FOR TESTING OUTSIDE TELEGRAM
if (!isMiniApp) {
  // Mock initData for local testing (Uses dummy ID 123456)
  initData = "user=%7B%22id%22%3A123456%7D&hash=mock";
}

const API_BASE = "https://api.hunterstar.online/api/v1";

/* ===== STATE ===== */
let library = [];
let history = [];
let uploadQueue = [];
let activeFile = null; // file currently open in the details panel
let globalLimitBytes = 20 * 1024 * 1024; // Default 20MB

/* ===== DOM ELEMENTS ===== */
const fileListEl = document.getElementById('main-file-list');
const emptyStateEl = document.getElementById('empty-state');
const activityListEl = document.getElementById('activity-list');
const widgetFilesCount = document.getElementById('widget-files-count');

const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const browseBtn = document.getElementById('browse-btn');
const dzDefault = document.getElementById('dz-default');
const mobileUploadBtn = document.querySelector('.upload-btn');
if (mobileUploadBtn) {
  mobileUploadBtn.addEventListener('click', (e) => {
    e.preventDefault();
    fileInput.click();
  });
}
const dzQueue = document.getElementById('dz-queue');
const dzSuccess = document.getElementById('dz-success');

const cmdPalette = document.getElementById('cmd-palette');
const cmdInput = document.getElementById('cmd-input');

const detailsPanel = document.getElementById('details-panel');
const dpClose = document.getElementById('dp-close');

/* ===== HELPERS ===== */
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + units[i];
}

function getFileIcon(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  if (['pdf'].includes(ext)) return '📄';
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return '🖼';
  if (['mp4', 'mov', 'avi', 'mkv'].includes(ext)) return '🎬';
  if (['mp3', 'wav', 'ogg'].includes(ext)) return '🎵';
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return '📦';
  if (['js', 'py', 'html', 'css', 'cpp', 'c', 'java'].includes(ext)) return '💻';
  return '📄';
}

function timeAgo(dateString) {
  const date = new Date(dateString);
  const seconds = Math.floor((new Date() - date) / 1000);
  let interval = seconds / 31536000;
  if (interval > 1) return Math.floor(interval) + " years ago";
  interval = seconds / 2592000;
  if (interval > 1) return Math.floor(interval) + " months ago";
  interval = seconds / 86400;
  if (interval > 1) return Math.floor(interval) + " days ago";
  interval = seconds / 3600;
  if (interval > 1) return Math.floor(interval) + " hours ago";
  interval = seconds / 60;
  if (interval > 1) return Math.floor(interval) + " mins ago";
  return "Just now";
}

// Prevents filenames from breaking markup (e.g. a file called "<img onerror=...>")
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}

/* ===== TOAST NOTIFICATIONS =====
   Small non-blocking feedback so failures (like a dead download link)
   don't just silently open a blank error page with no explanation. */
let toastContainer = document.getElementById('toast-container');
if (!toastContainer) {
  toastContainer = document.createElement('div');
  toastContainer.id = 'toast-container';
  toastContainer.className = 'toast-container';
  document.body.appendChild(toastContainer);
}

function toast(message, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = message;
  toastContainer.appendChild(el);
  requestAnimationFrame(() => el.classList.add('show'));
  setTimeout(() => {
    el.classList.remove('show');
    setTimeout(() => el.remove(), 300);
  }, 3200);
}

/* ===== RENDERERS ===== */
function renderLibrary() {
  widgetFilesCount.textContent = library.length;
  
  if (library.length === 0) {
    emptyStateEl.style.display = 'block';
    const rows = fileListEl.querySelectorAll('.file-row');
    rows.forEach(r => r.remove());
    return;
  }
  
  emptyStateEl.style.display = 'none';
  fileListEl.innerHTML = '';
  
  library.forEach(file => {
    const row = document.createElement('div');
    row.className = 'file-row';
    const icon = getFileIcon(file.name);
    const safeName = escapeHtml(file.name);
    
    row.innerHTML = `
      <div class="f-info">
        <span class="f-icon">${icon}</span>
        <span class="f-name">${safeName}</span>
      </div>
      <div class="f-meta">
        <span>${file.size}</span>
        <span>${file.category === 'public' ? '🌍 Public' : '🔒 Private'}</span>
      </div>
      <div class="f-actions" onclick="event.stopPropagation()">
        <button class="f-btn" data-action="download">⬇</button>
        <button class="f-btn" data-action="copy-link">🔗</button>
        <button class="f-btn" data-action="more">⋮</button>
      </div>
    `;

    row.querySelector('[data-action="download"]').addEventListener('click', () => downloadFile(file));
    row.querySelector('[data-action="copy-link"]').addEventListener('click', () => copyLink(file.id));
    row.querySelector('[data-action="more"]').addEventListener('click', (e) => {
      e.stopPropagation();
      openDetails(file);
    });

    row.addEventListener('click', () => openDetails(file));
    fileListEl.appendChild(row);
  });
}

function renderActivity() {
  activityListEl.innerHTML = '';
  history.forEach(log => {
    const el = document.createElement('div');
    el.className = 'act-item';
    el.innerHTML = `
      <span class="act-icon">${log.icon}</span>
      <div>
        <span>${escapeHtml(log.msg)}</span>
        <span class="act-time">${log.time}</span>
      </div>
    `;
    activityListEl.appendChild(el);
  });
}

function addLog(icon, msg) {
  history.unshift({ icon, msg, time: 'Just now' });
  if (history.length > 5) history.pop();
  renderActivity();
}

/* ===== FILE ACTIONS ===== */

// Copies the Telegram deep-link for a file
function copyLink(id) {
  navigator.clipboard?.writeText(`https://t.me/hunterstar_bot?start=${encodeURIComponent(id)}`);
  toast('Link copied to clipboard');
  if (isMiniApp && tg) tg.HapticFeedback?.notification('success');
}

// Copies the raw file ID (previously this was wired to copyLink by mistake,
// so "Copy ID" and "Copy Link" did the exact same thing)
function copyID(id) {
  navigator.clipboard?.writeText(id);
  toast('ID copied to clipboard');
  if (isMiniApp && tg) tg.HapticFeedback?.notification('success');
}

// Opens the download URL, but checks it first instead of blindly opening a
// new tab that may land on a raw "Internal Server Error" page with no context.
async function downloadFile(file) {
  const url = `${API_BASE}/download/${encodeURIComponent(file.id)}`;
  const win = window.open('', '_blank');
  try {
    const res = await fetch(url, { method: 'HEAD', headers: { "x-tg-data": initData } });
    if (!res.ok) {
      if (win) win.close();
      toast(`Download failed (server returned ${res.status}). Try again shortly.`, 'error');
      addLog('❌', `Download failed: ${file.name}`);
      return;
    }
    if (win) win.location.href = url;
    else window.open(url, '_blank');
  } catch (e) {
    if (win) win.close();
    console.error(e);
    toast('Download failed — check your connection.', 'error');
    addLog('❌', `Download failed: ${file.name}`);
  }
}

async function deleteFile(file) {
  if (!confirm(`Delete "${file.name}"? This cannot be undone.`)) return;
  try {
    const res = await fetch(`${API_BASE}/files/${encodeURIComponent(file.id)}`, {
      method: 'DELETE',
      headers: { "x-tg-data": initData }
    });
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    library = library.filter(f => f.id !== file.id);
    renderLibrary();
    fetchStats();
    addLog('🗑', `Deleted ${file.name}`);
    toast('File deleted');
    detailsPanel.classList.remove('open');
  } catch (e) {
    console.error(e);
    toast('Delete failed. Please try again.', 'error');
  }
}

async function renameFile(file) {
  const newName = prompt('Rename file', file.name);
  if (!newName || newName === file.name) return;
  try {
    const res = await fetch(`${API_BASE}/files/${encodeURIComponent(file.id)}`, {
      method: 'PATCH',
      headers: { "x-tg-data": initData, "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName })
    });
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    file.name = newName;
    renderLibrary();
    document.getElementById('dp-filename').textContent = newName;
    toast('File renamed');
  } catch (e) {
    console.error(e);
    toast('Rename failed. Please try again.', 'error');
  }
}

async function makePublic(file) {
  try {
    const res = await fetch(`${API_BASE}/files/${encodeURIComponent(file.id)}`, {
      method: 'PATCH',
      headers: { "x-tg-data": initData, "Content-Type": "application/json" },
      body: JSON.stringify({ category: 'public' })
    });
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    file.category = 'public';
    renderLibrary();
    toast('File is now public');
  } catch (e) {
    console.error(e);
    toast('Could not change visibility. Please try again.', 'error');
  }
}

/* ===== DETAILS PANEL ===== */
function openDetails(file) {
  activeFile = file;
  document.getElementById('dp-filename').textContent = file.name;
  document.getElementById('dp-size').textContent = file.size;
  document.getElementById('dp-hash').textContent = file.id;
  document.getElementById('dp-downloads').textContent = '0';
  document.getElementById('dp-visibility').textContent = file.category === 'public' ? 'Public' : 'Private';
  document.getElementById('dp-created').textContent = timeAgo(file.uploaded_at || new Date());
  
  detailsPanel.classList.add('open');
}

dpClose.addEventListener('click', () => {
  detailsPanel.classList.remove('open');
});

// The details-panel action buttons (Download / Share / Rename / Delete) had
// no click handlers at all before — wiring them up here.
const dpActionButtons = document.querySelectorAll('.dp-actions .dp-btn');
if (dpActionButtons[0]) dpActionButtons[0].addEventListener('click', () => activeFile && downloadFile(activeFile));
if (dpActionButtons[1]) dpActionButtons[1].addEventListener('click', () => activeFile && copyLink(activeFile.id));
if (dpActionButtons[2]) dpActionButtons[2].addEventListener('click', () => activeFile && renameFile(activeFile));
if (dpActionButtons[3]) dpActionButtons[3].addEventListener('click', () => activeFile && deleteFile(activeFile));

/* ===== API FETCH ===== */
async function fetchStats() {
  if (!initData) return;
  try {
    const res = await fetch(`${API_BASE}/stats`, {
      headers: { "x-tg-data": initData }
    });
    if (!res.ok) return;
    const stats = await res.json();
    
    document.getElementById('widget-files-count').textContent = stats.total_files;
    document.getElementById('widget-storage').textContent = formatBytes(stats.total_size);
    document.getElementById('widget-downloads').textContent = stats.total_downloads;
    document.getElementById('widget-shared').textContent = stats.total_shared;
    
    if (stats.limit_mb) {
        globalLimitBytes = stats.limit_mb * 1024 * 1024;
    }
    
    // Sidebar storage (100GB limit)
    const limit = 100 * 1024 * 1024 * 1024; // 100 GB
    const percent = Math.min((stats.total_size / limit) * 100, 100);
    const textEl = document.getElementById('sb-storage-text');
    const fillEl = document.getElementById('sb-storage-fill');
    
    if (textEl) textEl.textContent = `${formatBytes(stats.total_size)} / 100 GB`;
    if (fillEl) fillEl.style.width = `${percent}%`;
    
  } catch (e) {
    console.error("Failed to fetch stats", e);
  }
}

async function fetchLibrary() {
  if (!initData) return;
  try {
    const res = await fetch(`${API_BASE}/files`, {
      headers: { "x-tg-data": initData }
    });
    if (!res.ok) throw new Error("Failed to fetch files");
    const files = await res.json();
    library = files.map(f => ({
      name: f.name,
      size: formatBytes(f.size),
      id: f.id,
      category: f.category,
      uploaded_at: f.uploaded_at
    }));
    renderLibrary();
    addLog('🔄', 'Library synced');
  } catch (e) {
    console.error(e);
    addLog('❌', 'Sync failed');
    toast('Could not sync your library.', 'error');
  }
}

/* ===== DROPZONE & UPLOAD ===== */
browseBtn.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', e => {
  handleFiles(Array.from(e.target.files));
  e.target.value = '';
});

['dragenter', 'dragover'].forEach(evt => {
  dropzone.addEventListener(evt, e => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach(evt => {
  dropzone.addEventListener(evt, e => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
  });
});

dropzone.addEventListener('drop', e => {
  if (e.dataTransfer.files.length > 0) {
    handleFiles(Array.from(e.dataTransfer.files));
  }
});

function handleFiles(files) {
  if (!initData) {
    alert("Please open within Telegram to upload.");
    return;
  }
  
  // No size limit on the frontend for direct-to-R2 uploads
  const validFiles = files;

  if (validFiles.length === 0) return;
  
  uploadQueue = validFiles.map(file => ({ file, progress: 0, status: 'queued' }));
  dzDefault.hidden = true;
  dzSuccess.hidden = true;
  dzQueue.hidden = false;
  
  renderQueue();
  startUploads();
}

function renderQueue() {
  dzQueue.innerHTML = '';
  uploadQueue.forEach((item, idx) => {
    const el = document.createElement('div');
    el.className = 'queue-item';
    el.id = `q-${idx}`;
    el.innerHTML = `
      <div class="q-header">
        <span>${escapeHtml(item.file.name)}</span>
        <span class="q-pct">0%</span>
      </div>
      <div class="q-bar-track"><div class="q-bar-fill"></div></div>
      <div class="q-meta">
        <span>0 B / ${formatBytes(item.file.size)}</span>
        <span>Uploading...</span>
      </div>
    `;
    dzQueue.appendChild(el);
  });
}

function updateQueueItem(idx, loaded, total, percent, statusText) {
  const el = document.getElementById(`q-${idx}`);
  if (!el) return;
  el.querySelector('.q-pct').textContent = `${Math.floor(percent)}%`;
  el.querySelector('.q-bar-fill').style.width = `${percent}%`;
  el.querySelector('.q-meta span:first-child').textContent = `${formatBytes(loaded)} / ${formatBytes(total)}`;
  if (statusText) el.querySelector('.q-meta span:last-child').textContent = statusText;
}

async function computeSHA256(file) {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

async function uploadFile(item, idx) {
  // Step 0: Hash for Smart Upload Deduplication
  let sha256 = null;
  if (item.file.size < 100 * 1024 * 1024) { // only hash files < 100MB on frontend to prevent hanging
    updateQueueItem(idx, 0, item.file.size, 0, "Hashing...");
    sha256 = await computeSHA256(item.file);
  }

  // Step 1: Request Presigned URL
  const reqRes = await fetch(`${API_BASE}/upload/request`, {
    method: 'POST',
    headers: { "x-tg-data": initData, "Content-Type": "application/json" },
    body: JSON.stringify({
      name: item.file.name,
      size: item.file.size,
      mime_type: item.file.type || "application/octet-stream",
      sha256: sha256
    })
  });
  if (!reqRes.ok) throw new Error("Failed to request upload URL");
  const { url, r2_key, instant_success, final_meta } = await reqRes.json();
  
  if (instant_success) {
      toast('⚡ Instant Upload: File already exists in your cloud!');
      return final_meta;
  }

  // Step 2: Upload directly to R2 using XMLHttpRequest (for progress)
  await new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', url, true);
    
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const percent = (e.loaded / e.total) * 100;
        updateQueueItem(idx, e.loaded, e.total, percent, "Uploading...");
      }
    };
    
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error("R2 Upload failed"));
    };
    xhr.onerror = () => reject(new Error("Network Error"));
    xhr.send(item.file);
  });

  // Step 3: Confirm Upload
  const confRes = await fetch(`${API_BASE}/upload/confirm`, {
    method: 'POST',
    headers: { "x-tg-data": initData, "Content-Type": "application/json" },
    body: JSON.stringify({
      name: item.file.name,
      size: item.file.size,
      mime_type: item.file.type || "application/octet-stream",
      r2_key: r2_key
    })
  });
  if (!confRes.ok) throw new Error("Failed to confirm upload");
  return await confRes.json();
}

/* ===== ROUTING ===== */
function initRouter() {
  const urlParams = new URLSearchParams(window.location.search);
  const shareId = urlParams.get('f');
  
  // Also check if they used path-based routing (/f/XYZ)
  const pathParts = window.location.pathname.split('/');
  let pathShareId = null;
  if (pathParts[1] === 'f' && pathParts[2]) {
      pathShareId = pathParts[2];
  }
  
  const targetId = shareId || pathShareId;
  
  if (targetId) {
      // Hide dashboard, show preview
      document.getElementById('main-dashboard-view').hidden = true;
      document.querySelector('.sidebar').hidden = true;
      document.querySelector('.topbar').hidden = true;
      document.getElementById('file-preview-view').hidden = false;
      loadPreview(targetId);
  } else {
      renderLibrary();
      renderActivity();
      fetchLibrary();
      fetchStats();
  }
}

async function loadPreview(shareId) {
    try {
        const res = await fetch(`${API_BASE}/files/public/${shareId}`);
        if (!res.ok) throw new Error();
        
        const file = await res.json();
        
        document.getElementById('pv-filename').textContent = file.name;
        document.getElementById('pv-size').textContent = formatBytes(file.size);
        document.getElementById('pv-owner').textContent = 'Hunter'; // Mock owner
        document.getElementById('pv-date').textContent = new Date(file.uploaded_at).toLocaleDateString();
        document.getElementById('pv-downloads').textContent = '0'; // Could fetch real stats
        document.getElementById('pv-visibility').textContent = file.category === 'public' ? 'Public' : 'Private';
        document.getElementById('pv-hash').textContent = file.id; // Mock SHA until real SHA is saved
        document.getElementById('pv-icon').textContent = getFileIcon(file.name);
        
        document.getElementById('pv-btn-download').onclick = () => {
            window.location.href = `${API_BASE}/download/${file.id}`;
        };
    } catch (e) {
        toast('File not found or private', 'error');
        document.getElementById('pv-filename').textContent = "File not found";
    }
}

initRouter();