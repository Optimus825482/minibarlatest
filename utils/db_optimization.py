"""
Database Optimizasyon Modülü
Fiyatlandırma ve Karlılık Sistemi için veritabanı optimizasyonları

Erkan için - Database Performance Optimization
"""

from sqlalchemy import text, inspect
import logging

logger = logging.getLogger(__name__)


def get_db():
    """Lazy import to avoid circular dependency"""
    from app import db
    return db


class DatabaseOptimizer:
    """Veritabanı optimizasyon servisi"""

    @staticmethod
    def check_missing_indexes():
        """
        Eksik index'leri kontrol et ve öner
        
        Returns:
            dict: Eksik index önerileri
        """
        try:
            db = get_db()
            missing_indexes = []
            
            # Fiyatlandırma tabloları için kritik index'ler
            critical_indexes = {
                'urun_tedarikci_fiyatlari': [
                    ('idx_urun_tedarikci_aktif', ['urun_id', 'tedarikci_id', 'aktif']),
                    ('idx_urun_fiyat_tarih', ['urun_id', 'baslangic_tarihi', 'bitis_tarihi']),
                ],
                'oda_tipi_satis_fiyatlari': [
                    ('idx_oda_tipi_urun_aktif', ['oda_tipi', 'urun_id', 'aktif']),
                ],
                'sezon_fiyatlandirma': [
                    ('idx_sezon_tarih_aktif', ['baslangic_tarihi', 'bitis_tarihi', 'aktif']),
                ],
                'kampanyalar': [
                    ('idx_kampanya_aktif_tarih', ['aktif', 'baslangic_tarihi', 'bitis_tarihi']),
                ],
                'bedelsiz_limitler': [
                    ('idx_bedelsiz_oda_aktif', ['oda_id', 'aktif']),
                ],
                'minibar_islem_detaylari': [
                    ('idx_islem_detay_urun', ['urun_id', 'islem_id']),
                    ('idx_islem_detay_kar', ['kar_tutari', 'kar_orani']),
                ],
                'donemsel_kar_analizi': [
                    ('idx_kar_analiz_otel_donem', ['otel_id', 'donem_tipi', 'baslangic_tarihi']),
                ],
                'urun_stok': [
                    ('idx_urun_stok_otel', ['otel_id', 'urun_id']),
                    ('idx_urun_stok_kritik', ['mevcut_stok', 'kritik_stok_seviyesi']),
                ],
                'urun_fiyat_gecmisi': [
                    ('idx_fiyat_gecmis_urun_tarih', ['urun_id', 'degisiklik_tarihi']),
                ],
            }
            
            inspector = inspect(db.engine)
            
            for table_name, indexes in critical_indexes.items():
                # Tablo var mı kontrol et
                if table_name not in inspector.get_table_names():
                    logger.warning(f"Tablo bulunamadı: {table_name}")
                    continue
                
                existing_indexes = {idx['name'] for idx in inspector.get_indexes(table_name)}
                
                for index_name, columns in indexes:
                    if index_name not in existing_indexes:
                        missing_indexes.append({
                            'table': table_name,
                            'index_name': index_name,
                            'columns': columns,
                            'sql': f"CREATE INDEX {index_name} ON {table_name} ({', '.join(columns)});"
                        })
            
            return {
                'status': 'success',
                'missing_count': len(missing_indexes),
                'missing_indexes': missing_indexes
            }
            
        except Exception as e:
            logger.error(f"Index kontrolü hatası: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    @staticmethod
    def create_missing_indexes():
        """
        Eksik index'leri oluştur
        
        Returns:
            dict: Oluşturma sonucu
        """
        try:
            db = get_db()
            result = DatabaseOptimizer.check_missing_indexes()
            
            if result['status'] == 'error':
                return result
            
            created_indexes = []
            failed_indexes = []
            
            for index_info in result['missing_indexes']:
                try:
                    db.session.execute(text(index_info['sql']))
                    db.session.commit()
                    created_indexes.append(index_info['index_name'])
                    logger.info(f"Index oluşturuldu: {index_info['index_name']}")
                except Exception as e:
                    db.session.rollback()
                    failed_indexes.append({
                        'index': index_info['index_name'],
                        'error': str(e)
                    })
                    logger.error(f"Index oluşturma hatası ({index_info['index_name']}): {e}")
            
            return {
                'status': 'success',
                'created_count': len(created_indexes),
                'created_indexes': created_indexes,
                'failed_count': len(failed_indexes),
                'failed_indexes': failed_indexes
            }
            
        except Exception as e:
            logger.error(f"Index oluşturma hatası: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    @staticmethod
    def analyze_query_performance():
        """
        Query performansını analiz et
        
        Returns:
            dict: Performans analizi
        """
        try:
            db = get_db()
            # Yavaş query'leri tespit et (query_logs tablosundan)
            slow_queries = db.session.execute(text("""
                SELECT 
                    endpoint,
                    AVG(execution_time) as avg_time,
                    MAX(execution_time) as max_time,
                    COUNT(*) as call_count
                FROM query_logs
                WHERE timestamp > NOW() - INTERVAL '24 hours'
                GROUP BY endpoint
                HAVING AVG(execution_time) > 1.0
                ORDER BY avg_time DESC
                LIMIT 10
            """)).fetchall()
            
            # Tablo boyutları
            table_sizes = db.session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY size_bytes DESC
                LIMIT 10
            """)).fetchall()
            
            # Index kullanım istatistikleri
            index_usage = db.session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as index_scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC
                LIMIT 20
            """)).fetchall()
            
            # Kullanılmayan index'ler
            unused_indexes = db.session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                AND idx_scan = 0
                AND indexname NOT LIKE '%_pkey'
                ORDER BY pg_relation_size(indexrelid) DESC
            """)).fetchall()
            
            return {
                'status': 'success',
                'slow_queries': [
                    {
                        'endpoint': row[0],
                        'avg_time': float(row[1]),
                        'max_time': float(row[2]),
                        'call_count': row[3]
                    }
                    for row in slow_queries
                ],
                'table_sizes': [
                    {
                        'schema': row[0],
                        'table': row[1],
                        'size': row[2],
                        'size_bytes': row[3]
                    }
                    for row in table_sizes
                ],
                'index_usage': [
                    {
                        'schema': row[0],
                        'table': row[1],
                        'index': row[2],
                        'scans': row[3],
                        'tuples_read': row[4],
                        'tuples_fetched': row[5]
                    }
                    for row in index_usage
                ],
                'unused_indexes': [
                    {
                        'schema': row[0],
                        'table': row[1],
                        'index': row[2],
                        'size': row[3]
                    }
                    for row in unused_indexes
                ]
            }
            
        except Exception as e:
            logger.error(f"Query performans analizi hatası: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    @staticmethod
    def optimize_tables():
        """
        Tabloları optimize et (VACUUM ANALYZE)
        
        Returns:
            dict: Optimizasyon sonucu
        """
        try:
            db = get_db()
            # Fiyatlandırma ile ilgili kritik tablolar
            critical_tables = [
                'urun_tedarikci_fiyatlari',
                'oda_tipi_satis_fiyatlari',
                'kampanyalar',
                'bedelsiz_limitler',
                'minibar_islem_detaylari',
                'donemsel_kar_analizi',
                'urun_stok',
                'urun_fiyat_gecmisi',
            ]
            
            optimized_tables = []
            failed_tables = []
            
            for table in critical_tables:
                try:
                    # ANALYZE komutu - istatistikleri güncelle
                    db.session.execute(text(f"ANALYZE {table}"))
                    db.session.commit()
                    optimized_tables.append(table)
                    logger.info(f"Tablo optimize edildi: {table}")
                except Exception as e:
                    db.session.rollback()
                    failed_tables.append({
                        'table': table,
                        'error': str(e)
                    })
                    logger.error(f"Tablo optimizasyon hatası ({table}): {e}")
            
            return {
                'status': 'success',
                'optimized_count': len(optimized_tables),
                'optimized_tables': optimized_tables,
                'failed_count': len(failed_tables),
                'failed_tables': failed_tables
            }
            
        except Exception as e:
            logger.error(f"Tablo optimizasyon hatası: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    @staticmethod
    def get_connection_pool_stats():
        """
        Connection pool istatistiklerini getir
        
        Returns:
            dict: Pool istatistikleri
        """
        try:
            db = get_db()
            pool = db.engine.pool
            
            return {
                'status': 'success',
                'pool_size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'total_connections': pool.size() + pool.overflow(),
                'max_overflow': db.engine.pool._max_overflow,
                'pool_timeout': db.engine.pool._timeout,
                'pool_recycle': db.engine.pool._recycle
            }
            
        except Exception as e:
            logger.error(f"Connection pool stats hatası: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    @staticmethod
    def check_database_health():
        """
        Veritabanı sağlık kontrolü
        
        Returns:
            dict: Sağlık durumu
        """
        try:
            db = get_db()
            # Connection testi
            db.session.execute(text("SELECT 1"))
            
            # Aktif connection sayısı
            active_connections = db.session.execute(text("""
                SELECT count(*) 
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """)).scalar()
            
            # Database boyutu
            db_size = db.session.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)).scalar()
            
            # Deadlock sayısı (son 24 saat)
            deadlocks = db.session.execute(text("""
                SELECT deadlocks 
                FROM pg_stat_database 
                WHERE datname = current_database()
            """)).scalar()
            
            # Cache hit ratio
            cache_hit_ratio = db.session.execute(text("""
                SELECT 
                    ROUND(
                        100.0 * sum(blks_hit) / NULLIF(sum(blks_hit) + sum(blks_read), 0),
                        2
                    ) as cache_hit_ratio
                FROM pg_stat_database
                WHERE datname = current_database()
            """)).scalar()
            
            return {
                'status': 'healthy',
                'active_connections': active_connections,
                'database_size': db_size,
                'deadlocks': deadlocks or 0,
                'cache_hit_ratio': float(cache_hit_ratio) if cache_hit_ratio else 0,
                'timestamp': db.session.execute(text("SELECT NOW()")).scalar()
            }
            
        except Exception as e:
            logger.error(f"Database health check hatası: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    @staticmethod
    def run_full_optimization():
        """
        Tam optimizasyon paketi çalıştır
        
        Returns:
            dict: Tüm optimizasyon sonuçları
        """
        try:
            db = get_db()
            results = {
                'timestamp': db.session.execute(text("SELECT NOW()")).scalar(),
                'health_check': DatabaseOptimizer.check_database_health(),
                'missing_indexes': DatabaseOptimizer.check_missing_indexes(),
                'query_performance': DatabaseOptimizer.analyze_query_performance(),
                'connection_pool': DatabaseOptimizer.get_connection_pool_stats(),
            }
            
            # Eksik index varsa oluştur
            if results['missing_indexes']['missing_count'] > 0:
                results['index_creation'] = DatabaseOptimizer.create_missing_indexes()
            
            # Tabloları optimize et
            results['table_optimization'] = DatabaseOptimizer.optimize_tables()
            
            return {
                'status': 'success',
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Full optimization hatası: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
