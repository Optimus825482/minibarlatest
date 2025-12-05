# 🏨 OTEL MİNİBAR TAKİP SİSTEMİ - RAG EĞİTİM BELGESİ

## 📋 BELGE BİLGİLERİ

- **Versiyon:** 2.0
- **Tarih:** 5 Aralık 2025
- **Amaç:** AI Asistan RAG Eğitimi için Kapsamlı Sistem Dokümantasyonu
- **Hedef:** Sistemin tüm özelliklerini, iş akışlarını ve teknik detaylarını içeren eğitim verisi

---

## 1. SİSTEM TANIMI VE GENEL BAKIŞ

### 1.1 Sistem Nedir?

Otel Minibar Takip Sistemi, otel işletmelerinde minibar stok yönetimini, personel zimmet takibini, oda doluluk yönetimini ve tüketim analizlerini dijital ortamda yönetmek için geliştirilmiş profesyonel bir web uygulamasıdır.

### 1.2 Temel Amaçlar

- Otel minibar stoklarının gerçek zamanlı takibi
- Personel zimmet yönetimi ve FIFO algoritması ile kullanım takibi
- Oda bazlı minibar dolum ve tüketim kontrolü
- QR kod ile hızlı erişim ve misafir talep sistemi
- ML tabanlı anomali tespiti ve tahminleme
- Kapsamlı raporlama ve analiz

### 1.3 Teknoloji Stack

- **Backend:** Flask 3.0, Python 3.11+
- **Database:** PostgreSQL (Production), MySQL (Local)
- **ORM:** SQLAlchemy 2.0
- **Frontend:** Tailwind CSS 3.x, Chart.js 4.4
- **ML:** scikit-learn, pandas, numpy
- **Deployment:** Coolify (Docker), Railway
- **Task Queue:** Celery + Redis

---

## 2. KULLANICI ROLLERİ VE YETKİLERİ

### 2.1 Sistem Yöneticisi (sistem_yoneticisi)

**Tam sistem yetkisine sahip en üst düzey kullanıcı.**

**Yetkiler:**

- Otel tanımlama ve düzenleme
- Kat ve oda yönetimi
- Admin kullanıcı atama
- Depo sorumlusu ve kat sorumlusu tanımlama
- Sistem loglarını görüntüleme
- Audit trail erişimi
- Sistem ayarları yönetimi
- Tedarikçi yönetimi
- Setup (minibar şablonu) yönetimi
- Fiyat yönetimi ve karşılaştırma
- Tüm raporlara erişim

**Erişebildiği Sayfalar:**

- Dashboard (sistem_yoneticisi/dashboard.html)
- Otel tanımlama/düzenleme
- Kat tanımlama/düzenleme
- Oda tanımlama/düzenleme
- Admin atama
- Personel yönetimi
- Setup yönetimi
- Tedarikçi yönetimi
- Sistem logları
- Audit trail
- Fiyat yönetimi
- Depo stokları görüntüleme
- Minibar durumları
- Dolum talepleri

### 2.2 Admin (admin)

**Ürün ve personel yönetimi yetkisine sahip kullanıcı.**

**Yetkiler:**

- Ürün grubu oluşturma ve düzenleme
- Ürün tanımlama ve düzenleme
- Personel tanımlama (depo/kat sorumlusu)
- Tüm raporlara erişim
- Kampanya yönetimi
- Bedelsiz limit yönetimi
- ML Dashboard erişimi
- Karlılık analizi
- Fiyat yönetimi

**Erişebildiği Sayfalar:**

- Dashboard (admin/dashboard.html)
- Ürün grupları
- Ürünler
- Personel tanımlama
- Kampanya yönetimi
- Bedelsiz limit yönetimi
- ML Dashboard
- Karlılık dashboard
- Fiyat yönetimi
- DB Optimization dashboard

### 2.3 Depo Sorumlusu (depo_sorumlusu)

**Stok ve zimmet yönetimi yetkisine sahip kullanıcı. Birden fazla otele atanabilir.**

**Yetkiler:**

- Stok giriş/çıkış işlemleri
- Personel zimmet atama
- Zimmet iade alma
- Minibar durumlarını görüntüleme
- Stok raporları
- Zimmet raporları
- Doluluk yönetimi (Excel yükleme)
- Satın alma işlemleri
- Kat sorumlusu siparişlerini yönetme
- Görev raporları

**Erişebildiği Sayfalar:**

- Dashboard (depo_sorumlusu/dashboard.html)
- Stok girişi
- Stoklarım
- Personel zimmet
- Zimmet detay
- Minibar durumları
- Raporlar
- Doluluk yönetimi
- Satın alma
- Sipariş listesi
- Görev raporları
- Kat sorumlusu siparişleri

### 2.4 Kat Sorumlusu (kat_sorumlusu)

**Minibar dolum ve kontrol yetkisine sahip kullanıcı. Tek bir otele atanır.**

**Yetkiler:**

- Minibar ilk dolum
- Minibar kontrol ve doldurma
- Zimmet kullanımı
- Kendi zimmetini görüntüleme
- QR kod okutma
- Dolum talepleri görüntüleme
- Kişisel raporlar
- Toplu oda doldurma
- Görev yönetimi
- Sipariş hazırlama

**Erişebildiği Sayfalar:**

- Dashboard (kat_sorumlusu/dashboard.html)
- Minibar kontrol
- Minibar işlemleri
- Zimmetim
- Zimmet stoklarım
- QR okuyucu
- Dolum talepleri
- Toplu oda doldurma
- Görev listesi
- Görev yönetimi
- Sipariş hazırlama
- Raporlar
- Günlük doluluk
- Kritik stoklar

---

## 3. VERİTABANI YAPISI VE MODELLER

### 3.1 Ana Tablolar

#### oteller

Otel bilgilerini saklar.

- id, ad, adres, telefon, email, vergi_no, logo
- ilk_stok_yuklendi, ilk_stok_yukleme_tarihi
- email_bildirim_aktif, email_uyari_aktif, email_rapor_aktif
- aktif, olusturma_tarihi

#### kullanicilar

Tüm kullanıcı bilgilerini saklar.

- id, kullanici_adi, sifre_hash, ad, soyad, email, telefon
- rol (sistem_yoneticisi, admin, depo_sorumlusu, kat_sorumlusu)
- otel_id (kat sorumlusu için)
- depo_sorumlusu_id (kat sorumlusunun bağlı olduğu depo sorumlusu)
- aktif, olusturma_tarihi, son_giris

#### kullanici_otel

Depo sorumlusu - otel ilişkisi (Many-to-Many).

- id, kullanici_id, otel_id, olusturma_tarihi

#### katlar

Kat bilgilerini saklar.

- id, otel_id, kat_adi, kat_no, aciklama, aktif

#### odalar

Oda bilgilerini saklar.

- id, kat_id, oda_no, oda_tipi_id, kapasite
- qr_kod_token, qr_kod_gorsel, qr_kod_olusturma_tarihi
- misafir_mesaji, aktif

#### oda_tipleri

Oda tipi tanımları.

- id, ad, dolap_sayisi, aktif
- setuplar (Many-to-Many ilişki)

#### setuplar

Minibar setup şablonları (MINI, MAXI vb.).

- id, ad, aciklama, dolap_ici, aktif

#### setup_icerik

Setup içindeki ürünler.

- id, setup_id, urun_id, adet

#### urun_gruplari

Ürün kategorileri.

- id, grup_adi, aciklama, aktif

#### urunler

Ürün bilgileri.

- id, grup_id, urun_kodu, urun_adi, barkod, birim
- kritik_stok_seviyesi
- satis_fiyati, alis_fiyati, kar_tutari, kar_orani
- aktif

#### stok_hareketleri

Depo stok giriş/çıkış kayıtları.

- id, urun_id, hareket_tipi (giris, cikis, transfer, devir, sayim, fire)
- miktar, aciklama, islem_yapan_id, islem_tarihi

### 3.2 Zimmet Tabloları

#### personel_zimmet

Zimmet başlık bilgileri.

- id, personel_id, zimmet_tarihi, iade_tarihi
- teslim_eden_id, durum (aktif, iade_edildi, iptal)
- aciklama

#### personel_zimmet_detay

Zimmet detay bilgileri.

- id, zimmet_id, urun_id, miktar
- kullanilan_miktar, kalan_miktar, iade_edilen_miktar
- kritik_stok_seviyesi

### 3.3 Minibar Tabloları

#### minibar_islemleri

Minibar işlem başlık bilgileri.

- id, oda_id, personel_id
- islem_tipi (ilk_dolum, yeniden_dolum, eksik_tamamlama, sayim, duzeltme, kontrol, doldurma, ek_dolum, setup_kontrol, ekstra_ekleme, ekstra_tuketim)
- islem_tarihi, aciklama

#### minibar_islem_detay

Minibar işlem detayları.

- id, islem_id, urun_id
- baslangic_stok, bitis_stok, tuketim, eklenen_miktar
- ekstra_miktar, setup_miktari
- zimmet_detay_id
- satis_fiyati, alis_fiyati, kar_tutari, kar_orani
- bedelsiz, kampanya_id

#### minibar_dolum_talepleri

Misafir dolum talepleri.

- id, oda_id, talep_tarihi
- durum (beklemede, onaylandi, reddedildi, tamamlandi, iptal)
- tamamlanma_tarihi, notlar

### 3.4 Doluluk Yönetimi Tabloları

#### misafir_kayitlari

Excel'den yüklenen oda doluluk verileri.

- id, oda_id, islem_kodu
- misafir_sayisi
- giris_tarihi, giris_saati, cikis_tarihi, cikis_saati
- kayit_tipi (in_house, arrival, departure)
- olusturma_tarihi, olusturan_id

#### dosya_yuklemeleri

Excel dosya yükleme kayıtları.

- id, islem_kodu, otel_id
- dosya_adi, dosya_yolu, dosya_tipi, dosya_boyutu
- yukleme_tarihi, silme_tarihi, durum
- toplam_satir, basarili_satir, hatali_satir, hata_detaylari
- yuklenen_kullanici_id

### 3.5 QR Kod Tabloları

#### qr_kod_okutma_loglari

QR kod okutma geçmişi.

- id, oda_id, kullanici_id, okutma_tarihi
- okutma_tipi (misafir_okutma, personel_kontrol, sistem_kontrol)
- ip_adresi, user_agent, basarili, hata_mesaji

### 3.6 ML (Machine Learning) Tabloları

#### ml_metrics

ML metrik kayıtları.

- id, metric_type, entity_id, metric_value, timestamp, extra_data

#### ml_models

Eğitilmiş ML modelleri.

- id, model_type, metric_type, model_data, model_path
- parameters, training_date, accuracy, precision, recall, is_active

#### ml_alerts

ML uyarıları.

- id, alert_type, severity, entity_type, entity_id
- metric_value, expected_value, deviation_percent
- message, suggested_action
- created_at, is_read, is_false_positive
- resolved_at, resolved_by_id

#### ml_features

Feature engineering sonuçları.

- Statistical features (mean, std, min, max, median, q25, q75)
- Trend features (slope, direction, volatility, momentum)
- Time features (hour, day_of_week, is_weekend)
- Lag features (lag_1, lag_7, lag_30)
- Rolling features (rolling_mean_7, rolling_std_7, rolling_mean_30, rolling_std_30)

### 3.7 Fiyatlandırma ve Karlılık Tabloları

#### kampanyalar

Kampanya ve promosyon yönetimi.

- id, kampanya_adi, baslangic_tarihi, bitis_tarihi
- urun_id, indirim_tipi, indirim_degeri
- min_siparis_miktari, max_kullanim_sayisi, kullanilan_sayisi
- aktif, olusturan_id

#### bedelsiz_limitler

Bedelsiz tüketim limitleri.

- id, oda_id, urun_id, max_miktar, kullanilan_miktar
- baslangic_tarihi, bitis_tarihi, limit_tipi, kampanya_id, aktif

#### tedarikciler

Tedarikçi bilgileri.

- id, tedarikci_adi, iletisim_bilgileri, vergi_no, aktif

#### urun_tedarikci_fiyatlari

Ürün bazında tedarikçi fiyatları.

- id, urun_id, tedarikci_id, alis_fiyati
- minimum_miktar, baslangic_tarihi, bitis_tarihi, aktif

### 3.8 Log ve Audit Tabloları

#### sistem_loglari

İşlem logları.

- id, kullanici_id, islem_tipi, modul, islem_detay
- ip_adresi, tarayici, islem_tarihi

#### hata_loglari

Hata logları.

- id, kullanici_id, hata_tipi, hata_mesaji, hata_detay
- modul, url, method, ip_adresi, tarayici
- olusturma_tarihi, cozuldu, cozum_notu

#### audit_logs

Denetim izi kayıtları.

- id, kullanici_id, kullanici_adi, kullanici_rol
- islem_tipi (login, logout, create, update, delete, view, export, import, backup, restore)
- tablo_adi, kayit_id
- eski_deger, yeni_deger, degisiklik_ozeti
- http_method, url, endpoint
- ip_adresi, user_agent, islem_tarihi
- aciklama, basarili, hata_mesaji

---

## 4. İŞ AKIŞLARI VE SÜREÇLER

### 4.1 Stok Yönetimi Akışı

#### Stok Giriş İşlemi

1. Depo sorumlusu "Stok Girişi" sayfasına gider
2. Ürün seçer
3. Hareket tipi seçer (Giriş, Devir, Sayım)
4. Miktar girer
5. Açıklama ekler (opsiyonel)
6. Kaydet butonuna tıklar
7. Sistem stok hareketi kaydı oluşturur
8. Kritik stok kontrolü yapılır
9. Audit log kaydedilir

#### Stok Hesaplama

Mevcut stok = Toplam Giriş - Toplam Çıkış

- Giriş tipleri: giris, devir, sayim (pozitif)
- Çıkış tipleri: cikis, fire, zimmet (negatif)

### 4.2 Zimmet Yönetimi Akışı

#### Zimmet Atama

1. Depo sorumlusu "Personel Zimmet" sayfasına gider
2. Kat sorumlusu seçer
3. Ürünleri ve miktarları belirler
4. Sistem stok kontrolü yapar
5. Yeterli stok varsa zimmet oluşturulur
6. Stoktan çıkış yapılır (hareket_tipi: cikis)
7. Zimmet detayları kaydedilir

#### Zimmet Kullanımı (FIFO Algoritması)

Kat sorumlusu minibar doldururken zimmetten düşüm yapılır:

1. Personelin aktif zimmetleri tarihe göre sıralanır (en eski önce)
2. İhtiyaç duyulan miktar için en eski zimmetten başlanır
3. Kalan miktar yetmezse sonraki zimmete geçilir
4. Her zimmetten düşülen miktar kaydedilir
5. Zimmet tamamen kullanıldıysa durum "tamamlandi" olur

#### Zimmet İade

1. Depo sorumlusu zimmet detayına gider
2. İade edilecek ürün ve miktarı seçer
3. Sistem kalan miktarı kontrol eder
4. İade miktarı depoya giriş olarak kaydedilir
5. Zimmet detayı güncellenir

### 4.3 Minibar İşlemleri Akışı

#### İlk Dolum

1. Kat sorumlusu kat ve oda seçer
2. Sistem odanın setup'ını kontrol eder
3. Setup'a göre ürün listesi gösterilir
4. Her ürün için miktar girilir
5. Zimmet kontrolü yapılır
6. MinibarIslem kaydı oluşturulur (tip: ilk_dolum)
7. Her ürün için MinibarIslemDetay kaydı oluşturulur
8. Zimmetten düşüm yapılır (FIFO)

#### Kontrol ve Doldurma

1. Kat sorumlusu odayı seçer
2. Sistem son minibar durumunu getirir
3. Her ürün için:
   - Mevcut stok gösterilir
   - Gerçek sayım girilir
   - Eklenecek miktar girilir
4. Tüketim hesaplanır (Kayıtlı - Gerçek)
5. Yeni stok hesaplanır (Gerçek + Eklenen)
6. Zimmet kontrolü yapılır
7. MinibarIslem kaydı oluşturulur (tip: doldurma veya kontrol)
8. Zimmetten düşüm yapılır

#### Toplu Oda Doldurma

1. Kat sorumlusu kat seçer
2. Birden fazla oda seçer
3. Tek ürün ve miktar belirler
4. Sistem toplam zimmet kontrolü yapar
5. Her oda için sırayla işlem yapılır
6. Sonuç raporu gösterilir (başarılı/başarısız odalar)

### 4.4 QR Kod Akışı

#### QR Kod Oluşturma (Admin)

1. Admin "QR Yönetimi" sayfasına gider
2. Otel ve kat seçer
3. Odaları seçer
4. "QR Oluştur" butonuna tıklar
5. Sistem her oda için benzersiz token oluşturur
6. QR kod görseli oluşturulur (SVG/PNG)
7. Odalar tablosunda qr_kod_token ve qr_kod_gorsel güncellenir

#### QR Kod Okutma (Kat Sorumlusu)

1. Kat sorumlusu QR okuyucu sayfasına gider
2. Kamera ile QR kodu okutulur
3. Sistem token'ı doğrular
4. Oda bilgileri getirilir
5. Minibar kontrol sayfasına yönlendirilir
6. QR okutma logu kaydedilir

#### QR Kod Okutma (Misafir)

1. Misafir odadaki QR kodu telefonuyla okutulur
2. Sistem token'ı doğrular
3. Dolum talebi formu gösterilir
4. Misafir talep oluşturur
5. Talep "beklemede" durumunda kaydedilir
6. Kat sorumlusuna bildirim gönderilir

### 4.5 Doluluk Yönetimi Akışı

#### Excel Yükleme

1. Depo sorumlusu "Doluluk Yönetimi" sayfasına gider
2. Dosya tipi seçer (In-House, Arrivals, Departures)
3. Excel dosyası yükler
4. Sistem dosyayı parse eder
5. Her satır için:
   - Oda numarası eşleştirilir
   - Tarih bilgileri çıkarılır
   - Misafir sayısı alınır
6. MisafirKayit kayıtları oluşturulur
7. DosyaYukleme kaydı oluşturulur
8. Sonuç raporu gösterilir

#### Doluluk Kontrolü

- Sistem oda doluluk durumunu misafir kayıtlarından hesaplar
- Bugünün tarihi ile giris_tarihi ve cikis_tarihi karşılaştırılır
- Dolu odalar: giris_tarihi <= bugün <= cikis_tarihi
- Boş odalar: Aktif misafir kaydı yok

### 4.6 ML Anomali Tespiti Akışı

#### Veri Toplama

1. Sistem periyodik olarak metrikleri toplar
2. Stok seviyeleri, tüketim miktarları, dolum süreleri kaydedilir
3. MLMetric tablosuna zaman serisi verisi eklenir

#### Model Eğitimi

1. Yeterli veri biriktiğinde model eğitimi tetiklenir
2. Isolation Forest veya Z-Score algoritması kullanılır
3. Model parametreleri ve performans metrikleri kaydedilir
4. Model dosya sistemine kaydedilir (ml_models/ klasörü)

#### Anomali Tespiti

1. Yeni veri geldiğinde model ile tahmin yapılır
2. Anomali tespit edilirse MLAlert kaydı oluşturulur
3. Önem seviyesi belirlenir (dusuk, orta, yuksek, kritik)
4. Önerilen aksiyon eklenir
5. Dashboard'da uyarı gösterilir

---

## 5. API ENDPOİNTLERİ

### 5.1 Authentication API

- `POST /login` - Kullanıcı girişi
- `GET /logout` - Kullanıcı çıkışı
- `GET /setup` - İlk kurulum sayfası
- `POST /setup` - İlk kurulum işlemi

### 5.2 Dashboard API

- `GET /dashboard` - Rol bazlı dashboard yönlendirmesi
- `GET /sistem-yoneticisi/dashboard` - Sistem yöneticisi dashboard
- `GET /admin/dashboard` - Admin dashboard
- `GET /depo-sorumlusu/dashboard` - Depo sorumlusu dashboard
- `GET /kat-sorumlusu/dashboard` - Kat sorumlusu dashboard

### 5.3 Stok API

- `GET /api/stok-durum` - Stok durumu
- `POST /api/stok-giris` - Stok girişi
- `GET /api/urun-stok/<urun_id>` - Ürün stok bilgisi
- `GET /stoklarim` - Depo stokları listesi

### 5.4 Zimmet API

- `GET /personel-zimmet` - Zimmet listesi
- `POST /personel-zimmet` - Yeni zimmet oluştur
- `GET /zimmet-detay/<zimmet_id>` - Zimmet detayı
- `POST /zimmet-iade/<detay_id>` - Zimmet iade
- `POST /zimmet-iptal/<zimmet_id>` - Zimmet iptal
- `GET /api/zimmetim` - Kat sorumlusu zimmet bilgisi

### 5.5 Minibar API

- `GET /api/minibar-icerigi/<oda_id>` - Oda minibar içeriği
- `POST /api/minibar-islem-kaydet` - Minibar işlem kaydet
- `POST /api/minibar-ilk-dolum` - İlk dolum işlemi
- `GET /api/minibar-ilk-dolum-kontrol/<oda_id>` - İlk dolum kontrolü
- `POST /api/minibar-doldur` - Minibar doldurma
- `POST /api/toplu-oda-doldur` - Toplu oda doldurma
- `GET /api/toplu-oda-mevcut-durum` - Toplu oda mevcut durum

### 5.6 Oda ve Kat API

- `GET /api/odalar` - Tüm odalar
- `GET /api/odalar-by-kat/<kat_id>` - Kata göre odalar
- `GET /api/katlar` - Tüm katlar

### 5.7 Ürün API

- `GET /api/urunler` - Tüm ürünler
- `GET /api/urunler-by-grup/<grup_id>` - Gruba göre ürünler
- `GET /api/urun-gruplari` - Ürün grupları

### 5.8 QR Kod API

- `GET /qr/<token>` - QR kod ile oda erişimi
- `POST /api/qr-okutma-log` - QR okutma logu
- `GET /admin/qr-yonetimi` - QR yönetimi sayfası
- `POST /admin/qr-olustur` - QR kod oluştur

### 5.9 Doluluk API

- `GET /doluluk-yonetimi` - Doluluk yönetimi sayfası
- `POST /doluluk-yukle` - Excel yükleme
- `GET /api/doluluk-durum` - Doluluk durumu
- `DELETE /doluluk-sil/<islem_kodu>` - Doluluk kaydı silme

### 5.10 Rapor API

- `GET /depo-raporlar` - Depo raporları
- `GET /api/kat-rapor-veri` - Kat bazlı rapor verisi
- `GET /rapor/stok-durum` - Stok durum raporu
- `GET /rapor/zimmet` - Zimmet raporu
- `GET /rapor/minibar-tuketim` - Minibar tüketim raporu

### 5.11 ML API

- `GET /admin/ml-dashboard` - ML Dashboard
- `GET /api/ml/alerts` - ML uyarıları
- `POST /api/ml/train` - Model eğitimi tetikle
- `GET /api/ml/metrics` - ML metrikleri
- `POST /api/ml/alert/<alert_id>/resolve` - Uyarı çözümle

### 5.12 Health API

- `GET /health` - Sistem sağlık kontrolü
- `GET /api/health/db` - Veritabanı sağlık kontrolü

---

## 6. SAYFA VE TEMPLATE YAPISI

### 6.1 Ana Şablonlar

- `base.html` - Tüm sayfaların temel şablonu
- `login.html` - Giriş sayfası
- `setup.html` - İlk kurulum sayfası
- `reset_system.html` - Sistem sıfırlama sayfası

### 6.2 Admin Şablonları (templates/admin/)

- `dashboard.html` - Admin ana sayfa
- `urunler.html` - Ürün listesi ve yönetimi
- `urun_gruplari.html` - Ürün grupları yönetimi
- `urun_duzenle.html` - Ürün düzenleme
- `grup_duzenle.html` - Grup düzenleme
- `personel_tanimla.html` - Personel tanımlama
- `personel_duzenle.html` - Personel düzenleme
- `kampanya_yonetimi.html` - Kampanya yönetimi
- `bedelsiz_limit_yonetimi.html` - Bedelsiz limit yönetimi
- `ml_dashboard.html` - ML Dashboard
- `karlilik_dashboard.html` - Karlılık analizi
- `urun_fiyat_yonetimi.html` - Fiyat yönetimi
- `db_optimization_dashboard.html` - DB optimizasyon

### 6.3 Sistem Yöneticisi Şablonları (templates/sistem_yoneticisi/)

- `dashboard.html` - Sistem yöneticisi ana sayfa
- `otel_tanimla.html` - Otel tanımlama
- `kat_tanimla.html` - Kat tanımlama
- `kat_duzenle.html` - Kat düzenleme
- `oda_tanimla.html` - Oda tanımlama
- `oda_duzenle.html` - Oda düzenleme
- `admin_ata.html` - Admin atama
- `admin_duzenle.html` - Admin düzenleme
- `setup_yonetimi.html` - Setup (minibar şablonu) yönetimi
- `tedarikci_yonetimi.html` - Tedarikçi yönetimi
- `tedarikci_duzenle.html` - Tedarikçi düzenleme
- `fiyat_yonetimi.html` - Fiyat yönetimi
- `fiyat_karsilastirma.html` - Fiyat karşılaştırma
- `sistem_loglari.html` - Sistem logları
- `audit_trail.html` - Denetim izi
- `sistem_ayarlari.html` - Sistem ayarları
- `depo_stoklari.html` - Depo stokları
- `oda_minibar_stoklari.html` - Oda minibar stokları
- `dolum_talepleri.html` - Dolum talepleri

### 6.4 Depo Sorumlusu Şablonları (templates/depo_sorumlusu/)

- `dashboard.html` - Depo sorumlusu ana sayfa
- `stok_giris.html` - Stok giriş formu
- `stoklarim.html` - Stok listesi
- `personel_zimmet.html` - Zimmet yönetimi
- `zimmet_detay.html` - Zimmet detayı
- `minibar_durumlari.html` - Minibar durumları
- `raporlar.html` - Raporlar
- `doluluk_yonetimi.html` - Doluluk yönetimi (Excel yükleme)
- `satin_alma.html` - Satın alma
- `satin_alma_listesi.html` - Satın alma listesi
- `satin_alma_detay.html` - Satın alma detayı
- `siparis_listesi.html` - Sipariş listesi
- `kat_sorumlusu_siparisler.html` - Kat sorumlusu siparişleri
- `gorev_raporlari.html` - Görev raporları
- `yukleme_gorevleri.html` - Yükleme görevleri

### 6.5 Kat Sorumlusu Şablonları (templates/kat_sorumlusu/)

- `dashboard.html` - Kat sorumlusu ana sayfa
- `minibar_kontrol.html` - Minibar kontrol ve doldurma
- `minibar_islemleri.html` - Minibar işlemleri geçmişi
- `zimmetim.html` - Kendi zimmetleri
- `zimmet_stoklarim.html` - Zimmet stok durumu
- `qr_okuyucu.html` - QR kod okuyucu
- `dolum_talepleri.html` - Dolum talepleri
- `toplu_oda_doldurma.html` - Toplu oda doldurma
- `gorev_listesi.html` - Görev listesi
- `gorev_yonetimi.html` - Görev yönetimi
- `siparis_hazirla.html` - Sipariş hazırlama
- `siparis_listesi.html` - Sipariş listesi
- `raporlar.html` - Kişisel raporlar
- `gunluk_doluluk.html` - Günlük doluluk
- `kritik_stoklar.html` - Kritik stok uyarıları
- `oda_kontrol.html` - Oda kontrol

### 6.6 Rapor Şablonları (templates/raporlar/)

- `stok_raporlari.html` - Stok raporları
- `zimmet_raporlari.html` - Zimmet raporları
- `minibar_raporlari.html` - Minibar raporları
- `doluluk_raporlari.html` - Doluluk raporları
- `performans_raporlari.html` - Performans raporları
- `kat_bazli_rapor.html` - Kat bazlı rapor

### 6.7 Hata Şablonları (templates/errors/)

- `404.html` - Sayfa bulunamadı
- `429.html` - Çok fazla istek
- `500.html` - Sunucu hatası

---

## 7. YARDIMCI MODÜLLER (utils/)

### 7.1 Temel Yardımcılar

- `helpers.py` - Genel yardımcı fonksiyonlar

  - get_current_user() - Mevcut kullanıcıyı al
  - get_kritik_stok_urunler() - Kritik stok ürünlerini al
  - get_stok_toplamlari() - Stok toplamlarını hesapla
  - log_islem() - İşlem logla
  - log_hata() - Hata logla
  - get_stok_durumu() - Stok durumunu al

- `decorators.py` - Özel dekoratörler

  - @login_required - Giriş zorunluluğu
  - @role_required(rol) - Rol kontrolü
  - @setup_required - Setup kontrolü
  - @setup_not_completed - Setup tamamlanmamış kontrolü

- `audit.py` - Denetim izi fonksiyonları

  - audit_create() - Oluşturma kaydı
  - audit_update() - Güncelleme kaydı
  - audit_delete() - Silme kaydı
  - audit_login() - Giriş kaydı
  - audit_logout() - Çıkış kaydı
  - serialize_model() - Model serileştirme

- `authorization.py` - Yetkilendirme yardımcıları
  - get_kat_sorumlusu_otel() - Kat sorumlusunun oteli
  - get_depo_sorumlusu_oteller() - Depo sorumlusunun otelleri

### 7.2 Servis Modülleri

- `minibar_servisleri.py` - Minibar işlem servisleri
- `gorev_service.py` - Görev yönetimi servisi
- `gorev_oncelik_service.py` - Görev öncelik servisi
- `occupancy_service.py` - Doluluk servisi
- `qr_service.py` - QR kod servisi
- `backup_service.py` - Yedekleme servisi
- `email_service.py` - E-posta servisi
- `bildirim_service.py` - Bildirim servisi
- `excel_service.py` - Excel işlemleri servisi
- `fiyatlandirma_servisler.py` - Fiyatlandırma servisleri
- `satin_alma_servisleri.py` - Satın alma servisleri
- `tedarikci_servisleri.py` - Tedarikçi servisleri
- `yukleme_gorev_service.py` - Yükleme görev servisi

### 7.3 ML Modülleri (utils/ml/)

- `anomaly_detector.py` - Anomali tespit algoritmaları
- `data_collector.py` - Veri toplama
- `feature_engineer.py` - Feature engineering
- `model_manager.py` - Model yönetimi
- `model_trainer.py` - Model eğitimi
- `alert_manager.py` - Uyarı yönetimi
- `metrics_calculator.py` - Metrik hesaplama
- `report_generator.py` - Rapor oluşturma

### 7.4 Monitoring Modülleri (utils/monitoring/)

- `query_analyzer.py` - Sorgu analizi
- `api_metrics.py` - API metrikleri
- `backup_manager.py` - Yedekleme yönetimi
- `job_monitor.py` - İş izleme
- `log_viewer.py` - Log görüntüleme
- `ml_metrics.py` - ML metrikleri
- `profiler.py` - Performans profilleme

---

## 8. GÜVENLİK ÖZELLİKLERİ

### 8.1 Kimlik Doğrulama

- Session tabanlı authentication
- Şifre hashleme (Werkzeug Security)
- Güçlü şifre politikası (min 8 karakter, büyük/küçük harf, rakam, özel karakter)
- Oturum zaman aşımı

### 8.2 Yetkilendirme

- Rol bazlı erişim kontrolü (RBAC)
- @role_required dekoratörü ile endpoint koruması
- Otel bazlı veri izolasyonu

### 8.3 CSRF Koruması

- Flask-WTF CSRFProtect
- Tüm POST/PUT/DELETE isteklerinde CSRF token kontrolü

### 8.4 Rate Limiting

- Flask-Limiter ile istek sınırlama
- Login endpoint: 5 istek/dakika
- Genel: 200 istek/gün

### 8.5 Input Validasyonu

- WTForms ile form validasyonu
- SQLAlchemy ORM ile SQL injection koruması
- XSS koruması

### 8.6 Güvenlik Başlıkları

- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Content-Security-Policy
- Strict-Transport-Security (HTTPS)

### 8.7 Audit Trail

- Tüm CRUD işlemleri loglanır
- Login/logout kayıtları
- IP adresi ve user agent tracking
- Değişiklik geçmişi (eski/yeni değer)

---

## 9. RAPORLAMA SİSTEMİ

### 9.1 Stok Raporları

- Stok Durum Raporu: Mevcut stok durumu, kritik ürünler
- Stok Hareket Raporu: Giriş/çıkış hareketleri
- Kritik Stok Raporu: Kritik seviyenin altındaki ürünler

### 9.2 Zimmet Raporları

- Zimmet Özet Raporu: Personel bazlı zimmet durumu
- Zimmet Detay Raporu: Ürün bazlı zimmet bilgisi
- Zimmet Kullanım Raporu: Kullanım oranları

### 9.3 Minibar Raporları

- Minibar Tüketim Raporu: Oda bazlı tüketim
- Kat Bazlı Rapor: Kat bazlı tüketim analizi
- Ürün Bazlı Rapor: Ürün bazlı tüketim

### 9.4 Doluluk Raporları

- Günlük Doluluk: Günlük oda doluluk durumu
- Dönemsel Doluluk: Tarih aralığı bazlı doluluk

### 9.5 Performans Raporları

- Personel Performans: Kat sorumlusu performansı
- Görev Tamamlama: Görev tamamlama oranları

### 9.6 Export Formatları

- Excel (OpenPyXL)
- PDF (ReportLab)
- JSON (API)

---

## 10. ML SİSTEMİ

### 10.1 Metrik Tipleri

- **stok_seviye**: Ürün stok seviyeleri
- **tuketim_miktar**: Tüketim miktarları
- **dolum_sure**: Dolum süreleri
- **stok_bitis_tahmini**: Stok bitiş tahminleri
- **zimmet_kullanim**: Zimmet kullanım oranları
- **zimmet_fire**: Fire/kayıp oranları
- **doluluk_oran**: Otel doluluk oranları
- **bosta_tuketim**: Boş odada tüketim
- **talep_yanit_sure**: Talep yanıt süreleri
- **qr_okutma_siklik**: QR okutma sıklığı

### 10.2 Uyarı Tipleri

- **stok_anomali**: Stok seviye anomalisi
- **tuketim_anomali**: Tüketim pattern anomalisi
- **dolum_gecikme**: Dolum gecikmesi
- **stok_bitis_uyari**: Stok bitiş uyarısı
- **zimmet_fire_yuksek**: Yüksek fire oranı
- **bosta_tuketim_var**: Boş odada tüketim
- **doluda_tuketim_yok**: Dolu odada tüketim yok
- **talep_yanitlanmadi**: Yanıtlanmayan talep
- **qr_kullanim_dusuk**: Düşük QR kullanımı

### 10.3 Önem Seviyeleri

- **dusuk**: Bilgilendirme amaçlı
- **orta**: Dikkat gerektiren
- **yuksek**: Acil müdahale gerektiren
- **kritik**: Kritik durum

### 10.4 Algoritmalar

- **Isolation Forest**: Anomali tespiti için
- **Z-Score**: İstatistiksel anomali tespiti
- **Feature Engineering**: Özellik çıkarımı

### 10.5 Model Yönetimi

- Modeller dosya sisteminde saklanır (ml_models/ klasörü)
- Otomatik versiyonlama
- Periyodik cleanup (son 3 versiyon saklanır)
- Fallback mekanizması (model yoksa Z-Score kullanılır)

---

## 11. SETUP (MİNİBAR ŞABLONU) SİSTEMİ

### 11.1 Setup Nedir?

Setup, bir oda tipine atanacak minibar içeriğini tanımlayan şablondur. Örneğin:

- **MINI Setup**: Küçük minibar (5 ürün)
- **MAXI Setup**: Büyük minibar (15 ürün)
- **VIP Setup**: VIP oda minibarı (20 ürün)

### 11.2 Setup Yapısı

- Her setup'ın bir adı ve açıklaması vardır
- Setup içeriği: Ürün + Adet listesi
- Dolap içi/dışı ayrımı yapılabilir
- Bir oda tipine birden fazla setup atanabilir (Many-to-Many)

### 11.3 Setup Kullanımı

1. Sistem yöneticisi setup tanımlar
2. Setup'a ürünler ve adetler eklenir
3. Oda tiplerine setup atanır
4. Kat sorumlusu ilk dolum yaparken setup'a göre ürün listesi gelir
5. Kontrol sırasında setup miktarları referans alınır

---

## 12. SATIN ALMA VE TEDARİKÇİ SİSTEMİ

### 12.1 Tedarikçi Yönetimi

- Tedarikçi tanımlama (ad, iletişim, vergi no)
- Tedarikçi bazlı ürün fiyatları
- Tedarikçi performans takibi

### 12.2 Satın Alma Süreci

1. Kritik stok uyarısı oluşur
2. Depo sorumlusu sipariş oluşturur
3. Tedarikçi seçilir
4. Ürünler ve miktarlar belirlenir
5. Sipariş onaylanır
6. Teslim alındığında stok girişi yapılır

### 12.3 Sipariş Durumları

- **beklemede**: Sipariş oluşturuldu
- **onaylandi**: Sipariş onaylandı
- **teslim_alindi**: Ürünler teslim alındı
- **kismi_teslim**: Kısmi teslim yapıldı
- **tamamlandi**: Sipariş tamamlandı
- **iptal**: Sipariş iptal edildi

---

## 13. KAMPANYA VE BEDELSİZ SİSTEMİ

### 13.1 Kampanya Yönetimi

- Kampanya tanımlama (ad, tarih aralığı)
- İndirim tipi: Yüzde veya Tutar
- Ürün bazlı veya genel kampanya
- Kullanım limiti belirleme

### 13.2 Bedelsiz Limit Sistemi

- Oda bazlı bedelsiz tüketim limiti
- Ürün bazlı limit belirleme
- Kampanya ile entegrasyon
- Kullanım takibi

### 13.3 Bedelsiz Kullanım Akışı

1. Misafir check-in yapar
2. Oda için bedelsiz limit tanımlanır
3. Minibar kontrolünde tüketim tespit edilir
4. Bedelsiz limit kontrolü yapılır
5. Limit dahilindeyse bedelsiz olarak işaretlenir
6. Limit aşıldıysa ücretli olarak kaydedilir

---

## 14. GÖREV YÖNETİMİ SİSTEMİ

### 14.1 Görev Tipleri

- Minibar dolum görevi
- Kontrol görevi
- Yükleme görevi
- Sipariş hazırlama görevi

### 14.2 Görev Önceliklendirme

- Arrivals (yeni gelen misafirler) - Yüksek öncelik
- In-House (mevcut misafirler) - Normal öncelik
- Departures (çıkış yapacaklar) - Düşük öncelik

### 14.3 Görev Akışı

1. Sistem otomatik görev oluşturur (doluluk verilerine göre)
2. Kat sorumlusu görev listesini görür
3. Görev önceliğe göre sıralanır
4. Kat sorumlusu görevi tamamlar
5. Görev durumu güncellenir

---

## 15. DEPLOYMENT VE KONFIGÜRASYON

### 15.1 Environment Variables

```
# Database
DATABASE_URL=postgresql://user:pass@host:port/db
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=password
DB_NAME=minibar_takip
DB_PORT=5432

# Flask
SECRET_KEY=your-secret-key-min-32-chars
FLASK_ENV=production

# Redis (Celery)
REDIS_URL=redis://localhost:6379/0

# Sentry (Opsiyonel)
SENTRY_DSN=https://xxx@sentry.io/xxx
```

### 15.2 Coolify Deployment

- Docker container olarak deploy edilir
- PostgreSQL veritabanı
- Redis (Celery broker)
- Persistent volume (ml_models, uploads)
- Health check endpoint (/health)

### 15.3 Dosya Yapısı

```
/app/
├── app.py              # Ana uygulama
├── models.py           # Veritabanı modelleri
├── forms.py            # Form tanımları
├── config.py           # Konfigürasyon
├── celery_app.py       # Celery konfigürasyonu
├── routes/             # Route modülleri
├── templates/          # HTML şablonları
├── static/             # Statik dosyalar
├── utils/              # Yardımcı modüller
├── ml_models/          # ML model dosyaları
├── uploads/            # Yüklenen dosyalar
├── migrations/         # Veritabanı migration'ları
└── tests/              # Test dosyaları
```

---

## 16. SIKÇA SORULAN SORULAR (SSS)

### 16.1 Stok Yönetimi

**S: Stok nasıl hesaplanır?**
C: Mevcut stok = Toplam Giriş - Toplam Çıkış. Giriş tipleri (giris, devir, sayim) pozitif, çıkış tipleri (cikis, fire, zimmet) negatif olarak hesaplanır.

**S: Kritik stok uyarısı ne zaman oluşur?**
C: Mevcut stok, ürünün kritik_stok_seviyesi değerinin altına düştüğünde uyarı oluşur.

**S: Negatif stok olabilir mi?**
C: Hayır, sistem negatif stok oluşmasını engeller. Yetersiz stok durumunda işlem reddedilir.

### 16.2 Zimmet Yönetimi

**S: FIFO algoritması nasıl çalışır?**
C: Kat sorumlusu minibar doldururken, en eski tarihli zimmetten başlayarak düşüm yapılır. Bir zimmet tamamen kullanıldığında sonraki zimmete geçilir.

**S: Zimmet iade nasıl yapılır?**
C: Depo sorumlusu zimmet detayından iade miktarını girer. İade edilen miktar depoya giriş olarak kaydedilir.

**S: Zimmet iptal edilirse ne olur?**
C: Kullanılmayan tüm ürünler depoya iade edilir ve zimmet durumu "iptal" olarak güncellenir.

### 16.3 Minibar İşlemleri

**S: İlk dolum nedir?**
C: Bir odaya ilk kez minibar ürünleri yerleştirilmesidir. Her oda için sadece bir kez yapılır.

**S: Kontrol ve doldurma arasındaki fark nedir?**
C: Kontrol sadece mevcut durumu görüntüler. Doldurma ise eksik ürünleri tamamlar ve zimmetten düşüm yapar.

**S: Tüketim nasıl hesaplanır?**
C: Tüketim = Kayıtlı Stok - Gerçek Sayım. Pozitif değer tüketimi, negatif değer fazlalığı gösterir.

### 16.4 QR Kod Sistemi

**S: QR kod nasıl oluşturulur?**
C: Admin QR yönetimi sayfasından odaları seçerek toplu QR kod oluşturabilir.

**S: Misafir QR kodu okutunca ne olur?**
C: Misafir dolum talebi formu açılır. Talep oluşturulduğunda kat sorumlusuna bildirim gider.

### 16.5 Doluluk Yönetimi

**S: Hangi Excel formatları desteklenir?**
C: In-House, Arrivals ve Departures formatları desteklenir. Dosyalar .xlsx veya .xls formatında olmalıdır.

**S: Doluluk verileri nasıl güncellenir?**
C: Yeni Excel yüklendiğinde mevcut veriler güncellenir. Aynı işlem kodu ile yüklenen veriler üzerine yazılır.

### 16.6 ML Sistemi

**S: Anomali tespiti nasıl çalışır?**
C: Sistem geçmiş verileri analiz ederek normal pattern'ları öğrenir. Yeni veriler bu pattern'lardan sapma gösterdiğinde anomali uyarısı oluşturur.

**S: ML modelleri ne sıklıkla eğitilir?**
C: Modeller yeterli veri biriktiğinde (varsayılan 100 veri noktası) otomatik olarak yeniden eğitilir.

---

## 17. HATA KODLARI VE ÇÖZÜMLER

### 17.1 Veritabanı Hataları

- **OperationalError**: Veritabanı bağlantı hatası. Bağlantı ayarlarını kontrol edin.
- **IntegrityError**: Veri bütünlüğü hatası. Unique constraint veya foreign key ihlali.
- **TimeoutError**: Sorgu zaman aşımı. Sorguyu optimize edin.

### 17.2 Yetkilendirme Hataları

- **401 Unauthorized**: Giriş yapılmamış. Login sayfasına yönlendirilir.
- **403 Forbidden**: Yetkisiz erişim. Kullanıcının rolü yetersiz.

### 17.3 Validasyon Hataları

- **400 Bad Request**: Geçersiz form verisi. Form alanlarını kontrol edin.
- **CSRF Token Missing**: CSRF token eksik. Sayfayı yenileyin.

### 17.4 Rate Limiting

- **429 Too Many Requests**: Çok fazla istek. Bir süre bekleyin.

---

## 18. PERFORMANS OPTİMİZASYONLARI

### 18.1 Veritabanı

- Connection pooling (pool_size=1, max_overflow=2)
- Index'ler (oda_id, tarih, kullanici_id)
- Eager loading ile N+1 sorgu önleme
- Batch işlemler için bulk insert/update

### 18.2 Caching

- Stok toplamları tek sorguda hesaplama
- Session tabanlı kullanıcı cache
- Static dosya caching

### 18.3 Frontend

- Tailwind CSS (minimal CSS)
- Chart.js lazy loading
- AJAX ile partial updates
- Debounced search inputs

---

## 19. SONUÇ

Bu belge, Otel Minibar Takip Sistemi'nin tüm özelliklerini, iş akışlarını ve teknik detaylarını kapsamaktadır. AI asistanın RAG eğitimi için kullanılacak bu belge, sistemin:

- 4 farklı kullanıcı rolü ve yetkileri
- 30+ veritabanı tablosu ve ilişkileri
- 100+ API endpoint
- Stok, zimmet, minibar, QR kod, doluluk yönetimi iş akışları
- ML tabanlı anomali tespiti
- Güvenlik özellikleri
- Raporlama sistemi

hakkında kapsamlı bilgi içermektedir.

---

**Belge Sonu**
**Versiyon:** 2.0
**Son Güncelleme:** 5 Aralık 2025
