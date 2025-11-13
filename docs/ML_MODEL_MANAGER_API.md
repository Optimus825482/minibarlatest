# ModelManager API Documentation

## Genel Bakış

`ModelManager` sınıfı, ML modellerinin dosya sisteminde yönetimini sağlar.

**Lokasyon**: `utils/ml/model_manager.py`

## Sınıf: ModelManager

### Constructor

```python
ModelManager(db, models_dir=None)
```

**Parametreler**:

- `db` (SQLAlchemy): Database instance
- `models_dir` (str, optional): Model dizini (default: `/app/ml_models`)

**Örnek**:

```python
from utils.ml.model_manager import ModelManager

model_manager = ModelManager(db)
# veya custom dizin
model_manager = ModelManager(db, models_dir='/custom/path')
```

---

## Public Methods

### save_model_to_file()

Model'i dosyaya kaydet ve metadata'yı veritabanına yaz.

```python
save_model_to_file(
    model,
    model_type: str,
    metric_type: str,
    accuracy: float,
    precision: float,
    recall: float
) -> str
```

**Parametreler**:

- `model`: Eğitilmiş sklearn model
- `model_type` (str): 'isolation_forest' veya 'z_score'
- `metric_type` (str): 'stok_seviye', 'tuketim_miktar', vb.
- `accuracy` (float): Model accuracy (0.0-1.0)
- `precision` (float): Model precision (0.0-1.0)
- `recall` (float): Model recall (0.0-1.0)

**Returns**: `str` - Kaydedilen dosyanın path'i

**Raises**:

- `IOError`: Dosya yazma hatası
- `DatabaseError`: Veritabanı kayıt hatası

**Örnek**:

```python
from sklearn.ensemble import IsolationForest

# Model eğit
model = IsolationForest(contamination=0.1)
model.fit(X_train)

# Kaydet
filepath = model_manager.save_model_to_file(
    model=model,
    model_type='isolation_forest',
    metric_type='stok_seviye',
    accuracy=0.95,
    precision=0.92,
    recall=0.88
)

print(f"Model kaydedildi: {filepath}")
# Model kaydedildi: /app/ml_models/isolation_forest_stok_seviye_20251112_140530.pkl
```

**Log Çıktısı**:

```
💾 [MODEL_SAVE_START] Model kaydediliyor: isolation_forest_stok_seviye_20251112_140530.pkl
✅ [MODEL_SAVE_SUCCESS] Model kaydedildi: isolation_forest_stok_seviye |
   Path: isolation_forest_stok_seviye_20251112_140530.pkl |
   Size: 3.25MB | Accuracy: 95.00% |
   Serialize: 150ms | Total: 250ms | Disk: 45.2%
```

---

### load_model_from_file()

Model'i dosyadan yükle (retry mekanizması ile).

```python
load_model_from_file(
    model_type: str,
    metric_type: str,
    max_retries: int = 3
)
```

**Parametreler**:

- `model_type` (str): Model tipi
- `metric_type` (str): Metrik tipi
- `max_retries` (int): Maksimum retry sayısı (default: 3)

**Returns**: Model object veya `None` (bulunamazsa)

**Raises**:

- `PickleError`: Model deserialize hatası
- `IOError`: Dosya okuma hatası

**Örnek**:

```python
# Model yükle
model = model_manager.load_model_from_file(
    model_type='isolation_forest',
    metric_type='stok_seviye'
)

if model:
    # Tahmin yap
    predictions = model.predict(X_test)
else:
    print("Model bulunamadı, fallback kullan")
```

**Log Çıktısı**:

```
📂 [MODEL_LOAD_SUCCESS] Model yüklendi: isolation_forest_stok_seviye |
   Path: isolation_forest_stok_seviye_20251112_140530.pkl |
   Size: 3.25MB | Load time: 50ms | Attempt: 1/3
```

**Backward Compatibility**:

- Dosya bulunamazsa veritabanından yüklenir
- Yüklenen model otomatik dosyaya migrate edilir

---

### list_available_models()

Mevcut modelleri listele.

```python
list_available_models() -> List[Dict]
```

**Returns**: `List[Dict]` - Model bilgileri listesi

**Örnek**:

```python
models = model_manager.list_available_models()

for model in models:
    print(f"{model['model_type']}_{model['metric_type']}")
    print(f"  Path: {model['path']}")
    print(f"  Size: {model['size_kb']:.2f}KB")
    print(f"  Accuracy: {model['accuracy']:.2%}")
    print(f"  Created: {model['created_at']}")
```

**Çıktı**:

```
isolation_forest_stok_seviye
  Path: /app/ml_models/isolation_forest_stok_seviye_20251112_140530.pkl
  Size: 3328.50KB
  Accuracy: 95.00%
  Created: 2025-11-12 14:05:30

isolation_forest_tuketim_miktar
  Path: /app/ml_models/isolation_forest_tuketim_miktar_20251112_140530.pkl
  Size: 2867.20KB
  Accuracy: 92.50%
  Created: 2025-11-12 14:05:30
```

---

### get_model_info()

Belirli bir model hakkında bilgi al.

```python
get_model_info(
    model_type: str,
    metric_type: str
) -> Optional[Dict]
```

**Parametreler**:

- `model_type` (str): Model tipi
- `metric_type` (str): Metrik tipi

**Returns**: `Dict` veya `None`

**Örnek**:

```python
info = model_manager.get_model_info(
    model_type='isolation_forest',
    metric_type='stok_seviye'
)

if info:
    print(f"Path: {info['path']}")
    print(f"Size: {info['size_kb']:.2f}KB")
    print(f"Accuracy: {info['accuracy']:.2%}")
    print(f"Precision: {info['precision']:.2%}")
    print(f"Recall: {info['recall']:.2%}")
    print(f"Training Date: {info['training_date']}")
    print(f"Active: {info['is_active']}")
```

---

### cleanup_old_models()

Eski model versiyonlarını temizle.

```python
cleanup_old_models(keep_versions: int = 3) -> Dict
```

**Parametreler**:

- `keep_versions` (int): Her model tipi için kaç versiyon saklanacak (default: 3)

**Returns**: `Dict` - Temizlik sonuçları

**Örnek**:

```python
result = model_manager.cleanup_old_models(keep_versions=3)

print(f"Silinen model sayısı: {result['deleted_count']}")
print(f"Boşaltılan alan: {result['freed_space_mb']:.2f}MB")
print(f"Saklanan modeller: {result['kept_models']}")
print(f"Disk kullanımı: {result['disk_usage_percent']:.1f}%")
```

**Çıktı**:

```
Silinen model sayısı: 5
Boşaltılan alan: 15.50MB
Saklanan modeller: ['isolation_forest_stok_seviye', 'isolation_forest_tuketim_miktar']
Disk kullanımı: 42.1%
```

**Log Çıktısı**:

```
🗑️  [CLEANUP_SUCCESS] Model cleanup tamamlandı |
   Deleted: 5 models | Freed: 15.50MB |
   Kept: 2 types | Disk: 42.1% (25.50GB free)
```

---

### get_performance_stats()

Performance istatistiklerini getir.

```python
get_performance_stats(hours: int = 24) -> Dict
```

**Parametreler**:

- `hours` (int): Kaç saatlik veri (default: 24)

**Returns**: `Dict` - Performance istatistikleri

**Örnek**:

```python
stats = model_manager.get_performance_stats(hours=24)

print("Save Operations:")
print(f"  Count: {stats['save']['count']}")
print(f"  Success Rate: {stats['save']['success_rate']}%")
print(f"  Avg Time: {stats['save']['avg_time_ms']}ms")
print(f"  Avg Size: {stats['save']['avg_size_mb']}MB")

print("\nLoad Operations:")
print(f"  Count: {stats['load']['count']}")
print(f"  Success Rate: {stats['load']['success_rate']}%")
print(f"  Avg Time: {stats['load']['avg_time_ms']}ms")

print("\nDisk Usage:")
print(f"  Total: {stats['disk']['total_gb']}GB")
print(f"  Used: {stats['disk']['used_gb']}GB")
print(f"  Free: {stats['disk']['free_gb']}GB")
print(f"  Percent: {stats['disk']['percent']}%")
```

**Çıktı**:

```
Save Operations:
  Count: 15
  Success Rate: 98.5%
  Avg Time: 250ms
  Avg Size: 3.12MB

Load Operations:
  Count: 120
  Success Rate: 99.2%
  Avg Time: 50ms

Disk Usage:
  Total: 50.00GB
  Used: 22.60GB
  Free: 27.40GB
  Percent: 45.2%
```

---

## Private Methods

### \_ensure_directory_exists()

Model dizinini oluştur (yoksa).

### \_generate_filename()

Model dosya adı oluştur.

**Format**: `{model_type}_{metric_type}_{timestamp}.pkl`

**Örnek**: `isolation_forest_stok_seviye_20251112_140530.pkl`

### \_validate_path()

Path traversal saldırılarını önle.

**Raises**: `SecurityError` - Path traversal tespit edilirse

### \_get_file_size_kb()

Dosya boyutunu KB cinsinden döndür.

### \_check_disk_space()

Disk kullanımını kontrol et.

**Returns**: `{'total_gb', 'used_gb', 'free_gb', 'percent'}`

### \_validate_model_file()

Model dosyasının geçerli olup olmadığını kontrol et.

### \_log_performance_metric()

Performance metriklerini ml_metrics tablosuna kaydet.

---

## Error Handling

### File Not Found

```python
model = model_manager.load_model_from_file('isolation_forest', 'stok_seviye')
if model is None:
    # Fallback: Z-Score kullan
    pass
```

### Corrupt File

Otomatik retry mekanizması (exponential backoff):

- 1. deneme: hemen
- 2. deneme: 2 saniye sonra
- 3. deneme: 4 saniye sonra

### Disk Full

Otomatik cleanup tetiklenir:

```python
# Disk %90+ ise
if disk_info['percent'] > 90:
    model_manager.cleanup_old_models(keep_versions=1)
```

### Permission Denied

Log kaydedilir ve fallback devreye girer.

---

## Best Practices

### 1. Model Kaydetme

```python
try:
    filepath = model_manager.save_model_to_file(
        model=model,
        model_type='isolation_forest',
        metric_type='stok_seviye',
        accuracy=0.95,
        precision=0.92,
        recall=0.88
    )
    logger.info(f"Model kaydedildi: {filepath}")
except Exception as e:
    logger.error(f"Model kaydetme hatası: {str(e)}")
    # Fallback: Veritabanına kaydet
```

### 2. Model Yükleme

```python
model = model_manager.load_model_from_file(
    model_type='isolation_forest',
    metric_type='stok_seviye'
)

if model is None:
    # Fallback: Z-Score kullan
    logger.warning("Model bulunamadı, Z-Score fallback")
    return detect_with_zscore(values)

# Model kullan
predictions = model.predict(X)

# Bellekten temizle
del model
```

### 3. Periyodik Cleanup

```python
# Scheduler ile otomatik cleanup (her gece 04:00)
scheduler.add_job(
    func=lambda: model_manager.cleanup_old_models(keep_versions=3),
    trigger='cron',
    hour=4,
    minute=0
)
```

### 4. Monitoring

```python
# Performance monitoring
stats = model_manager.get_performance_stats(hours=24)

if stats['save']['success_rate'] < 95:
    logger.warning("Model save success rate düşük!")

if stats['load']['avg_time_ms'] > 100:
    logger.warning("Model load süresi yüksek!")

if stats['disk']['percent'] > 80:
    logger.warning("Disk kullanımı yüksek!")
```

---

## Environment Variables

```bash
# Model dizini (default: /app/ml_models)
ML_MODELS_DIR=/app/ml_models

# ML sistem aktif mi? (default: true)
ML_ENABLED=true
```

---

## Security

### Path Validation

Tüm dosya işlemlerinde path validation yapılır:

```python
# ✅ Güvenli
/app/ml_models/model.pkl

# ❌ Güvensiz (path traversal)
/app/ml_models/../../../etc/passwd
```

### File Permissions

- **Dizin**: 755 (rwxr-xr-x)
- **Dosyalar**: 644 (rw-r--r--)

### User

Container'da non-root user (`appuser`) kullanılır.

---

## Performance

### Benchmarks

| Operation   | Time   | Notes     |
| ----------- | ------ | --------- |
| Model Save  | ~250ms | 3MB model |
| Model Load  | ~50ms  | 3MB model |
| Cleanup     | ~500ms | 10 model  |
| List Models | ~10ms  | 20 model  |

### Memory Usage

| Scenario       | RAM Usage  |
| -------------- | ---------- |
| Öncesi (DB)    | 100MB      |
| Sonrası (File) | 50MB       |
| İyileştirme    | %50 azalma |

---

## Troubleshooting

### Problem: Model yüklenemiyor

**Kontrol**:

```bash
ls -lh /app/ml_models/
```

**Çözüm**:

```bash
# Permissions düzelt
chmod 755 /app/ml_models
chmod 644 /app/ml_models/*.pkl
```

### Problem: Disk dolu

**Kontrol**:

```bash
df -h /app/ml_models
```

**Çözüm**:

```python
# Manuel cleanup
model_manager.cleanup_old_models(keep_versions=1)
```

### Problem: Fallback rate yüksek

**Kontrol**:

```python
from utils.ml.anomaly_detector import AnomalyDetector
detector = AnomalyDetector(db)
stats = detector.get_fallback_stats()
print(stats)
```

**Çözüm**:

- Model dosyalarını kontrol et
- Migration çalıştır
- Model'leri yeniden eğit

---

## Changelog

### v1.0.0 (2025-11-12)

- ✅ Initial release
- ✅ File system storage
- ✅ Automatic cleanup
- ✅ Performance monitoring
- ✅ Comprehensive error handling
- ✅ Backward compatibility

---

**Son Güncelleme**: 2025-11-12  
**Versiyon**: 1.0.0  
**Yazar**: Kiro AI
