"""
Database Metrics Collector
PostgreSQL database metrics collection
"""

import logging
from sqlalchemy import text
from models import db

logger = logging.getLogger(__name__)


class DatabaseMetrics:
    """Database metrics collector"""
    
    def collect_all_metrics(self):
        """Collect all database metrics"""
        db_type = 'postgresql' if 'postgresql' in str(db.engine.url) else 'mysql'
        
        if db_type == 'postgresql':
            return {
                'connection_stats': self.get_connection_stats(),
                'table_sizes': self.get_table_sizes(),
                'index_usage': self.get_index_usage(),
                'cache_hit_ratio': self.get_cache_hit_ratio(),
                'database_size': self.get_database_size()
            }
        else:
            return {
                'connection_stats': self.get_mysql_connection_stats(),
                'database_size': self.get_mysql_database_size()
            }
    
    def get_connection_stats(self):
        """Get PostgreSQL connection statistics"""
        try:
            query = text("""
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active,
                    count(*) FILTER (WHERE state = 'idle') as idle,
                    count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)
            
            result = db.session.execute(query).fetchone()
            return {
                'total': result[0],
                'active': result[1],
                'idle': result[2],
                'idle_in_transaction': result[3]
            }
        except Exception as e:
            logger.error(f"Error getting connection stats: {str(e)}")
            return {}
    
    def get_table_sizes(self):
        """Get table sizes"""
        try:
            query = text("""
                SELECT 
                    tablename,
                    pg_size_pretty(pg_total_relation_size('public.'||tablename)) as size,
                    pg_total_relation_size('public.'||tablename) as size_bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size('public.'||tablename) DESC
                LIMIT 20
            """)
            
            results = db.session.execute(query).fetchall()
            return [
                {
                    'table': row[0],
                    'size': row[1],
                    'size_bytes': row[2]
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error getting table sizes: {str(e)}")
            return []
    
    def get_index_usage(self):
        """Get index usage statistics"""
        try:
            query = text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    pg_size_pretty(pg_relation_size(indexrelid)) as size
                FROM pg_stat_user_indexes
                ORDER BY idx_scan DESC
                LIMIT 20
            """)
            
            results = db.session.execute(query).fetchall()
            return [
                {
                    'schema': row[0],
                    'table': row[1],
                    'index': row[2],
                    'scans': row[3],
                    'tuples_read': row[4],
                    'tuples_fetched': row[5],
                    'size': row[6]
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error getting index usage: {str(e)}")
            return []
    
    def get_cache_hit_ratio(self):
        """Get cache hit ratio"""
        try:
            query = text("""
                SELECT 
                    sum(heap_blks_read) as heap_read,
                    sum(heap_blks_hit) as heap_hit,
                    CASE 
                        WHEN sum(heap_blks_hit) + sum(heap_blks_read) = 0 THEN 0
                        ELSE ROUND(
                            sum(heap_blks_hit)::numeric / 
                            (sum(heap_blks_hit) + sum(heap_blks_read)) * 100, 
                            2
                        )
                    END as ratio
                FROM pg_statio_user_tables
            """)
            
            result = db.session.execute(query).fetchone()
            return {
                'heap_read': result[0] or 0,
                'heap_hit': result[1] or 0,
                'ratio': float(result[2] or 0)
            }
        except Exception as e:
            logger.error(f"Error getting cache hit ratio: {str(e)}")
            return {'ratio': 0}
    
    def get_database_size(self):
        """Get database size"""
        try:
            query = text("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)
            
            result = db.session.execute(query).scalar()
            return result
        except Exception as e:
            logger.error(f"Error getting database size: {str(e)}")
            return "Unknown"
    
    def get_mysql_connection_stats(self):
        """Get MySQL connection statistics"""
        try:
            query = text("SHOW STATUS LIKE 'Threads_connected'")
            result = db.session.execute(query).fetchone()
            return {
                'total': int(result[1]) if result else 0
            }
        except Exception as e:
            logger.error(f"Error getting MySQL connection stats: {str(e)}")
            return {}
    
    def get_mysql_database_size(self):
        """Get MySQL database size"""
        try:
            query = text("""
                SELECT 
                    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as size_mb
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
            """)
            
            result = db.session.execute(query).scalar()
            return f"{result} MB" if result else "Unknown"
        except Exception as e:
            logger.error(f"Error getting MySQL database size: {str(e)}")
            return "Unknown"
    
    def get_slow_queries(self, limit=10):
        """Get slowest queries from pg_stat_statements"""
        try:
            query = text("""
                SELECT 
                    query,
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    max_exec_time,
                    rows
                FROM pg_stat_statements
                WHERE query NOT LIKE '%pg_stat_statements%'
                ORDER BY mean_exec_time DESC
                LIMIT :limit
            """)
            
            results = db.session.execute(query, {'limit': limit}).fetchall()
            return [
                {
                    'query': row[0][:200],  # Truncate long queries
                    'calls': row[1],
                    'total_time': round(row[2], 2),
                    'mean_time': round(row[3], 2),
                    'max_time': round(row[4], 2),
                    'rows': row[5]
                }
                for row in results
            ]
        except Exception as e:
            # pg_stat_statements extension may not be enabled
            logger.warning(f"Note: pg_stat_statements not available: {str(e)}")
            return []


# Global metrics instance
metrics = DatabaseMetrics()
