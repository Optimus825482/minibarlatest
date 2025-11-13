# Fiyatlandırma ve Karlılık Sistemi Migration Kılavuzu

## Genel Bakış

Bu migration script'i, mini bar stok takip sistemine kapsamlı fiyatlandırma ve karlılık hesaplama yetenekleri ekler.

## Oluşturulan Tablolar

### 1. Tedarikçi Yönetimi

- **tedarikciler**: Tedarikçi bilgileri
- **urun_tedarikci_fiyatlari**: Ürün-tedarikçi fiyat ilişkileri
- **urun_fiyat_gecmisi**: Fiyat değişiklik geçmişi

### 2. Dinamik Fiyatlandırma

- **oda_tipi_satis_fiyatlari**: Oda tipi bazlı satış fiyatları
- **sezon_fiyatlandirma**: Sezonluk fiyat çarpanları

### 3. Kampanya ve Bedelsiz

- **kampanyalar**: Promosyon ve indirim yönetimi
- **bedelsiz_limitler**: Bedelsiz tüketim limitleri
- **bedelsiz_kullanim_log**: Bedelsiz kullanım kayıtları

### 4. Karlılık Analizi

- **donemsel_kar_analizi**: Dönemsel karlılık raporları
- **roi_hesaplamalari**: ROI hesaplama kayıtları
- **fiyat_guncelleme_kurallari**: Otomatik fiyat güncelleme kuralları

### 5. Stok Yönetimi

- **urun_stok**: Ürün stok durumu ve değerleri

## Eklenen Kolonlar

### minibar_islem_detay Tablosu

- `satis_fiyati`: Satış fiyatı (NUMERIC)
- `alis_fiyati`: Alış fiyatı (NUMERIC)
- `kar_tutari`: Kar tutarı (NUMERIC)
- `kar_orani`: Kar oranı yüzdesi (NUMERIC)
- `bedelsiz`: Bedelsiz flag (BOOLEAN)
- `kampanya_id`: Kampanya referansı (INTEGER, FK)

## ENUM Tipleri

- **FiyatDegisiklikTipi**: alis_fiyati, satis_fiyati, kampanya
- **IndirimTipi**: yuzde, tutar
- **BedelsizLimitTipi**: misafir, kampanya, personel
- **DonemTipi**: gunluk, haftalik, aylik
- **KuralTipi**: otomatik_artir, otomatik_azalt, rakip_fiyat

## Kullanım

### Migration Çalıştırma (Upgrade)

**Önemli**: Migration'ı proje kök dizininden çalıştırın!

```bash
# Proje kök dizininde olduğunuzdan emin olun
cd D:\minibartakip2cool

# Migration'ı çalıştır
python migrations\add_fiyatlandirma_karlilik_sistemi.py
```

**veya Batch dosyası ile (Önerilen)**:

```bash
run_fiyatlandirma_migration.bat
```

Bu komut:

1. ✅ ENUM tiplerini oluşturur
2. ✅ Yeni tabloları oluşturur
3. ✅ MinibarIslemDetay tablosuna kolonlar ekler
4. ✅ Performans index'lerini oluşturur
5. ✅ Varsayılan verileri ekler (varsayılan tedarikçi)

### Rollback (Downgrade)

```bash
# Proje kök dizininde
python migrations\add_fiyatlandirma_karlilik_sistemi.py downgrade
```

**veya Batch dosyası ile**:

```bash
run_fiyatlandirma_migration.bat
# Menüden "2" seçin
```

⚠️ **UYARI**: Bu komut TÜM fiyatlandırma ve karlılık verilerini siler!

Onay gerektirir:

```
⚠️  UYARI: TÜM FİYATLANDIRMA VE KARLILIK VERİLERİ SİLİNECEK!
Bu işlem geri alınamaz!

Devam etmek istediğinize emin misiniz? (yes/no):
```

## Güvenlik Önlemleri

### Migration Öncesi

1. ✅ Veritabanı yedeği alın
2. ✅ Test ortamında deneyin
3. ✅ Mevcut verileri kontrol edin

### Migration Sonrası

1. ✅ Tablo yapılarını doğrulayın
2. ✅ Index'lerin oluştuğunu kontrol edin
3. ✅ Varsayılan verileri kontrol edin

## Performans Index'leri

Migration, aşağıdaki performans index'lerini otomatik oluşturur:

- Tedarikçi aktif durumu
- Ürün-tedarikçi fiyat sorguları
- Fiyat geçmişi tarih sorguları
- Oda tipi fiyat sorguları
- Sezon tarih aralığı sorguları
- Kampanya aktif durumu ve tarih
- Bedelsiz limit sorguları
- Kar analizi sorguları
- Stok kritik seviye sorguları

## Veri Bütünlüğü

### Foreign Key Constraints

- ✅ Tüm ilişkiler foreign key ile korunur
- ✅ CASCADE ve SET NULL stratejileri uygulanır
- ✅ Orphan kayıtlar önlenir

### Varsayılan Değerler

- ✅ Timestamp alanları otomatik doldurulur
- ✅ Boolean alanlar varsayılan değerlere sahip
- ✅ NUMERIC alanlar hassasiyet korumalı

## Sorun Giderme

### ENUM Zaten Var Hatası

```
⚠️  ENUM oluşturma hatası (zaten var olabilir)
```

Bu normal bir durumdur. ENUM'lar zaten varsa atlanır.

### Foreign Key Hatası

Eğer foreign key hatası alırsanız:

1. İlgili tabloların var olduğunu kontrol edin
2. Referans edilen kayıtların mevcut olduğunu doğrulayın

### Index Oluşturma Hatası

Index zaten varsa, `IF NOT EXISTS` sayesinde hata vermez.

## Gereksinimler

- PostgreSQL 12+
- Flask-SQLAlchemy
- Python 3.8+
- Mevcut mini bar stok takip sistemi

## İlgili Dosyalar

- `models.py`: Model tanımları
- `utils/fiyatlandirma_servisler.py`: Fiyatlandırma servisleri
- `routes/fiyatlandirma_routes.py`: API endpoint'leri
- `routes/karlilik_routes.py`: Karlılık API'leri

## Destek

Sorun yaşarsanız:

1. Migration log'larını kontrol edin
2. Veritabanı bağlantısını doğrulayın
3. Yetki kontrolü yapın (CREATE TABLE, CREATE INDEX)

## Versiyon

- **Versiyon**: 1.0.0
- **Tarih**: 2025-11-13
- **Gereksinimler**: 20.1, 20.2, 20.3
