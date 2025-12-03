"""
Health Check ve Monitoring Routes
PostgreSQL migration için health check ve database monitoring endpoint'leri
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timezone
from sqlalchemy import text
from models import db
import os
import pytz

# KKTC Timezone (Kıbrıs - Europe/Nicosia)
KKTC_TZ = pytz.timezone('Europe/Nicosia')

def get_kktc_now():
    """Kıbrıs saat diliminde şu anki zamanı döndürür."""
    return datetime.now(KKTC_TZ)

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Sistem health check endpoint'i
    Database bağlantısı, connection pool durumu ve temel metrikleri kontrol eder
    """
    try:
        # Database connection test
        db.session.execute(text('SELECT 1'))
        db_status = 'healthy'
        db_type = 'postgresql' if 'postgresql' in str(db.engine.url) else 'mysql'
        
        # Connection pool statistics
        pool = db.engine.pool
        pool_stats = {
            'size': pool.size(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'checked_in': pool.size() - pool.checkedout()
        }
        
        # Database version
        if db_type == 'postgresql':
            version_result = db.session.execute(text('SELECT version()')).scalar()
        else:
            version_result = db.session.execute(text('SELECT VERSION()')).scalar()
        
        response = {
            'status': 'healthy',
            'timestamp': get_kktc_now().isoformat(),
            'database': {
                'status': db_status,
                'type': db_type,
                'version': version_result.split()[0] if version_result else 'unknown'
            },
            'connection_pool': pool_stats,
            'environment': os.getenv('FLASK_ENV', 'production')
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': get_kktc_now().isoformat()
        }), 503


@health_bp.route('/health/database', methods=['GET'])
def database_health():
    """
    Detaylı database health check
    Connection pool, active connections, database size gibi metrikleri döner
    """
    try:
        db_type = 'postgresql' if 'postgresql' in str(db.engine.url) else 'mysql'
        
        # Connection pool stats
        pool = db.engine.pool
        pool_stats = {
            'size': pool.size(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'checked_in': pool.size() - pool.checkedout(),
            'usage_percent': (pool.checkedout() / pool.size() * 100) if pool.size() > 0 else 0
        }
        
        # Database specific metrics
        if db_type == 'postgresql':
            # PostgreSQL metrics
            connection_stats = db.session.execute(text("""
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active,
                    count(*) FILTER (WHERE state = 'idle') as idle,
                    count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)).fetchone()
            
            db_size = db.session.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)).scalar()
            
            cache_hit_ratio = db.session.execute(text("""
                SELECT 
                    ROUND(
                        sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0) * 100, 
                        2
                    ) as cache_hit_ratio
                FROM pg_statio_user_tables
            """)).scalar()
            
            metrics = {
                'connections': {
                    'total': connection_stats[0],
                    'active': connection_stats[1],
                    'idle': connection_stats[2],
                    'idle_in_transaction': connection_stats[3]
                },
                'database_size': db_size,
                'cache_hit_ratio': float(cache_hit_ratio) if cache_hit_ratio else 0
            }
        else:
            # MySQL metrics
            connection_stats = db.session.execute(text("""
                SHOW STATUS LIKE 'Threads_connected'
            """)).fetchone()
            
            db_size = db.session.execute(text("""
                SELECT 
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as size_mb
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
            """)).scalar()
            
            metrics = {
                'connections': {
                    'total': int(connection_stats[1]) if connection_stats else 0
                },
                'database_size_mb': float(db_size) if db_size else 0
            }
        
        return jsonify({
            'status': 'healthy',
            'database_type': db_type,
            'connection_pool': pool_stats,
            'metrics': metrics,
            'timestamp': get_kktc_now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': get_kktc_now().isoformat()
        }), 500


@health_bp.route('/health/pool-stats', methods=['GET'])
def pool_statistics():
    """
    Connection pool detaylı istatistikleri
    """
    try:
        pool = db.engine.pool
        
        stats = {
            'pool_size': pool.size(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'checked_in': pool.size() - pool.checkedout(),
            'max_overflow': pool._max_overflow,
            'timeout': pool._timeout,
            'recycle': pool._recycle,
            'usage_percent': round((pool.checkedout() / pool.size() * 100), 2) if pool.size() > 0 else 0,
            'status': 'healthy' if pool.checkedout() < pool.size() * 0.8 else 'warning',
            'timestamp': get_kktc_now().isoformat()
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': get_kktc_now().isoformat()
        }), 500


@health_bp.route('/health/celery', methods=['GET'])
def celery_health():
    """
    Celery worker ve beat durumunu kontrol et
    Public endpoint - login gerektirmez
    """
    try:
        from celery_app import celery
        
        result = {
            'status': 'unknown',
            'timestamp': get_kktc_now().isoformat(),
            'workers': [],
            'beat': {'status': 'unknown'},
            'broker': {'status': 'unknown'}
        }
        
        # Broker bağlantısını kontrol et
        try:
            celery.control.ping(timeout=2)
            result['broker']['status'] = 'connected'
        except Exception as e:
            result['broker']['status'] = 'disconnected'
            result['broker']['error'] = str(e)
        
        # Worker durumunu kontrol et
        try:
            inspect = celery.control.inspect(timeout=3)
            active_workers = inspect.active()
            
            if active_workers:
                result['workers'] = list(active_workers.keys())
                result['worker_count'] = len(active_workers)
                result['status'] = 'healthy'
            else:
                result['worker_count'] = 0
                result['status'] = 'no_workers'
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        # Zamanlanmış görevleri kontrol et (Beat çalışıyor mu?)
        try:
            inspect = celery.control.inspect(timeout=3)
            scheduled = inspect.scheduled()
            
            if scheduled:
                result['beat']['status'] = 'active'
                result['beat']['scheduled_tasks'] = sum(len(tasks) for tasks in scheduled.values())
            else:
                # Beat çalışıyor olabilir ama henüz zamanlanmış görev yok
                result['beat']['status'] = 'no_scheduled_tasks'
        except Exception as e:
            result['beat']['error'] = str(e)
        
        # Genel durum belirleme
        if result['broker']['status'] == 'connected' and result.get('worker_count', 0) > 0:
            result['status'] = 'healthy'
        elif result['broker']['status'] == 'connected':
            result['status'] = 'degraded'  # Broker var ama worker yok
        else:
            result['status'] = 'unhealthy'
        
        status_code = 200 if result['status'] == 'healthy' else 503
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': get_kktc_now().isoformat()
        }), 500


@health_bp.route('/health/routes', methods=['GET'])
def list_routes():
    """
    Tüm kayıtlı route'ları listele - Debug için
    """
    try:
        from flask import current_app
        
        routes = []
        for rule in current_app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': str(rule)
            })
        
        # Alfabetik sırala
        routes.sort(key=lambda x: x['path'])
        
        return jsonify({
            'total_routes': len(routes),
            'routes': routes,
            'timestamp': get_kktc_now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': get_kktc_now().isoformat()
        }), 500
