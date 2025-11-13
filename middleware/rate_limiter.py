"""
Rate Limiter Middleware
API endpoint'leri için rate limiting
"""
import logging
from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiting servisi"""
    
    def __init__(self):
        """Rate limiter başlat"""
        self.requests = defaultdict(list)
        self.lock = threading.Lock()
        logger.info("RateLimiter başlatıldı")
    
    def is_rate_limited(self, key: str, limit: int = 100, window: int = 60) -> bool:
        """
        Rate limit kontrolü
        
        Args:
            key: Unique key (IP, user_id, etc.)
            limit: Maksimum istek sayısı
            window: Zaman penceresi (saniye)
            
        Returns:
            bool: Rate limit aşıldı mı
        """
        try:
            with self.lock:
                now = datetime.now()
                cutoff = now - timedelta(seconds=window)
                
                # Eski istekleri temizle
                self.requests[key] = [
                    req_time for req_time in self.requests[key]
                    if req_time > cutoff
                ]
                
                # Limit kontrolü
                if len(self.requests[key]) >= limit:
                    logger.warning(f"Rate limit aşıldı: {key} ({len(self.requests[key])}/{limit})")
                    return True
                
                # Yeni isteği ekle
                self.requests[key].append(now)
                return False
                
        except Exception as e:
            logger.error(f"Rate limit kontrolü hatası: {str(e)}", exc_info=True)
            return False  # Hata durumunda izin ver
    
    def get_remaining(self, key: str, limit: int = 100, window: int = 60) -> int:
        """
        Kalan istek sayısını getir
        
        Args:
            key: Unique key
            limit: Maksimum istek sayısı
            window: Zaman penceresi (saniye)
            
        Returns:
            int: Kalan istek sayısı
        """
        try:
            with self.lock:
                now = datetime.now()
                cutoff = now - timedelta(seconds=window)
                
                # Eski istekleri temizle
                self.requests[key] = [
                    req_time for req_time in self.requests[key]
                    if req_time > cutoff
                ]
                
                return max(0, limit - len(self.requests[key]))
                
        except Exception as e:
            logger.error(f"Remaining hesaplama hatası: {str(e)}", exc_info=True)
            return limit
    
    def clear_key(self, key: str):
        """
        Belirli bir key'in rate limit'ini temizle
        
        Args:
            key: Unique key
        """
        try:
            with self.lock:
                if key in self.requests:
                    del self.requests[key]
                    logger.info(f"Rate limit temizlendi: {key}")
        except Exception as e:
            logger.error(f"Rate limit temizleme hatası: {str(e)}", exc_info=True)
    
    def clear_all(self):
        """Tüm rate limit'leri temizle"""
        try:
            with self.lock:
                self.requests.clear()
                logger.info("Tüm rate limit'ler temizlendi")
        except Exception as e:
            logger.error(f"Tüm rate limit temizleme hatası: {str(e)}", exc_info=True)


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limit(limit: int = 100, window: int = 60, key_func=None):
    """
    Rate limiting decorator
    
    Args:
        limit: Maksimum istek sayısı
        window: Zaman penceresi (saniye)
        key_func: Key oluşturma fonksiyonu (default: IP adresi)
        
    Usage:
        @rate_limit(limit=10, window=60)
        def my_endpoint():
            return "OK"
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Key oluştur
                if key_func:
                    key = key_func()
                else:
                    # Default: IP adresi
                    key = request.remote_addr
                
                # Rate limit kontrolü
                if _rate_limiter.is_rate_limited(key, limit, window):
                    remaining = _rate_limiter.get_remaining(key, limit, window)
                    return jsonify({
                        'success': False,
                        'error': 'Rate limit exceeded',
                        'message': f'Too many requests. Try again later.',
                        'limit': limit,
                        'window': window,
                        'remaining': remaining
                    }), 429
                
                # İsteği işle
                response = f(*args, **kwargs)
                
                # Rate limit header'ları ekle
                if hasattr(response, 'headers'):
                    remaining = _rate_limiter.get_remaining(key, limit, window)
                    response.headers['X-RateLimit-Limit'] = str(limit)
                    response.headers['X-RateLimit-Remaining'] = str(remaining)
                    response.headers['X-RateLimit-Window'] = str(window)
                
                return response
                
            except Exception as e:
                logger.error(f"Rate limit decorator hatası: {str(e)}", exc_info=True)
                return f(*args, **kwargs)  # Hata durumunda normal devam et
        
        return decorated_function
    return decorator


def get_rate_limiter() -> RateLimiter:
    """
    Global rate limiter instance'ını getir
    
    Returns:
        RateLimiter: Rate limiter instance
    """
    return _rate_limiter
