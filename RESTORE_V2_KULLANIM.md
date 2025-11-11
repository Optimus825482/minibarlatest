# 🔄 Gelişmiş Yedek Geri Yükleme Sistemi (V2)

## 📋 Özellikler

### ✨ Yeni Özellikler
- **CREATE TABLE Desteği**: Tablolar yoksa otomatik oluşturulur
- **Akıllı Parsing**: `public.` schema prefix'i ve `IF NOT EXISTS` desteği
- **Gelişmiş UI**: Modern, gradient tasarım ve animasyonlar
- **Detaylı İstatistikler**: Tablo sayısı, kayıt sayısı, yeni tablolar
- **Bağımlılık Yönetimi**: Foreign key ilişkileri otomatik tespit edilir
- **Hata Toleransı**: Hatalar loglanır ama işlem devam eder
- **Progress Bar**: Yükleme ve işlem durumu görsel olarak gösterilir

### 🎯 Kullanım Senaryoları

1. **Railway'den Coolify'a Migrasyon**
   - Railway backup'ını yükle
   - Tabloları karşılaştır
   - Seçili tabloları aktar

2. **Kısmi Restore**
   - Sadece belirli tabloları geri yükle
   - Bağımlılıklar otomatik seçilir

3. **Full Restore**
   - Tüm database'i sıfırdan yükle
   - Schema temizlenir ve yeniden oluşturulur

## 🚀 Kullanım

### 1. Sayfaya Erişim
```
URL: /restore_backup
Yetki: Sadece sistem_yoneticisi
```

### 2. Backup Yükleme
- `.sql` dosyasını seç veya sürükle-bırak
- "Dosyayı Yükle ve Analiz Et" butonuna tıkla
- Sistem otomatik olarak tabloları analiz eder

### 3. Tablo Karşılaştırması
Sistem şunları gösterir:
- ✅ **Yedekteki Kayıt**: Backup dosyasındaki kayıt sayısı
- 🔶 **Mevcut Kayıt**: Database'deki mevcut kayıt sayısı
- 🆕 **Yeni Tablo**: Henüz oluşturulmamış tablolar
- ⚠️ **Bağımlılıklar**: Foreign key ilişkileri

### 4. Restore Seçenekleri

#### A) Seçili Tabloları Aktar
1. İstediğin tabloları seç (checkbox)
2. Bağımlı tablolar otomatik seçilir
3. "Seçili Tabloları Aktar" butonuna tıkla

#### B) Tüm Database'i Geri Yükle
1. "Tüm Database'i Geri Yükle" butonuna tıkla
2. İki kez onay ver (güvenlik)
3. Tüm schema temizlenir ve yeniden oluşturulur

## 🔧 Teknik Detaylar

### CREATE TABLE Parsing
```python
# Desteklenen formatlar:
CREATE TABLE table_name (...)
CREATE TABLE IF NOT EXISTS table_name (...)
CREATE TABLE public.table_name (...)
CREATE TABLE IF NOT EXISTS public.table_name (...)
```

### INSERT Parsing
```python
# Desteklenen formatlar:
INSERT INTO table_name VALUES (...)
INSERT INTO public.table_name VALUES (...)
```

### Hata Yönetimi
- **TRUNCATE hatası** → DELETE dener
- **CREATE TABLE hatası** → Devam eder
- **INSERT hatası** → Loglanır, devam eder
- **Foreign Key hatası** → Geçici olarak devre dışı bırakılır

### Session Yönetimi
```python
session['backup_filepath']      # Yüklenen dosya yolu
session['create_statements']    # CREATE TABLE SQL'leri
```

## 📊 API Endpoint'leri

### 1. Upload Backup
```
POST /api/upload_backup
Content-Type: multipart/form-data

Response:
{
  "success": true,
  "filename": "backup.sql",
  "file_size": 1048576,
  "total_tables": 25,
  "comparison": [...]
}
```

### 2. Restore Tables
```
POST /api/restore_tables
Content-Type: application/json

Body:
{
  "tables": ["users", "products", "orders"]
}

Response:
{
  "success": true,
  "results": [
    {
      "table": "users",
      "success": true,
      "restored_count": 150,
      "error_count": 0,
      "created": false
    }
  ]
}
```

### 3. Restore Full
```
POST /api/restore_full

Response:
{
  "success": true,
  "message": "Full restore tamamlandı!",
  "success_count": 1250,
  "error_count": 5
}
```

## 🎨 UI Özellikleri

### Gradient Tasarım
- Modern gradient arka plan
- Smooth animasyonlar
- Responsive tasarım

### İstatistik Kartları
- Toplam Tablo
- Yedekteki Kayıt
- Mevcut Kayıt
- Yeni Tablo

### Durum Göstergeleri
- ⏳ Aktarılıyor...
- ✅ Aktarıldı: X kayıt
- ❌ Hata
- 🆕 Yeni Tablo

## 🔒 Güvenlik

### CSRF Koruması
```python
# routes/__init__.py
csrf.exempt(restore_v2_bp)
```

### Yetki Kontrolü
```python
@login_required
@role_required(['sistem_yoneticisi'])
```

### Dosya Doğrulama
- Sadece `.sql` dosyaları
- Max 100MB boyut
- Secure filename

## 🐛 Sorun Giderme

### Problem: "Backup dosyası bulunamadı"
**Çözüm**: Session timeout olmuş olabilir, dosyayı tekrar yükle

### Problem: "CREATE TABLE hatası"
**Çözüm**: Tablo zaten var, sistem otomatik TRUNCATE yapar

### Problem: "INSERT hatası"
**Çözüm**: 
- Binary data encoding problemi olabilir
- Foreign key constraint hatası olabilir
- Sistem devam eder, hata sayısı gösterilir

### Problem: "Foreign key constraint"
**Çözüm**: 
- Bağımlı tabloları önce seç
- Veya "Tüm Database'i Geri Yükle" kullan

## 📝 Örnek Kullanım

### Railway'den Coolify'a Migrasyon
```bash
# 1. Railway'den backup al
railway db backup > railway_backup.sql

# 2. Coolify'da restore sayfasına git
https://your-coolify-domain.com/restore_backup

# 3. railway_backup.sql dosyasını yükle

# 4. Tabloları karşılaştır ve seç

# 5. "Seçili Tabloları Aktar" veya "Tüm Database'i Geri Yükle"
```

## 🎯 Best Practices

1. **Backup Önce**: Mevcut database'in backup'ını al
2. **Test Et**: Önce test ortamında dene
3. **Seçici Ol**: Sadece gerekli tabloları aktar
4. **Bağımlılıkları Kontrol Et**: Foreign key ilişkilerine dikkat et
5. **Logları İzle**: Hata sayısını kontrol et

## 🔄 Versiyon Karşılaştırması

| Özellik | V1 | V2 |
|---------|----|----|
| CREATE TABLE Desteği | ❌ | ✅ |
| Modern UI | ❌ | ✅ |
| Progress Bar | ❌ | ✅ |
| İstatistikler | Basit | Detaylı |
| Hata Toleransı | Düşük | Yüksek |
| Bağımlılık Yönetimi | Manuel | Otomatik |
| Schema Prefix | ❌ | ✅ |

## 📞 Destek

Sorun yaşarsan:
1. Browser console'u kontrol et
2. Server loglarını incele
3. Session'ı temizle ve tekrar dene
4. Backup dosyasını text editor'de kontrol et

---

**Not**: Bu sistem Railway, Supabase, Heroku gibi platformlardan alınan SQL backup'larıyla uyumludur.
