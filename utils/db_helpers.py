"""
Database Helper Functions
PostgreSQL migration için database utility fonksiyonları
"""

import logging
import time
from functools import wraps
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DBAPIError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from models import db

logger = logging.getLogger(__name__)


def execute_with_retry(query, max_attempts=3):
    """
    Database query'sini retry logic ile çalıştır
    Connection error durumunda otomatik yeniden dener
    
    Args:
        query: SQLAlchemy query object
        max_attempts: Maksimum deneme sayısı
        
    Returns:
        Query result
        
    Raises:
        OperationalError: Tüm denemeler başarısız olursa
    """
    @retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((OperationalError, DBAPIError)),
        reraise=True
    )
    def _execute():
        try:
            return db.session.execute(query)
        except (OperationalError, DBAPIError) as e:
            # Connection error ise rollback ve retry
            if "connection" in str(e).lower() or "server" in str(e).lower():
                db.session.rollback()
                raise  # Retry edilecek
            # Diğer hatalar için retry yapma
            raise
    
    return _execute()


def safe_transaction(func):
    """
    Transaction decorator - Otomatik commit/rollback
    
    Usage:
        @safe_transaction
        def my_function():
            # Database operations
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            db.session.commit()
            return result
        except Exception as e:
            db.session.rollback()
            # Log error
            from utils.helpers import log_hata
            log_hata(e, modul=func.__name__)
            raise
    return wrapper


def check_connection():
    """
    Database bağlantısını kontrol et
    Bağlantı yoksa yeniden bağlanmayı dene
    
    Returns:
        bool: Bağlantı durumu
    """
    try:
        db.session.execute(text('SELECT 1'))
        return True
    except Exception:
        try:
            # Yeniden bağlanmayı dene
            db.session.remove()
            db.engine.dispose()
            db.session.execute(text('SELECT 1'))
            return True
        except Exception:
            return False


def reconnect_database():
    """
    Database bağlantısını yeniden kur
    Connection pool'u temizle ve yeni bağlantı oluştur
    """
    try:
        # Mevcut session'ı kapat
        db.session.remove()
        
        # Connection pool'u dispose et
        db.engine.dispose()
        
        # Yeni bağlantı test et
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        
        return True
    except Exception as e:
        from utils.helpers import log_hata
        log_hata(e, modul='reconnect_database')
        return False


def with_auto_reconnect(max_retries=3, delay=2):
    """
    Auto-reconnect decorator
    Database bağlantısı kesildiğinde otomatik yeniden bağlanır
    
    Args:
        max_retries: Maksimum yeniden deneme sayısı
        delay: Denemeler arası bekleme süresi (saniye)
        
    Usage:
        @with_auto_reconnect(max_retries=3, delay=2)
        def my_database_function():
            # Database operations
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    # Bağlantıyı kontrol et
                    if not check_connection():
                        reconnect_database()
                    
                    # Fonksiyonu çalıştır
                    return func(*args, **kwargs)

                except (OperationalError, DBAPIError) as e:
                    last_exception = e

                    # Connection error ise yeniden bağlan
                    if "connection" in str(e).lower() or "server" in str(e).lower():
                        logger.warning(
                            f"Connection error, attempt {attempt + 1}/{max_retries}"
                        )

                        if attempt < max_retries - 1:
                            time.sleep(delay * (attempt + 1))  # Exponential backoff
                            reconnect_database()
                        else:
                            raise
                    else:
                        # Diğer hatalar için retry yapma
                        raise

                except Exception:
                    # Diğer hatalar için retry yapma
                    raise
            
            # Tüm denemeler başarısız
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def get_pool_stats():
    """
    Connection pool istatistiklerini al
    
    Returns:
        dict: Pool statistics
    """
    pool = db.engine.pool
    
    return {
        'size': pool.size(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'checked_in': pool.size() - pool.checkedout(),
        'usage_percent': round((pool.checkedout() / pool.size() * 100), 2) if pool.size() > 0 else 0
    }


def close_idle_connections():
    """
    Boşta olan bağlantıları kapat
    Connection pool'u optimize et
    """
    try:
        # Pool'daki tüm bağlantıları dispose et
        db.engine.dispose()
        return True
    except Exception as e:
        from utils.helpers import log_hata
        log_hata(e, modul='close_idle_connections')
        return False
