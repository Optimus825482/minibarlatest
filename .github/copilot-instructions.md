# Minibar Takip Sistemi — Copilot Workspace Instructions

## Project Overview

Otel minibar envanter yönetim sistemi. Flask + PostgreSQL + Redis + Celery stack. Merit Royal Hotel zinciri için tasarlanmış, KKTC timezone (Europe/Nicosia) ile çalışır.

**Dil:** Kod İngilizce, UI/iş mantığı Türkçe. Model adları PascalCase Türkçe (`Kullanici`, `Otel`, `Urun`), tablo adları snake_case çoğul (`kullanicilar`, `oteller`).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Flask 3.0 |
| ORM | SQLAlchemy (Flask-SQLAlchemy) |
| Database | PostgreSQL 15 |
| Cache/Broker | Redis 7 |
| Task Queue | Celery 5.3 |
| WSGI | Gunicorn (gthread, 3 workers × 6 threads) |
| ML | scikit-learn (Isolation Forest), pandas |
| Frontend | Jinja2 + Tailwind CSS + vanilla JS |
| Forms | WTForms (Flask-WTF, CSRF enabled) |
| Reports | openpyxl (Excel), reportlab (PDF) |
| Deploy | Docker (multi-stage), Coolify |

## Build & Test Commands

```bash
# Install
pip install -r requirements.txt

# Run locally (Erkan runs from external terminal — port 5017)
flask run --port 5017

# Test
pytest --cov=. --cov-report=html
pytest -v --tb=short

# Docker
make setup      # First-time: build + start + init-db
make start      # docker-compose up -d
make stop       # docker-compose stop
make backup     # pg_dump
make restore    # pg_restore

# Celery
celery -A celery_app.celery worker --loglevel=info
celery -A celery_app.celery beat --loglevel=info
```

## Architecture

```
app.py                      # Flask factory, ProxyFix, blueprint registration
config.py                   # Single Config class, env-based, PostgreSQL only
models.py                   # Monolithic SQLAlchemy models (20+ tables)
models/                     # Modular model split (mirrors models.py)
forms.py                    # WTForms with Turkish validation
routes/                     # 35 route files — NOT Blueprints, direct @app.route()
  __init__.py               # register_all_routes(app) — central registration
utils/                      # 45+ service/helper modules
  ml/                       # 16 ML modules (anomaly detection pipeline)
  monitoring/               # 11 monitoring modules
middleware/                  # metrics_middleware.py, rate_limiter.py
templates/                  # Jinja2, organized by role (admin/, depo_sorumlusu/, etc.)
static/                     # Tailwind, Chart.js, PWA assets, vendor libs
ml_models/                  # Persisted sklearn .pkl files
migrations_manual/          # Hand-crafted Alembic migration scripts
```

### Route Registration Pattern

Routes register directly on `app` (no Flask Blueprints):

```python
# routes/some_routes.py
def register_some_routes(app):
    @app.route('/some-endpoint')
    @login_required
    @role_required('admin')
    def some_endpoint():
        ...

# routes/__init__.py
def register_all_routes(app):
    register_some_routes(app)
    # ... 30+ more
```

### Authorization Decorators

```python
@login_required              # Session check
@role_required('admin')      # Role enforcement
@setup_required              # System setup completion check
```

Roller: `superadmin`, `sistem_yoneticisi`, `admin`, `depo_sorumlusu`, `kat_sorumlusu`

### Audit Trail

Her CREATE/UPDATE/DELETE → `AuditLog` tablosu. Before/after JSON değerleri, user ID, KKTC timestamp.

### Caching Strategy

Redis ile sadece **master data** cache'lenir (ürünler, oteller, katlar, odalar, setup'lar). Stok, zimmet, minibar işlemleri **asla** cache'lenmez.

## Conventions

- **Service modülleri:** `*_servisleri.py` (Türkçe) veya `*_service.py` (İngilizce) — iş mantığı routes'tan ayrı
- **API endpoints:** `/api/` prefix ile RESTful, JSON response
- **Enum kullanımı:** `KullaniciRol`, `MinibarIslemTipi`, `StokHareketTipi` — string enum'lar
- **Timezone:** Her yerde `Europe/Nicosia` (KKTC) — `datetime.now()` yerine timezone-aware kullan
- **Cache version:** `config.py → CACHE_VERSION` — statik asset cache busting için güncelle
- **Database:** Sadece PostgreSQL. MySQL desteği kaldırıldı
- **Parameterized queries:** SQLAlchemy ORM kullan, raw SQL'de parametreli sorgular zorunlu

## Potential Pitfalls

- `models.py` monolitik (~1000+ satır) — dikkatli geniş diff'ler yapma
- Route'lar Blueprint değil, `app` üzerine kayıt — name collision'lara dikkat
- `migrations_manual/` klasöründe migration'lar elle yazılır, Alembic autogenerate güvenilir değil
- ML sistem opsiyonel (`ML_ENABLED` env var) — production'da kaynak kullanımına dikkat
- Gunicorn timeout 300s (5dk) — import süresi ~120s, uzun rapor sorguları var
- Production'da `SESSION_COOKIE_SECURE=true` olmalı

## Key Documentation

Ayrıntılı dökümantasyon için `docs/` altına bak. Ana referanslar:

- Sistem mimarisi: [docs/TEKNIK_SISTEM_DOKUMANI.md](docs/TEKNIK_SISTEM_DOKUMANI.md)
- Celery kullanımı: [docs/CELERY_KULLANIM_KILAVUZU.md](docs/CELERY_KULLANIM_KILAVUZU.md)
- ML pipeline: [docs/ML_SYSTEM_COMPLETE_FLOW.md](docs/ML_SYSTEM_COMPLETE_FLOW.md)
- Cache sistemi: [docs/CACHE_KULLANIM_KILAVUZU.md](docs/CACHE_KULLANIM_KILAVUZU.md)
- DB optimizasyon: [docs/DATABASE_OPTIMIZATION_GUIDE.md](docs/DATABASE_OPTIMIZATION_GUIDE.md)
- Coolify deploy: [docs/COOLIFY_DEPLOYMENT_GUIDE.md](docs/COOLIFY_DEPLOYMENT_GUIDE.md)
- Rol erişim: [docs/ROL_BAZLI_ERISIM_KONTROLU.md](docs/ROL_BAZLI_ERISIM_KONTROLU.md)
