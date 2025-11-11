# 🚀 İLK KURULUM REHBERİ

Sıfırdan yeni veritabanı kurulumu için adım adım kılavuz.

---

## 📋 İçindekiler

1. [Hızlı Kurulum (Önerilen)](#hizli-kurulum)
2. [Manuel Kurulum](#manuel-kurulum)
3. [Özel Admin Oluşturma](#ozel-admin-olusturma)
4. [Sorun Giderme](#sorun-giderme)

---

## ⚡ Hızlı Kurulum (Önerilen)

Tek komutla her şeyi otomatik kurar:

```bash
python quick_setup.py
```

### Ne Yapar?

✅ Veritabanını oluşturur  
✅ Tüm tabloları oluşturur  
✅ Varsayılan admin oluşturur  
✅ Örnek veriler ekler (opsiyonel)

### Varsayılan Giriş Bilgileri

```
Kullanıcı Adı: admin
Şifre: admin123
```

⚠️ **ÖNEMLİ:** İlk girişten sonra şifrenizi değiştirin!

---

## 🔧 Manuel Kurulum

Adım adım kontrollü kurulum:

### 1. Veritabanı ve Tabloları Oluştur

```bash
python init_db.py
```

**Çıktı:**
```
📡 MySQL sunucusuna bağlanılıyor...
🗄️  Veritabanı kontrol ediliyor: minibar_takip
✅ Veritabanı hazır: minibar_takip
📊 Tablolar oluşturuluyor...
✅ Toplam 25 tablo oluşturuldu
```

### 2. İlk Admin Oluştur

```bash
python setup_first_admin.py
```

**İnteraktif Kurulum:**
```
👤 YENİ SİSTEM YÖNETİCİSİ BİLGİLERİ
====================================

📝 Kullanıcı Adı (min 3 karakter): erkan
📝 Ad: Erkan
📝 Soyad: Yılmaz
📧 Email (opsiyonel): erkan@otel.com
📞 Telefon (opsiyonel): 
🔒 Şifre (min 6 karakter): ******
🔒 Şifre Tekrar: ******
```

---

## 👤 Özel Admin Oluşturma

Kendi bilgilerinizle admin oluşturmak için:

```bash
python setup_first_admin.py
```

### Özellikler

✅ Güvenli şifre girişi (görünmez)  
✅ Şifre tekrar kontrolü  
✅ Email ve telefon (opsiyonel)  
✅ Mevcut admin kontrolü  
✅ Detaylı hata yönetimi

### Örnek Kullanım

```bash
$ python setup_first_admin.py

🚀 OTEL MİNİBAR TAKİP SİSTEMİ
   İLK KURULUM - SİSTEM YÖNETİCİSİ OLUŞTURMA
============================================

🔍 Ortam kontrol ediliyor...
✅ DATABASE_URL bulundu
   Tip: postgresql

📡 Veritabanı bağlantısı test ediliyor...
✅ Veritabanı bağlantısı başarılı

📊 Tablolar kontrol ediliyor...
✅ 25 tablo bulundu

👤 YENİ SİSTEM YÖNETİCİSİ BİLGİLERİ
====================================

📝 Kullanıcı Adı (min 3 karakter): admin
📝 Ad: Sistem
📝 Soyad: Yöneticisi
📧 Email (opsiyonel): admin@otel.com
📞 Telefon (opsiyonel): 
🔒 Şifre (min 6 karakter): 
🔒 Şifre Tekrar: 

📋 ÖZET:
   Kullanıcı Adı: admin
   Ad Soyad: Sistem Yöneticisi
   Email: admin@otel.com
   Rol: Sistem Yöneticisi

Bu bilgilerle devam edilsin mi? (E/H): E

⏳ Sistem yöneticisi oluşturuluyor...
✅ Sistem yöneticisi başarıyla oluşturuldu!

🏨 Varsayılan otel oluşturuluyor...
✅ Varsayılan otel oluşturuldu

🎉 KURULUM BAŞARIYLA TAMAMLANDI!
```

---

## 🔍 Sorun Giderme

### Hata: "Veritabanı bağlantısı kurulamadı"

**Çözüm:**
1. `.env` dosyasını kontrol edin
2. Veritabanı servisinin çalıştığından emin olun
3. Bağlantı bilgilerini doğrulayın

```bash
# PostgreSQL için
PGHOST=localhost
PGUSER=postgres
PGPASSWORD=your_password
PGDATABASE=minibar_takip
PGPORT=5432

# veya

DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### Hata: "Tablolar bulunamadı"

**Çözüm:**
Önce tabloları oluşturun:

```bash
python init_db.py
```

### Hata: "Admin zaten mevcut"

**Çözüm:**
Script size seçenek sunar:
- Yeni admin oluşturmaya devam et
- İşlemi iptal et

### Hata: "Kullanıcı adı zaten kullanılıyor"

**Çözüm:**
Farklı bir kullanıcı adı seçin.

---

## 📊 Kurulum Sonrası

### 1. Uygulamayı Başlatın

```bash
python app.py
```

### 2. Tarayıcıda Açın

```
http://localhost:5014
```

### 3. Giriş Yapın

Oluşturduğunuz kullanıcı adı ve şifre ile giriş yapın.

### 4. İlk Yapılacaklar

#### a) Şifrenizi Değiştirin
```
Ayarlar > Profil > Şifre Değiştir
```

#### b) Otel Bilgilerini Güncelleyin
```
Ayarlar > Otel Yönetimi > Düzenle
```

Ekleyin:
- Otel adı
- Adres
- Telefon
- Email
- Logo (opsiyonel)

#### c) Kullanıcıları Ekleyin
```
Kullanıcılar > Yeni Kullanıcı
```

Roller:
- **Sistem Yöneticisi:** Tüm yetkilere sahip
- **Admin:** Otel yönetimi
- **Depo Sorumlusu:** Stok yönetimi
- **Kat Sorumlusu:** Minibar işlemleri

#### d) Ürün Grupları ve Ürünleri Tanımlayın
```
Ürünler > Ürün Grupları > Yeni Grup
Ürünler > Ürün Listesi > Yeni Ürün
```

Örnek gruplar:
- İçecekler
- Atıştırmalıklar
- Alkollü İçecekler

#### e) Kat ve Odaları Ekleyin
```
Oteller > Otel Seç > Katlar > Yeni Kat
Katlar > Kat Seç > Odalar > Yeni Oda
```

---

## 🔒 Güvenlik Önerileri

### 1. Güçlü Şifre Kullanın

❌ Zayıf: `123456`, `admin`, `password`  
✅ Güçlü: `Mk@9xP2#vL5q`, `Admin2024!Secure`

### 2. Varsayılan Şifreyi Değiştirin

Hızlı kurulum kullandıysanız:
```
Varsayılan: admin123
→ Mutlaka değiştirin!
```

### 3. Email Adresi Ekleyin

Şifre sıfırlama için gerekli.

### 4. Düzenli Yedekleme

```bash
# Manuel yedekleme
python backup_database.py

# Otomatik yedekleme (cron)
0 2 * * * cd /path/to/app && python backup_database.py
```

---

## 📞 Destek

Sorun yaşıyorsanız:

1. **Log dosyalarını kontrol edin:**
   - `minibar_errors.log`
   - `hata_loglari` tablosu

2. **Veritabanı durumunu kontrol edin:**
   ```bash
   python railway_health_check.py
   ```

3. **Tabloları yeniden oluşturun:**
   ```bash
   # ⚠️ DİKKAT: Tüm veriler silinir!
   python init_db.py
   ```

---

## 🎯 Özet

### Hızlı Kurulum (1 Komut)
```bash
python quick_setup.py
```

### Manuel Kurulum (2 Komut)
```bash
python init_db.py
python setup_first_admin.py
```

### Özel Kurulum (İnteraktif)
```bash
python setup_first_admin.py
# Kendi bilgilerinizi girin
```

---

## ✅ Kurulum Kontrol Listesi

- [ ] Veritabanı oluşturuldu
- [ ] Tablolar oluşturuldu
- [ ] İlk admin oluşturuldu
- [ ] Uygulama başlatıldı
- [ ] Giriş yapıldı
- [ ] Şifre değiştirildi
- [ ] Otel bilgileri güncellendi
- [ ] Kullanıcılar eklendi
- [ ] Ürünler tanımlandı
- [ ] Kat ve odalar eklendi

---

**🚀 Kurulum tamamlandı! İyi çalışmalar!**
