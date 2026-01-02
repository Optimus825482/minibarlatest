"""
Akıllı Cache Yönetim Modülü

SADECE statik/master data için cache kullanır.
Transactional data (stok, zimmet, DND) ASLA cache'lenmez!

Cache'lenebilir veriler:
- Ürün listesi (dropdown'lar için)
- Setup tanımları
- Otel/Kat/Oda listeleri
- Kullanıcı yetkileri

Cache'lenmemesi gerekenler:
- Stok miktarları
- Zimmet bakiyeleri
- DND durumları
- Görev durumları
- Minibar içerikleri

Kullanım:
    from utils.cache_manager import cache_manager, cached_master_data
    
    # Decorator ile
    @cached_master_data(timeout=300, key_prefix='urunler')
    def get_urun_listesi():
        return Urun.query.filter_by(aktif=True).all()
    
    # Manuel invalidation
    cache_manager.invalidate('urunler')
"""

import logging
import hashlib
from functools import wraps
from typing import Optional, Any, Callable
from flask import current_app

logger = logging.getLogger(__name__)

# Global cache instance
_cache = None
_cache_enabled = False


class CacheManager:
    """
    Redis tabanlı cache yöneticisi.
    Sadece master data için kullanılır.
    """
    
    # Cache key prefix'leri
    PREFIX = "minibar:"
    
    # TTL değerleri (saniye)
    TTL_SHORT = 60          # 1 dakika - Sık değişen master data
    TTL_MEDIUM = 300        # 5 dakika - Normal master data
    TTL_LONG = 600          # 10 dakika - Nadiren değişen data
    TTL_VERY_LONG = 3600    # 1 saat - Statik data
    
    # Cache'lenebilir key'ler ve TTL'leri
    ALLOWED_KEYS = {
        'urunler': TTL_MEDIUM,           # Ürün listesi
        'urun_gruplari': TTL_LONG,       # Ürün grupları
        'setuplar': TTL_LONG,            # Setup tanımları
        'setup_icerik': TTL_LONG,        # Setup içerikleri
        'oteller': TTL_VERY_LONG,        # Otel listesi
        'katlar': TTL_LONG,              # Kat listesi
        'odalar': TTL_MEDIUM,            # Oda listesi
        'oda_tipleri': TTL_VERY_LONG,    # Oda tipleri
        'kullanici_yetki': TTL_SHORT,    # Kullanıcı yetkileri
    }
    
    # ASLA cache'lenmemesi gerekenler (güvenlik için)
    BLACKLISTED_KEYS = [
        'stok',
        'zimmet',
        'dnd',
        'gorev',
        'minibar_icerik',
        'bakiye',
        'miktar',
    ]
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.enabled = redis_client is not None
        
    def _make_key(self, key: str, *args) -> str:
        """Cache key oluştur"""
        if args:
            # Argümanları hash'le
            args_hash = hashlib.md5(str(args).encode()).hexdigest()[:8]
            return f"{self.PREFIX}{key}:{args_hash}"
        return f"{self.PREFIX}{key}"
    
    def _is_allowed(self, key: str) -> bool:
        """Key cache'lenebilir mi kontrol et"""
        # Blacklist kontrolü
        for blacklisted in self.BLACKLISTED_KEYS:
            if blacklisted in key.lower():
                logger.warning(f"⚠️ Cache BLOCKED: '{key}' blacklist'te!")
                return False
        return True
    
    def get(self, key: str, *args) -> Optional[Any]:
        """Cache'den veri al"""
        if not self.enabled:
            return None
            
        if not self._is_allowed(key):
            return None
            
        try:
            import pickle
            cache_key = self._make_key(key, *args)
            data = self.redis.get(cache_key)
            if data:
                logger.debug(f"✅ Cache HIT: {cache_key}")
                return pickle.loads(data)
            logger.debug(f"❌ Cache MISS: {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Cache get hatası: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None, *args) -> bool:
        """Cache'e veri yaz"""
        if not self.enabled:
            return False
            
        if not self._is_allowed(key):
            return False
            
        try:
            import pickle
            cache_key = self._make_key(key, *args)
            
            # TTL belirle
            if timeout is None:
                timeout = self.ALLOWED_KEYS.get(key, self.TTL_MEDIUM)
            
            data = pickle.dumps(value)
            self.redis.setex(cache_key, timeout, data)
            logger.debug(f"✅ Cache SET: {cache_key} (TTL: {timeout}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set hatası: {str(e)}")
            return False
    
    def invalidate(self, key: str, *args) -> bool:
        """Cache'i invalidate et"""
        if not self.enabled:
            return False
            
        try:
            if args:
                # Spesifik key'i sil
                cache_key = self._make_key(key, *args)
                self.redis.delete(cache_key)
                logger.info(f"🗑️ Cache invalidated: {cache_key}")
            else:
                # Pattern ile tüm ilgili key'leri sil
                pattern = f"{self.PREFIX}{key}:*"
                keys = self.redis.keys(pattern)
                if keys:
                    self.redis.delete(*keys)
                    logger.info(f"🗑️ Cache invalidated: {len(keys)} keys matching '{pattern}'")
                    
                # Base key'i de sil
                base_key = f"{self.PREFIX}{key}"
                self.redis.delete(base_key)
            return True
        except Exception as e:
            logger.error(f"Cache invalidate hatası: {str(e)}")
            return False
    
    def invalidate_all(self) -> bool:
        """Tüm cache'i temizle"""
        if not self.enabled:
            return False
            
        try:
            pattern = f"{self.PREFIX}*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
                logger.info(f"🗑️ Tüm cache temizlendi: {len(keys)} keys")
            return True
        except Exception as e:
            logger.error(f"Cache invalidate_all hatası: {str(e)}")
            return False
    
    def get_stats(self) -> dict:
        """Cache istatistiklerini al"""
        if not self.enabled:
            return {'enabled': False}
            
        try:
            pattern = f"{self.PREFIX}*"
            keys = self.redis.keys(pattern)
            
            # Key'leri kategorize et
            stats = {
                'enabled': True,
                'total_keys': len(keys),
                'categories': {}
            }
            
            for key in keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                # Prefix'i çıkar ve kategoriyi bul
                category = key_str.replace(self.PREFIX, '').split(':')[0]
                stats['categories'][category] = stats['categories'].get(category, 0) + 1
            
            return stats
        except Exception as e:
            logger.error(f"Cache stats hatası: {str(e)}")
            return {'enabled': True, 'error': str(e)}


# Global instance
cache_manager = CacheManager()


def init_cache(app):
    """
    Cache sistemini başlat.
    
    Args:
        app: Flask application instance
        
    Returns:
        CacheManager: Configured cache manager
    """
    global cache_manager, _cache_enabled
    
    # Cache'i aktifleştir mi?
    cache_enabled = app.config.get('CACHE_ENABLED', True)
    is_development = app.config.get('IS_DEVELOPMENT', False)
    
    if not cache_enabled:
        logger.info("ℹ️ Cache devre dışı (config)")
        cache_manager = CacheManager(None)
        _cache_enabled = False
        return cache_manager
    
    try:
        import redis
        
        # Redis URL'i config'den al
        redis_url = app.config.get('REDIS_URL') or app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        
        # Redis client oluştur
        redis_client = redis.from_url(
            redis_url,
            socket_connect_timeout=5,
            socket_timeout=5,
            decode_responses=False  # Pickle için binary gerekli
        )
        
        # Bağlantıyı test et
        redis_client.ping()
        
        cache_manager = CacheManager(redis_client)
        _cache_enabled = True
        logger.info(f"✅ Cache aktif (Redis: {redis_url[:30]}...)")
        
        return cache_manager
        
    except Exception as e:
        logger.warning(f"⚠️ Redis bağlantısı başarısız, cache devre dışı: {str(e)}")
        cache_manager = CacheManager(None)
        _cache_enabled = False
        return cache_manager


def cached_master_data(timeout: Optional[int] = None, key_prefix: str = None):
    """
    Master data için cache decorator.
    
    SADECE statik/master data için kullanın!
    Stok, zimmet, DND gibi transactional data için KULLANMAYIN!
    
    Args:
        timeout: Cache TTL (saniye). None ise key'e göre otomatik belirlenir.
        key_prefix: Cache key prefix'i
        
    Usage:
        @cached_master_data(key_prefix='urunler')
        def get_urun_listesi():
            return Urun.query.filter_by(aktif=True).all()
    """
    def decorator(f: Callable):
        @wraps(f)
        def wrapper(*args, **kwargs):
            global cache_manager
            
            # Cache key oluştur
            key = key_prefix or f.__name__
            
            # Cache'den dene
            cached_value = cache_manager.get(key, *args, *kwargs.values())
            if cached_value is not None:
                return cached_value
            
            # Fonksiyonu çalıştır
            result = f(*args, **kwargs)
            
            # Cache'e yaz
            cache_manager.set(key, result, timeout, *args, *kwargs.values())
            
            return result
        return wrapper
    return decorator


# ============================================
# CACHE INVALIDATION HELPERS
# ============================================

def invalidate_urun_cache():
    """Ürün cache'ini temizle"""
    cache_manager.invalidate('urunler')
    cache_manager.invalidate('urun_gruplari')


def invalidate_setup_cache():
    """Setup cache'ini temizle"""
    cache_manager.invalidate('setuplar')
    cache_manager.invalidate('setup_icerik')


def invalidate_otel_cache():
    """Otel/Kat/Oda cache'ini temizle"""
    cache_manager.invalidate('oteller')
    cache_manager.invalidate('katlar')
    cache_manager.invalidate('odalar')
    cache_manager.invalidate('oda_tipleri')


def invalidate_all_master_data():
    """Tüm master data cache'ini temizle"""
    invalidate_urun_cache()
    invalidate_setup_cache()
    invalidate_otel_cache()


# ============================================
# TEDARİKÇİ CACHE HELPERS
# ============================================

class TedarikciCache:
    """
    Tedarikçi verisi için cache yönetimi.
    Performans ve fiyat karşılaştırma verileri için kullanılır.
    """
    
    # Cache key prefix'leri
    PREFIX_PERFORMANS = "tedarikci:performans:"
    PREFIX_EN_UYGUN = "tedarikci:en_uygun:"
    PREFIX_FIYAT = "tedarikci:fiyat:"
    
    # TTL değerleri
    TTL_PERFORMANS = 300    # 5 dakika
    TTL_EN_UYGUN = 600      # 10 dakika
    TTL_FIYAT = 300         # 5 dakika
    
    @classmethod
    def _make_key(cls, prefix: str, *args) -> str:
        """Cache key oluştur"""
        key_parts = [str(arg) for arg in args if arg is not None]
        return f"{prefix}{':'.join(key_parts)}"
    
    @classmethod
    def get_tedarikci_performans(cls, tedarikci_id: int, baslangic=None, bitis=None):
        """Tedarikçi performans verisini cache'den al"""
        global cache_manager
        if not cache_manager.enabled:
            return None
        
        key = cls._make_key(cls.PREFIX_PERFORMANS, tedarikci_id, 
                           str(baslangic) if baslangic else '', 
                           str(bitis) if bitis else '')
        return cache_manager.get(key)
    
    @classmethod
    def set_tedarikci_performans(cls, tedarikci_id: int, baslangic, bitis, data, timeout=None):
        """Tedarikçi performans verisini cache'e yaz"""
        global cache_manager
        if not cache_manager.enabled:
            return
        
        key = cls._make_key(cls.PREFIX_PERFORMANS, tedarikci_id,
                           str(baslangic) if baslangic else '',
                           str(bitis) if bitis else '')
        cache_manager.set(key, data, timeout or cls.TTL_PERFORMANS)
    
    @classmethod
    def invalidate_tedarikci_performans(cls, tedarikci_id: int):
        """Tedarikçi performans cache'ini temizle"""
        global cache_manager
        if not cache_manager.enabled:
            return
        
        pattern = f"{cls.PREFIX_PERFORMANS}{tedarikci_id}:*"
        try:
            if cache_manager.redis:
                keys = cache_manager.redis.keys(pattern)
                if keys:
                    cache_manager.redis.delete(*keys)
                    logger.debug(f"Tedarikçi {tedarikci_id} performans cache temizlendi")
        except Exception as e:
            logger.warning(f"Tedarikçi cache invalidation hatası: {e}")
    
    @classmethod
    def get_en_uygun_tedarikci(cls, urun_id: int, miktar: int = None):
        """En uygun tedarikçi verisini cache'den al"""
        global cache_manager
        if not cache_manager.enabled:
            return None
        
        key = cls._make_key(cls.PREFIX_EN_UYGUN, urun_id, miktar or 0)
        return cache_manager.get(key)
    
    @classmethod
    def set_en_uygun_tedarikci(cls, urun_id: int, miktar: int, data, timeout=None):
        """En uygun tedarikçi verisini cache'e yaz"""
        global cache_manager
        if not cache_manager.enabled:
            return
        
        key = cls._make_key(cls.PREFIX_EN_UYGUN, urun_id, miktar or 0)
        cache_manager.set(key, data, timeout or cls.TTL_EN_UYGUN)
    
    @classmethod
    def invalidate_en_uygun_tedarikci(cls, urun_id: int):
        """En uygun tedarikçi cache'ini temizle"""
        global cache_manager
        if not cache_manager.enabled:
            return
        
        pattern = f"{cls.PREFIX_EN_UYGUN}{urun_id}:*"
        try:
            if cache_manager.redis:
                keys = cache_manager.redis.keys(pattern)
                if keys:
                    cache_manager.redis.delete(*keys)
                    logger.debug(f"Ürün {urun_id} en uygun tedarikçi cache temizlendi")
        except Exception as e:
            logger.warning(f"En uygun tedarikçi cache invalidation hatası: {e}")
    
    @classmethod
    def get_fiyat_karsilastirma(cls, urun_id: int):
        """Fiyat karşılaştırma verisini cache'den al"""
        global cache_manager
        if not cache_manager.enabled:
            return None
        
        key = cls._make_key(cls.PREFIX_FIYAT, urun_id)
        return cache_manager.get(key)
    
    @classmethod
    def set_fiyat_karsilastirma(cls, urun_id: int, data, timeout=None):
        """Fiyat karşılaştırma verisini cache'e yaz"""
        global cache_manager
        if not cache_manager.enabled:
            return
        
        key = cls._make_key(cls.PREFIX_FIYAT, urun_id)
        cache_manager.set(key, data, timeout or cls.TTL_FIYAT)
    
    @classmethod
    def invalidate_fiyat_karsilastirma(cls, urun_id: int):
        """Fiyat karşılaştırma cache'ini temizle"""
        global cache_manager
        if not cache_manager.enabled:
            return
        
        key = cls._make_key(cls.PREFIX_FIYAT, urun_id)
        cache_manager.invalidate(key)
        logger.debug(f"Ürün {urun_id} fiyat karşılaştırma cache temizlendi")


# ============================================
# FİYAT CACHE HELPERS
# ============================================

class FiyatCache:
    """
    Fiyat verisi için cache yönetimi.
    Ürün fiyatları ve sezon fiyatlandırması için kullanılır.
    """
    
    PREFIX_URUN_FIYAT = "fiyat:urun:"
    PREFIX_SEZON = "fiyat:sezon:"
    PREFIX_BEDELSIZ = "fiyat:bedelsiz:"
    
    TTL_FIYAT = 300  # 5 dakika
    
    @classmethod
    def _make_key(cls, prefix: str, *args) -> str:
        key_parts = [str(arg) for arg in args if arg is not None]
        return f"{prefix}{':'.join(key_parts)}"
    
    @classmethod
    def get_urun_fiyat(cls, urun_id: int, oda_tipi_id: int = None):
        global cache_manager
        if not cache_manager.enabled:
            return None
        key = cls._make_key(cls.PREFIX_URUN_FIYAT, urun_id, oda_tipi_id or 0)
        return cache_manager.get(key)
    
    @classmethod
    def set_urun_fiyat(cls, urun_id: int, oda_tipi_id: int, data, timeout=None):
        global cache_manager
        if not cache_manager.enabled:
            return
        key = cls._make_key(cls.PREFIX_URUN_FIYAT, urun_id, oda_tipi_id or 0)
        cache_manager.set(key, data, timeout or cls.TTL_FIYAT)
    
    @classmethod
    def invalidate_urun_fiyat(cls, urun_id: int):
        global cache_manager
        if not cache_manager.enabled:
            return
        pattern = f"{cls.PREFIX_URUN_FIYAT}{urun_id}:*"
        try:
            if cache_manager.redis:
                keys = cache_manager.redis.keys(pattern)
                if keys:
                    cache_manager.redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Fiyat cache invalidation hatası: {e}")
    
    @classmethod
    def get_sezon_carpani(cls, otel_id: int, tarih=None):
        global cache_manager
        if not cache_manager.enabled:
            return None
        key = cls._make_key(cls.PREFIX_SEZON, otel_id, str(tarih) if tarih else '')
        return cache_manager.get(key)
    
    @classmethod
    def set_sezon_carpani(cls, otel_id: int, tarih, data, timeout=None):
        global cache_manager
        if not cache_manager.enabled:
            return
        key = cls._make_key(cls.PREFIX_SEZON, otel_id, str(tarih) if tarih else '')
        cache_manager.set(key, data, timeout or cls.TTL_FIYAT)


class KarCache:
    """
    Karlılık verisi için cache yönetimi.
    Dönemsel kar analizleri için kullanılır.
    """
    
    PREFIX_DONEMSEL = "kar:donemsel:"
    PREFIX_URUN = "kar:urun:"
    
    TTL_KAR = 300  # 5 dakika
    
    @classmethod
    def _make_key(cls, prefix: str, *args) -> str:
        key_parts = [str(arg) for arg in args if arg is not None]
        return f"{prefix}{':'.join(key_parts)}"
    
    @classmethod
    def get_donemsel_kar(cls, otel_id: int, baslangic, bitis):
        global cache_manager
        if not cache_manager.enabled:
            return None
        key = cls._make_key(cls.PREFIX_DONEMSEL, otel_id, str(baslangic), str(bitis))
        return cache_manager.get(key)
    
    @classmethod
    def set_donemsel_kar(cls, otel_id: int, baslangic, bitis, data, timeout=None):
        global cache_manager
        if not cache_manager.enabled:
            return
        key = cls._make_key(cls.PREFIX_DONEMSEL, otel_id, str(baslangic), str(bitis))
        cache_manager.set(key, data, timeout or cls.TTL_KAR)
    
    @classmethod
    def invalidate_otel_kar(cls, otel_id: int):
        global cache_manager
        if not cache_manager.enabled:
            return
        pattern = f"{cls.PREFIX_DONEMSEL}{otel_id}:*"
        try:
            if cache_manager.redis:
                keys = cache_manager.redis.keys(pattern)
                if keys:
                    cache_manager.redis.delete(*keys)
        except Exception as e:
            logger.warning(f"Kar cache invalidation hatası: {e}")
    
    @classmethod
    def get_urun_kar(cls, urun_id: int, baslangic=None, bitis=None):
        global cache_manager
        if not cache_manager.enabled:
            return None
        key = cls._make_key(cls.PREFIX_URUN, urun_id, 
                           str(baslangic) if baslangic else '',
                           str(bitis) if bitis else '')
        return cache_manager.get(key)
    
    @classmethod
    def set_urun_kar(cls, urun_id: int, baslangic, bitis, data, timeout=None):
        global cache_manager
        if not cache_manager.enabled:
            return
        key = cls._make_key(cls.PREFIX_URUN, urun_id,
                           str(baslangic) if baslangic else '',
                           str(bitis) if bitis else '')
        cache_manager.set(key, data, timeout or cls.TTL_KAR)


# ============================================
# CACHE STATS
# ============================================

class CacheStats:
    """
    Cache istatistikleri için yardımcı sınıf.
    """
    
    @classmethod
    def get_cache_info(cls) -> dict:
        """
        Cache durumu ve istatistiklerini döndür.
        
        Returns:
            dict: Cache bilgileri
        """
        global cache_manager
        
        if not cache_manager or not cache_manager.enabled:
            return {
                'enabled': False,
                'message': 'Cache devre dışı'
            }
        
        try:
            return cache_manager.get_stats()
        except Exception as e:
            return {
                'enabled': True,
                'error': str(e)
            }
    
    @classmethod
    def get_hit_rate(cls) -> float:
        """
        Cache hit oranını döndür.
        
        Returns:
            float: Hit oranı (0-100)
        """
        global cache_manager
        
        if not cache_manager or not cache_manager.enabled:
            return 0.0
        
        try:
            if cache_manager.redis:
                info = cache_manager.redis.info('stats')
                hits = info.get('keyspace_hits', 0)
                misses = info.get('keyspace_misses', 0)
                total = hits + misses
                if total > 0:
                    return (hits / total) * 100
            return 0.0
        except Exception:
            return 0.0
    
    @classmethod
    def get_memory_usage(cls) -> dict:
        """
        Cache bellek kullanımını döndür.
        
        Returns:
            dict: Bellek bilgileri
        """
        global cache_manager
        
        if not cache_manager or not cache_manager.enabled:
            return {'used': 0, 'peak': 0}
        
        try:
            if cache_manager.redis:
                info = cache_manager.redis.info('memory')
                return {
                    'used': info.get('used_memory_human', '0B'),
                    'peak': info.get('used_memory_peak_human', '0B'),
                    'used_bytes': info.get('used_memory', 0)
                }
            return {'used': 0, 'peak': 0}
        except Exception:
            return {'used': 0, 'peak': 0}
