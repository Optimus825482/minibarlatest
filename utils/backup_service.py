"""
Otomatik Veritabanı Yedekleme Servisi

Bu modül veritabanı yedekleme işlemlerini yönetir:
- Otomatik günlük yedekleme (23:59)
- Manuel yedekleme
- Eski yedeklerin otomatik silinmesi (15 günden eski)
- Yedek geri yükleme
- Yedek indirme

Kullanım:
    from utils.backup_service import BackupService
    
    # Manuel yedek al
    result = BackupService.create_backup(kullanici_id=1)
    
    # Eski yedekleri temizle
    BackupService.cleanup_old_backups(days=15)
"""

import os
import subprocess
import gzip
import shutil
from datetime import datetime, timezone, timedelta
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
from pathlib import Path
import logging
import uuid

logger = logging.getLogger(__name__)

# Backup klasörü
BACKUP_DIR = Path('backups')
BACKUP_DIR.mkdir(exist_ok=True)


class BackupService:
    """Veritabanı yedekleme servisi"""
    
    @staticmethod
    def get_db_config():
        """Veritabanı bağlantı bilgilerini al"""
        from config import Config
        
        db_url = Config.SQLALCHEMY_DATABASE_URI
        
        # postgresql://user:pass@host:port/dbname formatını parse et
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', '')
        elif db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', '')
        
        # user:pass@host:port/dbname
        if '@' in db_url:
            auth, rest = db_url.split('@', 1)
            if ':' in auth:
                user, password = auth.split(':', 1)
            else:
                user, password = auth, ''
        else:
            user, password = '', ''
            rest = db_url
        
        # host:port/dbname
        if '/' in rest:
            host_port, dbname = rest.rsplit('/', 1)
        else:
            host_port, dbname = rest, ''
        
        # host:port
        if ':' in host_port:
            host, port = host_port.split(':', 1)
        else:
            host, port = host_port, '5432'
        
        # Query parametrelerini temizle
        if '?' in dbname:
            dbname = dbname.split('?')[0]
        
        return {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'dbname': dbname
        }
    
    @staticmethod
    def create_backup(kullanici_id=None, aciklama=None):
        """
        Veritabanı yedeği oluştur
        
        Args:
            kullanici_id: Yedeği oluşturan kullanıcı ID
            aciklama: Yedek açıklaması
        
        Returns:
            dict: {
                'success': bool,
                'message': str,
                'backup_id': str,
                'filename': str,
                'file_size': int
            }
        """
        try:
            from models import db, BackupHistory
            
            db_config = BackupService.get_db_config()
            
            # Benzersiz backup ID oluştur
            backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            filename = f"{backup_id}.sql.gz"
            filepath = BACKUP_DIR / filename
            temp_filepath = BACKUP_DIR / f"{backup_id}.sql"
            
            logger.info(f"Yedekleme başlatılıyor: {filename}")
            
            # pg_dump komutu
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['password']
            
            # pg_dump çalıştır
            cmd = [
                'pg_dump',
                '-h', db_config['host'],
                '-p', db_config['port'],
                '-U', db_config['user'],
                '-d', db_config['dbname'],
                '-F', 'p',  # Plain text format
                '--no-owner',
                '--no-acl',
                '-f', str(temp_filepath)
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 dakika timeout
            )
            
            if result.returncode != 0:
                logger.error(f"pg_dump hatası: {result.stderr}")
                return {
                    'success': False,
                    'message': f'Yedekleme hatası: {result.stderr}',
                    'backup_id': None,
                    'filename': None,
                    'file_size': 0
                }
            
            # Dosyayı gzip ile sıkıştır
            with open(temp_filepath, 'rb') as f_in:
                with gzip.open(filepath, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Geçici dosyayı sil
            temp_filepath.unlink()
            
            # Dosya boyutunu al
            file_size = filepath.stat().st_size
            
            # Veritabanına kaydet
            backup_record = BackupHistory(
                backup_id=backup_id,
                filename=filename,
                file_size=file_size,
                description=aciklama or f"Otomatik yedek - {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                created_by=kullanici_id,
                status='completed'
            )
            db.session.add(backup_record)
            db.session.commit()
            
            logger.info(f"✅ Yedekleme tamamlandı: {filename} ({file_size / 1024 / 1024:.2f} MB)")
            
            return {
                'success': True,
                'message': 'Yedekleme başarıyla tamamlandı',
                'backup_id': backup_id,
                'filename': filename,
                'file_size': file_size
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Yedekleme zaman aşımına uğradı")
            return {
                'success': False,
                'message': 'Yedekleme zaman aşımına uğradı (10 dakika)',
                'backup_id': None,
                'filename': None,
                'file_size': 0
            }
        except Exception as e:
            logger.error(f"Yedekleme hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Yedekleme hatası: {str(e)}',
                'backup_id': None,
                'filename': None,
                'file_size': 0
            }

    @staticmethod
    def cleanup_old_backups(days=15):
        """
        Belirtilen günden eski yedekleri sil
        
        Args:
            days: Kaç günden eski yedekler silinecek (varsayılan: 15)
        
        Returns:
            dict: {
                'success': bool,
                'deleted_count': int,
                'deleted_files': list,
                'freed_space': int
            }
        """
        try:
            from models import db, BackupHistory
            
            cutoff_date = get_kktc_now() - timedelta(days=days)
            
            # Eski yedekleri bul
            old_backups = BackupHistory.query.filter(
                BackupHistory.created_at < cutoff_date
            ).all()
            
            deleted_files = []
            freed_space = 0
            
            for backup in old_backups:
                filepath = BACKUP_DIR / backup.filename
                
                # Dosyayı sil
                if filepath.exists():
                    file_size = filepath.stat().st_size
                    filepath.unlink()
                    freed_space += file_size
                    deleted_files.append(backup.filename)
                    logger.info(f"Eski yedek silindi: {backup.filename}")
                
                # Veritabanı kaydını sil
                db.session.delete(backup)
            
            db.session.commit()
            
            logger.info(f"✅ {len(deleted_files)} eski yedek silindi, {freed_space / 1024 / 1024:.2f} MB alan boşaltıldı")
            
            return {
                'success': True,
                'deleted_count': len(deleted_files),
                'deleted_files': deleted_files,
                'freed_space': freed_space
            }
            
        except Exception as e:
            logger.error(f"Eski yedek temizleme hatası: {str(e)}")
            return {
                'success': False,
                'deleted_count': 0,
                'deleted_files': [],
                'freed_space': 0
            }
    
    @staticmethod
    def restore_backup(backup_id, kullanici_id=None):
        """
        Yedeği geri yükle
        
        Args:
            backup_id: Yedek ID
            kullanici_id: İşlemi yapan kullanıcı ID
        
        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        try:
            from models import db, BackupHistory
            
            # Yedek kaydını bul
            backup = BackupHistory.query.filter_by(backup_id=backup_id).first()
            if not backup:
                return {'success': False, 'message': 'Yedek bulunamadı'}
            
            filepath = BACKUP_DIR / backup.filename
            if not filepath.exists():
                return {'success': False, 'message': 'Yedek dosyası bulunamadı'}
            
            db_config = BackupService.get_db_config()
            
            # Geçici SQL dosyası oluştur
            temp_filepath = BACKUP_DIR / f"restore_{backup_id}.sql"
            
            # Gzip dosyasını aç
            with gzip.open(filepath, 'rb') as f_in:
                with open(temp_filepath, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            logger.info(f"Yedek geri yükleniyor: {backup.filename}")
            
            # psql ile geri yükle
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['password']
            
            cmd = [
                'psql',
                '-h', db_config['host'],
                '-p', db_config['port'],
                '-U', db_config['user'],
                '-d', db_config['dbname'],
                '-f', str(temp_filepath)
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=1800  # 30 dakika timeout
            )
            
            # Geçici dosyayı sil
            temp_filepath.unlink()
            
            if result.returncode != 0:
                logger.error(f"Geri yükleme hatası: {result.stderr}")
                return {
                    'success': False,
                    'message': f'Geri yükleme hatası: {result.stderr}'
                }
            
            # Restore sayısını artır
            backup.restore_count += 1
            db.session.commit()
            
            logger.info(f"✅ Yedek geri yüklendi: {backup.filename}")
            
            return {
                'success': True,
                'message': 'Yedek başarıyla geri yüklendi'
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'message': 'Geri yükleme zaman aşımına uğradı (30 dakika)'
            }
        except Exception as e:
            logger.error(f"Geri yükleme hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Geri yükleme hatası: {str(e)}'
            }
    
    @staticmethod
    def get_backup_list():
        """
        Yedek listesini getir
        
        Returns:
            list: Yedek kayıtları listesi
        """
        try:
            from models import BackupHistory
            
            backups = BackupHistory.query.order_by(
                BackupHistory.created_at.desc()
            ).all()
            
            result = []
            for backup in backups:
                filepath = BACKUP_DIR / backup.filename
                exists = filepath.exists()
                
                result.append({
                    'backup_id': backup.backup_id,
                    'filename': backup.filename,
                    'file_size': backup.file_size,
                    'file_size_mb': round(backup.file_size / 1024 / 1024, 2) if backup.file_size else 0,
                    'description': backup.description,
                    'created_at': backup.created_at,
                    'created_by': backup.creator.ad + ' ' + backup.creator.soyad if backup.creator else 'Sistem',
                    'status': backup.status,
                    'restore_count': backup.restore_count,
                    'file_exists': exists
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Yedek listesi hatası: {str(e)}")
            return []
    
    @staticmethod
    def get_backup_settings():
        """
        Yedekleme ayarlarını getir
        
        Returns:
            dict: Yedekleme ayarları
        """
        try:
            from models import SistemAyar
            
            ayarlar = {
                'otomatik_yedekleme': True,
                'yedekleme_saati': '23:59',
                'saklama_suresi': 15,
                'son_yedekleme': None
            }
            
            # Veritabanından ayarları al
            for key in ayarlar.keys():
                ayar = SistemAyar.query.filter_by(anahtar=f'backup_{key}').first()
                if ayar:
                    if key == 'otomatik_yedekleme':
                        ayarlar[key] = ayar.deger == 'true'
                    elif key == 'saklama_suresi':
                        ayarlar[key] = int(ayar.deger)
                    else:
                        ayarlar[key] = ayar.deger
            
            return ayarlar
            
        except Exception as e:
            logger.error(f"Yedekleme ayarları hatası: {str(e)}")
            return {
                'otomatik_yedekleme': True,
                'yedekleme_saati': '23:59',
                'saklama_suresi': 15,
                'son_yedekleme': None
            }
    
    @staticmethod
    def save_backup_settings(otomatik_yedekleme=True, yedekleme_saati='23:59', saklama_suresi=15):
        """
        Yedekleme ayarlarını kaydet
        
        Args:
            otomatik_yedekleme: Otomatik yedekleme aktif mi
            yedekleme_saati: Yedekleme saati (HH:MM)
            saklama_suresi: Yedek saklama süresi (gün)
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            from models import db, SistemAyar
            
            ayarlar = {
                'backup_otomatik_yedekleme': 'true' if otomatik_yedekleme else 'false',
                'backup_yedekleme_saati': yedekleme_saati,
                'backup_saklama_suresi': str(saklama_suresi)
            }
            
            for anahtar, deger in ayarlar.items():
                ayar = SistemAyar.query.filter_by(anahtar=anahtar).first()
                if ayar:
                    ayar.deger = deger
                else:
                    ayar = SistemAyar(anahtar=anahtar, deger=deger)
                    db.session.add(ayar)
            
            db.session.commit()
            
            logger.info(f"✅ Yedekleme ayarları güncellendi")
            
            return {'success': True, 'message': 'Ayarlar kaydedildi'}
            
        except Exception as e:
            logger.error(f"Yedekleme ayarları kaydetme hatası: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_backup_stats():
        """
        Yedekleme istatistiklerini getir
        
        Returns:
            dict: İstatistikler
        """
        try:
            from models import BackupHistory
            
            total_backups = BackupHistory.query.count()
            total_size = sum([b.file_size or 0 for b in BackupHistory.query.all()])
            
            # Son yedek
            last_backup = BackupHistory.query.order_by(
                BackupHistory.created_at.desc()
            ).first()
            
            return {
                'total_backups': total_backups,
                'total_size': total_size,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'last_backup': last_backup.created_at if last_backup else None,
                'last_backup_filename': last_backup.filename if last_backup else None
            }
            
        except Exception as e:
            logger.error(f"Yedekleme istatistikleri hatası: {str(e)}")
            return {
                'total_backups': 0,
                'total_size': 0,
                'total_size_mb': 0,
                'last_backup': None,
                'last_backup_filename': None
            }

