# ⚡ HIZLI BAŞLANGIÇ - İLK KURULUM

Sıfırdan sistem kurulumu için en hızlı yol.

---

## 🎯 Tek Komut Kurulum

```bash
python quick_setup.py
```

Bu kadar! 🎉

---

## 📋 Ne Yapar?

1. ✅ Veritabanını oluşturur
2. ✅ Tüm tabloları oluşturur (25 tablo)
3. ✅ Varsayılan admin oluşturur
4. ✅ Varsayılan otel oluşturur
5. ✅ Örnek veriler ekler (opsiyonel)

---

## 🔑 Varsayılan Giriş

```
Kullanıcı Adı: admin
Şifre: admin123
```

⚠️ **İlk girişten sonra şifrenizi değiştirin!**

---

## 🚀 Başlatma

```bash
# Kurulum
python quick_setup.py

# Uygulama başlat
python app.py

# Tarayıcıda aç
http://localhost:5014
```

---

## 🎨 Alternatif: Özel Admin

Kendi bilgilerinizle admin oluşturmak için:

```bash
python setup_first_admin.py
```

İnteraktif olarak sorar:
- Kullanıcı adı
- Ad / Soyad
- Email (opsiyonel)
- Telefon (opsiyonel)
- Şifre (güvenli giriş)

---

## 📖 Detaylı Kılavuz

Daha fazla bilgi için:

```
ILK_KURULUM_REHBERI.md
```

---

## ⚠️ Sorun mu Yaşıyorsun?

### Veritabanı bağlantı hatası?

`.env` dosyasını kontrol et:

```env
# PostgreSQL
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# veya

PGHOST=localhost
PGUSER=postgres
PGPASSWORD=your_password
PGDATABASE=minibar_takip
```

### Tablolar yok?

```bash
python init_db.py
```

### Admin zaten var?

Script size sorar, devam edebilirsiniz.

---

## 🎯 Kurulum Sonrası

1. **Şifre değiştir** (Ayarlar > Profil)
2. **Otel bilgilerini güncelle** (Ayarlar > Otel)
3. **Kullanıcıları ekle** (Kullanıcılar)
4. **Ürünleri tanımla** (Ürünler)
5. **Kat ve odaları ekle** (Oteller)

---

**🚀 Hepsi bu kadar! İyi çalışmalar!**
