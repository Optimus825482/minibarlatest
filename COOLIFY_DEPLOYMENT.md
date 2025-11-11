# 🚀 Coolify Deployment Rehberi - Güvenli Kurulum

## ⚠️ ÖNEMLİ: Mevcut Veritabanı Koruması

Bu deployment, **mevcut veritabanınıza DOKUNMAZ**. Tüm verileriniz korunur.

## 📋 Ön Hazırlık

### 1. GitHub Repository Hazırlığı

```bash
# Değişiklikleri commit et
git add .
git commit -m "Coolify deployment hazırlığı - güvenli deployment"
git push origin main
```

### 2. Coolify'da Gerekli Environment Variables

Coolify Dashboard → Service → Environment Variables bölümüne şunları ekle:

```env
# DATABASE (ZORUNLU)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# FLASK (ZORUNLU)
SECRET_KEY=your-32-char-random-secret-key
FLASK_ENV=production

# SESSION SECURITY
SESSION_COOKIE_SECURE=false  # Coolify HTTP kullanıyorsa
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax

# PORT (Coolify otomatik ayarlar)
PORT=5000

# GUNICORN
GUNICORN_WORKERS=2
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=120

# TIMEZONE
TZ=Asia/Nicosia

# ML SYSTEM (Opsiyonel)
ML_ENABLED=true
ML_DATA_COLLECTION_INTERVAL=900
ML_ANOMALY_CHECK_INTERVAL=300
```

## 🔧 Coolify Deployment Adımları

### Adım 1: Yeni Service Oluştur

1. Coolify Dashboard'a git
2. **New Resource** → **Service** seç
3. **GitHub Repository** seç
4. Repository'nizi seçin (minibar-takip-sistemi)
5. Branch: `main`

### Adım 2: Build Configuration

**Build Pack:** Docker

**Dockerfile Path:** `Dockerfile.coolify`

**Build Command:** (Boş bırak, Dockerfile kullanılacak)

**Start Command:** (Boş bırak, Dockerfile'da tanımlı)

### Adım 3: Environment Variables

Yukarıdaki environment variables'ları ekle.

**ÖNEMLİ:** `DATABASE_URL` mevcut veritabanınızın URL'i olmalı!

### Adım 4: Port Configuration

- **Port:** 5000
- **Public Port:** 80 veya 443 (Coolify otomatik ayarlar)

### Adım 5: Deploy

**Deploy** butonuna tıkla.

## 🔍 Deployment Sırasında Ne Olur?

### 1. Güvenli Kontrol (`safe_deploy.py`)

```
✅ Veritabanı bağlantısı kontrol edilir
✅ Mevcut tablolar listelenir
✅ Veriler korunur
✅ Eksik tablolar raporlanır (ama oluşturulmaz!)
```

### 2. Uygulama Başlatılır

```
✅ Gunicorn başlar
✅ Mevcut verilerle çalışır
✅ Hiçbir veri silinmez
```

## 📊 Deployment Sonrası Kontrol

### 1. Logs Kontrolü

Coolify Dashboard → Service → Logs

Şunları görmeli:

```
✅ GÜVENLİ DEPLOYMENT - VERİTABANI KONTROLÜ
✅ Veritabanı bağlantısı başarılı
✅ X tablo bulundu
✅ Veriler korunuyor
✅ GÜVENLİ DEPLOYMENT KONTROLÜ TAMAMLANDI
```

### 2. Uygulama Testi

1. Coolify'ın verdiği URL'i aç
2. Mevcut kullanıcı ile giriş yap
3. Tüm verilerin yerinde olduğunu kontrol et

### 3. Health Check

```bash
curl https://your-app.coolify.io/health
```

Beklenen yanıt:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 🔄 Güncelleme (Re-deployment)

Her yeni deployment'ta:

1. GitHub'a push yap
2. Coolify otomatik deploy eder
3. `safe_deploy.py` tekrar çalışır
4. Veriler korunur ✅

## 🆘 Sorun Giderme

### Deployment Başarısız

**1. Database Connection Error**

```bash
# Coolify Shell'de test et
python -c "from safe_deploy import check_database_connection; check_database_connection()"
```

**Çözüm:**
- `DATABASE_URL` doğru mu kontrol et
- Veritabanı erişilebilir mi kontrol et

**2. Missing Tables**

Eğer eksik tablolar varsa:

```bash
# Coolify Shell'de
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

**3. Port Already in Use**

Coolify otomatik port atar, sorun olmamalı. Eğer olursa:
- Service'i restart et
- Environment variable `PORT` kontrol et

### Logs Görüntüleme

```bash
# Coolify Dashboard → Service → Logs
# veya
# Coolify Shell'de
tail -f /var/log/app.log
```

## 📝 Önemli Notlar

### ✅ Güvenli Deployment Özellikleri

- ✅ Mevcut tablolara dokunmaz
- ✅ Verileri korur
- ✅ Sadece kontrol yapar
- ✅ Eksik tabloları raporlar
- ✅ Otomatik rollback yok (veri kaybı riski yok)

### ⚠️ Dikkat Edilmesi Gerekenler

1. **DATABASE_URL:** Mutlaka mevcut veritabanınızın URL'i olmalı
2. **SECRET_KEY:** Production'da güçlü bir key kullan
3. **SESSION_COOKIE_SECURE:** HTTP kullanıyorsan `false` olmalı
4. **Backup:** Deployment öncesi yine de backup al (güvenlik için)

## 🔐 Güvenlik Kontrol Listesi

- [ ] `SECRET_KEY` güçlü ve benzersiz
- [ ] `DATABASE_URL` doğru
- [ ] `SESSION_COOKIE_SECURE` ortama uygun
- [ ] Environment variables Coolify'da tanımlı
- [ ] Backup alındı (opsiyonel ama önerilen)
- [ ] Health check çalışıyor
- [ ] Logs kontrol edildi

## 📞 Destek

Sorun yaşarsan:

1. Coolify Logs'u kontrol et
2. `safe_deploy.py` çıktısını incele
3. Database bağlantısını test et
4. Environment variables'ları doğrula

## 🎉 Başarılı Deployment

Eğer şunları görüyorsan, deployment başarılı:

```
✅ Veritabanı bağlantısı başarılı
✅ X tablo bulundu
✅ Veriler korunuyor
✅ GÜVENLİ DEPLOYMENT KONTROLÜ TAMAMLANDI
✅ Gunicorn started
```

Tebrikler! Uygulamanız Coolify'da çalışıyor ve tüm verileriniz korundu! 🚀
