# Coolify Deployment Guide - ML Model File System

## Genel Bakış

Bu guide, ML model dosya sistemi ile Coolify deployment sürecini açıklar.

**Önemli**: ML modelleri artık dosya sisteminde saklanıyor. Persistent volume gereklidir!

## Persistent Volume Konfigürasyonu

### 1. Coolify Dashboard'da Volume Oluşturma

1. **Coolify Dashboard** → **Resources** → **Volumes**
2. **Create Volume** butonuna tıkla
3. Volume bilgileri:
   - **Name**: `minibar-ml-models`
   - **Driver**: `local`
   - **Mount Path**: `/app/ml_models`

### 2. Volume'u Service'e Bağlama

1. **Services** → **minibar-app** → **Volumes**
2. **Add Volume** butonuna tıkla
3. Volume mapping:
   ```
   Source: minibar-ml-models
   Destination: /app/ml_models
   ```

### 3. Environment Variables

Coolify dashboard'da şu environment variable'ları ekle:

```bash
# ML Model Configuration
ML_ENABLED=true
ML_MODELS_DIR=/app/ml_models
ML_DATA_COLLECTION_INTERVAL=900
ML_ANOMALY_CHECK_INTERVAL=3600
ML_TRAINING_SCHEDULE=0 0 * * *

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Flask
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# Gunicorn
GUNICORN_WORKERS=2
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=120
```

## Deployment Adımları

### 1. GitHub'a Push

```bash
git add .
git commit -m "feat: ML model file system with persistent volume"
git push origin main
```

### 2. Coolify Auto-Deploy

Coolify otomatik olarak yeni commit'i algılar ve deploy eder.

**Deploy süreci**:

1. ✅ GitHub'dan kod çeker
2. ✅ Docker image build eder
3. ✅ Container'ı başlatır
4. ✅ Health check yapar
5. ✅ Volume'u mount eder

### 3. Migration Çalıştırma

Deploy tamamlandıktan sonra, SSH ile container'a bağlan:

```bash
# Coolify dashboard'dan SSH terminal aç veya:
docker exec -it <container_id> bash

# Database migration
flask db upgrade

# ML model migration (dry-run test)
python migrate_models_to_filesystem.py --dry-run

# Gerçek migration
python migrate_models_to_filesystem.py
```

### 4. Verification

```bash
# Volume mount kontrolü
ls -lh /app/ml_models/

# Permissions kontrolü
ls -la /app/ml_models/

# Model dosyaları kontrolü
find /app/ml_models -name "*.pkl" -type f

# Disk kullanımı
df -h /app/ml_models

# Database kontrolü
psql $DATABASE_URL -c "SELECT model_type, metric_type, model_path IS NOT NULL as has_path FROM ml_models WHERE is_active=true;"
```

## Docker Compose Konfigürasyonu

### docker-compose.coolify.yml

```yaml
version: "3.8"

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      ML_MODELS_DIR: /app/ml_models
      # ... diğer env vars
    volumes:
      - ml_models:/app/ml_models
      - ./uploads:/app/uploads
      - ./backups:/app/backups
    networks:
      - minibar_network

volumes:
  ml_models:
    driver: local

networks:
  minibar_network:
    driver: bridge
```

## Dockerfile Değişiklikleri

```dockerfile
# ML models dizini oluştur
RUN mkdir -p /app/ml_models && \
    chmod 755 /app/ml_models

# Volume tanımla
VOLUME ["/app/ml_models"]
```

## Troubleshooting

### Problem: Volume mount edilmedi

**Kontrol**:

```bash
docker inspect <container_id> | grep -A 10 Mounts
```

**Çözüm**:

1. Coolify dashboard → Volumes → Verify mount path
2. Container'ı restart et
3. Volume'u yeniden oluştur

### Problem: Permission denied

**Kontrol**:

```bash
ls -la /app/ml_models/
```

**Çözüm**:

```bash
# Container içinde
chmod 755 /app/ml_models
chown -R appuser:appuser /app/ml_models
```

### Problem: Model dosyaları kayboldu

**Sebep**: Volume persistent değil veya yanlış mount edilmiş.

**Çözüm**:

1. Backup'tan restore et:

   ```bash
   # Backup dizininden modelleri kopyala
   cp /app/backups/ml_models/*.pkl /app/ml_models/
   ```

2. Veritabanından migrate et:
   ```bash
   python migrate_models_to_filesystem.py
   ```

### Problem: Disk dolu

**Kontrol**:

```bash
df -h /app/ml_models
du -sh /app/ml_models/*
```

**Çözüm**:

```bash
# Eski modelleri temizle
python -c "from app import app, db; from utils.ml.model_manager import ModelManager; \
with app.app_context(): ModelManager(db).cleanup_old_models(keep_versions=1)"

# Manuel temizlik
find /app/ml_models -name "*.pkl" -mtime +30 -delete
```

## Monitoring

### Health Check

Coolify otomatik health check yapar:

```bash
curl http://localhost:5000/health
```

**Beklenen response**:

```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-11-12T14:30:00Z"
}
```

### Logs

```bash
# Coolify dashboard'dan logs görüntüle veya:
docker logs -f <container_id>

# ML scheduler logs
docker logs <container_id> | grep "ML Scheduler"

# Model cleanup logs
docker logs <container_id> | grep "Model cleanup"
```

### Metrics

```bash
# Disk kullanımı
docker exec <container_id> df -h /app/ml_models

# Model sayısı
docker exec <container_id> find /app/ml_models -name "*.pkl" | wc -l

# Toplam boyut
docker exec <container_id> du -sh /app/ml_models
```

## Backup ve Restore

### Backup

```bash
# Volume backup (Coolify dashboard'dan)
# veya manuel:
docker run --rm -v minibar-ml-models:/data -v $(pwd):/backup \
  alpine tar czf /backup/ml_models_backup_$(date +%Y%m%d).tar.gz -C /data .
```

### Restore

```bash
# Volume restore
docker run --rm -v minibar-ml-models:/data -v $(pwd):/backup \
  alpine tar xzf /backup/ml_models_backup_20251112.tar.gz -C /data
```

## Performance Optimization

### Volume Driver

Local driver yeterli. Daha yüksek performans için:

```yaml
volumes:
  ml_models:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /mnt/fast-ssd/ml_models
```

### Disk Space Management

Otomatik cleanup scheduler (her gece 04:00):

- Son 3 model versiyonu saklanır
- 30 günden eski inactive modeller silinir
- Disk %90+ ise kritik alert

## Security

### File Permissions

```bash
# Dizin: 755 (rwxr-xr-x)
chmod 755 /app/ml_models

# Dosyalar: 644 (rw-r--r--)
chmod 644 /app/ml_models/*.pkl

# Owner: appuser
chown -R appuser:appuser /app/ml_models
```

### Path Validation

ModelManager otomatik path validation yapar:

- Path traversal koruması
- Sadece `/app/ml_models/` içinde işlem
- Güvenli dosya adları

## Rollback Plan

### Deployment Rollback

```bash
# Coolify dashboard → Deployments → Previous version → Rollback
```

### Model Migration Rollback

```bash
# Container içinde
python migrate_models_to_filesystem.py --rollback
```

### Volume Rollback

```bash
# Backup'tan restore
docker run --rm -v minibar-ml-models:/data -v $(pwd):/backup \
  alpine tar xzf /backup/ml_models_backup_YYYYMMDD.tar.gz -C /data
```

## Success Criteria

Deployment başarılı sayılır:

- ✅ Container healthy
- ✅ Volume mount edildi (`/app/ml_models`)
- ✅ Model dosyaları erişilebilir
- ✅ Database migration tamamlandı
- ✅ ML scheduler çalışıyor
- ✅ Health check geçiyor
- ✅ Logs'da hata yok

## Checklist

### Pre-Deployment

- [ ] GitHub'a push edildi
- [ ] Dockerfile güncel
- [ ] docker-compose.yml güncel
- [ ] Environment variables ayarlandı
- [ ] Volume oluşturuldu

### Deployment

- [ ] Coolify auto-deploy başarılı
- [ ] Container başladı
- [ ] Health check geçti
- [ ] Volume mount edildi

### Post-Deployment

- [ ] Database migration çalıştırıldı
- [ ] Model migration çalıştırıldı (dry-run → gerçek)
- [ ] Model dosyaları kontrol edildi
- [ ] Logs kontrol edildi
- [ ] Performance metrikleri kontrol edildi

### Verification

- [ ] `/app/ml_models/` dizini var
- [ ] Model dosyaları `.pkl` formatında
- [ ] Permissions doğru (755/644)
- [ ] Disk kullanımı normal (< 100MB)
- [ ] ML scheduler çalışıyor
- [ ] Anomali tespiti çalışıyor

## Support

Sorun yaşarsanız:

1. **Logs kontrol et**: `docker logs <container_id>`
2. **Health check**: `curl http://localhost:5000/health`
3. **Volume kontrol**: `docker inspect <container_id>`
4. **Migration log**: `cat migration.log`
5. **Rollback**: `python migrate_models_to_filesystem.py --rollback`

---

**Son Güncelleme**: 2025-11-12  
**Versiyon**: 1.0.0  
**Platform**: Coolify  
**Yazar**: Kiro AI
