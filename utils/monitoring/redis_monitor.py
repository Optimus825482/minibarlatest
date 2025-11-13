"""
Redis Monitor - Redis Status and Performance Monitoring
Developer Dashboard için Redis izleme servisi
"""
import redis
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class RedisMonitor:
    """Redis izleme servisi"""
    
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
    
    def get_redis_info(self) -> Dict[str, Any]:
        """
        Redis genel bilgilerini getir
        
        Returns:
            Dict: Redis info
        """
        try:
            if not self.connected:
                return {
                    'connected': False,
                    'error': 'Redis bağlantısı yok'
                }
            
            info = self.redis.info()
            
            return {
                'connected': True,
                'redis_version': info.get('redis_version'),
                'redis_mode': info.get('redis_mode'),
                'os': info.get('os'),
                'arch_bits': info.get('arch_bits'),
                'process_id': info.get('process_id'),
                'tcp_port': info.get('tcp_port'),
                'uptime_in_seconds': info.get('uptime_in_seconds'),
                'uptime_in_days': info.get('uptime_in_days'),
                'config_file': info.get('config_file'),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Get redis info hatası: {str(e)}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Redis memory istatistiklerini getir
        
        Returns:
            Dict: Memory stats
        """
        try:
            if not self.connected:
                return {
                    'connected': False,
                    'error': 'Redis bağlantısı yok'
                }
            
            info = self.redis.info('memory')
            
            used_memory = info.get('used_memory', 0)
            used_memory_human = info.get('used_memory_human', '0B')
            used_memory_rss = info.get('used_memory_rss', 0)
            used_memory_peak = info.get('used_memory_peak', 0)
            used_memory_peak_human = info.get('used_memory_peak_human', '0B')
            maxmemory = info.get('maxmemory', 0)
            maxmemory_human = info.get('maxmemory_human', '0B')
            
            # Memory usage percentage
            memory_usage_percent = 0
            if maxmemory > 0:
                memory_usage_percent = (used_memory / maxmemory) * 100
            
            return {
                'connected': True,
                'used_memory': used_memory,
                'used_memory_human': used_memory_human,
                'used_memory_rss': used_memory_rss,
                'used_memory_peak': used_memory_peak,
                'used_memory_peak_human': used_memory_peak_human,
                'maxmemory': maxmemory,
                'maxmemory_human': maxmemory_human,
                'memory_usage_percent': round(memory_usage_percent, 2),
                'mem_fragmentation_ratio': info.get('mem_fragmentation_ratio', 0),
                'mem_allocator': info.get('mem_allocator'),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Get memory stats hatası: {str(e)}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def get_key_stats(self) -> Dict[str, Any]:
        """
        Redis key istatistiklerini getir
        
        Returns:
            Dict: Key stats
        """
        try:
            if not self.connected:
                return {
                    'connected': False,
                    'error': 'Redis bağlantısı yok'
                }
            
            info = self.redis.info('keyspace')
            stats_info = self.redis.info('stats')
            
            # Toplam key sayısı (tüm DB'ler)
            total_keys = 0
            db_stats = {}
            
            for key, value in info.items():
                if key.startswith('db'):
                    # Parse: keys=123,expires=45,avg_ttl=3600
                    parts = value.split(',')
                    keys_count = int(parts[0].split('=')[1])
                    expires_count = int(parts[1].split('=')[1]) if len(parts) > 1 else 0
                    
                    total_keys += keys_count
                    db_stats[key] = {
                        'keys': keys_count,
                        'expires': expires_count
                    }
            
            return {
                'connected': True,
                'total_keys': total_keys,
                'db_stats': db_stats,
                'keyspace_hits': stats_info.get('keyspace_hits', 0),
                'keyspace_misses': stats_info.get('keyspace_misses', 0),
                'evicted_keys': stats_info.get('evicted_keys', 0),
                'expired_keys': stats_info.get('expired_keys', 0),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Get key stats hatası: {str(e)}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def get_client_list(self) -> List[Dict[str, Any]]:
        """
        Bağlı client'ları listele
        
        Returns:
            List[Dict]: Client listesi
        """
        try:
            if not self.connected:
                return []
            
            clients = self.redis.client_list()
            
            return [
                {
                    'id': client.get('id'),
                    'addr': client.get('addr'),
                    'name': client.get('name'),
                    'age': client.get('age'),
                    'idle': client.get('idle'),
                    'db': client.get('db'),
                    'cmd': client.get('cmd'),
                    'flags': client.get('flags')
                }
                for client in clients
            ]
        except Exception as e:
            logger.error(f"Get client list hatası: {str(e)}")
            return []
    
    def get_slowlog(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Yavaş komutları getir
        
        Args:
            count: Kaç komut getirileceği
            
        Returns:
            List[Dict]: Slowlog entries
        """
        try:
            if not self.connected:
                return []
            
            slowlog = self.redis.slowlog_get(count)
            
            return [
                {
                    'id': entry['id'],
                    'start_time': entry['start_time'],
                    'duration': entry['duration'],  # microseconds
                    'command': ' '.join(str(arg) for arg in entry['command'])
                }
                for entry in slowlog
            ]
        except Exception as e:
            logger.error(f"Get slowlog hatası: {str(e)}")
            return []
    
    def ping(self) -> bool:
        """
        Redis bağlantısını test et
        
        Returns:
            bool: Bağlantı başarılı ise True
        """
        try:
            if not self.connected:
                return False
            
            return self.redis.ping()
        except Exception as e:
            logger.error(f"Ping hatası: {str(e)}")
            return False
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """
        Redis genel özet istatistikleri
        
        Returns:
            Dict: Özet istatistikler
        """
        try:
            if not self.connected:
                return {
                    'connected': False,
                    'error': 'Redis bağlantısı yok'
                }
            
            info = self.redis.info()
            stats = self.redis.info('stats')
            
            # Hit rate hesapla
            hits = stats.get('keyspace_hits', 0)
            misses = stats.get('keyspace_misses', 0)
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0
            
            return {
                'connected': True,
                'uptime_days': info.get('uptime_in_days', 0),
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'total_commands_processed': stats.get('total_commands_processed', 0),
                'instantaneous_ops_per_sec': stats.get('instantaneous_ops_per_sec', 0),
                'hit_rate': round(hit_rate, 2),
                'evicted_keys': stats.get('evicted_keys', 0),
                'expired_keys': stats.get('expired_keys', 0),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Get stats summary hatası: {str(e)}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def get_config(self, pattern: str = '*') -> Dict[str, str]:
        """
        Redis konfigürasyonunu getir
        
        Args:
            pattern: Config pattern
            
        Returns:
            Dict: Config değerleri
        """
        try:
            if not self.connected:
                return {}
            
            config = self.redis.config_get(pattern)
            return config
        except Exception as e:
            logger.error(f"Get config hatası: {str(e)}")
            return {}
