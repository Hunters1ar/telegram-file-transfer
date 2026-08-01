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
    
    row.innerHTML = `
      <div class="f-info">
        <span class="f-icon">${icon}</span>
        <span class="f-name">${file.name}</span>
      </div>
      <div class="f-meta">
        <span>${file.size}</span>
        <span>${file.category === 'public' ? '🌍 Public' : '🔒 Private'}</span>
      </div>
      <div class="f-actions" onclick="event.stopPropagation()">
        <button class="f-btn" onclick="window.open('${API_BASE}/download/${file.id}', '_blank')">⬇</button>
        <button class="f-btn" onclick="copyLink('${file.id}')">🔗</button>
        <button class="f-btn">⋮</button>
      </div>
    `;
    
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
        <span>${log.msg}</span>
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

function copyLink(id) {
  navigator.clipboard?.writeText(`https://t.me/hunterstar_bot?start=${id}`);
  if (isMiniApp && tg) tg.HapticFeedback?.notification('success');
}

/* ===== DETAILS PANEL ===== */
function openDetails(file) {
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
        <span>${item.file.name}</span>
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
      const el = document.getElementById(`q-${i}`);
      if (el) el.querySelector('.q-meta span:last-child').textContent = 'Error';
    }
  }
  
  renderLibrary();
  fetchStats();
  
  if (isMiniApp && tg) {
    tg.MainButton.hideProgress();
    tg.MainButton.hide();
    tg.HapticFeedback?.notification('success');
  }
  
  // Show Success Screen if at least one file succeeded
  if (lastResult) {
    dzQueue.hidden = true;
    dzSuccess.hidden = false;
    document.getElementById('success-filename').textContent = lastResult.name;
    document.getElementById('success-id').textContent = `🆔 ${lastResult.id}`;
    
    // Bind buttons
    document.getElementById('btn-copy-id').onclick = () => copyLink(lastResult.id); // Or copy ID
    document.getElementById('btn-copy-link').onclick = () => copyLink(lastResult.id);
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

/* ===== INIT ===== */
renderLibrary();
renderActivity();
fetchLibrary();
fetchStats();