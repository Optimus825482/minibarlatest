"""
Cache Service - Redis Cache Yönetimi
Developer Dashboard için cache monitoring ve yönetim servisi
"""
import redis
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class CacheService:
    """Redis cache yönetim servisi"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Args:
            redis_client: Redis client instance (None ise yeni oluşturulur)
        """
        try:
            if redis_client:
                self.redis = redis_client
            else:
                # Default Redis connection
                self.redis = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True,
                    socket_connect_timeout=5
                )
            # Test connection
            self.redis.ping()
            self.connected = True
        except Exception as e:
            logger.error(f"Redis bağlantı hatası: {str(e)}")
            self.redis = None
            self.connected = False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Cache istatistiklerini getir
        
        Returns:
            Dict: Cache stats (size, keys, memory, hit_rate)
        """
        try:
            if not self.connected:
                return {
                    'connected': False,
                    'error': 'Redis bağlantısı yok'
                }
            
            info = self.redis.info('stats')
            memory_info = self.redis.info('memory')
            
            # Key sayısı
            total_keys = sum(self.redis.dbsize() for _ in range(16))  # 16 DB
            
            # Memory kullanımı
            used_memory = memory_info.get('used_memory', 0)
            used_memory_human = memory_info.get('used_memory_human', '0B')
            max_memory = memory_info.get('maxmemory', 0)
            
            # Hit/Miss oranları
            keyspace_hits = info.get('keyspace_hits', 0)
            keyspace_misses = info.get('keyspace_misses', 0)
            total_commands = keyspace_hits + keyspace_misses
            
            hit_rate = 0
            if total_commands > 0:
                hit_rate = (keyspace_hits / total_commands) * 100
            
            return {
                'connected': True,
                'total_keys': total_keys,
                'used_memory': used_memory,
                'used_memory_human': used_memory_human,
                'max_memory': max_memory,
                'memory_usage_percent': (used_memory / max_memory * 100) if max_memory > 0 else 0,
                'keyspace_hits': keyspace_hits,
                'keyspace_misses': keyspace_misses,
                'hit_rate': round(hit_rate, 2),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Cache stats hatası: {str(e)}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def get_all_keys(self, pattern: str = '*', limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Cache anahtarlarını getir
        
        Args:
            pattern: Key pattern (default: '*')
            limit: Maksimum key sayısı
            
        Returns:
            List[Dict]: Key listesi (name, type, ttl, size)
        """
        try:
            if not self.connected:
                return []
            
            keys = []
            cursor = 0
            count = 0
            
            # SCAN ile iterate et (KEYS yerine - production safe)
            while count < limit:
                cursor, batch = self.redis.scan(cursor, match=pattern, count=100)
                
                for key in batch:
                    if count >= limit:
                        break
                    
                    try:
                        key_type = self.redis.type(key)
                        ttl = self.redis.ttl(key)
                        
                        # Key size hesapla
                        size = 0
                        if key_type == 'string':
                            value = self.redis.get(key)
                            size = len(str(value)) if value else 0
                        elif key_type == 'list':
                            size = self.redis.llen(key)
                        elif key_type == 'set':
                            size = self.redis.scard(key)
                        elif key_type == 'zset':
                            size = self.redis.zcard(key)
                        elif key_type == 'hash':
                            size = self.redis.hlen(key)
                        
                        keys.append({
                            'key': key,
                            'type': key_type,
                            'ttl': ttl,
                            'size': size,
                            'expires': ttl > 0
                        })
                        count += 1
                    except Exception as e:
                        logger.warning(f"Key bilgisi alınamadı ({key}): {str(e)}")
                        continue
                
                if cursor == 0:
                    break
            
            return keys
        except Exception as e:
            logger.error(f"Keys listesi hatası: {str(e)}")
            return []
    
    def get_key_details(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Belirli bir key'in detaylarını getir
        
        Args:
            key: Cache key
            
        Returns:
            Dict: Key detayları (type, ttl, value, size)
        """
        try:
            if not self.connected or not self.redis.exists(key):
                return None
            
            key_type = self.redis.type(key)
            ttl = self.redis.ttl(key)
            
            # Value'yu type'a göre al
            value = None
            size = 0
            
            if key_type == 'string':
                value = self.redis.get(key)
                size = len(str(value)) if value else 0
                # JSON parse dene
                try:
                    value = json.loads(value)
                except:
                    pass
            elif key_type == 'list':
                value = self.redis.lrange(key, 0, 100)  # İlk 100 item
                size = self.redis.llen(key)
            elif key_type == 'set':
                value = list(self.redis.smembers(key))[:100]
                size = self.redis.scard(key)
            elif key_type == 'zset':
                value = self.redis.zrange(key, 0, 100, withscores=True)
                size = self.redis.zcard(key)
            elif key_type == 'hash':
                value = self.redis.hgetall(key)
                size = self.redis.hlen(key)
            
            return {
                'key': key,
                'type': key_type,
                'ttl': ttl,
                'expires': ttl > 0,
                'size': size,
                'value': value,
                'memory_usage': self.redis.memory_usage(key) if hasattr(self.redis, 'memory_usage') else None
            }
        except Exception as e:
            logger.error(f"Key detay hatası ({key}): {str(e)}")
            return None
    
    def clear_cache(self, pattern: str = '*') -> Dict[str, Any]:
        """
        Cache'i temizle
        
        Args:
            pattern: Silinecek key pattern (default: '*' - tümü)
            
        Returns:
            Dict: Sonuç (success, deleted_count)
        """
        try:
            if not self.connected:
                return {
                    'success': False,
                    'error': 'Redis bağlantısı yok'
                }
            
            deleted_count = 0
            
            if pattern == '*':
                # Tüm database'i temizle
                deleted_count = self.redis.dbsize()
                self.redis.flushdb()
            else:
                # Pattern'e uyan key'leri sil
                cursor = 0
                while True:
                    cursor, keys = self.redis.scan(cursor, match=pattern, count=100)
                    if keys:
                        deleted_count += self.redis.delete(*keys)
                    if cursor == 0:
                        break
            
            logger.info(f"Cache temizlendi: {deleted_count} key silindi (pattern: {pattern})")
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'pattern': pattern,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Cache temizleme hatası: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_hit_miss_ratio(self) -> Dict[str, Any]:
        """
        Cache hit/miss oranlarını getir
        
        Returns:
            Dict: Hit/miss statistics
        """
        try:
            if not self.connected:
                return {
                    'connected': False,
                    'error': 'Redis bağlantısı yok'
                }
            
            info = self.redis.info('stats')
            
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total = hits + misses
            
            hit_rate = 0
            miss_rate = 0
            
            if total > 0:
                hit_rate = (hits / total) * 100
                miss_rate = (misses / total) * 100
            
            return {
                'connected': True,
                'hits': hits,
                'misses': misses,
                'total': total,
                'hit_rate': round(hit_rate, 2),
                'miss_rate': round(miss_rate, 2),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Hit/miss ratio hatası: {str(e)}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def delete_key(self, key: str) -> bool:
        """
        Belirli bir key'i sil
        
        Args:
            key: Silinecek key
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            if not self.connected:
                return False
            
            result = self.redis.delete(key)
            logger.info(f"Key silindi: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"Key silme hatası ({key}): {str(e)}")
            return False
    
    def set_ttl(self, key: str, ttl: int) -> bool:
        """
        Key'in TTL'ini ayarla
        
        Args:
            key: Key adı
            ttl: TTL (saniye)
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            if not self.connected or not self.redis.exists(key):
                return False
            
            result = self.redis.expire(key, ttl)
            logger.info(f"TTL ayarlandı: {key} = {ttl}s")
            return result
        except Exception as e:
            logger.error(f"TTL ayarlama hatası ({key}): {str(e)}")
            return False
