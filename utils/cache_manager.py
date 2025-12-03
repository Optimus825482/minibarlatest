"""
Redis Cache Yönetim Modülü
Fiyatlandırma ve Karlılık sistemleri için cache stratejileri
"""

from functools import wraps
from flask import current_app
from datetime import datetime, timezone
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
import logging
import json

logger = logging.getLogger(__name__)

# Cache instance'ı lazy import ile al (circular import önleme)
_cache = None

def get_cache():
    """Cache instance'ını al (lazy loading)"""
    global _cache
    if _cache is None:
        from app import cache
        _cache = cache
    return _cache


class CacheManager:
    """Merkezi cache yönetim sınıfı"""
    
    @staticmethod
    def get_cache():
        """Cache instance'ını al"""
        return get_cache()
    
    @staticmethod
    def make_cache_key(*args, **kwargs):
        """
        Cache key oluştur
        Args ve kwargs'tan unique bir key üretir
        """
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        return ":".join(key_parts)
    
    @staticmethod
    def invalidate_pattern(pattern):
        """
        Pattern'e uyan tüm cache key'lerini temizle
        Örnek: 'fiyat:urun:*' -> Tüm ürün fiyat cache'lerini temizle
        """
        try:
            cache = CacheManager.get_cache()
            if hasattr(cache.cache, '_client'):  # Redis backend
                redis_client = cache.cache._client
                prefix = current_app.config.get('CACHE_KEY_PREFIX', 'minibar_cache:')
                full_pattern = f"{prefix}{pattern}"
                
                # SCAN kullan (keys() yerine - production için daha güvenli)
                deleted_count = 0
                cursor = 0
                while True:
                    cursor, keys = redis_client.scan(cursor, match=full_pattern, count=100)
                    if keys:
                        redis_client.delete(*keys)
                        deleted_count += len(keys)
                    if cursor == 0:
                        break
                
                if deleted_count > 0:
                    logger.info(f"✅ Cache pattern temizlendi: {pattern} ({deleted_count} key)")
                return deleted_count
            return 0
        except Exception as e:
            logger.error(f"❌ Cache pattern temizleme hatası: {e}")
            return 0


class TedarikciCache:
    """Tedarikçi ve satın alma cache yönetimi"""
    
    @staticmethod
    def get_tedarikci_performans_key(tedarikci_id, donem_baslangic, donem_bitis):
        """Tedarikçi performans cache key'i oluştur"""
        baslangic_str = donem_baslangic.strftime('%Y-%m-%d') if donem_baslangic else 'none'
        bitis_str = donem_bitis.strftime('%Y-%m-%d') if donem_bitis else 'none'
        return f"tedarikci:performans:{tedarikci_id}:{baslangic_str}:{bitis_str}"
    
    @staticmethod
    def get_tedarikci_performans(tedarikci_id, donem_baslangic, donem_bitis):
        """
        Tedarikçi performans metriklerini cache'den getir
        Cache miss durumunda None döner
        """
        try:
            cache = CacheManager.get_cache()
            key = TedarikciCache.get_tedarikci_performans_key(tedarikci_id, donem_baslangic, donem_bitis)
            cached_data = cache.get(key)
            
            if cached_data:
                logger.debug(f"✅ Cache HIT: {key}")
                return cached_data
            
            logger.debug(f"❌ Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"❌ Cache okuma hatası: {e}")
            return None
    
    @staticmethod
    def set_tedarikci_performans(tedarikci_id, donem_baslangic, donem_bitis, data, timeout=300):
        """
        Tedarikçi performans metriklerini cache'e kaydet
        Varsayılan timeout: 5 dakika (300 saniye)
        """
        try:
            cache = CacheManager.get_cache()
            key = TedarikciCache.get_tedarikci_performans_key(tedarikci_id, donem_baslangic, donem_bitis)
            cache.set(key, data, timeout=timeout)
            logger.debug(f"✅ Cache SET: {key} (timeout: {timeout}s)")
            return True
        except Exception as e:
            logger.error(f"❌ Cache yazma hatası: {e}")
            return False
    
    @staticmethod
    def invalidate_tedarikci_performans(tedarikci_id):
        """Tedarikçi performans cache'ini temizle"""
        try:
            pattern = f"tedarikci:performans:{tedarikci_id}:*"
            deleted = CacheManager.invalidate_pattern(pattern)
            logger.info(f"✅ Tedarikçi {tedarikci_id} performans cache temizlendi ({deleted} key)")
            return deleted
        except Exception as e:
            logger.error(f"❌ Cache temizleme hatası: {e}")
            return 0
    
    @staticmethod
    def get_fiyat_karsilastirma_key(urun_id, miktar):
        """Fiyat karşılaştırma cache key'i oluştur"""
        return f"tedarikci:fiyat_karsilastirma:urun:{urun_id}:miktar:{miktar}"
    
    @staticmethod
    def get_fiyat_karsilastirma(urun_id, miktar):
        """
        Fiyat karşılaştırma sonuçlarını cache'den getir
        Cache miss durumunda None döner
        """
        try:
            cache = CacheManager.get_cache()
            key = TedarikciCache.get_fiyat_karsilastirma_key(urun_id, miktar)
            cached_data = cache.get(key)
            
            if cached_data:
                logger.debug(f"✅ Cache HIT: {key}")
                return cached_data
            
            logger.debug(f"❌ Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"❌ Cache okuma hatası: {e}")
            return None
    
    @staticmethod
    def set_fiyat_karsilastirma(urun_id, miktar, data, timeout=600):
        """
        Fiyat karşılaştırma sonuçlarını cache'e kaydet
        Varsayılan timeout: 10 dakika (600 saniye)
        """
        try:
            cache = CacheManager.get_cache()
            key = TedarikciCache.get_fiyat_karsilastirma_key(urun_id, miktar)
            cache.set(key, data, timeout=timeout)
            logger.debug(f"✅ Cache SET: {key} (timeout: {timeout}s)")
            return True
        except Exception as e:
            logger.error(f"❌ Cache yazma hatası: {e}")
            return False
    
    @staticmethod
    def invalidate_fiyat_karsilastirma(urun_id=None):
        """Fiyat karşılaştırma cache'ini temizle"""
        try:
            if urun_id:
                pattern = f"tedarikci:fiyat_karsilastirma:urun:{urun_id}:*"
            else:
                pattern = "tedarikci:fiyat_karsilastirma:*"
            deleted = CacheManager.invalidate_pattern(pattern)
            logger.info(f"✅ Fiyat karşılaştırma cache temizlendi ({deleted} key)")
            return deleted
        except Exception as e:
            logger.error(f"❌ Cache temizleme hatası: {e}")
            return 0
    
    @staticmethod
    def get_en_uygun_tedarikci_key(urun_id, miktar):
        """En uygun tedarikçi cache key'i oluştur"""
        return f"tedarikci:en_uygun:urun:{urun_id}:miktar:{miktar}"
    
    @staticmethod
    def get_en_uygun_tedarikci(urun_id, miktar):
        """
        En uygun tedarikçi sonucunu cache'den getir
        Cache miss durumunda None döner
        """
        try:
            cache = CacheManager.get_cache()
            key = TedarikciCache.get_en_uygun_tedarikci_key(urun_id, miktar)
            cached_data = cache.get(key)
            
            if cached_data:
                logger.debug(f"✅ Cache HIT: {key}")
                return cached_data
            
            logger.debug(f"❌ Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"❌ Cache okuma hatası: {e}")
            return None
    
    @staticmethod
    def set_en_uygun_tedarikci(urun_id, miktar, data, timeout=600):
        """
        En uygun tedarikçi sonucunu cache'e kaydet
        Varsayılan timeout: 10 dakika (600 saniye)
        """
        try:
            cache = CacheManager.get_cache()
            key = TedarikciCache.get_en_uygun_tedarikci_key(urun_id, miktar)
            cache.set(key, data, timeout=timeout)
            logger.debug(f"✅ Cache SET: {key} (timeout: {timeout}s)")
            return True
        except Exception as e:
            logger.error(f"❌ Cache yazma hatası: {e}")
            return False
    
    @staticmethod
    def invalidate_en_uygun_tedarikci(urun_id=None):
        """En uygun tedarikçi cache'ini temizle"""
        try:
            if urun_id:
                pattern = f"tedarikci:en_uygun:urun:{urun_id}:*"
            else:
                pattern = "tedarikci:en_uygun:*"
            deleted = CacheManager.invalidate_pattern(pattern)
            logger.info(f"✅ En uygun tedarikçi cache temizlendi ({deleted} key)")
            return deleted
        except Exception as e:
            logger.error(f"❌ Cache temizleme hatası: {e}")
            return 0


class FiyatCache:
    """Fiyatlandırma cache yönetimi"""
    
    @staticmethod
    def get_urun_fiyat_key(urun_id, oda_id=None, tarih=None):
        """Ürün fiyat cache key'i oluştur"""
        tarih_str = tarih.strftime('%Y-%m-%d') if tarih else get_kktc_now().strftime('%Y-%m-%d')
        oda_str = str(oda_id) if oda_id else 'default'
        return f"fiyat:urun:{urun_id}:oda:{oda_str}:tarih:{tarih_str}"
    
    @staticmethod
    def get_dinamik_fiyat(urun_id, oda_id=None, tarih=None, miktar=1):
        """
        Dinamik fiyat hesaplamasını cache'den getir
        Cache miss durumunda None döner
        """
        try:
            cache = CacheManager.get_cache()
            key = FiyatCache.get_urun_fiyat_key(urun_id, oda_id, tarih)
            cached_data = cache.get(key)
            
            if cached_data:
                logger.debug(f"✅ Cache HIT: {key}")
                return cached_data
            
            logger.debug(f"❌ Cache MISS: {key}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Cache get hatası: {e}")
            return None
    
    @staticmethod
    def set_dinamik_fiyat(urun_id, fiyat_data, oda_id=None, tarih=None, timeout=None):
        """
        Dinamik fiyat hesaplamasını cache'e kaydet
        
        Args:
            urun_id: Ürün ID
            fiyat_data: Fiyat bilgileri dict
            oda_id: Oda ID (opsiyonel)
            tarih: Tarih (opsiyonel)
            timeout: Cache timeout (saniye), None ise config'den alır
        """
        try:
            cache = CacheManager.get_cache()
            key = FiyatCache.get_urun_fiyat_key(urun_id, oda_id, tarih)
            
            if timeout is None:
                timeout = current_app.config.get('CACHE_TIMEOUT_FIYAT', 3600)
            
            cache.set(key, fiyat_data, timeout=timeout)
            logger.debug(f"✅ Cache SET: {key} (timeout: {timeout}s)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cache set hatası: {e}")
            return False
    
    @staticmethod
    def invalidate_urun_fiyat(urun_id):
        """
        Belirli bir ürünün tüm fiyat cache'lerini temizle
        Fiyat güncellemelerinde kullanılır
        """
        try:
            cache = CacheManager.get_cache()
            pattern = f"fiyat:urun:{urun_id}:*"
            
            # Pattern matching ile tüm key'leri bul ve sil
            if hasattr(cache.cache, '_client'):  # Redis backend
                redis_client = cache.cache._client
                prefix = current_app.config.get('CACHE_KEY_PREFIX', 'minibar_cache:')
                full_pattern = f"{prefix}{pattern}"
                
                deleted_count = 0
                cursor = 0
                while True:
                    cursor, keys = redis_client.scan(cursor, match=full_pattern, count=100)
                    if keys:
                        redis_client.delete(*keys)
                        deleted_count += len(keys)
                    if cursor == 0:
                        break
                
                logger.info(f"✅ Ürün {urun_id} fiyat cache'i temizlendi ({deleted_count} key)")
                return deleted_count
            else:
                # Simple cache için - tüm cache'i temizle
                cache.clear()
                logger.info(f"✅ Ürün {urun_id} için cache temizlendi (simple cache)")
                return 1
                
        except Exception as e:
            logger.error(f"❌ Fiyat cache invalidation hatası: {e}")
            return 0
    
    @staticmethod
    def invalidate_all_fiyat():
        """Tüm fiyat cache'lerini temizle"""
        try:
            pattern = "fiyat:*"
            count = CacheManager.invalidate_pattern(pattern)
            logger.info(f"✅ Tüm fiyat cache'leri temizlendi ({count} key)")
            return count
        except Exception as e:
            logger.error(f"❌ Tüm fiyat cache temizleme hatası: {e}")
            return 0


class KarCache:
    """Karlılık analizi cache yönetimi"""
    
    @staticmethod
    def get_donemsel_kar_key(otel_id, donem_tipi, baslangic, bitis):
        """Dönemsel kar analizi cache key'i"""
        baslangic_str = baslangic.strftime('%Y-%m-%d') if hasattr(baslangic, 'strftime') else str(baslangic)
        bitis_str = bitis.strftime('%Y-%m-%d') if hasattr(bitis, 'strftime') else str(bitis)
        return f"kar:donemsel:otel:{otel_id}:donem:{donem_tipi}:{baslangic_str}:{bitis_str}"
    
    @staticmethod
    def get_donemsel_kar(otel_id, donem_tipi, baslangic, bitis):
        """Dönemsel kar analizini cache'den getir"""
        try:
            cache = CacheManager.get_cache()
            key = KarCache.get_donemsel_kar_key(otel_id, donem_tipi, baslangic, bitis)
            cached_data = cache.get(key)
            
            if cached_data:
                logger.debug(f"✅ Cache HIT: {key}")
                return cached_data
            
            logger.debug(f"❌ Cache MISS: {key}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Kar cache get hatası: {e}")
            return None
    
    @staticmethod
    def set_donemsel_kar(otel_id, donem_tipi, baslangic, bitis, kar_data, timeout=None):
        """Dönemsel kar analizini cache'e kaydet"""
        try:
            cache = CacheManager.get_cache()
            key = KarCache.get_donemsel_kar_key(otel_id, donem_tipi, baslangic, bitis)
            
            if timeout is None:
                timeout = current_app.config.get('CACHE_TIMEOUT_KAR', 1800)
            
            cache.set(key, kar_data, timeout=timeout)
            logger.debug(f"✅ Cache SET: {key} (timeout: {timeout}s)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Kar cache set hatası: {e}")
            return False
    
    @staticmethod
    def get_urun_karlilik_key(urun_id, baslangic=None, bitis=None):
        """Ürün karlılık cache key'i"""
        baslangic_str = baslangic.strftime('%Y-%m-%d') if baslangic else 'all'
        bitis_str = bitis.strftime('%Y-%m-%d') if bitis else 'all'
        return f"kar:urun:{urun_id}:{baslangic_str}:{bitis_str}"
    
    @staticmethod
    def get_urun_karlilik(urun_id, baslangic=None, bitis=None):
        """Ürün karlılığını cache'den getir"""
        try:
            cache = CacheManager.get_cache()
            key = KarCache.get_urun_karlilik_key(urun_id, baslangic, bitis)
            cached_data = cache.get(key)
            
            if cached_data:
                logger.debug(f"✅ Cache HIT: {key}")
                return cached_data
            
            logger.debug(f"❌ Cache MISS: {key}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ürün karlılık cache get hatası: {e}")
            return None
    
    @staticmethod
    def set_urun_karlilik(urun_id, karlilik_data, baslangic=None, bitis=None, timeout=None):
        """Ürün karlılığını cache'e kaydet"""
        try:
            cache = CacheManager.get_cache()
            key = KarCache.get_urun_karlilik_key(urun_id, baslangic, bitis)
            
            if timeout is None:
                timeout = current_app.config.get('CACHE_TIMEOUT_KAR', 1800)
            
            cache.set(key, karlilik_data, timeout=timeout)
            logger.debug(f"✅ Cache SET: {key} (timeout: {timeout}s)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ürün karlılık cache set hatası: {e}")
            return False
    
    @staticmethod
    def invalidate_otel_kar(otel_id):
        """Otel bazlı tüm kar cache'lerini temizle"""
        try:
            pattern = f"kar:*:otel:{otel_id}:*"
            count = CacheManager.invalidate_pattern(pattern)
            logger.info(f"✅ Otel {otel_id} kar cache'i temizlendi ({count} key)")
            return count
        except Exception as e:
            logger.error(f"❌ Otel kar cache invalidation hatası: {e}")
            return 0
    
    @staticmethod
    def invalidate_urun_kar(urun_id):
        """Ürün bazlı tüm kar cache'lerini temizle"""
        try:
            pattern = f"kar:urun:{urun_id}:*"
            count = CacheManager.invalidate_pattern(pattern)
            logger.info(f"✅ Ürün {urun_id} kar cache'i temizlendi ({count} key)")
            return count
        except Exception as e:
            logger.error(f"❌ Ürün kar cache invalidation hatası: {e}")
            return 0
    
    @staticmethod
    def invalidate_all_kar():
        """Tüm kar cache'lerini temizle"""
        try:
            pattern = "kar:*"
            count = CacheManager.invalidate_pattern(pattern)
            logger.info(f"✅ Tüm kar cache'leri temizlendi ({count} key)")
            return count
        except Exception as e:
            logger.error(f"❌ Tüm kar cache temizleme hatası: {e}")
            return 0


class StokCache:
    """Stok yönetimi cache'i"""
    
    @staticmethod
    def get_stok_durum_key(urun_id, otel_id):
        """Stok durumu cache key'i"""
        return f"stok:durum:urun:{urun_id}:otel:{otel_id}"
    
    @staticmethod
    def get_stok_durum(urun_id, otel_id):
        """Stok durumunu cache'den getir"""
        try:
            cache = CacheManager.get_cache()
            key = StokCache.get_stok_durum_key(urun_id, otel_id)
            cached_data = cache.get(key)
            
            if cached_data:
                logger.debug(f"✅ Cache HIT: {key}")
                return cached_data
            
            logger.debug(f"❌ Cache MISS: {key}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Stok cache get hatası: {e}")
            return None
    
    @staticmethod
    def set_stok_durum(urun_id, otel_id, stok_data, timeout=None):
        """Stok durumunu cache'e kaydet"""
        try:
            cache = CacheManager.get_cache()
            key = StokCache.get_stok_durum_key(urun_id, otel_id)
            
            if timeout is None:
                timeout = current_app.config.get('CACHE_TIMEOUT_STOK', 300)
            
            cache.set(key, stok_data, timeout=timeout)
            logger.debug(f"✅ Cache SET: {key} (timeout: {timeout}s)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Stok cache set hatası: {e}")
            return False
    
    @staticmethod
    def invalidate_urun_stok(urun_id, otel_id=None):
        """Ürün stok cache'ini temizle"""
        try:
            if otel_id:
                pattern = f"stok:durum:urun:{urun_id}:otel:{otel_id}"
            else:
                pattern = f"stok:durum:urun:{urun_id}:*"
            
            count = CacheManager.invalidate_pattern(pattern)
            logger.info(f"✅ Ürün {urun_id} stok cache'i temizlendi ({count} key)")
            return count
        except Exception as e:
            logger.error(f"❌ Stok cache invalidation hatası: {e}")
            return 0
    
    @staticmethod
    def invalidate_otel_stok(otel_id):
        """Otel bazlı tüm stok cache'lerini temizle"""
        try:
            pattern = f"stok:*:otel:{otel_id}"
            count = CacheManager.invalidate_pattern(pattern)
            logger.info(f"✅ Otel {otel_id} stok cache'i temizlendi ({count} key)")
            return count
        except Exception as e:
            logger.error(f"❌ Otel stok cache invalidation hatası: {e}")
            return 0


def cache_with_invalidation(cache_class, get_method, set_method, invalidate_on=None):
    """
    Cache decorator with automatic invalidation
    
    Args:
        cache_class: Cache sınıfı (FiyatCache, KarCache, vb.)
        get_method: Cache'den veri çekme metodu adı
        set_method: Cache'e veri kaydetme metodu adı
        invalidate_on: Hangi işlemlerde cache'i temizleyeceği (list)
    
    Kullanım:
        @cache_with_invalidation(FiyatCache, 'get_dinamik_fiyat', 'set_dinamik_fiyat')
        def hesapla_fiyat(urun_id, oda_id):
            # Hesaplama
            return fiyat_data
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Cache'den veri çekmeyi dene
                get_func = getattr(cache_class, get_method)
                cached_result = get_func(*args, **kwargs)
                
                if cached_result is not None:
                    return cached_result
                
                # Cache miss - Fonksiyonu çalıştır
                result = func(*args, **kwargs)
                
                # Sonucu cache'e kaydet
                set_func = getattr(cache_class, set_method)
                set_func(*args, result, **kwargs)
                
                return result
                
            except Exception as e:
                logger.error(f"❌ Cache decorator hatası: {e}")
                # Cache hatası durumunda direkt fonksiyonu çalıştır
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Cache istatistikleri
class CacheStats:
    """Cache performans istatistikleri"""
    
    @staticmethod
    def get_cache_info():
        """Cache bilgilerini getir"""
        try:
            cache = CacheManager.get_cache()
            
            info = {
                'cache_type': current_app.config.get('CACHE_TYPE'),
                'default_timeout': current_app.config.get('CACHE_DEFAULT_TIMEOUT'),
                'fiyat_timeout': current_app.config.get('CACHE_TIMEOUT_FIYAT'),
                'kar_timeout': current_app.config.get('CACHE_TIMEOUT_KAR'),
                'stok_timeout': current_app.config.get('CACHE_TIMEOUT_STOK'),
            }
            
            # Redis backend ise istatistikleri ekle
            if hasattr(cache.cache, '_client'):
                redis_client = cache.cache._client
                redis_info = redis_client.info('stats')
                info['redis_stats'] = {
                    'total_connections_received': redis_info.get('total_connections_received', 0),
                    'total_commands_processed': redis_info.get('total_commands_processed', 0),
                    'keyspace_hits': redis_info.get('keyspace_hits', 0),
                    'keyspace_misses': redis_info.get('keyspace_misses', 0),
                }
                
                # Hit rate hesapla
                hits = redis_info.get('keyspace_hits', 0)
                misses = redis_info.get('keyspace_misses', 0)
                total = hits + misses
                info['redis_stats']['hit_rate'] = round((hits / total * 100), 2) if total > 0 else 0
            
            return info
            
        except Exception as e:
            logger.error(f"❌ Cache info hatası: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def clear_all_cache():
        """Tüm cache'i temizle (Dikkatli kullan!)"""
        try:
            cache = CacheManager.get_cache()
            cache.clear()
            logger.warning("⚠️ TÜM CACHE TEMİZLENDİ!")
            return True
        except Exception as e:
            logger.error(f"❌ Cache temizleme hatası: {e}")
            return False

