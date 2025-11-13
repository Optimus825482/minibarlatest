# 🚀 Hızlı Başlangıç - Fiyatlandırma Migration

## En Kolay Yöntem (Önerilen)

1. **Proje kök dizinine git**:

   ```bash
   cd D:\minibartakip2cool
   ```

2. **Batch dosyasını çalıştır**:

   ```bash
   run_fiyatlandirma_migration.bat
   ```

3. **Menüden "1" seç** (Migration Çalıştır)

4. **Bekle** - İşlem 5-10 saniye sürer

5. **Başarı mesajını gör** ✅

## Alternatif Yöntem (Python)

```bash
cd D:\minibartakip2cool
python migrations\add_fiyatlandirma_karlilik_sistemi.py
```

## Sorun mu Yaşıyorsun?

### Hata: "No module named 'models'"

**Çözüm**: Proje kök dizininde olduğundan emin ol!

```bash
cd D:\minibartakip2cool
```

### Hata: "No module named 'flask'"

**Çözüm**: Virtual environment'ı aktif et

```bash
venv\Scripts\activate
```

### Hata: "Connection refused"

**Çözüm**: PostgreSQL çalışıyor mu kontrol et

```bash
# PostgreSQL servisini başlat
net start postgresql-x64-14
```

### Hata: "Permission denied"

**Çözüm**: Veritabanı kullanıcısının CREATE yetkisi var mı?

## Rollback (Geri Al)

Eğer bir sorun olursa:

```bash
cd D:\minibartakip2cool
python migrations\add_fiyatlandirma_karlilik_sistemi.py downgrade
```

⚠️ **DİKKAT**: Bu komut tüm fiyatlandırma verilerini siler!

## Doğrulama

Migration başarılı olduysa şunları göreceksin:

```
======================================================================
🚀 FİYATLANDIRMA VE KARLILIK SİSTEMİ MIGRATION BAŞLIYOR
======================================================================

📋 1. ENUM tipleri oluşturuluyor...
   ✅ ENUM tipleri oluşturuldu

📋 2. Yeni tablolar oluşturuluyor...
   ✅ Tüm tablolar oluşturuldu

📋 3. MinibarIslemDetay tablosuna fiyat kolonları ekleniyor...
   ✅ Fiyat kolonları eklendi

📋 4. Performans index'leri oluşturuluyor...
   ✅ Index'ler oluşturuldu

📋 5. Varsayılan veriler ekleniyor...
   ✅ Varsayılan veriler eklendi

======================================================================
✅ MİGRATION BAŞARIYLA TAMAMLANDI!
======================================================================
```

## Yardım

Daha fazla bilgi için:

- `migrations/README_FIYATLANDIRMA_MIGRATION.md` - Detaylı kılavuz
- `migrations/MIGRATION_CHECKLIST.md` - Kontrol listesi
