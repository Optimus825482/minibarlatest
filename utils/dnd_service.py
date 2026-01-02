"""
Bağımsız DND (Do Not Disturb) Servis Modülü

Bu modül, görev sisteminden bağımsız DND kayıtlarını yönetir.
Görev atanmamış odalar için de DND kaydı yapılabilir.

Özellikler:
- Görev sisteminden bağımsız çalışır
- Günlük bazda oda başına tek kayıt
- Her kontrol için detay kaydı
- Minimum 3 kontrol gereksinimi
- Opsiyonel görev entegrasyonu

Kullanım:
    from utils.dnd_service import DNDService
    
    # DND kaydı oluştur/güncelle
    result = DNDService.kaydet(oda_id=101, personel_id=5, notlar="Kapıda tabela var")
    
    # Oda DND durumunu sorgula
    durum = DNDService.oda_durumu(oda_id=101)
    
    # Günlük DND listesi
    liste = DNDService.gunluk_liste(otel_id=1, tarih=date.today())
"""

from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import joinedload

from models import (
    db, Oda, Otel, Kullanici, OdaDNDKayit, OdaDNDKontrol,
    GorevDetay, GunlukGorev, GorevDurumLog, OdaKontrolKaydi
)


def get_kktc_now():
    """KKTC saat diliminde şu anki zamanı döndürür."""
    import pytz
    from datetime import datetime
    KKTC_TZ = pytz.timezone('Europe/Nicosia')
    return datetime.now(KKTC_TZ)


class DNDServiceError(Exception):
    """DND servis hataları için özel exception"""
    pass


class OdaNotFoundError(DNDServiceError):
    """Oda bulunamadı hatası"""
    pass


class DNDService:
    """
    Bağımsız DND yönetim servisi.
    Görev sisteminden bağımsız çalışır, opsiyonel entegrasyon sağlar.
    """
    
    # Sabitler
    MIN_KONTROL_SAYISI = 3  # Minimum kontrol sayısı
    DURUM_AKTIF = 'aktif'
    DURUM_TAMAMLANDI = 'tamamlandi'
    DURUM_IPTAL = 'iptal'
    
    @staticmethod
    def kaydet(
        oda_id: int,
        personel_id: int,
        notlar: Optional[str] = None,
        gorev_detay_id: Optional[int] = None
    ) -> Dict:
        """
        DND kaydı oluşturur veya mevcut kaydı günceller.
        
        Args:
            oda_id: Oda ID
            personel_id: Kontrol eden personel ID
            notlar: Opsiyonel notlar
            gorev_detay_id: Opsiyonel görev detay ID (varsa bağlanır)
            
        Returns:
            Dict: İşlem sonucu
            {
                'success': True,
                'dnd_kayit_id': 123,
                'dnd_sayisi': 2,
                'min_kontrol_tamamlandi': False,
                'durum': 'aktif',
                'mesaj': 'DND kaydı oluşturuldu (2/3)'
            }
            
        Raises:
            OdaNotFoundError: Oda bulunamadığında
            DNDServiceError: Diğer hatalar
        """
        try:
            simdi = get_kktc_now()
            bugun = simdi.date()
            
            # Oda kontrolü
            oda = db.session.get(Oda, oda_id)
            if not oda:
                raise OdaNotFoundError(f"Oda bulunamadı: {oda_id}")
            
            # Otel ID'yi oda üzerinden al
            otel_id = oda.kat.otel_id if oda.kat else None
            if not otel_id:
                raise DNDServiceError("Odanın otel bilgisi bulunamadı")
            
            # Bugünkü DND kaydını bul veya oluştur
            dnd_kayit = OdaDNDKayit.query.filter_by(
                oda_id=oda_id,
                kayit_tarihi=bugun
            ).first()
            
            if not dnd_kayit:
                # Yeni kayıt oluştur
                dnd_kayit = OdaDNDKayit(
                    oda_id=oda_id,
                    otel_id=otel_id,
                    kayit_tarihi=bugun,
                    dnd_sayisi=0,
                    ilk_dnd_zamani=simdi,
                    durum=DNDService.DURUM_AKTIF,
                    gorev_detay_id=gorev_detay_id
                )
                db.session.add(dnd_kayit)
                db.session.flush()
            
            # DND sayısını artır
            dnd_kayit.dnd_sayisi += 1
            dnd_kayit.son_dnd_zamani = simdi
            dnd_kayit.guncelleme_tarihi = simdi
            
            # Görev bağlantısı yoksa ve parametre geldiyse bağla
            if not dnd_kayit.gorev_detay_id and gorev_detay_id:
                dnd_kayit.gorev_detay_id = gorev_detay_id
            
            # Kontrol kaydı oluştur
            kontrol = OdaDNDKontrol(
                dnd_kayit_id=dnd_kayit.id,
                kontrol_no=dnd_kayit.dnd_sayisi,
                kontrol_eden_id=personel_id,
                kontrol_zamani=simdi,
                notlar=notlar or f'DND kontrolü #{dnd_kayit.dnd_sayisi}'
            )
            db.session.add(kontrol)
            
            # oda_kontrol_kayitlari tablosuna da DND kaydı ekle
            oda_kontrol_kaydi = OdaKontrolKaydi(
                oda_id=oda_id,
                personel_id=personel_id,
                kontrol_tarihi=bugun,
                baslangic_zamani=simdi,
                bitis_zamani=simdi,  # DND için başlangıç ve bitiş aynı
                kontrol_tipi='dnd'
            )
            db.session.add(oda_kontrol_kaydi)
            
            # Minimum kontrol tamamlandı mı?
            min_kontrol_tamamlandi = dnd_kayit.dnd_sayisi >= DNDService.MIN_KONTROL_SAYISI
            
            # Durum güncelle
            if min_kontrol_tamamlandi:
                dnd_kayit.durum = DNDService.DURUM_TAMAMLANDI
            
            # Görev entegrasyonu - varsa görev detayını da güncelle
            gorev_guncellendi = False
            if dnd_kayit.gorev_detay_id:
                gorev_guncellendi = DNDService._gorev_entegrasyonu(
                    dnd_kayit.gorev_detay_id,
                    dnd_kayit.dnd_sayisi,
                    personel_id,
                    simdi,
                    min_kontrol_tamamlandi
                )
            
            db.session.commit()
            
            # Mesaj oluştur
            if min_kontrol_tamamlandi:
                mesaj = f'Oda {oda.oda_no} - {dnd_kayit.dnd_sayisi}. DND kontrolü tamamlandı!'
            else:
                mesaj = f'Oda {oda.oda_no} DND olarak işaretlendi ({dnd_kayit.dnd_sayisi}/{DNDService.MIN_KONTROL_SAYISI})'
            
            return {
                'success': True,
                'dnd_kayit_id': dnd_kayit.id,
                'dnd_sayisi': dnd_kayit.dnd_sayisi,
                'min_kontrol_tamamlandi': min_kontrol_tamamlandi,
                'durum': dnd_kayit.durum,
                'mesaj': mesaj,
                'gorev_guncellendi': gorev_guncellendi
            }
            
        except OdaNotFoundError:
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            raise DNDServiceError(f"DND kayıt hatası: {str(e)}")
    
    @staticmethod
    def _gorev_entegrasyonu(
        gorev_detay_id: int,
        dnd_sayisi: int,
        personel_id: int,
        simdi: datetime,
        min_kontrol_tamamlandi: bool
    ) -> bool:
        """
        Görev sistemini DND kaydıyla senkronize eder.
        
        Args:
            gorev_detay_id: Görev detay ID
            dnd_sayisi: Güncel DND sayısı
            personel_id: İşlemi yapan personel
            simdi: İşlem zamanı
            min_kontrol_tamamlandi: 3+ kontrol yapıldı mı
            
        Returns:
            bool: Görev güncellendi mi
        """
        try:
            detay = db.session.get(GorevDetay, gorev_detay_id)
            if not detay:
                return False
            
            onceki_durum = detay.durum
            
            # GorevDetay'ı güncelle
            detay.dnd_sayisi = dnd_sayisi
            detay.son_dnd_zamani = simdi
            
            if min_kontrol_tamamlandi:
                detay.durum = 'completed'
                detay.kontrol_zamani = simdi
                detay.notlar = f'{dnd_sayisi} kez DND kontrolü yapıldı - Otomatik tamamlandı'
                
                # Ana görevi güncelle
                gorev = detay.gorev
                if gorev:
                    tamamlanan = sum(1 for d in gorev.detaylar if d.durum == 'completed')
                    if tamamlanan == len(gorev.detaylar):
                        gorev.durum = 'completed'
                        gorev.tamamlanma_tarihi = simdi
                    elif tamamlanan > 0:
                        gorev.durum = 'in_progress'
            else:
                detay.durum = 'dnd_pending'
            
            # Log kaydı
            log = GorevDurumLog(
                gorev_detay_id=detay.id,
                onceki_durum=onceki_durum,
                yeni_durum=detay.durum,
                degistiren_id=personel_id,
                aciklama=f'DND kontrolü #{dnd_sayisi} (Bağımsız DND sistemi)'
            )
            db.session.add(log)
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def oda_durumu(oda_id: int, tarih: Optional[date] = None) -> Optional[Dict]:
        """
        Odanın DND durumunu sorgular.
        
        Args:
            oda_id: Oda ID
            tarih: Sorgulanacak tarih (varsayılan: bugün)
            
        Returns:
            Dict veya None: DND durumu
            {
                'dnd_kayit_id': 123,
                'dnd_sayisi': 2,
                'ilk_dnd_zamani': '2026-01-01T10:30:00',
                'son_dnd_zamani': '2026-01-01T14:45:00',
                'durum': 'aktif',
                'min_kontrol_tamamlandi': False,
                'kontroller': [...]
            }
        """
        if tarih is None:
            tarih = get_kktc_now().date()
        
        dnd_kayit = OdaDNDKayit.query.filter_by(
            oda_id=oda_id,
            kayit_tarihi=tarih
        ).first()
        
        if not dnd_kayit:
            return None
        
        # Dynamic relationship olduğu için ayrı sorgu yapıyoruz
        kontroller = [{
            'kontrol_no': k.kontrol_no,
            'kontrol_zamani': k.kontrol_zamani.isoformat() if k.kontrol_zamani else None,
            'kontrol_eden_id': k.kontrol_eden_id,
            'notlar': k.notlar
        } for k in dnd_kayit.kontroller.order_by(OdaDNDKontrol.kontrol_no).all()]
        
        return {
            'dnd_kayit_id': dnd_kayit.id,
            'oda_id': dnd_kayit.oda_id,
            'dnd_sayisi': dnd_kayit.dnd_sayisi,
            'ilk_dnd_zamani': dnd_kayit.ilk_dnd_zamani.isoformat() if dnd_kayit.ilk_dnd_zamani else None,
            'son_dnd_zamani': dnd_kayit.son_dnd_zamani.isoformat() if dnd_kayit.son_dnd_zamani else None,
            'durum': dnd_kayit.durum,
            'min_kontrol_tamamlandi': dnd_kayit.min_kontrol_tamamlandi,
            'gorev_detay_id': dnd_kayit.gorev_detay_id,
            'kontroller': kontroller
        }
    
    @staticmethod
    def gunluk_liste(
        otel_id: int,
        tarih: Optional[date] = None,
        sadece_aktif: bool = False
    ) -> List[Dict]:
        """
        Otelin günlük DND listesini getirir.
        
        Args:
            otel_id: Otel ID
            tarih: Sorgulanacak tarih (varsayılan: bugün)
            sadece_aktif: Sadece aktif (tamamlanmamış) kayıtları getir
            
        Returns:
            List[Dict]: DND kayıtları listesi
        """
        if tarih is None:
            tarih = get_kktc_now().date()
        
        query = OdaDNDKayit.query.filter_by(
            otel_id=otel_id,
            kayit_tarihi=tarih
        ).options(
            joinedload(OdaDNDKayit.oda).joinedload(Oda.kat)
        )
        
        if sadece_aktif:
            query = query.filter_by(durum=DNDService.DURUM_AKTIF)
        
        kayitlar = query.order_by(OdaDNDKayit.son_dnd_zamani.desc()).all()
        
        result = []
        for kayit in kayitlar:
            kat_bilgi = None
            if kayit.oda and kayit.oda.kat:
                kat_bilgi = {
                    'kat_id': kayit.oda.kat.id,
                    'kat_no': kayit.oda.kat.kat_no,
                    'kat_adi': kayit.oda.kat.kat_adi
                }
            
            result.append({
                'dnd_kayit_id': kayit.id,
                'oda_id': kayit.oda_id,
                'oda_no': kayit.oda.oda_no if kayit.oda else None,
                'kat': kat_bilgi,
                'dnd_sayisi': kayit.dnd_sayisi,
                'ilk_dnd_zamani': kayit.ilk_dnd_zamani.isoformat() if kayit.ilk_dnd_zamani else None,
                'son_dnd_zamani': kayit.son_dnd_zamani.isoformat() if kayit.son_dnd_zamani else None,
                'durum': kayit.durum,
                'min_kontrol_tamamlandi': kayit.min_kontrol_tamamlandi,
                'gorev_bagli': kayit.gorev_detay_id is not None
            })
        
        return result
    
    @staticmethod
    def personel_gunluk_ozet(personel_id: int, tarih: Optional[date] = None) -> Dict:
        """
        Personelin günlük DND özetini getirir.
        
        Args:
            personel_id: Personel ID
            tarih: Sorgulanacak tarih (varsayılan: bugün)
            
        Returns:
            Dict: Özet bilgiler
        """
        if tarih is None:
            tarih = get_kktc_now().date()
        
        # Personelin yaptığı kontrolleri say
        kontroller = OdaDNDKontrol.query.join(OdaDNDKayit).filter(
            OdaDNDKontrol.kontrol_eden_id == personel_id,
            OdaDNDKayit.kayit_tarihi == tarih
        ).all()
        
        # Benzersiz odaları bul
        benzersiz_odalar = set()
        for k in kontroller:
            benzersiz_odalar.add(k.dnd_kayit.oda_id)
        
        return {
            'tarih': tarih.isoformat(),
            'toplam_kontrol': len(kontroller),
            'benzersiz_oda_sayisi': len(benzersiz_odalar),
            'kontrol_detaylari': [{
                'kontrol_id': k.id,
                'oda_id': k.dnd_kayit.oda_id,
                'kontrol_no': k.kontrol_no,
                'kontrol_zamani': k.kontrol_zamani.isoformat() if k.kontrol_zamani else None
            } for k in kontroller]
        }
    
    @staticmethod
    def gorev_ile_eslestir(oda_id: int, gorev_detay_id: int, tarih: Optional[date] = None) -> bool:
        """
        Mevcut DND kaydını görev detayı ile eşleştirir.
        
        Args:
            oda_id: Oda ID
            gorev_detay_id: Görev detay ID
            tarih: Tarih (varsayılan: bugün)
            
        Returns:
            bool: Eşleştirme başarılı mı
        """
        if tarih is None:
            tarih = get_kktc_now().date()
        
        try:
            dnd_kayit = OdaDNDKayit.query.filter_by(
                oda_id=oda_id,
                kayit_tarihi=tarih
            ).first()
            
            if dnd_kayit and not dnd_kayit.gorev_detay_id:
                dnd_kayit.gorev_detay_id = gorev_detay_id
                dnd_kayit.guncelleme_tarihi = get_kktc_now()
                db.session.commit()
                return True
            
            return False
            
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def iptal_et(dnd_kayit_id: int, personel_id: int, sebep: Optional[str] = None) -> Dict:
        """
        DND kaydını iptal eder.
        
        Args:
            dnd_kayit_id: DND kayıt ID
            personel_id: İptal eden personel ID
            sebep: İptal sebebi
            
        Returns:
            Dict: İşlem sonucu
        """
        try:
            dnd_kayit = db.session.get(OdaDNDKayit, dnd_kayit_id)
            if not dnd_kayit:
                raise DNDServiceError("DND kaydı bulunamadı")
            
            if dnd_kayit.durum == DNDService.DURUM_TAMAMLANDI:
                raise DNDServiceError("Tamamlanmış DND kaydı iptal edilemez")
            
            dnd_kayit.durum = DNDService.DURUM_IPTAL
            dnd_kayit.guncelleme_tarihi = get_kktc_now()
            
            # İptal notu ekle
            iptal_kontrol = OdaDNDKontrol(
                dnd_kayit_id=dnd_kayit.id,
                kontrol_no=0,  # 0 = iptal kaydı
                kontrol_eden_id=personel_id,
                kontrol_zamani=get_kktc_now(),
                notlar=f'İPTAL: {sebep}' if sebep else 'İPTAL'
            )
            db.session.add(iptal_kontrol)
            
            db.session.commit()
            
            return {
                'success': True,
                'mesaj': 'DND kaydı iptal edildi'
            }
            
        except DNDServiceError:
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            raise DNDServiceError(f"DND iptal hatası: {str(e)}")
