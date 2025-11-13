# Design Document

## Overview

Developer Dashboard Enhancement projesi, mevcut developer dashboard'a 10 yeni gelişmiş özellik ekleyerek sistem yöneticilerinin uygulama sağlığını, performansını ve durumunu daha etkili izlemesini sağlayacaktır. Tasarım, modern ve profesyonel bir UI/UX yaklaşımı ile modüler, ölçeklenebilir ve güvenli bir mimari üzerine kurulacaktır.

## Architecture

### Genel Mimari Prensipler

1. **Modüler Yapı**: Her özellik bağımsız modül olarak geliştirilecek
2. **API-First Yaklaşım**: Tüm özellikler RESTful API endpoint'leri ile sunulacak
3. **Real-time Updates**: WebSocket veya polling ile gerçek zamanlı veri güncellemeleri
4. **Caching Strategy**: Redis ile performans optimizasyonu
5. **Security First**: Tüm endpoint'ler authentication ve authorization kontrolü ile korunacak
6. **Error Handling**: Kapsamlı try-catch blokları ve kullanıcı dostu hata mesajları

### Teknoloji Stack

**Backend:**

- Flask Blueprint'ler (modüler route yönetimi)
- SQLAlchemy (database ORM)
- Redis (caching ve real-time data)
- psutil (sistem metrikleri)
- APScheduler (background job scheduling)

**Frontend:**

- Tailwind CSS (modern, responsive tasarım)
- Alpine.js veya Vanilla JS (hafif, performanslı)
- Chart.js (veri görselleştirme)
- Font Awesome (ikonlar)
- WebSocket/SSE (real-time updates)

### Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────────┐
│                    Developer Dashboard UI                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  Cache   │ │  Query   │ │   API    │ │Background│      │
│  │  Manager │ │ Analyzer │ │ Metrics  │ │   Jobs   │ ...  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask API Layer                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         developer_routes.py (Blueprint)              │  │
│  │  /api/cache  /api/queries  /api/metrics  /api/jobs  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  Cache   │ │  Query   │ │   API    │ │Background│      │
│  │ Service  │ │ Service  │ │ Service  │ │  Service │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │PostgreSQL│ │  Redis   │ │   Logs   │                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Cache Management Module

**Backend Service: `utils/monitoring/cache_service.py`**

```python
class CacheService:
    def get_cache_stats() -> dict
    def get_all_keys(pattern: str = '*') -> list
    def get_key_details(key: str) -> dict
    def clear_cache(pattern: str = '*') -> bool
    def get_hit_miss_ratio() -> dict
```

**API Endpoints:**

- `GET /developer/api/cache/stats` - Cache istatistikleri
- `GET /developer/api/cache/keys` - Tüm cache anahtarları
- `GET /developer/api/cache/key/<key>` - Belirli key detayı
- `DELETE /developer/api/cache/clear` - Cache temizleme
- `GET /developer/api/cache/metrics` - Hit/miss oranları

**Frontend Component:**

- Tab-based interface (Stats, Keys, Metrics)
- Real-time cache size monitoring
- Key search ve filtreleme
- Bulk delete işlemleri

### 2. Database Query Analyzer

**Backend Service: `utils/monitoring/query_analyzer.py`**

```python
class QueryAnalyzer:
    def capture_queries() -> None
    def get_slow_queries(threshold: float = 1.0) -> list
    def get_query_stats() -> dict
    def explain_query(query: str) -> dict
    def get_optimization_suggestions(query: str) -> list
```

**Database Schema:**

```sql
CREATE TABLE query_logs (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    execution_time FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    endpoint VARCHAR(255),
    user_id INTEGER,
    parameters JSONB
);

CREATE INDEX idx_query_logs_time ON query_logs(execution_time DESC);
CREATE INDEX idx_query_logs_timestamp ON query_logs(timestamp DESC);
```

**API Endpoints:**

- `GET /developer/api/queries/recent` - Son sorgular
- `GET /developer/api/queries/slow` - Yavaş sorgular
- `GET /developer/api/queries/stats` - Sorgu istatistikleri
- `POST /developer/api/queries/explain` - Query EXPLAIN
- `GET /developer/api/queries/optimize/<id>` - Optimizasyon önerileri

**Frontend Component:**

- Sortable query table (time, endpoint, user)
- Color-coded performance indicators
- Query detail modal (EXPLAIN plan, suggestions)
- Time range filtering

### 3. API Endpoint Performance Metrics

**Backend Service: `utils/monitoring/api_metrics.py`**

```python
class APIMetrics:
    def track_request(endpoint: str, duration: float, status: int) -> None
    def get_endpoint_stats() -> list
    def get_endpoint_details(endpoint: str) -> dict
    def get_error_rate(endpoint: str) -> float
    def get_response_time_percentiles(endpoint: str) -> dict
```

**Middleware: `middleware/metrics_middleware.py`**

```python
@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - g.start_time
    APIMetrics.track_request(request.endpoint, duration, response.status_code)
    return response
```

**API Endpoints:**

- `GET /developer/api/metrics/endpoints` - Tüm endpoint metrikleri
- `GET /developer/api/metrics/endpoint/<name>` - Belirli endpoint detayı
- `GET /developer/api/metrics/errors` - Hata oranları
- `GET /developer/api/metrics/performance` - Performans özeti

**Frontend Component:**

- Endpoint performance dashboard
- Response time charts (Chart.js)
- Error rate indicators
- Request volume graphs

### 4. Background Job Monitoring

**Backend Service: `utils/monitoring/job_monitor.py`**

```python
class JobMonitor:
    def get_active_jobs() -> list
    def get_pending_jobs() -> list
    def get_completed_jobs(limit: int = 50) -> list
    def get_failed_jobs() -> list
    def get_job_details(job_id: str) -> dict
    def retry_job(job_id: str) -> bool
    def cancel_job(job_id: str) -> bool
```

**Job Tracking Schema:**

```sql
CREATE TABLE background_jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    job_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration FLOAT,
    error_message TEXT,
    stack_trace TEXT,
    metadata JSONB
);
```

**API Endpoints:**

- `GET /developer/api/jobs/active` - Aktif görevler
- `GET /developer/api/jobs/pending` - Bekleyen görevler
- `GET /developer/api/jobs/completed` - Tamamlanan görevler
- `GET /developer/api/jobs/failed` - Başarısız görevler
- `POST /developer/api/jobs/<id>/retry` - Görevi yeniden çalıştır
- `DELETE /developer/api/jobs/<id>/cancel` - Görevi iptal et

**Frontend Component:**

- Job status dashboard (Active, Pending, Completed, Failed)
- Real-time job progress tracking
- Job detail modal (logs, errors, stack trace)
- Retry/Cancel actions

### 5. Redis Status Monitor

**Backend Service: `utils/monitoring/redis_monitor.py`**

```python
class RedisMonitor:
    def get_redis_info() -> dict
    def get_memory_stats() -> dict
    def get_key_stats() -> dict
    def get_client_list() -> list
    def get_slowlog() -> list
    def ping() -> bool
```

**API Endpoints:**

- `GET /developer/api/redis/status` - Redis durumu
- `GET /developer/api/redis/memory` - Memory kullanımı
- `GET /developer/api/redis/keys` - Key istatistikleri
- `GET /developer/api/redis/clients` - Bağlı clientlar
- `GET /developer/api/redis/slowlog` - Yavaş komutlar

**Frontend Component:**

- Redis health dashboard
- Memory usage visualization
- Key distribution charts
- Client connection list
- Slowlog viewer

### 6. ML Model Metrics

**Backend Service: `utils/monitoring/ml_metrics.py`**

```python
class MLMetrics:
    def get_model_list() -> list
    def get_model_metrics(model_name: str) -> dict
    def get_prediction_stats(model_name: str) -> dict
    def get_model_performance_history(model_name: str) -> list
    def get_feature_importance(model_name: str) -> dict
```

**API Endpoints:**

- `GET /developer/api/ml/models` - Tüm modeller
- `GET /developer/api/ml/model/<name>/metrics` - Model metrikleri
- `GET /developer/api/ml/model/<name>/predictions` - Tahmin istatistikleri
- `GET /developer/api/ml/model/<name>/history` - Performans geçmişi
- `GET /developer/api/ml/model/<name>/features` - Feature importance

**Frontend Component:**

- Model performance dashboard
- Accuracy/Precision/Recall charts
- Prediction volume graphs
- Feature importance visualization
- Model comparison tool

### 7. Real-time Log Viewer

**Backend Service: `utils/monitoring/log_viewer.py`**

```python
class LogViewer:
    def tail_logs(lines: int = 100) -> list
    def filter_logs(level: str, search: str) -> list
    def get_log_stats() -> dict
    def stream_logs() -> Generator
```

**API Endpoints:**

- `GET /developer/api/logs/tail` - Son loglar
- `GET /developer/api/logs/filter` - Filtrelenmiş loglar
- `GET /developer/api/logs/stats` - Log istatistikleri
- `GET /developer/api/logs/stream` - SSE log stream

**Frontend Component:**

- Real-time log viewer (SSE/WebSocket)
- Log level filtering (ERROR, WARNING, INFO, DEBUG)
- Search functionality
- Auto-scroll toggle
- Log export (JSON, TXT)

### 8. Database Backup/Restore Manager

**Backend Service: `utils/monitoring/backup_manager.py`**

```python
class BackupManager:
    def create_backup(description: str = None) -> dict
    def list_backups() -> list
    def get_backup_details(backup_id: str) -> dict
    def restore_backup(backup_id: str) -> bool
    def delete_backup(backup_id: str) -> bool
    def schedule_backup(cron_expression: str) -> bool
```

**Backup Schema:**

```sql
CREATE TABLE backup_history (
    id SERIAL PRIMARY KEY,
    backup_id VARCHAR(255) UNIQUE NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES kullanici(id),
    status VARCHAR(50),
    restore_count INTEGER DEFAULT 0
);
```

**API Endpoints:**

- `POST /developer/api/backup/create` - Yeni backup oluştur
- `GET /developer/api/backup/list` - Backup listesi
- `GET /developer/api/backup/<id>` - Backup detayı
- `POST /developer/api/backup/<id>/restore` - Backup restore
- `DELETE /developer/api/backup/<id>` - Backup sil
- `POST /developer/api/backup/schedule` - Otomatik backup zamanla

**Frontend Component:**

- Backup list with status indicators
- Create backup modal (with description)
- Restore confirmation dialog
- Download backup file
- Schedule backup interface (cron builder)

### 9. System Configuration Editor

**Backend Service: `utils/monitoring/config_editor.py`**

```python
class ConfigEditor:
    def list_config_files() -> list
    def get_config_content(filename: str) -> str
    def validate_config(filename: str, content: str) -> dict
    def save_config(filename: str, content: str) -> bool
    def get_config_history(filename: str) -> list
    def rollback_config(filename: str, version: int) -> bool
```

**Config Audit Schema:**

```sql
CREATE TABLE config_audit (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    old_content TEXT,
    new_content TEXT,
    changed_by INTEGER REFERENCES kullanici(id),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);
```

**API Endpoints:**

- `GET /developer/api/config/files` - Config dosyaları
- `GET /developer/api/config/file/<name>` - Config içeriği
- `POST /developer/api/config/validate` - Config validasyonu
- `PUT /developer/api/config/file/<name>` - Config kaydet
- `GET /developer/api/config/file/<name>/history` - Değişiklik geçmişi
- `POST /developer/api/config/file/<name>/rollback` - Geri al

**Frontend Component:**

- Config file browser
- Code editor with syntax highlighting (CodeMirror/Monaco)
- Validation feedback
- Change history viewer
- Rollback functionality

### 10. Performance Profiler

**Backend Service: `utils/monitoring/profiler.py`**

```python
class PerformanceProfiler:
    def start_profiling(duration: int = 60) -> str
    def stop_profiling(profile_id: str) -> dict
    def get_profile_results(profile_id: str) -> dict
    def get_cpu_hotspots() -> list
    def get_memory_allocations() -> list
    def export_profile(profile_id: str, format: str) -> bytes
```

**API Endpoints:**

- `POST /developer/api/profiler/start` - Profiling başlat
- `POST /developer/api/profiler/stop` - Profiling durdur
- `GET /developer/api/profiler/<id>/results` - Profiling sonuçları
- `GET /developer/api/profiler/<id>/cpu` - CPU hotspots
- `GET /developer/api/profiler/<id>/memory` - Memory allocations
- `GET /developer/api/profiler/<id>/export` - Sonuçları indir

**Frontend Component:**

- Profiler control panel (Start/Stop)
- Real-time profiling status
- CPU hotspot visualization (flame graph)
- Memory allocation charts
- Export results (JSON, HTML)

## Data Models

### Query Log Model

```python
class QueryLog(db.Model):
    __tablename__ = 'query_logs'
    id = db.Column(db.Integer, primary_key=True)
    query_text = db.Column(db.Text, nullable=False)
    execution_time = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    endpoint = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('kullanici.id'))
    parameters = db.Column(db.JSON)
```

### Background Job Model

```python
class BackgroundJob(db.Model):
    __tablename__ = 'background_jobs'
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(255), unique=True, nullable=False)
    job_name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    duration = db.Column(db.Float)
    error_message = db.Column(db.Text)
    stack_trace = db.Column(db.Text)
    metadata = db.Column(db.JSON)
```

### Backup History Model

```python
class BackupHistory(db.Model):
    __tablename__ = 'backup_history'
    id = db.Column(db.Integer, primary_key=True)
    backup_id = db.Column(db.String(255), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('kullanici.id'))
    status = db.Column(db.String(50))
    restore_count = db.Column(db.Integer, default=0)
```

### Config Audit Model

```python
class ConfigAudit(db.Model):
    __tablename__ = 'config_audit'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    old_content = db.Column(db.Text)
    new_content = db.Column(db.Text)
    changed_by = db.Column(db.Integer, db.ForeignKey('kullanici.id'))
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    change_reason = db.Column(db.Text)
```

## Error Handling

### Standart Error Response Format

```python
{
    "success": False,
    "error": {
        "code": "ERROR_CODE",
        "message": "Kullanıcı dostu hata mesajı",
        "details": "Teknik detaylar (sadece development)",
        "timestamp": "2025-11-12T18:50:00"
    }
}
```

### Error Handling Pattern

```python
try:
    # İşlem
    result = perform_operation()
    return jsonify({"success": True, "data": result})
except SpecificException as e:
    logging.error(f"Specific error: {str(e)}", exc_info=True)
    return jsonify({
        "success": False,
        "error": {
            "code": "SPECIFIC_ERROR",
            "message": "Kullanıcı dostu mesaj",
            "details": str(e) if app.debug else None
        }
    }), 400
except Exception as e:
    logging.critical(f"Unexpected error: {str(e)}", exc_info=True)
    return jsonify({
        "success": False,
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "Bir hata oluştu, lütfen tekrar deneyin",
            "details": str(e) if app.debug else None
        }
    }), 500
```

## Testing Strategy

### Unit Tests

- Her service class için ayrı test dosyası
- Mock kullanarak external dependency'leri izole et
- Edge case'leri test et
- Coverage hedefi: %80+

### Integration Tests

- API endpoint'leri test et
- Database işlemlerini test et
- Redis bağlantılarını test et
- Authentication/Authorization test et

### Performance Tests

- Load testing (locust veya ab)
- Response time benchmarks
- Memory leak kontrolü
- Concurrent request handling

### Security Tests

- SQL injection testleri
- XSS testleri
- CSRF token kontrolü
- Authentication bypass testleri

## UI/UX Design

### Design System

**Renk Paleti:**

```css
/* Primary Colors */
--primary: #667eea;
--primary-dark: #764ba2;
--primary-light: #a8b5ff;

/* Status Colors */
--success: #48bb78;
--warning: #ed8936;
--error: #f56565;
--info: #4299e1;

/* Neutral Colors */
--gray-50: #f7fafc;
--gray-100: #edf2f7;
--gray-200: #e2e8f0;
--gray-300: #cbd5e0;
--gray-400: #a0aec0;
--gray-500: #718096;
--gray-600: #4a5568;
--gray-700: #2d3748;
--gray-800: #1a202c;
--gray-900: #171923;
```

**Typography:**

```css
--font-primary: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
--font-mono: "Fira Code", "Consolas", "Monaco", monospace;

--text-xs: 0.75rem;
--text-sm: 0.875rem;
--text-base: 1rem;
--text-lg: 1.125rem;
--text-xl: 1.25rem;
--text-2xl: 1.5rem;
--text-3xl: 1.875rem;
```

**Spacing:**

```css
--space-1: 0.25rem;
--space-2: 0.5rem;
--space-3: 0.75rem;
--space-4: 1rem;
--space-6: 1.5rem;
--space-8: 2rem;
```

### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Header (Logo, Title, User Info, Logout)                    │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐                                               │
│  │          │  Main Content Area                            │
│  │ Sidebar  │  ┌──────────────────────────────────────┐    │
│  │  Menu    │  │                                       │    │
│  │          │  │  Feature-specific Content             │    │
│  │ - Cache  │  │  (Cards, Tables, Charts, Forms)       │    │
│  │ - Query  │  │                                       │    │
│  │ - API    │  │                                       │    │
│  │ - Jobs   │  │                                       │    │
│  │ - Redis  │  │                                       │    │
│  │ - ML     │  │                                       │    │
│  │ - Logs   │  │                                       │    │
│  │ - Backup │  │                                       │    │
│  │ - Config │  │                                       │    │
│  │ - Profile│  │                                       │    │
│  │          │  └──────────────────────────────────────┘    │
│  └──────────┘                                               │
└─────────────────────────────────────────────────────────────┘
```

### Component Patterns

**Metric Card:**

```html
<div class="metric-card">
  <div class="metric-icon">
    <i class="fas fa-icon"></i>
  </div>
  <div class="metric-content">
    <div class="metric-label">Label</div>
    <div class="metric-value">Value</div>
    <div class="metric-change">+5% from last hour</div>
  </div>
</div>
```

**Data Table:**

```html
<div class="data-table-container">
  <div class="table-header">
    <input type="search" placeholder="Search..." />
    <button class="btn-filter">Filter</button>
  </div>
  <table class="data-table">
    <thead>
      <tr>
        <th sortable>Column 1</th>
        <th sortable>Column 2</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      <!-- Rows -->
    </tbody>
  </table>
  <div class="table-pagination">
    <!-- Pagination controls -->
  </div>
</div>
```

**Modal Dialog:**

```html
<div class="modal-overlay">
  <div class="modal-container">
    <div class="modal-header">
      <h3>Title</h3>
      <button class="modal-close">&times;</button>
    </div>
    <div class="modal-body">
      <!-- Content -->
    </div>
    <div class="modal-footer">
      <button class="btn-secondary">Cancel</button>
      <button class="btn-primary">Confirm</button>
    </div>
  </div>
</div>
```

### Responsive Design

- **Desktop (>1280px)**: Full sidebar, 3-4 column grid
- **Tablet (768px-1280px)**: Collapsible sidebar, 2-3 column grid
- **Mobile (<768px)**: Hidden sidebar (hamburger menu), 1 column grid

### Dark Mode Support

Tüm componentler için dark mode desteği:

```css
@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #1a202c;
    --bg-secondary: #2d3748;
    --text-primary: #e2e8f0;
    --text-secondary: #a0aec0;
  }
}
```

## Security Considerations

1. **Authentication**: Tüm endpoint'ler `@developer_required` decorator ile korunacak
2. **Input Validation**: Tüm user input'ları validate edilecek
3. **SQL Injection**: Parameterized queries kullanılacak
4. **XSS Protection**: Output encoding yapılacak
5. **CSRF Protection**: Flask-WTF CSRF token'ları kullanılacak
6. **Rate Limiting**: API endpoint'leri için rate limiting uygulanacak
7. **Audit Logging**: Tüm kritik işlemler loglanacak
8. **Secure File Operations**: Backup/Config dosya işlemleri güvenli path kontrolü ile yapılacak

## Performance Optimization

1. **Caching**: Redis ile frequently accessed data cache'lenecek
2. **Lazy Loading**: Büyük data setleri pagination ile yüklenecek
3. **Async Operations**: Uzun süren işlemler background job olarak çalışacak
4. **Database Indexing**: Query performance için gerekli indexler oluşturulacak
5. **Frontend Optimization**: Minification, compression, CDN kullanımı
6. **Connection Pooling**: Database ve Redis connection pool'ları optimize edilecek

## Deployment Considerations

1. **Environment Variables**: Hassas bilgiler environment variable'larda saklanacak
2. **Database Migrations**: Alembic ile version-controlled migrations
3. **Backup Strategy**: Otomatik günlük backup'lar
4. **Monitoring**: Production'da error tracking (Sentry gibi)
5. **Logging**: Structured logging (JSON format)
6. **Health Checks**: Kubernetes/Docker health check endpoint'leri
