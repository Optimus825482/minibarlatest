"""
Görevlendirme Sistemi - BildirimService
Görev bildirimleri ve uyarıların yönetimi
"""

from datetime import datetime, date, timezone, timedelta
from typing import List, Dict, Optional
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload

from models import (
    db, GunlukGorev, GorevDetay, DNDKontrol, YuklemeGorev,
    Kullanici, Otel, SistemLog
)


class BildirimService:
    """Bildirim yönetim servisi"""
    
    # Bildirim tipleri
    BILDIRIM_TIPLERI = {
        'gorev_olusturuldu': 'Yeni görev oluşturuldu',
        'gorev_tamamlandi': 'Görev tamamlandı',
        'dnd_isaretlendi': 'Oda DND olarak işaretlendi',
        'dnd_tamamlanmadi': 'DND görev tamamlanmadı',
        'yukleme_bekliyor': 'Yükleme görevi bekliyor',
        'yukleme_tamamlandi': 'Yükleme tamamlandı',
        'yukleme_eksik': 'Eksik yükleme tespit edildi'
    }
    
    @staticmethod
    def send_task_notification(personel_id: int, mesaj: str, tip: str, ilgili_id: int = None) -> bool:
        """
        Görev bildirimi gönderir.
        
        Args:
            personel_id: Bildirim gönderilecek personel ID
            mesaj: Bildirim mesajı
            tip: Bildirim tipi
            ilgili_id: İlgili kayıt ID (görev, oda vb.)
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            # Personel kontrolü
            personel = Kullanici.query.get(personel_id)
            if not personel:
                raise ValueError("Personel bulunamadı")
            
            # Sistem log'a kaydet (bildirim olarak)
            log = SistemLog(
                kullanici_id=personel_id,
                islem_tipi='bildirim',
                modul='gorevlendirme',
                islem_detay={
                    'tip': tip,
                    'mesaj': mesaj,
                    'ilgili_id': ilgili_id,
                    'okundu': False,
                    'olusturma_zamani': datetime.now(timezone.utc).isoformat()
                }
            )
            db.session.add(log)
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Bildirim gönderme hatası: {str(e)}")
    
    @staticmethod
    def send_dnd_incomplete_notification(gorev_detay_ids: List[int]) -> bool:
        """
        Tamamlanmayan DND bildirimi gönderir.
        
        Args:
            gorev_detay_ids: Tamamlanmayan DND görev detay ID'leri
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            if not gorev_detay_ids:
                return True
            
            # Görev detaylarını al
            detaylar = GorevDetay.query.filter(
                GorevDetay.id.in_(gorev_detay_ids)
            ).options(
                joinedload(GorevDetay.oda),
                joinedload(GorevDetay.gorev).joinedload(GunlukGorev.personel)
            ).all()
            
            # Her detay için bildirim oluştur
            for detay in detaylar:
                if not detay.gorev or not detay.gorev.personel:
                    continue
                
                oda_no = detay.oda.oda_no if detay.oda else 'Bilinmiyor'
                ilk_dnd_zamani = detay.dnd_kontroller[0].kontrol_zamani.strftime('%H:%M') if detay.dnd_kontroller else 'Bilinmiyor'
                
                mesaj = f"Oda {oda_no} - DND görev tamamlanmadı. İlk DND: {ilk_dnd_zamani}, Kontrol sayısı: {detay.dnd_sayisi}"
                
                # Kat sorumlusuna bildirim
                BildirimService.send_task_notification(
                    personel_id=detay.gorev.personel_id,
                    mesaj=mesaj,
                    tip='dnd_tamamlanmadi',
                    ilgili_id=detay.id
                )
                
                # Sistem yöneticilerine bildirim
                sistem_yoneticileri = Kullanici.query.filter(
                    Kullanici.rol == 'sistem_yoneticisi',
                    Kullanici.aktif == True
                ).all()
                
                for yonetici in sistem_yoneticileri:
                    BildirimService.send_task_notification(
                        personel_id=yonetici.id,
                        mesaj=mesaj,
                        tip='dnd_tamamlanmadi',
                        ilgili_id=detay.id
                    )
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"DND bildirim gönderme hatası: {str(e)}")
    
    @staticmethod
    def send_upload_warning(depo_sorumlusu_id: int, dosya_tipi: str, otel_id: int = None) -> bool:
        """
        Yükleme uyarısı gönderir.
        
        Args:
            depo_sorumlusu_id: Depo sorumlusu ID
            dosya_tipi: 'inhouse' veya 'arrivals'
            otel_id: Otel ID (opsiyonel)
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            # Otel adını al
            otel_adi = ''
            if otel_id:
                otel = Otel.query.get(otel_id)
                otel_adi = f" ({otel.ad})" if otel else ''
            
            dosya_tipi_adi = 'In House' if dosya_tipi == 'inhouse' else 'Arrivals'
            mesaj = f"{dosya_tipi_adi} dosyası{otel_adi} henüz yüklenmedi. Lütfen yükleme yapınız."
            
            # Depo sorumlusuna bildirim
            BildirimService.send_task_notification(
                personel_id=depo_sorumlusu_id,
                mesaj=mesaj,
                tip='yukleme_bekliyor',
                ilgili_id=otel_id
            )
            
            # Sistem yöneticilerine bildirim
            sistem_yoneticileri = Kullanici.query.filter(
                Kullanici.rol == 'sistem_yoneticisi',
                Kullanici.aktif == True
            ).all()
            
            for yonetici in sistem_yoneticileri:
                BildirimService.send_task_notification(
                    personel_id=yonetici.id,
                    mesaj=mesaj,
                    tip='yukleme_eksik',
                    ilgili_id=otel_id
                )
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Yükleme uyarısı gönderme hatası: {str(e)}")
    
    @staticmethod
    def get_notifications(personel_id: int, sadece_okunmamis: bool = False, limit: int = 50) -> List[Dict]:
        """
        Personel bildirimlerini getirir.
        
        Args:
            personel_id: Personel ID
            sadece_okunmamis: Sadece okunmamış bildirimleri getir
            limit: Maksimum bildirim sayısı
            
        Returns:
            List[Dict]: Bildirim listesi
        """
        try:
            query = SistemLog.query.filter(
                SistemLog.kullanici_id == personel_id,
                SistemLog.islem_tipi == 'bildirim',
                SistemLog.modul == 'gorevlendirme'
            ).order_by(SistemLog.islem_tarihi.desc())
            
            if sadece_okunmamis:
                # JSONB içinde okundu=False olanları filtrele
                query = query.filter(
                    SistemLog.islem_detay['okundu'].astext == 'false'
                )
            
            bildirimler = query.limit(limit).all()
            
            result = []
            for bildirim in bildirimler:
                detay = bildirim.islem_detay or {}
                result.append({
                    'id': bildirim.id,
                    'tip': detay.get('tip'),
                    'mesaj': detay.get('mesaj'),
                    'ilgili_id': detay.get('ilgili_id'),
                    'okundu': detay.get('okundu', False),
                    'tarih': bildirim.islem_tarihi.isoformat() if bildirim.islem_tarihi else None
                })
            
            return result
            
        except Exception as e:
            raise Exception(f"Bildirim getirme hatası: {str(e)}")
    
    @staticmethod
    def mark_notification_read(bildirim_id: int) -> bool:
        """
        Bildirimi okundu olarak işaretler.
        
        Args:
            bildirim_id: Bildirim (SistemLog) ID
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            bildirim = SistemLog.query.get(bildirim_id)
            if not bildirim:
                raise ValueError("Bildirim bulunamadı")
            
            if bildirim.islem_detay:
                bildirim.islem_detay = {
                    **bildirim.islem_detay,
                    'okundu': True,
                    'okunma_zamani': datetime.now(timezone.utc).isoformat()
                }
                db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Bildirim okundu işaretleme hatası: {str(e)}")
    
    @staticmethod
    def get_unread_count(personel_id: int) -> int:
        """
        Okunmamış bildirim sayısını getirir.
        
        Args:
            personel_id: Personel ID
            
        Returns:
            int: Okunmamış bildirim sayısı
        """
        try:
            count = SistemLog.query.filter(
                SistemLog.kullanici_id == personel_id,
                SistemLog.islem_tipi == 'bildirim',
                SistemLog.modul == 'gorevlendirme',
                SistemLog.islem_detay['okundu'].astext == 'false'
            ).count()
            
            return count
            
        except Exception as e:
            raise Exception(f"Okunmamış bildirim sayısı getirme hatası: {str(e)}")
    
    @staticmethod
    def send_task_created_notification(personel_id: int, gorev_tipi: str, oda_sayisi: int) -> bool:
        """
        Görev oluşturuldu bildirimi gönderir.
        
        Args:
            personel_id: Personel ID
            gorev_tipi: Görev tipi
            oda_sayisi: Oda sayısı
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            tip_adi = 'In House' if gorev_tipi == 'inhouse_kontrol' else 'Arrivals'
            mesaj = f"Yeni {tip_adi} görevleri oluşturuldu. Toplam {oda_sayisi} oda kontrol edilecek."
            
            return BildirimService.send_task_notification(
                personel_id=personel_id,
                mesaj=mesaj,
                tip='gorev_olusturuldu'
            )
            
        except Exception as e:
            raise Exception(f"Görev oluşturuldu bildirimi hatası: {str(e)}")
