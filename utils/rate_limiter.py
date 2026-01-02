"""
Rate Limiting Modülü

Brute force ve DDoS saldırılarına karşı koruma sağlar.
Redis backend kullanarak distributed rate limiting destekler.

Özellikler:
- Login endpoint'leri için sıkı limitler
- API endpoint'leri için esnek limitler
- Whitelist desteği (health check, static files)
- Custom error handler

Kullanım:
    from utils.rate_limiter import init_rate_limiter, limiter
    
    # app.py'de
    init_rate_limiter(app)
    
    # Route'larda
    @app.route('/api/data')
    @limiter.limit("100 per minute")
    def get_data():
        pass
"""

import logging
from flask import request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

# Global limiter instance
limiter = None


def get_client_ip():
    """
    Client IP adresini al.
    Proxy arkasındaysa X-Forwarded-For header'ını kontrol et.
    """
    # Cloudflare, nginx gibi proxy'ler için
    if request.headers.get('X-Forwarded-For'):
        # İlk IP gerçek client IP'si
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return get_remote_address()


def _test_redis_connection(redis_url: str) -> bool:
    """Redis bağlantısını test et"""
    try:
        import redis
        client = redis.from_url(
            redis_url,
            socket_connect_timeout=2,
            socket_timeout=2
        )
        client.ping()
        return True
    except Exception:
        return False


def init_rate_limiter(app):
    """
    Rate limiter'ı Flask uygulamasına bağla.
    Redis yoksa otomatik olarak memory moduna geçer.
    
    Args:
        app: Flask application instance
        
    Returns:
        Limiter: Configured limiter instance
    """
    global limiter
    
    # Redis URL'i config'den al
    redis_url = app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    
    # Development modunda memory kullan
    is_development = app.config.get('IS_DEVELOPMENT', False)
    
    # Storage URI belirleme
    use_memory = is_development
    
    if not is_development:
        # Production'da Redis bağlantısını test et
        if _test_redis_connection(redis_url):
            storage_uri = redis_url
            logger.info(f"🔧 Rate Limiter: Redis storage ({redis_url[:30]}...)")
        else:
            # Redis yoksa memory'ye fallback
            use_memory = True
            logger.warning("⚠️ Rate Limiter: Redis bağlantısı yok, memory moduna geçiliyor")
    
    if use_memory:
        storage_uri = "memory://"
        logger.info("🔧 Rate Limiter: Memory storage")
    
    try:
        limiter = Limiter(
            key_func=get_client_ip,
            app=app,
            storage_uri=storage_uri,
            storage_options={
                "socket_connect_timeout": 2,
                "socket_timeout": 2
            } if not use_memory else {},
            strategy="fixed-window",
            default_limits=["10000 per day", "2000 per hour"],  # Production: 3 otel, 600 oda, çoklu kontrol
            headers_enabled=True,  # X-RateLimit headers
            swallow_errors=True,  # Hata durumunda app çalışmaya devam etsin
        )
        
        # Error handler
        @app.errorhandler(429)
        def ratelimit_handler(e):
            """Rate limit aşıldığında dönen response"""
            logger.warning(f"⚠️ Rate limit aşıldı: {get_client_ip()} - {request.path}")
            
            # API endpoint mi kontrol et
            if request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'Çok fazla istek gönderdiniz. Lütfen biraz bekleyin.',
                    'retry_after': e.description
                }), 429
            else:
                from flask import render_template
                return render_template('errors/429.html'), 429
        
        logger.info("✅ Rate Limiter başarıyla aktifleştirildi")
        return limiter
        
    except Exception as e:
        logger.error(f"❌ Rate Limiter başlatılamadı: {str(e)}")
        # Fallback: Memory-based limiter
        limiter = Limiter(
            key_func=get_client_ip,
            app=app,
            storage_uri="memory://",
            strategy="fixed-window",
            default_limits=["10000 per day", "2000 per hour"],
            swallow_errors=True,
        )
        logger.warning("⚠️ Rate Limiter memory modunda çalışıyor (fallback)")
        return limiter


# ============================================
# ENDPOINT-SPESİFİK LİMİTLER
# ============================================

# Login/Auth - Brute force koruması
LOGIN_LIMIT = "5 per minute"
LOGIN_LIMIT_STRICT = "10 per hour"

# API Genel
API_LIMIT_DEFAULT = "100 per minute"
API_LIMIT_HEAVY = "30 per minute"  # Ağır işlemler (rapor, export)

# Dosya yükleme
UPLOAD_LIMIT = "10 per hour"

# Public endpoint'ler
PUBLIC_LIMIT = "30 per minute"


def exempt_when_authenticated():
    """
    Authenticated kullanıcılar için rate limit'i gevşet.
    Session'da kullanıcı varsa True döner.
    """
    from flask import session
    return 'kullanici_id' in session


# Whitelist - Bu path'ler rate limit'ten muaf
EXEMPT_PATHS = [
    '/health',
    '/ready',
    '/static/',
    '/sw.js',
    '/manifest.json',
    '/favicon.ico',
]


def should_exempt():
    """Rate limit'ten muaf mı kontrol et"""
    path = request.path
    for exempt_path in EXEMPT_PATHS:
        if path.startswith(exempt_path):
            return True
    return False


# ============================================
# QR RATE LIMITER
# ============================================

class QRRateLimiter:
    """
    QR kod işlemleri için özel rate limiter.
    Brute force ve abuse koruması sağlar.
    """
    
    # Rate limit ayarları
    QR_SCAN_LIMIT = 30      # Dakikada maksimum QR tarama
    QR_GENERATE_LIMIT = 10  # Dakikada maksimum QR üretme
    
    # In-memory cache (Redis yoksa)
    _scan_cache = {}
    _generate_cache = {}
    
    @classmethod
    def _get_redis(cls):
        """Redis client'ı al"""
        global limiter
        if limiter and hasattr(limiter, '_storage') and hasattr(limiter._storage, '_redis'):
            return limiter._storage._redis
        return None
    
    @classmethod
    def _clean_old_entries(cls, cache: dict, window_seconds: int = 60):
        """Eski cache entry'lerini temizle"""
        import time
        current_time = time.time()
        keys_to_delete = [
            key for key, (count, timestamp) in cache.items()
            if current_time - timestamp > window_seconds
        ]
        for key in keys_to_delete:
            del cache[key]
    
    @classmethod
    def check_qr_scan_limit(cls, ip: str) -> bool:
        """
        QR tarama rate limit kontrolü.
        
        Args:
            ip: Client IP adresi
            
        Returns:
            bool: True = izin ver, False = limit aşıldı
        """
        import time
        
        redis = cls._get_redis()
        
        if redis:
            # Redis ile kontrol
            key = f"qr_scan:{ip}"
            try:
                count = redis.incr(key)
                if count == 1:
                    redis.expire(key, 60)  # 1 dakika TTL
                return count <= cls.QR_SCAN_LIMIT
            except Exception:
                pass
        
        # In-memory fallback
        cls._clean_old_entries(cls._scan_cache)
        current_time = time.time()
        
        if ip in cls._scan_cache:
            count, timestamp = cls._scan_cache[ip]
            if current_time - timestamp < 60:
                count += 1
                cls._scan_cache[ip] = (count, timestamp)
                return count <= cls.QR_SCAN_LIMIT
        
        cls._scan_cache[ip] = (1, current_time)
        return True
    
    @classmethod
    def check_qr_generate_limit(cls, ip: str) -> bool:
        """
        QR üretme rate limit kontrolü.
        
        Args:
            ip: Client IP adresi
            
        Returns:
            bool: True = izin ver, False = limit aşıldı
        """
        import time
        
        redis = cls._get_redis()
        
        if redis:
            # Redis ile kontrol
            key = f"qr_generate:{ip}"
            try:
                count = redis.incr(key)
                if count == 1:
                    redis.expire(key, 60)  # 1 dakika TTL
                return count <= cls.QR_GENERATE_LIMIT
            except Exception:
                pass
        
        # In-memory fallback
        cls._clean_old_entries(cls._generate_cache)
        current_time = time.time()
        
        if ip in cls._generate_cache:
            count, timestamp = cls._generate_cache[ip]
            if current_time - timestamp < 60:
                count += 1
                cls._generate_cache[ip] = (count, timestamp)
                return count <= cls.QR_GENERATE_LIMIT
        
        cls._generate_cache[ip] = (1, current_time)
        return True
