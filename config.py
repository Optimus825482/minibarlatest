import os
from datetime import timedelta

class Config:
    """Flask uygulama yapılandırması - GÜVENLİK İYİLEŞTİRMELERİ"""

    # Cache Busting Version - Her değişiklikte artır
    CACHE_VERSION = '1.1.87'

    ENV = os.getenv('FLASK_ENV', os.getenv('ENV', 'production')).lower()
    IS_DEVELOPMENT = ENV in {'development', 'dev', 'local'}
    
    # Template Caching - Production'da bile template değişikliklerini algıla
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Static dosyalar için cache'i devre dışı bırak

    # Database Configuration - PostgreSQL Only (MySQL support removed)
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # PostgreSQL variables
    PGHOST = os.getenv('PGHOST')
    PGUSER = os.getenv('PGUSER')
    PGPASSWORD = os.getenv('PGPASSWORD')
    PGDATABASE = os.getenv('PGDATABASE')
    PGPORT = os.getenv('PGPORT', '5432')
    
    # Database URI Construction
    if DATABASE_URL:
        # Coolify/Heroku DATABASE_URL kullan
        if DATABASE_URL.startswith('postgres://'):
            # Heroku postgres:// -> postgresql://
            SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace('postgres://', 'postgresql://')
        elif DATABASE_URL.startswith('postgresql://'):
            SQLALCHEMY_DATABASE_URI = DATABASE_URL
        else:
            SQLALCHEMY_DATABASE_URI = DATABASE_URL
    elif PGHOST and PGUSER:
        # PostgreSQL connection (Coolify internal)
        SQLALCHEMY_DATABASE_URI = f'postgresql+psycopg2://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}'
    else:
        # Local development için .env dosyasından oku
        DB_HOST = os.getenv('DB_HOST', 'localhost')
        DB_USER = os.getenv('DB_USER', 'postgres')
        DB_PASSWORD = os.getenv('DB_PASSWORD', '')
        DB_NAME = os.getenv('DB_NAME', 'minibar_takip')
        DB_PORT = os.getenv('DB_PORT', '5432')
        
        SQLALCHEMY_DATABASE_URI = f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # PostgreSQL Optimized Engine Options - Performance Optimized
    SQLALCHEMY_ENGINE_OPTIONS = {
        # Connection Pool Configuration - OPTIMIZED FOR GUNICORN (4 workers × 4 threads)
        'pool_size': 8,                     # 8 connections per worker (matches thread count)
        'max_overflow': 8,                  # Max 16 connections per worker
        'pool_timeout': 30,                 # 30 saniye wait timeout
        'pool_recycle': 900,                # 15 dakikada bir recycle (cloud-friendly)
        'pool_pre_ping': True,              # Health check before use
        
        # Connection Management
        'pool_reset_on_return': 'rollback',  # Reset connections on return
        
        # PostgreSQL Specific Options
        'connect_args': {
            'connect_timeout': 10,          # 10 saniye connection timeout
            'options': '-c timezone=Europe/Nicosia -c statement_timeout=60000',  # 60 saniye statement timeout (raporlar için)
            'application_name': 'minibar_takip',
            
            # Keep-alive settings (cloud deployment uyumlu)
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
        },
        
        # Execution Options
        'execution_options': {
            'isolation_level': 'READ COMMITTED'
        }
    }
    # Flask ayarları - GÜVENLİK İYİLEŞTİRMELERİ
    SECRET_KEY = os.getenv('SECRET_KEY')

    if not SECRET_KEY:
        if IS_DEVELOPMENT:
            SECRET_KEY = 'development-secret-key-change-in-production'
        else:
            raise ValueError("SECRET_KEY environment variable is required. Set a strong secret key in production.")

    if not IS_DEVELOPMENT and len(SECRET_KEY) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters long for security.")
    
    # Oturum ayarları - GÜVENLİK: Session güvenliği artırıldı
    # Coolify HTTP kullanıyorsa SECURE=False olmalı
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'  # 'Strict' önerilen ama 'Lax' uyumluluk için
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # 8 saat - otel personeli gün boyu çalışır
    
    # WTF Forms ayarları - GÜVENLİK
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 saat CSRF token timeout
    WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token']
    
    # Dosya yükleme ayarları - GÜVENLİK
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB - Optimized (was 100MB)
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'xlsm', 'pdf', 'sql'}  # xlsm ve SQL backup için eklendi
    
    # GÜVENLİK HEADERS - Production için önerilen
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; img-src 'self' data: https:; connect-src 'self'",
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'  # HTTPS için
    }
    
    # Celery Configuration (Redis sadece broker olarak kullanılıyor, cache yok)
    # Celery Configuration (Redis sadece broker olarak kullanılıyor, cache yok)
    # Easypanel/Docker: REDIS_URL env var'ından authenticated URL alınır
    # Örnek: redis://default:password@minibar_redis:6379/0
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True
    
    # Celery Task Limits (29.12.2025 - Magic numbers config'e taşındı)
    CELERY_TASK_TIME_LIMIT = int(os.getenv('CELERY_TASK_TIME_LIMIT', '3600'))  # 1 saat max
    CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv('CELERY_TASK_SOFT_TIME_LIMIT', '3000'))  # 50 dakika soft
    CELERY_WORKER_PREFETCH = int(os.getenv('CELERY_WORKER_PREFETCH', '1'))
    CELERY_MAX_TASKS_PER_CHILD = int(os.getenv('CELERY_MAX_TASKS_PER_CHILD', '1000'))
    
    # ============================================
    # CACHE CONFIGURATION (Master Data Only)
    # ============================================
    # Cache SADECE master data için kullanılır (ürün listesi, setup tanımları, otel/kat/oda listeleri)
    # Stok, zimmet, DND gibi transactional data ASLA cache'lenmez!
    CACHE_ENABLED = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
    # REDIS_URL yukarıda tanımlandı, cache ve rate limiter de aynı URL'i kullanır
    
    # ============================================
    # RATE LIMITING CONFIGURATION
    # ============================================
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    RATE_LIMIT_DEFAULT = os.getenv('RATE_LIMIT_DEFAULT', '20000 per day, 3000 per hour, 120 per minute')
    RATE_LIMIT_LOGIN = os.getenv('RATE_LIMIT_LOGIN', '10 per minute')
    RATE_LIMIT_API = os.getenv('RATE_LIMIT_API', '300 per minute')
    RATE_LIMIT_POLLING = os.getenv('RATE_LIMIT_POLLING', '600 per minute')
