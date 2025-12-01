"""
Görevlendirme Sistemi - YuklemeGorevService
Depo sorumluları için günlük doluluk yükleme görevlerinin yönetimi
"""

from datetime import datetime, date, timezone, timedelta
from typing import List, Dict, Optional
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload

from models import (
    db, YuklemeGorev, DosyaYukleme, Kullanici, Otel, 
    KullaniciOtel, GorevDurum
)


class YuklemeGorevService:
    """Yükleme görev yönetim servisi"""
    
    @staticmethod
    def create_daily_upload_tasks(tarih: date) -> List[Dict]:
        """
        Tüm depo sorumluları için günlük yükleme görevleri oluşturur.
        Her depo sorumlusu için In House ve Arrivals yükleme görevleri oluşturur.
        
        Args:
            tarih: Görev tarihi
            
        Returns:
            List[Dict]: Oluşturulan görev bilgileri
        """
        try:
            result = []
            
            # Tüm aktif depo sorumlularını bul
            depo_sorumluları = Kullanici.query.filter(
                Kullanici.rol == 'depo_sorumlusu',
                Kullanici.aktif == True
            ).all()
            
            for depo_sorumlusu in depo_sorumluları:
                # Depo sorumlusunun atandığı otelleri bul
                atamalar = KullaniciOtel.query.filter(
                    KullaniciOtel.kullanici_id == depo_sorumlusu.id
                ).all()
                
                for atama in atamalar:
                    otel_id = atama.otel_id
                    
                    # In House yükleme görevi
                    inhouse_gorev = YuklemeGorevService._create_upload_task(
                        otel_id=otel_id,
                        depo_sorumlusu_id=depo_sorumlusu.id,
                        tarih=tarih,
                        dosya_tipi='inhouse'
                    )
                    if inhouse_gorev:
                        result.append({
                            'gorev_id': inhouse_gorev.id,
                            'otel_id': otel_id,
                            'depo_sorumlusu_id': depo_sorumlusu.id,
                            'dosya_tipi': 'inhouse'
                        })
                    
                    # Arrivals yükleme görevi
                    arrivals_gorev = YuklemeGorevService._create_upload_task(
                        otel_id=otel_id,
                        depo_sorumlusu_id=depo_sorumlusu.id,
                        tarih=tarih,
                        dosya_tipi='arrivals'
                    )
                    if arrivals_gorev:
                        result.append({
                            'gorev_id': arrivals_gorev.id,
                            'otel_id': otel_id,
                            'depo_sorumlusu_id': depo_sorumlusu.id,
                            'dosya_tipi': 'arrivals'
                        })
            
            db.session.commit()
            return result
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Günlük yükleme görevi oluşturma hatası: {str(e)}")
    
    @staticmethod
    def _create_upload_task(otel_id: int, depo_sorumlusu_id: int, tarih: date, dosya_tipi: str) -> Optional[YuklemeGorev]:
        """
        Tek bir yükleme görevi oluşturur.
        
        Args:
            otel_id: Otel ID
            depo_sorumlusu_id: Depo sorumlusu ID
            tarih: Görev tarihi
            dosya_tipi: 'inhouse' veya 'arrivals'
            
        Returns:
            YuklemeGorev: Oluşturulan görev veya None
        """
        try:
            # Mevcut görev var mı kontrol et
            mevcut = YuklemeGorev.query.filter(
                YuklemeGorev.otel_id == otel_id,
                YuklemeGorev.gorev_tarihi == tarih,
                YuklemeGorev.dosya_tipi == dosya_tipi
            ).first()
            
            if mevcut:
                return None  # Zaten var
            
            gorev = YuklemeGorev(
                otel_id=otel_id,
                depo_sorumlusu_id=depo_sorumlusu_id,
                gorev_tarihi=tarih,
                dosya_tipi=dosya_tipi,
                durum='pending'
            )
            db.session.add(gorev)
            db.session.flush()
            
            return gorev
            
        except Exception as e:
            raise Exception(f"Yükleme görevi oluşturma hatası: {str(e)}")
    
    @staticmethod
    def complete_upload_task(otel_id: int, dosya_tipi: str, dosya_yukleme_id: int, tarih: date = None) -> bool:
        """
        Yükleme görevini tamamlar.
        
        Args:
            otel_id: Otel ID
            dosya_tipi: 'inhouse' veya 'arrivals'
            dosya_yukleme_id: DosyaYukleme kaydının ID'si
            tarih: Görev tarihi (varsayılan bugün)
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            if tarih is None:
                tarih = date.today()
            
            # Dosya tipini normalize et
            normalized_dosya_tipi = dosya_tipi.lower()
            if normalized_dosya_tipi == 'in_house':
                normalized_dosya_tipi = 'inhouse'
            
            gorev = YuklemeGorev.query.filter(
                YuklemeGorev.otel_id == otel_id,
                YuklemeGorev.gorev_tarihi == tarih,
                YuklemeGorev.dosya_tipi == normalized_dosya_tipi
            ).first()
            
            if not gorev:
                # Görev yoksa oluştur ve tamamla
                # Önce depo sorumlusunu bul
                atama = KullaniciOtel.query.join(Kullanici).filter(
                    KullaniciOtel.otel_id == otel_id,
                    Kullanici.rol == 'depo_sorumlusu',
                    Kullanici.aktif == True
                ).first()
                
                if atama:
                    gorev = YuklemeGorev(
                        otel_id=otel_id,
                        depo_sorumlusu_id=atama.kullanici_id,
                        gorev_tarihi=tarih,
                        dosya_tipi=normalized_dosya_tipi,
                        durum='completed',
                        yukleme_zamani=datetime.now(timezone.utc),
                        dosya_yukleme_id=dosya_yukleme_id
                    )
                    db.session.add(gorev)
                    db.session.commit()
                    return True
                return False
            
            # Görevi güncelle
            gorev.durum = 'completed'
            gorev.yukleme_zamani = datetime.now(timezone.utc)
            gorev.dosya_yukleme_id = dosya_yukleme_id
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Yükleme görevi tamamlama hatası: {str(e)}")
    
    @staticmethod
    def get_pending_uploads(depo_sorumlusu_id: int, tarih: date = None) -> List[Dict]:
        """
        Bekleyen yükleme görevlerini getirir.
        
        Args:
            depo_sorumlusu_id: Depo sorumlusu ID
            tarih: Görev tarihi (varsayılan bugün)
            
        Returns:
            List[Dict]: Bekleyen yükleme görevleri
        """
        try:
            if tarih is None:
                tarih = date.today()
            
            gorevler = YuklemeGorev.query.filter(
                YuklemeGorev.depo_sorumlusu_id == depo_sorumlusu_id,
                YuklemeGorev.gorev_tarihi == tarih,
                YuklemeGorev.durum == 'pending'
            ).options(joinedload(YuklemeGorev.otel)).all()
            
            result = []
            for gorev in gorevler:
                result.append({
                    'gorev_id': gorev.id,
                    'otel_id': gorev.otel_id,
                    'otel_adi': gorev.otel.ad if gorev.otel else None,
                    'dosya_tipi': gorev.dosya_tipi,
                    'gorev_tarihi': gorev.gorev_tarihi.isoformat(),
                    'durum': gorev.durum
                })
            
            return result
            
        except Exception as e:
            raise Exception(f"Bekleyen yükleme getirme hatası: {str(e)}")
    
    @staticmethod
    def get_upload_status(otel_id: int, tarih: date = None) -> Dict:
        """
        Yükleme durumunu getirir.
        
        Args:
            otel_id: Otel ID
            tarih: Görev tarihi (varsayılan bugün)
            
        Returns:
            Dict: Yükleme durumu bilgileri
        """
        try:
            if tarih is None:
                tarih = date.today()
            
            gorevler = YuklemeGorev.query.filter(
                YuklemeGorev.otel_id == otel_id,
                YuklemeGorev.gorev_tarihi == tarih
            ).options(
                joinedload(YuklemeGorev.depo_sorumlusu),
                joinedload(YuklemeGorev.dosya_yukleme)
            ).all()
            
            result = {
                'tarih': tarih.isoformat(),
                'otel_id': otel_id,
                'inhouse': None,
                'arrivals': None
            }
            
            for gorev in gorevler:
                gorev_bilgi = {
                    'gorev_id': gorev.id,
                    'durum': gorev.durum,
                    'yukleme_zamani': gorev.yukleme_zamani.isoformat() if gorev.yukleme_zamani else None,
                    'depo_sorumlusu': f"{gorev.depo_sorumlusu.ad} {gorev.depo_sorumlusu.soyad}" if gorev.depo_sorumlusu else None,
                    'dosya_yukleme_id': gorev.dosya_yukleme_id
                }
                
                if gorev.dosya_tipi == 'inhouse':
                    result['inhouse'] = gorev_bilgi
                elif gorev.dosya_tipi == 'arrivals':
                    result['arrivals'] = gorev_bilgi
            
            return result
            
        except Exception as e:
            raise Exception(f"Yükleme durumu getirme hatası: {str(e)}")
    
    @staticmethod
    def get_missing_uploads(baslangic: date, bitis: date, otel_id: int = None) -> List[Dict]:
        """
        Eksik yükleme günlerini tespit eder.
        
        Args:
            baslangic: Başlangıç tarihi
            bitis: Bitiş tarihi
            otel_id: Opsiyonel otel filtresi
            
        Returns:
            List[Dict]: Eksik yükleme bilgileri
        """
        try:
            result = []
            
            # Otelleri bul
            if otel_id:
                oteller = [Otel.query.get(otel_id)]
            else:
                oteller = Otel.query.filter(Otel.aktif == True).all()
            
            # Her gün için kontrol et
            current_date = baslangic
            while current_date <= bitis:
                for otel in oteller:
                    if not otel:
                        continue
                    
                    # In House kontrolü
                    inhouse_gorev = YuklemeGorev.query.filter(
                        YuklemeGorev.otel_id == otel.id,
                        YuklemeGorev.gorev_tarihi == current_date,
                        YuklemeGorev.dosya_tipi == 'inhouse',
                        YuklemeGorev.durum == 'completed'
                    ).first()
                    
                    if not inhouse_gorev:
                        # Depo sorumlusunu bul
                        atama = KullaniciOtel.query.join(Kullanici).filter(
                            KullaniciOtel.otel_id == otel.id,
                            Kullanici.rol == 'depo_sorumlusu'
                        ).first()
                        
                        result.append({
                            'tarih': current_date.isoformat(),
                            'otel_id': otel.id,
                            'otel_adi': otel.ad,
                            'dosya_tipi': 'inhouse',
                            'depo_sorumlusu_id': atama.kullanici_id if atama else None,
                            'depo_sorumlusu_adi': f"{atama.kullanici.ad} {atama.kullanici.soyad}" if atama and atama.kullanici else None
                        })
                    
                    # Arrivals kontrolü
                    arrivals_gorev = YuklemeGorev.query.filter(
                        YuklemeGorev.otel_id == otel.id,
                        YuklemeGorev.gorev_tarihi == current_date,
                        YuklemeGorev.dosya_tipi == 'arrivals',
                        YuklemeGorev.durum == 'completed'
                    ).first()
                    
                    if not arrivals_gorev:
                        atama = KullaniciOtel.query.join(Kullanici).filter(
                            KullaniciOtel.otel_id == otel.id,
                            Kullanici.rol == 'depo_sorumlusu'
                        ).first()
                        
                        result.append({
                            'tarih': current_date.isoformat(),
                            'otel_id': otel.id,
                            'otel_adi': otel.ad,
                            'dosya_tipi': 'arrivals',
                            'depo_sorumlusu_id': atama.kullanici_id if atama else None,
                            'depo_sorumlusu_adi': f"{atama.kullanici.ad} {atama.kullanici.soyad}" if atama and atama.kullanici else None
                        })
                
                current_date += timedelta(days=1)
            
            return result
            
        except Exception as e:
            raise Exception(f"Eksik yükleme tespiti hatası: {str(e)}")
    
    @staticmethod
    def get_upload_statistics(otel_id: int, donem: str = 'haftalik') -> Dict:
        """
        Yükleme istatistiklerini getirir.
        
        Args:
            otel_id: Otel ID
            donem: 'haftalik' veya 'aylik'
            
        Returns:
            Dict: Yükleme istatistikleri
        """
        try:
            today = date.today()
            
            if donem == 'haftalik':
                baslangic = today - timedelta(days=7)
            else:  # aylik
                baslangic = today - timedelta(days=30)
            
            # Toplam gün sayısı
            toplam_gun = (today - baslangic).days + 1
            
            # Tamamlanan yüklemeler
            tamamlanan_inhouse = YuklemeGorev.query.filter(
                YuklemeGorev.otel_id == otel_id,
                YuklemeGorev.gorev_tarihi >= baslangic,
                YuklemeGorev.gorev_tarihi <= today,
                YuklemeGorev.dosya_tipi == 'inhouse',
                YuklemeGorev.durum == 'completed'
            ).count()
            
            tamamlanan_arrivals = YuklemeGorev.query.filter(
                YuklemeGorev.otel_id == otel_id,
                YuklemeGorev.gorev_tarihi >= baslangic,
                YuklemeGorev.gorev_tarihi <= today,
                YuklemeGorev.dosya_tipi == 'arrivals',
                YuklemeGorev.durum == 'completed'
            ).count()
            
            return {
                'donem': donem,
                'baslangic': baslangic.isoformat(),
                'bitis': today.isoformat(),
                'toplam_gun': toplam_gun,
                'inhouse': {
                    'tamamlanan': tamamlanan_inhouse,
                    'beklenen': toplam_gun,
                    'oran': round((tamamlanan_inhouse / toplam_gun * 100), 1) if toplam_gun > 0 else 0
                },
                'arrivals': {
                    'tamamlanan': tamamlanan_arrivals,
                    'beklenen': toplam_gun,
                    'oran': round((tamamlanan_arrivals / toplam_gun * 100), 1) if toplam_gun > 0 else 0
                },
                'toplam_oran': round(((tamamlanan_inhouse + tamamlanan_arrivals) / (toplam_gun * 2) * 100), 1) if toplam_gun > 0 else 0
            }
            
        except Exception as e:
            raise Exception(f"Yükleme istatistikleri getirme hatası: {str(e)}")
