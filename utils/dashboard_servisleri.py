"""
Dashboard Bildirim Servisi

Bu modül, sistem yöneticisi ve depo sorumlusu dashboard'larında
gösterilecek bildirimleri yönetir.

Bildirim Tipleri:
- Kritik stok uyarıları
- Geciken sipariş bildirimleri
- Onay bekleyen sipariş sayacı
- Tedarikçi performans uyarıları
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from sqlalchemy import and_, or_
from models import (
    db, UrunStok, SatinAlmaSiparisi,
    TedarikciPerformans, Tedarikci, Urun, Otel
)
from flask import url_for
import logging

logger = logging.getLogger(__name__)


class DashboardBildirimServisi:
    """Dashboard bildirim yönetim servisi"""

    @staticmethod
    def get_dashboard_bildirimleri(kullanici_id: int, rol: str, otel_id: Optional[int] = None) -> List[Dict]:
        """
        Kullanıcı için dashboard bildirimlerini getir

        Args:
            kullanici_id: Kullanıcı ID
            rol: Kullanıcı rolü (sistem_yoneticisi, depo_sorumlusu)
            otel_id: Otel ID (depo sorumlusu için)

        Returns:
            list: Bildirim listesi
            [
                {
                    'tip': 'warning|danger|info|success',
                    'mesaj': str,
                    'link': str,
                    'sayi': int,
                    'oncelik': int  # 1-5 arası, 1 en yüksek
                }
            ]
        """
        try:
            bildirimler = []

            if rol == 'sistem_yoneticisi':
                # Sistem yöneticisi için tüm oteller
                bildirimler.extend(DashboardBildirimServisi._get_kritik_stok_bildirimleri())
                bildirimler.extend(DashboardBildirimServisi._get_geciken_siparis_bildirimleri())
                bildirimler.extend(DashboardBildirimServisi._get_onay_bekleyen_siparis_bildirimleri())
                bildirimler.extend(DashboardBildirimServisi._get_tedarikci_performans_uyarilari())

            elif rol == 'depo_sorumlusu' and otel_id:
                # Depo sorumlusu için sadece kendi oteli
                bildirimler.extend(DashboardBildirimServisi._get_kritik_stok_bildirimleri(otel_id))
                bildirimler.extend(DashboardBildirimServisi._get_geciken_siparis_bildirimleri(otel_id))
                bildirimler.extend(DashboardBildirimServisi._get_onay_bekleyen_siparis_bildirimleri(otel_id))
                bildirimler.extend(DashboardBildirimServisi._get_siparis_onerileri_bildirimi(otel_id))

            # Önceliğe göre sırala (1 en yüksek öncelik)
            bildirimler.sort(key=lambda x: x.get('oncelik', 5))

            return bildirimler

        except Exception as e:
            logger.error(f"Dashboard bildirimleri alınırken hata: {str(e)}")
            db.session.rollback()
            return []

    @staticmethod
    def _get_kritik_stok_bildirimleri(otel_id: Optional[int] = None) -> List[Dict]:
        """Kritik stok seviyesindeki ürünler için bildirim"""
        try:
            query = db.session.query(UrunStok).filter(
                UrunStok.mevcut_stok <= UrunStok.kritik_stok_seviyesi
            )

            if otel_id:
                query = query.filter(UrunStok.otel_id == otel_id)

            kritik_stoklar = query.all()
            sayi = len(kritik_stoklar)

            if sayi > 0:
                return [{
                    'tip': 'warning',
                    'mesaj': f'{sayi} ürün kritik stok seviyesinde',
                    'link': url_for('otomatik_siparis_onerileri'),
                    'sayi': sayi,
                    'oncelik': 2,
                    'ikon': 'exclamation-triangle'
                }]

            return []

        except Exception as e:
            logger.error(f"Kritik stok bildirimleri alınırken hata: {str(e)}")
            db.session.rollback()
            return []

    @staticmethod
    def _get_geciken_siparis_bildirimleri(otel_id: Optional[int] = None) -> List[Dict]:
        """Tahmini teslimat tarihi geçmiş siparişler için bildirim"""
        try:
            bugun = date.today()

            query = db.session.query(SatinAlmaSiparisi).filter(
                and_(
                    SatinAlmaSiparisi.tahmini_teslimat_tarihi < bugun,
                    SatinAlmaSiparisi.durum.in_([
                        'beklemede',
                        'onaylandi'
                    ])
                )
            )

            if otel_id:
                query = query.filter(SatinAlmaSiparisi.otel_id == otel_id)

            geciken_siparisler = query.all()
            sayi = len(geciken_siparisler)

            if sayi > 0:
                return [{
                    'tip': 'danger',
                    'mesaj': f'{sayi} sipariş gecikmede',
                    'link': url_for('yonetici_siparis_listesi'),
                    'sayi': sayi,
                    'oncelik': 1,  # En yüksek öncelik
                    'ikon': 'clock'
                }]

            return []

        except Exception as e:
            logger.error(f"Geciken sipariş bildirimleri alınırken hata: {str(e)}")
            db.session.rollback()
            return []

    @staticmethod
    def _get_onay_bekleyen_siparis_bildirimleri(otel_id: Optional[int] = None) -> List[Dict]:
        """Onay bekleyen siparişler için bildirim"""
        try:
            query = db.session.query(SatinAlmaSiparisi).filter(
                SatinAlmaSiparisi.durum == 'beklemede'
            )

            if otel_id:
                query = query.filter(SatinAlmaSiparisi.otel_id == otel_id)

            bekleyen_siparisler = query.all()
            sayi = len(bekleyen_siparisler)
        
            if sayi > 0:
                return [{
                    'tip': 'info',
                    'mesaj': f'{sayi} sipariş onay bekliyor',
                    'link': url_for('yonetici_siparis_listesi', durum='beklemede'),
                    'sayi': sayi,
                    'oncelik': 3,
                    'ikon': 'hourglass-half'
                }]

            return []

        except Exception as e:
            logger.error(f"Onay bekleyen sipariş bildirimleri alınırken hata: {str(e)}")
            db.session.rollback()
            return []

    @staticmethod
    def _get_tedarikci_performans_uyarilari(otel_id: Optional[int] = None) -> List[Dict]:
        """Düşük performanslı tedarikçiler için uyarı"""
        try:
            # Son 6 ay için performans kontrolü
            alti_ay_once = date.today() - timedelta(days=180)

            query = db.session.query(TedarikciPerformans).filter(
                and_(
                    TedarikciPerformans.donem_bitis >= alti_ay_once,
                    TedarikciPerformans.performans_skoru < 70  # %70'in altı düşük performans
                )
            )

            dusuk_performans = query.all()
            sayi = len(dusuk_performans)

            if sayi > 0:
                return [{
                    'tip': 'warning',
                    'mesaj': f'{sayi} tedarikçi düşük performans gösteriyor',
                    'link': url_for('tedarikci_performans_raporu'),
                    'sayi': sayi,
                    'oncelik': 4,
                    'ikon': 'chart-line'
                }]

            return []

        except Exception as e:
            logger.error(f"Tedarikçi performans uyarıları alınırken hata: {str(e)}")
            db.session.rollback()
            return []

    @staticmethod
    def _get_siparis_onerileri_bildirimi(otel_id: int) -> List[Dict]:
        """Otomatik sipariş önerileri bildirimi (sadece depo sorumlusu için)"""
        try:
            from utils.satin_alma_servisleri import SatinAlmaServisi

            # Otomatik sipariş önerilerini al
            oneriler = SatinAlmaServisi.otomatik_siparis_onerisi_olustur(otel_id)
            sayi = len(oneriler)

            if sayi > 0:
                return [{
                    'tip': 'success',
                    'mesaj': f'{sayi} ürün için sipariş önerisi mevcut',
                    'link': url_for('otomatik_siparis_onerileri'),
                    'sayi': sayi,
                    'oncelik': 3,
                    'ikon': 'lightbulb'
                }]

            return []

        except Exception as e:
            logger.error(f"Sipariş önerileri bildirimi alınırken hata: {str(e)}")
            db.session.rollback()
            return []

    @staticmethod
    def get_bildirim_sayilari(kullanici_id: int, rol: str, otel_id: Optional[int] = None) -> Dict:
        """
        Dashboard için özet bildirim sayıları

        Returns:
            dict: {
                'kritik_stok': int,
                'geciken_siparis': int,
                'onay_bekleyen': int,
                'toplam': int
            }
        """
        try:
            bildirimler = DashboardBildirimServisi.get_dashboard_bildirimleri(
                kullanici_id, rol, otel_id
            )

            sayilar = {
                'kritik_stok': 0,
                'geciken_siparis': 0,
                'onay_bekleyen': 0,
                'toplam': 0
            }

            for bildirim in bildirimler:
                sayi = bildirim.get('sayi', 0)
                sayilar['toplam'] += sayi

                if 'kritik stok' in bildirim['mesaj'].lower():
                    sayilar['kritik_stok'] = sayi
                elif 'gecikmede' in bildirim['mesaj'].lower():
                    sayilar['geciken_siparis'] = sayi
                elif 'onay bekliyor' in bildirim['mesaj'].lower():
                    sayilar['onay_bekleyen'] = sayi

            return sayilar

        except Exception as e:
            logger.error(f"Bildirim sayıları alınırken hata: {str(e)}")
            db.session.rollback()
            return {
                'kritik_stok': 0,
                'geciken_siparis': 0,
                'onay_bekleyen': 0,
                'toplam': 0
            }
