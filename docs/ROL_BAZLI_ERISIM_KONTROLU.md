# Rol Bazlı Erişim Kontrolü Dokümantasyonu

## Genel Bakış

Bu dokümantasyon, fiyatlandırma ve karlılık sistemi için rol bazlı erişim kontrollerini açıklar.

## Roller ve Yetkileri

### 1. Sistem Yöneticisi (sistem_yoneticisi)

**Tam Erişim** - Tüm API endpoint'lerine erişebilir

### 2. Admin (admin)

**Kampanya ve Oda Tipi Fiyatları Yönetimi**

- Kampanya oluşturma, güncelleme, silme
- Oda tipi fiyatları yönetimi
- Bedelsiz limit yönetimi
- Karlılık raporları görüntüleme
- Fiyat geçmişi görüntüleme

### 3. Depo Sorumlusu (depo_sorumlusu)

**Tedarikçi Fiyatları Yönetimi**

- Tedarikçi fiyatlarını görüntüleme ve güncelleme
- Alış fiyatlarını güncelleme
- Stok yönetimi
- Fiyat geçmişi görüntüleme

### 4. Kat Sorumlusu (kat_sorumlusu)

**Sadece Görüntüleme**

- Ürün fiyat bilgilerini görüntüleme
- Kampanya bilgilerini görüntüleme
- Bedelsiz limitleri görüntüleme
- Oda karlılığını görüntüleme
- Stok durumunu görüntüleme

---

## API Endpoint Yetkilendirme Matrisi

### Fiyatlandırma API'leri (`/api/v1/fiyat`)

| Endpoint                   | Sistem Yöneticisi | Admin | Depo Sorumlusu | Kat Sorumlusu |
| -------------------------- | ----------------- | ----- | -------------- | ------------- |
| `GET /urun/<id>`           | ✅                | ✅    | ✅             | ✅            |
| `POST /urun/<id>/guncelle` | ✅                | ✅    | ✅             | ❌            |
| `GET /tedarikci/<id>`      | ✅                | ✅    | ✅             | ❌            |
| `POST /dinamik-hesapla`    | ✅                | ✅    | ✅             | ✅            |
| `GET /guncel-fiyatlar`     | ✅                | ✅    | ✅             | ✅            |
| `GET /gecmis`              | ✅                | ✅    | ✅             | ❌            |

### Kampanya API'leri (`/api/v1/fiyat/kampanya`)

| Endpoint       | Sistem Yöneticisi | Admin | Depo Sorumlusu | Kat Sorumlusu |
| -------------- | ----------------- | ----- | -------------- | ------------- |
| `POST /`       | ✅                | ✅    | ❌             | ❌            |
| `GET /<id>`    | ✅                | ✅    | ❌             | ✅            |
| `PUT /<id>`    | ✅                | ✅    | ❌             | ❌            |
| `DELETE /<id>` | ✅                | ✅    | ❌             | ❌            |
| `GET /aktif`   | ✅                | ✅    | ❌             | ✅            |

### Bedelsiz Limit API'leri (`/api/v1/fiyat/bedelsiz`)

| Endpoint               | Sistem Yöneticisi | Admin | Depo Sorumlusu | Kat Sorumlusu |
| ---------------------- | ----------------- | ----- | -------------- | ------------- |
| `POST /`               | ✅                | ✅    | ❌             | ❌            |
| `GET /<id>`            | ✅                | ✅    | ❌             | ✅            |
| `PUT /<id>`            | ✅                | ✅    | ❌             | ❌            |
| `DELETE /<id>`         | ✅                | ✅    | ❌             | ❌            |
| `POST /<id>/aktif-yap` | ✅                | ✅    | ❌             | ❌            |
| `POST /<id>/pasif-yap` | ✅                | ✅    | ❌             | ❌            |
| `GET /oda-limitler`    | ✅                | ✅    | ❌             | ✅            |
| `GET /tumu`            | ✅                | ✅    | ❌             | ✅            |
| `GET /istatistikler`   | ✅                | ✅    | ❌             | ❌            |
| `GET /kullanim-takibi` | ✅                | ✅    | ❌             | ❌            |

### Cache Yönetimi API'leri (`/api/v1/fiyat/cache`)

| Endpoint                | Sistem Yöneticisi | Admin | Depo Sorumlusu | Kat Sorumlusu |
| ----------------------- | ----------------- | ----- | -------------- | ------------- |
| `GET /stats`            | ✅                | ✅    | ❌             | ❌            |
| `POST /clear/urun/<id>` | ✅                | ✅    | ❌             | ❌            |
| `POST /clear/all`       | ✅                | ❌    | ❌             | ❌            |

### Karlılık API'leri (`/api/v1/kar`)

| Endpoint                  | Sistem Yöneticisi | Admin | Depo Sorumlusu | Kat Sorumlusu |
| ------------------------- | ----------------- | ----- | -------------- | ------------- |
| `GET /dashboard`          | ✅                | ✅    | ❌             | ❌            |
| `GET /urun/<id>`          | ✅                | ✅    | ❌             | ✅            |
| `GET /oda/<id>`           | ✅                | ✅    | ❌             | ✅            |
| `GET /donemsel`           | ✅                | ✅    | ❌             | ❌            |
| `POST /hesapla`           | ✅                | ✅    | ❌             | ✅            |
| `GET /roi/<id>`           | ✅                | ✅    | ❌             | ❌            |
| `GET /analitik`           | ✅                | ✅    | ❌             | ❌            |
| `GET /trend`              | ✅                | ✅    | ❌             | ✅            |
| `GET /anomali/gelir`      | ✅                | ✅    | ❌             | ❌            |
| `GET /anomali/karlilik`   | ✅                | ✅    | ❌             | ❌            |
| `GET /optimizasyon/fiyat` | ✅                | ✅    | ❌             | ❌            |
| `GET /trend-data`         | ✅                | ✅    | ❌             | ❌            |
| `GET /urunler`            | ✅                | ✅    | ❌             | ✅            |

### Stok API'leri (`/api/v1/stok`)

| Endpoint            | Sistem Yöneticisi | Admin | Depo Sorumlusu | Kat Sorumlusu |
| ------------------- | ----------------- | ----- | -------------- | ------------- |
| `GET /durum/<id>`   | ✅                | ✅    | ✅             | ✅            |
| `GET /durum`        | ✅                | ✅    | ✅             | ✅            |
| `GET /kritik`       | ✅                | ✅    | ✅             | ❌            |
| `POST /sayim`       | ✅                | ✅    | ✅             | ❌            |
| `GET /devir-raporu` | ✅                | ✅    | ✅             | ❌            |
| `GET /deger-raporu` | ✅                | ✅    | ✅             | ❌            |
| `POST /guncelle`    | ✅                | ✅    | ✅             | ❌            |

---

## Decorator Kullanımı

### `@role_required` Decorator

```python
from utils.decorators import role_required

# Tek rol
@role_required(['admin'])
def my_endpoint():
    pass

# Çoklu rol
@role_required(['admin', 'sistem_yoneticisi'])
def my_endpoint():
    pass

# Tüm roller
@role_required(['sistem_yoneticisi', 'admin', 'depo_sorumlusu', 'kat_sorumlusu'])
def my_endpoint():
    pass
```

### Hata Yanıtları

**401 Unauthorized** - Kullanıcı giriş yapmamış

```json
{
  "success": false,
  "error": "Giriş yapmalısınız"
}
```

**403 Forbidden** - Kullanıcının yetkisi yok

```json
{
  "success": false,
  "error": "Bu işlem için yetkiniz yok (Gerekli: admin, sistem_yoneticisi, Mevcut: kat_sorumlusu)"
}
```

---

## Güvenlik Notları

1. **Her endpoint mutlaka `@login_required` decorator'ına sahip olmalı**
2. **Hassas işlemler için `@role_required` eklenmeli**
3. **API ve UI istekleri için farklı hata mesajları döndürülür**
4. **Tüm işlemler audit log'a kaydedilir**
5. **Session'da kullanıcı rolü saklanır ve her istekte kontrol edilir**

---

## Test Senaryoları

### 1. Sistem Yöneticisi Testi

```bash
# Tüm endpoint'lere erişebilmeli
curl -X GET http://localhost:5000/api/v1/fiyat/urun/1 \
  -H "Cookie: session=<sistem_yoneticisi_session>"
```

### 2. Admin Testi

```bash
# Kampanya oluşturabilmeli
curl -X POST http://localhost:5000/api/v1/fiyat/kampanya \
  -H "Cookie: session=<admin_session>" \
  -H "Content-Type: application/json" \
  -d '{"kampanya_adi": "Test", ...}'
```

### 3. Depo Sorumlusu Testi

```bash
# Tedarikçi fiyatlarını görebilmeli
curl -X GET http://localhost:5000/api/v1/fiyat/tedarikci/1 \
  -H "Cookie: session=<depo_sorumlusu_session>"

# Kampanya oluşturamamalı (403 dönmeli)
curl -X POST http://localhost:5000/api/v1/fiyat/kampanya \
  -H "Cookie: session=<depo_sorumlusu_session>"
```

### 4. Kat Sorumlusu Testi

```bash
# Fiyat bilgilerini görebilmeli
curl -X GET http://localhost:5000/api/v1/fiyat/urun/1 \
  -H "Cookie: session=<kat_sorumlusu_session>"

# Fiyat güncelleyememeli (403 dönmeli)
curl -X POST http://localhost:5000/api/v1/fiyat/urun/1/guncelle \
  -H "Cookie: session=<kat_sorumlusu_session>"
```

---

## Değişiklik Geçmişi

| Tarih      | Değişiklik                             | Yapan  |
| ---------- | -------------------------------------- | ------ |
| 2024-01-XX | İlk versiyon oluşturuldu               | Sistem |
| 2024-01-XX | Tüm endpoint'lere rol kontrolü eklendi | Sistem |

---

## İletişim

Sorularınız için: sistem@otel.com
