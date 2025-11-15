"""
Fiyatlandırma ve Karlılık Servisleri
Dinamik fiyat hesaplama, kampanya yönetimi ve karlılık analizi
"""

from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, or_, func
from models import (
    db, Urun, UrunTedarikciFiyat, OdaTipiSatisFiyati, 
    SezonFiyatlandirma, Kampanya, BedelsizLimit, BedelsizKullanimLog,
    MinibarIslemDetay, DonemselKarAnalizi, Tedarikci, UrunFiyatGecmisi
)
from utils.cache_manager import FiyatCache, KarCache
import logging

logger = logging.getLogger(__name__)


class FiyatYonetimServisi:
    """Fiyat yönetim ve hesaplama servisi"""

    @staticmethod
    def dinamik_fiyat_hesapla(
        urun_id: int,
        oda_id: int,
        oda_tipi_id: int,
        miktar: int = 1,
        tarih: Optional[datetime] = None
    ) -> Dict:
        """
        Dinamik fiyat hesaplama - Çok katmanlı fiyat algoritması
        
        Hesaplama Sırası:
        1. Alış fiyatı (tedarikçi)
        2. Oda tipi bazlı satış fiyatı
        3. Sezon çarpanı
        4. Kampanya indirimi
        5. Bedelsiz kontrol
        
        Args:
            urun_id: Ürün ID
            oda_id: Oda ID
            oda_tipi_id: Oda tipi ID (integer)
            miktar: Tüketim miktarı
            tarih: İşlem tarihi (None ise şimdi)
            
        Returns:
            dict: {
                'alis_fiyati': Decimal,
                'satis_fiyati': Decimal,
                'kar_tutari': Decimal,
                'kar_orani': float,
                'bedelsiz': bool,
                'bedelsiz_miktar': int,
                'ucretli_miktar': int,
                'uygulanan_kampanya': Optional[str],
                'kampanya_id': Optional[int],
                'sezon_carpani': Decimal,
                'detaylar': dict
            }
        """
        try:
            if tarih is None:
                tarih = datetime.now(timezone.utc)
            
            # Cache kontrolü - Bedelsiz hariç (oda bazlı değişir)
            if miktar == 1:  # Sadece birim fiyat için cache kullan
                cached_result = FiyatCache.get_dinamik_fiyat(urun_id, oda_id, tarih, miktar)
                if cached_result:
                    logger.debug(f"✅ Fiyat cache HIT: Ürün {urun_id}")
                    return cached_result
            
            # 1. Alış fiyatını getir
            alis_fiyati = FiyatYonetimServisi.guncel_alis_fiyati_getir(urun_id)
            if alis_fiyati is None:
                raise ValueError(f"Ürün {urun_id} için alış fiyatı bulunamadı")
            
            # 2. Oda tipi bazlı satış fiyatını getir
            satis_fiyati = FiyatYonetimServisi.oda_tipi_fiyati_getir(
                urun_id, oda_tipi_id, tarih
            )
            if satis_fiyati is None:
                # Varsayılan kar marjı %50
                satis_fiyati = alis_fiyati * Decimal('1.5')
            
            # 3. Sezon çarpanını uygula
            sezon_carpani, satis_fiyati = FiyatYonetimServisi.sezon_carpani_uygula(
                satis_fiyati, urun_id, tarih
            )
            
            # 4. Kampanya kontrolü ve uygulaması
            kampanya_sonuc = FiyatYonetimServisi.kampanya_uygula(
                satis_fiyati, urun_id, miktar, tarih
            )
            
            if kampanya_sonuc['uygulandı']:
                satis_fiyati = kampanya_sonuc['indirimli_fiyat']
                uygulanan_kampanya = kampanya_sonuc['kampanya_adi']
                kampanya_id = kampanya_sonuc['kampanya_id']
            else:
                uygulanan_kampanya = None
                kampanya_id = None
            
            # 5. Bedelsiz limit kontrolü
            bedelsiz_miktar, ucretli_miktar = FiyatYonetimServisi.bedelsiz_kontrol(
                oda_id, urun_id, miktar
            )
            
            # Toplam tutarları hesapla
            toplam_alis = alis_fiyati * miktar
            toplam_satis = (satis_fiyati * ucretli_miktar)  # Sadece ücretli miktar
            kar_tutari = toplam_satis - toplam_alis
            
            # Kar oranı hesapla (sıfıra bölme kontrolü)
            if toplam_alis > 0:
                kar_orani = float((kar_tutari / toplam_alis) * 100)
            else:
                kar_orani = 0.0
            
            result = {
                'alis_fiyati': alis_fiyati,
                'satis_fiyati': satis_fiyati,
                'kar_tutari': kar_tutari,
                'kar_orani': round(kar_orani, 2),
                'bedelsiz': bedelsiz_miktar > 0,
                'bedelsiz_miktar': bedelsiz_miktar,
                'ucretli_miktar': ucretli_miktar,
                'uygulanan_kampanya': uygulanan_kampanya,
                'kampanya_id': kampanya_id,
                'sezon_carpani': sezon_carpani,
                'detaylar': {
                    'toplam_alis': toplam_alis,
                    'toplam_satis': toplam_satis,
                    'birim_alis': alis_fiyati,
                    'birim_satis': satis_fiyati
                }
            }
            
            # Cache'e kaydet (sadece birim fiyat için)
            if miktar == 1:
                FiyatCache.set_dinamik_fiyat(urun_id, result, oda_id, tarih)
                logger.debug(f"✅ Fiyat cache SET: Ürün {urun_id}")
            
            return result
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"Dinamik fiyat hesaplama hatası: {str(e)}")

    @staticmethod
    def guncel_alis_fiyati_getir(
        urun_id: int,
        tedarikci_id: Optional[int] = None
    ) -> Optional[Decimal]:
        """
        Güncel alış fiyatını getir
        
        Args:
            urun_id: Ürün ID
            tedarikci_id: Tedarikçi ID (None ise en uygun tedarikçi)
            
        Returns:
            Decimal: Alış fiyatı veya None
        """
        try:
            simdi = datetime.now(timezone.utc)
            
            query = UrunTedarikciFiyat.query.filter(
                UrunTedarikciFiyat.urun_id == urun_id,
                UrunTedarikciFiyat.aktif == True,
                UrunTedarikciFiyat.baslangic_tarihi <= simdi
            ).filter(
                or_(
                    UrunTedarikciFiyat.bitis_tarihi.is_(None),
                    UrunTedarikciFiyat.bitis_tarihi >= simdi
                )
            )
            
            if tedarikci_id:
                query = query.filter(UrunTedarikciFiyat.tedarikci_id == tedarikci_id)
            
            # En düşük fiyatlı tedarikçiyi seç
            fiyat_kaydi = query.order_by(UrunTedarikciFiyat.alis_fiyati.asc()).first()
            
            if fiyat_kaydi:
                return fiyat_kaydi.alis_fiyati
            
            return None
            
        except Exception as e:
            raise Exception(f"Alış fiyatı getirme hatası: {str(e)}")

    @staticmethod
    def en_uygun_tedarikci_bul(urun_id: int) -> Optional[Dict]:
        """
        En uygun tedarikçiyi bul (en düşük fiyat)
        
        Args:
            urun_id: Ürün ID
            
        Returns:
            dict: Tedarikçi bilgileri veya None
        """
        try:
            simdi = datetime.now(timezone.utc)
            
            fiyat_kaydi = UrunTedarikciFiyat.query.filter(
                UrunTedarikciFiyat.urun_id == urun_id,
                UrunTedarikciFiyat.aktif == True,
                UrunTedarikciFiyat.baslangic_tarihi <= simdi
            ).filter(
                or_(
                    UrunTedarikciFiyat.bitis_tarihi.is_(None),
                    UrunTedarikciFiyat.bitis_tarihi >= simdi
                )
            ).order_by(
                UrunTedarikciFiyat.alis_fiyati.asc()
            ).first()
            
            if fiyat_kaydi:
                return {
                    'tedarikci_id': fiyat_kaydi.tedarikci_id,
                    'tedarikci_adi': fiyat_kaydi.tedarikci.tedarikci_adi,
                    'alis_fiyati': fiyat_kaydi.alis_fiyati,
                    'minimum_miktar': fiyat_kaydi.minimum_miktar
                }
            
            return None
            
        except Exception as e:
            raise Exception(f"Tedarikçi bulma hatası: {str(e)}")

    @staticmethod
    def fiyat_guncelle(
        urun_id: int,
        yeni_fiyat: Decimal,
        degisiklik_tipi: str,
        kullanici_id: int,
        sebep: Optional[str] = None
    ) -> bool:
        """
        Fiyat güncelleme ve geçmiş kaydı
        
        Args:
            urun_id: Ürün ID
            yeni_fiyat: Yeni fiyat
            degisiklik_tipi: 'alis_fiyati', 'satis_fiyati', 'kampanya'
            kullanici_id: İşlemi yapan kullanıcı
            sebep: Değişiklik sebebi
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            # Eski fiyatı al
            if degisiklik_tipi == 'alis_fiyati':
                eski_fiyat = FiyatYonetimServisi.guncel_alis_fiyati_getir(urun_id)
            else:
                # Satış fiyatı için varsayılan oda tipinden al
                oda_fiyat = OdaTipiSatisFiyati.query.filter_by(
                    urun_id=urun_id,
                    aktif=True
                ).first()
                eski_fiyat = oda_fiyat.satis_fiyati if oda_fiyat else None
            
            # Fiyat geçmişi kaydı oluştur
            gecmis = UrunFiyatGecmisi(
                urun_id=urun_id,
                eski_fiyat=eski_fiyat,
                yeni_fiyat=yeni_fiyat,
                degisiklik_tipi=degisiklik_tipi,
                degisiklik_sebebi=sebep,
                olusturan_id=kullanici_id
            )
            
            db.session.add(gecmis)
            
            # ✅ URUNLER TABLOSUNU GUNCELLE
            if degisiklik_tipi == 'alis_fiyati':
                urun = Urun.query.get(urun_id)
                if urun:
                    urun.alis_fiyati = yeni_fiyat
                    logger.info(f"✅ Ürün {urun_id} alış fiyatı güncellendi: {yeni_fiyat}")
            
            db.session.commit()
            
            # Cache invalidation - Fiyat değiştiğinde cache'i temizle
            FiyatCache.invalidate_urun_fiyat(urun_id)
            logger.info(f"✅ Ürün {urun_id} fiyat cache'i temizlendi")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Fiyat güncelleme hatası: {str(e)}")

    @staticmethod
    def oda_tipi_fiyati_getir(
        urun_id: int,
        oda_tipi_id: int,
        tarih: Optional[datetime] = None
    ) -> Optional[Decimal]:
        """
        Oda tipi bazlı satış fiyatını getir
        
        Args:
            urun_id: Ürün ID
            oda_tipi_id: Oda tipi ID (integer)
            tarih: Tarih (None ise şimdi)
            
        Returns:
            Decimal: Satış fiyatı veya None
        """
        try:
            if tarih is None:
                tarih = datetime.now(timezone.utc)
            
            fiyat_kaydi = OdaTipiSatisFiyati.query.filter(
                OdaTipiSatisFiyati.urun_id == urun_id,
                OdaTipiSatisFiyati.oda_tipi_id == oda_tipi_id,
                OdaTipiSatisFiyati.aktif == True,
                OdaTipiSatisFiyati.baslangic_tarihi <= tarih
            ).filter(
                or_(
                    OdaTipiSatisFiyati.bitis_tarihi.is_(None),
                    OdaTipiSatisFiyati.bitis_tarihi >= tarih
                )
            ).first()
            
            if fiyat_kaydi:
                return fiyat_kaydi.satis_fiyati
            
            return None
            
        except Exception as e:
            raise Exception(f"Oda tipi fiyatı getirme hatası: {str(e)}")

    @staticmethod
    def sezon_carpani_uygula(
        fiyat: Decimal,
        urun_id: int,
        tarih: datetime
    ) -> Tuple[Decimal, Decimal]:
        """
        Sezon çarpanını uygula
        
        Args:
            fiyat: Temel fiyat
            urun_id: Ürün ID
            tarih: Tarih
            
        Returns:
            tuple: (çarpan, yeni_fiyat)
        """
        try:
            tarih_date = tarih.date() if isinstance(tarih, datetime) else tarih
            
            # Ürün bazlı sezon çarpanı
            sezon = SezonFiyatlandirma.query.filter(
                SezonFiyatlandirma.urun_id == urun_id,
                SezonFiyatlandirma.aktif == True,
                SezonFiyatlandirma.baslangic_tarihi <= tarih_date,
                SezonFiyatlandirma.bitis_tarihi >= tarih_date
            ).first()
            
            # Genel sezon çarpanı (tüm ürünler için)
            if not sezon:
                sezon = SezonFiyatlandirma.query.filter(
                    SezonFiyatlandirma.urun_id.is_(None),
                    SezonFiyatlandirma.aktif == True,
                    SezonFiyatlandirma.baslangic_tarihi <= tarih_date,
                    SezonFiyatlandirma.bitis_tarihi >= tarih_date
                ).first()
            
            if sezon:
                carpan = sezon.fiyat_carpani
                yeni_fiyat = fiyat * carpan
                return (carpan, yeni_fiyat)
            
            # Sezon bulunamadı, çarpan 1.0
            return (Decimal('1.0'), fiyat)
            
        except Exception as e:
            raise Exception(f"Sezon çarpanı uygulama hatası: {str(e)}")

    @staticmethod
    def kampanya_uygula(
        fiyat: Decimal,
        urun_id: int,
        miktar: int,
        tarih: datetime
    ) -> Dict:
        """
        Kampanya indirimini uygula
        
        Args:
            fiyat: Temel fiyat
            urun_id: Ürün ID
            miktar: Miktar
            tarih: Tarih
            
        Returns:
            dict: {
                'uygulandı': bool,
                'kampanya_id': Optional[int],
                'kampanya_adi': Optional[str],
                'indirim_tutari': Decimal,
                'indirimli_fiyat': Decimal
            }
        """
        try:
            # Aktif kampanyaları bul
            kampanya = Kampanya.query.filter(
                Kampanya.urun_id == urun_id,
                Kampanya.aktif == True,
                Kampanya.baslangic_tarihi <= tarih,
                Kampanya.bitis_tarihi >= tarih,
                Kampanya.min_siparis_miktari <= miktar
            ).filter(
                or_(
                    Kampanya.max_kullanim_sayisi.is_(None),
                    Kampanya.kullanilan_sayisi < Kampanya.max_kullanim_sayisi
                )
            ).first()
            
            if not kampanya:
                return {
                    'uygulandı': False,
                    'kampanya_id': None,
                    'kampanya_adi': None,
                    'indirim_tutari': Decimal('0'),
                    'indirimli_fiyat': fiyat
                }
            
            # İndirim hesapla
            if kampanya.indirim_tipi.value == 'yuzde':
                indirim_tutari = fiyat * (kampanya.indirim_degeri / 100)
            else:  # tutar
                indirim_tutari = kampanya.indirim_degeri
            
            indirimli_fiyat = max(fiyat - indirim_tutari, Decimal('0'))
            
            return {
                'uygulandı': True,
                'kampanya_id': kampanya.id,
                'kampanya_adi': kampanya.kampanya_adi,
                'indirim_tutari': indirim_tutari,
                'indirimli_fiyat': indirimli_fiyat
            }
            
        except Exception as e:
            raise Exception(f"Kampanya uygulama hatası: {str(e)}")

    @staticmethod
    def bedelsiz_kontrol(
        oda_id: int,
        urun_id: int,
        miktar: int
    ) -> Tuple[int, int]:
        """
        Bedelsiz limit kontrolü
        
        Args:
            oda_id: Oda ID
            urun_id: Ürün ID
            miktar: Talep edilen miktar
            
        Returns:
            tuple: (bedelsiz_miktar, ucretli_miktar)
        """
        try:
            simdi = datetime.now(timezone.utc)
            
            # Aktif bedelsiz limiti bul
            limit = BedelsizLimit.query.filter(
                BedelsizLimit.oda_id == oda_id,
                BedelsizLimit.urun_id == urun_id,
                BedelsizLimit.aktif == True,
                BedelsizLimit.baslangic_tarihi <= simdi
            ).filter(
                or_(
                    BedelsizLimit.bitis_tarihi.is_(None),
                    BedelsizLimit.bitis_tarihi >= simdi
                )
            ).first()
            
            if not limit:
                return (0, miktar)
            
            # Kalan limit hesapla
            kalan_limit = limit.max_miktar - limit.kullanilan_miktar
            
            if kalan_limit <= 0:
                return (0, miktar)
            
            # Bedelsiz ve ücretli miktarları hesapla
            bedelsiz_miktar = min(miktar, kalan_limit)
            ucretli_miktar = miktar - bedelsiz_miktar
            
            return (bedelsiz_miktar, ucretli_miktar)
            
        except Exception as e:
            raise Exception(f"Bedelsiz kontrol hatası: {str(e)}")



class KampanyaServisi:
    """Kampanya yönetim servisi"""

    @staticmethod
    def kampanya_olustur(kampanya_data: Dict, kullanici_id: int) -> Dict:
        """
        Yeni kampanya oluştur
        
        Args:
            kampanya_data: {
                'kampanya_adi': str,
                'baslangic_tarihi': datetime,
                'bitis_tarihi': datetime,
                'urun_id': Optional[int],
                'indirim_tipi': str ('yuzde' veya 'tutar'),
                'indirim_degeri': Decimal,
                'min_siparis_miktari': int,
                'max_kullanim_sayisi': Optional[int]
            }
            kullanici_id: Oluşturan kullanıcı ID
            
        Returns:
            dict: Oluşturulan kampanya bilgileri
        """
        try:
            # Validasyon
            if not kampanya_data.get('kampanya_adi'):
                raise ValueError("Kampanya adı zorunludur")
            
            if not kampanya_data.get('baslangic_tarihi') or not kampanya_data.get('bitis_tarihi'):
                raise ValueError("Başlangıç ve bitiş tarihleri zorunludur")
            
            if kampanya_data['baslangic_tarihi'] >= kampanya_data['bitis_tarihi']:
                raise ValueError("Bitiş tarihi başlangıç tarihinden sonra olmalıdır")
            
            if kampanya_data.get('indirim_degeri', 0) <= 0:
                raise ValueError("İndirim değeri pozitif olmalıdır")
            
            # Yüzde indirimi için kontrol
            if kampanya_data.get('indirim_tipi') == 'yuzde':
                if kampanya_data['indirim_degeri'] > 100:
                    raise ValueError("Yüzde indirimi 100'den büyük olamaz")
            
            # Kampanya oluştur
            kampanya = Kampanya(
                kampanya_adi=kampanya_data['kampanya_adi'],
                baslangic_tarihi=kampanya_data['baslangic_tarihi'],
                bitis_tarihi=kampanya_data['bitis_tarihi'],
                urun_id=kampanya_data.get('urun_id'),
                indirim_tipi=kampanya_data['indirim_tipi'],
                indirim_degeri=kampanya_data['indirim_degeri'],
                min_siparis_miktari=kampanya_data.get('min_siparis_miktari', 1),
                max_kullanim_sayisi=kampanya_data.get('max_kullanim_sayisi'),
                olusturan_id=kullanici_id
            )
            
            db.session.add(kampanya)
            db.session.commit()
            
            return {
                'success': True,
                'kampanya_id': kampanya.id,
                'kampanya_adi': kampanya.kampanya_adi,
                'message': 'Kampanya başarıyla oluşturuldu'
            }
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Kampanya oluşturma hatası: {str(e)}")

    @staticmethod
    def kampanya_uygula(kampanya_id: int, fiyat: Decimal, miktar: int) -> Dict:
        """
        Kampanya indirimini hesapla
        
        Args:
            kampanya_id: Kampanya ID
            fiyat: Temel fiyat
            miktar: Miktar
            
        Returns:
            dict: {
                'indirim_tutari': Decimal,
                'indirimli_fiyat': Decimal,
                'indirim_orani': float
            }
        """
        try:
            kampanya = Kampanya.query.get(kampanya_id)
            
            if not kampanya:
                raise ValueError(f"Kampanya {kampanya_id} bulunamadı")
            
            if not kampanya.aktif:
                raise ValueError("Kampanya aktif değil")
            
            # Tarih kontrolü
            simdi = datetime.now(timezone.utc)
            if not (kampanya.baslangic_tarihi <= simdi <= kampanya.bitis_tarihi):
                raise ValueError("Kampanya tarihi geçerli değil")
            
            # Minimum miktar kontrolü
            if miktar < kampanya.min_siparis_miktari:
                raise ValueError(f"Minimum sipariş miktarı: {kampanya.min_siparis_miktari}")
            
            # Kullanım sayısı kontrolü
            if kampanya.max_kullanim_sayisi:
                if kampanya.kullanilan_sayisi >= kampanya.max_kullanim_sayisi:
                    raise ValueError("Kampanya kullanım limiti doldu")
            
            # İndirim hesapla
            if kampanya.indirim_tipi.value == 'yuzde':
                indirim_tutari = fiyat * (kampanya.indirim_degeri / 100)
                indirim_orani = float(kampanya.indirim_degeri)
            else:  # tutar
                indirim_tutari = kampanya.indirim_degeri
                indirim_orani = float((indirim_tutari / fiyat) * 100) if fiyat > 0 else 0
            
            indirimli_fiyat = max(fiyat - indirim_tutari, Decimal('0'))
            
            return {
                'indirim_tutari': indirim_tutari,
                'indirimli_fiyat': indirimli_fiyat,
                'indirim_orani': round(indirim_orani, 2)
            }
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"Kampanya uygulama hatası: {str(e)}")

    @staticmethod
    def kampanya_kullanim_guncelle(kampanya_id: int) -> bool:
        """
        Kampanya kullanım sayısını artır
        
        Args:
            kampanya_id: Kampanya ID
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            kampanya = Kampanya.query.get(kampanya_id)
            
            if not kampanya:
                raise ValueError(f"Kampanya {kampanya_id} bulunamadı")
            
            kampanya.kullanilan_sayisi += 1
            
            # Maksimum kullanım kontrolü
            if kampanya.max_kullanim_sayisi:
                if kampanya.kullanilan_sayisi >= kampanya.max_kullanim_sayisi:
                    kampanya.aktif = False
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Kampanya kullanım güncelleme hatası: {str(e)}")

    @staticmethod
    def aktif_kampanyalar_getir(
        urun_id: Optional[int] = None,
        tarih: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Aktif kampanyaları getir
        
        Args:
            urun_id: Ürün ID (None ise tüm kampanyalar)
            tarih: Tarih (None ise şimdi)
            
        Returns:
            list: Kampanya listesi
        """
        try:
            if tarih is None:
                tarih = datetime.now(timezone.utc)
            
            query = Kampanya.query.filter(
                Kampanya.aktif == True,
                Kampanya.baslangic_tarihi <= tarih,
                Kampanya.bitis_tarihi >= tarih
            )
            
            if urun_id:
                query = query.filter(
                    or_(
                        Kampanya.urun_id == urun_id,
                        Kampanya.urun_id.is_(None)
                    )
                )
            
            kampanyalar = query.all()
            
            sonuc = []
            for k in kampanyalar:
                # Kullanım limiti kontrolü
                if k.max_kullanim_sayisi:
                    if k.kullanilan_sayisi >= k.max_kullanim_sayisi:
                        continue
                
                sonuc.append({
                    'id': k.id,
                    'kampanya_adi': k.kampanya_adi,
                    'urun_id': k.urun_id,
                    'indirim_tipi': k.indirim_tipi.value,
                    'indirim_degeri': float(k.indirim_degeri),
                    'min_siparis_miktari': k.min_siparis_miktari,
                    'kalan_kullanim': (k.max_kullanim_sayisi - k.kullanilan_sayisi) if k.max_kullanim_sayisi else None,
                    'baslangic_tarihi': k.baslangic_tarihi.isoformat(),
                    'bitis_tarihi': k.bitis_tarihi.isoformat()
                })
            
            return sonuc
            
        except Exception as e:
            raise Exception(f"Aktif kampanyalar getirme hatası: {str(e)}")

    @staticmethod
    def kampanya_sil(kampanya_id: int, kullanici_id: int) -> bool:
        """
        Kampanyayı pasif yap (soft delete)
        
        Args:
            kampanya_id: Kampanya ID
            kullanici_id: İşlemi yapan kullanıcı
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            kampanya = Kampanya.query.get(kampanya_id)
            
            if not kampanya:
                raise ValueError(f"Kampanya {kampanya_id} bulunamadı")
            
            kampanya.aktif = False
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Kampanya silme hatası: {str(e)}")

    @staticmethod
    def kampanya_istatistikleri(kampanya_id: int) -> Dict:
        """
        Kampanya kullanım istatistikleri
        
        Args:
            kampanya_id: Kampanya ID
            
        Returns:
            dict: İstatistik bilgileri
        """
        try:
            kampanya = Kampanya.query.get(kampanya_id)
            
            if not kampanya:
                raise ValueError(f"Kampanya {kampanya_id} bulunamadı")
            
            # Kampanya ile yapılan işlemleri say
            toplam_kullanim = MinibarIslemDetay.query.filter_by(
                kampanya_id=kampanya_id
            ).count()
            
            # Toplam indirim tutarını hesapla
            toplam_indirim = db.session.query(
                func.sum(MinibarIslemDetay.satis_fiyati - MinibarIslemDetay.kar_tutari)
            ).filter(
                MinibarIslemDetay.kampanya_id == kampanya_id
            ).scalar() or Decimal('0')
            
            return {
                'kampanya_id': kampanya.id,
                'kampanya_adi': kampanya.kampanya_adi,
                'toplam_kullanim': toplam_kullanim,
                'max_kullanim': kampanya.max_kullanim_sayisi,
                'kalan_kullanim': (kampanya.max_kullanim_sayisi - kampanya.kullanilan_sayisi) if kampanya.max_kullanim_sayisi else None,
                'toplam_indirim_tutari': float(toplam_indirim),
                'aktif': kampanya.aktif,
                'baslangic_tarihi': kampanya.baslangic_tarihi.isoformat(),
                'bitis_tarihi': kampanya.bitis_tarihi.isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Kampanya istatistikleri hatası: {str(e)}")



class BedelsizServisi:
    """Bedelsiz limit yönetim servisi"""

    @staticmethod
    def limit_kontrol(oda_id: int, urun_id: int, miktar: int) -> Tuple[int, int]:
        """
        Bedelsiz limit kontrolü
        
        Args:
            oda_id: Oda ID
            urun_id: Ürün ID
            miktar: Talep edilen miktar
            
        Returns:
            tuple: (bedelsiz_miktar, ucretli_miktar)
        """
        try:
            simdi = datetime.now(timezone.utc)
            
            # Aktif bedelsiz limiti bul
            limit = BedelsizLimit.query.filter(
                BedelsizLimit.oda_id == oda_id,
                BedelsizLimit.urun_id == urun_id,
                BedelsizLimit.aktif == True,
                BedelsizLimit.baslangic_tarihi <= simdi
            ).filter(
                or_(
                    BedelsizLimit.bitis_tarihi.is_(None),
                    BedelsizLimit.bitis_tarihi >= simdi
                )
            ).first()
            
            if not limit:
                return (0, miktar)
            
            # Kalan limit hesapla
            kalan_limit = limit.max_miktar - limit.kullanilan_miktar
            
            if kalan_limit <= 0:
                return (0, miktar)
            
            # Bedelsiz ve ücretli miktarları hesapla
            bedelsiz_miktar = min(miktar, kalan_limit)
            ucretli_miktar = miktar - bedelsiz_miktar
            
            return (bedelsiz_miktar, ucretli_miktar)
            
        except Exception as e:
            raise Exception(f"Bedelsiz kontrol hatası: {str(e)}")

    @staticmethod
    def limit_kullan(
        oda_id: int,
        urun_id: int,
        miktar: int,
        islem_id: int
    ) -> Dict:
        """
        Bedelsiz limiti kullan ve log'la
        
        Args:
            oda_id: Oda ID
            urun_id: Ürün ID
            miktar: Kullanılan miktar
            islem_id: Minibar işlem ID
            
        Returns:
            dict: Kullanım bilgileri
        """
        try:
            simdi = datetime.now(timezone.utc)
            
            # Aktif limiti bul
            limit = BedelsizLimit.query.filter(
                BedelsizLimit.oda_id == oda_id,
                BedelsizLimit.urun_id == urun_id,
                BedelsizLimit.aktif == True,
                BedelsizLimit.baslangic_tarihi <= simdi
            ).filter(
                or_(
                    BedelsizLimit.bitis_tarihi.is_(None),
                    BedelsizLimit.bitis_tarihi >= simdi
                )
            ).first()
            
            if not limit:
                raise ValueError("Aktif bedelsiz limit bulunamadı")
            
            # Kalan limit kontrolü
            kalan_limit = limit.max_miktar - limit.kullanilan_miktar
            if miktar > kalan_limit:
                raise ValueError(f"Yetersiz bedelsiz limit. Kalan: {kalan_limit}")
            
            # Limiti güncelle
            limit.kullanilan_miktar += miktar
            
            # Log kaydı oluştur
            log = BedelsizKullanimLog(
                oda_id=oda_id,
                urun_id=urun_id,
                miktar=miktar,
                islem_id=islem_id,
                limit_id=limit.id
            )
            
            db.session.add(log)
            db.session.commit()
            
            return {
                'success': True,
                'kullanilan_miktar': miktar,
                'kalan_limit': limit.max_miktar - limit.kullanilan_miktar,
                'limit_tipi': limit.limit_tipi.value
            }
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Bedelsiz limit kullanma hatası: {str(e)}")

    @staticmethod
    def limit_tanimla(
        oda_id: int,
        urun_id: int,
        max_miktar: int,
        limit_tipi: str,
        baslangic_tarihi: datetime,
        bitis_tarihi: Optional[datetime] = None,
        kampanya_id: Optional[int] = None
    ) -> Dict:
        """
        Yeni bedelsiz limit tanımla
        
        Args:
            oda_id: Oda ID
            urun_id: Ürün ID
            max_miktar: Maksimum bedelsiz miktar
            limit_tipi: 'misafir', 'kampanya', 'personel'
            baslangic_tarihi: Başlangıç tarihi
            bitis_tarihi: Bitiş tarihi (opsiyonel)
            kampanya_id: Kampanya ID (opsiyonel)
            
        Returns:
            dict: Oluşturulan limit bilgileri
        """
        try:
            # Validasyon
            if max_miktar <= 0:
                raise ValueError("Maksimum miktar pozitif olmalıdır")
            
            if bitis_tarihi and baslangic_tarihi >= bitis_tarihi:
                raise ValueError("Bitiş tarihi başlangıç tarihinden sonra olmalıdır")
            
            # Mevcut aktif limiti kontrol et
            mevcut_limit = BedelsizLimit.query.filter(
                BedelsizLimit.oda_id == oda_id,
                BedelsizLimit.urun_id == urun_id,
                BedelsizLimit.aktif == True,
                BedelsizLimit.baslangic_tarihi <= baslangic_tarihi
            ).filter(
                or_(
                    BedelsizLimit.bitis_tarihi.is_(None),
                    BedelsizLimit.bitis_tarihi >= baslangic_tarihi
                )
            ).first()
            
            if mevcut_limit:
                raise ValueError("Bu oda ve ürün için zaten aktif bir limit mevcut")
            
            # Yeni limit oluştur
            limit = BedelsizLimit(
                oda_id=oda_id,
                urun_id=urun_id,
                max_miktar=max_miktar,
                baslangic_tarihi=baslangic_tarihi,
                bitis_tarihi=bitis_tarihi,
                limit_tipi=limit_tipi,
                kampanya_id=kampanya_id
            )
            
            db.session.add(limit)
            db.session.commit()
            
            return {
                'success': True,
                'limit_id': limit.id,
                'max_miktar': limit.max_miktar,
                'limit_tipi': limit.limit_tipi.value,
                'message': 'Bedelsiz limit başarıyla tanımlandı'
            }
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Bedelsiz limit tanımlama hatası: {str(e)}")

    @staticmethod
    def limit_iptal(limit_id: int) -> bool:
        """
        Bedelsiz limiti iptal et (pasif yap)
        
        Args:
            limit_id: Limit ID
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            limit = BedelsizLimit.query.get(limit_id)
            
            if not limit:
                raise ValueError(f"Limit {limit_id} bulunamadı")
            
            limit.aktif = False
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Limit iptal hatası: {str(e)}")

    @staticmethod
    def oda_limitleri_getir(oda_id: int, aktif_mi: bool = True) -> List[Dict]:
        """
        Oda için tanımlı bedelsiz limitleri getir
        
        Args:
            oda_id: Oda ID
            aktif_mi: Sadece aktif limitleri getir mi?
            
        Returns:
            list: Limit listesi
        """
        try:
            query = BedelsizLimit.query.filter_by(oda_id=oda_id)
            
            if aktif_mi:
                simdi = datetime.now(timezone.utc)
                query = query.filter(
                    BedelsizLimit.aktif == True,
                    BedelsizLimit.baslangic_tarihi <= simdi
                ).filter(
                    or_(
                        BedelsizLimit.bitis_tarihi.is_(None),
                        BedelsizLimit.bitis_tarihi >= simdi
                    )
                )
            
            limitler = query.all()
            
            sonuc = []
            for limit in limitler:
                sonuc.append({
                    'id': limit.id,
                    'urun_id': limit.urun_id,
                    'urun_adi': limit.urun.urun_adi if limit.urun else None,
                    'max_miktar': limit.max_miktar,
                    'kullanilan_miktar': limit.kullanilan_miktar,
                    'kalan_miktar': limit.max_miktar - limit.kullanilan_miktar,
                    'limit_tipi': limit.limit_tipi.value,
                    'kampanya_id': limit.kampanya_id,
                    'aktif': limit.aktif,
                    'baslangic_tarihi': limit.baslangic_tarihi.isoformat(),
                    'bitis_tarihi': limit.bitis_tarihi.isoformat() if limit.bitis_tarihi else None
                })
            
            return sonuc
            
        except Exception as e:
            raise Exception(f"Oda limitleri getirme hatası: {str(e)}")

    @staticmethod
    def kullanim_gecmisi(
        oda_id: Optional[int] = None,
        urun_id: Optional[int] = None,
        baslangic: Optional[datetime] = None,
        bitis: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Bedelsiz kullanım geçmişi
        
        Args:
            oda_id: Oda ID (opsiyonel)
            urun_id: Ürün ID (opsiyonel)
            baslangic: Başlangıç tarihi (opsiyonel)
            bitis: Bitiş tarihi (opsiyonel)
            
        Returns:
            list: Kullanım geçmişi
        """
        try:
            query = BedelsizKullanimLog.query
            
            if oda_id:
                query = query.filter_by(oda_id=oda_id)
            
            if urun_id:
                query = query.filter_by(urun_id=urun_id)
            
            if baslangic:
                query = query.filter(BedelsizKullanimLog.kullanilma_tarihi >= baslangic)
            
            if bitis:
                query = query.filter(BedelsizKullanimLog.kullanilma_tarihi <= bitis)
            
            loglar = query.order_by(BedelsizKullanimLog.kullanilma_tarihi.desc()).all()
            
            sonuc = []
            for log in loglar:
                sonuc.append({
                    'id': log.id,
                    'oda_id': log.oda_id,
                    'oda_no': log.oda.oda_no if log.oda else None,
                    'urun_id': log.urun_id,
                    'urun_adi': log.urun.urun_adi if log.urun else None,
                    'miktar': log.miktar,
                    'kullanilma_tarihi': log.kullanilma_tarihi.isoformat(),
                    'limit_id': log.limit_id,
                    'limit_tipi': log.limit.limit_tipi.value if log.limit else None
                })
            
            return sonuc
            
        except Exception as e:
            raise Exception(f"Kullanım geçmişi getirme hatası: {str(e)}")



class KarHesaplamaServisi:
    """Karlılık hesaplama ve analiz servisi"""

    @staticmethod
    def gercek_zamanli_kar_hesapla(islem_detay_listesi: List) -> Dict:
        """
        Gerçek zamanlı kar/zarar hesaplama
        
        Args:
            islem_detay_listesi: MinibarIslemDetay listesi veya ID listesi
            
        Returns:
            dict: {
                'toplam_gelir': Decimal,
                'toplam_maliyet': Decimal,
                'net_kar': Decimal,
                'kar_marji': float,
                'islem_sayisi': int,
                'bedelsiz_tuketim': Decimal,
                'kampanyali_tuketim': Decimal
            }
        """
        try:
            toplam_gelir = Decimal('0')
            toplam_maliyet = Decimal('0')
            bedelsiz_tuketim = Decimal('0')
            kampanyali_tuketim = Decimal('0')
            islem_sayisi = 0
            
            for detay in islem_detay_listesi:
                # Eğer ID ise, detayı getir
                if isinstance(detay, int):
                    detay = MinibarIslemDetay.query.get(detay)
                    if not detay:
                        continue
                
                # Tüketim varsa hesapla
                if detay.tuketim > 0:
                    # Gelir hesapla (bedelsiz hariç)
                    if not detay.bedelsiz and detay.satis_fiyati:
                        toplam_gelir += detay.satis_fiyati * detay.tuketim
                    
                    # Maliyet hesapla
                    if detay.alis_fiyati:
                        toplam_maliyet += detay.alis_fiyati * detay.tuketim
                    
                    # Bedelsiz tüketim
                    if detay.bedelsiz:
                        bedelsiz_tuketim += (detay.alis_fiyati or Decimal('0')) * detay.tuketim
                    
                    # Kampanyalı tüketim
                    if detay.kampanya_id:
                        kampanyali_tuketim += (detay.satis_fiyati or Decimal('0')) * detay.tuketim
                    
                    islem_sayisi += 1
            
            # Net kar hesapla
            net_kar = toplam_gelir - toplam_maliyet
            
            # Kar marjı hesapla (sıfıra bölme kontrolü)
            if toplam_maliyet > 0:
                kar_marji = float((net_kar / toplam_maliyet) * 100)
            else:
                kar_marji = 0.0
            
            return {
                'toplam_gelir': toplam_gelir,
                'toplam_maliyet': toplam_maliyet,
                'net_kar': net_kar,
                'kar_marji': round(kar_marji, 2),
                'islem_sayisi': islem_sayisi,
                'bedelsiz_tuketim': bedelsiz_tuketim,
                'kampanyali_tuketim': kampanyali_tuketim
            }
            
        except Exception as e:
            raise Exception(f"Gerçek zamanlı kar hesaplama hatası: {str(e)}")

    @staticmethod
    def donemsel_kar_analizi(
        otel_id: int = None,
        baslangic: date = None,
        bitis: date = None,
        donem_tipi: str = 'gunluk'
    ) -> Dict:
        """
        Dönemsel karlılık analizi
        
        Args:
            otel_id: Otel ID (opsiyonel, None ise tüm oteller)
            baslangic: Başlangıç tarihi
            bitis: Bitiş tarihi
            donem_tipi: 'gunluk', 'haftalik', 'aylik'
            
        Returns:
            dict: Analiz sonuçları
        """
        try:
            # Dönem içindeki minibar işlemlerini getir
            from models import MinibarIslem, Oda, Kat
            
            query = db.session.query(MinibarIslemDetay).join(
                MinibarIslem
            ).join(
                Oda
            ).join(
                Kat
            ).filter(
                MinibarIslem.islem_tarihi >= baslangic,
                MinibarIslem.islem_tarihi <= bitis
            )
            
            # Otel filtresi (opsiyonel)
            if otel_id:
                query = query.filter(Kat.otel_id == otel_id)
            
            islemler = query.all()
            
            # Kar hesapla
            kar_sonuc = KarHesaplamaServisi.gercek_zamanli_kar_hesapla(islemler)
            
            # Analiz kaydı oluştur veya güncelle (sadece otel_id varsa)
            if otel_id:
                analiz = DonemselKarAnalizi.query.filter_by(
                    otel_id=otel_id,
                    donem_tipi=donem_tipi,
                    baslangic_tarihi=baslangic,
                    bitis_tarihi=bitis
                ).first()
                
                if not analiz:
                    analiz = DonemselKarAnalizi(
                        otel_id=otel_id,
                        donem_tipi=donem_tipi,
                        baslangic_tarihi=baslangic,
                        bitis_tarihi=bitis
                    )
                    db.session.add(analiz)
                
                # Verileri güncelle
                analiz.toplam_gelir = kar_sonuc['toplam_gelir']
                analiz.toplam_maliyet = kar_sonuc['toplam_maliyet']
                analiz.net_kar = kar_sonuc['net_kar']
                analiz.kar_marji = Decimal(str(kar_sonuc['kar_marji']))
                analiz.analiz_verisi = {
                    'islem_sayisi': kar_sonuc['islem_sayisi'],
                    'bedelsiz_tuketim': float(kar_sonuc['bedelsiz_tuketim']),
                    'kampanyali_tuketim': float(kar_sonuc['kampanyali_tuketim'])
                }
                
                db.session.commit()
            
            return {
                'otel_id': otel_id,
                'donem_tipi': donem_tipi,
                'baslangic_tarihi': baslangic.isoformat(),
                'bitis_tarihi': bitis.isoformat(),
                'toplam_gelir': float(kar_sonuc['toplam_gelir']),
                'toplam_maliyet': float(kar_sonuc['toplam_maliyet']),
                'net_kar': float(kar_sonuc['net_kar']),
                'kar_marji': kar_sonuc['kar_marji'],
                'islem_sayisi': kar_sonuc['islem_sayisi'],
                'bedelsiz_tuketim': float(kar_sonuc['bedelsiz_tuketim']),
                'kampanyali_tuketim': float(kar_sonuc['kampanyali_tuketim'])
            }
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Dönemsel kar analizi hatası: {str(e)}")

    @staticmethod
    def urun_karliligi_analizi(
        urun_id: int,
        baslangic: Optional[date] = None,
        bitis: Optional[date] = None
    ) -> Dict:
        """
        Ürün bazlı karlılık analizi
        
        Args:
            urun_id: Ürün ID
            baslangic: Başlangıç tarihi (opsiyonel)
            bitis: Bitiş tarihi (opsiyonel)
            
        Returns:
            dict: Ürün karlılık bilgileri
        """
        try:
            from models import MinibarIslem
            
            query = db.session.query(MinibarIslemDetay).join(
                MinibarIslem
            ).filter(
                MinibarIslemDetay.urun_id == urun_id
            )
            
            if baslangic:
                query = query.filter(MinibarIslem.islem_tarihi >= baslangic)
            
            if bitis:
                query = query.filter(MinibarIslem.islem_tarihi <= bitis)
            
            detaylar = query.all()
            
            if not detaylar:
                return {
                    'urun_id': urun_id,
                    'toplam_satis': 0,
                    'toplam_gelir': 0,
                    'toplam_maliyet': 0,
                    'net_kar': 0,
                    'kar_marji': 0,
                    'ortalama_satis_fiyati': 0,
                    'ortalama_alis_fiyati': 0
                }
            
            # Hesaplamalar
            toplam_satis = sum(d.tuketim for d in detaylar if d.tuketim > 0)
            toplam_gelir = sum(
                (d.satis_fiyati or Decimal('0')) * d.tuketim 
                for d in detaylar 
                if d.tuketim > 0 and not d.bedelsiz
            )
            toplam_maliyet = sum(
                (d.alis_fiyati or Decimal('0')) * d.tuketim 
                for d in detaylar 
                if d.tuketim > 0
            )
            
            net_kar = toplam_gelir - toplam_maliyet
            kar_marji = float((net_kar / toplam_maliyet) * 100) if toplam_maliyet > 0 else 0
            
            # Ortalamalar
            ortalama_satis = toplam_gelir / toplam_satis if toplam_satis > 0 else Decimal('0')
            ortalama_alis = toplam_maliyet / toplam_satis if toplam_satis > 0 else Decimal('0')
            
            return {
                'urun_id': urun_id,
                'toplam_satis': toplam_satis,
                'toplam_gelir': float(toplam_gelir),
                'toplam_maliyet': float(toplam_maliyet),
                'net_kar': float(net_kar),
                'kar_marji': round(kar_marji, 2),
                'ortalama_satis_fiyati': float(ortalama_satis),
                'ortalama_alis_fiyati': float(ortalama_alis)
            }
            
        except Exception as e:
            raise Exception(f"Ürün karlılık analizi hatası: {str(e)}")

    @staticmethod
    def oda_karliligi_analizi(
        oda_id: int,
        baslangic: Optional[date] = None,
        bitis: Optional[date] = None
    ) -> Dict:
        """
        Oda bazlı karlılık analizi
        
        Args:
            oda_id: Oda ID
            baslangic: Başlangıç tarihi (opsiyonel)
            bitis: Bitiş tarihi (opsiyonel)
            
        Returns:
            dict: Oda karlılık bilgileri
        """
        try:
            from models import MinibarIslem
            
            query = db.session.query(MinibarIslemDetay).join(
                MinibarIslem
            ).filter(
                MinibarIslem.oda_id == oda_id
            )
            
            if baslangic:
                query = query.filter(MinibarIslem.islem_tarihi >= baslangic)
            
            if bitis:
                query = query.filter(MinibarIslem.islem_tarihi <= bitis)
            
            detaylar = query.all()
            
            if not detaylar:
                return {
                    'oda_id': oda_id,
                    'toplam_islem': 0,
                    'toplam_gelir': 0,
                    'toplam_maliyet': 0,
                    'net_kar': 0,
                    'kar_marji': 0,
                    'bedelsiz_tuketim': 0
                }
            
            # Kar hesapla
            kar_sonuc = KarHesaplamaServisi.gercek_zamanli_kar_hesapla(detaylar)
            
            return {
                'oda_id': oda_id,
                'toplam_islem': kar_sonuc['islem_sayisi'],
                'toplam_gelir': float(kar_sonuc['toplam_gelir']),
                'toplam_maliyet': float(kar_sonuc['toplam_maliyet']),
                'net_kar': float(kar_sonuc['net_kar']),
                'kar_marji': kar_sonuc['kar_marji'],
                'bedelsiz_tuketim': float(kar_sonuc['bedelsiz_tuketim']),
                'kampanyali_tuketim': float(kar_sonuc['kampanyali_tuketim'])
            }
            
        except Exception as e:
            raise Exception(f"Oda karlılık analizi hatası: {str(e)}")

    @staticmethod
    def roi_hesapla(
        urun_id: int,
        baslangic: date,
        bitis: date
    ) -> Dict:
        """
        ROI (Return on Investment) hesaplama
        
        Args:
            urun_id: Ürün ID
            baslangic: Başlangıç tarihi
            bitis: Bitiş tarihi
            
        Returns:
            dict: ROI bilgileri
        """
        try:
            # Ürün karlılığını al
            karlilik = KarHesaplamaServisi.urun_karliligi_analizi(
                urun_id, baslangic, bitis
            )
            
            # ROI hesapla: (Net Kar / Toplam Maliyet) * 100
            if karlilik['toplam_maliyet'] > 0:
                roi = (karlilik['net_kar'] / karlilik['toplam_maliyet']) * 100
            else:
                roi = 0
            
            # Dönem gün sayısı
            gun_sayisi = (bitis - baslangic).days + 1
            
            # Günlük ortalama kar
            gunluk_kar = karlilik['net_kar'] / gun_sayisi if gun_sayisi > 0 else 0
            
            return {
                'urun_id': urun_id,
                'donem': f"{baslangic.isoformat()} - {bitis.isoformat()}",
                'gun_sayisi': gun_sayisi,
                'toplam_yatirim': karlilik['toplam_maliyet'],
                'toplam_gelir': karlilik['toplam_gelir'],
                'net_kar': karlilik['net_kar'],
                'roi': round(roi, 2),
                'gunluk_ortalama_kar': round(gunluk_kar, 2),
                'kar_marji': karlilik['kar_marji']
            }
            
        except Exception as e:
            raise Exception(f"ROI hesaplama hatası: {str(e)}")

    @staticmethod
    def en_karlı_urunler(
        otel_id: Optional[int] = None,
        baslangic: Optional[date] = None,
        bitis: Optional[date] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        En karlı ürünleri listele
        
        Args:
            otel_id: Otel ID (opsiyonel)
            baslangic: Başlangıç tarihi (opsiyonel)
            bitis: Bitiş tarihi (opsiyonel)
            limit: Maksimum sonuç sayısı
            
        Returns:
            list: En karlı ürünler listesi
        """
        try:
            from models import MinibarIslem, Oda, Kat
            
            # Tüm ürünlerin karlılığını hesapla
            query = db.session.query(
                MinibarIslemDetay.urun_id,
                func.sum(MinibarIslemDetay.kar_tutari).label('toplam_kar'),
                func.sum(MinibarIslemDetay.tuketim).label('toplam_satis'),
                func.avg(MinibarIslemDetay.kar_orani).label('ortalama_kar_orani')
            ).join(MinibarIslem)
            
            if otel_id:
                query = query.join(Oda).join(Kat).filter(Kat.otel_id == otel_id)
            
            if baslangic:
                query = query.filter(MinibarIslem.islem_tarihi >= baslangic)
            
            if bitis:
                query = query.filter(MinibarIslem.islem_tarihi <= bitis)
            
            sonuclar = query.filter(
                MinibarIslemDetay.tuketim > 0
            ).group_by(
                MinibarIslemDetay.urun_id
            ).order_by(
                func.sum(MinibarIslemDetay.kar_tutari).desc()
            ).limit(limit).all()
            
            urun_listesi = []
            for sonuc in sonuclar:
                urun = Urun.query.get(sonuc.urun_id)
                urun_listesi.append({
                    'urun_id': sonuc.urun_id,
                    'urun_adi': urun.urun_adi if urun else 'Bilinmiyor',
                    'toplam_kar': float(sonuc.toplam_kar or 0),
                    'toplam_satis': int(sonuc.toplam_satis or 0),
                    'ortalama_kar_orani': round(float(sonuc.ortalama_kar_orani or 0), 2)
                })
            
            return urun_listesi
            
        except Exception as e:
            raise Exception(f"En karlı ürünler listesi hatası: {str(e)}")



class StokYonetimServisi:
    """Stok yönetim ve raporlama servisi"""

    @staticmethod
    def stok_durumu_getir(
        otel_id: int,
        urun_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Stok durumunu getir
        
        Args:
            otel_id: Otel ID
            urun_id: Ürün ID (opsiyonel, None ise tüm ürünler)
            
        Returns:
            list: Stok durumu listesi
        """
        try:
            from models import UrunStok
            
            query = UrunStok.query.filter_by(otel_id=otel_id)
            
            if urun_id:
                query = query.filter_by(urun_id=urun_id)
            
            stoklar = query.all()
            
            sonuc = []
            for stok in stoklar:
                sonuc.append({
                    'urun_id': stok.urun_id,
                    'urun_adi': stok.urun.urun_adi if stok.urun else 'Bilinmiyor',
                    'mevcut_stok': stok.mevcut_stok,
                    'minimum_stok': stok.minimum_stok,
                    'maksimum_stok': stok.maksimum_stok,
                    'kritik_stok_seviyesi': stok.kritik_stok_seviyesi,
                    'stok_durumu': stok.stok_durumu(),
                    'birim_maliyet': float(stok.birim_maliyet),
                    'toplam_deger': float(stok.toplam_deger),
                    'stok_devir_hizi': float(stok.stok_devir_hizi),
                    'son_giris_tarihi': stok.son_giris_tarihi.isoformat() if stok.son_giris_tarihi else None,
                    'son_cikis_tarihi': stok.son_cikis_tarihi.isoformat() if stok.son_cikis_tarihi else None
                })
            
            return sonuc
            
        except Exception as e:
            raise Exception(f"Stok durumu getirme hatası: {str(e)}")

    @staticmethod
    def kritik_stoklar_getir(otel_id: int) -> List[Dict]:
        """
        Kritik seviyedeki stokları getir
        
        Args:
            otel_id: Otel ID
            
        Returns:
            list: Kritik stok listesi
        """
        try:
            from models import UrunStok
            
            stoklar = UrunStok.query.filter(
                UrunStok.otel_id == otel_id,
                UrunStok.mevcut_stok <= UrunStok.kritik_stok_seviyesi
            ).all()
            
            sonuc = []
            for stok in stoklar:
                eksik_miktar = stok.minimum_stok - stok.mevcut_stok
                
                sonuc.append({
                    'urun_id': stok.urun_id,
                    'urun_adi': stok.urun.urun_adi if stok.urun else 'Bilinmiyor',
                    'mevcut_stok': stok.mevcut_stok,
                    'kritik_stok_seviyesi': stok.kritik_stok_seviyesi,
                    'minimum_stok': stok.minimum_stok,
                    'eksik_miktar': max(eksik_miktar, 0),
                    'stok_durumu': stok.stok_durumu(),
                    'son_cikis_tarihi': stok.son_cikis_tarihi.isoformat() if stok.son_cikis_tarihi else None
                })
            
            return sonuc
            
        except Exception as e:
            raise Exception(f"Kritik stoklar getirme hatası: {str(e)}")

    @staticmethod
    def stok_sayim_yap(
        otel_id: int,
        sayim_verileri: List[Dict],
        kullanici_id: int
    ) -> Dict:
        """
        Stok sayımı yap ve farkları kaydet
        
        Args:
            otel_id: Otel ID
            sayim_verileri: [{'urun_id': int, 'sayilan_miktar': int}, ...]
            kullanici_id: Sayımı yapan kullanıcı
            
        Returns:
            dict: Sayım sonuçları
        """
        try:
            from models import UrunStok, StokHareket
            
            toplam_fark = 0
            farkli_urunler = []
            
            for veri in sayim_verileri:
                urun_id = veri['urun_id']
                sayilan_miktar = veri['sayilan_miktar']
                
                # Stok kaydını getir
                stok = UrunStok.query.filter_by(
                    otel_id=otel_id,
                    urun_id=urun_id
                ).first()
                
                if not stok:
                    # Yeni stok kaydı oluştur
                    stok = UrunStok(
                        otel_id=otel_id,
                        urun_id=urun_id,
                        mevcut_stok=sayilan_miktar,
                        son_sayim_tarihi=datetime.now(timezone.utc),
                        son_sayim_miktari=sayilan_miktar,
                        sayim_farki=0,
                        son_guncelleyen_id=kullanici_id
                    )
                    db.session.add(stok)
                    continue
                
                # Fark hesapla
                fark = sayilan_miktar - stok.mevcut_stok
                
                if fark != 0:
                    toplam_fark += abs(fark)
                    farkli_urunler.append({
                        'urun_id': urun_id,
                        'urun_adi': stok.urun.urun_adi if stok.urun else 'Bilinmiyor',
                        'beklenen': stok.mevcut_stok,
                        'sayilan': sayilan_miktar,
                        'fark': fark
                    })
                
                # Stok güncelle
                stok.stok_guncelle(sayilan_miktar, 'sayim', kullanici_id)
                
                # Stok hareketi kaydet
                hareket = StokHareket(
                    urun_id=urun_id,
                    hareket_tipi='sayim',
                    miktar=fark,
                    aciklama=f"Stok sayımı - Fark: {fark}",
                    islem_yapan_id=kullanici_id
                )
                db.session.add(hareket)
            
            db.session.commit()
            
            return {
                'success': True,
                'toplam_urun': len(sayim_verileri),
                'farkli_urun_sayisi': len(farkli_urunler),
                'toplam_fark': toplam_fark,
                'farkli_urunler': farkli_urunler,
                'message': 'Stok sayımı başarıyla tamamlandı'
            }
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Stok sayımı hatası: {str(e)}")

    @staticmethod
    def stok_devir_raporu(
        otel_id: int,
        baslangic: date,
        bitis: date
    ) -> List[Dict]:
        """
        Stok devir hızı raporu
        
        Args:
            otel_id: Otel ID
            baslangic: Başlangıç tarihi
            bitis: Bitiş tarihi
            
        Returns:
            list: Stok devir raporu
        """
        try:
            from models import UrunStok, StokHareket
            
            # Dönem gün sayısı
            gun_sayisi = (bitis - baslangic).days + 1
            
            # Tüm ürünlerin stok hareketlerini al
            stoklar = UrunStok.query.filter_by(otel_id=otel_id).all()
            
            sonuc = []
            for stok in stoklar:
                # Dönem içindeki çıkışları hesapla
                toplam_cikis = db.session.query(
                    func.sum(StokHareket.miktar)
                ).filter(
                    StokHareket.urun_id == stok.urun_id,
                    StokHareket.hareket_tipi == 'cikis',
                    StokHareket.islem_tarihi >= baslangic,
                    StokHareket.islem_tarihi <= bitis
                ).scalar() or 0
                
                # Ortalama stok (basit hesaplama)
                ortalama_stok = stok.mevcut_stok
                
                # Devir hızı hesapla
                if ortalama_stok > 0:
                    devir_hizi = toplam_cikis / ortalama_stok
                    # Aylık devir hızına çevir
                    aylik_devir = (devir_hizi / gun_sayisi) * 30
                else:
                    aylik_devir = 0
                
                sonuc.append({
                    'urun_id': stok.urun_id,
                    'urun_adi': stok.urun.urun_adi if stok.urun else 'Bilinmiyor',
                    'mevcut_stok': stok.mevcut_stok,
                    'toplam_cikis': int(toplam_cikis),
                    'ortalama_stok': ortalama_stok,
                    'devir_hizi': round(float(devir_hizi), 2),
                    'aylik_devir_hizi': round(float(aylik_devir), 2),
                    'gun_sayisi': gun_sayisi
                })
            
            # Devir hızına göre sırala (yüksekten düşüğe)
            sonuc.sort(key=lambda x: x['aylik_devir_hizi'], reverse=True)
            
            return sonuc
            
        except Exception as e:
            raise Exception(f"Stok devir raporu hatası: {str(e)}")

    @staticmethod
    def stok_deger_raporu(otel_id: int) -> Dict:
        """
        Stok değer raporu
        
        Args:
            otel_id: Otel ID
            
        Returns:
            dict: Stok değer bilgileri
        """
        try:
            from models import UrunStok
            
            stoklar = UrunStok.query.filter_by(otel_id=otel_id).all()
            
            toplam_deger = Decimal('0')
            toplam_urun = 0
            toplam_miktar = 0
            kritik_stok_degeri = Decimal('0')
            
            urun_detaylari = []
            
            for stok in stoklar:
                toplam_deger += stok.toplam_deger
                toplam_urun += 1
                toplam_miktar += stok.mevcut_stok
                
                # Kritik stokların değeri
                if stok.mevcut_stok <= stok.kritik_stok_seviyesi:
                    kritik_stok_degeri += stok.toplam_deger
                
                urun_detaylari.append({
                    'urun_id': stok.urun_id,
                    'urun_adi': stok.urun.urun_adi if stok.urun else 'Bilinmiyor',
                    'mevcut_stok': stok.mevcut_stok,
                    'birim_maliyet': float(stok.birim_maliyet),
                    'toplam_deger': float(stok.toplam_deger),
                    'stok_durumu': stok.stok_durumu()
                })
            
            # Değere göre sırala (yüksekten düşüğe)
            urun_detaylari.sort(key=lambda x: x['toplam_deger'], reverse=True)
            
            return {
                'otel_id': otel_id,
                'toplam_stok_degeri': float(toplam_deger),
                'toplam_urun_sayisi': toplam_urun,
                'toplam_stok_miktari': toplam_miktar,
                'kritik_stok_degeri': float(kritik_stok_degeri),
                'ortalama_urun_degeri': float(toplam_deger / toplam_urun) if toplam_urun > 0 else 0,
                'urun_detaylari': urun_detaylari
            }
            
        except Exception as e:
            raise Exception(f"Stok değer raporu hatası: {str(e)}")

    @staticmethod
    def stok_guncelle(
        otel_id: int,
        urun_id: int,
        miktar: int,
        islem_tipi: str,
        kullanici_id: int,
        aciklama: Optional[str] = None
    ) -> Dict:
        """
        Stok güncelleme
        
        Args:
            otel_id: Otel ID
            urun_id: Ürün ID
            miktar: Miktar (pozitif veya negatif)
            islem_tipi: 'giris', 'cikis', 'devir', 'fire'
            kullanici_id: İşlemi yapan kullanıcı
            aciklama: Açıklama (opsiyonel)
            
        Returns:
            dict: Güncelleme sonucu
        """
        try:
            from models import UrunStok, StokHareket
            
            # Stok kaydını getir veya oluştur
            stok = UrunStok.query.filter_by(
                otel_id=otel_id,
                urun_id=urun_id
            ).first()
            
            if not stok:
                # Yeni stok kaydı oluştur
                stok = UrunStok(
                    otel_id=otel_id,
                    urun_id=urun_id,
                    mevcut_stok=0
                )
                db.session.add(stok)
            
            # Eski stok miktarı
            eski_stok = stok.mevcut_stok
            
            # Stok güncelle
            stok.stok_guncelle(miktar, islem_tipi, kullanici_id)
            
            # Stok hareketi kaydet
            hareket = StokHareket(
                urun_id=urun_id,
                hareket_tipi=islem_tipi,
                miktar=miktar,
                aciklama=aciklama or f"{islem_tipi.capitalize()} işlemi",
                islem_yapan_id=kullanici_id
            )
            db.session.add(hareket)
            
            db.session.commit()
            
            return {
                'success': True,
                'urun_id': urun_id,
                'eski_stok': eski_stok,
                'yeni_stok': stok.mevcut_stok,
                'islem_tipi': islem_tipi,
                'miktar': miktar,
                'stok_durumu': stok.stok_durumu(),
                'message': 'Stok başarıyla güncellendi'
            }
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Stok güncelleme hatası: {str(e)}")



class MLEntegrasyonServisi:
    """ML sistemi entegrasyon servisi - Fiyatlandırma ve karlılık için"""

    @staticmethod
    def gelir_anomali_tespit(
        otel_id: int,
        baslangic: date,
        bitis: date,
        esik_deger: float = 2.0
    ) -> List[Dict]:
        """
        Gelir anomalilerini tespit et
        
        Args:
            otel_id: Otel ID
            baslangic: Başlangıç tarihi
            bitis: Bitiş tarihi
            esik_deger: Z-score eşik değeri (varsayılan: 2.0)
            
        Returns:
            list: Anomali listesi
        """
        try:
            from models import MinibarIslem, MinibarIslemDetay, Oda, Kat, MLAlert
            import numpy as np
            
            # Günlük gelirleri hesapla
            gunluk_gelirler = db.session.query(
                func.date(MinibarIslem.islem_tarihi).label('tarih'),
                func.sum(MinibarIslemDetay.satis_fiyati * MinibarIslemDetay.tuketim).label('gelir')
            ).join(
                MinibarIslem
            ).join(
                Oda
            ).join(
                Kat
            ).filter(
                Kat.otel_id == otel_id,
                MinibarIslem.islem_tarihi >= baslangic,
                MinibarIslem.islem_tarihi <= bitis,
                MinibarIslemDetay.bedelsiz == False
            ).group_by(
                func.date(MinibarIslem.islem_tarihi)
            ).all()
            
            if len(gunluk_gelirler) < 7:
                return []  # Yeterli veri yok
            
            # Gelir değerlerini al
            gelirler = [float(g.gelir or 0) for g in gunluk_gelirler]
            
            # İstatistiksel hesaplamalar
            ortalama = np.mean(gelirler)
            std_sapma = np.std(gelirler)
            
            if std_sapma == 0:
                return []  # Varyasyon yok
            
            # Anomalileri tespit et
            anomaliler = []
            for g in gunluk_gelirler:
                gelir = float(g.gelir or 0)
                z_score = (gelir - ortalama) / std_sapma
                
                if abs(z_score) > esik_deger:
                    # Anomali tespit edildi
                    sapma_yuzdesi = ((gelir - ortalama) / ortalama) * 100
                    
                    anomaliler.append({
                        'tarih': g.tarih.isoformat(),
                        'gelir': round(gelir, 2),
                        'beklenen_gelir': round(ortalama, 2),
                        'z_score': round(z_score, 2),
                        'sapma_yuzdesi': round(sapma_yuzdesi, 2),
                        'anomali_tipi': 'yuksek' if z_score > 0 else 'dusuk',
                        'onem': 'kritik' if abs(z_score) > 3 else 'yuksek'
                    })
                    
                    # ML Alert oluştur
                    alert = MLAlert(
                        alert_type='tuketim_anomali',
                        severity='kritik' if abs(z_score) > 3 else 'yuksek',
                        entity_type='otel',
                        entity_id=otel_id,
                        metric_value=gelir,
                        expected_value=ortalama,
                        deviation_percent=abs(sapma_yuzdesi),
                        message=f"Gelir anomalisi tespit edildi: {g.tarih.isoformat()}",
                        suggested_action=f"Günlük gelir {'normalden %{abs(sapma_yuzdesi):.1f} yüksek' if z_score > 0 else 'normalden %{abs(sapma_yuzdesi):.1f} düşük'}"
                    )
                    db.session.add(alert)
            
            db.session.commit()
            
            return anomaliler
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Gelir anomali tespiti hatası: {str(e)}")

    @staticmethod
    def karlilik_anomali_tespit(
        otel_id: int,
        baslangic: date,
        bitis: date,
        esik_deger: float = 2.0
    ) -> List[Dict]:
        """
        Karlılık anomalilerini tespit et
        
        Args:
            otel_id: Otel ID
            baslangic: Başlangıç tarihi
            bitis: Bitiş tarihi
            esik_deger: Z-score eşik değeri
            
        Returns:
            list: Anomali listesi
        """
        try:
            from models import MinibarIslem, MinibarIslemDetay, Oda, Kat, MLAlert
            import numpy as np
            
            # Günlük kar marjlarını hesapla
            gunluk_karlar = db.session.query(
                func.date(MinibarIslem.islem_tarihi).label('tarih'),
                func.avg(MinibarIslemDetay.kar_orani).label('kar_marji')
            ).join(
                MinibarIslem
            ).join(
                Oda
            ).join(
                Kat
            ).filter(
                Kat.otel_id == otel_id,
                MinibarIslem.islem_tarihi >= baslangic,
                MinibarIslem.islem_tarihi <= bitis,
                MinibarIslemDetay.kar_orani.isnot(None)
            ).group_by(
                func.date(MinibarIslem.islem_tarihi)
            ).all()
            
            if len(gunluk_karlar) < 7:
                return []
            
            # Kar marjı değerlerini al
            kar_marjlari = [float(k.kar_marji or 0) for k in gunluk_karlar]
            
            # İstatistiksel hesaplamalar
            ortalama = np.mean(kar_marjlari)
            std_sapma = np.std(kar_marjlari)
            
            if std_sapma == 0:
                return []
            
            # Anomalileri tespit et
            anomaliler = []
            for k in gunluk_karlar:
                kar_marji = float(k.kar_marji or 0)
                z_score = (kar_marji - ortalama) / std_sapma
                
                if abs(z_score) > esik_deger:
                    sapma_yuzdesi = ((kar_marji - ortalama) / ortalama) * 100 if ortalama != 0 else 0
                    
                    anomaliler.append({
                        'tarih': k.tarih.isoformat(),
                        'kar_marji': round(kar_marji, 2),
                        'beklenen_kar_marji': round(ortalama, 2),
                        'z_score': round(z_score, 2),
                        'sapma_yuzdesi': round(sapma_yuzdesi, 2),
                        'anomali_tipi': 'yuksek' if z_score > 0 else 'dusuk',
                        'onem': 'kritik' if abs(z_score) > 3 else 'yuksek'
                    })
                    
                    # ML Alert oluştur
                    alert = MLAlert(
                        alert_type='tuketim_anomali',
                        severity='kritik' if abs(z_score) > 3 else 'yuksek',
                        entity_type='otel',
                        entity_id=otel_id,
                        metric_value=kar_marji,
                        expected_value=ortalama,
                        deviation_percent=abs(sapma_yuzdesi),
                        message=f"Karlılık anomalisi tespit edildi: {k.tarih.isoformat()}",
                        suggested_action=f"Kar marjı {'normalden %{abs(sapma_yuzdesi):.1f} yüksek' if z_score > 0 else 'normalden %{abs(sapma_yuzdesi):.1f} düşük'}. Fiyatlandırma stratejisini gözden geçirin."
                    )
                    db.session.add(alert)
            
            db.session.commit()
            
            return anomaliler
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Karlılık anomali tespiti hatası: {str(e)}")

    @staticmethod
    def trend_analizi(
        urun_id: int,
        donem: str = 'aylik',
        donem_sayisi: int = 6
    ) -> Dict:
        """
        Ürün trend analizi
        
        Args:
            urun_id: Ürün ID
            donem: 'gunluk', 'haftalik', 'aylik'
            donem_sayisi: Analiz edilecek dönem sayısı
            
        Returns:
            dict: Trend analizi sonuçları
        """
        try:
            from models import MinibarIslem, MinibarIslemDetay
            import numpy as np
            from datetime import timedelta
            
            # Dönem aralığını hesapla
            bugun = date.today()
            
            if donem == 'gunluk':
                baslangic = bugun - timedelta(days=donem_sayisi)
            elif donem == 'haftalik':
                baslangic = bugun - timedelta(weeks=donem_sayisi)
            else:  # aylik
                baslangic = bugun - timedelta(days=donem_sayisi * 30)
            
            # Dönemsel satış verilerini al
            if donem == 'gunluk':
                donemsel_satislar = db.session.query(
                    func.date(MinibarIslem.islem_tarihi).label('donem'),
                    func.sum(MinibarIslemDetay.tuketim).label('satis'),
                    func.avg(MinibarIslemDetay.satis_fiyati).label('ort_fiyat'),
                    func.avg(MinibarIslemDetay.kar_orani).label('ort_kar')
                ).join(
                    MinibarIslem
                ).filter(
                    MinibarIslemDetay.urun_id == urun_id,
                    MinibarIslem.islem_tarihi >= baslangic
                ).group_by(
                    func.date(MinibarIslem.islem_tarihi)
                ).order_by(
                    func.date(MinibarIslem.islem_tarihi)
                ).all()
            else:
                # Haftalık veya aylık için basitleştirilmiş
                donemsel_satislar = db.session.query(
                    func.date(MinibarIslem.islem_tarihi).label('donem'),
                    func.sum(MinibarIslemDetay.tuketim).label('satis'),
                    func.avg(MinibarIslemDetay.satis_fiyati).label('ort_fiyat'),
                    func.avg(MinibarIslemDetay.kar_orani).label('ort_kar')
                ).join(
                    MinibarIslem
                ).filter(
                    MinibarIslemDetay.urun_id == urun_id,
                    MinibarIslem.islem_tarihi >= baslangic
                ).group_by(
                    func.date(MinibarIslem.islem_tarihi)
                ).order_by(
                    func.date(MinibarIslem.islem_tarihi)
                ).all()
            
            if len(donemsel_satislar) < 3:
                return {
                    'urun_id': urun_id,
                    'trend': 'belirsiz',
                    'mesaj': 'Yeterli veri yok'
                }
            
            # Satış miktarlarını al
            satislar = [float(s.satis or 0) for s in donemsel_satislar]
            
            # Trend hesapla (basit lineer regresyon)
            x = np.arange(len(satislar))
            z = np.polyfit(x, satislar, 1)
            egim = z[0]
            
            # Trend yönü
            if egim > 0.5:
                trend = 'artan'
                trend_aciklama = 'Satışlar artış trendinde'
            elif egim < -0.5:
                trend = 'azalan'
                trend_aciklama = 'Satışlar azalış trendinde'
            else:
                trend = 'sabit'
                trend_aciklama = 'Satışlar stabil'
            
            # Ortalamalar
            ort_satis = np.mean(satislar)
            ort_fiyat = np.mean([float(s.ort_fiyat or 0) for s in donemsel_satislar])
            ort_kar = np.mean([float(s.ort_kar or 0) for s in donemsel_satislar])
            
            # Volatilite (standart sapma)
            volatilite = np.std(satislar)
            
            return {
                'urun_id': urun_id,
                'donem': donem,
                'donem_sayisi': len(donemsel_satislar),
                'trend': trend,
                'trend_aciklama': trend_aciklama,
                'egim': round(float(egim), 2),
                'ortalama_satis': round(float(ort_satis), 2),
                'ortalama_fiyat': round(float(ort_fiyat), 2),
                'ortalama_kar_marji': round(float(ort_kar), 2),
                'volatilite': round(float(volatilite), 2),
                'donemsel_veriler': [
                    {
                        'donem': s.donem.isoformat(),
                        'satis': int(s.satis or 0),
                        'ort_fiyat': round(float(s.ort_fiyat or 0), 2),
                        'ort_kar': round(float(s.ort_kar or 0), 2)
                    }
                    for s in donemsel_satislar
                ]
            }
            
        except Exception as e:
            raise Exception(f"Trend analizi hatası: {str(e)}")

    @staticmethod
    def fiyat_optimizasyon_onerisi(
        urun_id: int,
        hedef_kar_marji: float = 50.0
    ) -> Dict:
        """
        Fiyat optimizasyon önerisi
        
        Args:
            urun_id: Ürün ID
            hedef_kar_marji: Hedef kar marjı (%)
            
        Returns:
            dict: Fiyat önerisi
        """
        try:
            # Mevcut fiyatları al
            alis_fiyati = FiyatYonetimServisi.guncel_alis_fiyati_getir(urun_id)
            
            if not alis_fiyati:
                raise ValueError(f"Ürün {urun_id} için alış fiyatı bulunamadı")
            
            # Hedef satış fiyatını hesapla
            hedef_satis_fiyati = alis_fiyati * (1 + (hedef_kar_marji / 100))
            
            # Mevcut ortalama satış fiyatını al
            from models import MinibarIslemDetay
            
            mevcut_ort_fiyat = db.session.query(
                func.avg(MinibarIslemDetay.satis_fiyati)
            ).filter(
                MinibarIslemDetay.urun_id == urun_id,
                MinibarIslemDetay.satis_fiyati.isnot(None)
            ).scalar() or Decimal('0')
            
            # Fiyat farkı
            fiyat_farki = hedef_satis_fiyati - mevcut_ort_fiyat
            fark_yuzdesi = (fiyat_farki / mevcut_ort_fiyat) * 100 if mevcut_ort_fiyat > 0 else 0
            
            # Öneri
            if abs(fark_yuzdesi) < 5:
                oneri = 'Mevcut fiyat optimum seviyede'
                aksiyon = 'Fiyat değişikliği gerekmez'
            elif fark_yuzdesi > 0:
                oneri = f'Fiyat %{abs(fark_yuzdesi):.1f} artırılmalı'
                aksiyon = f'Satış fiyatını {float(hedef_satis_fiyati):.2f} TL yapın'
            else:
                oneri = f'Fiyat %{abs(fark_yuzdesi):.1f} azaltılmalı'
                aksiyon = f'Satış fiyatını {float(hedef_satis_fiyati):.2f} TL yapın'
            
            return {
                'urun_id': urun_id,
                'alis_fiyati': float(alis_fiyati),
                'mevcut_satis_fiyati': float(mevcut_ort_fiyat),
                'hedef_satis_fiyati': float(hedef_satis_fiyati),
                'hedef_kar_marji': hedef_kar_marji,
                'fiyat_farki': float(fiyat_farki),
                'fark_yuzdesi': round(float(fark_yuzdesi), 2),
                'oneri': oneri,
                'aksiyon': aksiyon
            }
            
        except Exception as e:
            raise Exception(f"Fiyat optimizasyon önerisi hatası: {str(e)}")
