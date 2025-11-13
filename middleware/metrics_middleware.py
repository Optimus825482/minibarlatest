"""
Metrics Middleware - API Request Tracking
Her API request'i otomatik olarak track eder
"""
import time
import logging
from flask import g, request
from functools import wraps

logger = logging.getLogger(__name__)


def init_metrics_middleware(app):
    """
    Flask app'e metrics middleware'ini ekle
    
    Args:
        app: Flask application instance
    """
    
    @app.before_request
    def before_request():
        """Request başlamadan önce"""
        try:
            g.start_time = time.time()
            g.request_tracked = False
        except Exception as e:
            logger.error(f"Before request hatası: {str(e)}")
    
    @app.after_request
    def after_request(response):
        """Request tamamlandıktan sonra"""
        try:
            # Sadece API endpoint'lerini track et
            if not hasattr(g, 'start_time'):
                return response
            
            # Duration hesapla
            duration = time.time() - g.start_time
            
            # Endpoint bilgisi
            endpoint = request.endpoint
            method = request.method
            status_code = response.status_code
            
            # User ID (session'dan)
            user_id = None
            if hasattr(request, 'user_id'):
                user_id = request.user_id
            
            # Metrics'e kaydet
            if endpoint and not g.request_tracked:
                from utils.monitoring.api_metrics import APIMetrics
                APIMetrics.track_request(
                    endpoint=endpoint,
                    duration=duration,
                    status_code=status_code,
                    method=method,
                    user_id=user_id
                )
                g.request_tracked = True
            
            # Response header'a duration ekle
            response.headers['X-Response-Time'] = f"{duration:.4f}s"
            
        except Exception as e:
            logger.error(f"After request hatası: {str(e)}")
        
        return response
    
    logger.info("✅ Metrics middleware başlatıldı")


def track_endpoint(f):
    """
    Decorator: Belirli bir endpoint'i manuel olarak track et
    
    Usage:
        @app.route('/api/example')
        @track_endpoint
        def example():
            return {'status': 'ok'}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        try:
            response = f(*args, **kwargs)
            duration = time.time() - start_time
            
            # Track metrics
            from utils.monitoring.api_metrics import APIMetrics
            APIMetrics.track_request(
                endpoint=request.endpoint,
                duration=duration,
                status_code=200,  # Başarılı response
                method=request.method
            )
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            
            # Track error
            from utils.monitoring.api_metrics import APIMetrics
            APIMetrics.track_request(
                endpoint=request.endpoint,
                duration=duration,
                status_code=500,  # Error response
                method=request.method
            )
            
            raise e
    
    return decorated_function
