"""
Backup Manager - Database Backup and Restore
Developer Dashboard için database backup/restore servisi
"""
import logging
import os
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from models import db, BackupHistory

logger = logging.getLogger(__name__)


class BackupManager:
    """Database backup/restore yönetim servisi"""
    
    def __init__(self):
        """Initialize backup manager"""
        self.db = db
        self.backup_dir = 'backups'
        
        # Backup klasörünü oluştur
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
    
    def create_backup(
        self,
        description: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Database backup oluştur
        
        Args:
            description: Backup açıklaması
            created_by: Oluşturan kullanıcı ID
            
        Returns:
            Dict: Backup bilgileri
        """
        backup_history = None
        try:
            backup_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"backup_{timestamp}_{backup_id[:8]}.sql"
            filepath = os.path.join(self.backup_dir, filename)
            
            # Database bilgilerini al
            db_url = self.db.engine.url
            
            # Backup history kaydı oluştur (yeni session)
            backup_history = BackupHistory(
                backup_id=backup_id,
                filename=filename,
                description=description,
                created_by=created_by,
                status='in_progress'
            )
            self.db.session.add(backup_history)
            self.db.session.flush()  # ID'yi al ama commit etme
            history_id = backup_history.id
            self.db.session.commit()
            
            # PostgreSQL backup komutu
            cmd = [
                'pg_dump',
                '-h', str(db_url.host),
                '-p', str(db_url.port or 5432),
                '-U', str(db_url.username),
                '-d', str(db_url.database),
                '-f', filepath,
                '--no-password'
            ]
            
            # PGPASSWORD environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = str(db_url.password)
            
            # Backup çalıştır
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 dakika timeout
            )
            
            if result.returncode != 0:
                # Hata
                backup_history.status = 'failed'
                self.db.session.commit()
                
                logger.error(f"Backup hatası: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr
                }
            
            # Başarılı
            file_size = os.path.getsize(filepath)
            backup_history.file_size = file_size
            backup_history.status = 'completed'
            self.db.session.commit()
            
            logger.info(f"Backup oluşturuldu: {filename} ({file_size} bytes)")
            
            return {
                'success': True,
                'backup_id': backup_id,
                'filename': filename,
                'file_size': file_size,
                'filepath': filepath
            }
        except Exception as e:
            logger.error(f"Create backup hatası: {str(e)}")
            
            # Backup history'yi güncelle
            try:
                if backup_history and backup_history.id:
                    backup_history.status = 'failed'
                    self.db.session.commit()
                else:
                    self.db.session.rollback()
            except Exception as rollback_error:
                logger.error(f"Rollback hatası: {str(rollback_error)}")
                try:
                    self.db.session.rollback()
                except:
                    pass
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Backup listesini getir
        
        Returns:
            List[Dict]: Backup listesi
        """
        try:
            backups = BackupHistory.query.order_by(
                BackupHistory.created_at.desc()
            ).all()
            
            return [
                {
                    'id': backup.id,
                    'backup_id': backup.backup_id,
                    'filename': backup.filename,
                    'file_size': backup.file_size,
                    'file_size_mb': round(backup.file_size / (1024 * 1024), 2) if backup.file_size else 0,
                    'description': backup.description,
                    'created_at': backup.created_at.isoformat() if backup.created_at else None,
                    'created_by': backup.created_by,
                    'status': backup.status,
                    'restore_count': backup.restore_count
                }
                for backup in backups
            ]
        except Exception as e:
            logger.error(f"List backups hatası: {str(e)}")
            return []
    
    def get_backup_details(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Backup detaylarını getir
        
        Args:
            backup_id: Backup ID
            
        Returns:
            Dict: Backup detayları
        """
        try:
            backup = BackupHistory.query.filter_by(backup_id=backup_id).first()
            if not backup:
                return None
            
            filepath = os.path.join(self.backup_dir, backup.filename)
            file_exists = os.path.exists(filepath)
            
            return {
                'id': backup.id,
                'backup_id': backup.backup_id,
                'filename': backup.filename,
                'file_size': backup.file_size,
                'file_size_mb': round(backup.file_size / (1024 * 1024), 2) if backup.file_size else 0,
                'description': backup.description,
                'created_at': backup.created_at.isoformat() if backup.created_at else None,
                'created_by': backup.created_by,
                'status': backup.status,
                'restore_count': backup.restore_count,
                'file_exists': file_exists,
                'filepath': filepath if file_exists else None
            }
        except Exception as e:
            logger.error(f"Get backup details hatası: {str(e)}")
            return None
    
    def restore_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Backup'tan restore et
        
        Args:
            backup_id: Backup ID
            
        Returns:
            Dict: Restore sonucu
        """
        try:
            backup = BackupHistory.query.filter_by(backup_id=backup_id).first()
            if not backup:
                return {
                    'success': False,
                    'error': 'Backup bulunamadı'
                }
            
            filepath = os.path.join(self.backup_dir, backup.filename)
            if not os.path.exists(filepath):
                return {
                    'success': False,
                    'error': 'Backup dosyası bulunamadı'
                }
            
            # Database bilgilerini al
            db_url = self.db.engine.url
            
            # PostgreSQL restore komutu
            cmd = [
                'psql',
                '-h', str(db_url.host),
                '-p', str(db_url.port or 5432),
                '-U', str(db_url.username),
                '-d', str(db_url.database),
                '-f', filepath,
                '--no-password'
            ]
            
            # PGPASSWORD environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = str(db_url.password)
            
            # Restore çalıştır
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 dakika timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Restore hatası: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr
                }
            
            # Restore count'u artır
            backup.restore_count += 1
            self.db.session.commit()
            
            logger.info(f"Backup restore edildi: {backup.filename}")
            
            return {
                'success': True,
                'message': 'Backup başarıyla restore edildi',
                'backup_id': backup_id
            }
        except Exception as e:
            logger.error(f"Restore backup hatası: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_backup(self, backup_id: str) -> bool:
        """
        Backup'ı sil
        
        Args:
            backup_id: Backup ID
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            backup = BackupHistory.query.filter_by(backup_id=backup_id).first()
            if not backup:
                return False
            
            # Dosyayı sil
            filepath = os.path.join(self.backup_dir, backup.filename)
            if os.path.exists(filepath):
                os.remove(filepath)
            
            # Database kaydını sil
            self.db.session.delete(backup)
            self.db.session.commit()
            
            logger.info(f"Backup silindi: {backup.filename}")
            return True
        except Exception as e:
            logger.error(f"Delete backup hatası: {str(e)}")
            self.db.session.rollback()
            return False
