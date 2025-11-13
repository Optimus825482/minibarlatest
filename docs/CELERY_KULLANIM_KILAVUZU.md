# Celery Asenkron İşlemler Kullanım Kılavuzu

## Genel Bakış

Celery, fiyatlandırma ve karlılık sistemi için ağır hesaplamaları arka planda çalıştıran asenkron task yönetim sistemidir. Bu sayede kullanıcı arayüzü donmadan, uzun süren işlemler arka planda tamamlanır.

## Mimari

```
┌─────────────────┐
│  Flask App      │
│  (API)          │
└────────┬────────┘
         │
         ↓
┌─────────────────┐      ┌─────────────────┐
│  Redis Broker   │◄────►│  Celery Worker  │
│  (Queue)        │      │  (Task Runner)  │
└─────────────────┘      └─────────────────┘
         ↑
         │
┌─────────────────┐
│  Celery Beat    │
│  (Scheduler)    │
└─────────────────┘
```

## Kurulum

### 1. Gereksinimler

```bash
# requirements.txt'de zaten mevcut
celery==5.3.4
redis==5.0.1
```

### 2. Redis Kurulumu

**Windows:**

```bash
# Redis Windows için:
# https://github.com/microsoftarchive/redis/releases
# İndirip çalıştırın
redis-server
```

**Linux/Mac:**

```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Mac
brew install redis
brew services start redis
```

### 3. Ortam Değişkenleri

`.env` dosyasına ekleyin:

```env
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

## Celery Başlatma

### Worker Başlatma

**Windows:**

```bash
start_celery_worker.bat
```

**Linux/Mac:**

```bash
chmod +x start_celery_worker.sh
./start_celery_worker.sh
```

**Manuel:**

```bash
celery -A celery_app worker --loglevel=info --pool=solo
```

### Beat Başlatma (Periyodik Task'lar için)

**Windows:**

```bash
start_celery_beat.bat
```

**Linux/Mac:**

```bash
chmod +x start_celery_beat.sh
./start_celery_beat.sh
```

**Manuel:**

```bash
celery -A celery_app beat --loglevel=info
```

## Asenkron Task'lar

### 1. Dönemsel Kar Hesaplama

Belirli bir tarih aralığı için kar analizi yapar.

**API Endpoint:**

```http
POST /api/v1/celery/task/donemsel-kar
Content-Type: application/json

{
    "otel_id": 1,
    "baslangic_tarihi": "2024-01-01",
    "bitis_tarihi": "2024-01-31",
    "donem_tipi": "aylik"
}
```

**Response:**

```json
{
  "success": true,
  "task_id": "abc123-def456-ghi789",
  "message": "Dönemsel kar hesaplama başlatıldı"
}
```

**Python Kullanımı:**

```python
from celery_app import donemsel_kar_hesapla_async

# Task'ı başlat
task = donemsel_kar_hesapla_async.delay(
    otel_id=1,
    baslangic_tarihi='2024-01-01',
    bitis_tarihi='2024-01-31',
    donem_tipi='aylik'
)

# Task ID'yi al
task_id = task.id
```

### 2. Tüketim Trendi Güncelleme

Ürün bazlı tüketim trendlerini analiz eder.

**API Endpoint:**

```http
POST /api/v1/celery/task/tuketim-trendi
Content-Type: application/json

{
    "otel_id": 1,
    "donem": "aylik"
}
```

**Python Kullanımı:**

```python
from celery_app import tuketim_trendi_guncelle_async

task = tuketim_trendi_guncelle_async.delay(
    otel_id=1,
    donem='aylik'
)
```

### 3. Stok Devir Hızı Güncelleme

Ürün stok devir hızlarını hesaplar.

**API Endpoint:**

```http
POST /api/v1/celery/task/stok-devir
Content-Type: application/json

{
    "otel_id": 1
}
```

**Python Kullanımı:**

```python
from celery_app import stok_devir_guncelle_async

task = stok_devir_guncelle_async.delay(otel_id=1)
```

## Task Durum Sorgulama

### Task Durumunu Kontrol Et

```http
GET /api/v1/celery/task/status/{task_id}
```

**Response:**

```json
{
  "success": true,
  "task_id": "abc123-def456-ghi789",
  "state": "SUCCESS",
  "result": {
    "status": "success",
    "analiz_id": 42,
    "data": {
      "toplam_gelir": 15000.0,
      "toplam_maliyet": 8000.0,
      "net_kar": 7000.0,
      "kar_marji": 46.67
    }
  },
  "info": {
    "status": "Task başarıyla tamamlandı"
  }
}
```

**Task Durumları:**

- `PENDING`: Beklemede
- `STARTED`: Çalışıyor
- `SUCCESS`: Başarılı
- `FAILURE`: Başarısız
- `RETRY`: Yeniden deneniyor

### Task Sonucunu Al

```http
GET /api/v1/celery/task/result/{task_id}
```

### Task'ı İptal Et

```http
POST /api/v1/celery/task/cancel/{task_id}
```

### Aktif Task'ları Listele

```http
GET /api/v1/celery/tasks/active
```

### Zamanlanmış Task'ları Listele

```http
GET /api/v1/celery/tasks/scheduled
```

## Periyodik Task'lar (Celery Beat)

Celery Beat, belirli zamanlarda otomatik çalışan task'ları yönetir.

### 1. Günlük Kar Analizi

- **Çalışma Zamanı**: Her gün gece 00:30
- **Görev**: Tüm oteller için önceki günün kar analizini yapar
- **Task**: `fiyatlandirma.gunluk_kar_analizi`

### 2. Haftalık Trend Analizi

- **Çalışma Zamanı**: Her Pazartesi sabah 06:00
- **Görev**: Tüm oteller için haftalık tüketim trendlerini günceller
- **Task**: `fiyatlandirma.haftalik_trend_analizi`

### 3. Aylık Stok Devir Analizi

- **Çalışma Zamanı**: Her ayın 1'i sabah 07:00
- **Görev**: Tüm oteller için stok devir hızlarını günceller
- **Task**: `fiyatlandirma.aylik_stok_devir_analizi`

## Monitoring ve Debugging

### Celery Flower (Web UI)

Celery task'larını web arayüzünden izlemek için:

```bash
pip install flower
celery -A celery_app flower
```

Tarayıcıda: `http://localhost:5555`

### Log Kontrolü

Worker logları:

```bash
# Worker çıktısında görünür
celery -A celery_app worker --loglevel=debug
```

Beat logları:

```bash
celery -A celery_app beat --loglevel=debug
```

### Redis Kontrolü

```bash
# Redis'e bağlan
redis-cli

# Queue'ları listele
KEYS *

# Queue uzunluğunu kontrol et
LLEN celery

# Task sonuçlarını kontrol et
KEYS celery-task-meta-*
```

## Hata Yönetimi

### Task Başarısız Olursa

Task'lar otomatik olarak hata durumunu yakalar ve result'a kaydeder:

```python
{
    "status": "error",
    "message": "Hata mesajı",
    "data": None
}
```

### Retry Mekanizması

Task'lar başarısız olduğunda otomatik retry yapılmaz. Manuel retry için:

```python
from celery_app import donemsel_kar_hesapla_async

# Başarısız task'ı yeniden başlat
task = donemsel_kar_hesapla_async.retry(
    args=[otel_id, baslangic, bitis],
    countdown=60  # 60 saniye sonra
)
```

## Production Deployment

### Supervisor ile Otomatik Başlatma (Linux)

`/etc/supervisor/conf.d/celery.conf`:

```ini
[program:celery_worker]
command=/path/to/venv/bin/celery -A celery_app worker --loglevel=info
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/worker.log

[program:celery_beat]
command=/path/to/venv/bin/celery -A celery_app beat --loglevel=info
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/beat.log
```

### Systemd ile Otomatik Başlatma (Linux)

`/etc/systemd/system/celery-worker.service`:

```ini
[Unit]
Description=Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/celery -A celery_app worker --loglevel=info --detach
Restart=always

[Install]
WantedBy=multi-user.target
```

Başlat:

```bash
sudo systemctl enable celery-worker
sudo systemctl start celery-worker
sudo systemctl status celery-worker
```

## Performans Optimizasyonu

### Worker Sayısını Artırma

```bash
# 4 worker process
celery -A celery_app worker --concurrency=4

# Otomatik (CPU sayısı kadar)
celery -A celery_app worker --autoscale=10,3
```

### Task Önceliklendirme

```python
# Yüksek öncelikli task
task.apply_async(priority=9)

# Düşük öncelikli task
task.apply_async(priority=1)
```

### Memory Leak Önleme

```python
# Config'de zaten ayarlı
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
```

## Güvenlik

### Task Yetkilendirme

API endpoint'leri zaten `@role_required` decorator ile korunuyor:

```python
@celery_bp.route('/task/donemsel-kar', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def start_donemsel_kar_task():
    # ...
```

### Redis Güvenliği

Production'da Redis'i şifrele:

```env
CELERY_BROKER_URL=redis://:password@localhost:6379/1
```

## Sorun Giderme

### Problem: Worker başlamıyor

**Çözüm:**

1. Redis çalışıyor mu kontrol et: `redis-cli ping`
2. Port kullanımda mı: `netstat -an | findstr 6379`
3. Firewall kontrolü

### Problem: Task sonucu alınamıyor

**Çözüm:**

1. Result backend ayarlandı mı kontrol et
2. Redis'te result var mı: `redis-cli KEYS celery-task-meta-*`
3. Task timeout'a uğramış olabilir

### Problem: Beat task'ları çalışmıyor

**Çözüm:**

1. Beat çalışıyor mu: `ps aux | grep celery`
2. Schedule doğru mu: `celery_app.py` içinde `beat_schedule` kontrol et
3. Timezone ayarları doğru mu

## Örnek Kullanım Senaryoları

### Senaryo 1: Aylık Kar Raporu Oluşturma

```python
from celery_app import donemsel_kar_hesapla_async
from datetime import datetime, timedelta

# Geçen ayın ilk ve son günü
bugun = datetime.now()
gecen_ay_son = bugun.replace(day=1) - timedelta(days=1)
gecen_ay_ilk = gecen_ay_son.replace(day=1)

# Task başlat
task = donemsel_kar_hesapla_async.delay(
    otel_id=1,
    baslangic_tarihi=gecen_ay_ilk.isoformat(),
    bitis_tarihi=gecen_ay_son.isoformat(),
    donem_tipi='aylik'
)

print(f"Task başlatıldı: {task.id}")
```

### Senaryo 2: Tüm Oteller için Trend Analizi

```python
from celery_app import tuketim_trendi_guncelle_async
from models import Otel

# Tüm oteller için
oteller = Otel.query.filter_by(aktif=True).all()

task_ids = []
for otel in oteller:
    task = tuketim_trendi_guncelle_async.delay(
        otel_id=otel.id,
        donem='aylik'
    )
    task_ids.append(task.id)

print(f"{len(task_ids)} task başlatıldı")
```

### Senaryo 3: Task Sonuçlarını Toplu Kontrol

```python
from celery.result import AsyncResult
from celery_app import celery

task_ids = ['task-1', 'task-2', 'task-3']

for task_id in task_ids:
    result = AsyncResult(task_id, app=celery)
    print(f"Task {task_id}: {result.state}")
    if result.state == 'SUCCESS':
        print(f"Sonuç: {result.result}")
```

## İletişim ve Destek

Sorunlar için:

- GitHub Issues
- Sistem Yöneticisi ile iletişime geçin
- Log dosyalarını kontrol edin: `app.log`

## Kaynaklar

- [Celery Dokümantasyonu](https://docs.celeryproject.org/)
- [Redis Dokümantasyonu](https://redis.io/documentation)
- [Flask-Celery Integration](https://flask.palletsprojects.com/en/2.3.x/patterns/celery/)
