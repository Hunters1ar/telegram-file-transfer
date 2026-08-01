/* ============================================
   HUNTERSTAR — MINIMAL + DASHBOARD SCRIPT
   ============================================ */

const tg = window.Telegram?.WebApp;
let isMiniApp = false;

if (tg) {
  tg.ready();
  tg.expand();
  isMiniApp = tg.platform !== 'unknown' && tg.platform !== undefined;
  if (isMiniApp) document.body.classList.add('tg-miniapp');
}

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
let library = [
  { name: 'quarterly_report.pdf', size: '4.2 MB', id: 'f9a2c7e1' },
  { name: 'clients_2025.zip', size: '128 MB', id: 'b4834d2e' },
  { name: 'media_assets.zip', size: '512 MB', id: '9f1ac702' }
];

let history = [
  { time: '14:22:01', type: 'upload', msg: 'quarterly_report.pdf (4.2MB) -> f9a2c7e1' },
  { time: '14:21:45', type: 'share', msg: 'b4834d2e shared to @user' },
  { time: '14:20:12', type: 'system', msg: 'Node sync complete' }
];

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

function generateHash() {
  return Math.random().toString(16).substring(2, 10);
}

function handleFiles(newFiles) {
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

function startUpload() {
  if (isMiniApp && tg) {
    tg.MainButton.setText('UPLOADING...');
    tg.MainButton.showProgress();
    tg.MainButton.show();
    tg.enableClosingConfirmation();
  }
  
  dzStatus.hidden = false;
  let currentIdx = 0;
  
  function uploadNext() {
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
    const duration = Math.min(2000, Math.max(500, item.file.size / 1024));
    const start = performance.now();
    
    function tick(now) {
      const t = Math.min((now - start) / duration, 1);
      item.progress = t * 100;
      const pct = Math.floor(t * 100);
      
      fileEl.querySelector('.file-status').textContent = `${pct}%`;
      statusPct.textContent = `${Math.floor(((currentIdx + t) / queuedFiles.length) * 100)}%`;
      statusBar.style.width = `${((currentIdx + t) / queuedFiles.length) * 100}%`;
      
      if (t < 1) {
        requestAnimationFrame(tick);
      } else {
        item.status = 'done';
        fileEl.classList.add('done');
        fileEl.querySelector('.file-status').textContent = 'Done';
        
        // Add to Library and Logs
        const id = generateHash();
        const sizeStr = formatBytes(item.file.size);
        library.unshift({ name: item.file.name, size: sizeStr, id });
        renderLibrary();
        addLog('upload', `${item.file.name} (${sizeStr}) -> ${id}`);
        
        if (isMiniApp && tg) tg.HapticFeedback?.impactOccurred('light');
        currentIdx++;
        setTimeout(uploadNext, 100);
      }
    }
    requestAnimationFrame(tick);
  }
  uploadNext();
}

/* ===== 5. INIT ===== */
renderLibrary();
renderHistory();    