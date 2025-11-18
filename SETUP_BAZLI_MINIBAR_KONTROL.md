# Setup Bazlı Minibar Kontrol Sistemi

**Tarih:** 17 Ocak 2025  
**Versiyon:** 1.0.0  
**Durum:** ✅ Tamamlandı

## 📋 Genel Bakış

Setup bazlı minibar kontrol sistemi, oda tipine göre tanımlanan setup'lar üzerinden minibar kontrolü yapılmasını sağlar. Eski "İlk Dolum" ve "Ek Dolum" sisteminin yerine geçen modern bir yaklaşımdır.

### Temel Özellikler

- ✅ Oda tipine göre otomatik setup yükleme
- ✅ Setup bazlı ürün kontrolü
- ✅ Eksik ürün tamamlama
- ✅ Setup üstü ekstra ürün ekleme
- ✅ Ekstra ürün tüketim takibi
- ✅ Zimmet stok kontrolü
- ✅ Otomatik tüketim hesaplama
- ✅ Audit trail kayıtları
- ✅ Responsive mobil tasarım

## 🏗️ Mimari

### Veritabanı Değişiklikleri

#### 1. Yeni Enum Değerleri

```sql
ALTER TYPE minibar_islem_tipi ADD VALUE 'setup_kontrol';
ALTER TYPE minibar_islem_tipi ADD VALUE 'ekstra_ekleme';
ALTER TYPE minibar_islem_tipi ADD VALUE 'ekstra_tuketim';
```

#### 2. Yeni Kolon

```sql
ALTER TABLE minibar_islem_detay
ADD COLUMN ekstra_miktar INTEGER DEFAULT 0;
```

#### 3. Performans Index'leri

```sql
CREATE INDEX idx_minibar_islem_oda_tarih ON minibar_islemleri(oda_id, islem_tarihi);
CREATE INDEX idx_minibar_islem_personel_tarih ON minibar_islemleri(personel_id, islem_tarihi);
CREATE INDEX idx_minibar_detay_urun ON minibar_islem_detay(urun_id);
CREATE INDEX idx_setup_icerik_setup ON setup_icerik(setup_id);
CREATE INDEX idx_oda_tipi_setup_oda_tipi ON oda_tipi_setup(oda_tipi_id);
CREATE INDEX idx_oda_tipi_setup_setup ON oda_tipi_setup(setup_id);
```

### Backend Bileşenleri

#### 1. Servis Katmanı (`utils/minibar_servisleri.py`)

**Custom Exception'lar:**

- `ZimmetStokYetersizError` - Zimmet stoğu yetersiz
- `OdaTipiNotFoundError` - Oda tipi bulunamadı
- `SetupNotFoundError` - Setup bulunamadı

**Servis Fonksiyonları:**

- `oda_setup_durumu_getir(oda_id)` - Oda setup durumunu getirir
- `tuketim_hesapla(...)` - Tüketim miktarını hesaplar
- `zimmet_stok_kontrol(...)` - Zimmet stok kontrolü
- `zimmet_stok_dusu(...)` - Zimmet stoğundan düşüş
- `minibar_stok_guncelle(...)` - Minibar stok güncelleme
- `tuketim_kaydet(...)` - Tüketim kaydı oluşturma

#### 2. API Endpoint'leri (`routes/kat_sorumlusu_routes.py`)

**GET Endpoint'leri:**

- `GET /api/kat-sorumlusu/oda-setup/<oda_id>` - Oda setup durumu

**POST Endpoint'leri:**

- `POST /api/kat-sorumlusu/urun-ekle` - Eksik ürün ekleme
- `POST /api/kat-sorumlusu/ekstra-ekle` - Ekstra ürün ekleme
- `POST /api/kat-sorumlusu/ekstra-sifirla` - Ekstra ürün sıfırlama

**Sayfa Route'u:**

- `GET /minibar-kontrol-setup` - Ana sayfa

### Frontend Bileşenleri

#### 1. Template (`templates/kat_sorumlusu/minibar_kontrol_setup.html`)

**Özellikler:**

- Responsive tasarım
- Accordion yapısı
- Modal dialog'lar
- Toast mesajları
- Loading state'leri
- Durum renklendirmesi

#### 2. JavaScript (`static/js/minibar_kontrol_setup.js`)

**Ana Fonksiyonlar:**

- Kat/Oda seçimi
- Setup listesi yükleme
- Accordion yönetimi
- Modal yönetimi
- API çağrıları
- Toast mesajları

## 🚀 Kullanım Kılavuzu

### 1. Oda Seçimi

**Manuel Seçim:**

1. Kat dropdown'ından kat seçin
2. Oda dropdown'ından oda seçin
3. Setup listesi otomatik yüklenir

**QR Kod ile:**

1. "QR Kod ile Başla" butonuna tıklayın
2. Oda QR kodunu tarayın
3. Setup listesi otomatik yüklenir

### 2. Setup Kontrolü

**Setup Görüntüleme:**

- Her setup accordion olarak gösterilir
- Dolap içi setup'lar mor renkte
- Dolap dışı setup'lar pembe renkte
- Accordion'a tıklayarak ürünleri görüntüleyin

**Ürün Durumları:**

- 🟢 **Tam** - Setup miktarı tam
- 🔴 **Eksik** - Setup miktarından az
- 🟠 **Ekstra** - Setup üstü ürün var

### 3. Eksik Ürün Ekleme

1. Eksik durumundaki ürünün yanındaki "Ekle" butonuna tıklayın
2. Modal açılır, ürün bilgileri gösterilir
3. Eklenecek miktarı girin (varsayılan: eksik miktar)
4. Zimmet stoğunuzu kontrol edin
5. "Kaydet" butonuna tıklayın

**İşlem Sonucu:**

- Tüketim otomatik hesaplanır
- Zimmet stoğundan düşüş yapılır
- Minibar stok güncellenir
- Setup listesi yenilenir

### 4. Ekstra Ürün Ekleme

1. Tam veya Ekstra durumundaki ürünün yanındaki "Ekstra" butonuna tıklayın
2. Modal açılır, ürün bilgileri gösterilir
3. Ekstra miktarı girin
4. Zimmet stoğunuzu kontrol edin
5. "Kaydet" butonuna tıklayın

**İşlem Sonucu:**

- Zimmet stoğundan düşüş yapılır
- Ekstra miktar kaydedilir
- Tüketim kaydedilmez (henüz tüketilmedi)
- Setup listesi yenilenir

### 5. Ekstra Ürün Sıfırlama

1. Ekstra miktarı olan ürünün yanındaki "Sıfırla" butonuna tıklayın
2. Onay modalı açılır
3. Ekstra miktar gösterilir
4. "Sıfırla" butonuna tıklayın

**İşlem Sonucu:**

- Ekstra miktar tüketim olarak kaydedilir
- Ekstra miktar sıfırlanır
- Setup listesi yenilenir

## 🔒 Güvenlik

### Yetkilendirme

- Tüm endpoint'ler `@login_required` decorator'ü ile korunur
- Tüm endpoint'ler `@role_required('kat_sorumlusu')` ile kısıtlanır
- Oda erişim kontrolü yapılır (kat sorumlusunun oteline ait mi?)

### Input Validasyonu

- Tüm API endpoint'lerinde input validasyonu yapılır
- Miktar değerleri pozitif olmalıdır
- Zimmet stok kontrolü yapılır
- Oda tipi ve setup kontrolü yapılır

### Audit Trail

- Her işlem audit log'a kaydedilir
- Kullanıcı, tarih, işlem tipi bilgileri saklanır
- İşlem detayları JSONB formatında kaydedilir

## 📊 Veri Akışı

### Eksik Ürün Ekleme Akışı

```
1. Kullanıcı "Ekle" butonuna tıklar
2. Modal açılır, ürün bilgileri gösterilir
3. Kullanıcı miktarı girer ve "Kaydet" tıklar
4. Frontend: POST /api/kat-sorumlusu/urun-ekle
5. Backend: Input validasyonu
6. Backend: Zimmet stok kontrolü
7. Backend: Transaction başlat
   a. Tüketim hesapla
   b. Zimmet stoğundan düş
   c. MinibarIslem kaydı oluştur
   d. MinibarIslemDetay kaydı oluştur
   e. Audit log kaydet
8. Backend: Transaction commit
9. Frontend: Success mesajı göster
10. Frontend: Setup listesini yenile
```

### Ekstra Ürün Ekleme Akışı

```
1. Kullanıcı "Ekstra" butonuna tıklar
2. Modal açılır, ürün bilgileri gösterilir
3. Kullanıcı ekstra miktarı girer ve "Kaydet" tıklar
4. Frontend: POST /api/kat-sorumlusu/ekstra-ekle
5. Backend: Input validasyonu
6. Backend: Zimmet stok kontrolü
7. Backend: Transaction başlat
   a. Zimmet stoğundan düş
   b. MinibarIslem kaydı oluştur (tuketim=0)
   c. MinibarIslemDetay kaydı oluştur (ekstra_miktar set)
   d. Audit log kaydet
8. Backend: Transaction commit
9. Frontend: Success mesajı göster
10. Frontend: Setup listesini yenile
```

### Ekstra Sıfırlama Akışı

```
1. Kullanıcı "Sıfırla" butonuna tıklar
2. Onay modalı açılır
3. Kullanıcı "Sıfırla" tıklar
4. Frontend: POST /api/kat-sorumlusu/ekstra-sifirla
5. Backend: Son ekstra miktarı bul
6. Backend: Transaction başlat
   a. MinibarIslem kaydı oluştur (tuketim=ekstra_miktar)
   b. MinibarIslemDetay kaydı oluştur (ekstra_miktar=0)
   c. Audit log kaydet
7. Backend: Transaction commit
8. Frontend: Success mesajı göster
9. Frontend: Setup listesini yenile
```

## 🐛 Hata Yönetimi

### Frontend Hataları

**Toast Mesajları:**

- Success (Yeşil) - İşlem başarılı
- Error (Kırmızı) - Hata oluştu
- Warning (Turuncu) - Uyarı
- Info (Mavi) - Bilgilendirme

**Hata Senaryoları:**

- Oda tipi bulunamadı
- Setup bulunamadı
- Zimmet stoğu yetersiz
- Network hatası
- Validation hatası

### Backend Hataları

**Custom Exception'lar:**

```python
try:
    # İşlem
except ZimmetStokYetersizError as e:
    return jsonify({'success': False, 'error': str(e)}), 400
except OdaTipiNotFoundError as e:
    return jsonify({'success': False, 'error': str(e)}), 404
except SetupNotFoundError as e:
    return jsonify({'success': False, 'error': str(e)}), 404
except Exception as e:
    log_hata(...)
    return jsonify({'success': False, 'error': 'İşlem sırasında hata oluştu'}), 500
```

## 📈 Performans

### Optimizasyonlar

- ✅ Database index'leri eklendi
- ✅ Eager loading kullanıldı
- ✅ Query optimizasyonu yapıldı
- ✅ Frontend caching (zimmet stokları)
- ✅ Lazy loading (accordion'lar)

### Beklenen Performans

- Setup listeleme: < 2 saniye
- Ürün ekleme: < 1 saniye
- Ekstra ekleme: < 1 saniye
- Ekstra sıfırlama: < 1 saniye

## 🔄 Migration

### Migration Çalıştırma

```bash
python migrations/add_setup_bazli_minibar_kontrol.py
```

### Rollback

```bash
python migrations/add_setup_bazli_minibar_kontrol.py downgrade
```

**Not:** Enum değerleri PostgreSQL'de kolayca silinemez. Rollback için manuel müdahale gerekebilir.

## 📱 Mobil Uyumluluk

### Responsive Tasarım

- ✅ Tablet desteği (768px+)
- ✅ Telefon desteği (< 768px)
- ✅ Touch-friendly butonlar
- ✅ Responsive grid layout
- ✅ Mobile-first yaklaşım

### Test Edilen Cihazlar

- iPad (1024x768)
- iPhone 12 (390x844)
- Samsung Galaxy S21 (360x800)
- Desktop (1920x1080)

## 🧪 Test

### Manuel Test Senaryoları

**Senaryo 1: Oda Seçimi**

1. Kat seçin
2. Oda seçin
3. Setup'ların yüklendiğini doğrulayın

**Senaryo 2: Eksik Ürün Ekleme**

1. Eksik durumundaki ürünü bulun
2. "Ekle" butonuna tıklayın
3. Miktarı girin ve kaydedin
4. Setup listesinin güncellendiğini doğrulayın

**Senaryo 3: Ekstra Ürün Ekleme**

1. Tam durumundaki ürünü bulun
2. "Ekstra" butonuna tıklayın
3. Ekstra miktarı girin ve kaydedin
4. Ekstra badge'inin göründüğünü doğrulayın

**Senaryo 4: Ekstra Sıfırlama**

1. Ekstra miktarı olan ürünü bulun
2. "Sıfırla" butonuna tıklayın
3. Onaylayın
4. Ekstra badge'inin kaldırıldığını doğrulayın

## 📝 Sık Sorulan Sorular

### S: Eski "İlk Dolum" sistemi ne olacak?

**C:** Eski sistem kaldırılacak. Tüm işlemler setup bazlı sistem üzerinden yapılacak.

### S: Ekstra ürün nedir?

**C:** Setup'ta tanımlı miktarın üzerinde eklenen ürünlerdir. Örneğin setup'ta 2 adet varsa ve siz 4 adet eklerseniz, 2 adeti ekstra olarak kaydedilir.

### S: Ekstra ürün neden sıfırlanır?

**C:** Ekstra ürünler tüketildiğinde "Sıfırla" butonu ile tüketim olarak kaydedilir. Bu sayede ekstra ürün takibi yapılır.

### S: Zimmet stoğum yetersizse ne olur?

**C:** İşlem yapılamaz ve hata mesajı gösterilir. Depo sorumlusundan zimmet almanız gerekir.

### S: QR kod ile nasıl başlarım?

**C:** "QR Kod ile Başla" butonuna tıklayın ve oda QR kodunu tarayın. Sistem otomatik olarak o odanın setup'larını yükler.

## 🔗 İlgili Dosyalar

### Backend

- `utils/minibar_servisleri.py` - Servis katmanı
- `routes/kat_sorumlusu_routes.py` - API endpoint'leri
- `models.py` - Veri modelleri
- `migrations/add_setup_bazli_minibar_kontrol.py` - Migration

### Frontend

- `templates/kat_sorumlusu/minibar_kontrol_setup.html` - Template
- `static/js/minibar_kontrol_setup.js` - JavaScript

### Dokümantasyon

- `SETUP_BAZLI_MINIBAR_KONTROL.md` - Bu dosya
- `.kiro/specs/setup-bazli-minibar-kontrol/requirements.md` - Gereksinimler
- `.kiro/specs/setup-bazli-minibar-kontrol/design.md` - Tasarım
- `.kiro/specs/setup-bazli-minibar-kontrol/tasks.md` - Task listesi

## 📞 Destek

Herhangi bir sorun veya soru için:

- Sistem yöneticisi ile iletişime geçin
- Hata log'larını kontrol edin (`hata_loglari` tablosu)
- Audit log'ları inceleyin (`audit_logs` tablosu)

---

**Son Güncelleme:** 17 Ocak 2025  
**Geliştirici:** Kiro AI Assistant  
**Versiyon:** 1.0.0
