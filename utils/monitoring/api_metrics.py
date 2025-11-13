"""
API Metrics - API Endpoint Performance Monitoring
Developer Dashboard için API endpoint performans izleme servisi
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class APIMetrics:
    """API endpoint performans izleme servisi"""
    
    # In-memory metrics storage (production'da Redis kullanılmalı)
    _metrics = defaultdict(lambda: {
        'request_count': 0,
        'total_duration': 0.0,
        'error_count': 0,
        'status_codes': defaultdict(int),
        'response_times': [],
        'last_request': None
    })
    _lock = threading.Lock()
    
    @classmethod
    def track_request(
        cls,
        endpoint: str,
        duration: float,
        status_code: int,
        method: str = 'GET',
        user_id: Optional[int] = None
    ) -> None:
        """
        API request'i track et
        
        Args:
            endpoint: Flask endpoint adı
            duration: Request süresi (saniye)
            status_code: HTTP status code
            method: HTTP method
            user_id: Kullanıcı ID
        """
        try:
            with cls._lock:
                metrics = cls._metrics[endpoint]
                
                # Request sayısını artır
                metrics['request_count'] += 1
                
                # Toplam süreyi ekle
                metrics['total_duration'] += duration
                
                # Hata sayısını artır (4xx, 5xx)
                if status_code >= 400:
                    metrics['error_count'] += 1
                
                # Status code sayacı
                metrics['status_codes'][status_code] += 1
                
                # Response time'ları sakla (son 1000 request)
                metrics['response_times'].append(duration)
                if len(metrics['response_times']) > 1000:
                    metrics['response_times'].pop(0)
                
                # Son request zamanı
                metrics['last_request'] = datetime.utcnow()
                
                # Method bilgisi
                if 'methods' not in metrics:
                    metrics['methods'] = defaultdict(int)
                metrics['methods'][method] += 1
                
        except Exception as e:
            logger.error(f"Track request hatası: {str(e)}")
    
    @classmethod
    def get_endpoint_stats(cls, sort_by: str = 'avg_time') -> List[Dict[str, Any]]:
        """
        Tüm endpoint istatistiklerini getir
        
        Args:
            sort_by: Sıralama kriteri (avg_time, request_count, error_rate)
            
        Returns:
            List[Dict]: Endpoint istatistikleri
        """
        try:
            stats = []
            
            with cls._lock:
                for endpoint, metrics in cls._metrics.items():
                    request_count = metrics['request_count']
                    if request_count == 0:
                        continue
                    
                    avg_time = metrics['total_duration'] / request_count
                    error_rate = (metrics['error_count'] / request_count) * 100
                    
                    # Response time percentiles
                    response_times = sorted(metrics['response_times'])
                    p50 = cls._percentile(response_times, 50)
                    p95 = cls._percentile(response_times, 95)
                    p99 = cls._percentile(response_times, 99)
                    
                    stats.append({
                        'endpoint': endpoint,
                        'request_count': request_count,
                        'avg_response_time': round(avg_time, 4),
                        'error_count': metrics['error_count'],
                        'error_rate': round(error_rate, 2),
                        'p50': round(p50, 4),
                        'p95': round(p95, 4),
                        'p99': round(p99, 4),
                        'last_request': metrics['last_request'].isoformat() if metrics['last_request'] else None,
                        'status_codes': dict(metrics['status_codes']),
                        'methods': dict(metrics.get('methods', {}))
                    })
            
            # Sıralama
            if sort_by == 'avg_time':
                stats.sort(key=lambda x: x['avg_response_time'], reverse=True)
            elif sort_by == 'request_count':
                stats.sort(key=lambda x: x['request_count'], reverse=True)
            elif sort_by == 'error_rate':
                stats.sort(key=lambda x: x['error_rate'], reverse=True)
            
            return stats
        except Exception as e:
            logger.error(f"Get endpoint stats hatası: {str(e)}")
            return []
    
    @classmethod
    def get_endpoint_details(cls, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Belirli bir endpoint'in detaylı istatistiklerini getir
        
        Args:
            endpoint: Endpoint adı
            
        Returns:
            Dict: Endpoint detayları
        """
        try:
            with cls._lock:
                if endpoint not in cls._metrics:
                    return None
                
                metrics = cls._metrics[endpoint]
                request_count = metrics['request_count']
                
                if request_count == 0:
                    return None
                
                avg_time = metrics['total_duration'] / request_count
                error_rate = (metrics['error_count'] / request_count) * 100
                
                # Response time statistics
                response_times = sorted(metrics['response_times'])
                min_time = min(response_times) if response_times else 0
                max_time = max(response_times) if response_times else 0
                
                return {
                    'endpoint': endpoint,
                    'request_count': request_count,
                    'total_duration': round(metrics['total_duration'], 4),
                    'avg_response_time': round(avg_time, 4),
                    'min_response_time': round(min_time, 4),
                    'max_response_time': round(max_time, 4),
                    'error_count': metrics['error_count'],
                    'error_rate': round(error_rate, 2),
                    'success_rate': round(100 - error_rate, 2),
                    'p50': round(cls._percentile(response_times, 50), 4),
                    'p75': round(cls._percentile(response_times, 75), 4),
                    'p90': round(cls._percentile(response_times, 90), 4),
                    'p95': round(cls._percentile(response_times, 95), 4),
                    'p99': round(cls._percentile(response_times, 99), 4),
                    'last_request': metrics['last_request'].isoformat() if metrics['last_request'] else None,
                    'status_codes': dict(metrics['status_codes']),
                    'methods': dict(metrics.get('methods', {})),
                    'timestamp': datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Get endpoint details hatası: {str(e)}")
            return None
    
    @classmethod
    def get_error_rate(cls, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Hata oranlarını getir
        
        Args:
            endpoint: Belirli bir endpoint (None ise tümü)
            
        Returns:
            Dict: Hata oranı istatistikleri
        """
        try:
            with cls._lock:
                if endpoint:
                    # Belirli endpoint için
                    if endpoint not in cls._metrics:
                        return {
                            'endpoint': endpoint,
                            'error_rate': 0,
                            'error_count': 0,
                            'request_count': 0
                        }
                    
                    metrics = cls._metrics[endpoint]
                    request_count = metrics['request_count']
                    error_count = metrics['error_count']
                    error_rate = (error_count / request_count * 100) if request_count > 0 else 0
                    
                    return {
                        'endpoint': endpoint,
                        'error_rate': round(error_rate, 2),
                        'error_count': error_count,
                        'request_count': request_count,
                        'status_codes': dict(metrics['status_codes'])
                    }
                else:
                    # Tüm endpoint'ler için
                    total_requests = 0
                    total_errors = 0
                    error_by_endpoint = []
                    
                    for ep, metrics in cls._metrics.items():
                        request_count = metrics['request_count']
                        error_count = metrics['error_count']
                        
                        total_requests += request_count
                        total_errors += error_count
                        
                        if error_count > 0:
                            error_rate = (error_count / request_count * 100) if request_count > 0 else 0
                            error_by_endpoint.append({
                                'endpoint': ep,
                                'error_rate': round(error_rate, 2),
                                'error_count': error_count,
                                'request_count': request_count
                            })
                    
                    # Hata oranına göre sırala
                    error_by_endpoint.sort(key=lambda x: x['error_rate'], reverse=True)
                    
                    overall_error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
                    
                    return {
                        'overall_error_rate': round(overall_error_rate, 2),
                        'total_errors': total_errors,
                        'total_requests': total_requests,
                        'error_by_endpoint': error_by_endpoint[:10],  # Top 10
                        'timestamp': datetime.utcnow().isoformat()
                    }
        except Exception as e:
            logger.error(f"Get error rate hatası: {str(e)}")
            return {
                'error': str(e)
            }
    
    @classmethod
    def get_performance_summary(cls) -> Dict[str, Any]:
        """
        Genel performans özeti
        
        Returns:
            Dict: Performans özeti
        """
        try:
            with cls._lock:
                total_requests = 0
                total_errors = 0
                total_duration = 0.0
                all_response_times = []
                endpoint_count = 0
                
                for metrics in cls._metrics.values():
                    if metrics['request_count'] > 0:
                        endpoint_count += 1
                        total_requests += metrics['request_count']
                        total_errors += metrics['error_count']
                        total_duration += metrics['total_duration']
                        all_response_times.extend(metrics['response_times'])
                
                avg_response_time = (total_duration / total_requests) if total_requests > 0 else 0
                error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
                
                # Overall percentiles
                all_response_times.sort()
                p50 = cls._percentile(all_response_times, 50)
                p95 = cls._percentile(all_response_times, 95)
                p99 = cls._percentile(all_response_times, 99)
                
                return {
                    'total_endpoints': endpoint_count,
                    'total_requests': total_requests,
                    'total_errors': total_errors,
                    'error_rate': round(error_rate, 2),
                    'avg_response_time': round(avg_response_time, 4),
                    'p50_response_time': round(p50, 4),
                    'p95_response_time': round(p95, 4),
                    'p99_response_time': round(p99, 4),
                    'timestamp': datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Get performance summary hatası: {str(e)}")
            return {
                'error': str(e)
            }
    
    @classmethod
    def reset_metrics(cls, endpoint: Optional[str] = None) -> bool:
        """
        Metrikleri sıfırla
        
        Args:
            endpoint: Belirli bir endpoint (None ise tümü)
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            with cls._lock:
                if endpoint:
                    if endpoint in cls._metrics:
                        del cls._metrics[endpoint]
                else:
                    cls._metrics.clear()
                
                logger.info(f"Metrics sıfırlandı: {endpoint or 'tümü'}")
                return True
        except Exception as e:
            logger.error(f"Reset metrics hatası: {str(e)}")
            return False
    
    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """
        Percentile hesapla
        
        Args:
            data: Sıralı veri listesi
            percentile: Percentile değeri (0-100)
            
        Returns:
            float: Percentile değeri
        """
        if not data:
            return 0.0
        
        k = (len(data) - 1) * (percentile / 100)
        f = int(k)
        c = k - f
        
        if f + 1 < len(data):
            return data[f] + (data[f + 1] - data[f]) * c
        else:
            return data[f]
