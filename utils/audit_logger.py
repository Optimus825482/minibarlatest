"""
Audit Logger
Kritik işlemleri ve güvenlik olaylarını loglama
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
from flask import request, g
from models import db

logger = logging.getLogger(__name__)


class AuditLogger:
    """Audit logging servisi"""
    
    # Audit event tipleri
    EVENT_TYPES = {
        'LOGIN': 'User Login',
        'LOGOUT': 'User Logout',
        'LOGIN_FAILED': 'Failed Login Attempt',
        'CONFIG_CHANGE': 'Configuration Changed',
        'BACKUP_CREATE': 'Backup Created',
        'BACKUP_RESTORE': 'Backup Restored',
        'BACKUP_DELETE': 'Backup Deleted',
        'CACHE_CLEAR': 'Cache Cleared',
        'QUERY_EXECUTE': 'Query Executed',
        'JOB_START': 'Job Started',
        'JOB_CANCEL': 'Job Cancelled',
        'PROFILER_START': 'Profiler Started',
        'PROFILER_STOP': 'Profiler Stopped',
        'SECURITY_ALERT': 'Security Alert',
        'RATE_LIMIT': 'Rate Limit Exceeded',
        'SQL_INJECTION': 'SQL Injection Attempt',
        'XSS_ATTEMPT': 'XSS Attempt',
        'UNAUTHORIZED_ACCESS': 'Unauthorized Access Attempt'
    }
    
    @staticmethod
    def log_event(
        event_type: str,
        description: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        severity: str = 'INFO'
    ):
        """
        Audit event logla
        
        Args:
            event_type: Event tipi (EVENT_TYPES'dan)
            description: Event açıklaması
            user_id: Kullanıcı ID
            ip_address: IP adresi
            metadata: Ek bilgiler
            severity: Önem seviyesi (INFO, WARNING, ERROR, CRITICAL)
        """
        try:
            # User bilgisi
            if user_id is None and hasattr(g, 'user'):
                user_id = g.user.id if g.user else None
            
            # IP adresi
            if ip_address is None and request:
                ip_address = request.remote_addr
            
            # Audit log oluştur
            audit_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'event_name': AuditLogger.EVENT_TYPES.get(event_type, event_type),
                'description': description,
                'user_id': user_id,
                'ip_address': ip_address,
                'user_agent': request.user_agent.string if request else None,
                'endpoint': request.endpoint if request else None,
                'method': request.method if request else None,
                'severity': severity,
                'metadata': metadata or {}
            }
            
            # Log dosyasına yaz
            audit_log_file = 'logs/audit.log'
            try:
                import os
                os.makedirs('logs', exist_ok=True)
                with open(audit_log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(audit_entry) + '\n')
            except Exception as e:
                logger.error(f"Audit log dosyasına yazılamadı: {str(e)}")
            
            # Logger'a da yaz
            log_message = f"[AUDIT] {event_type}: {description} (User: {user_id}, IP: {ip_address})"
            
            if severity == 'CRITICAL':
                logger.critical(log_message)
            elif severity == 'ERROR':
                logger.error(log_message)
            elif severity == 'WARNING':
                logger.warning(log_message)
            else:
                logger.info(log_message)
            
            # Database'e kaydet (opsiyonel)
            # TODO: AuditLog model'i varsa buraya ekle
            
        except Exception as e:
            logger.error(f"Audit logging hatası: {str(e)}", exc_info=True)
    
    @staticmethod
    def log_security_event(
        event_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Güvenlik olayını logla
        
        Args:
            event_type: Event tipi
            description: Açıklama
            metadata: Ek bilgiler
        """
        AuditLogger.log_event(
            event_type=event_type,
            description=description,
            metadata=metadata,
            severity='WARNING'
        )
    
    @staticmethod
    def log_critical_event(
        event_type: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Kritik olayı logla
        
        Args:
            event_type: Event tipi
            description: Açıklama
            metadata: Ek bilgiler
        """
        AuditLogger.log_event(
            event_type=event_type,
            description=description,
            metadata=metadata,
            severity='CRITICAL'
        )
    
    @staticmethod
    def get_recent_events(limit: int = 100, event_type: Optional[str] = None) -> list:
        """
        Son audit event'leri getir
        
        Args:
            limit: Maksimum kayıt sayısı
            event_type: Filtrelenecek event tipi
            
        Returns:
            list: Audit event'leri
        """
        try:
            events = []
            audit_log_file = 'logs/audit.log'
            
            import os
            if not os.path.exists(audit_log_file):
                return []
            
            with open(audit_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                # Son N satırı al
                for line in lines[-limit:]:
                    try:
                        event = json.loads(line.strip())
                        
                        # Event type filtresi
                        if event_type and event.get('event_type') != event_type:
                            continue
                        
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
            
            # Ters çevir (en yeni önce)
            events.reverse()
            return events
            
        except Exception as e:
            logger.error(f"Audit events getirme hatası: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def get_user_activity(user_id: int, limit: int = 50) -> list:
        """
        Kullanıcı aktivitelerini getir
        
        Args:
            user_id: Kullanıcı ID
            limit: Maksimum kayıt sayısı
            
        Returns:
            list: Kullanıcı aktiviteleri
        """
        try:
            all_events = AuditLogger.get_recent_events(limit=limit * 2)
            user_events = [
                event for event in all_events
                if event.get('user_id') == user_id
            ]
            return user_events[:limit]
            
        except Exception as e:
            logger.error(f"User activity getirme hatası: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def get_security_events(limit: int = 100) -> list:
        """
        Güvenlik olaylarını getir
        
        Args:
            limit: Maksimum kayıt sayısı
            
        Returns:
            list: Güvenlik olayları
        """
        try:
            all_events = AuditLogger.get_recent_events(limit=limit * 2)
            security_events = [
                event for event in all_events
                if event.get('event_type') in [
                    'SECURITY_ALERT', 'RATE_LIMIT', 'SQL_INJECTION',
                    'XSS_ATTEMPT', 'UNAUTHORIZED_ACCESS', 'LOGIN_FAILED'
                ]
            ]
            return security_events[:limit]
            
        except Exception as e:
            logger.error(f"Security events getirme hatası: {str(e)}", exc_info=True)
            return []


def audit_log(event_type: str, description: str = None):
    """
    Audit logging decorator
    
    Args:
        event_type: Event tipi
        description: Açıklama (opsiyonel)
        
    Usage:
        @audit_log('CONFIG_CHANGE', 'Config file updated')
        def update_config():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Fonksiyonu çalıştır
                result = f(*args, **kwargs)
                
                # Başarılı ise logla
                desc = description or f"Function {f.__name__} executed"
                AuditLogger.log_event(
                    event_type=event_type,
                    description=desc,
                    metadata={'function': f.__name__}
                )
                
                return result
                
            except Exception as e:
                # Hata durumunda da logla
                desc = description or f"Function {f.__name__} failed"
                AuditLogger.log_event(
                    event_type=event_type,
                    description=f"{desc}: {str(e)}",
                    metadata={'function': f.__name__, 'error': str(e)},
                    severity='ERROR'
                )
                raise
        
        return decorated_function
    return decorator


# Global audit logger
_audit_logger = AuditLogger()


def get_audit_logger() -> AuditLogger:
    """
    Global audit logger instance'ını getir
    
    Returns:
        AuditLogger: Audit logger instance
    """
    return _audit_logger
