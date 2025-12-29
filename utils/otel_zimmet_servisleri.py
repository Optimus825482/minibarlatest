"""
Otel Bazlı Zimmet Stok Servisleri
Tarih: 2025-12-29
Açıklama: Otel bazlı ortak zimmet deposu yönetimi için servis fonksiyonları

Yeni Sistem:
- Her otel için tek bir ortak zimmet deposu (otel_zimmet_stok)
- Tüm kat sorumluları aynı depodan kullanır
- Personel bazlı kullanım takibi (personel_zimmet_kullanim)
- Otel ve personel bazlı raporlama
"""

from models import (
    db, OtelZimmetStok, PersonelZimmetKullanim, 
    Kullanici, Urun, Otel, PersonelZimmet, PersonelZimmetDetay
)
from datetime import datetime
from sqlalchemy import func, desc
from sqlalchemy.exc import IntegrityError
import pytz
import logging

logger = logging.getLogger(__name__)

KKTC_TZ = pytz.timezone('Europe/Nicosia')

def get_kktc_now():
    return datetime.now(KKTC_TZ)


class OtelZimmetStokYetersizError(Exception):
    """Otel zimmet stoğu yetersiz hatası"""
    def __init__(self, urun_adi, mevcut, gereken, otel_adi=None):
        self.urun_adi = urun_adi
        self.mevcut = mevcut
        self.gereken = gereken
        self.otel_adi = otel_adi
        msg = f"Otel zimmet deposunda yeterli {urun_adi} bulunmamaktadır. Mevcut: {mevcut}, Gereken: {gereken}"
        if otel_adi:
            msg = f"[{otel_adi}] " + msg
        super().__init__(msg)


class OtelZimmetServisi:
    """Otel bazlı zimmet stok yönetimi servisi"""

    @staticmethod
    def get_otel_zimmet_stok(otel_id: int, urun_id: int) -> OtelZimmetStok:
        """
        Belirli bir otel ve ürün için zimmet stoğunu getir
        
        Args:
            otel_id: Otel ID
            urun_id: Ürün ID
            
        Returns:
            OtelZimmetStok veya None
        """
        return OtelZimmetStok.query.filter_by(
            otel_id=otel_id,
            urun_id=urun_id
        ).first()
    
    @staticmethod
    def get_veya_olustur_otel_zimmet_stok(otel_id: int, urun_id: int) -> OtelZimmetStok:
        """
        Otel zimmet stoğunu getir, yoksa oluştur
        
        Args:
            otel_id: Otel ID
            urun_id: Ürün ID
            
        Returns:
            OtelZimmetStok
        """
        stok = OtelZimmetStok.query.filter_by(
            otel_id=otel_id,
            urun_id=urun_id
        ).first()
        
        if not stok:
            stok = OtelZimmetStok(
                otel_id=otel_id,
                urun_id=urun_id,
                toplam_miktar=0,
                kullanilan_miktar=0,
                kalan_miktar=0
            )
            db.session.add(stok)
            try:
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                stok = OtelZimmetStok.query.filter_by(
                    otel_id=otel_id,
                    urun_id=urun_id
                ).first()
        
        return stok
    
    @staticmethod
    def get_otel_tum_zimmet_stoklari(otel_id: int, sadece_stoklu: bool = False):
        """
        Bir otelin tüm zimmet stoklarını getir
        
        Args:
            otel_id: Otel ID
            sadece_stoklu: True ise sadece kalan_miktar > 0 olanları getir
            
        Returns:
            List[OtelZimmetStok]
        """
        query = OtelZimmetStok.query.filter_by(otel_id=otel_id)
        
        if sadece_stoklu:
            query = query.filter(OtelZimmetStok.kalan_miktar > 0)
        
        return query.join(Urun).order_by(Urun.urun_adi).all()

    @staticmethod
    def stok_kontrol(otel_id: int, urun_id: int, miktar: int) -> tuple:
        """
        Otel zimmet deposunda yeterli stok var mı kontrol eder
        
        Args:
            otel_id: Otel ID
            urun_id: Ürün ID
            miktar: Gereken miktar
            
        Returns:
            tuple: (yeterli_mi: bool, mevcut_miktar: int, otel_zimmet_stok: OtelZimmetStok)
            
        Raises:
            OtelZimmetStokYetersizError: Stok yetersizse
        """
        stok = OtelZimmetStok.query.filter_by(
            otel_id=otel_id,
            urun_id=urun_id
        ).first()
        
        if not stok:
            urun = Urun.query.get(urun_id)
            otel = Otel.query.get(otel_id)
            raise OtelZimmetStokYetersizError(
                urun.urun_adi if urun else 'Ürün',
                0,
                miktar,
                otel.ad if otel else None
            )
        
        if stok.kalan_miktar < miktar:
            urun = Urun.query.get(urun_id)
            otel = Otel.query.get(otel_id)
            raise OtelZimmetStokYetersizError(
                urun.urun_adi if urun else 'Ürün',
                stok.kalan_miktar,
                miktar,
                otel.ad if otel else None
            )
        
        return True, stok.kalan_miktar, stok
    
    @staticmethod
    def stok_dusu(
        otel_id: int, 
        urun_id: int, 
        miktar: int, 
        personel_id: int,
        islem_tipi: str = 'minibar_kullanim',
        referans_id: int = None,
        aciklama: str = None,
        olusturan_id: int = None
    ) -> tuple:
        """
        Otel zimmet deposundan stok düşer ve kullanım kaydı oluşturur
        
        Args:
            otel_id: Otel ID
            urun_id: Ürün ID
            miktar: Düşülecek miktar
            personel_id: Kullanan personel ID
            islem_tipi: İşlem tipi (minibar_kullanim, iade, duzeltme)
            referans_id: İlgili işlem ID (MinibarIslem ID vb.)
            aciklama: Açıklama
            olusturan_id: İşlemi yapan kullanıcı ID
            
        Returns:
            tuple: (OtelZimmetStok, PersonelZimmetKullanim)
            
        Raises:
            OtelZimmetStokYetersizError: Stok yetersizse
        """
        try:
            # Stok kontrolü
            _, _, stok = OtelZimmetServisi.stok_kontrol(otel_id, urun_id, miktar)
            
            # Stok düş
            stok.kullanilan_miktar += miktar
            stok.kalan_miktar -= miktar
            stok.son_guncelleme = get_kktc_now()
            
            # Kullanım kaydı oluştur
            kullanim = PersonelZimmetKullanim(
                otel_zimmet_stok_id=stok.id,
                personel_id=personel_id,
                urun_id=urun_id,
                kullanilan_miktar=miktar,
                islem_tipi=islem_tipi,
                referans_islem_id=referans_id,
                aciklama=aciklama,
                olusturan_id=olusturan_id or personel_id,
                islem_tarihi=get_kktc_now()
            )
            db.session.add(kullanim)
            db.session.commit()
            
            logger.info(
                f"Otel zimmet stok düşüşü: otel_id={otel_id}, urun_id={urun_id}, "
                f"miktar={miktar}, personel_id={personel_id}, kalan={stok.kalan_miktar}"
            )
            
            return stok, kullanim
            
        except OtelZimmetStokYetersizError:
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Otel zimmet stok düşüş hatası: {e}")
            raise
    
    @staticmethod
    def stok_ekle(
        otel_id: int,
        urun_id: int,
        miktar: int,
        aciklama: str = None
    ) -> OtelZimmetStok:
        """
        Otel zimmet deposuna stok ekler
        
        Args:
            otel_id: Otel ID
            urun_id: Ürün ID
            miktar: Eklenecek miktar
            aciklama: Açıklama
            
        Returns:
            OtelZimmetStok
        """
        try:
            stok = OtelZimmetServisi.get_veya_olustur_otel_zimmet_stok(otel_id, urun_id)
            
            stok.toplam_miktar += miktar
            stok.kalan_miktar += miktar
            stok.son_guncelleme = get_kktc_now()
            
            db.session.commit()
            
            logger.info(
                f"Otel zimmet stok ekleme: otel_id={otel_id}, urun_id={urun_id}, "
                f"miktar={miktar}, yeni_toplam={stok.toplam_miktar}"
            )
            
            return stok
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Otel zimmet stok ekleme hatası: {e}")
            raise

    @staticmethod
    def stok_iade(
        otel_id: int,
        urun_id: int,
        miktar: int,
        personel_id: int,
        referans_id: int = None,
        aciklama: str = None,
        olusturan_id: int = None
    ) -> tuple:
        """
        Otel zimmet deposuna stok iade eder
        
        Args:
            otel_id: Otel ID
            urun_id: Ürün ID
            miktar: İade edilecek miktar
            personel_id: İade eden personel ID
            referans_id: İlgili işlem ID
            aciklama: Açıklama
            olusturan_id: İşlemi yapan kullanıcı ID
            
        Returns:
            tuple: (OtelZimmetStok, PersonelZimmetKullanim)
        """
        try:
            stok = OtelZimmetServisi.get_veya_olustur_otel_zimmet_stok(otel_id, urun_id)
            
            # İade işlemi - kullanılan miktarı azalt, kalan miktarı artır
            stok.kullanilan_miktar = max(0, stok.kullanilan_miktar - miktar)
            stok.kalan_miktar += miktar
            stok.son_guncelleme = get_kktc_now()
            
            # İade kaydı oluştur (negatif değil, islem_tipi ile ayırt edilir)
            kullanim = PersonelZimmetKullanim(
                otel_zimmet_stok_id=stok.id,
                personel_id=personel_id,
                urun_id=urun_id,
                kullanilan_miktar=miktar,
                islem_tipi='iade',
                referans_islem_id=referans_id,
                aciklama=aciklama or 'Zimmet iadesi',
                olusturan_id=olusturan_id or personel_id,
                islem_tarihi=get_kktc_now()
            )
            db.session.add(kullanim)
            db.session.commit()
            
            logger.info(
                f"Otel zimmet stok iade: otel_id={otel_id}, urun_id={urun_id}, "
                f"miktar={miktar}, personel_id={personel_id}"
            )
            
            return stok, kullanim
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Otel zimmet stok iade hatası: {e}")
            raise

    @staticmethod
    def get_personel_kullanim_ozeti(personel_id: int, otel_id: int = None) -> list:
        """
        Personelin zimmet kullanım özetini getir
        
        Args:
            personel_id: Personel ID
            otel_id: Otel ID (opsiyonel, belirtilmezse tüm oteller)
            
        Returns:
            List[dict]: Ürün bazlı kullanım özeti
        """
        query = db.session.query(
            Urun.id.label('urun_id'),
            Urun.urun_adi,
            func.sum(
                func.case(
                    (PersonelZimmetKullanim.islem_tipi != 'iade', PersonelZimmetKullanim.kullanilan_miktar),
                    else_=0
                )
            ).label('toplam_kullanim'),
            func.sum(
                func.case(
                    (PersonelZimmetKullanim.islem_tipi == 'iade', PersonelZimmetKullanim.kullanilan_miktar),
                    else_=0
                )
            ).label('toplam_iade'),
            func.count(PersonelZimmetKullanim.id).label('islem_sayisi')
        ).join(
            Urun, PersonelZimmetKullanim.urun_id == Urun.id
        ).filter(
            PersonelZimmetKullanim.personel_id == personel_id
        )
        
        if otel_id:
            query = query.join(
                OtelZimmetStok, PersonelZimmetKullanim.otel_zimmet_stok_id == OtelZimmetStok.id
            ).filter(OtelZimmetStok.otel_id == otel_id)
        
        query = query.group_by(Urun.id, Urun.urun_adi).order_by(Urun.urun_adi)
        
        return [
            {
                'urun_id': row.urun_id,
                'urun_adi': row.urun_adi,
                'toplam_kullanim': row.toplam_kullanim or 0,
                'toplam_iade': row.toplam_iade or 0,
                'net_kullanim': (row.toplam_kullanim or 0) - (row.toplam_iade or 0),
                'islem_sayisi': row.islem_sayisi
            }
            for row in query.all()
        ]
    
    @staticmethod
    def get_otel_kullanim_raporu(otel_id: int, baslangic_tarihi=None, bitis_tarihi=None) -> dict:
        """
        Otel bazlı zimmet kullanım raporu
        
        Args:
            otel_id: Otel ID
            baslangic_tarihi: Başlangıç tarihi (opsiyonel)
            bitis_tarihi: Bitiş tarihi (opsiyonel)
            
        Returns:
            dict: Rapor verisi
        """
        # Otel bilgisi
        otel = Otel.query.get(otel_id)
        if not otel:
            return None
        
        # Stok durumu
        stoklar = OtelZimmetStok.query.filter_by(otel_id=otel_id).all()
        
        toplam_stok = sum(s.toplam_miktar for s in stoklar)
        toplam_kullanilan = sum(s.kullanilan_miktar for s in stoklar)
        toplam_kalan = sum(s.kalan_miktar for s in stoklar)
        kritik_urunler = [s for s in stoklar if s.stok_durumu in ('kritik', 'stokout')]
        
        # Kullanım sorgusu
        kullanim_query = db.session.query(
            PersonelZimmetKullanim
        ).join(
            OtelZimmetStok, PersonelZimmetKullanim.otel_zimmet_stok_id == OtelZimmetStok.id
        ).filter(OtelZimmetStok.otel_id == otel_id)
        
        if baslangic_tarihi:
            kullanim_query = kullanim_query.filter(
                PersonelZimmetKullanim.islem_tarihi >= baslangic_tarihi
            )
        if bitis_tarihi:
            kullanim_query = kullanim_query.filter(
                PersonelZimmetKullanim.islem_tarihi <= bitis_tarihi
            )
        
        # Personel bazlı kullanım
        personel_kullanim = db.session.query(
            Kullanici.id.label('personel_id'),
            Kullanici.ad,
            Kullanici.soyad,
            func.sum(
                func.case(
                    (PersonelZimmetKullanim.islem_tipi != 'iade', PersonelZimmetKullanim.kullanilan_miktar),
                    else_=0
                )
            ).label('toplam_kullanim'),
            func.sum(
                func.case(
                    (PersonelZimmetKullanim.islem_tipi == 'iade', PersonelZimmetKullanim.kullanilan_miktar),
                    else_=0
                )
            ).label('toplam_iade')
        ).join(
            OtelZimmetStok, PersonelZimmetKullanim.otel_zimmet_stok_id == OtelZimmetStok.id
        ).join(
            Kullanici, PersonelZimmetKullanim.personel_id == Kullanici.id
        ).filter(OtelZimmetStok.otel_id == otel_id)
        
        if baslangic_tarihi:
            personel_kullanim = personel_kullanim.filter(
                PersonelZimmetKullanim.islem_tarihi >= baslangic_tarihi
            )
        if bitis_tarihi:
            personel_kullanim = personel_kullanim.filter(
                PersonelZimmetKullanim.islem_tarihi <= bitis_tarihi
            )
        
        personel_kullanim = personel_kullanim.group_by(
            Kullanici.id, Kullanici.ad, Kullanici.soyad
        ).all()

        return {
            'otel': {
                'id': otel.id,
                'ad': otel.ad
            },
            'stok_ozeti': {
                'toplam_stok': toplam_stok,
                'toplam_kullanilan': toplam_kullanilan,
                'toplam_kalan': toplam_kalan,
                'kullanim_orani': round((toplam_kullanilan / toplam_stok * 100), 1) if toplam_stok > 0 else 0,
                'urun_cesidi': len(stoklar),
                'kritik_urun_sayisi': len(kritik_urunler)
            },
            'kritik_urunler': [
                {
                    'urun_id': s.urun_id,
                    'urun_adi': s.urun.urun_adi if s.urun else 'Bilinmiyor',
                    'kalan_miktar': s.kalan_miktar,
                    'kritik_seviye': s.kritik_stok_seviyesi,
                    'durum': s.stok_durumu
                }
                for s in kritik_urunler
            ],
            'personel_kullanim': [
                {
                    'personel_id': p.personel_id,
                    'ad_soyad': f"{p.ad} {p.soyad}",
                    'toplam_kullanim': p.toplam_kullanim or 0,
                    'toplam_iade': p.toplam_iade or 0,
                    'net_kullanim': (p.toplam_kullanim or 0) - (p.toplam_iade or 0)
                }
                for p in personel_kullanim
            ]
        }
    
    @staticmethod
    def get_kritik_stok_urunleri(otel_id: int = None) -> list:
        """
        Kritik stok seviyesindeki ürünleri getir
        
        Args:
            otel_id: Otel ID (opsiyonel, belirtilmezse tüm oteller)
            
        Returns:
            List[OtelZimmetStok]
        """
        query = OtelZimmetStok.query.filter(
            OtelZimmetStok.kalan_miktar <= OtelZimmetStok.kritik_stok_seviyesi
        )
        
        if otel_id:
            query = query.filter(OtelZimmetStok.otel_id == otel_id)
        
        return query.join(Urun).join(Otel).order_by(
            OtelZimmetStok.kalan_miktar
        ).all()


# =============================================================================
# WRAPPER FONKSİYONLAR - Mevcut sistemle uyumluluk için
# =============================================================================

def otel_zimmet_stok_kontrol(otel_id: int, urun_id: int, miktar: int):
    """
    Otel zimmet deposunda yeterli stok var mı kontrol eder
    Mevcut zimmet_stok_kontrol() fonksiyonunun otel bazlı versiyonu
    
    Args:
        otel_id: Otel ID
        urun_id: Ürün ID
        miktar: Gereken miktar
        
    Returns:
        tuple: (yeterli_mi, mevcut_miktar, otel_zimmet_stok)
        
    Raises:
        OtelZimmetStokYetersizError: Stok yetersizse
    """
    return OtelZimmetServisi.stok_kontrol(otel_id, urun_id, miktar)


def otel_zimmet_stok_dusu(
    otel_id: int,
    urun_id: int,
    miktar: int,
    personel_id: int,
    islem_tipi: str = 'minibar_kullanim',
    referans_id: int = None,
    aciklama: str = None
):
    """
    Otel zimmet deposundan stok düşer
    Mevcut zimmet_stok_dusu() fonksiyonunun otel bazlı versiyonu
    
    Args:
        otel_id: Otel ID
        urun_id: Ürün ID
        miktar: Düşülecek miktar
        personel_id: Kullanan personel ID
        islem_tipi: İşlem tipi
        referans_id: Referans işlem ID
        aciklama: Açıklama
        
    Returns:
        tuple: (OtelZimmetStok, PersonelZimmetKullanim)
    """
    return OtelZimmetServisi.stok_dusu(
        otel_id=otel_id,
        urun_id=urun_id,
        miktar=miktar,
        personel_id=personel_id,
        islem_tipi=islem_tipi,
        referans_id=referans_id,
        aciklama=aciklama
    )


def get_personel_otel_id(personel_id: int) -> int:
    """
    Personelin bağlı olduğu otel ID'sini getir
    
    Args:
        personel_id: Personel ID
        
    Returns:
        int: Otel ID veya None
    """
    personel = Kullanici.query.get(personel_id)
    if personel and personel.otel_id:
        return personel.otel_id
    return None


def get_kat_sorumlusu_zimmet_stoklari(personel_id: int) -> list:
    """
    Kat sorumlusunun erişebildiği otel zimmet stoklarını getir
    
    Args:
        personel_id: Personel ID
        
    Returns:
        List[dict]: Stok listesi
    """
    otel_id = get_personel_otel_id(personel_id)
    if not otel_id:
        return []
    
    stoklar = OtelZimmetServisi.get_otel_tum_zimmet_stoklari(otel_id, sadece_stoklu=True)
    
    # Personelin kendi kullanımlarını da ekle
    kullanim_ozeti = OtelZimmetServisi.get_personel_kullanim_ozeti(personel_id, otel_id)
    kullanim_dict = {k['urun_id']: k for k in kullanim_ozeti}
    
    return [
        {
            'urun_id': s.urun_id,
            'urun_adi': s.urun.urun_adi if s.urun else 'Bilinmiyor',
            'urun_kodu': s.urun.urun_kodu if s.urun else None,
            'birim': s.urun.birim if s.urun else 'Adet',
            'otel_stok': s.kalan_miktar,
            'kritik_seviye': s.kritik_stok_seviyesi,
            'stok_durumu': s.stok_durumu,
            'benim_kullanimim': kullanim_dict.get(s.urun_id, {}).get('net_kullanim', 0)
        }
        for s in stoklar
    ]


# =============================================================================
# MİGRASYON YARDIMCI FONKSİYONLARI
# =============================================================================

def migrate_personel_zimmet_to_otel_stok(otel_id: int, dry_run: bool = True) -> dict:
    """
    Mevcut personel zimmetlerini otel zimmet stokuna migrate eder
    
    Args:
        otel_id: Otel ID
        dry_run: True ise sadece simülasyon yapar, değişiklik yapmaz
        
    Returns:
        dict: Migration sonucu
    """
    result = {
        'otel_id': otel_id,
        'dry_run': dry_run,
        'islem_sayisi': 0,
        'urun_sayisi': 0,
        'toplam_miktar': 0,
        'hatalar': [],
        'detaylar': []
    }
    
    try:
        # Bu oteldeki tüm aktif zimmetleri bul
        zimmetler = PersonelZimmet.query.filter_by(
            otel_id=otel_id,
            durum='aktif'
        ).all()
        
        if not zimmetler:
            result['hatalar'].append(f"Otel {otel_id} için aktif zimmet bulunamadı")
            return result
        
        # Ürün bazlı toplam hesapla
        urun_toplamlari = {}
        
        for zimmet in zimmetler:
            for detay in zimmet.detaylar:
                urun_id = detay.urun_id
                kalan = detay.kalan_miktar if detay.kalan_miktar is not None else (detay.miktar - detay.kullanilan_miktar)
                
                if urun_id not in urun_toplamlari:
                    urun_toplamlari[urun_id] = {
                        'toplam_miktar': 0,
                        'kullanilan_miktar': 0,
                        'kalan_miktar': 0
                    }
                
                urun_toplamlari[urun_id]['toplam_miktar'] += detay.miktar
                urun_toplamlari[urun_id]['kullanilan_miktar'] += detay.kullanilan_miktar
                urun_toplamlari[urun_id]['kalan_miktar'] += kalan

        # Otel zimmet stokuna ekle/güncelle
        for urun_id, miktarlar in urun_toplamlari.items():
            urun = Urun.query.get(urun_id)
            urun_adi = urun.urun_adi if urun else f"Ürün #{urun_id}"
            
            result['detaylar'].append({
                'urun_id': urun_id,
                'urun_adi': urun_adi,
                'toplam_miktar': miktarlar['toplam_miktar'],
                'kullanilan_miktar': miktarlar['kullanilan_miktar'],
                'kalan_miktar': miktarlar['kalan_miktar']
            })
            
            if not dry_run:
                stok = OtelZimmetStok.query.filter_by(
                    otel_id=otel_id,
                    urun_id=urun_id
                ).first()
                
                if stok:
                    # Mevcut stoku güncelle
                    stok.toplam_miktar = miktarlar['toplam_miktar']
                    stok.kullanilan_miktar = miktarlar['kullanilan_miktar']
                    stok.kalan_miktar = miktarlar['kalan_miktar']
                    stok.son_guncelleme = get_kktc_now()
                else:
                    # Yeni stok oluştur
                    stok = OtelZimmetStok(
                        otel_id=otel_id,
                        urun_id=urun_id,
                        toplam_miktar=miktarlar['toplam_miktar'],
                        kullanilan_miktar=miktarlar['kullanilan_miktar'],
                        kalan_miktar=miktarlar['kalan_miktar']
                    )
                    db.session.add(stok)
            
            result['urun_sayisi'] += 1
            result['toplam_miktar'] += miktarlar['kalan_miktar']
        
        if not dry_run:
            db.session.commit()
            logger.info(f"Otel {otel_id} zimmet migration tamamlandı: {result['urun_sayisi']} ürün")
        
        result['islem_sayisi'] = len(zimmetler)
        
    except Exception as e:
        if not dry_run:
            db.session.rollback()
        result['hatalar'].append(str(e))
        logger.error(f"Migration hatası: {e}")
    
    return result


def sync_otel_zimmet_stok(otel_id: int) -> dict:
    """
    Otel zimmet stoğunu personel zimmetleriyle senkronize eder
    
    Args:
        otel_id: Otel ID
        
    Returns:
        dict: Senkronizasyon sonucu
    """
    return migrate_personel_zimmet_to_otel_stok(otel_id, dry_run=False)
