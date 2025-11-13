# Fiyatlandırma Migration Kontrol Listesi

## Migration Öncesi Kontroller

- [ ] Veritabanı yedeği alındı mı?
- [ ] Test ortamında denendi mi?
- [ ] PostgreSQL versiyonu uygun mu? (12+)
- [ ] Gerekli Python paketleri yüklü mü?
- [ ] .env dosyası yapılandırıldı mı?

## Migration Adımları

### 1. Yedek Al

```bash
# PostgreSQL yedek
pg_dump -U postgres -d minibar_db > backup_before_fiyatlandirma.sql

# veya Python script ile
python backup_database.py
```

### 2. Migration Çalıştır

**ÖNEMLİ**: Proje kök dizininden çalıştırın!

```bash
# Proje kök dizinine git
cd D:\minibartakip2cool

# Doğrudan Python ile
python migrations\add_fiyatlandirma_karlilik_sistemi.py

# veya Batch dosyası ile (Önerilen)
run_fiyatlandirma_migration.bat
```

### 3. Doğrulama Kontrolleri

#### Tabloları Kontrol Et

```sql
-- Tüm tabloların oluştuğunu kontrol et
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'tedarikciler',
    'urun_tedarikci_fiyatlari',
    'urun_fiyat_gecmisi',
    'oda_tipi_satis_fiyatlari',
    'sezon_fiyatlandirma',
    'kampanyalar',
    'bedelsiz_limitler',
    'bedelsiz_kullanim_log',
    'donemsel_kar_analizi',
    'fiyat_guncelleme_kurallari',
    'roi_hesaplamalari',
    'urun_stok'
);
```

#### Kolonları Kontrol Et

```sql
-- MinibarIslemDetay yeni kolonları
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'minibar_islem_detay'
AND column_name IN (
    'satis_fiyati',
    'alis_fiyati',
    'kar_tutari',
    'kar_orani',
    'bedelsiz',
    'kampanya_id'
);
```

#### Index'leri Kontrol Et

```sql
-- Tüm index'leri listele
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
AND indexname LIKE 'idx_%fiyat%'
OR indexname LIKE 'idx_%kar%'
OR indexname LIKE 'idx_%kampanya%';
```

#### ENUM Tiplerini Kontrol Et

```sql
-- ENUM tiplerini listele
SELECT typname
FROM pg_type
WHERE typname IN (
    'fiyatdegisikliktipi',
    'indirimtipi',
    'bedelsizlimittipi',
    'donemtipi',
    'kuraltipi'
);
```

## Migration Sonrası Kontroller

- [ ] Tüm tablolar oluşturuldu mu? (12 tablo)
- [ ] MinibarIslemDetay'a 6 kolon eklendi mi?
- [ ] Index'ler oluşturuldu mu? (15+ index)
- [ ] ENUM tipleri oluşturuldu mu? (5 tip)
- [ ] Varsayılan tedarikçi eklendi mi?
- [ ] Foreign key constraint'ler çalışıyor mu?
- [ ] Uygulama hatasız başlıyor mu?

## Test Senaryoları

### 1. Tedarikçi Oluşturma

```python
from models import db, Tedarikci

tedarikci = Tedarikci(
    tedarikci_adi="Test Tedarikçi",
    iletisim_bilgileri={"telefon": "123456", "email": "test@test.com"}
)
db.session.add(tedarikci)
db.session.commit()
```

### 2. Ürün Fiyatı Ekleme

```python
from models import UrunTedarikciFiyat
from datetime import datetime, timezone

fiyat = UrunTedarikciFiyat(
    urun_id=1,
    tedarikci_id=1,
    alis_fiyati=10.50,
    baslangic_tarihi=datetime.now(timezone.utc),
    olusturan_id=1
)
db.session.add(fiyat)
db.session.commit()
```

### 3. Kampanya Oluşturma

```python
from models import Kampanya, IndirimTipi
from datetime import datetime, timezone, timedelta

kampanya = Kampanya(
    kampanya_adi="Test Kampanya",
    baslangic_tarihi=datetime.now(timezone.utc),
    bitis_tarihi=datetime.now(timezone.utc) + timedelta(days=30),
    indirim_tipi=IndirimTipi.YUZDE,
    indirim_degeri=10,
    olusturan_id=1
)
db.session.add(kampanya)
db.session.commit()
```

## Sorun Giderme

### Hata: "relation already exists"

**Çözüm**: Tablo zaten var. Normal durum, migration devam eder.

### Hata: "type already exists"

**Çözüm**: ENUM zaten var. Normal durum, migration devam eder.

### Hata: "column already exists"

**Çözüm**: Kolon zaten var. `IF NOT EXISTS` kullanıldığı için sorun yok.

### Hata: "permission denied"

**Çözüm**: Veritabanı kullanıcısının CREATE yetkisi olduğundan emin olun.

## Rollback Prosedürü

Eğer bir sorun olursa:

```bash
# 1. Migration'ı geri al
python migrations/add_fiyatlandirma_karlilik_sistemi.py downgrade

# 2. Yedeği geri yükle
psql -U postgres -d minibar_db < backup_before_fiyatlandirma.sql
```

## İletişim

Sorun yaşarsanız:

- Migration log'larını kaydedin
- Hata mesajını not edin
- Veritabanı versiyonunu kontrol edin

## Notlar

- Migration yaklaşık 5-10 saniye sürer
- Veri kaybı olmaz (sadece yeni tablolar/kolonlar eklenir)
- Mevcut işlevsellik etkilenmez
- Rollback güvenlidir (ama veri kaybı olur!)
