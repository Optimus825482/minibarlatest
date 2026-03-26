"""
Dashboard Data Service - Cache + Eager Loading ile Dashboard Verileri

Bu modül dashboard'larda kullanılan verileri optimize eder:
1. Sık kullanılan istatistikleri cache'ler
2. N+1 problemini eager loading ile çözer
3. Transactional data'yı cache'lemez (güvenlik)

KULLANIM:
    from utils.dashboard_data_service import DashboardDataService
    
    # Sistem yöneticisi dashboard verileri
    data = DashboardDataService.get_sistem_yoneticisi_stats()
    
    # Depo sorumlusu dashboard verileri
    data = DashboardDataService.get_depo_stats(otel_id)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import func

logger = logging.getLogger(__name__)


class DashboardDataService:
    """
    Dashboard verileri için cache + eager loading servisi.
    """
    
    @staticmethod
    def _get_cache_manager():
        """Cache manager'ı al (lazy import)"""
        try:
            from utils.cache_manager import cache_manager
            return cache_manager
        except ImportError:
            return None
    
    # ============================================
    # GENEL İSTATİSTİKLER (Cache'lenebilir)
    # ============================================
    
    @staticmethod
    def get_genel_istatistikler() -> Dict[str, int]:
        """
        Genel sistem istatistiklerini cache ile getir.
        
        Returns:
            Dict: {toplam_kat, toplam_oda, toplam_kullanici, toplam_personel, ...}
        """
        cache = DashboardDataService._get_cache_manager()
        cache_key = 'dashboard_genel_istatistikler'
        
        # Cache'den dene (kısa TTL - 60 saniye)
        if cache and cache.enabled:
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"✅ Cache HIT: {cache_key}")
                return cached
        
        try:
            from models import Kat, Oda, Kullanici, UrunGrup, Urun
            
            stats = {
                'toplam_kat': Kat.query.count(),
                'toplam_oda': Oda.query.count(),
                'toplam_kullanici': Kullanici.query.filter(
                    Kullanici.rol.in_(['admin', 'depo_sorumlusu', 'kat_sorumlusu']),
                    Kullanici.aktif.is_(True)
                ).count(),
                'toplam_personel': Kullanici.query.filter(
                    Kullanici.rol.in_(['depo_sorumlusu', 'kat_sorumlusu']),
                    Kullanici.aktif.is_(True)
                ).count(),
                'toplam_urun_grup': UrunGrup.query.filter_by(aktif=True).count(),
                'toplam_urun': Urun.query.filter_by(aktif=True).count(),
                'admin_count': Kullanici.query.filter_by(rol='admin', aktif=True).count(),
                'depo_count': Kullanici.query.filter_by(rol='depo_sorumlusu', aktif=True).count(),
                'kat_count': Kullanici.query.filter_by(rol='kat_sorumlusu', aktif=True).count(),
            }
            
            # Cache'e yaz (60 saniye TTL)
            if cache and cache.enabled:
                cache.set(cache_key, stats, 60)
                logger.debug(f"✅ Cache SET: {cache_key}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Genel istatistikler hatası: {str(e)}")
            return {
                'toplam_kat': 0, 'toplam_oda': 0, 'toplam_kullanici': 0,
                'toplam_personel': 0, 'toplam_urun_grup': 0, 'toplam_urun': 0,
                'admin_count': 0, 'depo_count': 0, 'kat_count': 0
            }
    
    @staticmethod
    def get_kat_oda_dagilimi() -> Dict[str, List]:
        """
        Kat bazlı oda dağılımını cache + eager loading ile getir.
        
        Returns:
            Dict: {kat_labels: [...], kat_oda_sayilari: [...]}
        """
        cache = DashboardDataService._get_cache_manager()
        cache_key = 'dashboard_kat_oda_dagilimi'
        
        # Cache'den dene
        if cache and cache.enabled:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            from models import Kat
            
            # Eager loading ile katları ve odalarını getir
            katlar = Kat.query.options(
                selectinload(Kat.odalar)
            ).filter_by(aktif=True).order_by(Kat.kat_no).all()
            
            result = {
                'kat_labels': [kat.kat_adi for kat in katlar],
                'kat_oda_sayilari': [len(kat.odalar) for kat in katlar]
            }
            
            # Cache'e yaz (5 dakika TTL)
            if cache and cache.enabled:
                cache.set(cache_key, result, 300)
            
            return result
            
        except Exception as e:
            logger.error(f"Kat oda dağılımı hatası: {str(e)}")
            return {'kat_labels': [], 'kat_oda_sayilari': []}
    
    # ============================================
    # SON EKLENENLER (Eager Loading)
    # ============================================
    
    @staticmethod
    def get_son_eklenenler(limit: int = 5) -> Dict[str, List]:
        """
        Son eklenen kayıtları eager loading ile getir.
        NOT: Bu veriler cache'lenmez (sık değişir)
        
        Args:
            limit: Her kategori için kayıt limiti
            
        Returns:
            Dict: {son_katlar, son_odalar, son_personeller, son_urunler}
        """
        try:
            from models import Kat, Oda, Kullanici, Urun
            
            # Son katlar (otel bilgisi ile)
            son_katlar = Kat.query.options(
                joinedload(Kat.otel)
            ).order_by(Kat.olusturma_tarihi.desc()).limit(limit).all()
            
            # Son odalar (kat ve otel bilgisi ile)
            son_odalar = Oda.query.options(
                joinedload(Oda.kat).joinedload(Kat.otel)
            ).order_by(Oda.olusturma_tarihi.desc()).limit(limit).all()
            
            # Son personeller
            son_personeller = Kullanici.query.filter(
                Kullanici.rol.in_(['depo_sorumlusu', 'kat_sorumlusu']),
                Kullanici.aktif.is_(True)
            ).order_by(Kullanici.olusturma_tarihi.desc()).limit(limit).all()
            
            # Son ürünler (grup bilgisi ile)
            son_urunler = Urun.query.options(
                joinedload(Urun.grup)
            ).filter_by(aktif=True).order_by(Urun.olusturma_tarihi.desc()).limit(limit).all()
            
            return {
                'son_katlar': son_katlar,
                'son_odalar': son_odalar,
                'son_personeller': son_personeller,
                'son_urunler': son_urunler
            }
            
        except Exception as e:
            logger.error(f"Son eklenenler hatası: {str(e)}")
            return {
                'son_katlar': [],
                'son_odalar': [],
                'son_personeller': [],
                'son_urunler': []
            }
    
    # ============================================
    # STOK HAREKETLERİ (Eager Loading - Cache YOK)
    # ============================================
    
    @staticmethod
    def get_son_stok_hareketleri(limit: int = 10) -> List:
        """
        Son stok hareketlerini eager loading ile getir.
        NOT: Transactional data - ASLA cache'lenmez!
        
        Args:
            limit: Kayıt limiti
            
        Returns:
            List[StokHareket]: Son stok hareketleri
        """
        try:
            from models import StokHareket, Urun
            
            return StokHareket.query.options(
                joinedload(StokHareket.urun).joinedload(Urun.grup),
                joinedload(StokHareket.islem_yapan)
            ).order_by(StokHareket.islem_tarihi.desc()).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Son stok hareketleri hatası: {str(e)}")
            return []
    
    @staticmethod
    def get_stok_hareket_grafik_verileri(gun_sayisi: int = 7) -> Dict[str, List]:
        """
        Son X günün stok hareket grafiği verilerini getir.
        NOT: Transactional data - ASLA cache'lenmez!
        
        Args:
            gun_sayisi: Kaç günlük veri
            
        Returns:
            Dict: {gun_labels, giris_verileri, cikis_verileri}
        """
        try:
            from models import db, StokHareket
            import pytz
            
            KKTC_TZ = pytz.timezone('Europe/Nicosia')
            bugun = datetime.now(KKTC_TZ).date()
            
            gun_labels = []
            giris_verileri = []
            cikis_verileri = []
            
            for i in range(gun_sayisi - 1, -1, -1):
                tarih = bugun - timedelta(days=i)
                gun_labels.append(tarih.strftime('%d.%m'))
                
                # Giriş
                giris = db.session.query(func.sum(StokHareket.miktar)).filter(
                    func.date(StokHareket.islem_tarihi) == tarih,
                    StokHareket.hareket_tipi == 'giris'
                ).scalar() or 0
                giris_verileri.append(float(giris))
                
                # Çıkış
                cikis = db.session.query(func.sum(StokHareket.miktar)).filter(
                    func.date(StokHareket.islem_tarihi) == tarih,
                    StokHareket.hareket_tipi == 'cikis'
                ).scalar() or 0
                cikis_verileri.append(float(cikis))
            
            return {
                'gun_labels': gun_labels,
                'giris_verileri': giris_verileri,
                'cikis_verileri': cikis_verileri
            }
            
        except Exception as e:
            logger.error(f"Stok hareket grafik verileri hatası: {str(e)}")
            return {'gun_labels': [], 'giris_verileri': [], 'cikis_verileri': []}
    
    # ============================================
    # ZİMMET İSTATİSTİKLERİ (Eager Loading - Cache YOK)
    # ============================================
    
    @staticmethod
    def get_zimmet_istatistikleri() -> Dict[str, Any]:
        """
        Zimmet istatistiklerini eager loading ile getir.
        NOT: Transactional data - ASLA cache'lenmez!
        
        Returns:
            Dict: {aktif_zimmetler, toplam_iade, bu_ay_iadeler, iptal_zimmetler}
        """
        try:
            from models import db, PersonelZimmet, PersonelZimmetDetay, StokHareket
            import pytz
            
            KKTC_TZ = pytz.timezone('Europe/Nicosia')
            
            aktif_zimmetler = PersonelZimmet.query.filter_by(durum='aktif').count()
            
            toplam_iade = db.session.query(func.sum(PersonelZimmetDetay.iade_edilen_miktar)).filter(
                PersonelZimmetDetay.iade_edilen_miktar > 0
            ).scalar() or 0
            
            # Bu ay yapılan iade işlemleri
            ay_basi = datetime.now(KKTC_TZ).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            bu_ay_iadeler = StokHareket.query.filter(
                StokHareket.hareket_tipi == 'giris',
                StokHareket.aciklama.like('%Zimmet iadesi%'),
                StokHareket.islem_tarihi >= ay_basi
            ).count()
            
            iptal_zimmetler = PersonelZimmet.query.filter_by(durum='iptal').count()
            
            return {
                'aktif_zimmetler': aktif_zimmetler,
                'toplam_iade': int(toplam_iade),
                'bu_ay_iadeler': bu_ay_iadeler,
                'iptal_zimmetler': iptal_zimmetler
            }
            
        except Exception as e:
            logger.error(f"Zimmet istatistikleri hatası: {str(e)}")
            return {
                'aktif_zimmetler': 0,
                'toplam_iade': 0,
                'bu_ay_iadeler': 0,
                'iptal_zimmetler': 0
            }
    
    # ============================================
    # ÜRÜN TÜKETİM VERİLERİ (Cache'lenebilir - 5 dk)
    # ============================================
    
    @staticmethod
    def get_urun_tuketim_verileri(gun_sayisi: int = 30, limit: int = 10) -> Dict[str, List]:
        """
        En çok tüketilen ürünleri cache ile getir.
        
        Args:
            gun_sayisi: Kaç günlük veri
            limit: Kaç ürün
            
        Returns:
            Dict: {urun_labels, urun_tuketim_miktarlari}
        """
        cache = DashboardDataService._get_cache_manager()
        cache_key = f'dashboard_urun_tuketim_{gun_sayisi}_{limit}'
        
        # Cache'den dene (5 dakika TTL)
        if cache and cache.enabled:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        try:
            from models import db, Urun, MinibarIslem, MinibarIslemDetay
            import pytz
            
            KKTC_TZ = pytz.timezone('Europe/Nicosia')
            bugun = datetime.now(KKTC_TZ).date()
            baslangic = bugun - timedelta(days=gun_sayisi)
            
            # Minibar işlemlerinden en çok tüketilen ürünleri al
            urun_tuketim = db.session.query(
                Urun.urun_adi,
                func.sum(MinibarIslemDetay.tuketim).label('toplam_tuketim')
            ).join(
                MinibarIslemDetay, MinibarIslemDetay.urun_id == Urun.id
            ).join(
                MinibarIslem, MinibarIslem.id == MinibarIslemDetay.islem_id
            ).filter(
                func.date(MinibarIslem.islem_tarihi) >= baslangic,
                MinibarIslemDetay.tuketim > 0
            ).group_by(
                Urun.id, Urun.urun_adi
            ).order_by(
                func.sum(MinibarIslemDetay.tuketim).desc()
            ).limit(limit).all()
            
            result = {
                'urun_labels': [u[0] for u in urun_tuketim],
                'urun_tuketim_miktarlari': [float(u[1] or 0) for u in urun_tuketim]
            }
            
            # Cache'e yaz (5 dakika TTL)
            if cache and cache.enabled:
                cache.set(cache_key, result, 300)
            
            return result
            
        except Exception as e:
            logger.error(f"Ürün tüketim verileri hatası: {str(e)}")
            return {'urun_labels': [], 'urun_tuketim_miktarlari': []}
    
    # ============================================
    # CACHE INVALIDATION
    # ============================================
    
    @staticmethod
    def invalidate_dashboard_cache():
        """Dashboard cache'ini temizle"""
        cache = DashboardDataService._get_cache_manager()
        if cache and cache.enabled:
            cache.invalidate('dashboard_genel_istatistikler')
            cache.invalidate('dashboard_kat_oda_dagilimi')
            cache.invalidate('dashboard_urun_tuketim')
            logger.info("🗑️ Dashboard cache temizlendi")
