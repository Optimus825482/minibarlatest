# 🏨 Otel Minibar Takip Sistemi - Genel Bakış

## 📌 Sistem Özeti
Flask tabanlı, PostgreSQL/MySQL destekli profesyonel otel minibar yönetim sistemi. Rol bazlı yetkilendirme, stok takibi, zimmet yönetimi, QR kod entegrasyonu ve ML anomali tespiti içerir.

---

## 🎯 Temel Özellikler

### 1. **Rol Bazlı Yetkilendirme**
- **Sistem Yöneticisi**: Otel tanımlama, admin atama, sistem yönetimi
- **Admin**: Ürün/personel yönetimi, raporlar, minibar sıfırlama
- **Depo Sorumlusu**: Stok giriş/çıkış, zimmet yönetimi, minibar takibi
- **Kat Sorumlusu**: Minibar dolum/kontrol, zimmet kullanımı

### 2. **Stok Yönetimi**
- Depo stok takibi (giriş/çıkış/devir/sayım)
- Kritik stok uyarıları
- Ürün grubu bazlı organizasyon
- Gerçek zamanlı stok hesaplama

### 3. **Zimmet Sistemi**
- Personel bazlı zimmet takibi
- Kullanım ve iade yönetimi
- Kalan miktar kontrolü
- Detaylı zimmet raporları

### 4. **Minibar Yönetimi**
- İlk dolum, yeniden dolum, kontrol
- Oda bazlı tüketim takibi
- QR kod ile hızlı erişim
- Misafir dolum talepleri

### 5. **QR Kod Sistemi**
- Oda bazlı QR kodlar
- Kat sorumlusu hızlı erişim
- Misafir dolum talebi
- Okutma logları

### 6. **Doluluk Yönetimi**
- Excel ile toplu veri yükleme (In-House/Arrivals)
- Otomatik oda doluluk takibi
- Tarih bazlı misafir kayıtları
- Dosya yükleme geçmişi

### 7. **ML Anomali Tespiti**
- Stok seviye anomalileri
- Tüketim pattern analizi
- Dolum süresi tahminleri
- Otomatik uyarı sistemi

### 8. **Raporlama**
- Stok durum/hareket raporları
- Zimmet raporları
- Minibar tüketim analizi
- Excel/PDF export

---

## 🏗️ Teknik Mimari

### **Backend**
- **Framework**: Flask 3.0
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL (Railway) / MySQL (Local)
- **Auth**: Session-based + CSRF koruması
- **Security**: Rate limiting, secure headers, input validation

### **Frontend**
- **CSS**: Tailwind CSS 3.x
- **Charts**: Chart.js 4.4
- **Icons**: Heroicons
- **QR**: qrcode[pil] library

### **Database Yapısı**
```
📊 Ana Tablolar:
├── oteller (Otel bilgileri)
├── kullanicilar (Tüm roller)
├── kullanici_otel (Depo sorumlusu-otel ilişkisi)
├── katlar, odalar
├── urun_gruplari, urunler
├── stok_hareketleri
├── personel_zimmet, personel_zimmet_detay
├── minibar_islemleri, minibar_islem_detay
├── minibar_dolum_talepleri
├── misafir_kayitlari (Doluluk yönetimi)
├── dosya_yuklemeleri (Excel upload)
├── qr_kod_okutma_loglari
├── ml_metrics, ml_models, ml_alerts (ML sistemi)
├── audit_logs (Denetim izi)
├── sistem_loglari, hata_loglari
└── otomatik_raporlar
```

### **Modüler Route Yapısı**
```
routes/
├── __init__.py (Merkezi registration)
├── auth_routes.py (Login/logout/setup)
├── dashboard_routes.py (Rol bazlı dashboard)
├── sistem_yoneticisi_routes.py
├── admin_routes.py (Ürün/personel)
├── admin_user_routes.py (Kullanıcı yönetimi)
├── admin_minibar_routes.py (Minibar yönetimi)
├── admin_stok_routes.py (Stok yönetimi)
├── admin_zimmet_routes.py (Zimmet yönetimi)
├── admin_qr_routes.py (QR yönetimi)
├── depo_routes.py (Depo sorumlusu)
├── kat_sorumlusu_routes.py
├── kat_sorumlusu_ilk_dolum_routes.py
├── kat_sorumlusu_qr_routes.py
├── misafir_qr_routes.py
├── dolum_talebi_routes.py
├── doluluk_routes.py (Excel upload)
├── rapor_routes.py (Raporlama)
├── ml_routes.py (ML sistemi)
├── api_routes.py (REST API)
├── health_routes.py (Health check)
└── error_handlers.py
```

---

## 🔐 Güvenlik Özellikleri

### **Authentication & Authorization**
- Session-based authentication
- Rol bazlı erişim kontrolü (@role_required)
- Şifre hashleme (Werkzeug)
- CSRF token koruması (Flask-WTF)

### **Security Headers**
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection
- Content-Security-Policy
- Strict-Transport-Security (HTTPS)

### **Input Validation**
- WTForms validation
- SQL injection koruması (SQLAlchemy ORM)
- XSS koruması (Bleach)
- File upload restrictions (16MB, sadece xlsx/xls/pdf)

### **Audit Trail**
- Tüm CRUD işlemleri loglanır
- Login/logout kayıtları
- IP adresi ve user agent tracking
- Değişiklik geçmişi (eski/yeni değer)

---

## 📊 İş Akışları

### **1. Stok Yönetimi Akışı**
```
Depo Giriş → Stok Hareketi Kaydı → Zimmet Oluşturma → 
Kat Sorumlusu Kullanımı → Minibar Dolumu → Tüketim Takibi
```

### **2. Minibar Dolum Akışı**
```
İlk Dolum (Kat Sorumlusu) → Misafir Girişi → 
Tüketim → Kontrol/Doldurma → Zimmet Güncelleme → 
Stok Hareketi
```

### **3. QR Kod Akışı**
```
Admin QR Oluşturma → Oda QR Yazdırma → 
Kat Sorumlusu/Misafir Okutma → Hızlı Erişim/Talep
```

### **4. Doluluk Yönetimi Akışı**
```
Excel Hazırlama (In-House/Arrivals) → Upload → 
Otomatik Parse → Misafir Kayıt → Oda Doluluk Takibi
```

---

## 🚀 Deployment

### **Railway (Production)**
- PostgreSQL database
- Gunicorn WSGI server
- Environment variables (.env.railway)
- Automatic migrations (init_db.py)
- Health check endpoint (/health)

### **Docker (Local/Dev)**
- docker-compose.yml
- MySQL container
- Flask app container
- Volume persistence
- Tek komut setup (docker.bat)

### **Local Development**
- Virtual environment
- .env configuration
- Flask development server
- MySQL/PostgreSQL local

---

## 📈 Performans Optimizasyonları

### **Database**
- Connection pooling (pool_size=1, max_overflow=2)
- Pool pre-ping (health check)
- Query retry mekanizması (3 deneme)
- Index'ler (oda_id, tarih, kullanici_id)
- Eager loading (relationship lazy loading)

### **Caching**
- Stok toplamları tek sorguda (get_stok_toplamlari)
- Session-based user caching
- Static file caching

### **Frontend**
- Tailwind CSS (minimal CSS)
- Chart.js lazy loading
- AJAX ile partial updates
- Debounced search inputs

---

## 🧪 Test Yapısı

```
tests/
├── test_config.py (Konfigürasyon testleri)
├── test_models.py (Model testleri)
├── test_routes.py (Route testleri)
├── test_auth.py (Authentication testleri)
├── test_stok.py (Stok yönetimi testleri)
├── test_zimmet.py (Zimmet testleri)
├── test_minibar.py (Minibar testleri)
└── test_ml.py (ML sistemi testleri)
```

**Test Araçları**: pytest, pytest-flask, pytest-cov, factory-boy, faker

---

## 📝 Önemli Dosyalar

### **Konfigürasyon**
- `.env` - Environment variables
- `config.py` - Flask configuration
- `alembic.ini` - Database migrations
- `docker-compose.yml` - Docker setup
- `railway.json` - Railway deployment

### **Ana Dosyalar**
- `app.py` - Flask application bootstrap
- `models.py` - SQLAlchemy models (779 satır)
- `forms.py` - WTForms definitions
- `requirements.txt` - Python dependencies

### **Utility Modülleri**
- `utils/helpers.py` - Helper functions
- `utils/decorators.py` - Custom decorators
- `utils/audit.py` - Audit trail
- `utils/authorization.py` - Authorization helpers

### **Scripts**
- `init_db.py` - Database initialization
- `backup_database.py` - Database backup
- `add_local_superadmin.py` - Superadmin creation
- `railway_health_check.py` - Health check

---

## 🔧 Bakım ve Yönetim

### **Database Backup**
```bash
python backup_database.py  # Local
python backup_database_docker.py  # Docker
```

### **Sistem Sıfırlama**
- URL: `/resetsystem`
- Şifre: `518518Erkan!`
- Tüm verileri siler, ilk kuruluma döner

### **Log Yönetimi**
- `minibar_errors.log` - Hata logları
- `sistem_loglari` tablosu - İşlem logları
- `hata_loglari` tablosu - Exception logları
- `audit_logs` tablosu - Denetim izi

### **Health Check**
- Endpoint: `/health`
- Database connection check
- Uptime tracking
- JSON response

---

## 📚 Dokümantasyon

```
docs/
├── README.md (Dokümantasyon indeksi)
├── KULLANIM_KLAVUZU_BOLUM_1.md (Kurulum)
├── KULLANIM_KLAVUZU_BOLUM_2.md (Kullanım)
├── KULLANIM_KLAVUZU_BOLUM_3.md (Yönetim)
├── akis_sema.md (14 akış diyagramı)
├── SISTEM_SIFIRLAMA_KILAVUZU.md
├── refactoring_report.md (Modüler yapı)
└── ... (daha fazla)
```

---

## 🎨 UI/UX Özellikleri

- **Responsive Design**: Mobil/tablet/desktop uyumlu
- **Dark Mode**: Tailwind dark mode desteği
- **Real-time Updates**: AJAX ile canlı veri
- **Toast Notifications**: Flash messages
- **Loading States**: Spinner ve skeleton screens
- **Form Validation**: Client + server-side
- **Accessibility**: ARIA labels, keyboard navigation

---

## 🔮 Gelecek Özellikler (Roadmap)

- [ ] Multi-tenant support (çoklu otel)
- [ ] Mobile app (React Native)
- [ ] Real-time notifications (WebSocket)
- [ ] Advanced analytics dashboard
- [ ] Automated reporting (email/PDF)
- [ ] Integration APIs (PMS systems)
- [ ] Barcode scanning
- [ ] Invoice generation

---

## 📞 Teknik Destek

- **Hata Logları**: `minibar_errors.log`
- **Database Logs**: `sistem_loglari`, `hata_loglari`
- **Health Check**: `/health` endpoint
- **Debug Mode**: `FLASK_ENV=development`

---

## 📊 Sistem İstatistikleri

- **Toplam Satır**: ~15,000+ (tüm proje)
- **Route Sayısı**: 100+ endpoint
- **Model Sayısı**: 20+ tablo
- **Test Coverage**: %80+ (hedef)
- **Deployment**: Railway (production), Docker (local)

---

**Son Güncelleme**: 2025-01-09  
**Versiyon**: 2.0 (Modüler Yapı + ML + Doluluk Yönetimi)  
**Geliştirici**: Erkan için özel sistem
