# Fiyatlandırma ve Karlılık Hesaplama Sistemi - Teknik Spesifikasyon

## 1. MEVCUT SİSTEM ANALİZİ

### 1.1 Mevcut Veri Yapısı Durumu

#### Mevcut Fiyat Alanları: **YOK**
- `Urun` tablosunda fiyat alanı bulunmuyor
- `StokHareket` tablosunda fiyat bilgisi yok
- `PersonelZimmetDetay` tablosunda değer bilgisi yok
- `MinibarIslemDetay` tablosunda satış fiyatı yok

#### Mevcut Raporlama Sistemi
- ✅ Miktar bazlı raporlar (stok, tüketim, zimmet)
- ✅ Excel export fonksiyonları
- ✅ Doluluk raporları
- ✅ Performans raporları
- ❌ **Fiyat bazlı raporlar YOK**
- ❌ **Karlılık analizi YOK**
- ❌ **ROI hesaplamaları YOK**

### 1.2 Güçlü Yanlar
- Sağlam stok takip altyapısı
- Kapsamlı audit trail sistemi
- Multi-otel yapısı hazır
- ML sistem entegrasyonu mevcut
- QR kod sistemi çalışıyor

### 1.3 Zayıf Yanlar
- Fiyat yönetimi altyapısı eksik
- Tedarikçi takip sistemi yok
- Karlılık hesaplama mekanizması yok
- Promosyon/kampanya yönetimi yok

---

## 2. YENİ GEREKSİNİMLER TEKNİK SPESİFİKASYONU

### 2.1 Ürün Bazlı Alış Fiyatı Sistemi

#### A. Tedarikçi Yönetimi
**Yeni Tablo: `Tedarikci`**
```sql
- id (Primary Key)
- tedarikci_adi (String, 200)
- iletisim_bilgileri (JSON) - telefon, email, adres
- aktif (Boolean, default: true)
- olusturma_tarihi (DateTime)
- guncelleme_tarihi (DateTime)
```

**Yeni Tablo: `UrunTedarikciFiyat`**
```sql
- id (Primary Key)
- urun_id (Foreign Key -> Urun.id)
- tedarikci_id (Foreign Key -> Tedarikci.id)
- alis_fiyati (Numeric(10,2))
- minimum_miktar (Integer, default: 1)
- baslangic_tarihi (DateTime)
- bitis_tarihi (DateTime, nullable)
- aktif (Boolean, default: true)
- olusturma_tarihi (DateTime)
- olusturan_id (Foreign Key -> Kullanici.id)

Index: (urun_id, tedarikci_id, aktif)
```

#### B. Fiyat Geçmişi ve Trend Analizi
**Yeni Tablo: `UrunFiyatGecmisi`**
```sql
- id (Primary Key)
- urun_id (Foreign Key -> Urun.id)
- eski_fiyat (Numeric(10,2))
- yeni_fiyat (Numeric(10,2))
- degisiklik_tipi (Enum: 'alis_fiyati', 'satis_fiyati', 'kampanya')
- degisiklik_tarihi (DateTime)
- degisiklik_sebebi (Text)
- olusturan_id (Foreign Key -> Kullanici.id)
```

#### C. Otomatik Fiyat Güncelleme Mekanizması
**Yeni Model: `FiyatGuncellemeKurali`**
```sql
- id (Primary Key)
- urun_id (Foreign Key -> Urun.id, nullable - tüm ürünler için)
- kural_tipi (Enum: 'otomatik_artir', 'otomatik_azalt', 'rakip_fiyat')
- artirma_orani (Float, nullable)
- azaltma_orani (Float, nullable)
- min_fiyat (Numeric(10,2), nullable)
- max_fiyat (Numeric(10,2), nullable)
- aktif (Boolean, default: true)
- son_uygulama (DateTime, nullable)
```

### 2.2 Satış Fiyatı Yönetimi

#### A. Dinamik Satış Fiyatı Sistemi
**Yeni Tablo: `OdaTipiSatisFiyati`**
```sql
- id (Primary Key)
- oda_tipi (String, 100) - 'Standard', 'Deluxe', 'Suite' vs.
- urun_id (Foreign Key -> Urun.id)
- satis_fiyati (Numeric(10,2))
- baslangic_tarihi (DateTime)
- bitis_tarihi (DateTime, nullable)
- aktif (Boolean, default: true)
```

**Yeni Tablo: `SezonFiyatlandirma`**
```sql
- id (Primary Key)
- sezon_adi (String, 100) - 'Yaz', 'Kış', 'Bayram' vs.
- baslangic_tarihi (Date)
- bitis_tarihi (Date)
- urun_id (Foreign Key -> Urun.id)
- fiyat_carpani (Float, default: 1.0) - mevcut fiyatı carpar
- aktif (Boolean, default: true)
```

#### B. Promosyon Fiyatları
**Yeni Tablo: `Kampanya`**
```sql
- id (Primary Key)
- kampanya_adi (String, 200)
- baslangic_tarihi (DateTime)
- bitis_tarihi (DateTime)
- urun_id (Foreign Key -> Urun.id, nullable - tüm ürünler)
- indirim_tipi (Enum: 'yuzde', 'tutar')
- indirim_degeri (Float) - % değeri veya TL tutarı
- min_siparis_miktari (Integer, default: 1)
- max_kullanim_sayisi (Integer, nullable)
- kullanilank_sayisi (Integer, default: 0)
- aktif (Boolean, default: true)
```

#### C. Bedelsiz Tanımlama Sistemi
**Yeni Tablo: `BedelsizLimit`**
```sql
- id (Primary Key)
- oda_id (Foreign Key -> Oda.id)
- urun_id (Foreign Key -> Urun.id)
- max_miktar (Integer) - Bedelsiz limit
- kullanilan_miktar (Integer, default: 0)
- baslangic_tarihi (DateTime)
- bitis_tarihi (DateTime, nullable)
- limit_tipi (Enum: 'misafir', 'kampanya', 'personel')
- Kampanya_id (Foreign Key -> Kampanya.id, nullable)
```

**Yeni Tablo: `BedelsizKullanimLog`**
```sql
- id (Primary Key)
- oda_id (Foreign Key -> Oda.id)
- urun_id (Foreign Key -> Urun.id)
- miktar (Integer)
- islem_id (Foreign Key -> MinibarIslem.id)
- kullanilma_tarihi (DateTime)
- limit_id (Foreign Key -> BedelsizLimit.id)
```

### 2.3 Karlılık Hesaplama Sistemi

#### A. Gerçek Zamanlı Kar/Zarar Hesaplaması
**Yeni Model: `KarHesaplamaServisi`**
```python
class KarHesaplamaServisi:
    @staticmethod
    def urun_karliligi_hesapla(urun_id, tarih_araligi=None):
        """Ürün bazında karlılık hesaplama"""
        
    @staticmethod  
    def oda_karliligi_hesapla(oda_id, tarih_araligi=None):
        """Oda bazında karlılık hesaplama"""
        
    @staticmethod
    def donemsel_kar_raporu(otel_id, baslangic, bitis):
        """Dönemsel kar raporu"""
```

#### B. Dönemsel Kar Analizleri
**Yeni Tablo: `DonemselKarAnalizi`**
```sql
- id (Primary Key)
- otel_id (Foreign Key -> Otel.id)
- donem_tipi (Enum: 'gunluk', 'haftalik', 'aylik')
- baslangic_tarihi (Date)
- bitis_tarihi (Date)
- toplam_gelir (Numeric(12,2))
- toplam_maliyet (Numeric(12,2))
- net_kar (Numeric(12,2))
- kar_marji (Float) - %
- analiz_verisi (JSON) - detaylı veriler
- olusturma_tarihi (DateTime)
```

#### C. ROI (Yatırım Getirisi) Hesaplamaları
**Yeni Model: `ROIHesaplamaServisi`**
```python
class ROIHesaplamaServisi:
    @staticmethod
    def urun_roi_hesapla(urun_id, baslangic, bitis):
        """Ürün bazında ROI hesaplama"""
        
    @staticmethod
    def kategori_roi_hesapla(kategori_id, baslangic, bitis):
        """Kategori bazında ROI hesaplama"""
        
    @staticmethod
    def otel_genel_roi(otel_id, yil):
        """Otel genel ROI hesaplama"""
```

### 2.4 Mini Bar Tüketim Analizi

#### A. Gerçek Zamanlı Tüketim Verileri
**Güncelleme: `MinibarIslemDetay`**
```sql
ALTER TABLE minibar_islem_detay ADD COLUMN:
- satis_fiyati (Numeric(10,2)) - Satış fiyatı
- alis_fiyati (Numeric(10,2)) - Alış fiyatı (tarihsel)
- kar_tutari (Numeric(10,2)) - Kar tutarı
- kar_orani (Float) - Kar oranı %
- bedelsiz (Boolean, default: false) - Bedelsiz işlem mi?
- kampanya_id (Foreign Key -> Kampanya.id, nullable)
```

#### B. Tüketim Kalıpları Analizi
**Yeni Tablo: `TuketimKalibi`**
```sql
- id (Primary Key)
- urun_id (Foreign Key -> Urun.id)
- oda_tipi (String, 100)
- gunler_haftasi (JSON) - Hangi günlerde tüketim
- saat_araligi (String) - '08:00-12:00' vs.
- ortalama_tuketim (Float)
- mevsimsel_degisim (Float) - %
- olusturma_tarihi (DateTime)
```

#### C. Popüler Ürün Trendleri
**Yeni Tablo: `UrunTrendAnalizi`**
```sql
- id (Primary Key)
- urun_id (Foreign Key -> Urun.id)
- donem (Enum: 'haftalik', 'aylik', 'yillik')
- baslangic_tarihi (Date)
- tuketim_miktari (Integer)
- tuketim_degeri (Numeric(10,2))
-Onceki_donem_miktari (Integer)
- degisim_orani (Float) - %
- trend_yonu (Enum: 'yukselen', 'dusen', 'sabit')
```

---

## 3. TEKNİK IMPLEMENTASYON PLANI

### 3.1 Veritabanı Değişiklikleri

#### Faz 1: Temel Fiyat Altyapısı (1-2 hafta)
```sql
-- Tedarikçi sistemi
CREATE TABLE tedarikciler (...);
CREATE TABLE urun_tedarikci_fiyatlari (...);
CREATE TABLE urun_fiyat_gecmisi (...);

-- Satış fiyat sistemi  
CREATE TABLE oda_tipi_satis_fiyatlari (...);
CREATE TABLE sezon_fiyatlandirma (...);

-- Minibar işlem güncellemeleri
ALTER TABLE minibar_islem_detay ADD COLUMN satis_fiyati, alis_fiyati, kar_tutari, kar_orani, bedelsiz;
```

#### Faz 2: Kampanya ve Bedelsiz Sistem (1 hafta)
```sql
-- Kampanya sistemi
CREATE TABLE kampanyalar (...);
CREATE TABLE bedelsiz_limitler (...);
CREATE TABLE bedelsiz_kullanim_log (...);
```

#### Faz 3: Analitik ve Raporlama (1-2 hafta)
```sql
-- Karlılık analizi
CREATE TABLE donemsel_kar_analizi (...);
CREATE TABLE tuketim_kalibi (...);
CREATE TABLE urun_trend_analizi (...);

-- ROI hesaplamaları
CREATE TABLE roi_hesaplamalari (...);
```

### 3.2 API Geliştirme Planı

#### A. Fiyat Yönetimi API'leri
```
GET    /api/fiyat/urun/{urun_id}              # Ürün fiyat bilgileri
POST   /api/fiyat/urun/{urun_id}/guncelle     # Ürün fiyat güncelleme
GET    /api/fiyat/tedarikci/{tedarikci_id}    # Tedarikçi fiyatları
POST   /api/fiyat/kampanya                     # Kampanya oluşturma
GET    /api/fiyat/oda-tipi/{oda_tipi}         # Oda tipi fiyatları
```

#### B. Karlılık API'leri
```
GET    /api/kar/urun/{urun_id}                # Ürün karlılık bilgisi
GET    /api/kar/oda/{oda_id}                  # Oda karlılık bilgisi  
GET    /api/kar/donemsel                      # Dönemsel kar raporu
GET    /api/kar/roi/{urun_id}                 # ROI hesaplama
GET    /api/kar/analitik                      # Karlılık analitikleri
```

#### C. Tüketim Analizi API'leri
```
GET    /api/tuketim/trend                     # Tüketim trendleri
GET    /api/tuketim/kalip                     # Tüketim kalıpları
GET    /api/tuketim/populer                   # Popüler ürünler
POST   /api/tuketim/analiz                    # Özel analiz
```

### 3.3 Backend Servis Geliştirmeleri

#### A. Fiyat Yönetim Servisi
```python
class FiyatYonetimServisi:
    def urun_fiyat_getir(self, urun_id, oda_tipi=None, tarih=None):
        """Dinamik fiyat hesaplama"""
        
    def kampanya_uygula(self, urun_id, miktar, oda_id=None):
        """Kampanya fiyat hesaplama"""
        
    def bedelsiz_kontrol(self, oda_id, urun_id, miktar):
        """Bedelsiz limit kontrolü"""
```

#### B. Karlılık Hesaplama Servisi
```python
class KarHesaplamaServisi:
    def gercek_zamanli_kar(self, islem_detay_listesi):
        """Gerçek zamanlı kar hesaplama"""
        
    def donemsel_analiz(self, otel_id, baslangic, bitis):
        """Dönemsel kar analizi"""
        
    def urun_roi(self, urun_id, baslangic, bitis):
        """ROI hesaplama"""
```

#### C. Tüketim Analiz Servisi
```python
class TuketimAnalizServisi:
    def tuketim_trendi(self, otel_id, tarih_araligi):
        """Tüketim trend analizi"""
        
    def sezonluk_dagilim(self, urun_id, yil):
        """Sezonluk tüketim dağılımı"""
        
    def populer_urunler(self, otel_id, donem):
        """Popüler ürün analizi"""
```

### 3.4 Frontend Geliştirme Planı

#### A. Fiyat Yönetim Ekranları
- **Ürün Fiyat Yönetimi**: `/admin/fiyatlar/urunler`
- **Tedarikçi Fiyat Listesi**: `/admin/fiyatlar/tedarikci` 
- **Kampanya Yönetimi**: `/admin/fiyatlar/kampanyalar`
- **Sezon Fiyatlandırma**: `/admin/fiyatlar/sezon`

#### B. Karlılık Dashboard'u
- **Genel Bakış**: `/admin/karlilik/dashboard`
- **Ürün Karlılığı**: `/admin/karlilik/urunler`
- **Oda Karlılığı**: `/admin/karlilik/odalar`
- **ROI Analizi**: `/admin/karlilik/roi`
- **Dönemsel Raporlar**: `/admin/karlilik/raporlar`

#### C. Tüketim Analiz Ekranları
- **Tüketim Dashboard'u**: `/admin/analiz/tuketim`
- **Trend Analizi**: `/admin/analiz/trendler`
- **Popüler Ürünler**: `/admin/analiz/populer`
- **Sezonluk Analiz**: `/admin/analiz/sezon`

---

## 4. ENTEGRASYON GEREKSİNİMLERİ

### 4.1 Mevcut Sistemle Entegrasyon
- **Stok Yönetimi**: Mevcut stok sistemi ile entegre çalışma
- **QR Kod Sistemi**: Bedelsiz işlemlerde QR kod entegrasyonu
- **Audit Trail**: Tüm fiyat değişikliklerinin loglanması
- **ML Sistemi**: Tüketim trendleri ML sistemi ile entegre

### 4.2 Dış Sistem Entegrasyonları
- **Muhasebe Sistemi**: Kar/zarar verilerinin aktarımı
- **ERP Sistemi**: Tedarikçi fiyat senkronizasyonu
- **POS Sistemi**: Satış fiyat senkronizasyonu (gelecekte)

### 4.3 Veri Migrasyonu
```python
class FiyatMigrasyonServisi:
    def mevcut_stoklara_fiyat_ata(self):
        """Mevcut stoklara varsayılan fiyat atama"""
        
    def tarihsel_fiyat_hesaplama(self):
        """Geçmiş işlemlere fiyat hesaplama"""
        
    def baseline_karlilik_olustur(self):
        """Mevcut veriler için baseline karlılık oluşturma"""
```

---

## 5. PERFORMANS VE ÖLÇEKLENEBİLİRLİK

### 5.1 Veritabanı Optimizasyonları
```sql
-- Indexler
CREATE INDEX idx_urun_fiyat_tarih ON urun_fiyat_gecmisi(urun_id, degisiklik_tarihi);
CREATE INDEX idx_kampanya_aktif ON kampanyalar(aktif, baslangic_tarihi, bitis_tarihi);
CREATE INDEX idx_bedelsiz_limit ON bedelsiz_limitler(oda_id, aktif);

-- Partitioning (büyük veri için)
CREATE TABLE tuketim_analizi_2025 PARTITION OF tuketim_analizi
FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

### 5.2 Cache Stratejisi
```python
# Redis Cache kullanımı
class FiyatCache:
    @cache.memoize(timeout=3600)  # 1 saat
    def urun_fiyat_cache(self, urun_id, oda_tipi, tarih):
        pass
        
    @cache.memoize(timeout=1800)  # 30 dakika  
    def kar_hesaplama_cache(self, otel_id, baslangic, bitis):
        pass
```

### 5.3 Asenkron İşlemler
```python
# Celery kullanarak
@celery.task
def donemsel_kar_hesapla(otel_id, baslangic, bitis):
    """Dönemsel kar hesaplama asenkron"""
    
@celery.task  
def tuketim_trendi_guncelle():
    """Tüketim trendi güncelleme"""
```

---

## 6. GÜVENLİK VE ERİŞİM KONTROLÜ

### 6.1 Rol Bazlı Erişim
- **Sistem Yöneticisi**: Tüm fiyat işlemleri
- **Admin**: Oda tipi fiyatları, kampanyalar
- **Depo Sorumlusu**: Tedarikçi fiyatları
- **Kat Sorumlusu**: Sadece görüntüleme

### 6.2 Audit ve İzleme
```python
# Fiyat değişiklik logları
class FiyatAuditLog(db.Model):
    islem_tipi = db.Column('fiyat_degisiklik')  # Fiyat değişikliği
    eski_deger = db.Column(db.Numeric(10,2))
    yeni_deger = db.Column(db.Numeric(10,2))
    degisiklik_sebebi = db.Column(db.Text)
```

### 6.3 Veri Doğrulama
```python
class FiyatValidation:
    @staticmethod
    def validate_fiyat(fiyat):
        if fiyat < 0:
            raise ValidationError("Fiyat negatif olamaz")
            
    @staticmethod  
    def validate_kampanya(kampanya):
        if kampanya.indirim_tipi == 'yuzde' and kampanya.indirim_degeri > 100:
            raise ValidationError("İndirim oranı 100%'den fazla olamaz")
```

---

## 7. TEST STRATEJİSİ

### 7.1 Unit Testler
```python
class TestFiyatYonetim(unittest.TestCase):
    def test_urun_fiyat_hesaplama(self):
        pass
        
    def test_kampanya_uygulama(self):
        pass
        
    def test_bedelsiz_limit_kontrolu(self):
        pass
```

### 7.2 Integration Testler
```python
class TestFiyatEntegrasyon(unittest.TestCase):
    def test_stok_fiyat_entegrasyonu(self):
        pass
        
    def test_karlilik_hesaplama(self):
        pass
```

### 7.3 Performance Testler
```python
class TestPerformans(unittest.TestCase):
    def test_fiyat_hesaplama_performans(self):
        # 1000 ürün için fiyat hesaplama süresi < 1 saniye
        
    def test_kar_raporu_performans(self):
        # Aylık kar raporu oluşturma süresi < 5 saniye
```

Bu teknik spesifikasyon, mini bar stok takip sisteminize kapsamlı bir fiyatlandırma ve karlılık hesaplama sistemi eklenmesi için detaylı bir yol haritası sunmaktadır.