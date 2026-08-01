/* ============================================
   HUNTERSTAR — MINIMAL + DASHBOARD SCRIPT
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

// FOR TESTING OUTSIDE TELEGRAM (Replace with your actual Telegram ID during local testing if needed)
if (!isMiniApp) {
  // Mock initData for testing
  // initData = "user=%7B%22id%22%3A123456%7D&hash=mock";
}

const API_BASE = "https://api.hunterstar.online/api";

/* ===== 1. CLOCK ===== */
function updateClock() {
  const now = new Date();
  const h = String(now.getUTCHours()).padStart(2, '0');
  const m = String(now.getUTCMinutes()).padStart(2, '0');
  const s = String(now.getUTCSeconds()).padStart(2, '0');
  const el = document.getElementById('status-time');
  if (el) el.textContent = `${h}:${m}:${s} UTC`;
}
updateClock();
setInterval(updateClock, 1000);

/* ===== 2. STATE & MOCK DATA ===== */
let library = [];
let history = [];

/* ===== 3. RENDER FUNCTIONS ===== */
function renderLibrary() {
  const list = document.getElementById('library-list');
  list.innerHTML = '';
  document.getElementById('lib-count').textContent = `${library.length} FILES`;
  
  library.forEach(file => {
    const el = document.createElement('div');
    el.className = 'lib-item';
    el.innerHTML = `
      <div class="lib-info">
        <span class="lib-name">${file.name}</span>
        <span class="lib-meta">${file.size}</span>
      </div>
      <button class="lib-id" data-id="${file.id}">${file.id}</button>
    `;
    list.appendChild(el);
  });
  
  // Copy ID functionality
  list.querySelectorAll('.lib-id').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.id;
      navigator.clipboard?.writeText(id);
      btn.classList.add('copied');
      btn.textContent = 'COPIED';
      setTimeout(() => {
        btn.classList.remove('copied');
        btn.textContent = id;
      }, 1500);
    });
  });
}

function renderHistory() {
  const list = document.getElementById('logs-list');
  list.innerHTML = '';
  
  history.forEach(log => {
    const el = document.createElement('div');
    el.className = 'log-item';
    el.innerHTML = `
      <span class="log-time">${log.time}</span>
      <span class="log-type ${log.type}">${log.type.toUpperCase()}</span>
      <span class="log-msg">${log.msg}</span>
    `;
    list.appendChild(el);
  });
}

function addLog(type, msg) {
  const now = new Date();
  const time = `${String(now.getUTCHours()).padStart(2, '0')}:${String(now.getUTCMinutes()).padStart(2, '0')}:${String(now.getUTCSeconds()).padStart(2, '0')}`;
  history.unshift({ time, type, msg });
  if (history.length > 20) history.pop(); // Keep logs concise
  renderHistory();
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
      id: f.id
    }));
    renderLibrary();
    addLog('system', 'Synced library from cloud');
  } catch (e) {
    console.error(e);
    addLog('error', 'Failed to sync library');
  }
}

/* ===== 4. DROPZONE LOGIC ===== */
const dropzone = document.getElementById('dropzone');
const folderInput = document.getElementById('folder-input');
const browseBtn = document.getElementById('browse-btn');
const fileList = document.getElementById('file-list');
const dzStatus = document.getElementById('dz-status');
const statusText = document.getElementById('status-text');
const statusPct = document.getElementById('status-pct');
const statusBar = document.getElementById('status-bar');

let queuedFiles = [];

browseBtn.addEventListener('click', () => folderInput.click());

folderInput.addEventListener('change', e => {
  handleFiles(Array.from(e.target.files).map(f => ({ file: f, path: f.webkitRelativePath || f.name })));
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
    if (evt === 'dragleave' && e.target !== dropzone) return;
    dropzone.classList.remove('dragover');
  });
});

dropzone.addEventListener('drop', async e => {
  const items = e.dataTransfer.items;
  if (items && items.length > 0 && items[0].webkitGetAsEntry) {
    const entries = [];
    for (let i = 0; i < items.length; i++) {
      const entry = items[i].webkitGetAsEntry();
      if (entry) entries.push(entry);
    }
    if (entries.length > 0) {
      const files = [];
      for (const entry of entries) {
        await traverseEntry(entry, '', files);
      }
      handleFiles(files);
      return;
    }
  }
  if (e.dataTransfer.files.length > 0) {
    handleFiles(Array.from(e.dataTransfer.files).map(f => ({ file: f, path: f.name })));
  }
});

function traverseEntry(entry, path, results) {
  return new Promise(resolve => {
    if (entry.isFile) {
      entry.file(file => {
        results.push({ file, path: path + file.name });
        resolve();
      }, () => resolve());
    } else if (entry.isDirectory) {
      const reader = entry.createReader();
      const dirPath = path + entry.name + '/';
      readAllEntries(reader, async (entries) => {
        for (const e of entries) await traverseEntry(e, dirPath, results);
        resolve();
      });
    } else { resolve(); }
  });
}

function readAllEntries(reader, callback) {
  const all = [];
  function read() {
    reader.readEntries(entries => {
      if (entries.length === 0) callback(all);
      else { all.push(...entries); read(); }
    }, () => callback(all));
  }
  read();
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return (bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1) + ' ' + units[i];
}

function handleFiles(newFiles) {
  if (!initData) {
    addLog('error', 'Authentication required via Telegram');
    if (isMiniApp && tg) tg.showAlert('Please open this inside the Telegram App.');
    return;
  }
  
  queuedFiles = newFiles.map(({ file, path }) => ({
    file, path, progress: 0, status: 'queued'
  }));
  renderFileList();
  startUpload();
}

function renderFileList() {
  fileList.innerHTML = '';
  if (queuedFiles.length === 0) return;
  
  queuedFiles.forEach((item, idx) => {
    const el = document.createElement('div');
    el.className = 'file-item';
    el.id = `file-${idx}`;
    el.innerHTML = `
      <span class="file-name">${item.path}</span>
      <span class="file-status">Queued</span>
    `;
    fileList.appendChild(el);
  });
}

async function uploadFile(item, idx, onProgress) {
  const formData = new FormData();
  formData.append('file', item.file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/upload`, true);
    xhr.setRequestHeader("x-tg-data", initData);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const percent = (e.loaded / e.total) * 100;
        onProgress(percent);
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

async function startUpload() {
  if (isMiniApp && tg) {
    tg.MainButton.setText('UPLOADING...');
    tg.MainButton.showProgress();
    tg.MainButton.show();
    tg.enableClosingConfirmation();
  }
  
  dzStatus.hidden = false;
  let currentIdx = 0;
  
  async function uploadNext() {
    if (currentIdx >= queuedFiles.length) {
      statusText.textContent = `Uploaded ${queuedFiles.length} files`;
      statusPct.textContent = '100%';
      statusBar.style.width = '100%';
      if (isMiniApp && tg) {
        tg.MainButton.hideProgress();
        tg.MainButton.setText('UPLOAD COMPLETE');
        tg.HapticFeedback?.notification('success');
      }
      return;
    }
    
    const item = queuedFiles[currentIdx];
    item.status = 'uploading';
    const fileEl = document.getElementById(`file-${currentIdx}`);
    fileEl.querySelector('.file-status').textContent = '0%';
    statusText.textContent = `Uploading ${item.file.name}...`;

    try {
      const res = await uploadFile(item, currentIdx, (percent) => {
        item.progress = percent;
        fileEl.querySelector('.file-status').textContent = `${Math.floor(percent)}%`;
        const totalPct = Math.floor(((currentIdx + (percent / 100)) / queuedFiles.length) * 100);
        statusPct.textContent = `${totalPct}%`;
        statusBar.style.width = `${totalPct}%`;
      });
      
      item.status = 'done';
      fileEl.classList.add('done');
      fileEl.querySelector('.file-status').textContent = 'Done';
      
      const sizeStr = formatBytes(item.file.size);
      library.unshift({ name: item.file.name, size: sizeStr, id: res.id });
      renderLibrary();
      addLog('upload', `${item.file.name} (${sizeStr}) -> ${res.id}`);
      
      if (isMiniApp && tg) tg.HapticFeedback?.impactOccurred('light');
    } catch (e) {
      item.status = 'failed';
      fileEl.querySelector('.file-status').textContent = 'Error';
      addLog('error', `Failed to upload ${item.file.name}`);
    }

    currentIdx++;
    uploadNext();
  }
  uploadNext();
}

/* ===== 5. INIT ===== */
renderHistory();
fetchLibrary();    