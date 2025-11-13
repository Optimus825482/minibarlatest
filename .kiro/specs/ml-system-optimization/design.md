# Design Document - ML Sistem Optimizasyonu

## Overview

Bu design, ML modellerinin veritabanından dosya sistemine taşınması ve performans optimizasyonunu kapsar. Mevcut sistemde modeller PostgreSQL'de BLOB olarak saklanıyor. Yeni sistemde modeller `/app/ml_models/` dizininde pickle dosyaları olarak saklanacak ve ihtiyaç anında yüklenecek.

**Temel Hedefler:**

- RAM kullanımını %50 azaltmak
- Model yükleme süresini < 100ms tutmak
- Backward compatibility sağlamak
- Zero downtime migration
- Coolify deployment uyumluluğu

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ML System Architecture                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │   Scheduler  │─────▶│ Anomaly      │                     │
│  │   (app.py)   │      │ Detector     │                     │
│  └──────────────┘      └──────┬───────┘                     │
│                               │                              │
│                               ▼                              │
│                    ┌──────────────────┐                      │
│                    │  Model Manager   │◀────────┐            │
│                    │   (NEW)          │         │            │
│                    └────┬─────────┬───┘         │            │
│                         │         │             │            │
│              ┌──────────▼─┐   ┌──▼──────────┐  │            │
│              │ File System│   │  PostgreSQL │  │            │
│              │  Storage   │   │  (metadata) │  │            │
│              │            │   │             │  │            │
│              │ /app/      │   │ ml_models   │  │            │
│              │ ml_models/ │   │ table       │  │            │
│              └────────────┘   └─────────────┘  │            │
│                                                 │            │
│                    ┌──────────────────┐         │            │
│                    │  Model Trainer   │─────────┘            │
│                    │                  │                      │
│                    └──────────────────┘                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
1. Model Training Flow:
   Model Trainer → ModelManager.save_model_to_file()
                → File System (/app/ml_models/model.pkl)
                → PostgreSQL (metadata: path, accuracy, date)

2. Anomaly Detection Flow:
   Anomaly Detector → ModelManager.load_model_from_file()
                   → Check File System
                   → If not found: Check PostgreSQL (backward compat)
                   → Return Model
                   → Use for detection
                   → Clear from memory

3. Cleanup Flow:
   Scheduler → ModelManager.cleanup_old_models()
            → List files in /app/ml_models/
            → Keep latest 3 versions per type
            → Delete old files
            → Update PostgreSQL (is_active=false)
```

## Components and Interfaces

### 1. ModelManager Class

**Location**: `utils/ml/model_manager.py`

```python
class ModelManager:
    """
    Merkezi model yönetim servisi

    Sorumluluklar:
    - Model dosyalarını kaydetme/yükleme
    - Model versiyonlama
    - Otomatik temizlik
    - Hata yönetimi
    - Monitoring
    """

    def __init__(self, db, models_dir='/app/ml_models'):
        """
        Args:
            db: SQLAlchemy database instance
            models_dir: Model dosyalarının saklanacağı dizin
        """
        self.db = db
        self.models_dir = Path(models_dir)
        self._ensure_directory_exists()
        self.logger = logging.getLogger(__name__)

    def save_model_to_file(
        self,
        model,
        model_type: str,
        metric_type: str,
        accuracy: float,
        precision: float,
        recall: float
    ) -> str:
        """
        Modeli dosyaya kaydet ve metadata'yı veritabanına yaz

        Args:
            model: Eğitilmiş sklearn model
            model_type: 'isolation_forest' veya 'z_score'
            metric_type: 'stok_seviye', 'tuketim_miktar', vb.
            accuracy, precision, recall: Model performans metrikleri

        Returns:
            str: Kaydedilen dosyanın path'i

        Raises:
            IOError: Dosya yazma hatası
            DatabaseError: Veritabanı kayıt hatası
        """
        pass

    def load_model_from_file(
        self,
        model_type: str,
        metric_type: str
    ) -> Optional[Any]:
        """
        Modeli dosyadan yükle

        Args:
            model_type: Model tipi
            metric_type: Metrik tipi

        Returns:
            Model object veya None (bulunamazsa)

        Raises:
            PickleError: Model deserialize hatası
            IOError: Dosya okuma hatası
        """
        pass

    def list_available_models(self) -> List[Dict]:
        """
        Mevcut modelleri listele

        Returns:
            List of dicts: [
                {
                    'model_type': 'isolation_forest',
                    'metric_type': 'stok_seviye',
                    'path': '/app/ml_models/...',
                    'size_kb': 123,
                    'created_at': datetime,
                    'accuracy': 0.95
                }
            ]
        """
        pass

    def cleanup_old_models(self, keep_versions: int = 3) -> Dict:
        """
        Eski model versiyonlarını temizle

        Args:
            keep_versions: Her model tipi için kaç versiyon saklanacak

        Returns:
            Dict: {
                'deleted_count': 5,
                'freed_space_mb': 25.5,
                'kept_models': ['model1.pkl', 'model2.pkl']
            }
        """
        pass

    def get_model_info(
        self,
        model_type: str,
        metric_type: str
    ) -> Optional[Dict]:
        """
        Model bilgilerini getir

        Returns:
            Dict veya None: {
                'path': '/app/ml_models/...',
                'size_kb': 123,
                'accuracy': 0.95,
                'training_date': datetime,
                'is_active': True
            }
        """
        pass

    def migrate_from_database(self, dry_run: bool = False) -> Dict:
        """
        Veritabanındaki modelleri dosya sistemine migrate et

        Args:
            dry_run: True ise sadece rapor göster, değişiklik yapma

        Returns:
            Dict: {
                'migrated': 10,
                'failed': 0,
                'skipped': 2,
                'errors': []
            }
        """
        pass

    def _ensure_directory_exists(self):
        """Model dizinini oluştur (yoksa)"""
        pass

    def _generate_filename(
        self,
        model_type: str,
        metric_type: str
    ) -> str:
        """
        Model dosya adı oluştur
        Format: {model_type}_{metric_type}_{timestamp}.pkl
        """
        pass

    def _validate_model_file(self, filepath: Path) -> bool:
        """Model dosyasının geçerli olup olmadığını kontrol et"""
        pass

    def _get_file_size_kb(self, filepath: Path) -> float:
        """Dosya boyutunu KB cinsinden döndür"""
        pass

    def _check_disk_space(self) -> Dict:
        """
        Disk kullanımını kontrol et
        Returns: {'total_gb': 100, 'used_gb': 50, 'free_gb': 50, 'percent': 50}
        """
        pass
```

### 2. Model Trainer Integration

**Location**: `utils/ml/model_trainer.py`

**Değişiklikler:**

```python
class ModelTrainer:
    def __init__(self, db):
        self.db = db
        self.model_manager = ModelManager(db)  # NEW
        # ... existing code

    def save_model(self, model, model_type, metric_type, accuracy, precision, recall):
        """
        ÖNCE: Modeli veritabanına BLOB olarak kaydediyordu
        SONRA: ModelManager kullanarak dosyaya kaydedecek
        """
        try:
            # Yeni yöntem: Dosyaya kaydet
            model_path = self.model_manager.save_model_to_file(
                model=model,
                model_type=model_type,
                metric_type=metric_type,
                accuracy=accuracy,
                precision=precision,
                recall=recall
            )

            logger.info(f"✅ Model kaydedildi: {model_path}")
            return model_path

        except Exception as e:
            logger.error(f"❌ Model kaydetme hatası: {str(e)}")
            # Fallback: Eski yöntemi dene (backward compat)
            return self._save_to_database_legacy(model, ...)
```

### 3. Anomaly Detector Integration

**Location**: `utils/ml/anomaly_detector.py`

**Değişiklikler:**

```python
class AnomalyDetector:
    def __init__(self, db):
        self.db = db
        self.model_manager = ModelManager(db)  # NEW
        self._loaded_models = {}  # Cache (optional)

    def detect_with_model(self, metric_type: str, values: List[float]):
        """
        ÖNCE: Modeli veritabanından yüklüyordu (her seferinde)
        SONRA: ModelManager kullanarak dosyadan yükleyecek
        """
        try:
            # Model yükle (dosyadan)
            model = self.model_manager.load_model_from_file(
                model_type='isolation_forest',
                metric_type=metric_type
            )

            if model is None:
                # Fallback: Z-Score kullan
                logger.warning(f"Model bulunamadı, Z-Score fallback: {metric_type}")
                return self.detect_with_zscore(values)

            # Model ile tahmin yap
            predictions = model.predict(values)

            # Modeli bellekten temizle (optional)
            del model

            return predictions

        except Exception as e:
            logger.error(f"Model yükleme hatası: {str(e)}")
            # Fallback: Z-Score
            return self.detect_with_zscore(values)
```

### 4. Database Schema Changes

**Migration**: `migrations/versions/add_model_path_column.py`

```python
"""Add model_path column to ml_models table

Revision ID: abc123
"""

def upgrade():
    # model_path kolonu ekle
    op.add_column('ml_models',
        sa.Column('model_path', sa.String(500), nullable=True)
    )

    # model_data kolonunu nullable yap
    op.alter_column('ml_models', 'model_data',
        existing_type=sa.LargeBinary(),
        nullable=True
    )

    # Index ekle
    op.create_index('idx_ml_models_path', 'ml_models', ['model_path'])

def downgrade():
    op.drop_index('idx_ml_models_path', 'ml_models')
    op.alter_column('ml_models', 'model_data',
        existing_type=sa.LargeBinary(),
        nullable=False
    )
    op.drop_column('ml_models', 'model_path')
```

**Updated Schema:**

```sql
CREATE TABLE ml_models (
    id SERIAL PRIMARY KEY,
    model_type VARCHAR(50) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    model_data BYTEA NULL,              -- NULLABLE (backward compat)
    model_path VARCHAR(500) NULL,       -- NEW
    parameters JSONB,
    training_date TIMESTAMP WITH TIME ZONE NOT NULL,
    accuracy DOUBLE PRECISION,
    precision DOUBLE PRECISION,
    recall DOUBLE PRECISION,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ml_models_type_active ON ml_models(model_type, metric_type, is_active);
CREATE INDEX idx_ml_models_path ON ml_models(model_path);
```

## Data Models

### File System Structure

```
/app/ml_models/
├── isolation_forest_stok_seviye_20251112_120000.pkl
├── isolation_forest_stok_seviye_20251111_120000.pkl
├── isolation_forest_stok_seviye_20251110_120000.pkl
├── isolation_forest_tuketim_miktar_20251112_120000.pkl
├── isolation_forest_tuketim_miktar_20251111_120000.pkl
├── isolation_forest_dolum_sure_20251112_120000.pkl
├── .gitkeep
└── README.md
```

**File Naming Convention:**

```
{model_type}_{metric_type}_{timestamp}.pkl

Examples:
- isolation_forest_stok_seviye_20251112_120000.pkl
- isolation_forest_tuketim_miktar_20251112_120000.pkl
- z_score_dolum_sure_20251112_120000.pkl
```

**File Permissions:**

- Files: 644 (rw-r--r--)
- Directory: 755 (rwxr-xr-x)

### Model Metadata (PostgreSQL)

```python
{
    'id': 123,
    'model_type': 'isolation_forest',
    'metric_type': 'stok_seviye',
    'model_data': None,  # NULL (yeni modeller için)
    'model_path': '/app/ml_models/isolation_forest_stok_seviye_20251112_120000.pkl',
    'parameters': {
        'contamination': 0.1,
        'n_estimators': 100,
        'random_state': 42
    },
    'training_date': '2025-11-12 12:00:00+00',
    'accuracy': 0.95,
    'precision': 0.92,
    'recall': 0.88,
    'is_active': True,
    'created_at': '2025-11-12 12:00:00+00'
}
```

## Error Handling

### Error Scenarios and Responses

| Scenario                 | Detection                | Response               | Fallback               |
| ------------------------ | ------------------------ | ---------------------- | ---------------------- |
| Model dosyası bulunamadı | File not found exception | Log error, check DB    | Z-Score method         |
| Model corrupt            | Pickle load error        | Log error, retry 3x    | Z-Score method         |
| Disk dolu                | Disk space check         | Alert admin, cleanup   | Continue with existing |
| Permission denied        | File access error        | Log error, check perms | Use DB model           |
| DB connection lost       | SQLAlchemy error         | Retry 3x, use cache    | Continue with file     |
| Model too old            | Timestamp check          | Log warning            | Use anyway             |

### Retry Strategy

```python
def load_model_with_retry(self, model_type, metric_type, max_retries=3):
    """
    Exponential backoff ile retry

    Retry delays: 1s, 2s, 4s
    """
    for attempt in range(max_retries):
        try:
            return self.load_model_from_file(model_type, metric_type)
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 2 ** attempt  # 1, 2, 4 seconds
                logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s")
                time.sleep(delay)
            else:
                logger.error(f"All retries failed: {str(e)}")
                return None
```

### Fallback Mechanism

```python
def detect_anomalies_with_fallback(self, metric_type, values):
    """
    1. Try: Load model from file
    2. Fallback 1: Load model from database
    3. Fallback 2: Use Z-Score method
    """
    # Try file system
    model = self.model_manager.load_model_from_file(model_type, metric_type)

    if model:
        return self._detect_with_model(model, values)

    # Fallback 1: Database
    model = self._load_from_database_legacy(model_type, metric_type)

    if model:
        logger.warning("Using database model (fallback)")
        return self._detect_with_model(model, values)

    # Fallback 2: Z-Score
    logger.warning("Using Z-Score method (fallback)")
    return self.detect_with_zscore(values)
```

## Testing Strategy

### Unit Tests

**test_model_manager.py:**

```python
class TestModelManager:
    def test_save_model_to_file(self):
        """Model dosyaya kaydedilmeli"""

    def test_load_model_from_file(self):
        """Model dosyadan yüklenmeli"""

    def test_file_not_found_returns_none(self):
        """Dosya bulunamazsa None dönmeli"""

    def test_cleanup_keeps_latest_versions(self):
        """Cleanup en son 3 versiyonu saklamalı"""

    def test_disk_space_warning(self):
        """Disk doluysa warning loglamalı"""

    def test_corrupt_file_handling(self):
        """Corrupt dosya gracefully handle edilmeli"""
```

### Integration Tests

**test_ml_system_integration.py:**

```python
class TestMLSystemIntegration:
    def test_train_save_load_flow(self):
        """Eğit → Kaydet → Yükle flow'u çalışmalı"""

    def test_anomaly_detection_with_file_model(self):
        """Anomali tespiti dosya modeliyle çalışmalı"""

    def test_fallback_to_zscore(self):
        """Model bulunamazsa Z-Score fallback çalışmalı"""

    def test_migration_from_database(self):
        """DB'den dosyaya migration çalışmalı"""
```

### Performance Tests

**test_performance.py:**

```python
class TestPerformance:
    def test_model_load_time(self):
        """Model yükleme < 100ms olmalı"""
        start = time.time()
        model = manager.load_model_from_file('isolation_forest', 'stok_seviye')
        duration = (time.time() - start) * 1000
        assert duration < 100, f"Load time {duration}ms > 100ms"

    def test_memory_usage(self):
        """Model yükleme RAM artışı < 50MB olmalı"""

    def test_concurrent_access(self):
        """10 thread aynı anda model yükleyebilmeli"""
```

## Deployment

### Coolify Configuration

**docker-compose.yml:**

```yaml
services:
  app:
    image: minibar-takip:latest
    volumes:
      - ml_models:/app/ml_models # Persistent volume
    environment:
      - ML_MODELS_DIR=/app/ml_models
      - ML_ENABLED=true

volumes:
  ml_models:
    driver: local
```

**Dockerfile:**

```dockerfile
FROM python:3.9-slim

# Model dizini oluştur
RUN mkdir -p /app/ml_models && \
    chmod 755 /app/ml_models

# App kodu
COPY . /app
WORKDIR /app

# Dependencies
RUN pip install -r requirements.txt

# Model dizini için volume
VOLUME ["/app/ml_models"]

CMD ["gunicorn", "app:app"]
```

### Migration Steps

**1. Veritabanı Migration:**

```bash
# Alembic migration çalıştır
flask db upgrade

# model_path kolonu eklendi
# model_data kolonu nullable yapıldı
```

**2. Model Migration:**

```bash
# Dry-run (test)
python migrate_models_to_filesystem.py --dry-run

# Gerçek migration
python migrate_models_to_filesystem.py

# Çıktı:
# ✅ Migrated: 10 models
# ❌ Failed: 0 models
# ⏭️  Skipped: 2 models (already migrated)
# 💾 Total size: 45.5 MB
```

**3. Deployment:**

```bash
# GitHub'a push
git push origin main

# Coolify auto-deploy
# Persistent volume mount edilecek
# Mevcut model dosyaları korunacak
```

**4. Verification:**

```bash
# Model dosyalarını kontrol et
ls -lh /app/ml_models/

# Anomali tespiti test et
python test_ml_system.py

# Logs kontrol et
tail -f /var/log/minibar_takip.log | grep "Model"
```

## Monitoring and Logging

### Log Messages

```python
# Model kaydetme
logger.info(f"💾 Model saved: {path}, size: {size_kb}KB, accuracy: {accuracy:.2%}")

# Model yükleme
logger.info(f"📂 Model loaded: {path}, load_time: {load_time_ms}ms")

# Model bulunamadı
logger.error(f"❌ Model not found: {model_type}_{metric_type}, using fallback")

# Cleanup
logger.info(f"🗑️  Cleaned {count} old models, freed {size_mb}MB")

# Disk warning
logger.warning(f"⚠️  Disk usage {percent}% (threshold: 90%)")

# Migration
logger.info(f"🔄 Migrated {count} models from database to filesystem")
```

### Metrics to Track

```python
# ml_metrics tablosuna kaydet
{
    'metric_type': 'model_load_time',
    'entity_id': model_id,
    'metric_value': load_time_ms,
    'timestamp': now(),
    'extra_data': {
        'model_type': 'isolation_forest',
        'metric_type': 'stok_seviye',
        'file_size_kb': 123
    }
}
```

## Security Considerations

### File Permissions

- Model dosyaları: 644 (owner: rw, others: r)
- Model dizini: 755 (owner: rwx, others: rx)
- Owner: app user (non-root)

### Path Validation

```python
def _validate_path(self, filepath: Path) -> bool:
    """
    Path traversal saldırılarını önle
    """
    # Resolve absolute path
    abs_path = filepath.resolve()

    # models_dir içinde mi kontrol et
    if not str(abs_path).startswith(str(self.models_dir)):
        raise SecurityError("Path traversal attempt detected")

    return True
```

### Data Sanitization

- Model dosyalarında sensitive data olmamalı
- Pickle güvenlik riskleri (trusted source only)
- File size limits (max 10MB per model)

## Performance Optimization

### Caching Strategy (Optional)

```python
class ModelManager:
    def __init__(self, db, cache_enabled=False):
        self._cache = {} if cache_enabled else None

    def load_model_from_file(self, model_type, metric_type):
        # Check cache first
        if self._cache:
            cache_key = f"{model_type}_{metric_type}"
            if cache_key in self._cache:
                return self._cache[cache_key]

        # Load from file
        model = self._load_from_file(...)

        # Cache it
        if self._cache:
            self._cache[cache_key] = model

        return model
```

### Lazy Loading

- Modeller sadece ihtiyaç anında yüklenir
- Kullanım sonrası bellekten temizlenir
- Concurrent access için thread-safe

### Compression (Future)

```python
# Model dosyalarını gzip ile sıkıştır
# .pkl.gz formatında sakla
# %50-70 disk tasarrufu
```

## Rollback Plan

### Rollback Scenarios

**Scenario 1: Migration başarısız**

```bash
# Alembic downgrade
flask db downgrade -1

# Eski kodu deploy et
git revert HEAD
git push origin main
```

**Scenario 2: Model dosyaları corrupt**

```bash
# Veritabanındaki model_data kullan (backward compat)
# Sistem otomatik fallback yapacak

# Veya backup'tan restore et
cp /backup/ml_models/* /app/ml_models/
```

**Scenario 3: Disk dolu**

```bash
# Manuel cleanup
python -c "from utils.ml.model_manager import ModelManager; ModelManager(db).cleanup_old_models(keep_versions=1)"

# Veya eski modelleri sil
rm /app/ml_models/*_202511*.pkl
```

## Success Metrics

### Performance Metrics

- ✅ Model yükleme süresi: < 100ms (target: 50ms)
- ✅ RAM kullanımı: %50 azalma
- ✅ Disk kullanımı: < 100MB (tüm modeller)
- ✅ Model yükleme başarı oranı: > %99.9

### Reliability Metrics

- ✅ Fallback kullanım oranı: < %1
- ✅ Model corruption rate: < %0.1
- ✅ Migration success rate: %100

### Business Metrics

- ✅ Zero downtime migration
- ✅ Backward compatibility: %100
- ✅ Anomali tespit kalitesi: Değişmedi (aynı)

## Future Enhancements

### Phase 2: Model Compression

- Gzip compression (.pkl.gz)
- %50-70 disk tasarrufu
- Minimal performance impact

### Phase 3: Model Versioning API

- REST API for model management
- Model comparison tools
- A/B testing support

### Phase 4: Distributed Storage

- S3/MinIO integration
- Multi-region support
- CDN for model distribution

### Phase 5: Model Monitoring Dashboard

- Real-time model performance
- Drift detection
- Auto-retraining triggers
