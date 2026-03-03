"""
System Monitor Routes
Sistem performans izleme ve log takibi API endpoint'leri
Superadmin erişimli — Executive Dashboard'a entegre
"""

import os
import time
import logging
import psutil
from datetime import datetime, timedelta
from flask import render_template, jsonify, request
from models import db
from sqlalchemy import text
from utils.decorators import login_required, role_required
from utils.monitoring.api_metrics import APIMetrics

logger = logging.getLogger(__name__)

# In-memory error log buffer (circular, max 200 entries)
_error_log_buffer = []
_ERROR_LOG_MAX = 200
_app_start_time = time.time()


def capture_error_log(message, level='ERROR', module=None):
    """Capture an error/warning into the in-memory buffer"""
    global _error_log_buffer
    _error_log_buffer.append({
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'module': module or 'app',
        'message': str(message)[:500]
    })
    if len(_error_log_buffer) > _ERROR_LOG_MAX:
        _error_log_buffer = _error_log_buffer[-_ERROR_LOG_MAX:]


class _ErrorCapture(logging.Handler):
    """Logging handler that captures ERROR+ into our buffer"""
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            capture_error_log(
                self.format(record),
                level=record.levelname,
                module=record.module
            )


def register_system_monitor_routes(app):
    """System monitor route'larını register et"""

    # Attach error capture handler to root logger
    handler = _ErrorCapture()
    handler.setLevel(logging.WARNING)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger().addHandler(handler)

    @app.route('/system-monitor')
    @login_required
    @role_required('superadmin')
    def system_monitor():
        """System Monitor sayfası"""
        return render_template('sistem_yoneticisi/system_monitor.html')

    @app.route('/api/system-monitor/overview')
    @login_required
    @role_required('superadmin')
    def api_system_overview():
        """Genel sistem durumu — gauge'lar için"""
        try:
            # CPU & Memory (container-aware)
            cpu_percent = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()

            # Disk
            disk = psutil.disk_usage('/')

            # Uptime
            uptime_seconds = time.time() - _app_start_time
            uptime_str = str(timedelta(seconds=int(uptime_seconds)))

            # DB connections
            db_stats = _get_db_connection_stats()

            # API metrics summary
            api_summary = APIMetrics.get_performance_summary()

            # Process info
            proc = psutil.Process(os.getpid())
            proc_mem = proc.memory_info().rss / (1024 * 1024)  # MB

            return jsonify({
                'success': True,
                'data': {
                    'cpu': {
                        'percent': cpu_percent,
                        'cores': psutil.cpu_count()
                    },
                    'memory': {
                        'percent': mem.percent,
                        'used_mb': round(mem.used / (1024**2)),
                        'total_mb': round(mem.total / (1024**2)),
                        'available_mb': round(mem.available / (1024**2))
                    },
                    'disk': {
                        'percent': disk.percent,
                        'used_gb': round(disk.used / (1024**3), 1),
                        'total_gb': round(disk.total / (1024**3), 1)
                    },
                    'app': {
                        'uptime': uptime_str,
                        'uptime_seconds': int(uptime_seconds),
                        'process_memory_mb': round(proc_mem, 1),
                        'pid': os.getpid()
                    },
                    'database': db_stats,
                    'api': {
                        'total_requests': api_summary.get('total_requests', 0),
                        'avg_response_ms': round(api_summary.get('avg_response_time', 0) * 1000, 1),
                        'error_rate': api_summary.get('error_rate', 0),
                        'p95_ms': round(api_summary.get('p95_response_time', 0) * 1000, 1),
                        'endpoints_tracked': api_summary.get('endpoint_count', 0)
                    }
                }
            })
        except Exception as e:
            logger.error(f"System overview hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/system-monitor/endpoints')
    @login_required
    @role_required('superadmin')
    def api_system_endpoints():
        """En yavaş / en çok çağrılan endpoint'ler"""
        try:
            sort_by = request.args.get('sort', 'avg_time')
            stats = APIMetrics.get_endpoint_stats(sort_by=sort_by)
            # Top 20
            return jsonify({'success': True, 'data': stats[:20]})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/system-monitor/db-stats')
    @login_required
    @role_required('superadmin')
    def api_system_db_stats():
        """Database detaylı istatistikleri"""
        try:
            stats = {
                'connections': _get_db_connection_stats(),
                'cache_hit': _get_cache_hit_ratio(),
                'db_size': _get_db_size(),
                'table_sizes': _get_top_tables(),
                'active_queries': _get_active_queries()
            }
            return jsonify({'success': True, 'data': stats})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/system-monitor/error-log')
    @login_required
    @role_required('superadmin')
    def api_system_error_log():
        """Son hata logları"""
        try:
            limit = min(int(request.args.get('limit', 50)), _ERROR_LOG_MAX)
            logs = _error_log_buffer[-limit:]
            logs.reverse()  # newest first
            return jsonify({'success': True, 'data': logs, 'total': len(_error_log_buffer)})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


# ---- Helper functions ----

def _get_db_connection_stats():
    try:
        result = db.session.execute(text("""
            SELECT
                count(*) as total,
                count(*) FILTER (WHERE state = 'active') as active,
                count(*) FILTER (WHERE state = 'idle') as idle,
                count(*) FILTER (WHERE state = 'idle in transaction') as idle_tx
            FROM pg_stat_activity
            WHERE datname = current_database()
        """)).fetchone()
        return {
            'total': result[0], 'active': result[1],
            'idle': result[2], 'idle_in_transaction': result[3]
        }
    except Exception:
        db.session.rollback()
        return {'total': 0, 'active': 0, 'idle': 0, 'idle_in_transaction': 0}


def _get_cache_hit_ratio():
    try:
        result = db.session.execute(text("""
            SELECT CASE
                WHEN sum(heap_blks_hit) + sum(heap_blks_read) = 0 THEN 0
                ELSE ROUND(sum(heap_blks_hit)::numeric /
                    (sum(heap_blks_hit) + sum(heap_blks_read)) * 100, 2)
            END FROM pg_statio_user_tables
        """)).scalar()
        return float(result or 0)
    except Exception:
        db.session.rollback()
        return 0


def _get_db_size():
    try:
        return db.session.execute(
            text("SELECT pg_size_pretty(pg_database_size(current_database()))")
        ).scalar() or 'N/A'
    except Exception:
        db.session.rollback()
        return 'N/A'


def _get_top_tables():
    try:
        rows = db.session.execute(text("""
            SELECT tablename,
                   pg_size_pretty(pg_total_relation_size('public.'||tablename)) as size,
                   pg_total_relation_size('public.'||tablename) as bytes
            FROM pg_tables WHERE schemaname='public'
            ORDER BY pg_total_relation_size('public.'||tablename) DESC LIMIT 10
        """)).fetchall()
        return [{'table': r[0], 'size': r[1], 'bytes': r[2]} for r in rows]
    except Exception:
        db.session.rollback()
        return []


def _get_active_queries():
    try:
        rows = db.session.execute(text("""
            SELECT pid, state, EXTRACT(EPOCH FROM now()-query_start)::int as duration_sec,
                   LEFT(query, 120) as query
            FROM pg_stat_activity
            WHERE datname = current_database() AND state = 'active'
              AND pid != pg_backend_pid()
            ORDER BY query_start LIMIT 5
        """)).fetchall()
        return [{'pid': r[0], 'state': r[1], 'duration': r[2], 'query': r[3]} for r in rows]
    except Exception:
        db.session.rollback()
        return []
