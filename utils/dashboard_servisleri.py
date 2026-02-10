"""
Dashboard Bildirim Servisi

Bu modül, sistem yöneticisi ve depo sorumlusu dashboard'larında
gösterilecek bildirimleri yönetir.

Bildirim Tipleri:
- Kritik stok uyarıları
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from sqlalchemy import and_, or_
from models import db, UrunStok, Urun, Otel
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
        """
        try:
            bildirimler = []

            if rol == 'sistem_yoneticisi':
                bildirimler.extend(DashboardBildirimServisi._get_kritik_stok_bildirimleri())

            elif rol == 'depo_sorumlusu' and otel_id:
                bildirimler.extend(DashboardBildirimServisi._get_kritik_stok_bildirimleri(otel_id))

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
                    'link': url_for('kat_sorumlusu_siparisler'),
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
    def get_bildirim_sayilari(kullanici_id: int, rol: str, otel_id: Optional[int] = None) -> Dict:
        """
        Dashboard için özet bildirim sayıları

        Returns:
            dict: {
                'kritik_stok': int,
                'toplam': int
            }
        """
        try:
            bildirimler = DashboardBildirimServisi.get_dashboard_bildirimleri(
                kullanici_id, rol, otel_id
            )

            sayilar = {
                'kritik_stok': 0,
                'toplam': 0
            }

            for bildirim in bildirimler:
                sayi = bildirim.get('sayi', 0)
                sayilar['toplam'] += sayi

                if 'kritik stok' in bildirim['mesaj'].lower():
                    sayilar['kritik_stok'] = sayi

            return sayilar

        except Exception as e:
            logger.error(f"Bildirim sayıları alınırken hata: {str(e)}")
            db.session.rollback()
            return {
                'kritik_stok': 0,
                'toplam': 0
            }
