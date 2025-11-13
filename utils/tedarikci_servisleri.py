"""
Tedarikçi Yönetim Servisleri
Tedarikçi CRUD, performans hesaplama ve en uygun tedarikçi bulma
"""

from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, or_, func, desc
from models import (
    db, Tedarikci, UrunTedarikciFiyat, SatinAlmaSiparisi, 
    SatinAlmaSiparisDetay, TedarikciPerformans, SiparisDurum
)
from utils.cache_manager import TedarikciCache
import logging

logger = logging.getLogger(__name__)


class TedarikciServisi:
    """Tedarikçi yönetim servisleri"""

    @staticmethod
    def tedarikci_olustur(tedarikci_data: Dict, kullanici_id: int) -> Dict:
        """
        Yeni tedarikçi oluştur

        Args:
            tedarikci_data: {
                'tedarikci_adi': str,
                'telefon': str,
                'email': str,
                'adres': str,
                'vergi_no': str,
                'odeme_kosullari': str
            }
            kullanici_id: İşlemi yapan kullanıcı

        Returns:
            dict: {'success': bool, 'tedarikci_id': int, 'message': str}
        """
        try:
            # Validasyon
            if not tedarikci_data.get('tedarikci_adi'):
                return {
                    'success': False,
                    'message': 'Tedarikçi adı zorunludur'
                }

            # Aynı isimde tedarikçi kontrolü
            mevcut = Tedarikci.query.filter_by(
                tedarikci_adi=tedarikci_data['tedarikci_adi']
            ).first()
            
            if mevcut:
                return {
                    'success': False,
                    'message': 'Bu isimde bir tedarikçi zaten mevcut'
                }

            # İletişim bilgilerini JSON formatında hazırla
            iletisim_bilgileri = {
                'telefon': tedarikci_data.get('telefon', ''),
                'email': tedarikci_data.get('email', ''),
                'adres': tedarikci_data.get('adres', ''),
                'odeme_kosullari': tedarikci_data.get('odeme_kosullari', '')
            }

            # Yeni tedarikçi oluştur
            tedarikci = Tedarikci(
                tedarikci_adi=tedarikci_data['tedarikci_adi'],
                iletisim_bilgileri=iletisim_bilgileri,
                vergi_no=tedarikci_data.get('vergi_no', ''),
                aktif=True
            )

            db.session.add(tedarikci)
            db.session.commit()

            logger.info(
                f"Yeni tedarikçi oluşturuldu: {tedarikci.tedarikci_adi} "
                f"(ID: {tedarikci.id}) - Kullanıcı: {kullanici_id}"
            )

            return {
                'success': True,
                'tedarikci_id': tedarikci.id,
                'message': 'Tedarikçi başarıyla oluşturuldu'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Tedarikçi oluşturma hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Tedarikçi oluşturulurken hata oluştu: {str(e)}'
            }

    @staticmethod
    def tedarikci_guncelle(tedarikci_id: int, tedarikci_data: Dict, kullanici_id: int) -> Dict:
        """
        Tedarikçi bilgilerini güncelle

        Args:
            tedarikci_id: Tedarikçi ID
            tedarikci_data: Güncellenecek veriler
            kullanici_id: İşlemi yapan kullanıcı

        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            tedarikci = Tedarikci.query.get(tedarikci_id)
            
            if not tedarikci:
                return {
                    'success': False,
                    'message': 'Tedarikçi bulunamadı'
                }

            # Tedarikçi adı güncelleniyorsa, aynı isimde başka tedarikçi var mı kontrol et
            if 'tedarikci_adi' in tedarikci_data and \
               tedarikci_data['tedarikci_adi'] != tedarikci.tedarikci_adi:
                mevcut = Tedarikci.query.filter(
                    Tedarikci.tedarikci_adi == tedarikci_data['tedarikci_adi'],
                    Tedarikci.id != tedarikci_id
                ).first()
                
                if mevcut:
                    return {
                        'success': False,
                        'message': 'Bu isimde başka bir tedarikçi zaten mevcut'
                    }
                
                tedarikci.tedarikci_adi = tedarikci_data['tedarikci_adi']

            # İletişim bilgilerini güncelle
            if any(key in tedarikci_data for key in ['telefon', 'email', 'adres', 'odeme_kosullari']):
                iletisim = tedarikci.iletisim_bilgileri or {}
                
                if 'telefon' in tedarikci_data:
                    iletisim['telefon'] = tedarikci_data['telefon']
                if 'email' in tedarikci_data:
                    iletisim['email'] = tedarikci_data['email']
                if 'adres' in tedarikci_data:
                    iletisim['adres'] = tedarikci_data['adres']
                if 'odeme_kosullari' in tedarikci_data:
                    iletisim['odeme_kosullari'] = tedarikci_data['odeme_kosullari']
                
                tedarikci.iletisim_bilgileri = iletisim

            # Vergi no güncelle
            if 'vergi_no' in tedarikci_data:
                tedarikci.vergi_no = tedarikci_data['vergi_no']

            # Aktiflik durumu güncelle
            if 'aktif' in tedarikci_data:
                tedarikci.aktif = tedarikci_data['aktif']

            db.session.commit()

            logger.info(
                f"Tedarikçi güncellendi: {tedarikci.tedarikci_adi} "
                f"(ID: {tedarikci_id}) - Kullanıcı: {kullanici_id}"
            )

            return {
                'success': True,
                'message': 'Tedarikçi başarıyla güncellendi'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Tedarikçi güncelleme hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Tedarikçi güncellenirken hata oluştu: {str(e)}'
            }

    @staticmethod
    def tedarikci_listele(
        aktif: Optional[bool] = None,
        arama: Optional[str] = None,
        sayfa: Optional[int] = None,
        sayfa_basina: int = 50
    ) -> Dict:
        """
        Tedarikçileri listele

        Args:
            aktif: True/False/None (None ise hepsi)
            arama: Tedarikçi adında arama
            sayfa: Sayfa numarası (None ise pagination yok)
            sayfa_basina: Sayfa başına kayıt sayısı

        Returns:
            dict: {
                'tedarikciler': list,
                'toplam': int,
                'sayfa': int,
                'toplam_sayfa': int
            } veya pagination yoksa list
        """
        try:
            query = Tedarikci.query

            # Aktiflik filtresi
            if aktif is not None:
                query = query.filter_by(aktif=aktif)

            # Arama filtresi
            if arama:
                query = query.filter(
                    Tedarikci.tedarikci_adi.ilike(f'%{arama}%')
                )

            # Sıralama
            query = query.order_by(Tedarikci.tedarikci_adi)

            # Pagination
            if sayfa is not None:
                toplam = query.count()
                toplam_sayfa = (toplam + sayfa_basina - 1) // sayfa_basina
                offset = (sayfa - 1) * sayfa_basina
                tedarikciler = query.limit(sayfa_basina).offset(offset).all()
            else:
                tedarikciler = query.all()
                toplam = len(tedarikciler)
                toplam_sayfa = 1

            # Sonuçları formatla
            sonuc = []
            for tedarikci in tedarikciler:
                iletisim = tedarikci.iletisim_bilgileri or {}
                
                sonuc.append({
                    'id': tedarikci.id,
                    'tedarikci_adi': tedarikci.tedarikci_adi,
                    'telefon': iletisim.get('telefon', ''),
                    'email': iletisim.get('email', ''),
                    'adres': iletisim.get('adres', ''),
                    'vergi_no': tedarikci.vergi_no or '',
                    'odeme_kosullari': iletisim.get('odeme_kosullari', ''),
                    'aktif': tedarikci.aktif,
                    'olusturma_tarihi': tedarikci.olusturma_tarihi
                })

            # Pagination varsa dict döndür, yoksa list
            if sayfa is not None:
                return {
                    'tedarikciler': sonuc,
                    'toplam': toplam,
                    'sayfa': sayfa,
                    'toplam_sayfa': toplam_sayfa
                }
            else:
                return sonuc

        except Exception as e:
            logger.error(f"Tedarikçi listeleme hatası: {str(e)}")
            return [] if sayfa is None else {
                'tedarikciler': [],
                'toplam': 0,
                'sayfa': 1,
                'toplam_sayfa': 0
            }

    @staticmethod
    def tedarikci_sil(tedarikci_id: int, kullanici_id: int) -> Dict:
        """
        Tedarikçiyi pasif yap (soft delete)

        Args:
            tedarikci_id: Tedarikçi ID
            kullanici_id: İşlemi yapan kullanıcı

        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            tedarikci = Tedarikci.query.get(tedarikci_id)
            
            if not tedarikci:
                return {
                    'success': False,
                    'message': 'Tedarikçi bulunamadı'
                }

            # Aktif siparişi var mı kontrol et
            aktif_siparis = SatinAlmaSiparisi.query.filter(
                SatinAlmaSiparisi.tedarikci_id == tedarikci_id,
                SatinAlmaSiparisi.durum.in_([
                    SiparisDurum.BEKLEMEDE,
                    SiparisDurum.ONAYLANDI,
                    SiparisDurum.KISMI_TESLIM
                ])
            ).first()

            if aktif_siparis:
                return {
                    'success': False,
                    'message': 'Tedarikçinin aktif siparişi bulunmaktadır, pasif yapılamaz'
                }

            # Tedarikçiyi pasif yap
            tedarikci.aktif = False
            db.session.commit()

            logger.info(
                f"Tedarikçi pasif yapıldı: {tedarikci.tedarikci_adi} "
                f"(ID: {tedarikci_id}) - Kullanıcı: {kullanici_id}"
            )

            return {
                'success': True,
                'message': 'Tedarikçi başarıyla pasif yapıldı'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Tedarikçi silme hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Tedarikçi silinirken hata oluştu: {str(e)}'
            }

    @staticmethod
    def tedarikci_detay(tedarikci_id: int) -> Optional[Dict]:
        """
        Tedarikçi detay bilgilerini getir

        Args:
            tedarikci_id: Tedarikçi ID

        Returns:
            dict: Tedarikçi detayları veya None
        """
        try:
            tedarikci = Tedarikci.query.get(tedarikci_id)
            
            if not tedarikci:
                return None

            iletisim = tedarikci.iletisim_bilgileri or {}

            # Toplam sipariş sayısı
            toplam_siparis = SatinAlmaSiparisi.query.filter_by(
                tedarikci_id=tedarikci_id
            ).count()

            # Aktif sipariş sayısı
            aktif_siparis = SatinAlmaSiparisi.query.filter(
                SatinAlmaSiparisi.tedarikci_id == tedarikci_id,
                SatinAlmaSiparisi.durum.in_([
                    SiparisDurum.BEKLEMEDE,
                    SiparisDurum.ONAYLANDI,
                    SiparisDurum.KISMI_TESLIM
                ])
            ).count()

            # Toplam sipariş tutarı
            toplam_tutar = db.session.query(
                func.sum(SatinAlmaSiparisi.toplam_tutar)
            ).filter_by(tedarikci_id=tedarikci_id).scalar() or Decimal('0')

            return {
                'id': tedarikci.id,
                'tedarikci_adi': tedarikci.tedarikci_adi,
                'telefon': iletisim.get('telefon', ''),
                'email': iletisim.get('email', ''),
                'adres': iletisim.get('adres', ''),
                'vergi_no': tedarikci.vergi_no or '',
                'odeme_kosullari': iletisim.get('odeme_kosullari', ''),
                'aktif': tedarikci.aktif,
                'olusturma_tarihi': tedarikci.olusturma_tarihi,
                'toplam_siparis': toplam_siparis,
                'aktif_siparis': aktif_siparis,
                'toplam_tutar': float(toplam_tutar)
            }

        except Exception as e:
            logger.error(f"Tedarikçi detay getirme hatası: {str(e)}")
            return None

    @staticmethod
    def tedarikci_performans_hesapla(
        tedarikci_id: int,
        donem_baslangic: date,
        donem_bitis: date
    ) -> Dict:
        """
        Tedarikçi performans metriklerini hesapla

        Args:
            tedarikci_id: Tedarikçi ID
            donem_baslangic: Dönem başlangıç tarihi
            donem_bitis: Dönem bitiş tarihi

        Returns:
            dict: {
                'toplam_siparis': int,
                'zamaninda_teslimat': int,
                'zamaninda_teslimat_orani': float,
                'ortalama_teslimat_suresi': int,
                'toplam_tutar': Decimal,
                'performans_skoru': float
            }
        """
        try:
            # Cache'den kontrol et
            cached_result = TedarikciCache.get_tedarikci_performans(
                tedarikci_id, donem_baslangic, donem_bitis
            )
            if cached_result:
                logger.debug(f"Performans cache'den geldi: Tedarikçi {tedarikci_id}")
                return cached_result
            
            tedarikci = Tedarikci.query.get(tedarikci_id)
            
            if not tedarikci:
                return {
                    'success': False,
                    'message': 'Tedarikçi bulunamadı'
                }

            # Dönem içindeki tamamlanmış siparişleri getir
            siparisler = SatinAlmaSiparisi.query.filter(
                SatinAlmaSiparisi.tedarikci_id == tedarikci_id,
                SatinAlmaSiparisi.siparis_tarihi >= datetime.combine(donem_baslangic, datetime.min.time()),
                SatinAlmaSiparisi.siparis_tarihi <= datetime.combine(donem_bitis, datetime.max.time()),
                SatinAlmaSiparisi.durum.in_([
                    SiparisDurum.TESLIM_ALINDI,
                    SiparisDurum.TAMAMLANDI
                ])
            ).all()

            toplam_siparis = len(siparisler)

            if toplam_siparis == 0:
                return {
                    'toplam_siparis': 0,
                    'zamaninda_teslimat': 0,
                    'zamaninda_teslimat_orani': 0.0,
                    'ortalama_teslimat_suresi': 0,
                    'toplam_tutar': Decimal('0'),
                    'performans_skoru': 0.0
                }

            # Zamanında teslimat hesapla
            zamaninda_teslimat = TedarikciServisi._zamaninda_teslimat_hesapla(siparisler)

            # Ortalama teslimat süresi hesapla (gün cinsinden)
            ortalama_teslimat_suresi = TedarikciServisi._ortalama_teslimat_suresi_hesapla(siparisler)

            # Toplam tutar
            toplam_tutar = sum(s.toplam_tutar for s in siparisler)

            # Zamanında teslimat oranı
            zamaninda_oran = (zamaninda_teslimat / toplam_siparis * 100) if toplam_siparis > 0 else 0

            # Performans skoru hesapla
            performans_skoru = TedarikciServisi._performans_skoru_hesapla(
                zamaninda_oran,
                ortalama_teslimat_suresi
            )

            # Performans kaydını veritabanına kaydet/güncelle
            performans_kayit = TedarikciPerformans.query.filter_by(
                tedarikci_id=tedarikci_id,
                donem_baslangic=donem_baslangic,
                donem_bitis=donem_bitis
            ).first()

            if performans_kayit:
                # Güncelle
                performans_kayit.toplam_siparis_sayisi = toplam_siparis
                performans_kayit.zamaninda_teslimat_sayisi = zamaninda_teslimat
                performans_kayit.ortalama_teslimat_suresi = ortalama_teslimat_suresi
                performans_kayit.toplam_siparis_tutari = toplam_tutar
                performans_kayit.performans_skoru = Decimal(str(performans_skoru))
            else:
                # Yeni kayıt oluştur
                performans_kayit = TedarikciPerformans(
                    tedarikci_id=tedarikci_id,
                    donem_baslangic=donem_baslangic,
                    donem_bitis=donem_bitis,
                    toplam_siparis_sayisi=toplam_siparis,
                    zamaninda_teslimat_sayisi=zamaninda_teslimat,
                    ortalama_teslimat_suresi=ortalama_teslimat_suresi,
                    toplam_siparis_tutari=toplam_tutar,
                    performans_skoru=Decimal(str(performans_skoru))
                )
                db.session.add(performans_kayit)

            db.session.commit()

            logger.info(
                f"Tedarikçi performans hesaplandı: {tedarikci.tedarikci_adi} "
                f"(ID: {tedarikci_id}) - Skor: {performans_skoru:.2f}"
            )

            result = {
                'toplam_siparis': toplam_siparis,
                'zamaninda_teslimat': zamaninda_teslimat,
                'zamaninda_teslimat_orani': round(zamaninda_oran, 2),
                'ortalama_teslimat_suresi': ortalama_teslimat_suresi,
                'toplam_tutar': float(toplam_tutar),
                'performans_skoru': round(performans_skoru, 2)
            }
            
            # Cache'e kaydet (5 dakika)
            TedarikciCache.set_tedarikci_performans(
                tedarikci_id, donem_baslangic, donem_bitis, result, timeout=300
            )
            
            return result

        except Exception as e:
            db.session.rollback()
            logger.error(f"Performans hesaplama hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Performans hesaplanırken hata oluştu: {str(e)}'
            }

    @staticmethod
    def _zamaninda_teslimat_hesapla(siparisler: List[SatinAlmaSiparisi]) -> int:
        """
        Zamanında teslimat sayısını hesapla

        Args:
            siparisler: Sipariş listesi

        Returns:
            int: Zamanında teslim edilen sipariş sayısı
        """
        zamaninda = 0
        
        for siparis in siparisler:
            if siparis.gerceklesen_teslimat_tarihi and \
               siparis.tahmini_teslimat_tarihi:
                # Gerçekleşen tarih, tahmini tarihten önce veya aynı ise zamanında
                if siparis.gerceklesen_teslimat_tarihi <= siparis.tahmini_teslimat_tarihi:
                    zamaninda += 1

        return zamaninda

    @staticmethod
    def _ortalama_teslimat_suresi_hesapla(siparisler: List[SatinAlmaSiparisi]) -> int:
        """
        Ortalama teslimat süresini hesapla (gün cinsinden)

        Args:
            siparisler: Sipariş listesi

        Returns:
            int: Ortalama teslimat süresi (gün)
        """
        toplam_sure = 0
        gecerli_siparis = 0

        for siparis in siparisler:
            if siparis.gerceklesen_teslimat_tarihi and siparis.siparis_tarihi:
                # Sipariş tarihi ile teslimat tarihi arasındaki fark
                sure = (siparis.gerceklesen_teslimat_tarihi - siparis.siparis_tarihi.date()).days
                toplam_sure += sure
                gecerli_siparis += 1

        return toplam_sure // gecerli_siparis if gecerli_siparis > 0 else 0

    @staticmethod
    def _performans_skoru_hesapla(
        zamaninda_oran: float,
        ortalama_teslimat_suresi: int
    ) -> float:
        """
        Performans skoru hesapla (0-100 arası)

        Formül:
        - Zamanında teslimat oranı: %70 ağırlık
        - Teslimat hızı: %30 ağırlık
          (Teslimat süresi ne kadar kısa olursa o kadar yüksek puan)

        Args:
            zamaninda_oran: Zamanında teslimat oranı (0-100)
            ortalama_teslimat_suresi: Ortalama teslimat süresi (gün)

        Returns:
            float: Performans skoru (0-100)
        """
        # Zamanında teslimat skoru (%70 ağırlık)
        zamaninda_skoru = zamaninda_oran * 0.7

        # Teslimat hızı skoru (%30 ağırlık)
        # Referans: 7 gün ideal, 14 gün orta, 21+ gün kötü
        if ortalama_teslimat_suresi <= 7:
            hiz_skoru = 100
        elif ortalama_teslimat_suresi <= 14:
            # 7-14 gün arası: 100'den 50'ye doğru lineer azalma
            hiz_skoru = 100 - ((ortalama_teslimat_suresi - 7) * 7.14)
        elif ortalama_teslimat_suresi <= 21:
            # 14-21 gün arası: 50'den 25'e doğru lineer azalma
            hiz_skoru = 50 - ((ortalama_teslimat_suresi - 14) * 3.57)
        else:
            # 21+ gün: 25'den 0'a doğru lineer azalma
            hiz_skoru = max(0, 25 - ((ortalama_teslimat_suresi - 21) * 2.5))

        hiz_skoru = hiz_skoru * 0.3

        # Toplam performans skoru
        performans_skoru = zamaninda_skoru + hiz_skoru

        return min(100, max(0, performans_skoru))

    @staticmethod
    def zamaninda_teslimat_orani_hesapla(tedarikci_id: int, gun_sayisi: int = 90) -> float:
        """
        Son X gündeki zamanında teslimat oranını hesapla

        Args:
            tedarikci_id: Tedarikçi ID
            gun_sayisi: Geriye dönük gün sayısı (varsayılan: 90)

        Returns:
            float: Zamanında teslimat oranı (0-100)
        """
        try:
            baslangic_tarihi = datetime.now(timezone.utc) - timedelta(days=gun_sayisi)

            siparisler = SatinAlmaSiparisi.query.filter(
                SatinAlmaSiparisi.tedarikci_id == tedarikci_id,
                SatinAlmaSiparisi.siparis_tarihi >= baslangic_tarihi,
                SatinAlmaSiparisi.durum.in_([
                    SiparisDurum.TESLIM_ALINDI,
                    SiparisDurum.TAMAMLANDI
                ])
            ).all()

            if not siparisler:
                return 0.0

            zamaninda = TedarikciServisi._zamaninda_teslimat_hesapla(siparisler)
            oran = (zamaninda / len(siparisler) * 100) if siparisler else 0

            return round(oran, 2)

        except Exception as e:
            logger.error(f"Zamanında teslimat oranı hesaplama hatası: {str(e)}")
            return 0.0

    @staticmethod
    def performans_raporu_getir(
        tedarikci_id: int,
        donem_baslangic: Optional[date] = None,
        donem_bitis: Optional[date] = None
    ) -> Optional[Dict]:
        """
        Tedarikçi performans raporunu getir

        Args:
            tedarikci_id: Tedarikçi ID
            donem_baslangic: Dönem başlangıç (None ise son 6 ay)
            donem_bitis: Dönem bitiş (None ise bugün)

        Returns:
            dict: Performans raporu veya None
        """
        try:
            # Varsayılan dönem: Son 6 ay
            if not donem_bitis:
                donem_bitis = date.today()
            if not donem_baslangic:
                donem_baslangic = donem_bitis - timedelta(days=180)

            # Performans hesapla
            performans = TedarikciServisi.tedarikci_performans_hesapla(
                tedarikci_id,
                donem_baslangic,
                donem_bitis
            )

            if 'success' in performans and not performans['success']:
                return None

            # Tedarikçi bilgilerini ekle
            tedarikci = Tedarikci.query.get(tedarikci_id)
            if not tedarikci:
                return None

            performans['tedarikci_adi'] = tedarikci.tedarikci_adi
            performans['donem_baslangic'] = donem_baslangic.isoformat()
            performans['donem_bitis'] = donem_bitis.isoformat()

            return performans

        except Exception as e:
            logger.error(f"Performans raporu getirme hatası: {str(e)}")
            return None

    @staticmethod
    def en_uygun_tedarikci_bul(
        urun_id: int,
        miktar: int,
        tarih: Optional[date] = None
    ) -> Optional[Dict]:
        """
        Ürün için en uygun tedarikçiyi bul (fiyat + performans)

        Algoritma:
        1. Aktif tedarikçi fiyatlarını getir
        2. Minimum miktar kontrolü yap
        3. Her tedarikçi için performans skorunu al
        4. Fiyat ve performans skorunu birleştir
        5. En yüksek skora sahip tedarikçiyi seç

        Skor Hesaplama:
        - Fiyat skoru: %60 ağırlık (düşük fiyat = yüksek skor)
        - Performans skoru: %40 ağırlık

        Args:
            urun_id: Ürün ID
            miktar: Sipariş miktarı
            tarih: Fiyat geçerlilik tarihi (None ise bugün)

        Returns:
            dict: {
                'tedarikci_id': int,
                'tedarikci_adi': str,
                'birim_fiyat': Decimal,
                'toplam_fiyat': Decimal,
                'performans_skoru': float,
                'toplam_skor': float,
                'tahmini_teslimat_suresi': int,
                'minimum_miktar': int
            } veya None
        """
        try:
            # Cache'den kontrol et
            cached_result = TedarikciCache.get_en_uygun_tedarikci(urun_id, miktar)
            if cached_result:
                logger.debug(f"En uygun tedarikçi cache'den geldi: Ürün {urun_id}")
                return cached_result
            
            if not tarih:
                tarih = date.today()

            # Aktif tedarikçi fiyatlarını getir
            fiyatlar = UrunTedarikciFiyat.query.filter(
                UrunTedarikciFiyat.urun_id == urun_id,
                UrunTedarikciFiyat.aktif == True,
                UrunTedarikciFiyat.baslangic_tarihi <= datetime.combine(tarih, datetime.min.time())
            ).filter(
                or_(
                    UrunTedarikciFiyat.bitis_tarihi.is_(None),
                    UrunTedarikciFiyat.bitis_tarihi >= datetime.combine(tarih, datetime.min.time())
                )
            ).all()

            if not fiyatlar:
                logger.warning(f"Ürün için aktif tedarikçi fiyatı bulunamadı: {urun_id}")
                return None

            # Minimum miktar kontrolü - uygun fiyatları filtrele
            uygun_fiyatlar = [f for f in fiyatlar if miktar >= f.minimum_miktar]

            if not uygun_fiyatlar:
                logger.warning(
                    f"Ürün için minimum miktar şartını sağlayan tedarikçi yok: "
                    f"urun_id={urun_id}, miktar={miktar}"
                )
                return None

            # Her tedarikçi için skor hesapla
            tedarikci_skorlari = []

            for fiyat in uygun_fiyatlar:
                # Tedarikçi aktif mi kontrol et
                if not fiyat.tedarikci.aktif:
                    continue

                # Performans skorunu al (son 90 gün)
                performans_skoru = TedarikciServisi.zamaninda_teslimat_orani_hesapla(
                    fiyat.tedarikci_id,
                    gun_sayisi=90
                )

                # Ortalama teslimat süresini al
                baslangic = date.today() - timedelta(days=90)
                siparisler = SatinAlmaSiparisi.query.filter(
                    SatinAlmaSiparisi.tedarikci_id == fiyat.tedarikci_id,
                    SatinAlmaSiparisi.siparis_tarihi >= datetime.combine(baslangic, datetime.min.time()),
                    SatinAlmaSiparisi.durum.in_([
                        SiparisDurum.TESLIM_ALINDI,
                        SiparisDurum.TAMAMLANDI
                    ])
                ).all()

                ortalama_teslimat = TedarikciServisi._ortalama_teslimat_suresi_hesapla(siparisler)
                if ortalama_teslimat == 0:
                    ortalama_teslimat = 10  # Varsayılan: 10 gün

                tedarikci_skorlari.append({
                    'tedarikci_id': fiyat.tedarikci_id,
                    'tedarikci_adi': fiyat.tedarikci.tedarikci_adi,
                    'birim_fiyat': fiyat.alis_fiyati,
                    'toplam_fiyat': fiyat.alis_fiyati * miktar,
                    'performans_skoru': performans_skoru,
                    'ortalama_teslimat': ortalama_teslimat,
                    'minimum_miktar': fiyat.minimum_miktar
                })

            if not tedarikci_skorlari:
                logger.warning(f"Ürün için aktif tedarikçi bulunamadı: {urun_id}")
                return None

            # Fiyat skorunu hesapla (normalize edilmiş)
            # En düşük fiyat = 100 puan, en yüksek fiyat = 0 puan
            fiyatlar_list = [t['birim_fiyat'] for t in tedarikci_skorlari]
            min_fiyat = min(fiyatlar_list)
            max_fiyat = max(fiyatlar_list)

            for tedarikci in tedarikci_skorlari:
                if max_fiyat == min_fiyat:
                    fiyat_skoru = 100
                else:
                    # Düşük fiyat yüksek skor
                    fiyat_skoru = 100 - ((tedarikci['birim_fiyat'] - min_fiyat) / 
                                        (max_fiyat - min_fiyat) * 100)

                # Toplam skor: %60 fiyat + %40 performans
                toplam_skor = (fiyat_skoru * 0.6) + (tedarikci['performans_skoru'] * 0.4)
                tedarikci['fiyat_skoru'] = round(fiyat_skoru, 2)
                tedarikci['toplam_skor'] = round(toplam_skor, 2)

            # En yüksek skora sahip tedarikçiyi seç
            en_uygun = max(tedarikci_skorlari, key=lambda x: x['toplam_skor'])

            logger.info(
                f"En uygun tedarikçi bulundu: {en_uygun['tedarikci_adi']} "
                f"(Skor: {en_uygun['toplam_skor']:.2f}) - Ürün: {urun_id}"
            )

            result = {
                'tedarikci_id': en_uygun['tedarikci_id'],
                'tedarikci_adi': en_uygun['tedarikci_adi'],
                'birim_fiyat': float(en_uygun['birim_fiyat']),
                'toplam_fiyat': float(en_uygun['toplam_fiyat']),
                'performans_skoru': en_uygun['performans_skoru'],
                'fiyat_skoru': en_uygun['fiyat_skoru'],
                'toplam_skor': en_uygun['toplam_skor'],
                'tahmini_teslimat_suresi': en_uygun['ortalama_teslimat'],
                'minimum_miktar': en_uygun['minimum_miktar']
            }
            
            # Cache'e kaydet (10 dakika)
            TedarikciCache.set_en_uygun_tedarikci(urun_id, miktar, result, timeout=600)
            
            return result

        except Exception as e:
            logger.error(f"En uygun tedarikçi bulma hatası: {str(e)}")
            return None

    @staticmethod
    def tedarikci_karsilastir(
        urun_id: int,
        miktar: int,
        tarih: Optional[date] = None
    ) -> List[Dict]:
        """
        Ürün için tüm uygun tedarikçileri karşılaştır

        Args:
            urun_id: Ürün ID
            miktar: Sipariş miktarı
            tarih: Fiyat geçerlilik tarihi (None ise bugün)

        Returns:
            list: Tedarikçi karşılaştırma listesi (skora göre sıralı)
        """
        try:
            if not tarih:
                tarih = date.today()

            # Aktif tedarikçi fiyatlarını getir
            fiyatlar = UrunTedarikciFiyat.query.filter(
                UrunTedarikciFiyat.urun_id == urun_id,
                UrunTedarikciFiyat.aktif == True,
                UrunTedarikciFiyat.baslangic_tarihi <= datetime.combine(tarih, datetime.min.time())
            ).filter(
                or_(
                    UrunTedarikciFiyat.bitis_tarihi.is_(None),
                    UrunTedarikciFiyat.bitis_tarihi >= datetime.combine(tarih, datetime.min.time())
                )
            ).all()

            if not fiyatlar:
                return []

            # Tüm tedarikçiler için bilgileri topla
            karsilastirma = []

            for fiyat in fiyatlar:
                if not fiyat.tedarikci.aktif:
                    continue

                # Minimum miktar kontrolü
                minimum_karsilaniyor = miktar >= fiyat.minimum_miktar

                # Performans skorunu al
                performans_skoru = TedarikciServisi.zamaninda_teslimat_orani_hesapla(
                    fiyat.tedarikci_id,
                    gun_sayisi=90
                )

                # Ortalama teslimat süresi
                baslangic = date.today() - timedelta(days=90)
                siparisler = SatinAlmaSiparisi.query.filter(
                    SatinAlmaSiparisi.tedarikci_id == fiyat.tedarikci_id,
                    SatinAlmaSiparisi.siparis_tarihi >= datetime.combine(baslangic, datetime.min.time()),
                    SatinAlmaSiparisi.durum.in_([
                        SiparisDurum.TESLIM_ALINDI,
                        SiparisDurum.TAMAMLANDI
                    ])
                ).all()

                ortalama_teslimat = TedarikciServisi._ortalama_teslimat_suresi_hesapla(siparisler)

                karsilastirma.append({
                    'tedarikci_id': fiyat.tedarikci_id,
                    'tedarikci_adi': fiyat.tedarikci.tedarikci_adi,
                    'birim_fiyat': float(fiyat.alis_fiyati),
                    'toplam_fiyat': float(fiyat.alis_fiyati * miktar),
                    'minimum_miktar': fiyat.minimum_miktar,
                    'minimum_karsilaniyor': minimum_karsilaniyor,
                    'performans_skoru': performans_skoru,
                    'ortalama_teslimat_suresi': ortalama_teslimat if ortalama_teslimat > 0 else None,
                    'toplam_siparis_sayisi': len(siparisler)
                })

            # Fiyata göre sırala (düşükten yükseğe)
            karsilastirma.sort(key=lambda x: x['birim_fiyat'])

            return karsilastirma

        except Exception as e:
            logger.error(f"Tedarikçi karşılaştırma hatası: {str(e)}")
            return []

    @staticmethod
    def tedarikci_performans_raporu(
        tedarikci_id: Optional[int] = None,
        donem_baslangic: Optional[date] = None,
        donem_bitis: Optional[date] = None,
        otel_id: Optional[int] = None
    ) -> Dict:
        """
        Tedarikçi performans raporu oluştur
        
        Grafik ve tablo görselleştirmeleri için veri hazırlar:
        - Temel performans metrikleri
        - Zaman serisi verileri (aylık performans)
        - Sipariş durum dağılımı
        - Ürün bazında analiz
        
        Args:
            tedarikci_id: Belirli bir tedarikçi (None ise tüm tedarikçiler)
            donem_baslangic: Dönem başlangıç (None ise son 6 ay)
            donem_bitis: Dönem bitiş (None ise bugün)
            otel_id: Otel filtresi (None ise tüm oteller)
        
        Returns:
            dict: {
                'tedarikci_performanslari': list,  # Tedarikçi bazında metrikler
                'zaman_serisi': list,  # Aylık performans verileri
                'siparis_durum_dagilimi': dict,  # Durum bazında sipariş sayıları
                'en_iyi_tedarikciler': list,  # Top 5 tedarikçi
                'en_kotu_tedarikciler': list,  # Bottom 5 tedarikçi
                'genel_istatistikler': dict  # Genel özet
            }
        """
        try:
            # Varsayılan dönem: Son 6 ay
            if not donem_bitis:
                donem_bitis = date.today()
            if not donem_baslangic:
                donem_baslangic = donem_bitis - timedelta(days=180)
            
            # Tedarikçi filtresi
            if tedarikci_id:
                tedarikciler = [Tedarikci.query.get(tedarikci_id)]
                if not tedarikciler[0]:
                    return {
                        'success': False,
                        'message': 'Tedarikçi bulunamadı'
                    }
            else:
                tedarikciler = Tedarikci.query.filter_by(aktif=True).all()
            
            # Tedarikçi bazında performans metrikleri
            tedarikci_performanslari = []
            
            for tedarikci in tedarikciler:
                # Dönem içindeki siparişleri getir
                siparis_query = SatinAlmaSiparisi.query.filter(
                    SatinAlmaSiparisi.tedarikci_id == tedarikci.id,
                    SatinAlmaSiparisi.siparis_tarihi >= datetime.combine(donem_baslangic, datetime.min.time()),
                    SatinAlmaSiparisi.siparis_tarihi <= datetime.combine(donem_bitis, datetime.max.time())
                )
                
                if otel_id:
                    siparis_query = siparis_query.filter_by(otel_id=otel_id)
                
                siparisler = siparis_query.all()
                
                if not siparisler:
                    continue
                
                # Tamamlanmış siparişler
                tamamlanan_siparisler = [
                    s for s in siparisler 
                    if s.durum in [SiparisDurum.TESLIM_ALINDI, SiparisDurum.TAMAMLANDI]
                ]
                
                toplam_siparis = len(siparisler)
                tamamlanan_sayisi = len(tamamlanan_siparisler)
                
                # Zamanında teslimat hesapla
                zamaninda_teslimat = TedarikciServisi._zamaninda_teslimat_hesapla(tamamlanan_siparisler)
                zamaninda_oran = (zamaninda_teslimat / tamamlanan_sayisi * 100) if tamamlanan_sayisi > 0 else 0
                
                # Ortalama teslimat süresi
                ortalama_teslimat = TedarikciServisi._ortalama_teslimat_suresi_hesapla(tamamlanan_siparisler)
                
                # Toplam tutar
                toplam_tutar = sum(s.toplam_tutar for s in siparisler)
                
                # Performans skoru
                performans_skoru = TedarikciServisi._performans_skoru_hesapla(
                    zamaninda_oran,
                    ortalama_teslimat
                )
                
                # İptal edilen siparişler
                iptal_sayisi = len([s for s in siparisler if s.durum == SiparisDurum.IPTAL])
                iptal_orani = (iptal_sayisi / toplam_siparis * 100) if toplam_siparis > 0 else 0
                
                # Geciken siparişler
                geciken_sayisi = len([
                    s for s in tamamlanan_siparisler
                    if s.gerceklesen_teslimat_tarihi and s.tahmini_teslimat_tarihi and
                    s.gerceklesen_teslimat_tarihi > s.tahmini_teslimat_tarihi
                ])
                
                tedarikci_performanslari.append({
                    'tedarikci_id': tedarikci.id,
                    'tedarikci_adi': tedarikci.tedarikci_adi,
                    'toplam_siparis': toplam_siparis,
                    'tamamlanan_siparis': tamamlanan_sayisi,
                    'iptal_edilen_siparis': iptal_sayisi,
                    'iptal_orani': round(iptal_orani, 2),
                    'zamaninda_teslimat': zamaninda_teslimat,
                    'zamaninda_oran': round(zamaninda_oran, 2),
                    'geciken_siparis': geciken_sayisi,
                    'ortalama_teslimat_suresi': ortalama_teslimat,
                    'toplam_tutar': float(toplam_tutar),
                    'performans_skoru': round(performans_skoru, 2)
                })
            
            # Performans skoruna göre sırala
            tedarikci_performanslari.sort(key=lambda x: x['performans_skoru'], reverse=True)
            
            # En iyi ve en kötü tedarikçiler
            en_iyi_tedarikciler = tedarikci_performanslari[:5]
            en_kotu_tedarikciler = tedarikci_performanslari[-5:] if len(tedarikci_performanslari) > 5 else []
            
            # Zaman serisi verileri (aylık performans)
            zaman_serisi = TedarikciServisi._aylik_performans_hesapla(
                tedarikci_id,
                donem_baslangic,
                donem_bitis,
                otel_id
            )
            
            # Sipariş durum dağılımı
            siparis_durum_dagilimi = TedarikciServisi._siparis_durum_dagilimi_hesapla(
                tedarikci_id,
                donem_baslangic,
                donem_bitis,
                otel_id
            )
            
            # Genel istatistikler
            genel_istatistikler = {
                'toplam_tedarikci': len(tedarikci_performanslari),
                'toplam_siparis': sum(t['toplam_siparis'] for t in tedarikci_performanslari),
                'toplam_tutar': sum(t['toplam_tutar'] for t in tedarikci_performanslari),
                'ortalama_performans_skoru': round(
                    sum(t['performans_skoru'] for t in tedarikci_performanslari) / len(tedarikci_performanslari), 2
                ) if tedarikci_performanslari else 0,
                'ortalama_zamaninda_oran': round(
                    sum(t['zamaninda_oran'] for t in tedarikci_performanslari) / len(tedarikci_performanslari), 2
                ) if tedarikci_performanslari else 0
            }
            
            logger.info(
                f"Tedarikçi performans raporu oluşturuldu: "
                f"{len(tedarikci_performanslari)} tedarikçi - "
                f"Dönem: {donem_baslangic} - {donem_bitis}"
            )
            
            return {
                'success': True,
                'tedarikci_performanslari': tedarikci_performanslari,
                'zaman_serisi': zaman_serisi,
                'siparis_durum_dagilimi': siparis_durum_dagilimi,
                'en_iyi_tedarikciler': en_iyi_tedarikciler,
                'en_kotu_tedarikciler': en_kotu_tedarikciler,
                'genel_istatistikler': genel_istatistikler,
                'donem_baslangic': donem_baslangic.isoformat(),
                'donem_bitis': donem_bitis.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Tedarikçi performans raporu hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Performans raporu oluşturulurken hata oluştu: {str(e)}'
            }

    @staticmethod
    def _aylik_performans_hesapla(
        tedarikci_id: Optional[int],
        donem_baslangic: date,
        donem_bitis: date,
        otel_id: Optional[int]
    ) -> List[Dict]:
        """
        Aylık performans verilerini hesapla (grafik için)
        
        Args:
            tedarikci_id: Tedarikçi ID (None ise tüm tedarikçiler)
            donem_baslangic: Dönem başlangıç
            donem_bitis: Dönem bitiş
            otel_id: Otel filtresi
        
        Returns:
            list: [
                {
                    'ay': str,  # 'YYYY-MM' formatında
                    'ay_adi': str,  # 'Ocak 2024' formatında
                    'siparis_sayisi': int,
                    'zamaninda_oran': float,
                    'ortalama_teslimat_suresi': int,
                    'toplam_tutar': float
                }
            ]
        """
        try:
            aylik_veriler = []
            
            # Ay ay döngü
            current_date = date(donem_baslangic.year, donem_baslangic.month, 1)
            
            while current_date <= donem_bitis:
                # Ayın son günü
                if current_date.month == 12:
                    ay_sonu = date(current_date.year + 1, 1, 1) - timedelta(days=1)
                else:
                    ay_sonu = date(current_date.year, current_date.month + 1, 1) - timedelta(days=1)
                
                # Dönem bitişini aşmayalım
                if ay_sonu > donem_bitis:
                    ay_sonu = donem_bitis
                
                # Bu ay için siparişleri getir
                siparis_query = SatinAlmaSiparisi.query.filter(
                    SatinAlmaSiparisi.siparis_tarihi >= datetime.combine(current_date, datetime.min.time()),
                    SatinAlmaSiparisi.siparis_tarihi <= datetime.combine(ay_sonu, datetime.max.time())
                )
                
                if tedarikci_id:
                    siparis_query = siparis_query.filter_by(tedarikci_id=tedarikci_id)
                
                if otel_id:
                    siparis_query = siparis_query.filter_by(otel_id=otel_id)
                
                siparisler = siparis_query.all()
                
                # Tamamlanmış siparişler
                tamamlanan = [
                    s for s in siparisler
                    if s.durum in [SiparisDurum.TESLIM_ALINDI, SiparisDurum.TAMAMLANDI]
                ]
                
                siparis_sayisi = len(siparisler)
                
                if siparis_sayisi > 0:
                    # Zamanında teslimat oranı
                    zamaninda = TedarikciServisi._zamaninda_teslimat_hesapla(tamamlanan)
                    zamaninda_oran = (zamaninda / len(tamamlanan) * 100) if tamamlanan else 0
                    
                    # Ortalama teslimat süresi
                    ortalama_teslimat = TedarikciServisi._ortalama_teslimat_suresi_hesapla(tamamlanan)
                    
                    # Toplam tutar
                    toplam_tutar = sum(s.toplam_tutar for s in siparisler)
                    
                    # Ay adı
                    ay_adlari = [
                        'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                        'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'
                    ]
                    ay_adi = f"{ay_adlari[current_date.month - 1]} {current_date.year}"
                    
                    aylik_veriler.append({
                        'ay': current_date.strftime('%Y-%m'),
                        'ay_adi': ay_adi,
                        'siparis_sayisi': siparis_sayisi,
                        'zamaninda_oran': round(zamaninda_oran, 2),
                        'ortalama_teslimat_suresi': ortalama_teslimat,
                        'toplam_tutar': float(toplam_tutar)
                    })
                
                # Bir sonraki ay
                if current_date.month == 12:
                    current_date = date(current_date.year + 1, 1, 1)
                else:
                    current_date = date(current_date.year, current_date.month + 1, 1)
            
            return aylik_veriler
            
        except Exception as e:
            logger.error(f"Aylık performans hesaplama hatası: {str(e)}")
            return []

    @staticmethod
    def _siparis_durum_dagilimi_hesapla(
        tedarikci_id: Optional[int],
        donem_baslangic: date,
        donem_bitis: date,
        otel_id: Optional[int]
    ) -> Dict:
        """
        Sipariş durum dağılımını hesapla (pasta grafik için)
        
        Args:
            tedarikci_id: Tedarikçi ID (None ise tüm tedarikçiler)
            donem_baslangic: Dönem başlangıç
            donem_bitis: Dönem bitiş
            otel_id: Otel filtresi
        
        Returns:
            dict: {
                'beklemede': int,
                'onaylandi': int,
                'kismi_teslim': int,
                'teslim_alindi': int,
                'tamamlandi': int,
                'iptal': int
            }
        """
        try:
            siparis_query = SatinAlmaSiparisi.query.filter(
                SatinAlmaSiparisi.siparis_tarihi >= datetime.combine(donem_baslangic, datetime.min.time()),
                SatinAlmaSiparisi.siparis_tarihi <= datetime.combine(donem_bitis, datetime.max.time())
            )
            
            if tedarikci_id:
                siparis_query = siparis_query.filter_by(tedarikci_id=tedarikci_id)
            
            if otel_id:
                siparis_query = siparis_query.filter_by(otel_id=otel_id)
            
            siparisler = siparis_query.all()
            
            # Durum bazında sayıları hesapla
            dagilim = {
                'beklemede': 0,
                'onaylandi': 0,
                'kismi_teslim': 0,
                'teslim_alindi': 0,
                'tamamlandi': 0,
                'iptal': 0
            }
            
            for siparis in siparisler:
                durum_key = siparis.durum.value
                if durum_key in dagilim:
                    dagilim[durum_key] += 1
            
            return dagilim
            
        except Exception as e:
            logger.error(f"Sipariş durum dağılımı hesaplama hatası: {str(e)}")
            return {
                'beklemede': 0,
                'onaylandi': 0,
                'kismi_teslim': 0,
                'teslim_alindi': 0,
                'tamamlandi': 0,
                'iptal': 0
            }
