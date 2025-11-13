"""
Job Monitor - Background Job Tracking
Developer Dashboard için background job izleme servisi
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from models import db, BackgroundJob
import uuid

logger = logging.getLogger(__name__)


class JobMonitor:
    """Background job izleme servisi"""
    
    def __init__(self):
        """Initialize job monitor"""
        self.db = db
    
    def create_job(
        self,
        job_name: str,
        metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Yeni job oluştur
        
        Args:
            job_name: Job adı
            metadata: Ek metadata
            
        Returns:
            str: Job ID
        """
        try:
            job_id = str(uuid.uuid4())
            
            job = BackgroundJob(
                job_id=job_id,
                job_name=job_name,
                status='pending',
                job_metadata=metadata or {}
            )
            
            self.db.session.add(job)
            self.db.session.commit()
            
            logger.info(f"Job oluşturuldu: {job_name} ({job_id})")
            return job_id
        except Exception as e:
            logger.error(f"Create job hatası: {str(e)}")
            self.db.session.rollback()
            return None
    
    def start_job(self, job_id: str) -> bool:
        """
        Job'ı başlat
        
        Args:
            job_id: Job ID
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            job = BackgroundJob.query.filter_by(job_id=job_id).first()
            if not job:
                return False
            
            job.status = 'running'
            job.started_at = datetime.utcnow()
            
            self.db.session.commit()
            logger.info(f"Job başlatıldı: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Start job hatası: {str(e)}")
            self.db.session.rollback()
            return False
    
    def complete_job(
        self,
        job_id: str,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None
    ) -> bool:
        """
        Job'ı tamamla
        
        Args:
            job_id: Job ID
            error_message: Hata mesajı (başarısızsa)
            stack_trace: Stack trace (başarısızsa)
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            job = BackgroundJob.query.filter_by(job_id=job_id).first()
            if not job:
                return False
            
            job.completed_at = datetime.utcnow()
            
            if error_message:
                job.status = 'failed'
                job.error_message = error_message
                job.stack_trace = stack_trace
            else:
                job.status = 'completed'
            
            # Duration hesapla
            if job.started_at:
                duration = (job.completed_at - job.started_at).total_seconds()
                job.duration = duration
            
            self.db.session.commit()
            logger.info(f"Job tamamlandı: {job_id} ({job.status})")
            return True
        except Exception as e:
            logger.error(f"Complete job hatası: {str(e)}")
            self.db.session.rollback()
            return False
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Job'ı iptal et
        
        Args:
            job_id: Job ID
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            job = BackgroundJob.query.filter_by(job_id=job_id).first()
            if not job:
                return False
            
            job.status = 'cancelled'
            job.completed_at = datetime.utcnow()
            
            if job.started_at:
                duration = (job.completed_at - job.started_at).total_seconds()
                job.duration = duration
            
            self.db.session.commit()
            logger.info(f"Job iptal edildi: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Cancel job hatası: {str(e)}")
            self.db.session.rollback()
            return False
    
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """
        Aktif job'ları getir
        
        Returns:
            List[Dict]: Aktif job listesi
        """
        try:
            jobs = BackgroundJob.query.filter_by(status='running').order_by(
                BackgroundJob.started_at.desc()
            ).all()
            
            return [self._job_to_dict(job) for job in jobs]
        except Exception as e:
            logger.error(f"Get active jobs hatası: {str(e)}")
            return []
    
    def get_pending_jobs(self) -> List[Dict[str, Any]]:
        """
        Bekleyen job'ları getir
        
        Returns:
            List[Dict]: Bekleyen job listesi
        """
        try:
            jobs = BackgroundJob.query.filter_by(status='pending').order_by(
                BackgroundJob.created_at.desc()
            ).all()
            
            return [self._job_to_dict(job) for job in jobs]
        except Exception as e:
            logger.error(f"Get pending jobs hatası: {str(e)}")
            return []
    
    def get_completed_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Tamamlanan job'ları getir
        
        Args:
            limit: Maksimum job sayısı
            
        Returns:
            List[Dict]: Tamamlanan job listesi
        """
        try:
            jobs = BackgroundJob.query.filter_by(status='completed').order_by(
                BackgroundJob.completed_at.desc()
            ).limit(limit).all()
            
            return [self._job_to_dict(job) for job in jobs]
        except Exception as e:
            logger.error(f"Get completed jobs hatası: {str(e)}")
            return []
    
    def get_failed_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Başarısız job'ları getir
        
        Args:
            limit: Maksimum job sayısı
            
        Returns:
            List[Dict]: Başarısız job listesi
        """
        try:
            jobs = BackgroundJob.query.filter_by(status='failed').order_by(
                BackgroundJob.completed_at.desc()
            ).limit(limit).all()
            
            return [self._job_to_dict(job) for job in jobs]
        except Exception as e:
            logger.error(f"Get failed jobs hatası: {str(e)}")
            return []
    
    def get_job_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Job detaylarını getir
        
        Args:
            job_id: Job ID
            
        Returns:
            Dict: Job detayları
        """
        try:
            job = BackgroundJob.query.filter_by(job_id=job_id).first()
            if not job:
                return None
            
            return self._job_to_dict(job, include_details=True)
        except Exception as e:
            logger.error(f"Get job details hatası: {str(e)}")
            return None
    
    def retry_job(self, job_id: str) -> Optional[str]:
        """
        Başarısız job'ı yeniden çalıştır
        
        Args:
            job_id: Job ID
            
        Returns:
            str: Yeni job ID
        """
        try:
            old_job = BackgroundJob.query.filter_by(job_id=job_id).first()
            if not old_job or old_job.status != 'failed':
                return None
            
            # Yeni job oluştur
            new_job_id = self.create_job(
                job_name=old_job.job_name,
                metadata=old_job.job_metadata
            )
            
            logger.info(f"Job retry edildi: {job_id} -> {new_job_id}")
            return new_job_id
        except Exception as e:
            logger.error(f"Retry job hatası: {str(e)}")
            return None
    
    def get_job_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Job istatistiklerini getir
        
        Args:
            hours: Son kaç saat
            
        Returns:
            Dict: İstatistikler
        """
        try:
            since = datetime.utcnow() - timedelta(hours=hours)
            
            # Toplam job sayısı
            total_jobs = BackgroundJob.query.filter(
                BackgroundJob.created_at >= since
            ).count()
            
            # Status bazlı sayılar
            completed = BackgroundJob.query.filter(
                BackgroundJob.created_at >= since,
                BackgroundJob.status == 'completed'
            ).count()
            
            failed = BackgroundJob.query.filter(
                BackgroundJob.created_at >= since,
                BackgroundJob.status == 'failed'
            ).count()
            
            running = BackgroundJob.query.filter_by(status='running').count()
            pending = BackgroundJob.query.filter_by(status='pending').count()
            
            # Başarı oranı
            success_rate = (completed / total_jobs * 100) if total_jobs > 0 else 0
            
            # Ortalama duration
            from sqlalchemy import func
            avg_duration = self.db.session.query(
                func.avg(BackgroundJob.duration)
            ).filter(
                BackgroundJob.created_at >= since,
                BackgroundJob.duration.isnot(None)
            ).scalar() or 0
            
            # En uzun job
            longest_job = BackgroundJob.query.filter(
                BackgroundJob.created_at >= since,
                BackgroundJob.duration.isnot(None)
            ).order_by(
                BackgroundJob.duration.desc()
            ).first()
            
            return {
                'total_jobs': total_jobs,
                'completed': completed,
                'failed': failed,
                'running': running,
                'pending': pending,
                'success_rate': round(success_rate, 2),
                'avg_duration': round(avg_duration, 2),
                'longest_duration': round(longest_job.duration, 2) if longest_job else 0,
                'longest_job_name': longest_job.job_name if longest_job else None,
                'period_hours': hours,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Get job stats hatası: {str(e)}")
            return {
                'total_jobs': 0,
                'error': str(e)
            }
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Eski job kayıtlarını temizle
        
        Args:
            days: Kaç günden eski job'lar silinsin
            
        Returns:
            int: Silinen job sayısı
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted = BackgroundJob.query.filter(
                BackgroundJob.created_at < cutoff_date,
                BackgroundJob.status.in_(['completed', 'failed', 'cancelled'])
            ).delete()
            
            self.db.session.commit()
            logger.info(f"{deleted} eski job kaydı silindi (>{days} gün)")
            
            return deleted
        except Exception as e:
            logger.error(f"Cleanup old jobs hatası: {str(e)}")
            self.db.session.rollback()
            return 0
    
    def _job_to_dict(self, job: BackgroundJob, include_details: bool = False) -> Dict[str, Any]:
        """
        Job modelini dict'e çevir
        
        Args:
            job: BackgroundJob instance
            include_details: Detaylı bilgi dahil edilsin mi
            
        Returns:
            Dict: Job bilgileri
        """
        data = {
            'job_id': job.job_id,
            'job_name': job.job_name,
            'status': job.status,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'duration': round(job.duration, 2) if job.duration else None
        }
        
        if include_details:
            data.update({
                'error_message': job.error_message,
                'stack_trace': job.stack_trace,
                'metadata': job.job_metadata
            })
        
        return data
