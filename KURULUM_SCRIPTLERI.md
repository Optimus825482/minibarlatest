# 📦 KURULUM SCRİPTLERİ - GENEL BAKIŞ

Sistem kurulumu için hazırlanmış tüm scriptler ve kullanım kılavuzu.

---

## 🎯 Hangi Script Ne İçin?

| Script | Kullanım | Önerilen |
|--------|----------|----------|
| `quick_setup.py` | Tek komutla tam kurulum | ⭐⭐⭐⭐⭐ |
| `setup_first_admin.py` | Özel admin oluşturma | ⭐⭐⭐⭐ |
| `init_db.py` | Sadece veritabanı/tablolar | ⭐⭐⭐ |
| `kurulum.bat` | Windows hızlı kurulum | ⭐⭐⭐⭐⭐ |
| `kurulum.sh` | Linux/Mac hızlı kurulum | ⭐⭐⭐⭐⭐ |

---

## 1️⃣ quick_setup.py

### 🎯 Amaç
Sıfırdan tam otomatik kurulum.

### ✨ Özellikler
- Veritabanı oluşturma
- Tablo oluşturma
- Varsayılan admin (admin/admin123)
- Varsayılan otel
- Örnek veriler (opsiyonel)

### 📝 Kullanım
```bash
python quick_setup.py
```

### 🔄 İşlem Akışı
```
1. Ortam kontrolü
   ↓
2. Veritabanı bağlantısı
   ↓
3. init_db.py çalıştır
   ↓
4. Varsayılan admin oluştur
   ↓
5. Varsayılan otel oluştur
   ↓
6. Örnek veriler (opsiyonel)
   ↓
7. Başarı mesajı
```

### ✅ Avantajlar
- Tek komut
- Hızlı kurulum
- Hata yönetimi
- Kullanıcı dostu

### ⚠️ Dezavantajlar
- Varsayılan şifre (admin123)
- Özelleştirme yok

---

## 2️⃣ setup_first_admin.py

### 🎯 Amaç
Özel bilgilerle admin oluşturma.

### ✨ Özellikler
- İnteraktif kullanıcı girişi
- Güvenli şifre girişi (görünmez)
- Şifre tekrar kontrolü
- Email ve telefon (opsiyonel)
- Mevcut admin kontrolü
- Detaylı doğrulama

### 📝 Kullanım
```bash
python setup_first_admin.py
```

### 🔄 İşlem Akışı
```
1. Ortam kontrolü
   ↓
2. Veritabanı bağlantısı
   ↓
3. Tablo kontrolü
   ↓
4. Mevcut admin kontrolü
   ↓
5. Kullanıcı bilgileri al
   ↓
6. Onay al
   ↓
7. Admin oluştur
   ↓
8. Varsayılan otel oluştur
   ↓
9. Başarı mesajı
```

### ✅ Avantajlar
- Özelleştirilebilir
- Güvenli şifre
- Detaylı kontroller
- Profesyonel

### ⚠️ Dezavantajlar
- Manuel giriş gerekli
- Daha uzun sürer

---

## 3️⃣ init_db.py

### 🎯 Amaç
Sadece veritabanı ve tabloları oluşturur.

### ✨ Özellikler
- Veritabanı oluşturma
- 25 tablo oluşturma
- Migration desteği
- Doğrulama

### 📝 Kullanım
```bash
python init_db.py
```

### 🔄 İşlem Akışı
```
1. MySQL'e bağlan
   ↓
2. Veritabanı oluştur
   ↓
3. Tabloları oluştur
   ↓
4. Migration çalıştır
   ↓
5. Doğrulama
   ↓
6. Başarı mesajı
```

### ✅ Avantajlar
- Sadece veritabanı
- Hızlı
- Basit

### ⚠️ Dezavantajlar
- Admin oluşturmaz
- Ek adım gerekli

---

## 4️⃣ kurulum.bat (Windows)

### 🎯 Amaç
Windows için tek tıkla kurulum.

### ✨ Özellikler
- Batch dosyası
- Türkçe karakter desteği
- quick_setup.py çalıştırır
- Hata kontrolü
- Kullanıcı dostu mesajlar

### 📝 Kullanım
```cmd
kurulum.bat
```

veya dosyaya çift tıklayın.

### ✅ Avantajlar
- Çift tıkla çalışır
- Windows entegrasyonu
- Kolay kullanım

---

## 5️⃣ kurulum.sh (Linux/Mac)

### 🎯 Amaç
Linux/Mac için tek komut kurulum.

### ✨ Özellikler
- Shell script
- quick_setup.py çalıştırır
- Hata kontrolü
- Kullanıcı dostu mesajlar

### 📝 Kullanım
```bash
chmod +x kurulum.sh
./kurulum.sh
```

### ✅ Avantajlar
- Unix/Linux uyumlu
- Kolay kullanım
- Otomatik

---

## 🔄 Kurulum Senaryoları

### Senaryo 1: Yeni Sistem (Hızlı)
```bash
# En hızlı yol
python quick_setup.py

# veya Windows
kurulum.bat

# veya Linux/Mac
./kurulum.sh
```

**Sonuç:**
- Varsayılan admin: admin/admin123
- Varsayılan otel
- Örnek veriler (opsiyonel)

---

### Senaryo 2: Yeni Sistem (Özel)
```bash
# Adım 1: Veritabanı
python init_db.py

# Adım 2: Özel admin
python setup_first_admin.py
```

**Sonuç:**
- Kendi admin bilgileriniz
- Güvenli şifre
- Özelleştirilmiş

---

### Senaryo 3: Sadece Veritabanı
```bash
# Sadece tablolar
python init_db.py
```

**Sonuç:**
- Boş veritabanı
- 25 tablo
- Admin yok (manuel ekleme gerekli)

---

### Senaryo 4: Mevcut Sisteme Admin Ekle
```bash
# Yeni admin ekle
python setup_first_admin.py
```

**Sonuç:**
- Ek admin oluşturulur
- Mevcut veriler korunur

---

## 📊 Karşılaştırma Tablosu

| Özellik | quick_setup | setup_first_admin | init_db |
|---------|-------------|-------------------|---------|
| Veritabanı oluşturur | ✅ | ❌ | ✅ |
| Tabloları oluşturur | ✅ | ❌ | ✅ |
| Admin oluşturur | ✅ | ✅ | ❌ |
| Otel oluşturur | ✅ | ✅ | ❌ |
| Örnek veriler | ✅ | ❌ | ❌ |
| Özelleştirilebilir | ❌ | ✅ | ❌ |
| Hız | ⚡⚡⚡ | ⚡⚡ | ⚡⚡⚡ |
| Kullanım kolaylığı | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## 🔒 Güvenlik Notları

### Varsayılan Şifre
```
Kullanıcı: admin
Şifre: admin123
```

⚠️ **ÖNEMLİ:**
- İlk girişten sonra mutlaka değiştirin!
- Production ortamında kullanmayın!
- Güçlü şifre belirleyin!

### Güçlü Şifre Örnekleri
```
❌ Zayıf: 123456, admin, password
✅ Güçlü: Mk@9xP2#vL5q, Admin2024!Secure
```

---

## 🐛 Sorun Giderme

### Hata: "Veritabanı bağlantısı kurulamadı"

**Çözüm:**
```bash
# .env dosyasını kontrol et
cat .env

# Veritabanı servisini kontrol et
# PostgreSQL
pg_isready

# MySQL
mysqladmin ping
```

### Hata: "Tablolar bulunamadı"

**Çözüm:**
```bash
# Önce tabloları oluştur
python init_db.py
```

### Hata: "Admin zaten mevcut"

**Çözüm:**
Script size seçenek sunar:
- Yeni admin oluşturmaya devam et
- İşlemi iptal et

### Hata: "ModuleNotFoundError"

**Çözüm:**
```bash
# Bağımlılıkları yükle
pip install -r requirements.txt
```

---

## 📖 Ek Kaynaklar

- **Detaylı Kılavuz:** [ILK_KURULUM_REHBERI.md](ILK_KURULUM_REHBERI.md)
- **Hızlı Başlangıç:** [KURULUM_HIZLI_BASLANGIC.md](KURULUM_HIZLI_BASLANGIC.md)
- **Ana README:** [README.md](README.md)

---

## 🎯 Önerilen Kurulum Yolu

### Yeni Kullanıcılar İçin
```bash
# Windows
kurulum.bat

# Linux/Mac
./kurulum.sh
```

### Deneyimli Kullanıcılar İçin
```bash
# Özel admin ile
python setup_first_admin.py
```

### Geliştiriciler İçin
```bash
# Manuel kontrol
python init_db.py
python setup_first_admin.py
```

---

**🚀 Başarılı kurulumlar!**
