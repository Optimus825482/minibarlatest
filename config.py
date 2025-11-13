import os
from datetime import timedelta

class Config:
    """Flask uygulama yapılandırması - GÜVENLİK İYİLEŞTİRMELERİ"""

    ENV = os.getenv('FLASK_ENV', os.getenv('ENV', 'production')).lower()
    IS_DEVELOPMENT = ENV in {'development', 'dev', 'local'}

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
    
    # PostgreSQL Optimized Engine Options - Coolify Production
    SQLALCHEMY_ENGINE_OPTIONS = {
        # Connection Pool Configuration
        'pool_size': 5,                     # 5 connection pool
        'max_overflow': 10,                 # Max 15 connection total
        'pool_timeout': 30,                 # 30 saniye wait timeout
        'pool_recycle': 3600,               # 1 saatte bir recycle
        'pool_pre_ping': True,              # Health check before use
        
        # PostgreSQL Specific Options
        'connect_args': {
            'connect_timeout': 10,          # 10 saniye connection timeout
            'options': '-c timezone=utc -c statement_timeout=30000',  # 30 saniye query timeout
            'application_name': 'minibar_takip',
            
            # Keep-alive settings
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
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)  # 1 saatten 30 dakikaya düşürüldü
    
    # WTF Forms ayarları - GÜVENLİK
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 saat CSRF token timeout
    WTF_CSRF_HEADERS = ['X-CSRFToken', 'X-CSRF-Token']
    
    # Dosya yükleme ayarları - GÜVENLİK
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB - backup restore için artırıldı
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'pdf', 'sql'}  # SQL backup için eklendi
    
    # GÜVENLİK HEADERS - Production için önerilen
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; img-src 'self' data: https:; connect-src 'self'",
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'  # HTTPS için
    }
    
    # Redis Cache Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Flask-Caching Configuration
    CACHE_TYPE = 'redis' if not IS_DEVELOPMENT else 'simple'  # Development'ta simple cache
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 3600  # 1 saat default timeout
    CACHE_KEY_PREFIX = 'minibar_cache:'
    
    # Cache Timeouts (saniye)
    CACHE_TIMEOUT_FIYAT = 3600  # 1 saat - Fiyat hesaplamaları
    CACHE_TIMEOUT_KAR = 1800  # 30 dakika - Kar analizleri
    CACHE_TIMEOUT_STOK = 300  # 5 dakika - Stok durumu
    CACHE_TIMEOUT_RAPOR = 600  # 10 dakika - Raporlar
    
    # Celery Configuration
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True
