"""
Performance Profiler - System Performance Profiling
Developer Dashboard için performans profiling servisi
"""
import logging
import cProfile
import pstats
import io
import time
import psutil
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class PerformanceProfiler:
    """Performans profiling servisi"""
    
    # Aktif profiler'lar
    _active_profilers = {}
    _lock = threading.Lock()
    
    @classmethod
    def start_profiling(cls, duration: int = 60) -> str:
        """
        Profiling başlat
        
        Args:
            duration: Profiling süresi (saniye)
            
        Returns:
            str: Profile ID
        """
        try:
            profile_id = f"profile_{int(time.time())}"
            
            # cProfile oluştur
            profiler = cProfile.Profile()
            profiler.enable()
            
            with cls._lock:
                cls._active_profilers[profile_id] = {
                    'profiler': profiler,
                    'start_time': datetime.utcnow(),
                    'duration': duration,
                    'status': 'running'
                }
            
            logger.info(f"Profiling başlatıldı: {profile_id} ({duration}s)")
            
            return profile_id
        except Exception as e:
            logger.error(f"Start profiling hatası: {str(e)}")
            return None
    
    @classmethod
    def stop_profiling(cls, profile_id: str) -> Dict[str, Any]:
        """
        Profiling durdur
        
        Args:
            profile_id: Profile ID
            
        Returns:
            Dict: Profiling sonuçları
        """
        try:
            with cls._lock:
                if profile_id not in cls._active_profilers:
                    return {
                        'success': False,
                        'error': 'Profile bulunamadı'
                    }
                
                profile_data = cls._active_profilers[profile_id]
                profiler = profile_data['profiler']
                
                # Profiler'ı durdur
                profiler.disable()
                profile_data['status'] = 'stopped'
                profile_data['end_time'] = datetime.utcnow()
            
            # Stats oluştur
            stats_stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=stats_stream)
            stats.sort_stats('cumulative')
            stats.print_stats(50)  # Top 50
            
            logger.info(f"Profiling durduruldu: {profile_id}")
            
            return {
                'success': True,
                'profile_id': profile_id,
                'stats': stats_stream.getvalue()
            }
        except Exception as e:
            logger.error(f"Stop profiling hatası: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def get_profile_results(cls, profile_id: str) -> Optional[Dict[str, Any]]:
        """
        Profile sonuçlarını getir
        
        Args:
            profile_id: Profile ID
            
        Returns:
            Dict: Profile sonuçları
        """
        try:
            with cls._lock:
                if profile_id not in cls._active_profilers:
                    return None
                
                profile_data = cls._active_profilers[profile_id]
                profiler = profile_data['profiler']
            
            # Stats oluştur
            stats_stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=stats_stream)
            stats.sort_stats('cumulative')
            stats.print_stats(100)  # Top 100
            
            return {
                'profile_id': profile_id,
                'start_time': profile_data['start_time'].isoformat(),
                'end_time': profile_data.get('end_time').isoformat() if profile_data.get('end_time') else None,
                'status': profile_data['status'],
                'stats': stats_stream.getvalue()
            }
        except Exception as e:
            logger.error(f"Get profile results hatası: {str(e)}")
            return None
    
    @classmethod
    def get_cpu_hotspots(cls, profile_id: str) -> List[Dict[str, Any]]:
        """
        CPU hotspot'ları getir
        
        Args:
            profile_id: Profile ID
            
        Returns:
            List[Dict]: CPU hotspot'ları
        """
        try:
            with cls._lock:
                if profile_id not in cls._active_profilers:
                    return []
                
                profile_data = cls._active_profilers[profile_id]
                profiler = profile_data['profiler']
            
            # Stats oluştur
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            
            # Top fonksiyonları al
            hotspots = []
            for func, (cc, nc, tt, ct, callers) in list(stats.stats.items())[:20]:
                filename, line, func_name = func
                hotspots.append({
                    'function': func_name,
                    'filename': filename,
                    'line': line,
                    'call_count': cc,
                    'total_time': round(tt, 4),
                    'cumulative_time': round(ct, 4)
                })
            
            return hotspots
        except Exception as e:
            logger.error(f"Get CPU hotspots hatası: {str(e)}")
            return []
    
    @classmethod
    def get_memory_allocations(cls) -> Dict[str, Any]:
        """
        Memory allocation bilgilerini getir
        
        Returns:
            Dict: Memory allocations
        """
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss': memory_info.rss,
                'rss_mb': round(memory_info.rss / (1024 * 1024), 2),
                'vms': memory_info.vms,
                'vms_mb': round(memory_info.vms / (1024 * 1024), 2),
                'percent': process.memory_percent(),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Get memory allocations hatası: {str(e)}")
            return {
                'error': str(e)
            }
    
    @classmethod
    def export_profile(cls, profile_id: str, format: str = 'json') -> Optional[str]:
        """
        Profile sonuçlarını export et
        
        Args:
            profile_id: Profile ID
            format: Export formatı (json, text)
            
        Returns:
            str: Export edilmiş data
        """
        try:
            results = cls.get_profile_results(profile_id)
            if not results:
                return None
            
            if format == 'json':
                import json
                return json.dumps(results, indent=2)
            else:
                return results['stats']
        except Exception as e:
            logger.error(f"Export profile hatası: {str(e)}")
            return None
    
    @classmethod
    def list_active_profiles(cls) -> List[Dict[str, Any]]:
        """
        Aktif profile'ları listele
        
        Returns:
            List[Dict]: Aktif profile listesi
        """
        try:
            with cls._lock:
                profiles = []
                for profile_id, data in cls._active_profilers.items():
                    profiles.append({
                        'profile_id': profile_id,
                        'start_time': data['start_time'].isoformat(),
                        'duration': data['duration'],
                        'status': data['status']
                    })
                return profiles
        except Exception as e:
            logger.error(f"List active profiles hatası: {str(e)}")
            return []
