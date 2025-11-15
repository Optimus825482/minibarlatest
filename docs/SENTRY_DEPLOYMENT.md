# Sentry Deployment Rehberi

## 🎯 Genel Bakış

Bu projede iki Sentry deployment var:

1. **Sentry Server** (Self-hosted) - Kendi sunucunda
2. **Uygulama Sentry Entegrasyonu** - Her deploy'da release tracking

---

## 📦 1. Sentry Server Kurulumu (Self-Hosted)

### Gereksinimler

- Docker & Docker Compose
- En az 4GB RAM
- 20GB disk alanı
- Domain (opsiyonel ama önerilen)

### Kurulum Adımları

```bash
# Script'i çalıştırılabilir yap
chmod +x scripts/deploy_sentry_server.sh

# Kurulumu başlat
./scripts/deploy_sentry_server.sh
```

### Manuel Kurulum

```bash
# Dizin oluştur
mkdir -p ~/sentry-data
cd ~/sentry-data

# Sentry self-hosted'ı indir
git clone https://github.com/getsentry/self-hosted.git
cd self-hosted

# Kurulum
./install.sh

# Başlat
docker-compose up -d
```

### Coolify ile Deploy

1. Coolify'da **New Resource** → **Docker Compose**
2. Repository: `~/sentry-data/self-hosted`
3. Compose file: `docker-compose.yml`
4. Domain ayarla: `sentry.yourdomain.com`
5. SSL ekle (Let's Encrypt)
6. Deploy!

### İlk Ayarlar

1. Sentry'ye giriş yap: `http://sentry.yourdomain.com`
2. Organization oluştur: `erkan-mm`
3. Project oluştur: `python-flask`
4. **Settings** → **Developer Settings** → **Internal Integrations**
5. Yeni integration oluştur:
   - Name: `Python Flask Release Integration`
   - Permissions: `Releases: Admin`, `Organization: Read`
6. Auth Token'ı kopyala

---

## 🚀 2. Uygulama Sentry Entegrasyonu

### Environment Variables

Coolify'da veya `.env` dosyasında:

```bash
# Sentry Configuration
SENTRY_DSN=https://your-dsn@sentry.yourdomain.com/1
SENTRY_AUTH_TOKEN=ccc0e94734513a126fd2a36c040ba968a83b31b450730ac76aea4fcbc55c0f33
SENTRY_ORG=erkan-mm
SENTRY_PROJECT=python-flask
SENTRY_ENVIRONMENT=production
```

### Release Script Kullanımı

```bash
# Script'i çalıştırılabilir yap
chmod +x scripts/sentry_release.sh

# Her deploy'da çalıştır
./scripts/sentry_release.sh
```

### Coolify Post-Deploy Hook

Coolify'da **Settings** → **Post Deployment Command**:

```bash
chmod +x scripts/sentry_release.sh && ./scripts/sentry_release.sh
```

---

## 🔧 3. Dockerfile Entegrasyonu (Opsiyonel)

Eğer build sırasında release oluşturmak istersen:

```dockerfile
# Dockerfile.coolify sonuna ekle
RUN curl -sL https://sentry.io/get-cli/ | bash

# Build args
ARG SENTRY_AUTH_TOKEN
ARG SENTRY_ORG=erkan-mm
ARG SENTRY_PROJECT=python-flask

# Release oluştur
RUN if [ -n "$SENTRY_AUTH_TOKEN" ]; then \
    VERSION=$(date +%Y%m%d-%H%M%S) && \
    sentry-cli releases new "$VERSION" && \
    sentry-cli releases finalize "$VERSION"; \
    fi
```

---

## 📊 4. Monitoring & Alerts

### Sentry'de Ayarlar

1. **Alerts** → **Create Alert Rule**
2. Koşullar:
   - Error rate > 10/dakika
   - Response time > 2 saniye
   - Yeni error tipi
3. Bildirim kanalları:
   - Email
   - Slack (opsiyonel)
   - Discord (opsiyonel)

### Performance Monitoring

```python
# app.py'de zaten var
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,  # Production'da 0.1 yap
    profiles_sample_rate=1.0,
    environment=os.getenv('SENTRY_ENVIRONMENT', 'production')
)
```

---

## 🔍 5. Troubleshooting

### Sentry CLI Kurulum Hatası

```bash
# Manuel kurulum
curl -sL https://sentry.io/get-cli/ | bash

# Veya
pip install sentry-cli
```

### Auth Token Hatası

```bash
# Token'ı test et
export SENTRY_AUTH_TOKEN=your-token
sentry-cli info
```

### Release Oluşturulamıyor

```bash
# Debug mode
export SENTRY_LOG_LEVEL=debug
./scripts/sentry_release.sh
```

### Docker Compose Hatası

```bash
# Logları kontrol et
cd ~/sentry-data/self-hosted
docker-compose logs -f

# Yeniden başlat
docker-compose down
docker-compose up -d
```

---

## 📝 6. Best Practices

### Production Ayarları

1. **Traces Sample Rate**: `0.1` (10% sampling)
2. **Profiles Sample Rate**: `0.1`
3. **Data Retention**: 90 gün
4. **Rate Limiting**: Aktif
5. **IP Filtering**: Sadece sunucu IP'leri

### Güvenlik

- Auth token'ı `.env` dosyasında tut
- `.env` dosyasını `.gitignore`'a ekle
- Sentry admin paneline sadece güvenli IP'lerden erişim
- SSL/TLS zorunlu
- 2FA aktif

### Backup

```bash
# Sentry veritabanı backup
cd ~/sentry-data/self-hosted
docker-compose exec postgres pg_dump -U postgres > backup.sql

# Restore
docker-compose exec -T postgres psql -U postgres < backup.sql
```

---

## 🎉 Tamamlandı!

Artık:

- ✅ Kendi Sentry sunucun çalışıyor
- ✅ Her deploy'da otomatik release tracking
- ✅ Error monitoring aktif
- ✅ Performance tracking aktif

**Sentry Dashboard**: `http://sentry.yourdomain.com`
