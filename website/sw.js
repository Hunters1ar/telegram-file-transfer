const CACHE_NAME = 'hunterstar-v2.3';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './style.css',
  './script.js',
  './icon.png',
  './icons/trash-icon.webp',
  './icons/favourite-icon.webp',
  './icons/settings-icon.webp',
  './icons/folders-icon.webp',
  './icons/dashboard-icon.webp',
  './icons/stats-icon.webp',
  './icons/notification-icon.webp',
  './icons/upload.webp'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            return caches.delete(name);
          }
        })
      );
    })
  );
  // Force all open tabs to reload with the new service worker immediately
  self.clients.claim();
  self.clients.matchAll({ type: 'window' }).then(clients => {
    clients.forEach(client => client.navigate(client.url));
  });
});

self.addEventListener('fetch', (event) => {
  // Skip cross-origin requests, API calls, and non-GET requests
  if (
    event.request.method !== 'GET' ||
    !event.request.url.startsWith(self.location.origin) ||
    event.request.url.includes('/api/v1/')
  ) {
    return;
  }
  
  event.respondWith(
    caches.match(event.request).then((response) => {
      // Return cached response if found
      if (response) {
        return response;
      }
      
      // Otherwise fetch from network
      return fetch(event.request).then((fetchResponse) => {
        // Cache new successful GET requests dynamically
        if (!fetchResponse || fetchResponse.status !== 200 || fetchResponse.type !== 'basic') {
          return fetchResponse;
        }
        
        let responseToCache = fetchResponse.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });
        
        return fetchResponse;
      });
    }).catch(() => {
      // Offline fallback
      return caches.match('./index.html');
    })
  );
});


