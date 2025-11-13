/**
 * Service Worker - PWA Support
 * Minibar Takip Sistemi
 */

const CACHE_NAME = 'minibar-takip-v1';
const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/js/loading.js',
  '/static/js/toast.js',
  '/static/js/theme.js',
  '/static/manifest.json',
  '/static/icons/ios/32.png',
  '/static/icons/android/android-launchericon-144-144.png'
];

// Install event - cache resources
self.addEventListener('install', event => {
  console.log('[SW] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[SW] Caching app shell');
        return cache.addAll(urlsToCache);
      })
      .catch(err => {
        console.error('[SW] Cache failed:', err);
      })
  );
  self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  return self.clients.claim();
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other non-http(s) requests
  if (!event.request.url.startsWith('http')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }

        // Clone the request
        const fetchRequest = event.request.clone();

        return fetch(fetchRequest).then(response => {
          // Check if valid response
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clone the response
          const responseToCache = response.clone();

          // Cache the fetched response
          caches.open(CACHE_NAME)
            .then(cache => {
              cache.put(event.request, responseToCache);
            });

          return response;
        }).catch(err => {
          console.error('[SW] Fetch failed:', err);
          // Return offline page if available
          return caches.match('/offline.html');
        });
      })
  );
});

// Background sync
self.addEventListener('sync', event => {
  console.log('[SW] Background sync:', event.tag);
  if (event.tag === 'sync-data') {
    event.waitUntil(syncData());
  }
});

// Push notification
self.addEventListener('push', event => {
  console.log('[SW] Push received:', event);
  
  const options = {
    body: event.data ? event.data.text() : 'Yeni bildirim',
    icon: '/static/icons/android/android-launchericon-144-144.png',
    badge: '/static/icons/ios/32.png',
    vibrate: [200, 100, 200],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    }
  };

  event.waitUntil(
    self.registration.showNotification('Minibar Takip', options)
  );
});

// Notification click
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notification clicked:', event);
  event.notification.close();

  event.waitUntil(
    clients.openWindow('/')
  );
});

// Helper function for background sync
async function syncData() {
  try {
    // Sync logic here
    console.log('[SW] Syncing data...');
    return Promise.resolve();
  } catch (err) {
    console.error('[SW] Sync failed:', err);
    return Promise.reject(err);
  }
}

console.log('[SW] Service Worker loaded');
