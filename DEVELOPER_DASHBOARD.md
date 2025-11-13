# Developer Dashboard Kullanım Kılavuzu

## Giriş Bilgileri

**URL:** `/developer`  
**Şifre:** `518518Erkan!!`

## Özellikler

### 1. Sistem Sağlık Durumu

- ✅ Database bağlantı kontrolü
- 📊 CPU kullanımı (gerçek zamanlı)
- 💾 RAM kullanımı (gerçek zamanlı)
- 💿 Disk kullanımı (gerçek zamanlı)

### 2. Database İstatistikleri

- Toplam kullanıcı sayısı
- Toplam otel sayısı
- Toplam oda sayısı
- Toplam rezervasyon sayısı
- Toplam misafir sayısı
- Son 24 saatteki yeni rezervasyonlar

### 3. Kullanıcı İstatistikleri

- Toplam kullanıcılar
- Aktif kullanıcılar
- Admin kullanıcılar
- Pasif kullanıcılar

### 4. Hata Logları

- Son 50 hata kaydı
- Gerçek zamanlı hata takibi
- Log dosyasından otomatik okuma

### 5. Hızlı Aksiyonlar

- 🔄 Metrikleri Yenile
- 📄 Logları Görüntüle
- 🗑️ Cache Temizle (yakında)
- ❤️ Sağlık Kontrolü

## API Endpoint'leri

### System Health

```
GET /developer/api/system-health
```

Sistem sağlık durumunu JSON formatında döner.

**Response:**

```json
{
  "database": { "status": "healthy", "message": "Database bağlantısı OK" },
  "disk": { "status": "healthy", "percent": 45.2 },
  "memory": { "status": "healthy", "percent": 62.1 },
  "cpu": { "status": "healthy", "percent": 23.5 },
  "timestamp": "2025-11-12T18:50:00"
}
```

### Logs

```
GET /developer/api/logs?lines=100
```

Son N satır log kaydını döner.

**Parameters:**

- `lines` (optional): Kaç satır log getirileceği (default: 100)

## Auto-Refresh

Dashboard her 30 saniyede bir otomatik olarak sistem sağlık kontrolü yapar ve konsola yazar.

## Güvenlik

- Session tabanlı authentication
- Şifre korumalı giriş
- Logout özelliği
- Session timeout

## Gelecek Özellikler

- [ ] Cache yönetimi
- [ ] Database query analizi
- [ ] API endpoint performans metrikleri
- [ ] Background job monitoring
- [ ] Redis durumu
- [ ] ML model metrikleri
- [ ] Gerçek zamanlı log viewer
- [ ] Database backup/restore
- [ ] Sistem konfigürasyon editörü
- [ ] Performance profiling

## Notlar

- Dashboard sadece sistem geliştiricisi için tasarlanmıştır
- Production ortamında dikkatli kullanılmalıdır
- Hassas bilgiler içerebilir
- Şifre güvenli bir şekilde saklanmalıdır
