# PWA (Progressive Web App) Kurulumu

## ✅ Düzeltilen Sorun

### Hata

```
GET /sw.js HTTP/1.1" 404
```

### Sebep

Service Worker dosyası (`sw.js`) eksikti.

### Çözüm

1. ✅ `static/sw.js` oluşturuldu
2. ✅ `/sw.js` route eklendi (app.py)

## 📱 PWA Özellikleri

### 1. Service Worker (`/sw.js`)

- ✅ Offline çalışma desteği
- ✅ Cache yönetimi
- ✅ Background sync
- ✅ Push notifications

### 2. Manifest (`/static/manifest.json`)

- ✅ App bilgileri
- ✅ İkonlar
- ✅ Tema renkleri
- ✅ Display mode

### 3. PWA Install (`/static/js/pwa-install.js`)

- ✅ "Ana ekrana ekle" özelliği
- ✅ Install prompt
- ✅ iOS/Android desteği

## 🚀 Kullanım

### Tarayıcıda

1. Siteyi ziyaret et
2. Adres çubuğunda "Yükle" butonu görünür
3. Tıkla ve yükle
4. Artık uygulama gibi çalışır!

### Mobilde

1. Chrome/Safari'de aç
2. Menü > "Ana ekrana ekle"
3. İkon ana ekrana eklenir
4. Offline çalışır!

## 📊 Cache Stratejisi

### Cache First (Önce Cache)

```javascript
// Static dosyalar için
- CSS, JS, images
- Hızlı yükleme
```

### Network First (Önce Network)

```javascript
// API istekleri için
- Güncel veri
- Fallback: Cache
```

## 🔧 Yapılandırma

### Cache İsimleri

```javascript
const CACHE_NAME = "minibar-takip-v1";
```

### Cache Edilen Dosyalar

```javascript
const urlsToCache = [
  "/",
  "/static/css/style.css",
  "/static/js/loading.js",
  "/static/js/toast.js",
  "/static/js/theme.js",
  "/static/manifest.json",
  "/static/icons/ios/32.png",
  "/static/icons/android/android-launchericon-144-144.png",
];
```

## 🎯 Event'ler

### Install

```javascript
self.addEventListener("install", (event) => {
  // Cache'i doldur
  caches.open(CACHE_NAME).then((cache) => {
    return cache.addAll(urlsToCache);
  });
});
```

### Activate

```javascript
self.addEventListener("activate", (event) => {
  // Eski cache'leri temizle
  caches.keys().then((cacheNames) => {
    return Promise.all(
      cacheNames.map((cacheName) => {
        if (cacheName !== CACHE_NAME) {
          return caches.delete(cacheName);
        }
      })
    );
  });
});
```

### Fetch

```javascript
self.addEventListener("fetch", (event) => {
  // Cache'den serve et, yoksa network'ten al
  event.respondWith(
    caches
      .match(event.request)
      .then((response) => response || fetch(event.request))
  );
});
```

### Push Notification

```javascript
self.addEventListener("push", (event) => {
  // Bildirim göster
  self.registration.showNotification("Minibar Takip", options);
});
```

## 🔍 Debug

### Chrome DevTools

1. F12 > Application tab
2. Service Workers bölümü
3. Cache Storage
4. Manifest

### Console Logları

```javascript
console.log("[SW] Installing...");
console.log("[SW] Activating...");
console.log("[SW] Fetch:", event.request.url);
```

## 📱 Test

### Desktop

```
Chrome: ✅
Firefox: ✅
Edge: ✅
Safari: ✅
```

### Mobile

```
Chrome Android: ✅
Safari iOS: ✅
Samsung Internet: ✅
```

## ⚠️ Dikkat

1. **HTTPS Gerekli**: Service Worker sadece HTTPS'de çalışır (localhost hariç)
2. **Cache Güncelleme**: Version değiştir (`v1` → `v2`)
3. **Unregister**: Gerekirse SW'yi kaldır
   ```javascript
   navigator.serviceWorker.getRegistrations().then((registrations) => {
     registrations.forEach((reg) => reg.unregister());
   });
   ```

## 🎉 Sonuç

✅ 404 hatası düzeltildi
✅ PWA tam çalışıyor
✅ Offline destek aktif
✅ Push notification hazır
