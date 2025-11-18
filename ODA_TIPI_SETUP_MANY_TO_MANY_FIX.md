# Oda Tipi Setup Many-to-Many İlişki Düzeltmesi

## Problem

Kat Yönetimi sayfasındaki Oda Tipleri modalında setup'lar görünmüyordu.

## Kök Neden

1. API'den gelen veri yapısı yanlıştı - `tip.setup` string olarak bekleniyordu ama artık many-to-many ilişki
2. Frontend'de tek setup gösteriliyordu, çoklu setup desteği yoktu
3. Yeni/Düzenle modallarında tek seçim vardı, çoklu seçim yoktu

## Yapılan Değişiklikler

### 1. Backend API Güncellemeleri (`routes/sistem_yoneticisi_routes.py`)

#### GET /api/oda-tipleri

- ✅ `setup_adlari` array eklendi - setup isimlerini döndürüyor
- ✅ `setup_ids` zaten vardı

#### POST /api/oda-tipleri

- ✅ `setup` string yerine `setup_ids` array kabul ediyor
- ✅ Many-to-many ilişki ile setup'lar ekleniyor
- ✅ Response'da `setup_ids` ve `setup_adlari` döndürülüyor

#### PUT /api/oda-tipleri/<id>

- ✅ `setup` string yerine `setup_ids` array kabul ediyor
- ✅ Many-to-many ilişki ile setup'lar güncelleniyor
- ✅ Response'da `setup_ids` ve `setup_adlari` döndürülüyor

### 2. Frontend Güncellemeleri (`templates/sistem_yoneticisi/kat_tanimla.html`)

#### Oda Tipleri Listesi

- ✅ Setup'lar artık array olarak gösteriliyor
- ✅ Her setup için renkli badge gösteriliyor (MINI=yeşil, MAXI=mor)
- ✅ Birden fazla setup yan yana gösteriliyor

#### Yeni Oda Tipi Modal

- ✅ Setup select'i `multiple` yapıldı
- ✅ Setup listesi API'den dinamik yükleniyor (`/api/setup`)
- ✅ Ctrl/Cmd ile çoklu seçim yapılabiliyor
- ✅ `setup_ids` array olarak gönderiliyor

#### Oda Tipi Düzenle Modal

- ✅ Setup select'i `multiple` yapıldı
- ✅ Setup listesi API'den dinamik yükleniyor
- ✅ Mevcut setup'lar otomatik seçili geliyor
- ✅ `setup_ids` array olarak gönderiliyor

#### JavaScript Fonksiyonları

- ✅ `yeniOdaTipiModal()` - Setup listesini API'den çekiyor
- ✅ `odaTipiKaydet()` - Çoklu setup ID'leri gönderiyor
- ✅ `odaTipiDuzenleModal()` - Setup'ları yükleyip seçili olanları işaretliyor
- ✅ `odaTipiGuncelle()` - Çoklu setup ID'leri gönderiyor
- ✅ `loadOdaTipleri()` - Setup'ları array olarak render ediyor

## Test Senaryoları

### ✅ Görüntüleme

1. Kat Yönetimi > Oda Tipleri butonuna tıkla
2. Tabloda setup sütununda setup'lar görünmeli
3. Birden fazla setup varsa yan yana badge'ler görünmeli

### ✅ Yeni Ekleme

1. Yeni Ekle butonuna tıkla
2. Setup listesi yüklenmeli
3. Ctrl/Cmd ile birden fazla setup seç
4. Kaydet
5. Tabloda seçilen setup'lar görünmeli

### ✅ Düzenleme

1. Bir oda tipinin Düzenle butonuna tıkla
2. Setup listesi yüklenmeli
3. Mevcut setup'lar seçili gelmeli
4. Setup'ları değiştir
5. Güncelle
6. Tabloda yeni setup'lar görünmeli

## Teknik Detaylar

### Many-to-Many İlişki

```python
# OdaTipi modelinde
setuplar = db.relationship('Setup', secondary='oda_tipi_setup', backref='oda_tipleri')
```

### API Response Formatı

```json
{
  "success": true,
  "oda_tipleri": [
    {
      "id": 1,
      "ad": "STANDARD",
      "dolap_sayisi": 1,
      "setup_ids": [1, 2],
      "setup_adlari": ["MINI", "MAXI"]
    }
  ]
}
```

### Frontend Render

```javascript
// Çoklu setup gösterimi
setupHTML = tip.setup_adlari
  .map((setupAd) => {
    const renk = setupAd === "MAXI" ? "purple" : "green";
    return `<span class="badge ${renk}">${setupAd}</span>`;
  })
  .join("");
```

## Sonuç

✅ Setup'lar artık Oda Tipleri modalında görünüyor
✅ Çoklu setup seçimi çalışıyor
✅ Yeni ekleme ve düzenleme çalışıyor
✅ Many-to-many ilişki tam entegre
