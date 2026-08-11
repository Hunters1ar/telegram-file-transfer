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
  initData = "user=%7B%22id%22%3A123456%7D&hash=mock";
}

const API_BASE = "https://api.hunterstar.online/api/v1";

/* ===== STATE ===== */
let library = [];
let customFolders = [];
let activityLogs = [];
let uploadQueue = [];
let activeFile = null; 
let activeUploadedFile = null; 
let globalLimitBytes = 20 * 1024 * 1024; 
let currentView = 'dashboard';

/* ===== FAVORITES & TRASH (client-side, persisted locally) ===== */
const isFavorite = (id) => {
  const f = library.find(file => file.id === id);
  return f ? f.is_favorite : false;
};
const activeLibrary = () => library;

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
const mainSearchInput = document.getElementById('main-search-input');

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

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}

/* ===== TOAST NOTIFICATIONS ===== */
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
// Shared file-row builder used by every view. `context` = 'default' | 'trash'.
function buildFileRow(file, context = 'default') {
  const row = document.createElement('div');
  row.className = 'file-row';
  row.setAttribute('draggable', 'true');
  row.addEventListener('dragstart', e => {
    e.dataTransfer.setData('text/plain', file.id);
    row.classList.add('dragging');
  });
  row.addEventListener('dragend', () => {
    row.classList.remove('dragging');
  });
  const icon = getFileIcon(file.name);
  const safeName = escapeHtml(file.name);

  if (context === 'trash') {
    row.innerHTML = `
      <div class="f-info">
        <span class="f-icon">${icon}</span>
        <span class="f-name">${safeName}</span>
      </div>
      <div class="f-meta"><span>${file.size}</span></div>
      <div class="f-actions" onclick="event.stopPropagation()">
        <button class="f-btn" data-action="restore" title="Restore">♻</button>
        <button class="f-btn f-btn-danger" data-action="purge" title="Delete permanently">🗑</button>
      </div>
    `;
    row.querySelector('[data-action="restore"]').addEventListener('click', () => restoreFromTrash(file));
    row.querySelector('[data-action="purge"]').addEventListener('click', () => purgeFile(file));
    return row;
  }

  const fav = isFavorite(file.id);
  row.innerHTML = `
    <div class="f-info">
      <span class="f-icon">${icon}</span>
      <span class="f-name">${safeName}</span>
    </div>
    <div class="f-meta">
      <span>${file.size}</span>
      <span>${file.sharing === 'public' ? '🌍 Public' : '🔒 Private'}</span>
    </div>
    <div class="f-actions" onclick="event.stopPropagation()">
      <button class="f-btn f-star ${fav ? 'is-fav' : ''}" data-action="fav" title="Favorite">⭐</button>
      <button class="f-btn" data-action="download">⬇</button>
      <button class="f-btn" data-action="copy-link">🔗</button>
      <button class="f-btn f-btn-danger" data-action="trash" title="Delete permanently">🗑</button>
    </div>
  `;
  row.querySelector('[data-action="fav"]').addEventListener('click', (e) => { e.stopPropagation(); toggleFavorite(file); });
  row.querySelector('[data-action="download"]').addEventListener('click', () => downloadFile(file));
  row.querySelector('[data-action="copy-link"]').addEventListener('click', () => copyLink(file.id));
  row.querySelector('[data-action="trash"]').addEventListener('click', (e) => { e.stopPropagation(); deleteFile(file); });
  row.addEventListener('click', () => openDetails(file));
  return row;
}

function renderLibrary() {
  const visible = activeLibrary();
  widgetFilesCount.textContent = visible.length;

  if (visible.length === 0) {
    emptyStateEl.style.display = 'block';
    const rows = fileListEl.querySelectorAll('.file-row');
    rows.forEach(r => r.remove());
  } else {
    emptyStateEl.style.display = 'none';
    fileListEl.innerHTML = '';
    visible.forEach(file => fileListEl.appendChild(buildFileRow(file)));
  }

  // Keep the other views in sync whenever the library changes.
  renderFolders();
  renderFavorites();
  renderAnalytics();
}

function renderActivity() {
  activityListEl.innerHTML = '';
  activityLogs.forEach(log => {
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
  activityLogs.unshift({ icon, msg, time: 'Just now' });
  if (activityLogs.length > 5) activityLogs.pop();
  renderActivity();
}

/* ===== FILE ACTIONS ===== */
function copyLink(id) {
  navigator.clipboard?.writeText(`https://t.me/hunterstar_bot?start=${encodeURIComponent(id)}`);
  toast('Link copied to clipboard');
  if (isMiniApp && tg) tg.HapticFeedback?.notification('success');
}

function copyID(id) {
  navigator.clipboard?.writeText(id);
  toast('ID copied to clipboard');
  if (isMiniApp && tg) tg.HapticFeedback?.notification('success');
}

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
    const data = await res.json();
    file.name = data.name || newName;
    renderLibrary();
    document.getElementById('dp-filename').textContent = file.name;
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
      body: JSON.stringify({ sharing: 'public' })
    });
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    file.sharing = 'public';
    renderLibrary();
    toast('File is now public');
  } catch (e) {
    console.error(e);
    toast('Could not change visibility. Please try again.', 'error');
  }
}

async function makePrivate(file) {
  try {
    const res = await fetch(`${API_BASE}/files/${encodeURIComponent(file.id)}`, {
      method: 'PATCH',
      headers: { "x-tg-data": initData, "Content-Type": "application/json" },
      body: JSON.stringify({ sharing: 'private' })
    });
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    file.sharing = 'private';
    renderLibrary();
    toast('File is now private');
  } catch (e) {
    console.error(e);
    toast('Could not change visibility. Please try again.', 'error');
  }
}

/* ===== FAVORITES ACTIONS ===== */
async function toggleFavorite(file) {
  const newFavState = !file.is_favorite;
  // Optimistic update
  file.is_favorite = newFavState;
  renderLibrary();
  
  try {
    const res = await fetch(`${API_BASE}/files/${encodeURIComponent(file.id)}`, {
      method: 'PATCH',
      headers: { "x-tg-data": initData, "Content-Type": "application/json" },
      body: JSON.stringify({ is_favorite: newFavState })
    });
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    
    if (newFavState) {
      toast('Added to favorites');
      addLog('★', `Favorited ${file.name}`);
    } else {
      toast('Removed from favorites');
    }
  } catch (e) {
    console.error(e);
    toast('Could not update favorite. Please try again.', 'error');
    // Revert on error
    file.is_favorite = !newFavState;
    renderLibrary();
  }
}

/* ===== FILE TYPE GROUPING (for Folders & Analytics) ===== */
function getFileType(filename) {
  const ext = (filename.split('.').pop() || '').toLowerCase();
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) return { key: 'images', label: 'Images', icon: '🖼' };
  if (['mp4', 'mov', 'avi', 'mkv', 'webm'].includes(ext)) return { key: 'videos', label: 'Videos', icon: '🎬' };
  if (['mp3', 'wav', 'ogg', 'm4a', 'flac'].includes(ext)) return { key: 'audio', label: 'Audio', icon: '🎵' };
  if (['pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'ppt', 'pptx'].includes(ext)) return { key: 'documents', label: 'Documents', icon: '📄' };
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return { key: 'archives', label: 'Archives', icon: '📦' };
  if (['js', 'ts', 'py', 'html', 'css', 'cpp', 'c', 'java', 'json'].includes(ext)) return { key: 'code', label: 'Code', icon: '💻' };
  return { key: 'other', label: 'Other', icon: '📁' };
}

function parseSizeToBytes(file) {
  if (typeof file.sizeBytes === 'number') return file.sizeBytes;
  return 0;
}

/* ===== VIEW RENDERERS ===== */
const folderGridEl = document.getElementById('folder-grid');
const folderDetailEl = document.getElementById('folder-detail');
const folderFileListEl = document.getElementById('folder-file-list');
const folderDetailTitleEl = document.getElementById('folder-detail-title');
const folderBackBtn = document.getElementById('folder-back');
let openFolderKey = null;

async function moveFileToFolder(fileId, folderId) {
  try {
    const res = await fetch(`${API_BASE}/files/${encodeURIComponent(fileId)}`, {
      method: 'PATCH',
      headers: { "x-tg-data": initData, "Content-Type": "application/json" },
      body: JSON.stringify({ folder_id: folderId || "" })
    });
    if (!res.ok) throw new Error("Move failed");
    
    // Optimistic update
    const file = library.find(f => f.id === fileId);
    if (file) file.folder_id = folderId || null;
    renderLibrary();
    toast("File moved successfully");
    addLog('📂', `Moved file to folder`);
  } catch (e) {
    console.error(e);
    toast("Could not move file.", "error");
  }
}

document.getElementById('btn-new-folder')?.addEventListener('click', async () => {
  const name = prompt("Enter folder name:");
  if (!name) return;
  try {
    const res = await fetch(`${API_BASE}/folders/`, {
      method: 'POST',
      headers: { "x-tg-data": initData, "Content-Type": "application/json" },
      body: JSON.stringify({ name })
    });
    if (!res.ok) throw new Error("Failed to create folder");
    const newFolder = await res.json();
    await fetchFolders(); // Sync all to get exact schema
    renderFolders();
    toast("Folder created");
  } catch (e) {
    console.error(e);
    toast("Could not create folder. Name might be taken.", "error");
  }
});

function renderFolders() {
  if (!folderGridEl) return;
  
  const unfolderedSection = document.getElementById('unfoldered-section');
  const unfolderedFileListEl = document.getElementById('unfoldered-file-list');
  
  folderGridEl.innerHTML = '';
  if (customFolders.length === 0) {
    folderGridEl.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><span class="empty-icon">📁</span><p>No folders yet. Click '+ New Folder' to create one.</p></div>`;
  }

  customFolders.forEach(folder => {
    const folderFiles = activeLibrary().filter(f => f.folder_id === folder.id);
    const bytes = folderFiles.reduce((acc, f) => acc + parseSizeToBytes(f), 0);
    
    const card = document.createElement('div');
    card.className = 'folder-card';
    card.innerHTML = `
      <div style="display:flex; justify-content:space-between;">
        <span class="folder-card-icon">📁</span>
        <button class="f-btn f-btn-danger btn-del-folder" data-id="${folder.id}" title="Delete Folder">✕</button>
      </div>
      <span class="folder-card-name">${escapeHtml(folder.name)}</span>
      <span class="folder-card-meta">${folderFiles.length} file${folderFiles.length === 1 ? '' : 's'}${bytes ? ' · ' + formatBytes(bytes) : ''}</span>
    `;
    
    card.addEventListener('click', (e) => {
      if (e.target.classList.contains('btn-del-folder')) {
        e.stopPropagation();
        deleteFolder(folder);
      } else {
        openFolder(folder.id);
      }
    });

    // Drag and Drop Logic
    card.addEventListener('dragover', e => {
      e.preventDefault();
      card.classList.add('drag-over');
    });
    card.addEventListener('dragleave', e => {
      card.classList.remove('drag-over');
    });
    card.addEventListener('drop', e => {
      e.preventDefault();
      card.classList.remove('drag-over');
      const fileId = e.dataTransfer.getData('text/plain');
      if (fileId) moveFileToFolder(fileId, folder.id);
    });
    
    folderGridEl.appendChild(card);
  });

  // Populate Unfoldered Files
  if (unfolderedFileListEl) {
    unfolderedFileListEl.innerHTML = '';
    const unfolderedFiles = activeLibrary().filter(f => !f.folder_id);
    if (unfolderedFiles.length === 0) {
      unfolderedFileListEl.innerHTML = `<div class="empty-state"><p style="color:var(--text-muted); font-size:13px; margin:0;">No unorganized files.</p></div>`;
    } else {
      unfolderedFiles.forEach(file => unfolderedFileListEl.appendChild(buildFileRow(file)));
    }
  }

  // If a folder is open, refresh its contents
  if (openFolderKey && customFolders.find(f => f.id === openFolderKey)) {
    openFolder(openFolderKey);
  } else {
    openFolderKey = null;
    folderDetailEl.hidden = true;
    folderGridEl.hidden = false;
    if (unfolderedSection) unfolderedSection.hidden = false;
  }
}

async function deleteFolder(folder) {
  if (!confirm(`Delete folder "${folder.name}"? Files inside will be moved to the main dashboard.`)) return;
  try {
    const res = await fetch(`${API_BASE}/folders/${folder.id}`, {
      method: 'DELETE',
      headers: { "x-tg-data": initData }
    });
    if (!res.ok) throw new Error("Delete failed");
    // Update local state files to have no folder
    library.forEach(f => {
      if (f.folder_id === folder.id) f.folder_id = null;
    });
    customFolders = customFolders.filter(f => f.id !== folder.id);
    if (openFolderKey === folder.id) {
      openFolderKey = null;
      folderDetailEl.hidden = true;
      folderGridEl.hidden = false;
      const unfolderedSection = document.getElementById('unfoldered-section');
      if (unfolderedSection) unfolderedSection.hidden = false;
    }
    renderLibrary();
    toast("Folder deleted");
  } catch(e) {
    console.error(e);
    toast("Failed to delete folder", "error");
  }
}

function openFolder(folderId) {
  const folder = customFolders.find(f => f.id === folderId);
  if (!folder) return;
  openFolderKey = folderId;
  folderDetailTitleEl.textContent = `📁 ${folder.name}`;
  folderFileListEl.innerHTML = '';
  
  const files = activeLibrary().filter(f => f.folder_id === folderId);
  if (files.length === 0) {
    folderFileListEl.innerHTML = `<div style="color:var(--text-muted); font-size:13px;">This folder is empty.</div>`;
  } else {
    files.forEach(file => folderFileListEl.appendChild(buildFileRow(file)));
  }
  
  folderGridEl.hidden = true;
  folderDetailEl.hidden = false;
  const unfolderedSection = document.getElementById('unfoldered-section');
  if (unfolderedSection) unfolderedSection.hidden = true;
}

if (folderBackBtn) {
  folderBackBtn.addEventListener('click', () => {
    openFolderKey = null;
    folderDetailEl.hidden = true;
    folderGridEl.hidden = false;
    const unfolderedSection = document.getElementById('unfoldered-section');
    if (unfolderedSection) unfolderedSection.hidden = false;
  });
}

function renderFavorites() {
  const listEl = document.getElementById('fav-file-list');
  if (!listEl) return;
  const favs = activeLibrary().filter(f => isFavorite(f.id));
  listEl.innerHTML = '';
  if (favs.length === 0) {
    listEl.innerHTML = `<div class="empty-state"><span class="empty-icon">⭐</span><p>No favorites yet. Tap the star on a file to add it here.</p></div>`;
    return;
  }
  favs.forEach(file => listEl.appendChild(buildFileRow(file)));
}


function renderAnalytics() {
  const visible = activeLibrary();
  const totalFiles = visible.length;
  const publicCount = visible.filter(f => f.sharing === 'public').length;
  const privateCount = totalFiles - publicCount;
  const favCount = visible.filter(f => isFavorite(f.id)).length;
  const totalBytes = visible.reduce((sum, f) => sum + parseSizeToBytes(f), 0);
  const limit = 100 * 1024 * 1024 * 1024;

  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('an-files', totalFiles);
  set('an-public', publicCount);
  set('an-favorites', favCount);
  set('an-storage-used', formatBytes(totalBytes));
  set('an-storage-sub', `of 100 GB`);
  const fill = document.getElementById('an-storage-fill');
  if (fill) fill.style.width = `${Math.min((totalBytes / limit) * 100, 100)}%`;

  // Bar chart by file type
  const typeChart = document.getElementById('an-type-chart');
  if (typeChart) {
    const groups = groupByType();
    const keys = Object.keys(groups).sort((a, b) => groups[b].files.length - groups[a].files.length);
    const max = keys.reduce((m, k) => Math.max(m, groups[k].files.length), 0) || 1;
    if (keys.length === 0) {
      typeChart.innerHTML = `<p style="color:var(--text-muted);font-size:13px">No files to analyze yet.</p>`;
    } else {
      typeChart.innerHTML = keys.map(k => {
        const g = groups[k];
        const pct = (g.files.length / max) * 100;
        return `
          <div class="bar-row">
            <div class="bar-label"><span>${g.icon} ${g.label}</span><span>${g.files.length}</span></div>
            <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
          </div>`;
      }).join('');
    }
  }

  // Visibility split
  const visChart = document.getElementById('an-visibility-chart');
  if (visChart) {
    const total = totalFiles || 1;
    const pubPct = (publicCount / total) * 100;
    const privPct = (privateCount / total) * 100;
    visChart.innerHTML = `
      <div class="split-track">
        <div class="split-seg-public" style="width:${pubPct}%"></div>
        <div class="split-seg-private" style="width:${privPct}%"></div>
      </div>
      <div class="split-legend">
        <div class="legend-row"><span class="legend-dot" style="background:var(--crimson)"></span> Public <span class="count">${publicCount}</span></div>
        <div class="legend-row"><span class="legend-dot" style="background:rgba(255,255,255,0.35)"></span> Private <span class="count">${privateCount}</span></div>
      </div>`;
  }
}

const viewMap = {
  dashboard: 'main-dashboard-view',
  folders: 'view-folders',
  favorites: 'view-favorites',
  settings: 'view-settings',
  analytics: 'view-analytics'
};

function showView(view) {
  if (!viewMap[view]) return;
  currentView = view;

  Object.values(viewMap).forEach(id => {
    const el = document.getElementById(id);
    if (el) el.hidden = (id !== viewMap[view]);
  });

  // Sync active state on both navs.
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(i =>
    i.classList.toggle('active', i.dataset.view === view));
  document.querySelectorAll('.m-nav-item').forEach(i => {
    if (i.classList.contains('upload-btn')) return;
    i.classList.toggle('active', i.dataset.view === view);
  });

  // Close details panel when leaving the dashboard.
  if (view !== 'dashboard') detailsPanel.classList.remove('open');

  // Refresh the freshly shown view's data.
  if (view === 'folders') renderFolders();
  else if (view === 'favorites') renderFavorites();
  else if (view === 'analytics') renderAnalytics();
}

/* ===== DETAILS PANEL ===== */
function refreshVisibilityButton() {
  const btn = document.getElementById('dp-btn-visibility');
  if (!btn || !activeFile) return;
  const isPublic = activeFile.sharing === 'public';
  btn.innerHTML = isPublic ? '<span class="dp-icon">🔒</span> Make Private' : '<span class="dp-icon">🌍</span> Make Public';
}

function openDetails(file) {
  activeFile = file;
  document.getElementById('dp-filename').textContent = file.name;
  document.getElementById('dp-size').textContent = file.size;
  document.getElementById('dp-hash').textContent = file.id;
  document.getElementById('dp-downloads').textContent = '0';
  document.getElementById('dp-visibility').textContent = file.sharing === 'public' ? '🌍 Public' : '🔒 Private';
  document.getElementById('dp-created').textContent = timeAgo(file.uploaded_at || new Date());
  refreshVisibilityButton();
  
  const ext = file.name.split('.').pop().toLowerCase();
  const previewEl = document.getElementById('dp-media-preview');
  if (previewEl) {
    previewEl.innerHTML = '';
    previewEl.hidden = true;
    
    const mediaUrl = `${API_BASE}/download/${encodeURIComponent(file.id)}`;
    
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) {
      previewEl.innerHTML = `<img src="${mediaUrl}" alt="${escapeHtml(file.name)}">`;
      previewEl.hidden = false;
    } else if (['mp3', 'wav', 'ogg', 'm4a'].includes(ext)) {
      previewEl.innerHTML = `<audio controls controlsList="nodownload"><source src="${mediaUrl}"></audio>`;
      previewEl.hidden = false;
    } else if (['mp4', 'webm', 'mov'].includes(ext)) {
      previewEl.innerHTML = `<video controls controlsList="nodownload" src="${mediaUrl}"></video>`;
      previewEl.hidden = false;
    }
  }

  detailsPanel.classList.add('open');
}

dpClose.addEventListener('click', () => {
  detailsPanel.classList.remove('open');
  const previewEl = document.getElementById('dp-media-preview');
  if (previewEl) {
    previewEl.innerHTML = '';
    previewEl.hidden = true;
  }
});

const dpActionButtons = document.querySelectorAll('.dp-actions .dp-btn:not(#dp-btn-visibility)');
if (dpActionButtons[0]) dpActionButtons[0].addEventListener('click', () => activeFile && downloadFile(activeFile));
if (dpActionButtons[1]) dpActionButtons[1].addEventListener('click', () => activeFile && copyLink(activeFile.id));
if (dpActionButtons[2]) dpActionButtons[2].addEventListener('click', () => activeFile && renameFile(activeFile));
if (dpActionButtons[3]) dpActionButtons[3].addEventListener('click', () => activeFile && deleteFile(activeFile));

const dpVisibilityBtn = document.getElementById('dp-btn-visibility');
if (dpVisibilityBtn) {
  dpVisibilityBtn.addEventListener('click', async () => {
    if (!activeFile) return;
    if (activeFile.sharing === 'public') {
      await makePrivate(activeFile);
    } else {
      await makePublic(activeFile);
    }
    document.getElementById('dp-visibility').textContent = activeFile.sharing === 'public' ? '🌍 Public' : '🔒 Private';
    refreshVisibilityButton();
  });
}

const dpMoveBtn = document.getElementById('dp-btn-move');
const folderModal = document.getElementById('folder-modal');
const folderModalList = document.getElementById('folder-modal-list');
const btnCloseFolderModal = document.getElementById('btn-close-folder-modal');

if (dpMoveBtn) {
  dpMoveBtn.addEventListener('click', () => {
    if (!activeFile) return;
    folderModalList.innerHTML = '';
    
    // Add root option
    const rootItem = document.createElement('div');
    rootItem.className = 'cmd-item';
    rootItem.innerHTML = `<span>📁</span> Dashboard (Remove from folder)`;
    rootItem.onclick = () => {
      moveFileToFolder(activeFile.id, "root");
      folderModal.hidden = true;
    };
    folderModalList.appendChild(rootItem);
    
    customFolders.forEach(folder => {
      const el = document.createElement('div');
      el.className = 'cmd-item';
      el.innerHTML = `<span>📁</span> ${escapeHtml(folder.name)}`;
      el.onclick = () => {
        moveFileToFolder(activeFile.id, folder.id);
        folderModal.hidden = true;
      };
      folderModalList.appendChild(el);
    });
    
    folderModal.hidden = false;
  });
}

if (btnCloseFolderModal) {
  btnCloseFolderModal.addEventListener('click', () => {
    folderModal.hidden = true;
  });
}

/* ===== API FETCH ===== */
async function fetchStats() {
  if (!initData) return;
  try {
    const res = await fetch(`${API_BASE}/stats/`, {
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
    
    const limit = 100 * 1024 * 1024 * 1024; 
    const percent = Math.min((stats.total_size / limit) * 100, 100);
    const textEl = document.getElementById('sb-storage-text');
    const fillEl = document.getElementById('sb-storage-fill');
    
    if (textEl) textEl.textContent = `${formatBytes(stats.total_size)} / 100 GB`;
    if (fillEl) fillEl.style.width = `${percent}%`;
    
  } catch (e) {
    console.error("Failed to fetch stats", e);
  }
}

async function fetchFolders() {
  if (!initData) return;
  try {
    const res = await fetch(`${API_BASE}/folders/`, {
      headers: { "x-tg-data": initData }
    });
    if (!res.ok) throw new Error("Failed to fetch folders");
    customFolders = await res.json();
  } catch (e) {
    console.error("Failed to fetch folders", e);
  }
}

async function fetchLibrary() {
  if (!initData) return;
  try {
    await fetchFolders(); // Sync folders first
    const res = await fetch(`${API_BASE}/files/`, {
      headers: { "x-tg-data": initData }
    });
    if (!res.ok) throw new Error("Failed to fetch files");
    const files = await res.json();
    library = files.map(f => ({
      name: f.name,
      size: formatBytes(f.size),
      sizeBytes: f.size || 0,
      id: f.id,
      category: f.category,
      sharing: f.sharing || 'private',
      is_favorite: f.is_favorite || false,
      folder_id: f.folder_id || null,
      uploaded_at: f.uploaded_at
    }));
    renderLibrary();
    addLog('🔄', 'Library synced');
  } catch (e) {
    console.error(e);
    addLog('❌', 'Sync failed: ' + e.message);
    toast('Sync err: ' + e.message, 'error');
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
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="q-pct">0%</span>
          <button class="q-cancel-btn" data-idx="${idx}" title="Cancel">✕</button>
        </div>
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

dzQueue.addEventListener('click', (e) => {
  if (e.target.classList.contains('q-cancel-btn')) {
    const idx = parseInt(e.target.dataset.idx, 10);
    cancelUpload(idx);
  }
});

function cancelUpload(idx) {
  const item = uploadQueue[idx];
  if (!item || item.status === 'done' || item.status === 'cancelled') return;
  item.status = 'cancelled';
  if (item.xhr) item.xhr.abort();
  if (item.abortController) item.abortController.abort();
  
  updateQueueItem(idx, 0, item.file.size, 0, 'Cancelled');
  const el = document.getElementById(`q-${idx}`);
  if (el) el.classList.add('q-cancelled');
}

async function computeSHA256(file) {
  if (!window.crypto || !window.crypto.subtle) return null;
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

async function uploadFile(item, idx) {
  item.abortController = new AbortController();
  let sha256 = null;
  if (item.file.size < 100 * 1024 * 1024) {
    updateQueueItem(idx, 0, item.file.size, 0, "Hashing...");
    sha256 = await computeSHA256(item.file);
  }

  const reqRes = await fetch(`${API_BASE}/upload/request/`, {
    method: 'POST',
    headers: { "x-tg-data": initData, "Content-Type": "application/json" },
    signal: item.abortController.signal,
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

  await new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    item.xhr = xhr;
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

  const confRes = await fetch(`${API_BASE}/upload/confirm/`, {
    method: 'POST',
    headers: { "x-tg-data": initData, "Content-Type": "application/json" },
    signal: item.abortController.signal,
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

async function startUploads() {
  let lastSuccess = null;

  for (let idx = 0; idx < uploadQueue.length; idx++) {
    const item = uploadQueue[idx];
    if (item.status === 'cancelled') continue;
    item.status = 'uploading';
    try {
      const result = await uploadFile(item, idx);
      if (item.status === 'cancelled') continue;
      item.status = 'done';
      updateQueueItem(idx, item.file.size, item.file.size, 100, 'Done');

      const newFile = {
        name: (result && result.name) || item.file.name,
        size: formatBytes((result && result.size) ?? item.file.size),
        sizeBytes: (result && result.size) ?? item.file.size ?? 0,
        id: (result && (result.id || result.file_id || result.r2_key)) || null,
        category: (result && result.category) || 'private',
        sharing: (result && result.sharing) || 'private',
        uploaded_at: (result && result.uploaded_at) || new Date().toISOString()
      };
      library.unshift(newFile);
      addLog('⬆', `Uploaded ${newFile.name}`);
      lastSuccess = newFile;
    } catch (e) {
      if (item.status === 'cancelled') continue;
      console.error(e);
      item.status = 'error';
      updateQueueItem(idx, 0, item.file.size, 0, 'Failed');
      toast(`Upload failed: ${item.file.name}`, 'error');
      addLog('❌', `Upload failed: ${item.file.name}`);
    }
  }

  renderLibrary();
  fetchStats();

  if (lastSuccess) {
    activeUploadedFile = lastSuccess;
    dzQueue.hidden = true;
    dzSuccess.hidden = false;
    
    document.getElementById('success-filename').textContent = lastSuccess.name;
    document.getElementById('success-id').textContent = '🆔 ' + lastSuccess.id;
  } else {
    // If all failed or cancelled, revert to default dropzone view
    dzQueue.hidden = true;
    dzDefault.hidden = false;
  }
}

/* ===== SUCCESS CARD ACTIONS ===== */
document.getElementById('btn-copy-id').addEventListener('click', () => {
  if (activeUploadedFile && activeUploadedFile.id) copyID(activeUploadedFile.id);
});
document.getElementById('btn-copy-link').addEventListener('click', () => {
  if (activeUploadedFile && activeUploadedFile.id) copyLink(activeUploadedFile.id);
});
document.getElementById('btn-make-public').addEventListener('click', async () => {
  if (activeUploadedFile) {
    await makePublic(activeUploadedFile);
    toast('File is now public!');
  }
});

/* ===== COMMAND PALETTE LOGIC (Ctrl+K) ===== */
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    cmdPalette.hidden = false;
    cmdInput.focus();
  }
  if (e.key === 'Escape') {
    cmdPalette.hidden = true;
    cmdInput.value = '';
  }
});

cmdPalette.addEventListener('click', (e) => {
  if (e.target === cmdPalette) {
    cmdPalette.hidden = true;
  }
});

document.querySelectorAll('.cmd-item').forEach(item => {
  item.addEventListener('click', () => {
    const action = item.dataset.action;
    if (action === 'upload') {
      fileInput.click();
    } else if (action === 'folder') {
      showView('folders');
    } else if (action === 'settings') {
      showView('settings');
    } else if (action === 'language') {
      showView('settings');
      setTimeout(() => document.getElementById('lang-select')?.focus(), 50);
    }
    cmdPalette.hidden = true;
  });
});

// Also allow clicking the main search bar to open the command palette for better UX
if (mainSearchInput) {
  mainSearchInput.addEventListener('focus', () => {
    cmdPalette.hidden = false;
    cmdInput.focus();
    mainSearchInput.blur();
  });
}

/* ===== MOBILE & SIDEBAR NAV ROUTING ===== */
document.querySelectorAll('.m-nav-item').forEach(item => {
  item.addEventListener('click', (e) => {
    e.preventDefault();
    if (item.classList.contains('upload-btn')) return;
    if (item.dataset.view) showView(item.dataset.view);
  });
});

document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => {
  item.addEventListener('click', (e) => {
    e.preventDefault();
    if (item.dataset.view) showView(item.dataset.view);
  });
});

/* ===== INITIALIZATION ===== */
fetchStats();
fetchLibrary();
