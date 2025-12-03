"""
Query Result Caching
TTL-based caching for frequently accessed data
"""

from functools import lru_cache, wraps
from datetime import datetime, timedelta
from typing import Any, Optional
import hashlib
import json
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')

def get_kktc_now():
    """Kıbrıs saat diliminde şu anki zamanı döndürür."""
    return datetime.now(KKTC_TZ)


class QueryCache:
    """TTL-based query result cache"""
    
    def __init__(self, ttl_seconds=300):
        """
        Args:
            ttl_seconds: Time to live in seconds (default: 5 minutes)
        """
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            
            # Check if expired
            if get_kktc_now() - timestamp < timedelta(seconds=self.ttl):
                return value
            
            # Expired, remove from cache
            del self.cache[key]
        
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache"""
        self.cache[key] = (value, get_kktc_now())
    
    def invalidate(self, pattern: Optional[str] = None):
        """
        Invalidate cache entries
        
        Args:
            pattern: If provided, only invalidate keys containing this pattern
                    If None, invalidate all
        """
        if pattern:
            keys_to_delete = [k for k in self.cache if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]
        else:
            self.cache.clear()
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'ttl_seconds': self.ttl
        }
    
    def cached(self, key_prefix: str = ''):
        """
        Decorator for caching function results
        
        Usage:
            @cache.cached(key_prefix='urunler')
            def get_all_urunler():
                return Urun.query.all()
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                key_parts = [key_prefix, func.__name__]
                
                # Add args to key
                if args:
                    key_parts.append(str(args))
                if kwargs:
                    key_parts.append(str(sorted(kwargs.items())))
                
                cache_key = hashlib.md5(
                    '|'.join(key_parts).encode()
                ).hexdigest()
                
                # Try to get from cache
                result = self.get(cache_key)
                if result is not None:
                    return result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result)
                
                return result
            
            return wrapper
        return decorator


# Global cache instance
query_cache = QueryCache(ttl_seconds=300)  # 5 minutes


# Cached helper functions
@lru_cache(maxsize=128)
def get_aktif_urun_gruplari():
    """
    Cache active product groups
    Uses Python's built-in LRU cache
    """
    from models import UrunGrup
    return UrunGrup.query.filter_by(aktif=True).all()


def get_stok_toplamlari_cached(urun_ids: tuple):
    """
    Cache stock totals
    
    Args:
        urun_ids: Tuple of product IDs (must be tuple for caching)
    """
    cache_key = f"stok_toplam_{','.join(map(str, sorted(urun_ids)))}"
    
    result = query_cache.get(cache_key)
    if result:
        return result
    
    # Calculate stock totals
    from utils.helpers import get_stok_toplamlari
    result = get_stok_toplamlari(list(urun_ids))
    
    query_cache.set(cache_key, result)
    return result


def get_kritik_stok_urunler_cached():
    """Cache critical stock products"""
    cache_key = "kritik_stok_urunler"
    
    result = query_cache.get(cache_key)
    if result:
        return result
    
    from utils.helpers import get_kritik_stok_urunler
    result = get_kritik_stok_urunler()
    
    query_cache.set(cache_key, result)
    return result


# Cache invalidation helpers
def invalidate_stok_cache():
    """Invalidate all stock-related caches"""
    query_cache.invalidate('stok')
    query_cache.invalidate('kritik')


def invalidate_urun_cache():
    """Invalidate all product-related caches"""
    query_cache.invalidate('urun')
    get_aktif_urun_gruplari.cache_clear()  # Clear LRU cache


def invalidate_all_caches():
    """Invalidate all caches"""
    query_cache.invalidate()
    get_aktif_urun_gruplari.cache_clear()
