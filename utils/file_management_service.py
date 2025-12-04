"""
Dosya Yönetim Servisi
Excel dosyalarının yüklenmesi, silinmesi ve temizlenmesi işlemlerini yönetir
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
from typing import Tuple, Dict
from werkzeug.utils import secure_filename
from models import db, DosyaYukleme, MisafirKayit
from sqlalchemy import and_
from utils.audit import log_audit


class FileManagementService:
    """Dosya yönetimi servisi sınıfı"""
    
    # Konfigürasyon
    UPLOAD_FOLDER = 'uploads/doluluk/'
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'xlsm'}
    FILE_RETENTION_DAYS = 4
    
    @staticmethod
    def save_uploaded_file(file, user_id, otel_id=None):
        """
        Yüklenen dosyayı kaydeder
        
        Args:
            file: Werkzeug FileStorage objesi
            user_id: Yükleyen kullanıcı ID
            otel_id: Otel ID (hangi otele ait olduğu)
            
        Returns:
            tuple: (success, file_path, islem_kodu, error_message)
        """
        try:
            # Dosya var mı kontrol et
            if not file or file.filename == '':
                return False, None, None, 'Dosya seçilmedi'
            
            # Dosya uzantısı kontrolü
            if not FileManagementService._allowed_file(file.filename):
                return False, None, None, 'Geçersiz dosya formatı. Sadece .xlsx, .xls ve .xlsm dosyaları kabul edilir'
            
            # Dosya boyutu kontrolü (stream'den okumadan önce)
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  # Başa dön
            
            if file_size > FileManagementService.MAX_FILE_SIZE:
                size_mb = file_size / (1024 * 1024)
                return False, None, None, f'Dosya çok büyük ({size_mb:.1f} MB). Maksimum 10 MB'
            
            # Upload klasörünü oluştur
            FileManagementService._ensure_upload_folder()
            
            # Benzersiz işlem kodu oluştur
            islem_kodu = FileManagementService.generate_islem_kodu()
            
            # Güvenli dosya adı oluştur
            original_filename = secure_filename(file.filename)
            file_extension = original_filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{islem_kodu}.{file_extension}"
            
            # Dosya yolu
            file_path = os.path.join(FileManagementService.UPLOAD_FOLDER, unique_filename)
            
            # Dosyayı kaydet
            file.save(file_path)
            
            # Veritabanı kaydı oluştur
            dosya_yukleme = DosyaYukleme(
                islem_kodu=islem_kodu,
                dosya_adi=original_filename,
                dosya_yolu=file_path,
                dosya_tipi='in_house',  # Başlangıçta varsayılan, sonra güncellenecek
                dosya_boyutu=file_size,
                yukleme_tarihi=get_kktc_now(),
                durum='yuklendi',
                yuklenen_kullanici_id=user_id,
                otel_id=otel_id  # Otel ID eklendi
            )
            
            db.session.add(dosya_yukleme)
            db.session.commit()
            
            return True, file_path, islem_kodu, None
            
        except Exception as e:
            db.session.rollback()
            return False, None, None, f'Dosya kaydetme hatası: {str(e)}'
    
    @staticmethod
    def delete_upload_by_islem_kodu(islem_kodu: str, user_id: int = None) -> Tuple[bool, str, Dict]:
        """
        İşlem koduna göre yüklemeyi ve ilgili kayıtları siler.
        Tamamlanmış görevleri korur, bekleyen görevleri siler.
        
        Args:
            islem_kodu: İşlem kodu
            user_id: Silme işlemini yapan kullanıcı ID (audit için)
            
        Returns:
            Tuple[bool, str, Dict]: (success, message, summary)
            summary: {
                'deleted_misafir_kayit': int,
                'deleted_pending_tasks': int,
                'preserved_completed_tasks': int,
                'deleted_empty_gorevler': int
            }
        """
        # Boş özet
        empty_summary = {
            'deleted_misafir_kayit': 0,
            'deleted_pending_tasks': 0,
            'preserved_completed_tasks': 0,
            'deleted_empty_gorevler': 0
        }
        
        try:
            # Dosya yükleme kaydını bul
            dosya_yukleme = DosyaYukleme.query.filter_by(islem_kodu=islem_kodu).first()
            
            if not dosya_yukleme:
                return False, 'İşlem kodu bulunamadı', empty_summary
            
            # Audit log için dosya bilgilerini sakla (silmeden önce)
            dosya_adi = dosya_yukleme.dosya_adi
            dosya_tipi = dosya_yukleme.dosya_tipi
            dosya_yolu = dosya_yukleme.dosya_yolu
            
            # İlgili MisafirKayit ID'lerini topla (silmeden önce)
            misafir_kayitlar = MisafirKayit.query.filter_by(islem_kodu=islem_kodu).all()
            misafir_kayit_ids = [mk.id for mk in misafir_kayitlar]
            
            # Özet bilgilerini hazırla
            summary = {
                'deleted_misafir_kayit': len(misafir_kayit_ids),
                'deleted_pending_tasks': 0,
                'preserved_completed_tasks': 0,
                'deleted_empty_gorevler': 0
            }
            
            # Görev yönetimini çağır (MisafirKayit silinmeden önce)
            if misafir_kayit_ids:
                from utils.gorev_service import GorevService
                gorev_result = GorevService.handle_misafir_kayit_deletion(misafir_kayit_ids)
                
                summary['deleted_pending_tasks'] = gorev_result.get('deleted_pending', 0)
                summary['preserved_completed_tasks'] = gorev_result.get('nullified_completed', 0)
                summary['deleted_empty_gorevler'] = gorev_result.get('deleted_empty_gorevler', 0)
            
            # MisafirKayit kayıtlarını sil
            for mk in misafir_kayitlar:
                db.session.delete(mk)
            
            # YuklemeGorev tablosunu güncelle (dashboard senkronizasyonu için)
            try:
                from models import YuklemeGorev
                from datetime import date
                
                # Dosya tipini YuklemeGorev formatına çevir
                dosya_tipi_map = {
                    'in_house': 'inhouse',
                    'arrivals': 'arrivals', 
                    'departures': 'departures'
                }
                yukleme_dosya_tipi = dosya_tipi_map.get(dosya_tipi, dosya_tipi)
                
                # İlgili yükleme görevini bul ve pending'e çevir
                yukleme_gorev = YuklemeGorev.query.filter(
                    YuklemeGorev.dosya_yukleme_id == dosya_yukleme.id
                ).first()
                
                if yukleme_gorev:
                    yukleme_gorev.durum = 'pending'
                    yukleme_gorev.yukleme_zamani = None
                    yukleme_gorev.dosya_yukleme_id = None
                    summary['reset_yukleme_gorev'] = 1
            except Exception as yg_err:
                print(f"YuklemeGorev güncelleme hatası: {yg_err}")
            
            # Fiziksel dosyayı sil
            if os.path.exists(dosya_yukleme.dosya_yolu):
                try:
                    os.remove(dosya_yukleme.dosya_yolu)
                except Exception as e:
                    # Dosya silme hatası kritik değil, log'la ve devam et
                    print(f"Dosya silme hatası: {str(e)}")
            
            # Dosya yükleme kaydını tamamen sil
            db.session.delete(dosya_yukleme)
            db.session.commit()
            
            # Başarı mesajı oluştur
            message_parts = [f"{summary['deleted_misafir_kayit']} misafir kaydı silindi"]
            if summary['deleted_pending_tasks'] > 0:
                message_parts.append(f"{summary['deleted_pending_tasks']} bekleyen görev silindi")
            if summary['preserved_completed_tasks'] > 0:
                message_parts.append(f"{summary['preserved_completed_tasks']} tamamlanmış görev korundu")
            if summary['deleted_empty_gorevler'] > 0:
                message_parts.append(f"{summary['deleted_empty_gorevler']} boş ana görev silindi")
            
            message = ', '.join(message_parts)
            
            # Audit log kaydı oluştur (Requirements 4.3)
            audit_aciklama = (
                f"Doluluk dosyası silindi - İşlem Kodu: {islem_kodu}, "
                f"Dosya: {dosya_adi}, Tip: {dosya_tipi}"
            )
            
            log_audit(
                islem_tipi='delete',
                tablo_adi='dosya_yukleme',
                kayit_id=None,  # Kayıt zaten silindi
                eski_deger={
                    'islem_kodu': islem_kodu,
                    'dosya_adi': dosya_adi,
                    'dosya_tipi': dosya_tipi,
                    'dosya_yolu': dosya_yolu
                },
                yeni_deger=None,
                aciklama=audit_aciklama,
                basarili=True
            )
            
            # Görev yönetimi için ayrı audit log
            if summary['deleted_pending_tasks'] > 0 or summary['preserved_completed_tasks'] > 0:
                gorev_aciklama = (
                    f"Görev yönetimi - Silinen bekleyen: {summary['deleted_pending_tasks']}, "
                    f"Korunan tamamlanmış: {summary['preserved_completed_tasks']}, "
                    f"Silinen boş ana görev: {summary['deleted_empty_gorevler']}"
                )
                
                log_audit(
                    islem_tipi='delete',
                    tablo_adi='gorev_detay',
                    kayit_id=None,
                    eski_deger=summary,
                    yeni_deger=None,
                    aciklama=gorev_aciklama,
                    basarili=True
                )
            
            return True, message, summary
            
        except Exception as e:
            db.session.rollback()
            
            # Hata durumunda da audit log kaydı oluştur
            try:
                log_audit(
                    islem_tipi='delete',
                    tablo_adi='dosya_yukleme',
                    kayit_id=None,
                    eski_deger={'islem_kodu': islem_kodu},
                    yeni_deger=None,
                    aciklama=f"Doluluk dosyası silme hatası - İşlem Kodu: {islem_kodu}",
                    basarili=False,
                    hata_mesaji=str(e)
                )
            except Exception:
                # Audit log hatası ana hatayı gizlememeli
                pass
            
            return False, f'Silme hatası: {str(e)}', empty_summary
    
    @staticmethod
    def cleanup_old_files():
        """
        4 günden eski dosyaları otomatik siler
        (Cron job veya scheduler ile çalıştırılacak)
        
        Returns:
            dict: {
                'success': bool,
                'deleted_count': int,
                'message': str
            }
        """
        try:
            # 4 gün önceki tarih
            cutoff_date = get_kktc_now() - timedelta(days=FileManagementService.FILE_RETENTION_DAYS)
            
            # Eski dosyaları bul
            old_uploads = DosyaYukleme.query.filter(
                and_(
                    DosyaYukleme.yukleme_tarihi < cutoff_date,
                    DosyaYukleme.durum != 'silindi'
                )
            ).all()
            
            deleted_count = 0
            
            for upload in old_uploads:
                # Fiziksel dosyayı sil
                if os.path.exists(upload.dosya_yolu):
                    try:
                        os.remove(upload.dosya_yolu)
                        deleted_count += 1
                    except Exception as e:
                        print(f"Dosya silme hatası ({upload.dosya_yolu}): {str(e)}")
                
                # Durumu güncelle
                upload.durum = 'silindi'
                upload.silme_tarihi = get_kktc_now()
            
            db.session.commit()
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'message': f'{deleted_count} eski dosya temizlendi'
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'deleted_count': 0,
                'message': f'Temizleme hatası: {str(e)}'
            }
    
    @staticmethod
    def generate_islem_kodu():
        """
        Benzersiz işlem kodu oluşturur
        Format: DOLULUK-YYYYMMDD-HHMMSS-RANDOM
        
        Returns:
            str: Benzersiz işlem kodu
        """
        now = get_kktc_now()
        date_part = now.strftime('%Y%m%d')
        time_part = now.strftime('%H%M%S')
        random_part = str(uuid.uuid4())[:8].upper()
        
        return f"DOLULUK-{date_part}-{time_part}-{random_part}"
    
    @staticmethod
    def _allowed_file(filename):
        """Dosya uzantısı kontrolü"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in FileManagementService.ALLOWED_EXTENSIONS
    
    @staticmethod
    def _ensure_upload_folder():
        """Upload klasörünü oluştur (yoksa)"""
        if not os.path.exists(FileManagementService.UPLOAD_FOLDER):
            os.makedirs(FileManagementService.UPLOAD_FOLDER, exist_ok=True)
    
    @staticmethod
    def update_dosya_yukleme_status(islem_kodu, durum, **kwargs):
        """
        Dosya yükleme durumunu günceller
        
        Args:
            islem_kodu: İşlem kodu
            durum: Yeni durum
            **kwargs: Ek alanlar (dosya_tipi, toplam_satir, basarili_satir, hatali_satir, hata_detaylari)
        """
        try:
            dosya_yukleme = DosyaYukleme.query.filter_by(islem_kodu=islem_kodu).first()
            
            if dosya_yukleme:
                dosya_yukleme.durum = durum
                
                # Ek alanları güncelle
                if 'dosya_tipi' in kwargs:
                    dosya_yukleme.dosya_tipi = kwargs['dosya_tipi']
                if 'toplam_satir' in kwargs:
                    dosya_yukleme.toplam_satir = kwargs['toplam_satir']
                if 'basarili_satir' in kwargs:
                    dosya_yukleme.basarili_satir = kwargs['basarili_satir']
                if 'hatali_satir' in kwargs:
                    dosya_yukleme.hatali_satir = kwargs['hatali_satir']
                if 'hata_detaylari' in kwargs:
                    dosya_yukleme.hata_detaylari = kwargs['hata_detaylari']
                
                db.session.commit()
                return True
            
            return False
            
        except Exception as e:
            db.session.rollback()
            print(f"Durum güncelleme hatası: {str(e)}")
            return False

