"""
Performance Monitoring
Query performance tracking ve slow query detection
"""

import time
import hashlib
from functools import wraps
from datetime import datetime, timezone
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
from flask import request
from models import db


class PerformanceMonitor:
    """Query performance tracker"""
    
    def __init__(self, slow_query_threshold=1.0):
        """
        Args:
            slow_query_threshold: Slow query threshold in seconds
        """
        self.slow_query_threshold = slow_query_threshold
        self.query_stats = []
    
    def track_query(self, func):
        """
        Decorator to track query performance
        
        Usage:
            @monitor.track_query
            def my_query_function():
                return User.query.all()
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log slow queries
                if execution_time > self.slow_query_threshold:
                    self._log_slow_query(
                        func.__name__,
                        execution_time,
                        args,
                        kwargs
                    )
                
                # Store stats
                self.query_stats.append({
                    'function': func.__name__,
                    'execution_time': execution_time,
                    'timestamp': get_kktc_now().isoformat()
                })
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                self._log_failed_query(
                    func.__name__,
                    execution_time,
                    str(e)
                )
                raise
        
        return wrapper
    
    def _log_slow_query(self, func_name, execution_time, args, kwargs):
        """Log slow query to database"""
        try:
            query_hash = hashlib.md5(func_name.encode()).hexdigest()
            
            # Bu kısım query_performance_log tablosuna yazacak
            # Şimdilik print ediyoruz
            print(f"⚠️  SLOW QUERY: {func_name} took {execution_time:.2f}s")
            
            # TODO: Save to query_performance_log table
            # from models import QueryPerformanceLog
            # log = QueryPerformanceLog(
            #     query_hash=query_hash,
            #     query_text=func_name,
            #     execution_time_ms=execution_time * 1000,
            #     endpoint=request.endpoint if request else None
            # )
            # db.session.add(log)
            # db.session.commit()
            
        except Exception as e:
            print(f"Error logging slow query: {str(e)}")
    
    def _log_failed_query(self, func_name, execution_time, error):
        """Log failed query"""
        print(f"❌ FAILED QUERY: {func_name} failed after {execution_time:.2f}s: {error}")
    
    def get_stats(self):
        """Get performance statistics"""
        if not self.query_stats:
            return {
                'total_queries': 0,
                'avg_time': 0,
                'max_time': 0,
                'min_time': 0
            }
        
        times = [s['execution_time'] for s in self.query_stats]
        
        return {
            'total_queries': len(self.query_stats),
            'avg_time': sum(times) / len(times),
            'max_time': max(times),
            'min_time': min(times),
            'slow_queries': len([t for t in times if t > self.slow_query_threshold])
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.query_stats = []


# Global monitor instance
monitor = PerformanceMonitor(slow_query_threshold=1.0)

