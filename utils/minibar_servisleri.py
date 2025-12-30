"""
Minibar Servisleri - Setup Bazlı Minibar Kontrol Sistemi
Tarih: 2025-01-17
Açıklama: Setup bazlı minibar kontrol için iş mantığı fonksiyonları
"""

from models import (
    db, Oda, OdaTipi, Setup, SetupIcerik, Urun,
    MinibarIslem, MinibarIslemDetay, PersonelZimmetDetay,
    PersonelZimmet
)
from datetime import datetime, timezone
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
from sqlalchemy import desc
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class ZimmetStokYetersizError(Exception):
    """Zimmet stoğu yetersiz hatası"""
    def __init__(self, urun_adi, mevcut, gereken):
        self.urun_adi = urun_adi
        self.mevcut = mevcut
        self.gereken = gereken
        super().__init__(
            f"Zimmetinizde yeterli {urun_adi} bulunmamaktadır. "
            f"Mevcut: {mevcut}, Gereken: {gereken}"
        )


class OdaTipiNotFoundError(Exception):
    """Oda tipi bulunamadı hatası"""
    def __init__(self, oda_no):
        self.oda_no = oda_no
        super().__init__(f"Oda {oda_no} için oda tipi tanımlanmamış")


class SetupNotFoundError(Exception):
    """Setup bulunamadı hatası"""
    def __init__(self, oda_tipi_adi):
        self.oda_tipi_adi = oda_tipi_adi
        super().__init__(f"{oda_tipi_adi} oda tipi için setup tanımlanmamış")


# ============================================================================
# SERVIS FONKSIYONLARI
# ============================================================================

def oda_setup_durumu_getir(oda_id):
    """
    Odanın tüm setup'larını ve mevcut durumlarını getirir (Otel bazlı)
    
    Args:
        oda_id (int): Oda ID
        
    Returns:
        dict: Oda bilgileri, setup'lar ve ürün durumları
        
    Raises:
        OdaTipiNotFoundError: Oda tipi tanımlı değilse
        SetupNotFoundError: Setup tanımlı değilse
    """
    try:
        from models import Kat, oda_tipi_setup
        from sqlalchemy import and_
        
        # Odayı getir
        oda = Oda.query.get_or_404(oda_id)
        
        # Oda tipi kontrolü
        if not oda.oda_tipi_id:
            raise OdaTipiNotFoundError(oda.oda_no)
        
        oda_tipi = OdaTipi.query.get(oda.oda_tipi_id)
        if not oda_tipi:
            raise OdaTipiNotFoundError(oda.oda_no)
        
        # Odanın otelini bul (kat üzerinden)
        kat = Kat.query.get(oda.kat_id)
        if not kat:
            raise OdaTipiNotFoundError(oda.oda_no)
        
        otel_id = kat.otel_id
        
        # Otel bazlı setup'ları getir
        setup_rows = db.session.execute(
            db.select(oda_tipi_setup.c.setup_id).where(
                and_(
                    oda_tipi_setup.c.otel_id == otel_id,
                    oda_tipi_setup.c.oda_tipi_id == oda_tipi.id
                )
            )
        ).fetchall()
        
        setup_ids = [row[0] for row in setup_rows]
        
        # Setup'ları getir
        if setup_ids:
            setuplar = Setup.query.filter(Setup.id.in_(setup_ids), Setup.aktif == True).all()
        else:
            # Otel bazlı atama yoksa, geriye uyumluluk için global ilişkiyi kullan
            setuplar = [s for s in oda_tipi.setuplar if s.aktif]
        
        if not setuplar:
            raise SetupNotFoundError(oda_tipi.ad)
        
        # Her setup için ürün durumlarını hesapla
        setup_listesi = []
        dolap_ici_setuplar = []
        dolap_disi_setuplar = []
        
        for setup in setuplar:
            if not setup.aktif:
                continue
                
            # Setup içeriğini getir
            icerikler = SetupIcerik.query.filter_by(
                setup_id=setup.id
            ).join(Urun).filter(Urun.aktif == True).all()
            
            urun_listesi = []
            
            for icerik in icerikler:
                # Son minibar işleminden mevcut miktarı bul
                son_islem_detay = MinibarIslemDetay.query.join(
                    MinibarIslem
                ).filter(
                    MinibarIslem.oda_id == oda_id,
                    MinibarIslemDetay.urun_id == icerik.urun_id
                ).order_by(desc(MinibarIslem.islem_tarihi)).first()
                
                mevcut_miktar = 0
                ekstra_miktar = 0
                
                if son_islem_detay:
                    mevcut_miktar = son_islem_detay.bitis_stok or 0
                    ekstra_miktar = son_islem_detay.ekstra_miktar or 0
                
                # Durum hesapla
                setup_miktari = icerik.adet
                toplam_miktar = mevcut_miktar + ekstra_miktar
                
                if toplam_miktar < setup_miktari:
                    durum = 'eksik'
                    eksik_miktar = setup_miktari - toplam_miktar
                    fazla_miktar = 0
                elif ekstra_miktar > 0:
                    durum = 'ekstra_var'
                    eksik_miktar = 0
                    fazla_miktar = ekstra_miktar
                else:
                    durum = 'tam'
                    eksik_miktar = 0
                    fazla_miktar = 0
                
                urun_listesi.append({
                    'urun_id': icerik.urun_id,
                    'urun_adi': icerik.urun.urun_adi,
                    'birim': icerik.urun.birim,
                    'setup_miktari': setup_miktari,
                    'mevcut_miktar': mevcut_miktar,
                    'ekstra_miktar': ekstra_miktar,
                    'durum': durum,
                    'eksik_miktar': eksik_miktar,
                    'fazla_miktar': fazla_miktar
                })
            
            # Dolap içi ise dolap sayısı kadar ayrı ayrı ekle
            if setup.dolap_ici:
                dolap_sayisi = oda_tipi.dolap_sayisi or 1
                for dolap_no in range(1, dolap_sayisi + 1):
                    dolap_ici_setuplar.append({
                        'setup_id': setup.id,
                        'setup_adi': f"{setup.ad} - Dolap {dolap_no}",
                        'dolap_ici': True,
                        'dolap_no': dolap_no,
                        'dolap_sayisi': dolap_sayisi,
                        'urunler': urun_listesi
                    })
            else:
                # Dolap dışı tek sefer ekle
                dolap_disi_setuplar.append({
                    'setup_id': setup.id,
                    'setup_adi': setup.ad,
                    'dolap_ici': False,
                    'dolap_no': 0,
                    'dolap_sayisi': 0,
                    'urunler': urun_listesi
                })
        
        # Önce dolap içi, sonra dolap dışı
        setup_listesi = dolap_ici_setuplar + dolap_disi_setuplar
        
        return {
            'oda': {
                'id': oda.id,
                'oda_no': oda.oda_no,
                'oda_tipi': oda_tipi.ad,
                'oda_tipi_id': oda_tipi.id,
                'dolap_sayisi': oda_tipi.dolap_sayisi or 0
            },
            'setuplar': setup_listesi
        }
        
    except (OdaTipiNotFoundError, SetupNotFoundError):
        raise
    except Exception as e:
        logger.error(f"Oda setup durumu getirme hatası: {e}")
        raise


def tuketim_hesapla(oda_id, urun_id, setup_miktari, eklenen_miktar):
    """
    Tüketim miktarını hesaplar
    
    Args:
        oda_id (int): Oda ID
        urun_id (int): Ürün ID
        setup_miktari (int): Setup'ta olması gereken miktar
        eklenen_miktar (int): Eklenen miktar
        
    Returns:
        int: Tüketim miktarı
    """
    try:
        # Son durumu getir
        son_islem_detay = MinibarIslemDetay.query.join(
            MinibarIslem
        ).filter(
            MinibarIslem.oda_id == oda_id,
            MinibarIslemDetay.urun_id == urun_id
        ).order_by(desc(MinibarIslem.islem_tarihi)).first()
        
        mevcut_miktar = 0
        if son_islem_detay:
            mevcut_miktar = son_islem_detay.bitis_stok or 0
        
        # Tüketim = (Setup miktarı - Mevcut miktar)
        # Eklenen miktar tüketimi karşılar
        tuketim = max(0, setup_miktari - mevcut_miktar)
        
        # Eklenen miktar tüketimden fazlaysa, tüketim = eklenen miktar
        tuketim = min(tuketim, eklenen_miktar)
        
        return tuketim
        
    except Exception as e:
        logger.error(f"Tüketim hesaplama hatası: {e}")
        raise


def zimmet_stok_kontrol(personel_id, urun_id, miktar):
    """
    Kat sorumlusunun zimmetinde yeterli stok var mı kontrol eder
    
    YENİ SİSTEM: Otel bazlı ortak zimmet deposundan kontrol eder.
    Personelin bağlı olduğu otelin zimmet deposunu kullanır.
    
    Args:
        personel_id (int): Personel ID
        urun_id (int): Ürün ID
        miktar (int): Gereken miktar
        
    Returns:
        tuple: (bool, int, OtelZimmetStok) - (Yeterli mi, Mevcut miktar, Otel zimmet stok)
        
    Raises:
        ZimmetStokYetersizError: Stok yetersizse
    """
    from models import Kullanici, OtelZimmetStok
    from utils.otel_zimmet_servisleri import OtelZimmetServisi, OtelZimmetStokYetersizError
    
    try:
        # Personelin otel_id'sini bul
        personel = Kullanici.query.get(personel_id)
        if not personel or not personel.otel_id:
            urun = Urun.query.get(urun_id)
            raise ZimmetStokYetersizError(
                urun.urun_adi if urun else 'Ürün',
                0,
                miktar
            )
        
        otel_id = personel.otel_id
        
        # Otel zimmet deposundan kontrol et
        try:
            yeterli, mevcut, otel_stok = OtelZimmetServisi.stok_kontrol(otel_id, urun_id, miktar)
            return yeterli, mevcut, otel_stok
        except OtelZimmetStokYetersizError as e:
            # Otel bazlı hatayı mevcut hata tipine çevir
            raise ZimmetStokYetersizError(e.urun_adi, e.mevcut, e.gereken)
        
    except ZimmetStokYetersizError:
        raise
    except Exception as e:
        logger.error(f"Zimmet stok kontrol hatası: {e}")
        raise


def zimmet_stok_dusu(personel_id, urun_id, miktar, zimmet_detay_id=None, referans_id=None):
    """
    Zimmet stoğundan düşüş yapar
    
    YENİ SİSTEM: Otel bazlı ortak zimmet deposundan düşer ve kullanım kaydı oluşturur.
    
    Args:
        personel_id (int): Personel ID
        urun_id (int): Ürün ID
        miktar (int): Düşülecek miktar
        zimmet_detay_id (int, optional): Eski sistem için - artık kullanılmıyor
        referans_id (int, optional): MinibarIslem ID referansı
        
    Returns:
        OtelZimmetStok: Güncellenen otel zimmet stok
        
    Raises:
        ZimmetStokYetersizError: Stok yetersizse
    """
    from models import Kullanici
    from utils.otel_zimmet_servisleri import OtelZimmetServisi, OtelZimmetStokYetersizError
    
    try:
        # Personelin otel_id'sini bul
        personel = Kullanici.query.get(personel_id)
        if not personel or not personel.otel_id:
            raise ZimmetStokYetersizError('Ürün', 0, miktar)
        
        otel_id = personel.otel_id
        
        # Otel zimmet deposundan düş
        try:
            otel_stok, kullanim = OtelZimmetServisi.stok_dusu(
                otel_id=otel_id,
                urun_id=urun_id,
                miktar=miktar,
                personel_id=personel_id,
                islem_tipi='minibar_kullanim',
                referans_id=referans_id,
                aciklama=f"Minibar kullanımı - Personel: {personel.ad} {personel.soyad}"
            )
            return otel_stok
        except OtelZimmetStokYetersizError as e:
            raise ZimmetStokYetersizError(e.urun_adi, e.mevcut, e.gereken)
        
    except ZimmetStokYetersizError:
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f"Zimmet stok düşüş hatası: {e}")
        raise


def minibar_stok_guncelle(oda_id, urun_id, yeni_miktar, ekstra_miktar=0):
    """
    Minibar stok miktarını günceller
    
    Args:
        oda_id (int): Oda ID
        urun_id (int): Ürün ID
        yeni_miktar (int): Yeni miktar
        ekstra_miktar (int): Ekstra miktar
        
    Returns:
        dict: Güncelleme sonucu
    """
    try:
        # Son durumu getir
        son_islem_detay = MinibarIslemDetay.query.join(
            MinibarIslem
        ).filter(
            MinibarIslem.oda_id == oda_id,
            MinibarIslemDetay.urun_id == urun_id
        ).order_by(desc(MinibarIslem.islem_tarihi)).first()
        
        baslangic_stok = 0
        if son_islem_detay:
            # Önceki işlemin bitiş stoğu
            baslangic_stok = son_islem_detay.bitis_stok or 0
        else:
            # İlk işlem - Setup miktarını bul
            oda = Oda.query.get(oda_id)
            if oda and oda.oda_tipi_id:
                oda_tipi = OdaTipi.query.get(oda.oda_tipi_id)
                if oda_tipi:
                    # Oda tipinin setup'larından ürünü bul
                    for setup in oda_tipi.setuplar:
                        setup_icerik = SetupIcerik.query.filter_by(
                            setup_id=setup.id,
                            urun_id=urun_id
                        ).first()
                        if setup_icerik:
                            baslangic_stok = setup_icerik.adet
                            break
        
        return {
            'baslangic_stok': baslangic_stok,
            'bitis_stok': yeni_miktar,
            'ekstra_miktar': ekstra_miktar
        }
        
    except Exception as e:
        logger.error(f"Minibar stok güncelleme hatası: {e}")
        raise


def tuketim_kaydet(oda_id, urun_id, miktar, personel_id, islem_tipi='setup_kontrol',
                   eklenen_miktar=0, ekstra_miktar=0, zimmet_detay_id=None):
    """
    Tüketimi minibar_islem tablosuna kaydeder
    
    Args:
        oda_id (int): Oda ID
        urun_id (int): Ürün ID
        miktar (int): Tüketim miktarı
        personel_id (int): Personel ID
        islem_tipi (str): İşlem tipi (setup_kontrol, ekstra_ekleme, ekstra_tuketim)
        eklenen_miktar (int): Eklenen miktar
        ekstra_miktar (int): Ekstra miktar
        zimmet_detay_id (int, optional): Zimmet detay ID
        
    Returns:
        MinibarIslem: Oluşturulan işlem kaydı
    """
    try:
        # Stok durumunu getir
        stok_durumu = minibar_stok_guncelle(oda_id, urun_id, 
                                           eklenen_miktar, ekstra_miktar)
        
        # MinibarIslem kaydı oluştur
        islem = MinibarIslem(
            oda_id=oda_id,
            personel_id=personel_id,
            islem_tipi=islem_tipi,
            islem_tarihi=get_kktc_now(),
            aciklama=f"{islem_tipi} işlemi"
        )
        db.session.add(islem)
        db.session.flush()  # ID'yi al
        
        # MinibarIslemDetay kaydı oluştur
        detay = MinibarIslemDetay(
            islem_id=islem.id,
            urun_id=urun_id,
            baslangic_stok=stok_durumu['baslangic_stok'],
            bitis_stok=stok_durumu['bitis_stok'],
            tuketim=miktar,
            eklenen_miktar=eklenen_miktar,
            ekstra_miktar=ekstra_miktar,
            zimmet_detay_id=zimmet_detay_id
        )
        db.session.add(detay)
        db.session.commit()
        
        return islem
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Tüketim kaydetme hatası: {e}")
        raise

