"""
Cache Decorator
Redis cache decorator ve cache stratejileri
"""
import logging
import json
import hashlib
from functools import wraps
from typing import Any, Callable, Optional
from datetime import timedelta
from flask import request

logger = logging.getLogger(__name__)


class CacheStrategy:
    """Cache stratejisi yönetimi"""
    
    def __init__(self, redis_client=None):
        """
        Cache strategy başlat
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        logger.info("CacheStrategy başlatıldı")
    
    def get_redis(self):
        """Redis client'ı getir"""
        if self.redis is None:
            try:
                from extensions import redis_client
                self.redis = redis_client
            except Exception as e:
                logger.warning(f"Redis client alınamadı: {str(e)}")
        return self.redis
    
    def generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Cache key oluştur
        
        Args:
            prefix: Key prefix
            *args: Fonksiyon argümanları
            **kwargs: Fonksiyon keyword argümanları
            
        Returns:
            str: Cache key
        """
        try:
            # Argümanları serialize et
            key_data = {
                'args': args,
                'kwargs': kwargs
            }
            key_str = json.dumps(key_data, sort_keys=True)
            
            # Hash oluştur
            key_hash = hashlib.md5(key_str.encode()).hexdigest()
            
            return f"{prefix}:{key_hash}"
            
        except Exception as e:
            logger.error(f"Cache key oluşturma hatası: {str(e)}", exc_info=True)
            return f"{prefix}:default"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Cache'den değer al
        
        Args:
            key: Cache key
            
        Returns:
            Any: Cache'deki değer veya None
        """
        try:
            redis = self.get_redis()
            if redis is None:
                return None
            
            value = redis.get(key)
            if value:
                return json.loads(value)
            
            return None
            
        except Exception as e:
            logger.error(f"Cache get hatası: {str(e)}", exc_info=True)
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """
        Cache'e değer kaydet
        
        Args:
            key: Cache key
            value: Kaydedilecek değer
            ttl: Time to live (saniye)
        """
        try:
            redis = self.get_redis()
            if redis is None:
                return
            
            value_json = json.dumps(value)
            redis.setex(key, ttl, value_json)
            
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            
        except Exception as e:
            logger.error(f"Cache set hatası: {str(e)}", exc_info=True)
    
    def delete(self, key: str):
        """
        Cache'den sil
        
        Args:
            key: Cache key
        """
        try:
            redis = self.get_redis()
            if redis is None:
                return
            
            redis.delete(key)
            logger.debug(f"Cache deleted: {key}")
            
        except Exception as e:
            logger.error(f"Cache delete hatası: {str(e)}", exc_info=True)
    
    def invalidate_pattern(self, pattern: str):
        """
        Pattern'e uyan tüm cache'leri sil
        
        Args:
            pattern: Cache key pattern (örn: "user:*")
        """
        try:
            redis = self.get_redis()
            if redis is None:
                return
            
            keys = redis.keys(pattern)
            if keys:
                redis.delete(*keys)
                logger.info(f"Cache invalidated: {len(keys)} keys ({pattern})")
            
        except Exception as e:
            logger.error(f"Cache invalidate hatası: {str(e)}", exc_info=True)
    
    def warm_cache(self, key: str, func: Callable, *args, **kwargs):
        """
        Cache warming - cache'i önceden doldur
        
        Args:
            key: Cache key
            func: Çalıştırılacak fonksiyon
            *args: Fonksiyon argümanları
            **kwargs: Fonksiyon keyword argümanları
        """
        try:
            # Fonksiyonu çalıştır
            result = func(*args, **kwargs)
            
            # Cache'e kaydet
            self.set(key, result)
            
            logger.info(f"Cache warmed: {key}")
            
        except Exception as e:
            logger.error(f"Cache warming hatası: {str(e)}", exc_info=True)


# Global cache strategy instance
_cache_strategy = CacheStrategy()


def cached(ttl: int = 300, key_prefix: str = None, invalidate_on_error: bool = False):
    """
    Cache decorator
    
    Args:
        ttl: Time to live (saniye)
        key_prefix: Cache key prefix
        invalidate_on_error: Hata durumunda cache'i sil
        
    Usage:
        @cached(ttl=60, key_prefix='user_data')
        def get_user_data(user_id):
            return fetch_from_db(user_id)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Key prefix
                prefix = key_prefix or f.__name__
                
                # Cache key oluştur
                cache_key = _cache_strategy.generate_cache_key(prefix, *args, **kwargs)
                
                # Cache'den al
                cached_value = _cache_strategy.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value
                
                # Cache miss - fonksiyonu çalıştır
                logger.debug(f"Cache miss: {cache_key}")
                result = f(*args, **kwargs)
                
                # Cache'e kaydet
                _cache_strategy.set(cache_key, result, ttl)
                
                return result
                
            except Exception as e:
                logger.error(f"Cache decorator hatası: {str(e)}", exc_info=True)
                
                # Hata durumunda cache'i sil
                if invalidate_on_error:
                    try:
                        _cache_strategy.delete(cache_key)
                    except:
                        pass
                
                # Fonksiyonu normal çalıştır
                return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def cache_invalidate(key_prefix: str):
    """
    Cache invalidation decorator
    
    Args:
        key_prefix: Silinecek cache key prefix
        
    Usage:
        @cache_invalidate('user_data')
        def update_user(user_id):
            # Update user
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Fonksiyonu çalıştır
                result = f(*args, **kwargs)
                
                # Cache'i sil
                pattern = f"{key_prefix}:*"
                _cache_strategy.invalidate_pattern(pattern)
                
                return result
                
            except Exception as e:
                logger.error(f"Cache invalidate decorator hatası: {str(e)}", exc_info=True)
                raise
        
        return decorated_function
    return decorator


def get_cache_strategy() -> CacheStrategy:
    """
    Global cache strategy instance'ını getir
    
    Returns:
        CacheStrategy: Cache strategy instance
    """
    return _cache_strategy
