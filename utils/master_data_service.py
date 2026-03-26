"""
Master Data Service - Cache + Eager Loading Entegrasyonu

Bu modül master data sorgularını optimize eder:
1. Redis cache ile tekrarlayan sorguları önler
2. Eager loading ile N+1 problemini çözer
3. Blacklist koruması ile transactional data'yı korur

KULLANIM:
    from utils.master_data_service import MasterDataService
    
    # Ürün listesi (cached + eager loaded)
    urunler = MasterDataService.get_urunler()
    
    # Otel listesi (cached)
    oteller = MasterDataService.get_oteller()
    
    # Cache invalidation (ürün eklendiğinde/güncellendiğinde)
    MasterDataService.invalidate_urunler()

ÖNEMLI:
- Stok, zimmet, DND gibi transactional data bu servisten ALINMAZ
- Bu servis SADECE dropdown'lar ve listeler için kullanılır
"""

import logging
from typing import List
from sqlalchemy.orm import joinedload, selectinload

logger = logging.getLogger(__name__)


class MasterDataService:
    """
    Master data için cache + eager loading servisi.
    Singleton pattern - tüm uygulama tek instance kullanır.
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
    # ÜRÜN SERVİSLERİ
    # ============================================
    
    @staticmethod
    def get_urunler(aktif: bool = True, grup_id: int | None = None) -> List:
        """
        Ürün listesini cache + eager loading ile getir.
        
        Args:
            aktif: Sadece aktif ürünler
            grup_id: Ürün grubu filtresi
            
        Returns:
            List[Urun]: Ürün listesi (grup bilgisi dahil)
        """
        cache = MasterDataService._get_cache_manager()
        cache_key = f"urunler_{aktif}_{grup_id}"
        
        # Cache'den dene
        if cache and cache.enabled:
            cached = cache.get('urunler', aktif, grup_id)
            if cached is not None:
                logger.debug(f"✅ Cache HIT: {cache_key}")
                return cached
        
        # Database'den al (eager loading ile)
        try:
            from models import Urun
            
            query = Urun.query.options(
                joinedload(Urun.grup)  # Grup bilgisini eager load et
            )
            
            if aktif:
                query = query.filter_by(aktif=True)
            
            if grup_id:
                query = query.filter_by(grup_id=grup_id)
            
            urunler = query.order_by(Urun.urun_adi).all()
            
            # Cache'e yaz
            if cache and cache.enabled:
                cache.set('urunler', urunler, None, aktif, grup_id)
                logger.debug(f"✅ Cache SET: {cache_key}")
            
            return urunler
            
        except Exception as e:
            logger.error(f"Ürün listesi hatası: {str(e)}")
            return []
    
    @staticmethod
    def get_urun_gruplari(aktif: bool = True) -> List:
        """
        Ürün gruplarını cache ile getir.
        
        Args:
            aktif: Sadece aktif gruplar
            
        Returns:
            List[UrunGrup]: Ürün grubu listesi
        """
        cache = MasterDataService._get_cache_manager()
        
        # Cache'den dene
        if cache and cache.enabled:
            cached = cache.get('urun_gruplari', aktif)
            if cached is not None:
                return cached
        
        try:
            from models import UrunGrup
            
            query = UrunGrup.query
            if aktif:
                query = query.filter_by(aktif=True)
            
            gruplar = query.order_by(UrunGrup.grup_adi).all()
            
            # Cache'e yaz
            if cache and cache.enabled:
                cache.set('urun_gruplari', gruplar, None, aktif)
            
            return gruplar
            
        except Exception as e:
            logger.error(f"Ürün grupları hatası: {str(e)}")
            return []
    
    @staticmethod
    def invalidate_urunler():
        """Ürün cache'ini temizle"""
        cache = MasterDataService._get_cache_manager()
        if cache and cache.enabled:
            cache.invalidate('urunler')
            cache.invalidate('urun_gruplari')
            logger.info("🗑️ Ürün cache temizlendi")
    
    # ============================================
    # OTEL/KAT/ODA SERVİSLERİ
    # ============================================
    
    @staticmethod
    def get_oteller(aktif: bool = True) -> List:
        """
        Otel listesini cache ile getir.
        
        Args:
            aktif: Sadece aktif oteller
            
        Returns:
            List[Otel]: Otel listesi
        """
        cache = MasterDataService._get_cache_manager()
        
        # Cache'den dene
        if cache and cache.enabled:
            cached = cache.get('oteller', aktif)
            if cached is not None:
                return cached
        
        try:
            from models import Otel
            
            query = Otel.query
            if aktif:
                query = query.filter_by(aktif=True)
            
            oteller = query.order_by(Otel.ad).all()
            
            # Cache'e yaz
            if cache and cache.enabled:
                cache.set('oteller', oteller, None, aktif)
            
            return oteller
            
        except Exception as e:
            logger.error(f"Otel listesi hatası: {str(e)}")
            return []
    
    @staticmethod
    def get_katlar(otel_id: int | None = None, aktif: bool = True) -> List:
        """
        Kat listesini cache + eager loading ile getir.
        
        Args:
            otel_id: Otel filtresi
            aktif: Sadece aktif katlar
            
        Returns:
            List[Kat]: Kat listesi (otel bilgisi dahil)
        """
        cache = MasterDataService._get_cache_manager()
        
        # Cache'den dene
        if cache and cache.enabled:
            cached = cache.get('katlar', otel_id, aktif)
            if cached is not None:
                return cached
        
        try:
            from models import Kat
            
            query = Kat.query.options(
                joinedload(Kat.otel)  # Otel bilgisini eager load et
            )
            
            if aktif:
                query = query.filter_by(aktif=True)
            
            if otel_id:
                query = query.filter_by(otel_id=otel_id)
            
            katlar = query.order_by(Kat.kat_no).all()
            
            # Cache'e yaz
            if cache and cache.enabled:
                cache.set('katlar', katlar, None, otel_id, aktif)
            
            return katlar
            
        except Exception as e:
            logger.error(f"Kat listesi hatası: {str(e)}")
            return []
    
    @staticmethod
    def get_odalar(
        kat_id: int | None = None, otel_id: int | None = None, aktif: bool = True
    ) -> List:
        """
        Oda listesini cache + eager loading ile getir.
        
        Args:
            kat_id: Kat filtresi
            otel_id: Otel filtresi
            aktif: Sadece aktif odalar
            
        Returns:
            List[Oda]: Oda listesi (kat ve oda tipi bilgisi dahil)
        """
        cache = MasterDataService._get_cache_manager()
        
        # Cache'den dene
        if cache and cache.enabled:
            cached = cache.get('odalar', kat_id, otel_id, aktif)
            if cached is not None:
                return cached
        
        try:
            from models import Oda, Kat
            
            query = Oda.query.options(
                joinedload(Oda.kat).joinedload(Kat.otel),  # Kat ve otel bilgisini eager load et
                joinedload(Oda.oda_tipi_rel)  # Oda tipi bilgisini eager load et
            )
            
            if aktif:
                query = query.filter_by(aktif=True)
            
            if kat_id:
                query = query.filter_by(kat_id=kat_id)
            
            if otel_id:
                query = query.join(Kat).filter(Kat.otel_id == otel_id)
            
            odalar = query.order_by(Oda.oda_no).all()
            
            # Cache'e yaz
            if cache and cache.enabled:
                cache.set('odalar', odalar, None, kat_id, otel_id, aktif)
            
            return odalar
            
        except Exception as e:
            logger.error(f"Oda listesi hatası: {str(e)}")
            return []
    
    @staticmethod
    def get_oda_tipleri() -> List:
        """
        Oda tiplerini cache ile getir.
        
        Returns:
            List[OdaTipi]: Oda tipi listesi
        """
        cache = MasterDataService._get_cache_manager()
        
        # Cache'den dene
        if cache and cache.enabled:
            cached = cache.get('oda_tipleri')
            if cached is not None:
                return cached
        
        try:
            from models import OdaTipi
            
            tipler = OdaTipi.query.order_by(OdaTipi.tip_adi).all()
            
            # Cache'e yaz
            if cache and cache.enabled:
                cache.set('oda_tipleri', tipler)
            
            return tipler
            
        except Exception as e:
            logger.error(f"Oda tipleri hatası: {str(e)}")
            return []
    
    @staticmethod
    def invalidate_otel_cache():
        """Otel/Kat/Oda cache'ini temizle"""
        cache = MasterDataService._get_cache_manager()
        if cache and cache.enabled:
            cache.invalidate('oteller')
            cache.invalidate('katlar')
            cache.invalidate('odalar')
            cache.invalidate('oda_tipleri')
            logger.info("🗑️ Otel/Kat/Oda cache temizlendi")
    
    # ============================================
    # SETUP SERVİSLERİ
    # ============================================
    
    @staticmethod
    def get_setuplar(otel_id: int | None = None, aktif: bool = True) -> List:
        """
        Setup listesini cache + eager loading ile getir.
        
        Args:
            otel_id: Otel filtresi
            aktif: Sadece aktif setup'lar
            
        Returns:
            List[Setup]: Setup listesi (içerik bilgisi dahil)
        """
        cache = MasterDataService._get_cache_manager()
        
        # Cache'den dene
        if cache and cache.enabled:
            cached = cache.get('setuplar', otel_id, aktif)
            if cached is not None:
                return cached
        
        try:
            from models import Setup, SetupIcerik
            
            query = Setup.query.options(
                selectinload(Setup.icerikler).joinedload(SetupIcerik.urun)  # İçerikleri ve ürünleri eager load et
            )
            
            if aktif:
                query = query.filter_by(aktif=True)
            
            if otel_id:
                query = query.filter_by(otel_id=otel_id)
            
            setuplar = query.order_by(Setup.setup_adi).all()
            
            # Cache'e yaz
            if cache and cache.enabled:
                cache.set('setuplar', setuplar, None, otel_id, aktif)
            
            return setuplar
            
        except Exception as e:
            logger.error(f"Setup listesi hatası: {str(e)}")
            return []
    
    @staticmethod
    def invalidate_setup_cache():
        """Setup cache'ini temizle"""
        cache = MasterDataService._get_cache_manager()
        if cache and cache.enabled:
            cache.invalidate('setuplar')
            cache.invalidate('setup_icerik')
            logger.info("🗑️ Setup cache temizlendi")
    
    # ============================================
    # KULLANICI SERVİSLERİ
    # ============================================
    
    @staticmethod
    def get_kullanicilar(
        rol: str | None = None, otel_id: int | None = None, aktif: bool = True
    ) -> List:
        """
        Kullanıcı listesini eager loading ile getir.
        NOT: Kullanıcı listesi cache'lenmez (güvenlik)
        
        Args:
            rol: Rol filtresi
            otel_id: Otel filtresi
            aktif: Sadece aktif kullanıcılar
            
        Returns:
            List[Kullanici]: Kullanıcı listesi
        """
        try:
            from models import Kullanici, KullaniciOtel
            
            query = Kullanici.query.options(
                selectinload(Kullanici.otel_yetkileri).joinedload(KullaniciOtel.otel)
            )
            
            if aktif:
                query = query.filter_by(aktif=True)
            
            if rol:
                query = query.filter_by(rol=rol)
            
            if otel_id:
                query = query.filter_by(otel_id=otel_id)
            
            return query.order_by(Kullanici.ad, Kullanici.soyad).all()
            
        except Exception as e:
            logger.error(f"Kullanıcı listesi hatası: {str(e)}")
            return []
    
    # ============================================
    # TOPLU INVALIDATION
    # ============================================
    
    @staticmethod
    def invalidate_all():
        """Tüm master data cache'ini temizle"""
        MasterDataService.invalidate_urunler()
        MasterDataService.invalidate_otel_cache()
        MasterDataService.invalidate_setup_cache()
        logger.info("🗑️ Tüm master data cache temizlendi")
