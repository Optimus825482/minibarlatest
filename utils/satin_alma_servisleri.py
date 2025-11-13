"""
Satın Alma Yönetim Servisleri
Sipariş oluşturma, takip, stok entegrasyonu ve otomatik sipariş önerileri
"""

from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, or_, func, desc
from models import (
    db, SatinAlmaSiparisi, SatinAlmaSiparisDetay, Tedarikci,
    UrunStok, StokHareket, Urun, SiparisDurum, TedarikciPerformans
)
from utils.tedarikci_servisleri import TedarikciServisi
from utils.cache_manager import TedarikciCache
import logging
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import os
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


class SatinAlmaServisi:
    """Satın alma yönetim servisleri"""

    @staticmethod
    def siparis_no_uret() -> str:
        """
        Benzersiz sipariş numarası üret
        Format: SA-YYYYMMDD-XXXX
        
        Returns:
            str: Sipariş numarası
        """
        try:
            bugun = datetime.now(timezone.utc)
            tarih_str = bugun.strftime('%Y%m%d')
            
            # Bugün oluşturulan son sipariş numarasını bul
            son_siparis = SatinAlmaSiparisi.query.filter(
                SatinAlmaSiparisi.siparis_no.like(f'SA-{tarih_str}-%')
            ).order_by(desc(SatinAlmaSiparisi.siparis_no)).first()
            
            if son_siparis:
                # Son numarayı parse et ve 1 artır
                son_no = int(son_siparis.siparis_no.split('-')[-1])
                yeni_no = son_no + 1
            else:
                yeni_no = 1
            
            siparis_no = f'SA-{tarih_str}-{yeni_no:04d}'
            
            return siparis_no
            
        except Exception as e:
            logger.error(f"Sipariş no üretme hatası: {str(e)}")
            # Fallback: timestamp bazlı
            return f'SA-{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}'

    @staticmethod
    def siparis_olustur(siparis_data: Dict, kullanici_id: int) -> Dict:
        """
        Yeni satın alma siparişi oluştur

        Args:
            siparis_data: {
                'tedarikci_id': int,
                'otel_id': int,
                'urunler': [
                    {'urun_id': int, 'miktar': int, 'birim_fiyat': Decimal}
                ],
                'tahmini_teslimat_tarihi': date,
                'aciklama': str (optional)
            }
            kullanici_id: Siparişi oluşturan kullanıcı

        Returns:
            dict: {
                'success': bool,
                'siparis_id': int,
                'siparis_no': str,
                'toplam_tutar': Decimal,
                'message': str
            }
        """
        try:
            # Validasyon
            if not siparis_data.get('otel_id'):
                return {
                    'success': False,
                    'message': 'Otel seçimi zorunludur'
                }
            
            if not siparis_data.get('urunler') or len(siparis_data['urunler']) == 0:
                return {
                    'success': False,
                    'message': 'En az bir ürün seçilmelidir'
                }
            
            # Tedarikçi kontrolü (opsiyonel)
            tedarikci = None
            tedarikci_id = siparis_data.get('tedarikci_id')
            if tedarikci_id:
                tedarikci = Tedarikci.query.get(tedarikci_id)
                if not tedarikci:
                    return {
                        'success': False,
                        'message': 'Tedarikçi bulunamadı'
                    }
                
                if not tedarikci.aktif:
                    return {
                        'success': False,
                        'message': 'Seçilen tedarikçi pasif durumda'
                    }
            
            # Sipariş numarası üret
            siparis_no = SatinAlmaServisi.siparis_no_uret()
            
            # Toplam tutarı hesapla
            toplam_tutar = Decimal('0')
            for urun_data in siparis_data['urunler']:
                miktar = urun_data.get('miktar', 0)
                birim_fiyat = Decimal(str(urun_data.get('birim_fiyat', 0)))
                toplam_tutar += miktar * birim_fiyat
            
            # Sipariş oluştur
            siparis = SatinAlmaSiparisi(
                siparis_no=siparis_no,
                tedarikci_id=tedarikci_id,  # None olabilir
                otel_id=siparis_data['otel_id'],
                siparis_tarihi=datetime.now(timezone.utc),
                tahmini_teslimat_tarihi=siparis_data.get('tahmini_teslimat_tarihi'),
                durum='beklemede',
                toplam_tutar=toplam_tutar,
                aciklama=siparis_data.get('aciklama', ''),
                olusturan_id=kullanici_id
            )
            
            db.session.add(siparis)
            db.session.flush()  # ID'yi al
            
            # Sipariş detaylarını oluştur
            for urun_data in siparis_data['urunler']:
                urun_id = urun_data.get('urun_id')
                miktar = urun_data.get('miktar', 0)
                birim_fiyat = Decimal(str(urun_data.get('birim_fiyat', 0)))
                
                # Ürün kontrolü
                urun = Urun.query.get(urun_id)
                if not urun:
                    db.session.rollback()
                    return {
                        'success': False,
                        'message': f'Ürün bulunamadı: ID {urun_id}'
                    }
                
                detay = SatinAlmaSiparisDetay(
                    siparis_id=siparis.id,
                    urun_id=urun_id,
                    miktar=miktar,
                    birim_fiyat=birim_fiyat,
                    toplam_fiyat=miktar * birim_fiyat,
                    teslim_alinan_miktar=0
                )
                
                db.session.add(detay)
            
            db.session.commit()
            
            tedarikci_adi = tedarikci.tedarikci_adi if tedarikci else 'Belirtilmemiş'
            logger.info(
                f"Yeni sipariş oluşturuldu: {siparis_no} "
                f"(ID: {siparis.id}) - Tedarikçi: {tedarikci_adi} "
                f"- Tutar: {toplam_tutar} - Kullanıcı: {kullanici_id}"
            )
            
            return {
                'success': True,
                'siparis_id': siparis.id,
                'siparis_no': siparis_no,
                'toplam_tutar': float(toplam_tutar),
                'message': 'Sipariş başarıyla oluşturuldu'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Sipariş oluşturma hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Sipariş oluşturulurken hata oluştu: {str(e)}'
            }

    @staticmethod
    def siparis_durum_guncelle(
        siparis_id: int,
        yeni_durum: str,
        kullanici_id: int,
        gerceklesen_teslimat_tarihi: Optional[date] = None
    ) -> Dict:
        """
        Sipariş durumunu güncelle

        Args:
            siparis_id: Sipariş ID
            yeni_durum: Yeni durum (SiparisDurum enum değeri)
            kullanici_id: İşlemi yapan kullanıcı
            gerceklesen_teslimat_tarihi: Teslimat tarihi (teslim_alindi durumu için)

        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            siparis = SatinAlmaSiparisi.query.get(siparis_id)
            
            if not siparis:
                return {
                    'success': False,
                    'message': 'Sipariş bulunamadı'
                }
            
            # Durum geçişi kontrolü
            eski_durum = siparis.durum
            
            # İptal edilen sipariş tekrar aktif edilemez
            if eski_durum == SiparisDurum.IPTAL:
                return {
                    'success': False,
                    'message': 'İptal edilen sipariş güncellenemez'
                }
            
            # Tamamlanan sipariş güncellenemez
            if eski_durum == SiparisDurum.TAMAMLANDI:
                return {
                    'success': False,
                    'message': 'Tamamlanan sipariş güncellenemez'
                }
            
            # Durum güncelle
            try:
                siparis.durum = SiparisDurum(yeni_durum)
            except ValueError:
                return {
                    'success': False,
                    'message': f'Geçersiz sipariş durumu: {yeni_durum}'
                }
            
            # Onaylanan sipariş için onaylayan kullanıcıyı kaydet
            if siparis.durum == 'onaylandi':
                siparis.onaylayan_id = kullanici_id
            
            # Teslim alınan sipariş için teslimat tarihini kaydet
            if siparis.durum in [SiparisDurum.TESLIM_ALINDI, SiparisDurum.KISMI_TESLIM]:
                if gerceklesen_teslimat_tarihi:
                    siparis.gerceklesen_teslimat_tarihi = gerceklesen_teslimat_tarihi
                else:
                    siparis.gerceklesen_teslimat_tarihi = date.today()
            
            db.session.commit()
            
            # Sipariş tamamlandıysa tedarikçi performans cache'ini temizle
            if siparis.durum in [SiparisDurum.TESLIM_ALINDI, SiparisDurum.TAMAMLANDI] and siparis.tedarikci_id:
                TedarikciCache.invalidate_tedarikci_performans(siparis.tedarikci_id)
                logger.debug(f"Tedarikçi {siparis.tedarikci_id} performans cache temizlendi")
            
            eski_durum_str = eski_durum if isinstance(eski_durum, str) else eski_durum.value
            logger.info(
                f"Sipariş durumu güncellendi: {siparis.siparis_no} "
                f"({eski_durum_str} -> {yeni_durum}) - Kullanıcı: {kullanici_id}"
            )
            
            return {
                'success': True,
                'message': 'Sipariş durumu başarıyla güncellendi'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Sipariş durum güncelleme hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Sipariş durumu güncellenirken hata oluştu: {str(e)}'
            }

    @staticmethod
    def siparis_listele(
        otel_id: Optional[int] = None,
        durum: Optional[str] = None,
        tedarikci_id: Optional[int] = None,
        baslangic_tarihi: Optional[date] = None,
        bitis_tarihi: Optional[date] = None,
        sayfa: int = 1,
        sayfa_basina: int = 50
    ) -> Dict:
        """
        Siparişleri filtrele ve listele

        Args:
            otel_id: Otel filtresi
            durum: Durum filtresi
            tedarikci_id: Tedarikçi filtresi
            baslangic_tarihi: Başlangıç tarihi filtresi
            bitis_tarihi: Bitiş tarihi filtresi
            sayfa: Sayfa numarası
            sayfa_basina: Sayfa başına kayıt sayısı

        Returns:
            dict: {
                'siparisler': list,
                'toplam': int,
                'sayfa': int,
                'toplam_sayfa': int
            }
        """
        try:
            # Eager loading ile N+1 sorgu problemini önle
            query = SatinAlmaSiparisi.query.options(
                db.joinedload(SatinAlmaSiparisi.tedarikci),
                db.joinedload(SatinAlmaSiparisi.otel),
                db.joinedload(SatinAlmaSiparisi.olusturan)
            )
            
            # Filtreler
            if otel_id:
                query = query.filter_by(otel_id=otel_id)
            
            if durum:
                try:
                    query = query.filter_by(durum=SiparisDurum(durum))
                except ValueError:
                    pass
            
            if tedarikci_id:
                query = query.filter_by(tedarikci_id=tedarikci_id)
            
            if baslangic_tarihi:
                query = query.filter(
                    SatinAlmaSiparisi.siparis_tarihi >= datetime.combine(baslangic_tarihi, datetime.min.time())
                )
            
            if bitis_tarihi:
                query = query.filter(
                    SatinAlmaSiparisi.siparis_tarihi <= datetime.combine(bitis_tarihi, datetime.max.time())
                )
            
            # Sıralama: En yeni önce
            query = query.order_by(desc(SatinAlmaSiparisi.siparis_tarihi))
            
            # Toplam kayıt sayısı
            toplam = query.count()
            
            # Pagination
            toplam_sayfa = (toplam + sayfa_basina - 1) // sayfa_basina
            offset = (sayfa - 1) * sayfa_basina
            
            siparisler = query.limit(sayfa_basina).offset(offset).all()
            
            # Sonuçları formatla
            sonuc = []
            for siparis in siparisler:
                sonuc.append({
                    'id': siparis.id,
                    'siparis_no': siparis.siparis_no,
                    'tedarikci_id': siparis.tedarikci_id,
                    'tedarikci_adi': siparis.tedarikci.tedarikci_adi if siparis.tedarikci else 'Belirtilmemiş',
                    'otel_id': siparis.otel_id,
                    'otel_adi': siparis.otel.ad,
                    'siparis_tarihi': siparis.siparis_tarihi,
                    'tahmini_teslimat_tarihi': siparis.tahmini_teslimat_tarihi,
                    'gerceklesen_teslimat_tarihi': siparis.gerceklesen_teslimat_tarihi,
                    'durum': siparis.durum.value if hasattr(siparis.durum, 'value') else siparis.durum,
                    'toplam_tutar': float(siparis.toplam_tutar),
                    'aciklama': siparis.aciklama or '',
                    'olusturan_id': siparis.olusturan_id,
                    'olusturan_adi': f"{siparis.olusturan.ad} {siparis.olusturan.soyad}" if siparis.olusturan else '',
                    'detay_sayisi': len(siparis.detaylar)
                })
            
            return {
                'siparisler': sonuc,
                'toplam': toplam,
                'sayfa': sayfa,
                'toplam_sayfa': toplam_sayfa
            }
            
        except Exception as e:
            logger.error(f"Sipariş listeleme hatası: {str(e)}")
            return {
                'siparisler': [],
                'toplam': 0,
                'sayfa': 1,
                'toplam_sayfa': 0
            }

    @staticmethod
    def siparis_detay(siparis_id: int) -> Optional[Dict]:
        """
        Sipariş detaylarını getir

        Args:
            siparis_id: Sipariş ID

        Returns:
            dict: Sipariş detayları veya None
        """
        try:
            # Eager loading ile ilişkili verileri tek sorguda getir
            siparis = SatinAlmaSiparisi.query.options(
                db.joinedload(SatinAlmaSiparisi.tedarikci),
                db.joinedload(SatinAlmaSiparisi.otel),
                db.joinedload(SatinAlmaSiparisi.olusturan),
                db.joinedload(SatinAlmaSiparisi.onaylayan),
                db.joinedload(SatinAlmaSiparisi.detaylar).joinedload(SatinAlmaSiparisDetay.urun)
            ).get(siparis_id)
            
            if not siparis:
                return None
            
            # Detayları formatla
            detaylar = []
            for detay in siparis.detaylar:
                detaylar.append({
                    'id': detay.id,
                    'urun_id': detay.urun_id,
                    'urun_adi': detay.urun.urun_adi,
                    'miktar': detay.miktar,
                    'birim_fiyat': float(detay.birim_fiyat),
                    'toplam_fiyat': float(detay.toplam_fiyat),
                    'teslim_alinan_miktar': detay.teslim_alinan_miktar,
                    'kalan_miktar': detay.miktar - detay.teslim_alinan_miktar
                })
            
            return {
                'id': siparis.id,
                'siparis_no': siparis.siparis_no,
                'tedarikci_id': siparis.tedarikci_id,
                'tedarikci_adi': siparis.tedarikci.tedarikci_adi if siparis.tedarikci else 'Belirtilmemiş',
                'tedarikci_telefon': siparis.tedarikci.iletisim_bilgileri.get('telefon', '') if siparis.tedarikci and siparis.tedarikci.iletisim_bilgileri else '',
                'otel_id': siparis.otel_id,
                'otel_adi': siparis.otel.ad,
                'siparis_tarihi': siparis.siparis_tarihi,
                'tahmini_teslimat_tarihi': siparis.tahmini_teslimat_tarihi,
                'gerceklesen_teslimat_tarihi': siparis.gerceklesen_teslimat_tarihi,
                'durum': siparis.durum if isinstance(siparis.durum, str) else siparis.durum.value,
                'toplam_tutar': float(siparis.toplam_tutar),
                'aciklama': siparis.aciklama or '',
                'olusturan_id': siparis.olusturan_id,
                'olusturan_adi': f"{siparis.olusturan.ad} {siparis.olusturan.soyad}" if siparis.olusturan else '',
                'onaylayan_id': siparis.onaylayan_id,
                'onaylayan_adi': f"{siparis.onaylayan.ad} {siparis.onaylayan.soyad}" if siparis.onaylayan else '',
                'detaylar': detaylar
            }
            
        except Exception as e:
            logger.error(f"Sipariş detay getirme hatası: {str(e)}")
            return None


    @staticmethod
    def siparis_iptal(siparis_id: int, kullanici_id: int, iptal_nedeni: str = '') -> Dict:
        """
        Siparişi iptal et

        Args:
            siparis_id: Sipariş ID
            kullanici_id: İşlemi yapan kullanıcı
            iptal_nedeni: İptal nedeni

        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            siparis = SatinAlmaSiparisi.query.get(siparis_id)
            
            if not siparis:
                return {
                    'success': False,
                    'message': 'Sipariş bulunamadı'
                }
            
            # Sadece beklemede veya onaylanmış siparişler iptal edilebilir
            if siparis.durum not in ['beklemede', 'onaylandi']:
                return {
                    'success': False,
                    'message': 'Bu durumda olan sipariş iptal edilemez'
                }
            
            siparis.durum = SiparisDurum.IPTAL
            
            # İptal nedenini açıklamaya ekle
            if iptal_nedeni:
                mevcut_aciklama = siparis.aciklama or ''
                siparis.aciklama = f"{mevcut_aciklama}\n\nİPTAL NEDENİ: {iptal_nedeni}"
            
            db.session.commit()
            
            logger.info(
                f"Sipariş iptal edildi: {siparis.siparis_no} "
                f"- Kullanıcı: {kullanici_id} - Neden: {iptal_nedeni}"
            )
            
            return {
                'success': True,
                'message': 'Sipariş başarıyla iptal edildi'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Sipariş iptal hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Sipariş iptal edilirken hata oluştu: {str(e)}'
            }


    @staticmethod
    def otomatik_siparis_onerisi_olustur(otel_id: int, gun_sayisi: int = 30) -> List[Dict]:
        """
        Kritik stok seviyesindeki ürünler için otomatik sipariş önerisi oluştur

        Algoritma:
        1. Kritik stok seviyesinin altındaki ürünleri bul
        2. Son X günlük tüketim ortalamasını hesapla
        3. Önerilen sipariş miktarını hesapla (ortalama tüketim * 2)
        4. Her ürün için en uygun tedarikçiyi bul

        Args:
            otel_id: Otel ID
            gun_sayisi: Tüketim analizi için geriye dönük gün sayısı (varsayılan: 30)

        Returns:
            list: [
                {
                    'urun_id': int,
                    'urun_adi': str,
                    'mevcut_stok': int,
                    'kritik_seviye': int,
                    'minimum_stok': int,
                    'ortalama_gunluk_tuketim': float,
                    'tahmini_tuketim_30_gun': int,
                    'onerilen_miktar': int,
                    'en_uygun_tedarikci': dict or None
                }
            ]
        """
        try:
            # Kritik stok seviyesinin altındaki ürünleri bul
            kritik_stoklar = UrunStok.query.filter(
                UrunStok.otel_id == otel_id,
                UrunStok.mevcut_stok <= UrunStok.kritik_stok_seviyesi
            ).all()
            
            if not kritik_stoklar:
                logger.info(f"Otel {otel_id} için kritik stok seviyesinde ürün yok")
                return []
            
            oneriler = []
            baslangic_tarihi = datetime.now(timezone.utc) - timedelta(days=gun_sayisi)
            
            for stok in kritik_stoklar:
                try:
                    # Son X günlük çıkış hareketlerini al
                    cikis_hareketleri = StokHareket.query.filter(
                        StokHareket.urun_id == stok.urun_id,
                        StokHareket.hareket_tipi == 'cikis',
                        StokHareket.islem_tarihi >= baslangic_tarihi
                    ).all()
                    
                    # Toplam tüketim
                    toplam_tuketim = sum(h.miktar for h in cikis_hareketleri)
                    
                    # Ortalama günlük tüketim
                    ortalama_gunluk = toplam_tuketim / gun_sayisi if gun_sayisi > 0 else 0
                    
                    # 30 günlük tahmini tüketim
                    tahmini_tuketim_30_gun = int(ortalama_gunluk * 30)
                    
                    # Önerilen miktar hesapla
                    # Formül: (Minimum stok - Mevcut stok) + Tahmini 30 günlük tüketim
                    eksik_miktar = max(0, stok.minimum_stok - stok.mevcut_stok)
                    onerilen_miktar = eksik_miktar + tahmini_tuketim_30_gun
                    
                    # Minimum 1 birim sipariş öner
                    if onerilen_miktar < 1:
                        onerilen_miktar = max(1, int(ortalama_gunluk * 7))  # En az 1 haftalık
                    
                    # En uygun tedarikçiyi bul
                    en_uygun_tedarikci = TedarikciServisi.en_uygun_tedarikci_bul(
                        urun_id=stok.urun_id,
                        miktar=onerilen_miktar
                    )
                    
                    # Öncelik hesapla
                    stok_orani = (stok.kritik_stok_seviyesi - stok.mevcut_stok) / max(stok.kritik_stok_seviyesi, 1)
                    if stok_orani >= 0.8:
                        oncelik = 'kritik'
                    elif stok_orani >= 0.5:
                        oncelik = 'dikkat'
                    else:
                        oncelik = 'normal'
                    
                    # Stok yüzdesi hesapla (kritik seviyeye göre)
                    if stok.kritik_stok_seviyesi > 0:
                        stok_yuzde = (stok.mevcut_stok / stok.kritik_stok_seviyesi) * 100
                    else:
                        stok_yuzde = 100 if stok.mevcut_stok > 0 else 0
                    
                    oneri = {
                        'urun_id': stok.urun_id,
                        'urun_adi': stok.urun.urun_adi,
                        'birim': stok.urun.birim,  # Ürün birimi eklendi
                        'mevcut_stok': stok.mevcut_stok,
                        'kritik_seviye': stok.kritik_stok_seviyesi,
                        'minimum_stok': stok.minimum_stok,
                        'ortalama_gunluk_tuketim': round(ortalama_gunluk, 2),
                        'tahmini_tuketim': round(ortalama_gunluk, 2),  # Template için alias
                        'tahmini_tuketim_30_gun': tahmini_tuketim_30_gun,
                        'onerilen_miktar': onerilen_miktar,
                        'oncelik': oncelik,  # Öncelik eklendi
                        'stok_yuzde': round(stok_yuzde, 1),  # Stok yüzdesi eklendi
                        'en_uygun_tedarikci': en_uygun_tedarikci
                    }
                    
                    oneriler.append(oneri)
                    
                except Exception as e:
                    logger.error(f"Ürün {stok.urun_id} için öneri oluşturma hatası: {str(e)}")
                    continue
            
            # Öncelik sırasına göre sırala: En kritik olanlar önce
            # Kritiklik = (Kritik seviye - Mevcut stok) / Kritik seviye
            oneriler.sort(
                key=lambda x: (x['kritik_seviye'] - x['mevcut_stok']) / max(x['kritik_seviye'], 1),
                reverse=True
            )
            
            logger.info(
                f"Otel {otel_id} için {len(oneriler)} adet sipariş önerisi oluşturuldu"
            )
            
            return oneriler
            
        except Exception as e:
            logger.error(f"Otomatik sipariş önerisi oluşturma hatası: {str(e)}")
            return []

    @staticmethod
    def siparis_onerisi_onayla(
        otel_id: int,
        oneri_listesi: List[Dict],
        kullanici_id: int
    ) -> Dict:
        """
        Sipariş önerilerini onaylayıp siparişleri oluştur

        Args:
            otel_id: Otel ID
            oneri_listesi: [
                {
                    'urun_id': int,
                    'miktar': int,
                    'tedarikci_id': int,
                    'birim_fiyat': Decimal
                }
            ]
            kullanici_id: İşlemi yapan kullanıcı

        Returns:
            dict: {
                'success': bool,
                'olusturulan_siparisler': list,
                'message': str
            }
        """
        try:
            if not oneri_listesi:
                return {
                    'success': False,
                    'message': 'Onaylanacak öneri bulunamadı'
                }
            
            # Tedarikçilere göre grupla
            tedarikci_gruplari = {}
            for oneri in oneri_listesi:
                tedarikci_id = oneri.get('tedarikci_id')
                if not tedarikci_id:
                    continue
                
                if tedarikci_id not in tedarikci_gruplari:
                    tedarikci_gruplari[tedarikci_id] = []
                
                tedarikci_gruplari[tedarikci_id].append(oneri)
            
            # Her tedarikçi için ayrı sipariş oluştur
            olusturulan_siparisler = []
            
            for tedarikci_id, urunler in tedarikci_gruplari.items():
                # Tahmini teslimat tarihi: 7 gün sonra
                tahmini_teslimat = date.today() + timedelta(days=7)
                
                siparis_data = {
                    'tedarikci_id': tedarikci_id,
                    'otel_id': otel_id,
                    'urunler': [
                        {
                            'urun_id': u['urun_id'],
                            'miktar': u['miktar'],
                            'birim_fiyat': u['birim_fiyat']
                        }
                        for u in urunler
                    ],
                    'tahmini_teslimat_tarihi': tahmini_teslimat,
                    'aciklama': 'Otomatik sipariş önerisi ile oluşturuldu'
                }
                
                sonuc = SatinAlmaServisi.siparis_olustur(siparis_data, kullanici_id)
                
                if sonuc['success']:
                    olusturulan_siparisler.append({
                        'siparis_id': sonuc['siparis_id'],
                        'siparis_no': sonuc['siparis_no'],
                        'tedarikci_id': tedarikci_id,
                        'toplam_tutar': sonuc['toplam_tutar']
                    })
            
            if olusturulan_siparisler:
                logger.info(
                    f"Otomatik önerilerden {len(olusturulan_siparisler)} sipariş oluşturuldu "
                    f"- Otel: {otel_id} - Kullanıcı: {kullanici_id}"
                )
                
                return {
                    'success': True,
                    'olusturulan_siparisler': olusturulan_siparisler,
                    'message': f'{len(olusturulan_siparisler)} adet sipariş başarıyla oluşturuldu'
                }
            else:
                return {
                    'success': False,
                    'message': 'Sipariş oluşturulamadı'
                }
            
        except Exception as e:
            logger.error(f"Sipariş önerisi onaylama hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Sipariş oluşturulurken hata oluştu: {str(e)}'
            }


    @staticmethod
    def stok_giris_olustur(
        siparis_id: int,
        teslim_alinan_urunler: List[Dict],
        kullanici_id: int,
        gerceklesen_teslimat_tarihi: Optional[date] = None
    ) -> Dict:
        """
        Sipariş teslimatından stok girişi oluştur

        Args:
            siparis_id: Sipariş ID
            teslim_alinan_urunler: [
                {'urun_id': int, 'miktar': int}
            ]
            kullanici_id: İşlemi yapan kullanıcı
            gerceklesen_teslimat_tarihi: Teslimat tarihi (None ise bugün)

        Returns:
            dict: {
                'success': bool,
                'stok_giris_kayitlari': list,
                'siparis_durumu': str,
                'message': str
            }
        """
        try:
            siparis = SatinAlmaSiparisi.query.get(siparis_id)
            
            if not siparis:
                return {
                    'success': False,
                    'message': 'Sipariş bulunamadı'
                }
            
            # Sipariş durumu kontrolü
            if siparis.durum not in [
                'onaylandi',
                'kismi_teslim'
            ]:
                return {
                    'success': False,
                    'message': 'Bu durumda olan sipariş için stok girişi yapılamaz'
                }
            
            if not teslim_alinan_urunler:
                return {
                    'success': False,
                    'message': 'Teslim alınan ürün bilgisi girilmelidir'
                }
            
            # Teslimat tarihi
            if not gerceklesen_teslimat_tarihi:
                gerceklesen_teslimat_tarihi = date.today()
            
            stok_giris_kayitlari = []
            
            # Her ürün için stok girişi yap
            for urun_data in teslim_alinan_urunler:
                urun_id = urun_data.get('urun_id')
                teslim_miktar = urun_data.get('miktar', 0)
                
                if teslim_miktar <= 0:
                    continue
                
                # Sipariş detayını bul
                detay = SatinAlmaSiparisDetay.query.filter_by(
                    siparis_id=siparis_id,
                    urun_id=urun_id
                ).first()
                
                if not detay:
                    logger.warning(
                        f"Sipariş {siparis_id} için ürün {urun_id} detayı bulunamadı"
                    )
                    continue
                
                # Teslim alınan miktar kontrolü
                kalan_miktar = detay.miktar - detay.teslim_alinan_miktar
                
                if teslim_miktar > kalan_miktar:
                    return {
                        'success': False,
                        'message': f'Ürün {detay.urun.urun_adi} için teslim miktarı sipariş miktarını aşıyor'
                    }
                
                # Stok kaydını bul veya oluştur
                stok = UrunStok.query.filter_by(
                    urun_id=urun_id,
                    otel_id=siparis.otel_id
                ).first()
                
                if not stok:
                    # Yeni stok kaydı oluştur
                    stok = UrunStok(
                        urun_id=urun_id,
                        otel_id=siparis.otel_id,
                        mevcut_stok=0,
                        minimum_stok=10,  # Varsayılan
                        kritik_stok_seviyesi=5,  # Varsayılan
                        birim_maliyet=detay.birim_fiyat
                    )
                    db.session.add(stok)
                    db.session.flush()
                
                # Eski stok değerleri
                eski_stok = stok.mevcut_stok
                eski_maliyet = stok.birim_maliyet or Decimal('0')
                
                # Yeni birim maliyet hesapla (Ağırlıklı ortalama)
                # Formül: (Eski Stok * Eski Maliyet + Yeni Miktar * Yeni Maliyet) / (Eski Stok + Yeni Miktar)
                if eski_stok > 0:
                    toplam_maliyet = (eski_stok * eski_maliyet) + (teslim_miktar * detay.birim_fiyat)
                    yeni_toplam_stok = eski_stok + teslim_miktar
                    yeni_birim_maliyet = toplam_maliyet / yeni_toplam_stok
                else:
                    yeni_birim_maliyet = detay.birim_fiyat
                
                # Stok güncelle
                stok.mevcut_stok += teslim_miktar
                stok.birim_maliyet = yeni_birim_maliyet
                
                # Stok hareket kaydı oluştur
                stok_hareket = StokHareket(
                    urun_id=urun_id,
                    hareket_tipi='giris',
                    miktar=teslim_miktar,
                    aciklama=f'Satın alma siparişi: {siparis.siparis_no}',
                    islem_yapan_id=kullanici_id,
                    islem_tarihi=datetime.now(timezone.utc)
                )
                
                db.session.add(stok_hareket)
                
                # Sipariş detayını güncelle
                detay.teslim_alinan_miktar += teslim_miktar
                
                stok_giris_kayitlari.append({
                    'urun_id': urun_id,
                    'urun_adi': detay.urun.urun_adi,
                    'teslim_miktar': teslim_miktar,
                    'eski_stok': eski_stok,
                    'yeni_stok': stok.mevcut_stok,
                    'eski_maliyet': float(eski_maliyet),
                    'yeni_maliyet': float(yeni_birim_maliyet)
                })
            
            # Sipariş durumunu güncelle
            # Tüm ürünler teslim alındı mı kontrol et
            tum_teslim_alindi = all(
                d.teslim_alinan_miktar >= d.miktar
                for d in siparis.detaylar
            )
            
            if tum_teslim_alindi:
                siparis.durum = SiparisDurum.TAMAMLANDI
                yeni_durum = 'tamamlandi'
            else:
                # Kısmi teslimat
                siparis.durum = SiparisDurum.KISMI_TESLIM
                yeni_durum = 'kismi_teslim'
            
            siparis.gerceklesen_teslimat_tarihi = gerceklesen_teslimat_tarihi
            
            # Tedarikçi performansını güncelle
            SatinAlmaServisi._tedarikci_performans_guncelle(siparis)
            
            db.session.commit()
            
            logger.info(
                f"Stok girişi tamamlandı: Sipariş {siparis.siparis_no} "
                f"- {len(stok_giris_kayitlari)} ürün - Durum: {yeni_durum} "
                f"- Kullanıcı: {kullanici_id}"
            )
            
            return {
                'success': True,
                'stok_giris_kayitlari': stok_giris_kayitlari,
                'siparis_durumu': yeni_durum,
                'message': 'Stok girişi başarıyla tamamlandı'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Stok giriş hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Stok girişi yapılırken hata oluştu: {str(e)}'
            }

    @staticmethod
    def _tedarikci_performans_guncelle(siparis: SatinAlmaSiparisi) -> None:
        """
        Sipariş tamamlandığında tedarikçi performansını güncelle

        Args:
            siparis: Tamamlanan sipariş
        """
        try:
            # Tedarikçi yoksa performans güncellemesi yapma
            if not siparis.tedarikci_id:
                return
            
            # Sadece tam teslim edilen siparişler için performans güncelle
            if siparis.durum != SiparisDurum.TAMAMLANDI:
                return
            
            if not siparis.gerceklesen_teslimat_tarihi or not siparis.tahmini_teslimat_tarihi:
                return
            
            # Bu ay için performans kaydını bul veya oluştur
            bugun = date.today()
            donem_baslangic = date(bugun.year, bugun.month, 1)
            
            # Bir sonraki ayın ilk günü
            if bugun.month == 12:
                donem_bitis = date(bugun.year + 1, 1, 1) - timedelta(days=1)
            else:
                donem_bitis = date(bugun.year, bugun.month + 1, 1) - timedelta(days=1)
            
            performans = TedarikciPerformans.query.filter_by(
                tedarikci_id=siparis.tedarikci_id,
                donem_baslangic=donem_baslangic,
                donem_bitis=donem_bitis
            ).first()
            
            if not performans:
                # Yeni performans kaydı oluştur
                performans = TedarikciPerformans(
                    tedarikci_id=siparis.tedarikci_id,
                    donem_baslangic=donem_baslangic,
                    donem_bitis=donem_bitis,
                    toplam_siparis_sayisi=0,
                    zamaninda_teslimat_sayisi=0,
                    ortalama_teslimat_suresi=0,
                    toplam_siparis_tutari=Decimal('0'),
                    performans_skoru=Decimal('0')
                )
                db.session.add(performans)
            
            # Metrikleri güncelle
            performans.toplam_siparis_sayisi += 1
            performans.toplam_siparis_tutari += siparis.toplam_tutar
            
            # Zamanında teslimat kontrolü
            if siparis.gerceklesen_teslimat_tarihi <= siparis.tahmini_teslimat_tarihi:
                performans.zamaninda_teslimat_sayisi += 1
            
            # Ortalama teslimat süresini güncelle
            teslimat_suresi = (siparis.gerceklesen_teslimat_tarihi - siparis.siparis_tarihi.date()).days
            
            if performans.ortalama_teslimat_suresi == 0:
                performans.ortalama_teslimat_suresi = teslimat_suresi
            else:
                # Ağırlıklı ortalama
                toplam_sure = performans.ortalama_teslimat_suresi * (performans.toplam_siparis_sayisi - 1)
                performans.ortalama_teslimat_suresi = (toplam_sure + teslimat_suresi) // performans.toplam_siparis_sayisi
            
            # Performans skorunu hesapla
            zamaninda_oran = (performans.zamaninda_teslimat_sayisi / performans.toplam_siparis_sayisi * 100) \
                if performans.toplam_siparis_sayisi > 0 else 0
            
            performans_skoru = TedarikciServisi._performans_skoru_hesapla(
                zamaninda_oran,
                performans.ortalama_teslimat_suresi
            )
            
            performans.performans_skoru = Decimal(str(performans_skoru))
            
            tedarikci_adi = siparis.tedarikci.tedarikci_adi if siparis.tedarikci else 'Belirtilmemiş'
            logger.info(
                f"Tedarikçi performansı güncellendi: {tedarikci_adi} "
                f"- Skor: {performans_skoru:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Tedarikçi performans güncelleme hatası: {str(e)}")
            # Hata olsa bile ana işlemi etkilemesin
            pass


    @staticmethod
    def geciken_siparisler_kontrol(
        otel_id: Optional[int] = None,
        gecikme_gun_esigi: int = 2
    ) -> List[Dict]:
        """
        Tahmini teslimat tarihi geçmiş siparişleri bul

        Args:
            otel_id: Otel filtresi (None ise tüm oteller)
            gecikme_gun_esigi: Gecikme eşiği (gün) - varsayılan 2 gün

        Returns:
            list: [
                {
                    'siparis_id': int,
                    'siparis_no': str,
                    'tedarikci_id': int,
                    'tedarikci_adi': str,
                    'otel_id': int,
                    'otel_adi': str,
                    'tahmini_teslimat_tarihi': str,
                    'gecikme_gun': int,
                    'toplam_tutar': float,
                    'durum': str
                }
            ]
        """
        try:
            bugun = date.today()
            gecikme_tarihi = bugun - timedelta(days=gecikme_gun_esigi)
            
            query = SatinAlmaSiparisi.query.filter(
                SatinAlmaSiparisi.tahmini_teslimat_tarihi <= gecikme_tarihi,
                SatinAlmaSiparisi.durum.in_([
                    'onaylandi',
                    'kismi_teslim'
                ])
            )
            
            if otel_id:
                query = query.filter_by(otel_id=otel_id)
            
            geciken_siparisler = query.order_by(
                SatinAlmaSiparisi.tahmini_teslimat_tarihi
            ).all()
            
            sonuc = []
            for siparis in geciken_siparisler:
                gecikme_gun = (bugun - siparis.tahmini_teslimat_tarihi).days
                
                sonuc.append({
                    'siparis_id': siparis.id,
                    'siparis_no': siparis.siparis_no,
                    'tedarikci_id': siparis.tedarikci_id,
                    'tedarikci_adi': siparis.tedarikci.tedarikci_adi if siparis.tedarikci else 'Belirtilmemiş',
                    'tedarikci_telefon': siparis.tedarikci.iletisim_bilgileri.get('telefon', '') if siparis.tedarikci and siparis.tedarikci.iletisim_bilgileri else '',
                    'otel_id': siparis.otel_id,
                    'otel_adi': siparis.otel.ad,
                    'siparis_tarihi': siparis.siparis_tarihi,
                    'tahmini_teslimat_tarihi': siparis.tahmini_teslimat_tarihi,
                    'gecikme_gun': gecikme_gun,
                    'toplam_tutar': float(siparis.toplam_tutar),
                    'durum': siparis.durum if isinstance(siparis.durum, str) else siparis.durum.value,
                    'olusturan_adi': f"{siparis.olusturan.ad} {siparis.olusturan.soyad}" if siparis.olusturan else ''
                })
            
            if sonuc:
                logger.info(
                    f"Geciken sipariş kontrolü: {len(sonuc)} adet gecikmiş sipariş bulundu"
                )
            
            return sonuc
            
        except Exception as e:
            logger.error(f"Geciken sipariş kontrolü hatası: {str(e)}")
            return []

    @staticmethod
    def gecikme_bildirimi_olustur(
        siparis_id: int,
        bildirim_tipi: str = 'email'
    ) -> Dict:
        """
        Geciken sipariş için bildirim oluştur

        Args:
            siparis_id: Sipariş ID
            bildirim_tipi: 'email' veya 'dashboard'

        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            siparis = SatinAlmaSiparisi.query.get(siparis_id)
            
            if not siparis:
                return {
                    'success': False,
                    'message': 'Sipariş bulunamadı'
                }
            
            if not siparis.tahmini_teslimat_tarihi:
                return {
                    'success': False,
                    'message': 'Tahmini teslimat tarihi belirtilmemiş'
                }
            
            bugun = date.today()
            gecikme_gun = (bugun - siparis.tahmini_teslimat_tarihi).days
            
            if gecikme_gun <= 0:
                return {
                    'success': False,
                    'message': 'Sipariş henüz gecikmemiş'
                }
            
            # Bildirim mesajı oluştur
            mesaj = (
                f"Sipariş Gecikme Uyarısı!\n\n"
                f"Sipariş No: {siparis.siparis_no}\n"
                f"Tedarikçi: {siparis.tedarikci.tedarikci_adi if siparis.tedarikci else 'Belirtilmemiş'}\n"
                f"Tahmini Teslimat: {siparis.tahmini_teslimat_tarihi.strftime('%d.%m.%Y')}\n"
                f"Gecikme: {gecikme_gun} gün\n"
                f"Toplam Tutar: {siparis.toplam_tutar} TL\n\n"
                f"Lütfen tedarikçi ile iletişime geçiniz."
            )
            
            logger.info(
                f"Gecikme bildirimi oluşturuldu: {siparis.siparis_no} "
                f"- Gecikme: {gecikme_gun} gün"
            )
            
            return {
                'success': True,
                'message': mesaj,
                'gecikme_gun': gecikme_gun
            }
            
        except Exception as e:
            logger.error(f"Gecikme bildirimi oluşturma hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Bildirim oluşturulurken hata oluştu: {str(e)}'
            }

    @staticmethod
    def dashboard_bildirimleri_getir(
        kullanici_id: int,
        otel_id: Optional[int] = None
    ) -> Dict:
        """
        Kullanıcı için dashboard bildirimlerini getir

        Args:
            kullanici_id: Kullanıcı ID
            otel_id: Otel filtresi (None ise kullanıcının tüm otelleri)

        Returns:
            dict: {
                'kritik_stok_sayisi': int,
                'geciken_siparis_sayisi': int,
                'bekleyen_siparis_sayisi': int,
                'siparis_onerileri_sayisi': int,
                'bildirimler': list
            }
        """
        try:
            bildirimler = []
            
            # Kritik stok uyarıları
            if otel_id:
                kritik_stok_query = UrunStok.query.filter(
                    UrunStok.otel_id == otel_id,
                    UrunStok.mevcut_stok <= UrunStok.kritik_stok_seviyesi
                )
            else:
                kritik_stok_query = UrunStok.query.filter(
                    UrunStok.mevcut_stok <= UrunStok.kritik_stok_seviyesi
                )
            
            kritik_stok_sayisi = kritik_stok_query.count()
            
            if kritik_stok_sayisi > 0:
                bildirimler.append({
                    'tip': 'warning',
                    'baslik': 'Kritik Stok Uyarısı',
                    'mesaj': f'{kritik_stok_sayisi} ürün kritik stok seviyesinde',
                    'link': '/otomatik-siparis-onerileri',
                    'oncelik': 'yuksek'
                })
            
            # Geciken siparişler
            geciken_siparisler = SatinAlmaServisi.geciken_siparisler_kontrol(
                otel_id=otel_id,
                gecikme_gun_esigi=0
            )
            
            geciken_siparis_sayisi = len(geciken_siparisler)
            
            if geciken_siparis_sayisi > 0:
                bildirimler.append({
                    'tip': 'danger',
                    'baslik': 'Geciken Siparişler',
                    'mesaj': f'{geciken_siparis_sayisi} sipariş teslimat tarihini geçti',
                    'link': '/siparis-listesi?durum=geciken',
                    'oncelik': 'kritik'
                })
            
            # Onay bekleyen siparişler
            bekleyen_query = SatinAlmaSiparisi.query.filter_by(
                durum='beklemede'
            )
            
            if otel_id:
                bekleyen_query = bekleyen_query.filter_by(otel_id=otel_id)
            
            bekleyen_siparis_sayisi = bekleyen_query.count()
            
            if bekleyen_siparis_sayisi > 0:
                bildirimler.append({
                    'tip': 'info',
                    'baslik': 'Onay Bekleyen Siparişler',
                    'mesaj': f'{bekleyen_siparis_sayisi} sipariş onay bekliyor',
                    'link': '/siparis-listesi?durum=beklemede',
                    'oncelik': 'orta'
                })
            
            # Sipariş önerileri
            if otel_id:
                oneriler = SatinAlmaServisi.otomatik_siparis_onerisi_olustur(otel_id)
                siparis_onerileri_sayisi = len(oneriler)
                
                if siparis_onerileri_sayisi > 0:
                    bildirimler.append({
                        'tip': 'success',
                        'baslik': 'Sipariş Önerileri',
                        'mesaj': f'{siparis_onerileri_sayisi} ürün için sipariş önerisi mevcut',
                        'link': '/otomatik-siparis-onerileri',
                        'oncelik': 'dusuk'
                    })
            else:
                siparis_onerileri_sayisi = 0
            
            # Öncelik sırasına göre sırala
            oncelik_sirasi = {'kritik': 0, 'yuksek': 1, 'orta': 2, 'dusuk': 3}
            bildirimler.sort(key=lambda x: oncelik_sirasi.get(x['oncelik'], 99))
            
            return {
                'kritik_stok_sayisi': kritik_stok_sayisi,
                'geciken_siparis_sayisi': geciken_siparis_sayisi,
                'bekleyen_siparis_sayisi': bekleyen_siparis_sayisi,
                'siparis_onerileri_sayisi': siparis_onerileri_sayisi,
                'bildirimler': bildirimler
            }
            
        except Exception as e:
            logger.error(f"Dashboard bildirimleri getirme hatası: {str(e)}")
            return {
                'kritik_stok_sayisi': 0,
                'geciken_siparis_sayisi': 0,
                'bekleyen_siparis_sayisi': 0,
                'siparis_onerileri_sayisi': 0,
                'bildirimler': []
            }

    @staticmethod
    def satin_alma_ozet_raporu(
        otel_id: Optional[int] = None,
        donem_baslangic: Optional[date] = None,
        donem_bitis: Optional[date] = None,
        tedarikci_id: Optional[int] = None
    ) -> Dict:
        """
        Dönemsel satın alma özet raporu
        
        Tedarikçi ve ürün bazında analizler:
        - Tedarikçi bazında sipariş ve tutar analizi
        - Ürün bazında satın alma analizi
        - Aylık satın alma trendi
        - Maliyet analizi
        - Fiyat trend analizi
        
        Args:
            otel_id: Otel filtresi (None ise tüm oteller)
            donem_baslangic: Dönem başlangıç (None ise son 3 ay)
            donem_bitis: Dönem bitiş (None ise bugün)
            tedarikci_id: Tedarikçi filtresi (None ise tüm tedarikçiler)
        
        Returns:
            dict: {
                'tedarikci_analizi': list,  # Tedarikçi bazında analiz
                'urun_analizi': list,  # Ürün bazında analiz
                'aylik_trend': list,  # Aylık satın alma trendi
                'maliyet_analizi': dict,  # Toplam maliyet analizi
                'fiyat_trend_analizi': list,  # Fiyat değişim analizi
                'genel_ozet': dict  # Genel özet bilgiler
            }
        """
        try:
            # Varsayılan dönem: Son 3 ay
            if not donem_bitis:
                donem_bitis = date.today()
            if not donem_baslangic:
                donem_baslangic = donem_bitis - timedelta(days=90)
            
            # Siparişleri getir
            siparis_query = SatinAlmaSiparisi.query.filter(
                SatinAlmaSiparisi.siparis_tarihi >= datetime.combine(donem_baslangic, datetime.min.time()),
                SatinAlmaSiparisi.siparis_tarihi <= datetime.combine(donem_bitis, datetime.max.time())
            )
            
            if otel_id:
                siparis_query = siparis_query.filter_by(otel_id=otel_id)
            
            if tedarikci_id:
                siparis_query = siparis_query.filter_by(tedarikci_id=tedarikci_id)
            
            siparisler = siparis_query.all()
            
            if not siparisler:
                return {
                    'success': True,
                    'message': 'Belirtilen dönemde sipariş bulunamadı',
                    'tedarikci_analizi': [],
                    'urun_analizi': [],
                    'aylik_trend': [],
                    'maliyet_analizi': {},
                    'fiyat_trend_analizi': [],
                    'genel_ozet': {}
                }
            
            # Tedarikçi bazında analiz
            tedarikci_analizi = SatinAlmaServisi._tedarikci_bazinda_analiz(siparisler)
            
            # Ürün bazında analiz
            urun_analizi = SatinAlmaServisi._urun_bazinda_analiz(siparisler)
            
            # Aylık trend
            aylik_trend = SatinAlmaServisi._aylik_satin_alma_trend(
                otel_id,
                donem_baslangic,
                donem_bitis,
                tedarikci_id
            )
            
            # Maliyet analizi
            maliyet_analizi = SatinAlmaServisi._maliyet_analizi(siparisler)
            
            # Fiyat trend analizi
            fiyat_trend_analizi = SatinAlmaServisi._fiyat_trend_analizi(
                siparisler,
                donem_baslangic,
                donem_bitis
            )
            
            # Genel özet
            genel_ozet = {
                'toplam_siparis': len(siparisler),
                'toplam_tutar': float(sum(s.toplam_tutar for s in siparisler)),
                'ortalama_siparis_tutari': float(
                    sum(s.toplam_tutar for s in siparisler) / len(siparisler)
                ) if siparisler else 0,
                'benzersiz_tedarikci': len(set(s.tedarikci_id for s in siparisler)),
                'benzersiz_urun': len(set(
                    d.urun_id for s in siparisler for d in s.detaylar
                )),
                'tamamlanan_siparis': len([
                    s for s in siparisler
                    if s.durum in [SiparisDurum.TESLIM_ALINDI, SiparisDurum.TAMAMLANDI]
                ]),
                'iptal_edilen_siparis': len([
                    s for s in siparisler if s.durum == SiparisDurum.IPTAL
                ]),
                'donem_baslangic': donem_baslangic.isoformat(),
                'donem_bitis': donem_bitis.isoformat()
            }
            
            logger.info(
                f"Satın alma özet raporu oluşturuldu: "
                f"{len(siparisler)} sipariş - "
                f"Dönem: {donem_baslangic} - {donem_bitis}"
            )
            
            return {
                'success': True,
                'tedarikci_analizi': tedarikci_analizi,
                'urun_analizi': urun_analizi,
                'aylik_trend': aylik_trend,
                'maliyet_analizi': maliyet_analizi,
                'fiyat_trend_analizi': fiyat_trend_analizi,
                'genel_ozet': genel_ozet
            }
            
        except Exception as e:
            logger.error(f"Satın alma özet raporu hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Özet raporu oluşturulurken hata oluştu: {str(e)}'
            }

    @staticmethod
    def _tedarikci_bazinda_analiz(siparisler: List[SatinAlmaSiparisi]) -> List[Dict]:
        """
        Tedarikçi bazında sipariş ve tutar analizi
        
        Args:
            siparisler: Sipariş listesi
        
        Returns:
            list: [
                {
                    'tedarikci_id': int,
                    'tedarikci_adi': str,
                    'siparis_sayisi': int,
                    'toplam_tutar': float,
                    'ortalama_siparis_tutari': float,
                    'tamamlanan_siparis': int,
                    'iptal_edilen_siparis': int,
                    'pay_yuzdesi': float  # Toplam içindeki pay
                }
            ]
        """
        try:
            tedarikci_verileri = {}
            toplam_tutar_genel = sum(s.toplam_tutar for s in siparisler)
            
            for siparis in siparisler:
                tedarikci_id = siparis.tedarikci_id
                
                if tedarikci_id not in tedarikci_verileri:
                    tedarikci_verileri[tedarikci_id] = {
                        'tedarikci_id': tedarikci_id,
                        'tedarikci_adi': siparis.tedarikci.tedarikci_adi if siparis.tedarikci else 'Belirtilmemiş',
                        'siparis_sayisi': 0,
                        'toplam_tutar': Decimal('0'),
                        'tamamlanan_siparis': 0,
                        'iptal_edilen_siparis': 0
                    }
                
                tedarikci_verileri[tedarikci_id]['siparis_sayisi'] += 1
                tedarikci_verileri[tedarikci_id]['toplam_tutar'] += siparis.toplam_tutar
                
                if siparis.durum in [SiparisDurum.TESLIM_ALINDI, SiparisDurum.TAMAMLANDI]:
                    tedarikci_verileri[tedarikci_id]['tamamlanan_siparis'] += 1
                elif siparis.durum == SiparisDurum.IPTAL:
                    tedarikci_verileri[tedarikci_id]['iptal_edilen_siparis'] += 1
            
            # Sonuçları formatla
            sonuc = []
            for veri in tedarikci_verileri.values():
                ortalama_tutar = veri['toplam_tutar'] / veri['siparis_sayisi'] if veri['siparis_sayisi'] > 0 else 0
                pay_yuzdesi = (veri['toplam_tutar'] / toplam_tutar_genel * 100) if toplam_tutar_genel > 0 else 0
                
                sonuc.append({
                    'tedarikci_id': veri['tedarikci_id'],
                    'tedarikci_adi': veri['tedarikci_adi'],
                    'siparis_sayisi': veri['siparis_sayisi'],
                    'toplam_tutar': float(veri['toplam_tutar']),
                    'ortalama_siparis_tutari': float(ortalama_tutar),
                    'tamamlanan_siparis': veri['tamamlanan_siparis'],
                    'iptal_edilen_siparis': veri['iptal_edilen_siparis'],
                    'pay_yuzdesi': round(pay_yuzdesi, 2)
                })
            
            # Toplam tutara göre sırala (büyükten küçüğe)
            sonuc.sort(key=lambda x: x['toplam_tutar'], reverse=True)
            
            return sonuc
            
        except Exception as e:
            logger.error(f"Tedarikçi bazında analiz hatası: {str(e)}")
            return []

    @staticmethod
    def _urun_bazinda_analiz(siparisler: List[SatinAlmaSiparisi]) -> List[Dict]:
        """
        Ürün bazında satın alma analizi
        
        Args:
            siparisler: Sipariş listesi
        
        Returns:
            list: [
                {
                    'urun_id': int,
                    'urun_adi': str,
                    'toplam_miktar': int,
                    'toplam_tutar': float,
                    'ortalama_birim_fiyat': float,
                    'siparis_sayisi': int,
                    'tedarikci_sayisi': int,  # Kaç farklı tedarikçiden alındı
                    'en_dusuk_fiyat': float,
                    'en_yuksek_fiyat': float
                }
            ]
        """
        try:
            urun_verileri = {}
            
            for siparis in siparisler:
                for detay in siparis.detaylar:
                    urun_id = detay.urun_id
                    
                    if urun_id not in urun_verileri:
                        urun_verileri[urun_id] = {
                            'urun_id': urun_id,
                            'urun_adi': detay.urun.urun_adi,
                            'toplam_miktar': 0,
                            'toplam_tutar': Decimal('0'),
                            'siparis_sayisi': 0,
                            'tedarikciler': set(),
                            'fiyatlar': []
                        }
                    
                    urun_verileri[urun_id]['toplam_miktar'] += detay.miktar
                    urun_verileri[urun_id]['toplam_tutar'] += detay.toplam_fiyat
                    urun_verileri[urun_id]['siparis_sayisi'] += 1
                    urun_verileri[urun_id]['tedarikciler'].add(siparis.tedarikci_id)
                    urun_verileri[urun_id]['fiyatlar'].append(float(detay.birim_fiyat))
            
            # Sonuçları formatla
            sonuc = []
            for veri in urun_verileri.values():
                ortalama_fiyat = veri['toplam_tutar'] / veri['toplam_miktar'] if veri['toplam_miktar'] > 0 else 0
                
                sonuc.append({
                    'urun_id': veri['urun_id'],
                    'urun_adi': veri['urun_adi'],
                    'toplam_miktar': veri['toplam_miktar'],
                    'toplam_tutar': float(veri['toplam_tutar']),
                    'ortalama_birim_fiyat': float(ortalama_fiyat),
                    'siparis_sayisi': veri['siparis_sayisi'],
                    'tedarikci_sayisi': len(veri['tedarikciler']),
                    'en_dusuk_fiyat': min(veri['fiyatlar']) if veri['fiyatlar'] else 0,
                    'en_yuksek_fiyat': max(veri['fiyatlar']) if veri['fiyatlar'] else 0
                })
            
            # Toplam tutara göre sırala (büyükten küçüğe)
            sonuc.sort(key=lambda x: x['toplam_tutar'], reverse=True)
            
            return sonuc
            
        except Exception as e:
            logger.error(f"Ürün bazında analiz hatası: {str(e)}")
            return []

    @staticmethod
    def _aylik_satin_alma_trend(
        otel_id: Optional[int],
        donem_baslangic: date,
        donem_bitis: date,
        tedarikci_id: Optional[int]
    ) -> List[Dict]:
        """
        Aylık satın alma trendi (grafik için)
        
        Args:
            otel_id: Otel filtresi
            donem_baslangic: Dönem başlangıç
            donem_bitis: Dönem bitiş
            tedarikci_id: Tedarikçi filtresi
        
        Returns:
            list: [
                {
                    'ay': str,  # 'YYYY-MM'
                    'ay_adi': str,  # 'Ocak 2024'
                    'siparis_sayisi': int,
                    'toplam_tutar': float,
                    'ortalama_siparis_tutari': float
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
                
                if otel_id:
                    siparis_query = siparis_query.filter_by(otel_id=otel_id)
                
                if tedarikci_id:
                    siparis_query = siparis_query.filter_by(tedarikci_id=tedarikci_id)
                
                siparisler = siparis_query.all()
                
                siparis_sayisi = len(siparisler)
                toplam_tutar = sum(s.toplam_tutar for s in siparisler)
                ortalama_tutar = toplam_tutar / siparis_sayisi if siparis_sayisi > 0 else 0
                
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
                    'toplam_tutar': float(toplam_tutar),
                    'ortalama_siparis_tutari': float(ortalama_tutar)
                })
                
                # Bir sonraki ay
                if current_date.month == 12:
                    current_date = date(current_date.year + 1, 1, 1)
                else:
                    current_date = date(current_date.year, current_date.month + 1, 1)
            
            return aylik_veriler
            
        except Exception as e:
            logger.error(f"Aylık satın alma trend hatası: {str(e)}")
            return []

    @staticmethod
    def _maliyet_analizi(siparisler: List[SatinAlmaSiparisi]) -> Dict:
        """
        Maliyet analizi
        
        Args:
            siparisler: Sipariş listesi
        
        Returns:
            dict: {
                'toplam_maliyet': float,
                'tamamlanan_maliyet': float,
                'bekleyen_maliyet': float,
                'iptal_edilen_maliyet': float,
                'ortalama_siparis_maliyeti': float,
                'en_yuksek_siparis': dict,
                'en_dusuk_siparis': dict
            }
        """
        try:
            toplam_maliyet = sum(s.toplam_tutar for s in siparisler)
            
            tamamlanan_maliyet = sum(
                s.toplam_tutar for s in siparisler
                if s.durum in [SiparisDurum.TESLIM_ALINDI, SiparisDurum.TAMAMLANDI]
            )
            
            bekleyen_maliyet = sum(
                s.toplam_tutar for s in siparisler
                if s.durum in ['beklemede', 'onaylandi', 'kismi_teslim']
            )
            
            iptal_edilen_maliyet = sum(
                s.toplam_tutar for s in siparisler
                if s.durum == SiparisDurum.IPTAL
            )
            
            ortalama_maliyet = toplam_maliyet / len(siparisler) if siparisler else 0
            
            # En yüksek ve en düşük sipariş
            en_yuksek = max(siparisler, key=lambda s: s.toplam_tutar) if siparisler else None
            en_dusuk = min(siparisler, key=lambda s: s.toplam_tutar) if siparisler else None
            
            return {
                'toplam_maliyet': float(toplam_maliyet),
                'tamamlanan_maliyet': float(tamamlanan_maliyet),
                'bekleyen_maliyet': float(bekleyen_maliyet),
                'iptal_edilen_maliyet': float(iptal_edilen_maliyet),
                'ortalama_siparis_maliyeti': float(ortalama_maliyet),
                'en_yuksek_siparis': {
                    'siparis_no': en_yuksek.siparis_no,
                    'tedarikci_adi': en_yuksek.tedarikci.tedarikci_adi if en_yuksek.tedarikci else 'Belirtilmemiş',
                    'tutar': float(en_yuksek.toplam_tutar)
                } if en_yuksek else None,
                'en_dusuk_siparis': {
                    'siparis_no': en_dusuk.siparis_no,
                    'tedarikci_adi': en_dusuk.tedarikci.tedarikci_adi if en_dusuk.tedarikci else 'Belirtilmemiş',
                    'tutar': float(en_dusuk.toplam_tutar)
                } if en_dusuk else None
            }
            
        except Exception as e:
            logger.error(f"Maliyet analizi hatası: {str(e)}")
            return {}

    @staticmethod
    def _fiyat_trend_analizi(
        siparisler: List[SatinAlmaSiparisi],
        donem_baslangic: date,
        donem_bitis: date
    ) -> List[Dict]:
        """
        Fiyat trend analizi - En çok sipariş edilen ürünlerin fiyat değişimi
        
        Args:
            siparisler: Sipariş listesi
            donem_baslangic: Dönem başlangıç
            donem_bitis: Dönem bitiş
        
        Returns:
            list: [
                {
                    'urun_id': int,
                    'urun_adi': str,
                    'baslangic_fiyat': float,
                    'bitis_fiyat': float,
                    'degisim_yuzdesi': float,
                    'degisim_tipi': str  # 'artti', 'azaldi', 'degismedi'
                }
            ]
        """
        try:
            # Ürün bazında fiyat verilerini topla
            urun_fiyatlari = {}
            
            for siparis in siparisler:
                for detay in siparis.detaylar:
                    urun_id = detay.urun_id
                    
                    if urun_id not in urun_fiyatlari:
                        urun_fiyatlari[urun_id] = {
                            'urun_adi': detay.urun.urun_adi,
                            'fiyat_kayitlari': []
                        }
                    
                    urun_fiyatlari[urun_id]['fiyat_kayitlari'].append({
                        'tarih': siparis.siparis_tarihi.date(),
                        'fiyat': float(detay.birim_fiyat)
                    })
            
            # En çok sipariş edilen 10 ürünü al
            en_cok_siparis_edilen = sorted(
                urun_fiyatlari.items(),
                key=lambda x: len(x[1]['fiyat_kayitlari']),
                reverse=True
            )[:10]
            
            # Fiyat değişimlerini hesapla
            sonuc = []
            
            for urun_id, veri in en_cok_siparis_edilen:
                # Tarihe göre sırala
                kayitlar = sorted(veri['fiyat_kayitlari'], key=lambda x: x['tarih'])
                
                if len(kayitlar) < 2:
                    continue
                
                baslangic_fiyat = kayitlar[0]['fiyat']
                bitis_fiyat = kayitlar[-1]['fiyat']
                
                # Değişim yüzdesi
                if baslangic_fiyat > 0:
                    degisim_yuzdesi = ((bitis_fiyat - baslangic_fiyat) / baslangic_fiyat) * 100
                else:
                    degisim_yuzdesi = 0
                
                # Değişim tipi
                if degisim_yuzdesi > 1:
                    degisim_tipi = 'artti'
                elif degisim_yuzdesi < -1:
                    degisim_tipi = 'azaldi'
                else:
                    degisim_tipi = 'degismedi'
                
                sonuc.append({
                    'urun_id': urun_id,
                    'urun_adi': veri['urun_adi'],
                    'baslangic_fiyat': baslangic_fiyat,
                    'bitis_fiyat': bitis_fiyat,
                    'degisim_yuzdesi': round(degisim_yuzdesi, 2),
                    'degisim_tipi': degisim_tipi,
                    'siparis_sayisi': len(kayitlar)
                })
            
            # Değişim yüzdesine göre sırala (en çok değişenler önce)
            sonuc.sort(key=lambda x: abs(x['degisim_yuzdesi']), reverse=True)
            
            return sonuc
            
        except Exception as e:
            logger.error(f"Fiyat trend analizi hatası: {str(e)}")
            return []
