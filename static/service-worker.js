// Service Worker - Minibar Takip Sistemi PWA
const CACHE_VERSION = "minibar-v1.0.2";
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const DYNAMIC_CACHE = `${CACHE_VERSION}-dynamic`;
const IMAGE_CACHE = `${CACHE_VERSION}-images`;

// Önbelleğe alınacak statik dosyalar
const STATIC_ASSETS = [
  "/",
  "/static/manifest.json",
  // CDN'ler CORS hatası verdiği için cache'lenmiyor
  // Tailwind ve Chart.js her zaman network'ten yüklenecek
];

// Cache boyut limitleri
const MAX_DYNAMIC_CACHE_SIZE = 50;
const MAX_IMAGE_CACHE_SIZE = 60;

// Cache boyutunu sınırla
const limitCacheSize = (cacheName, maxSize) => {
  caches.open(cacheName).then((cache) => {
    cache.keys().then((keys) => {
      if (keys.length > maxSize) {
        cache.delete(keys[0]).then(() => limitCacheSize(cacheName, maxSize));
      }
    });
  });
};

// Service Worker kurulumu
self.addEventListener("install", (event) => {
  console.log("[SW] Installing service worker...");

  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => {
        console.log("[SW] Caching static assets");
        return cache.addAll(STATIC_ASSETS);
      })
      .catch((err) => {
        console.log("[SW] Error caching static assets:", err);
      })
  );

  // Yeni service worker'ı hemen aktif et
  self.skipWaiting();
});

// Eski cache'leri temizle
self.addEventListener("activate", (event) => {
  console.log("[SW] Activating service worker...");

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter(
            (cacheName) =>
              cacheName.startsWith("minibar-") &&
              cacheName !== STATIC_CACHE &&
              cacheName !== DYNAMIC_CACHE &&
              cacheName !== IMAGE_CACHE
          )
          .map((cacheName) => {
            console.log("[SW] Deleting old cache:", cacheName);
            return caches.delete(cacheName);
          })
      );
    })
  );

  // Tüm client'ları kontrol et
  return self.clients.claim();
});

// Fetch olayları - Network First stratejisi (dinamik içerik için)
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // CDN istekleri - Direkt network'e git (CORS hatası önleme)
  if (url.origin !== location.origin) {
    event.respondWith(fetch(request));
    return;
  }

  // API istekleri - Network First
  if (url.pathname.includes("/api/") || request.method !== "GET") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Başarılı response'u cache'le
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(DYNAMIC_CACHE).then((cache) => {
              cache.put(request, responseClone);
              limitCacheSize(DYNAMIC_CACHE, MAX_DYNAMIC_CACHE_SIZE);
            });
          }
          return response;
        })
        .catch(() => {
          // Network başarısız - cache'den dön
          return caches.match(request);
        })
    );
    return;
  }

  // Resimler - Cache First
  if (request.destination === "image") {
    event.respondWith(
      caches
        .match(request)
        .then((cacheResponse) => {
          return (
            cacheResponse ||
            fetch(request).then((fetchResponse) => {
              return caches.open(IMAGE_CACHE).then((cache) => {
                cache.put(request, fetchResponse.clone());
                limitCacheSize(IMAGE_CACHE, MAX_IMAGE_CACHE_SIZE);
                return fetchResponse;
              });
            })
          );
        })
        .catch(() => {
          // Fallback görsel (opsiyonel)
          return new Response("<svg>...</svg>", {
            headers: { "Content-Type": "image/svg+xml" },
          });
        })
    );
    return;
  }

  // Statik dosyalar - Cache First
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(request).then((cacheResponse) => {
        return (
          cacheResponse ||
          fetch(request).then((fetchResponse) => {
            return caches.open(STATIC_CACHE).then((cache) => {
              cache.put(request, fetchResponse.clone());
              return fetchResponse;
            });
          })
        );
      })
    );
    return;
  }

  // HTML sayfalar - Network First (güncel içerik için)
  event.respondWith(
    fetch(request)
      .then((response) => {
        const responseClone = response.clone();
        caches.open(DYNAMIC_CACHE).then((cache) => {
          cache.put(request, responseClone);
          limitCacheSize(DYNAMIC_CACHE, MAX_DYNAMIC_CACHE_SIZE);
        });
        return response;
      })
      .catch(() => {
        return caches.match(request).then((cacheResponse) => {
          return (
            cacheResponse ||
            caches.match("/").then((fallback) => {
              return (
                fallback ||
                new Response("Offline - İnternet bağlantınızı kontrol edin", {
                  status: 503,
                  statusText: "Service Unavailable",
                  headers: new Headers({
                    "Content-Type": "text/plain",
                  }),
                })
              );
            })
          );
        });
      })
  );
});

// Background Sync (opsiyonel - form verilerini offline gönderme)
self.addEventListener("sync", (event) => {
  console.log("[SW] Background sync:", event.tag);

  if (event.tag === "sync-data") {
    event.waitUntil(
      // Offline'da bekleyen verileri gönder
      syncPendingData()
    );
  }
});

// Push bildirimleri (opsiyonel - gelecekte eklenebilir)
self.addEventListener("push", (event) => {
  const options = {
    body: event.data ? event.data.text() : "Yeni bildirim",
    icon: "/static/icons/icon-192x192.png",
    badge: "/static/icons/icon-72x72.png",
    vibrate: [200, 100, 200],
    tag: "minibar-notification",
    requireInteraction: false,
  };

  event.waitUntil(self.registration.showNotification("Minibar Takip", options));
});

// Bildirime tıklama
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  event.waitUntil(clients.openWindow("/"));
});

// Yardımcı fonksiyon - Offline verileri senkronize et
async function syncPendingData() {
  // Offline'da kaydedilen verileri al ve gönder
  // İleride implement edilebilir
  console.log("[SW] Syncing pending data...");
}

// Periyodik arka plan senkronizasyonu (opsiyonel)
self.addEventListener("periodicsync", (event) => {
  if (event.tag === "update-content") {
    event.waitUntil(updateContent());
  }
});

async function updateContent() {
  // İçeriği periyodik olarak güncelle
  console.log("[SW] Updating content...");
}
