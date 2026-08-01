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

const API_BASE = "https://api.hunterstar.online/api";

/* ===== STATE ===== */
let library = [];
let history = [];
let uploadQueue = [];
let activeFile = null; // file currently open in the details panel

/* ===== DOM ELEMENTS ===== */
const fileListEl = document.getElementById('main-file-list');
const emptyStateEl = document.getElementById('empty-state');
const activityListEl = document.getElementById('activity-list');
const widgetFilesCount = document.getElementById('widget-files-count');

const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const browseBtn = document.getElementById('browse-btn');
const dzDefault = document.getElementById('dz-default');
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
  
  uploadQueue = files.map(file => ({ file, progress: 0, status: 'queued' }));
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

function updateQueueItem(idx, loaded, total, percent) {
  const el = document.getElementById(`q-${idx}`);
  if (!el) return;
  el.querySelector('.q-pct').textContent = `${Math.floor(percent)}%`;
  el.querySelector('.q-bar-fill').style.width = `${percent}%`;
  el.querySelector('.q-meta span:first-child').textContent = `${formatBytes(loaded)} / ${formatBytes(total)}`;
}

async function uploadFile(item, idx) {
  const formData = new FormData();
  formData.append('file', item.file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/upload`, true);
    xhr.setRequestHeader("x-tg-data", initData);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const percent = (e.loaded / e.total) * 100;
        updateQueueItem(idx, e.loaded, e.total, percent);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(xhr.responseText));
      }
    };
    xhr.onerror = () => reject(new Error("Network Error"));
    xhr.send(formData);
  });
}

async function startUploads() {
  if (isMiniApp && tg) {
    tg.MainButton.setText('UPLOADING...');
    tg.MainButton.showProgress();
    tg.MainButton.show();
  }
  
  let lastResult = null;
  let anyFailed = false;
  
  for (let i = 0; i < uploadQueue.length; i++) {
    const item = uploadQueue[i];
    try {
      const res = await uploadFile(item, i);
      const el = document.getElementById(`q-${i}`);
      if (el) el.querySelector('.q-meta span:last-child').textContent = 'Completed';
      
      const sizeStr = formatBytes(item.file.size);
      const newFile = { name: item.file.name, size: sizeStr, id: res.id, category: 'private', uploaded_at: new Date() };
      library.unshift(newFile);
      addLog('⬆', `Uploaded ${item.file.name}`);
      lastResult = newFile;
      
      if (isMiniApp && tg) tg.HapticFeedback?.impactOccurred('light');
    } catch (e) {
      console.error(e);
      anyFailed = true;
      const el = document.getElementById(`q-${i}`);
      if (el) el.querySelector('.q-meta span:last-child').textContent = 'Error';
    }
  }
  
  renderLibrary();
  fetchStats();
  
  if (isMiniApp && tg) {
    tg.MainButton.hideProgress();
    tg.MainButton.hide();
    tg.HapticFeedback?.notification(lastResult ? 'success' : 'error');
  }

  if (anyFailed) {
    toast(lastResult ? 'Some files failed to upload.' : 'Upload failed. Please try again.', 'error');
  }
  
  // Show Success Screen if at least one file succeeded
  if (lastResult) {
    dzQueue.hidden = true;
    dzSuccess.hidden = false;
    document.getElementById('success-filename').textContent = lastResult.name;
    document.getElementById('success-id').textContent = `🆔 ${lastResult.id}`;
    
    // Bind buttons — Copy ID now actually copies the raw ID instead of
    // duplicating the Copy Link behavior, and Make Public is now wired up
    // (it previously had no handler at all).
    document.getElementById('btn-copy-id').onclick = () => copyID(lastResult.id);
    document.getElementById('btn-copy-link').onclick = () => copyLink(lastResult.id);
    document.getElementById('btn-make-public').onclick = () => makePublic(lastResult);
  } else {
    setTimeout(() => {
      dzQueue.hidden = true;
      dzDefault.hidden = false;
    }, 2000);
  }
}

/* ===== COMMAND PALETTE (CMD+K) ===== */
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    toggleCmdPalette();
  }
  if (e.key === 'Escape' && !cmdPalette.hidden) {
    toggleCmdPalette();
  }
});

function toggleCmdPalette() {
  if (cmdPalette.hidden) {
    cmdPalette.hidden = false;
    cmdInput.focus();
    cmdInput.value = '';
  } else {
    cmdPalette.hidden = true;
  }
}

cmdPalette.addEventListener('click', e => {
  if (e.target === cmdPalette) toggleCmdPalette(); // Click outside to close
});

// The command items (Upload File / Create Folder / Settings) rendered but
// did nothing when clicked — wiring them to real actions.
document.querySelectorAll('.cmd-item').forEach(item => {
  item.addEventListener('click', () => {
    const action = item.dataset.action;
    toggleCmdPalette();
    if (action === 'upload') fileInput.click();
    else if (action === 'folder') toast('Folders are coming soon.');
    else if (action === 'settings') toast('Settings are coming soon.');
  });
});

/* ===== INIT ===== */
renderLibrary();
renderActivity();
fetchLibrary();
fetchStats();