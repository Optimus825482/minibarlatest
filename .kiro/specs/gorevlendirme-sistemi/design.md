# Design Document - Görevlendirme Sistemi

## Overview

Bu doküman, Minibar Takip Sistemi için günlük görevlendirme sisteminin teknik tasarımını tanımlar. Sistem, günlük doluluk verileri (In House ve Arrivals) yüklendikten sonra kat sorumluları için otomatik minibar kontrol görevleri oluşturur. Depo sorumluları için günlük yükleme görevleri takip edilir ve tüm roller için dashboard entegrasyonu sağlanır.

## Architecture

### Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────────────┐
│                    Görevlendirme Sistemi                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Routes    │  │  Services   │  │        Models           │  │
│  │             │  │             │  │                         │  │
│  │ gorev_      │  │ GorevService│  │ GunlukGorev             │  │
│  │ routes.py   │──│             │──│ GorevDetay              │  │
│  │             │  │ DNDService  │  │ DNDKontrol              │  │
│  │             │  │             │  │ YuklemeGorev            │  │
│  │             │  │ Bildirim    │  │ GorevDurumLog           │  │
│  │             │  │ Service     │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Dashboard Entegrasyonu                   ││
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐││
│  │  │Kat Sorumlusu │ │Depo Sorumlusu│ │ Sistem Yöneticisi    │││
│  │  │  Dashboard   │ │  Dashboard   │ │    Dashboard         │││
│  │  └──────────────┘ └──────────────┘ └──────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Veri Akışı

```
Excel Yükleme (Depo Sorumlusu)
        │
        ▼
┌───────────────────┐
│ ExcelProcessing   │
│ Service           │
└───────────────────┘
        │
        ▼
┌───────────────────┐     ┌───────────────────┐
│ MisafirKayit      │────▶│ GorevService      │
│ (In House/Arrival)│     │ .create_tasks()   │
└───────────────────┘     └───────────────────┘
                                  │
                                  ▼
                          ┌───────────────────┐
                          │ GunlukGorev       │
                          │ GorevDetay        │
                          └───────────────────┘
                                  │
                                  ▼
                          ┌───────────────────┐
                          │ BildirimService   │
                          │ .send_notification│
                          └───────────────────┘
```

## Components and Interfaces

### 1. Models (models.py)

#### GunlukGorev Model

```python
class GorevTipi(str, enum.Enum):
    INHOUSE_KONTROL = 'inhouse_kontrol'
    ARRIVAL_KONTROL = 'arrival_kontrol'
    INHOUSE_YUKLEME = 'inhouse_yukleme'
    ARRIVALS_YUKLEME = 'arrivals_yukleme'

class GorevDurum(str, enum.Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    DND_PENDING = 'dnd_pending'
    INCOMPLETE = 'incomplete'

class GunlukGorev(db.Model):
    __tablename__ = 'gunluk_gorevler'

    id: int (PK)
    otel_id: int (FK -> oteller.id)
    personel_id: int (FK -> kullanicilar.id)
    gorev_tarihi: date
    gorev_tipi: GorevTipi
    durum: GorevDurum
    olusturma_tarihi: datetime
    tamamlanma_tarihi: datetime (nullable)
    notlar: text (nullable)
```

#### GorevDetay Model

```python
class GorevDetay(db.Model):
    __tablename__ = 'gorev_detaylari'

    id: int (PK)
    gorev_id: int (FK -> gunluk_gorevler.id)
    oda_id: int (FK -> odalar.id)
    misafir_kayit_id: int (FK -> misafir_kayitlari.id)
    durum: GorevDurum
    varis_saati: time (nullable, Arrivals için)
    kontrol_zamani: datetime (nullable)
    dnd_sayisi: int (default 0)
    son_dnd_zamani: datetime (nullable)
    notlar: text (nullable)
```

#### DNDKontrol Model

```python
class DNDKontrol(db.Model):
    __tablename__ = 'dnd_kontroller'

    id: int (PK)
    gorev_detay_id: int (FK -> gorev_detaylari.id)
    kontrol_zamani: datetime
    kontrol_eden_id: int (FK -> kullanicilar.id)
    notlar: text (nullable)
```

#### YuklemeGorev Model

```python
class YuklemeGorev(db.Model):
    __tablename__ = 'yukleme_gorevleri'

    id: int (PK)
    otel_id: int (FK -> oteller.id)
    depo_sorumlusu_id: int (FK -> kullanicilar.id)
    gorev_tarihi: date
    dosya_tipi: str ('inhouse' veya 'arrivals')
    durum: GorevDurum
    yukleme_zamani: datetime (nullable)
    dosya_yukleme_id: int (FK -> dosya_yuklemeleri.id, nullable)
```

#### GorevDurumLog Model

```python
class GorevDurumLog(db.Model):
    __tablename__ = 'gorev_durum_loglari'

    id: int (PK)
    gorev_detay_id: int (FK -> gorev_detaylari.id)
    onceki_durum: GorevDurum
    yeni_durum: GorevDurum
    degisiklik_zamani: datetime
    degistiren_id: int (FK -> kullanicilar.id)
    aciklama: text (nullable)
```

### 2. Services (utils/)

#### GorevService (utils/gorev_service.py)

```python
class GorevService:
    @staticmethod
    def create_daily_tasks(otel_id: int, tarih: date) -> dict:
        """Günlük görevleri oluşturur"""

    @staticmethod
    def create_inhouse_tasks(otel_id: int, personel_id: int, tarih: date) -> list:
        """In House kontrol görevlerini oluşturur"""

    @staticmethod
    def create_arrival_tasks(otel_id: int, personel_id: int, tarih: date) -> list:
        """Arrivals kontrol görevlerini oluşturur"""

    @staticmethod
    def complete_task(gorev_detay_id: int, personel_id: int, notlar: str = None) -> bool:
        """Görevi tamamlar"""

    @staticmethod
    def mark_dnd(gorev_detay_id: int, personel_id: int, notlar: str = None) -> dict:
        """Odayı DND olarak işaretler"""

    @staticmethod
    def get_pending_tasks(personel_id: int, tarih: date) -> list:
        """Bekleyen görevleri getirir"""

    @staticmethod
    def get_completed_tasks(personel_id: int, tarih: date) -> list:
        """Tamamlanan görevleri getirir"""

    @staticmethod
    def get_dnd_tasks(personel_id: int, tarih: date) -> list:
        """DND durumundaki görevleri getirir"""

    @staticmethod
    def calculate_countdown(varis_saati: time) -> dict:
        """Varış saatine kalan süreyi hesaplar"""
```

#### YuklemeGorevService (utils/yukleme_gorev_service.py)

```python
class YuklemeGorevService:
    @staticmethod
    def create_daily_upload_tasks(tarih: date) -> list:
        """Tüm depo sorumluları için günlük yükleme görevleri oluşturur"""

    @staticmethod
    def complete_upload_task(otel_id: int, dosya_tipi: str, dosya_yukleme_id: int) -> bool:
        """Yükleme görevini tamamlar"""

    @staticmethod
    def get_pending_uploads(depo_sorumlusu_id: int, tarih: date) -> list:
        """Bekleyen yükleme görevlerini getirir"""

    @staticmethod
    def get_upload_status(otel_id: int, tarih: date) -> dict:
        """Yükleme durumunu getirir"""

    @staticmethod
    def get_missing_uploads(baslangic: date, bitis: date) -> list:
        """Eksik yükleme günlerini getirir"""

    @staticmethod
    def get_upload_statistics(otel_id: int, donem: str) -> dict:
        """Yükleme istatistiklerini getirir (haftalık/aylık)"""
```

#### BildirimService (utils/bildirim_service.py)

```python
class BildirimService:
    @staticmethod
    def send_task_notification(personel_id: int, mesaj: str, tip: str) -> bool:
        """Görev bildirimi gönderir"""

    @staticmethod
    def send_dnd_incomplete_notification(gorev_detay_ids: list) -> bool:
        """Tamamlanmayan DND bildirimi gönderir"""

    @staticmethod
    def send_upload_warning(depo_sorumlusu_id: int, dosya_tipi: str) -> bool:
        """Yükleme uyarısı gönderir"""

    @staticmethod
    def get_notifications(personel_id: int) -> list:
        """Bildirimleri getirir"""
```

### 3. Routes (routes/gorev_routes.py)

```python
# Kat Sorumlusu Routes
GET  /gorevler                      # Günlük görev listesi
GET  /gorevler/inhouse              # In House görevleri
GET  /gorevler/arrivals             # Arrivals görevleri
GET  /gorevler/dnd                  # DND odaları listesi
POST /gorevler/<id>/tamamla         # Görevi tamamla
POST /gorevler/<id>/dnd             # DND olarak işaretle
GET  /gorevler/raporlar             # Görev raporları

# Depo Sorumlusu Routes
GET  /depo/gorevler                 # Yükleme görevleri
GET  /depo/personel-gorevler        # Personel görev durumları
GET  /depo/gorev-raporlari          # Görev raporları

# Sistem Yöneticisi Routes
GET  /sistem/gorev-ozeti            # Otel geneli görev özeti
GET  /sistem/yukleme-takip          # Yükleme takip raporu
GET  /sistem/dnd-bildirimleri       # DND bildirimleri

# API Routes
GET  /api/gorevler/bekleyen         # Bekleyen görev sayısı
GET  /api/gorevler/countdown/<id>   # Geri sayım bilgisi
POST /api/gorevler/bildirim-oku     # Bildirimi okundu işaretle
```

## Data Models

### Entity Relationship Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Kullanici     │     │   GunlukGorev   │     │   GorevDetay    │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │◄────│ personel_id(FK) │     │ id (PK)         │
│ rol             │     │ id (PK)         │◄────│ gorev_id (FK)   │
│ otel_id (FK)    │     │ otel_id (FK)    │     │ oda_id (FK)     │
│ depo_sorumlusu  │     │ gorev_tarihi    │     │ misafir_kayit_id│
│ _id (FK)        │     │ gorev_tipi      │     │ durum           │
└─────────────────┘     │ durum           │     │ varis_saati     │
        │               │ olusturma_tarihi│     │ kontrol_zamani  │
        │               │ tamamlanma_     │     │ dnd_sayisi      │
        │               │ tarihi          │     │ son_dnd_zamani  │
        │               └─────────────────┘     └─────────────────┘
        │                                               │
        │               ┌─────────────────┐             │
        │               │   DNDKontrol    │             │
        │               ├─────────────────┤             │
        │               │ id (PK)         │             │
        └──────────────►│ gorev_detay_id  │◄────────────┘
                        │ (FK)            │
                        │ kontrol_zamani  │
                        │ kontrol_eden_id │
                        │ (FK)            │
                        │ notlar          │
                        └─────────────────┘

┌─────────────────┐     ┌─────────────────┐
│  YuklemeGorev   │     │ GorevDurumLog   │
├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │
│ otel_id (FK)    │     │ gorev_detay_id  │
│ depo_sorumlusu  │     │ (FK)            │
│ _id (FK)        │     │ onceki_durum    │
│ gorev_tarihi    │     │ yeni_durum      │
│ dosya_tipi      │     │ degisiklik_     │
│ durum           │     │ zamani          │
│ yukleme_zamani  │     │ degistiren_id   │
│ dosya_yukleme   │     │ (FK)            │
│ _id (FK)        │     │ aciklama        │
└─────────────────┘     └─────────────────┘
```

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Görev Oluşturma Tutarlılığı

_For any_ doluluk verisi yüklemesi, yükleme tamamlandığında ilgili kat sorumluları için görev listesi oluşturulmalı ve görev sayısı yüklenen oda sayısına eşit olmalıdır.
**Validates: Requirements 1.1**

### Property 2: In House ve Arrivals Ayrımı

_For any_ görev listesi, In House ve Arrivals görevleri ayrı listeler halinde döndürülmeli ve hiçbir görev her iki listede birden bulunmamalıdır.
**Validates: Requirements 1.4, 2.1, 3.1**

### Property 3: Görev Tamamlama Durumu

_For any_ tamamlanan görev, durum "completed" olarak güncellenmeli ve tamamlanma zamanı kaydedilmelidir.
**Validates: Requirements 2.2, 3.4**

### Property 4: DND İşaretleme ve Listeleme

_For any_ DND olarak işaretlenen oda, hem ana görev listesinde hem de DND listesinde görünmeli ve DND sayısı artmalıdır.
**Validates: Requirements 2.3, 2.4**

### Property 5: DND 3 Kontrol Kuralı

_For any_ DND odası, 3 kez DND olarak işaretlendiğinde görev durumu otomatik olarak "completed" olmalıdır.
**Validates: Requirements 4.3**

### Property 6: Geri Sayım Hesaplama

_For any_ Arrivals görevi, geri sayım değeri varış saati ile şimdiki zaman arasındaki fark olmalı ve negatif olamaz.
**Validates: Requirements 3.2**

### Property 7: Yükleme Görevi Tamamlama

_For any_ dosya yüklemesi, ilgili yükleme görevi "completed" olarak işaretlenmeli ve yükleme zamanı kaydedilmelidir.
**Validates: Requirements 6.2**

### Property 8: Eksik Yükleme Tespiti

_For any_ tarih aralığı sorgusu, yükleme yapılmayan günler doğru şekilde tespit edilmeli ve ilgili depo sorumluları listelenmelidir.
**Validates: Requirements 9.4**

### Property 9: Görev Durumu Log Round-Trip

_For any_ görev durumu değişikliği, log kaydı oluşturulmalı ve JSON serialize/deserialize işlemi sonrası orijinal veri ile eşleşmelidir.
**Validates: Requirements 10.1, 10.3, 10.4**

### Property 10: Dashboard Veri Tutarlılığı

_For any_ personel ve tarih kombinasyonu, tamamlanan + tamamlanmayan görev sayısı toplam görev sayısına eşit olmalıdır.
**Validates: Requirements 5.1, 7.1, 8.1**

## Error Handling

### Hata Senaryoları ve Çözümleri

| Senaryo                    | Hata Tipi         | Çözüm                                        |
| -------------------------- | ----------------- | -------------------------------------------- |
| Doluluk verisi yüklenemedi | FileUploadError   | Kullanıcıya hata mesajı göster, log kaydet   |
| Görev oluşturulamadı       | TaskCreationError | Transaction rollback, retry mekanizması      |
| DND işaretleme başarısız   | DNDMarkError      | Kullanıcıya bilgi ver, manuel işlem seçeneği |
| Bildirim gönderilemedi     | NotificationError | Queue'ya ekle, retry mekanizması             |
| Veritabanı bağlantı hatası | DatabaseError     | Connection pool retry, fallback              |

### Validasyon Kuralları

```python
# Görev oluşturma validasyonu
def validate_task_creation(otel_id: int, personel_id: int, tarih: date) -> bool:
    if not otel_id or not personel_id:
        raise ValueError("Otel ve personel ID zorunludur")
    if tarih < date.today():
        raise ValueError("Geçmiş tarih için görev oluşturulamaz")
    return True

# DND işaretleme validasyonu
def validate_dnd_mark(gorev_detay_id: int, personel_id: int) -> bool:
    gorev = GorevDetay.query.get(gorev_detay_id)
    if not gorev:
        raise ValueError("Görev bulunamadı")
    if gorev.durum == GorevDurum.COMPLETED:
        raise ValueError("Tamamlanmış görev DND olarak işaretlenemez")
    return True
```

## Testing Strategy

### Test Framework

- **Unit Tests**: pytest
- **Property-Based Tests**: hypothesis (Python PBT kütüphanesi)
- **Integration Tests**: pytest + Flask test client

### Unit Test Kapsamı

1. **Model Tests**

   - GunlukGorev CRUD işlemleri
   - GorevDetay CRUD işlemleri
   - DNDKontrol kayıt işlemleri
   - YuklemeGorev durum güncellemeleri

2. **Service Tests**

   - GorevService.create_daily_tasks()
   - GorevService.complete_task()
   - GorevService.mark_dnd()
   - YuklemeGorevService.complete_upload_task()
   - BildirimService.send_task_notification()

3. **Route Tests**
   - GET /gorevler endpoint'leri
   - POST /gorevler/<id>/tamamla
   - POST /gorevler/<id>/dnd
   - API endpoint'leri

### Property-Based Test Gereksinimleri

Her property-based test:

- Minimum 100 iterasyon çalıştırılmalı
- Hypothesis kütüphanesi kullanılmalı
- Design dokümanındaki property numarası ile etiketlenmeli
- Format: `**Feature: gorevlendirme-sistemi, Property {number}: {property_text}**`

### Test Dosya Yapısı

```
tests/
├── test_gorev_models.py          # Model unit tests
├── test_gorev_service.py         # Service unit tests
├── test_gorev_routes.py          # Route integration tests
├── test_gorev_properties.py      # Property-based tests
└── conftest.py                   # Test fixtures
```

### Örnek Property Test

```python
from hypothesis import given, strategies as st, settings

@settings(max_examples=100)
@given(
    oda_sayisi=st.integers(min_value=1, max_value=100),
    inhouse_orani=st.floats(min_value=0, max_value=1)
)
def test_gorev_olusturma_tutarliligi(oda_sayisi, inhouse_orani):
    """
    **Feature: gorevlendirme-sistemi, Property 1: Görev Oluşturma Tutarlılığı**
    **Validates: Requirements 1.1**
    """
    # Test implementation
    pass
```
