"""
Query Analyzer - Database Query Performance Monitoring
Developer Dashboard için query analiz ve optimizasyon servisi
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import text, inspect
from models import db, QueryLog

logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """Database query analiz servisi"""
    
    def __init__(self):
        """Initialize query analyzer"""
        self.db = db
    
    def capture_query(
        self,
        query_text: str,
        execution_time: float,
        endpoint: Optional[str] = None,
        user_id: Optional[int] = None,
        parameters: Optional[Dict] = None
    ) -> bool:
        """
        Query'yi logla
        
        Args:
            query_text: SQL query
            execution_time: Çalışma süresi (saniye)
            endpoint: Flask endpoint
            user_id: Kullanıcı ID
            parameters: Query parametreleri
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            query_log = QueryLog(
                query_text=query_text,
                execution_time=execution_time,
                endpoint=endpoint,
                user_id=user_id,
                parameters=parameters
            )
            self.db.session.add(query_log)
            self.db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Query capture hatası: {str(e)}")
            self.db.session.rollback()
            return False
    
    def get_recent_queries(
        self,
        limit: int = 100,
        min_execution_time: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Son query'leri getir
        
        Args:
            limit: Maksimum query sayısı
            min_execution_time: Minimum çalışma süresi filtresi (saniye)
            
        Returns:
            List[Dict]: Query listesi
        """
        try:
            query = QueryLog.query.order_by(QueryLog.timestamp.desc())
            
            if min_execution_time:
                query = query.filter(QueryLog.execution_time >= min_execution_time)
            
            queries = query.limit(limit).all()
            
            return [
                {
                    'id': q.id,
                    'query_text': q.query_text[:500],  # İlk 500 karakter
                    'execution_time': round(q.execution_time, 4),
                    'timestamp': q.timestamp.isoformat() if q.timestamp else None,
                    'endpoint': q.endpoint,
                    'user_id': q.user_id,
                    'is_slow': q.execution_time > 1.0
                }
                for q in queries
            ]
        except Exception as e:
            logger.error(f"Recent queries hatası: {str(e)}")
            return []
    
    def get_slow_queries(
        self,
        threshold: float = 1.0,
        limit: int = 50,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Yavaş query'leri getir
        
        Args:
            threshold: Yavaş query eşiği (saniye)
            limit: Maksimum query sayısı
            hours: Son kaç saat
            
        Returns:
            List[Dict]: Yavaş query listesi
        """
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            queries = QueryLog.query.filter(
                QueryLog.execution_time >= threshold,
                QueryLog.timestamp >= since
            ).order_by(
                QueryLog.execution_time.desc()
            ).limit(limit).all()
            
            return [
                {
                    'id': q.id,
                    'query_text': q.query_text[:500],
                    'execution_time': round(q.execution_time, 4),
                    'timestamp': q.timestamp.isoformat() if q.timestamp else None,
                    'endpoint': q.endpoint,
                    'user_id': q.user_id,
                    'severity': self._get_severity(q.execution_time)
                }
                for q in queries
            ]
        except Exception as e:
            logger.error(f"Slow queries hatası: {str(e)}")
            return []
    
    def get_query_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Query istatistiklerini getir
        
        Args:
            hours: Son kaç saat
            
        Returns:
            Dict: İstatistikler
        """
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Toplam query sayısı
            total_queries = QueryLog.query.filter(
                QueryLog.timestamp >= since
            ).count()
            
            # Ortalama execution time
            from sqlalchemy import func
            avg_time = self.db.session.query(
                func.avg(QueryLog.execution_time)
            ).filter(
                QueryLog.timestamp >= since
            ).scalar() or 0
            
            # En yavaş query
            slowest = QueryLog.query.filter(
                QueryLog.timestamp >= since
            ).order_by(
                QueryLog.execution_time.desc()
            ).first()
            
            # Yavaş query sayısı (>1s)
            slow_count = QueryLog.query.filter(
                QueryLog.timestamp >= since,
                QueryLog.execution_time >= 1.0
            ).count()
            
            # Çok yavaş query sayısı (>5s)
            very_slow_count = QueryLog.query.filter(
                QueryLog.timestamp >= since,
                QueryLog.execution_time >= 5.0
            ).count()
            
            # Endpoint bazlı istatistikler
            endpoint_stats = self.db.session.query(
                QueryLog.endpoint,
                func.count(QueryLog.id).label('count'),
                func.avg(QueryLog.execution_time).label('avg_time')
            ).filter(
                QueryLog.timestamp >= since,
                QueryLog.endpoint.isnot(None)
            ).group_by(
                QueryLog.endpoint
            ).order_by(
                func.avg(QueryLog.execution_time).desc()
            ).limit(10).all()
            
            return {
                'total_queries': total_queries,
                'avg_execution_time': round(avg_time, 4),
                'slowest_query_time': round(slowest.execution_time, 4) if slowest else 0,
                'slow_queries_count': slow_count,
                'very_slow_queries_count': very_slow_count,
                'slow_percentage': round((slow_count / total_queries * 100), 2) if total_queries > 0 else 0,
                'top_endpoints': [
                    {
                        'endpoint': stat.endpoint,
                        'count': stat.count,
                        'avg_time': round(stat.avg_time, 4)
                    }
                    for stat in endpoint_stats
                ],
                'period_hours': hours,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Query stats hatası: {str(e)}")
            return {
                'total_queries': 0,
                'error': str(e)
            }
    
    def explain_query(self, query_text: str) -> Dict[str, Any]:
        """
        Query EXPLAIN planını getir
        
        Args:
            query_text: SQL query
            
        Returns:
            Dict: EXPLAIN sonucu
        """
        try:
            # EXPLAIN ANALYZE çalıştır
            explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS) {query_text}"
            result = self.db.session.execute(text(explain_query))
            explain_plan = result.fetchone()[0]
            
            return {
                'success': True,
                'plan': explain_plan,
                'query': query_text
            }
        except Exception as e:
            logger.error(f"EXPLAIN query hatası: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query_text
            }
    
    def get_optimization_suggestions(self, query_id: int) -> Dict[str, Any]:
        """
        Query optimizasyon önerileri
        
        Args:
            query_id: QueryLog ID
            
        Returns:
            Dict: Optimizasyon önerileri
        """
        try:
            query_log = QueryLog.query.get(query_id)
            if not query_log:
                return {
                    'success': False,
                    'error': 'Query bulunamadı'
                }
            
            suggestions = []
            query_text = query_log.query_text.upper()
            
            # Basit optimizasyon kontrolleri
            if 'SELECT *' in query_text:
                suggestions.append({
                    'type': 'warning',
                    'title': 'SELECT * kullanımı',
                    'description': 'Sadece ihtiyacınız olan kolonları seçin',
                    'impact': 'medium'
                })
            
            if 'WHERE' not in query_text and 'SELECT' in query_text:
                suggestions.append({
                    'type': 'warning',
                    'title': 'WHERE clause eksik',
                    'description': 'Tüm satırları çekmek yerine filtreleme kullanın',
                    'impact': 'high'
                })
            
            if query_log.execution_time > 5.0:
                suggestions.append({
                    'type': 'critical',
                    'title': 'Çok yavaş query',
                    'description': 'Query 5 saniyeden uzun sürüyor. Index ekleyin veya query\'yi optimize edin',
                    'impact': 'critical'
                })
            elif query_log.execution_time > 1.0:
                suggestions.append({
                    'type': 'warning',
                    'title': 'Yavaş query',
                    'description': 'Query 1 saniyeden uzun sürüyor. Optimizasyon gerekebilir',
                    'impact': 'medium'
                })
            
            if 'JOIN' in query_text and query_log.execution_time > 1.0:
                suggestions.append({
                    'type': 'info',
                    'title': 'JOIN optimizasyonu',
                    'description': 'JOIN edilen kolonlarda index olduğundan emin olun',
                    'impact': 'medium'
                })
            
            if 'ORDER BY' in query_text and 'LIMIT' not in query_text:
                suggestions.append({
                    'type': 'info',
                    'title': 'LIMIT kullanımı',
                    'description': 'ORDER BY ile birlikte LIMIT kullanmayı düşünün',
                    'impact': 'low'
                })
            
            if not suggestions:
                suggestions.append({
                    'type': 'success',
                    'title': 'İyi performans',
                    'description': 'Query iyi performans gösteriyor',
                    'impact': 'none'
                })
            
            return {
                'success': True,
                'query_id': query_id,
                'execution_time': query_log.execution_time,
                'suggestions': suggestions,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Optimization suggestions hatası: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_query_by_id(self, query_id: int) -> Optional[Dict[str, Any]]:
        """
        ID'ye göre query detayı getir
        
        Args:
            query_id: QueryLog ID
            
        Returns:
            Dict: Query detayları
        """
        try:
            query_log = QueryLog.query.get(query_id)
            if not query_log:
                return None
            
            return {
                'id': query_log.id,
                'query_text': query_log.query_text,
                'execution_time': round(query_log.execution_time, 4),
                'timestamp': query_log.timestamp.isoformat() if query_log.timestamp else None,
                'endpoint': query_log.endpoint,
                'user_id': query_log.user_id,
                'parameters': query_log.parameters,
                'is_slow': query_log.execution_time > 1.0,
                'severity': self._get_severity(query_log.execution_time)
            }
        except Exception as e:
            logger.error(f"Get query by ID hatası: {str(e)}")
            return None
    
    def _get_severity(self, execution_time: float) -> str:
        """
        Execution time'a göre severity seviyesi
        
        Args:
            execution_time: Çalışma süresi (saniye)
            
        Returns:
            str: Severity level (low, medium, high, critical)
        """
        if execution_time >= 10.0:
            return 'critical'
        elif execution_time >= 5.0:
            return 'high'
        elif execution_time >= 1.0:
            return 'medium'
        else:
            return 'low'
    
    def cleanup_old_logs(self, days: int = 30) -> int:
        """
        Eski logları temizle
        
        Args:
            days: Kaç günden eski loglar silinsin
            
        Returns:
            int: Silinen log sayısı
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted = QueryLog.query.filter(
                QueryLog.timestamp < cutoff_date
            ).delete()
            
            self.db.session.commit()
            logger.info(f"{deleted} eski query log silindi (>{days} gün)")
            
            return deleted
        except Exception as e:
            logger.error(f"Cleanup old logs hatası: {str(e)}")
            self.db.session.rollback()
            return 0


# ============================================
# SQLAlchemy Event Listener - Otomatik Query Logging
# ============================================

from sqlalchemy import event
from sqlalchemy.engine import Engine
import time
from flask import has_request_context, request, g

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Query başlamadan önce zamanı kaydet"""
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Query bittikten sonra logla"""
    try:
        # Execution time hesapla
        total_time = time.time() - conn.info['query_start_time'].pop(-1)
        
        # Sadece yavaş query'leri logla (>0.1s) veya tüm query'leri loglamak için threshold'u kaldır
        if total_time > 0.01:  # 10ms üzeri query'leri logla
            # Flask request context varsa endpoint bilgisini al
            endpoint = None
            user_id = None
            
            if has_request_context():
                endpoint = request.endpoint
                # Session'dan user_id al (varsa)
                from flask import session
                user_id = session.get('user_id')
            
            # Query'yi connection-level operation ile logla (flush-safe)
            try:
                # Raw SQL kullan - session.add() yerine
                from models import db
                from sqlalchemy import text
                import uuid
                
                # Yeni connection al (mevcut transaction'dan bağımsız)
                with db.engine.connect() as log_conn:
                    log_conn.execute(
                        text("""
                            INSERT INTO query_logs (query_text, execution_time, endpoint, user_id, timestamp)
                            VALUES (:query_text, :execution_time, :endpoint, :user_id, NOW())
                        """),
                        {
                            'query_text': statement[:2000],
                            'execution_time': total_time,
                            'endpoint': endpoint,
                            'user_id': user_id
                        }
                    )
                    log_conn.commit()
                
            except Exception as log_error:
                # Logging hatası ana query'yi etkilememeli
                logger.debug(f"Query log hatası: {str(log_error)}")
                
    except Exception as e:
        # Event listener hatası uygulamayı çökertmemeli
        logger.debug(f"Query event listener hatası: {str(e)}")


def setup_query_logging():
    """Query logging'i aktif et"""
    logger.info("✅ SQLAlchemy query logging aktif edildi (threshold: 10ms)")


# Otomatik olarak aktif et
setup_query_logging()
