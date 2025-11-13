# Database Optimizasyon Kılavuzu

Fiyatlandırma ve Karlılık Sistemi için veritabanı performans optimizasyonu rehberi.

## İçindekiler

1. [Genel Bakış](#genel-bakış)
2. [Index Yönetimi](#index-yönetimi)
3. [Query Performansı](#query-performansı)
4. [Connection Pool](#connection-pool)
5. [Tablo Optimizasyonu](#tablo-optimizasyonu)
6. [Kullanım](#kullanım)
7. [Best Practices](#best-practices)

---

## Genel Bakış

Database optimizasyon sistemi, fiyatlandırma ve karlılık hesaplama modülünün performansını artırmak için tasarlanmıştır.

### Özellikler

- ✅ Otomatik index kontrolü ve oluşturma
- ✅ Query performans analizi
- ✅ Connection pool monitoring
- ✅ Tablo optimizasyonu (ANALYZE)
- ✅ Sağlık kontrolü
- ✅ CLI ve Web UI desteği

---

## Index Yönetimi

### Kritik Index'ler

Fiyatlandırma sistemi için gerekli index'ler:

#### 1. Ürün-Tedarikçi Fiyatları

```sql
CREATE INDEX idx_urun_tedarikci_aktif ON urun_tedarikci_fiyatlari (urun_id, tedarikci_id, aktif);
CREATE INDEX idx_urun_fiyat_tarih ON urun_tedarikci_fiyatlari (urun_id, baslangic_tarihi, bitis_tarihi);
```

#### 2. Oda Tipi Fiyatları

```sql
CREATE INDEX idx_oda_tipi_urun_aktif ON oda_tipi_satis_fiyatlari (oda_tipi, urun_id, aktif);
```

#### 3. Kampanyalar

```sql
CREATE INDEX idx_kampanya_aktif_tarih ON kampanyalar (aktif, baslangic_tarihi, bitis_tarihi);
```

#### 4. Stok Yönetimi

```sql
CREATE INDEX idx_urun_stok_otel ON urun_stok (otel_id, urun_id);
CREATE INDEX idx_urun_stok_kritik ON urun_stok (mevcut_stok, kritik_stok_seviyesi);
```

#### 5. Karlılık Analizi

```sql
CREATE INDEX idx_kar_analiz_otel_donem ON donemsel_kar_analizi (otel_id, donem_tipi, baslangic_tarihi);
CREATE INDEX idx_islem_detay_kar ON minibar_islem_detaylari (kar_tutari, kar_orani);
```

### Index Kontrolü

**CLI:**

```bash
python run_db_optimization.py --check-indexes
```

**Web UI:**

```
http://localhost:5000/api/v1/db/dashboard
```

**API:**

```bash
curl -X GET http://localhost:5000/api/v1/db/indexes/check
```

### Index Oluşturma

**CLI:**

```bash
python run_db_optimization.py --create-indexes
```

**API:**

```bash
curl -X POST http://localhost:5000/api/v1/db/indexes/create
```

---

## Query Performansı

### Performans Analizi

Sistem, son 24 saatteki yavaş query'leri tespit eder (>1 saniye).

**CLI:**

```bash
python run_db_optimization.py --analyze-performance
```

**API:**

```bash
curl -X GET http://localhost:5000/api/v1/db/performance/analyze
```

### Yavaş Query Optimizasyonu

#### 1. Fiyat Hesaplama Query'leri

**Problem:** Dinamik fiyat hesaplama yavaş

```sql
-- Yavaş
SELECT * FROM urun_tedarikci_fiyatlari
WHERE urun_id = 1 AND aktif = true;
```

**Çözüm:** Index kullan

```sql
-- Hızlı (idx_urun_tedarikci_aktif kullanır)
SELECT * FROM urun_tedarikci_fiyatlari
WHERE urun_id = 1 AND tedarikci_id = 1 AND aktif = true;
```

#### 2. Karlılık Analizi Query'leri

**Problem:** Dönemsel kar analizi yavaş

```sql
-- Yavaş
SELECT SUM(kar_tutari) FROM minibar_islem_detaylari
WHERE islem_tarihi BETWEEN '2024-01-01' AND '2024-01-31';
```

**Çözüm:** Önceden hesaplanmış donemsel_kar_analizi tablosunu kullan

```sql
-- Hızlı
SELECT net_kar FROM donemsel_kar_analizi
WHERE donem_tipi = 'aylik' AND baslangic_tarihi = '2024-01-01';
```

### Cache Stratejisi

```python
# Fiyat hesaplama - 1 saat cache
@cache.memoize(timeout=3600)
def dinamik_fiyat_hesapla(urun_id, oda_id):
    pass

# Kar analizi - 30 dakika cache
@cache.memoize(timeout=1800)
def donemsel_kar_analizi(otel_id, baslangic, bitis):
    pass
```

---

## Connection Pool

### Mevcut Ayarlar (config.py)

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 5,              # 5 connection pool
    'max_overflow': 10,          # Max 15 connection total
    'pool_timeout': 30,          # 30 saniye wait timeout
    'pool_recycle': 3600,        # 1 saatte bir recycle
    'pool_pre_ping': True,       # Health check before use
}
```

### Pool Monitoring

**CLI:**

```bash
python run_db_optimization.py --check-health
```

**API:**

```bash
curl -X GET http://localhost:5000/api/v1/db/pool/stats
```

### Pool Optimizasyonu

#### Küçük Uygulama (< 100 kullanıcı)

```python
'pool_size': 5,
'max_overflow': 10,
```

#### Orta Uygulama (100-500 kullanıcı)

```python
'pool_size': 10,
'max_overflow': 20,
```

#### Büyük Uygulama (> 500 kullanıcı)

```python
'pool_size': 20,
'max_overflow': 30,
```

---

## Tablo Optimizasyonu

### ANALYZE Komutu

PostgreSQL'de ANALYZE komutu, query planner'ın daha iyi kararlar alması için tablo istatistiklerini günceller.

**CLI:**

```bash
python run_db_optimization.py --optimize-tables
```

**API:**

```bash
curl -X POST http://localhost:5000/api/v1/db/tables/optimize
```

### Optimize Edilen Tablolar

- `urun_tedarikci_fiyatlari`
- `oda_tipi_satis_fiyatlari`
- `kampanyalar`
- `bedelsiz_limitler`
- `minibar_islem_detaylari`
- `donemsel_kar_analizi`
- `urun_stok`
- `urun_fiyat_gecmisi`

### Optimizasyon Sıklığı

- **Günlük:** Yoğun kullanılan tablolar
- **Haftalık:** Orta kullanılan tablolar
- **Aylık:** Az kullanılan tablolar

---

## Kullanım

### 1. CLI Kullanımı

#### Sağlık Kontrolü

```bash
python run_db_optimization.py --check-health
```

#### Index Kontrolü ve Oluşturma

```bash
python run_db_optimization.py --check-indexes
python run_db_optimization.py --create-indexes
```

#### Tablo Optimizasyonu

```bash
python run_db_optimization.py --optimize-tables
```

#### Tam Optimizasyon

```bash
python run_db_optimization.py --full-optimization
```

#### Windows Batch Script

```bash
run_db_optimization.bat
```

### 2. Web UI Kullanımı

Dashboard'a erişim:

```
http://localhost:5000/api/v1/db/dashboard
```

**Not:** Sadece `sistem_yoneticisi` rolü erişebilir.

### 3. API Kullanımı

#### Sağlık Kontrolü

```bash
curl -X GET http://localhost:5000/api/v1/db/health
```

#### Index Kontrolü

```bash
curl -X GET http://localhost:5000/api/v1/db/indexes/check
```

#### Index Oluşturma

```bash
curl -X POST http://localhost:5000/api/v1/db/indexes/create
```

#### Performans Analizi

```bash
curl -X GET http://localhost:5000/api/v1/db/performance/analyze
```

#### Tablo Optimizasyonu

```bash
curl -X POST http://localhost:5000/api/v1/db/tables/optimize
```

#### Tam Optimizasyon

```bash
curl -X POST http://localhost:5000/api/v1/db/optimize/full
```

---

## Best Practices

### 1. Düzenli Bakım

```bash
# Haftalık cron job
0 2 * * 0 cd /path/to/app && python run_db_optimization.py --full-optimization
```

### 2. Monitoring

- Cache hit ratio > %95 olmalı
- Yavaş query sayısı < 10 olmalı
- Connection pool overflow < %20 olmalı

### 3. Index Stratejisi

✅ **Yapılması Gerekenler:**

- Sık kullanılan WHERE kolonlarına index
- JOIN kolonlarına index
- ORDER BY kolonlarına index
- Composite index'ler (çok kolonlu)

❌ **Yapılmaması Gerekenler:**

- Küçük tablolara index (<1000 satır)
- Çok sık güncellenen kolonlara index
- Low cardinality kolonlara index (boolean)

### 4. Query Optimizasyonu

✅ **İyi Pratikler:**

```python
# Cache kullan
@cache.memoize(timeout=3600)
def get_fiyat(urun_id):
    pass

# Lazy loading yerine eager loading
query = Urun.query.options(
    joinedload(Urun.tedarikci_fiyatlari)
).filter_by(id=urun_id).first()

# Pagination kullan
query = Urun.query.paginate(page=1, per_page=50)
```

❌ **Kötü Pratikler:**

```python
# N+1 problem
for urun in urunler:
    fiyat = urun.tedarikci_fiyatlari  # Her seferinde query

# SELECT *
query = db.session.execute("SELECT * FROM urunler")

# Cache'siz ağır hesaplamalar
def kar_hesapla():
    # Ağır hesaplama, cache yok
    pass
```

### 5. Connection Pool Yönetimi

```python
# Session'ı her zaman kapat
try:
    result = db.session.query(...)
    db.session.commit()
except:
    db.session.rollback()
finally:
    db.session.close()

# Context manager kullan
with app.app_context():
    result = db.session.query(...)
```

---

## Troubleshooting

### Problem: Yavaş Query'ler

**Çözüm:**

1. Index kontrolü yap
2. EXPLAIN ANALYZE kullan
3. Query'yi optimize et
4. Cache ekle

### Problem: Connection Pool Doldu

**Çözüm:**

1. Pool size'ı artır
2. Connection leak kontrolü
3. Session'ları düzgün kapat

### Problem: Disk Doldu

**Çözüm:**

1. Eski log'ları temizle
2. VACUUM FULL çalıştır
3. Gereksiz index'leri sil

---

## Sonuç

Database optimizasyonu, fiyatlandırma ve karlılık sisteminin performansı için kritiktir. Düzenli bakım ve monitoring ile sistem her zaman optimal performansta çalışacaktır.

**Önerilen Bakım Takvimi:**

- Günlük: Sağlık kontrolü
- Haftalık: Tam optimizasyon
- Aylık: Performans analizi ve raporlama

---

**Erkan için hazırlandı** 🚀
