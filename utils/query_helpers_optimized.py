"""
Query Optimization Helpers - N+1 Problem Çözümleri
Erkan için - Eager Loading ve Optimized Query'ler
"""

from sqlalchemy.orm import joinedload, selectinload, subqueryload
from models import (
    db, PersonelZimmet, PersonelZimmetDetay, MinibarIslem, MinibarIslemDetay,
    StokHareket, Urun, Kullanici, Oda, Kat, UrunGrup
)
import logging

logger = logging.getLogger(__name__)


def get_zimmetler_optimized(durum=None, personel_id=None, limit=None):
    """
    Zimmet kayıtlarını N+1 problemi olmadan getir
    
    Args:
        durum: Zimmet durumu ('aktif', 'iade_edildi', 'iptal')
        personel_id: Personel ID filtresi
        limit: Kayıt limiti
    
    Returns:
        List[PersonelZimmet]: Optimize edilmiş zimmet listesi
    """
    try:
        query = PersonelZimmet.query.options(
            # Personel bilgisini eager load et
            joinedload(PersonelZimmet.personel),
            # Teslim eden bilgisini eager load et
            joinedload(PersonelZimmet.teslim_eden),
            # Detayları ve ürünleri eager load et
            selectinload(PersonelZimmet.detaylar).joinedload(PersonelZimmetDetay.urun).joinedload(Urun.grup)
        )
        
        if durum:
            query = query.filter_by(durum=durum)
        
        if personel_id:
            query = query.filter_by(personel_id=personel_id)
        
        query = query.order_by(PersonelZimmet.zimmet_tarihi.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
        
    except Exception as e:
        logger.error(f"Zimmet query hatası: {e}")
        return []


def get_minibar_islemler_optimized(oda_id=None, personel_id=None, islem_tipi=None, limit=None):
    """
    Minibar işlemlerini N+1 problemi olmadan getir
    
    Args:
        oda_id: Oda ID filtresi
        personel_id: Personel ID filtresi
        islem_tipi: İşlem tipi filtresi
        limit: Kayıt limiti
    
    Returns:
        List[MinibarIslem]: Optimize edilmiş minibar işlem listesi
    """
    try:
        query = MinibarIslem.query.options(
            # Oda ve kat bilgisini eager load et
            joinedload(MinibarIslem.oda).joinedload(Oda.kat),
            # Personel bilgisini eager load et
            joinedload(MinibarIslem.personel),
            # Detayları ve ürünleri eager load et
            selectinload(MinibarIslem.detaylar).joinedload(MinibarIslemDetay.urun).joinedload(Urun.grup)
        )
        
        if oda_id:
            query = query.filter_by(oda_id=oda_id)
        
        if personel_id:
            query = query.filter_by(personel_id=personel_id)
        
        if islem_tipi:
            query = query.filter_by(islem_tipi=islem_tipi)
        
        query = query.order_by(MinibarIslem.islem_tarihi.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
        
    except Exception as e:
        logger.error(f"Minibar işlem query hatası: {e}")
        return []


def get_stok_hareketleri_optimized(urun_id=None, hareket_tipi=None, limit=50):
    """
    Stok hareketlerini N+1 problemi olmadan getir
    
    Args:
        urun_id: Ürün ID filtresi
        hareket_tipi: Hareket tipi filtresi
        limit: Kayıt limiti (default: 50)
    
    Returns:
        List[StokHareket]: Optimize edilmiş stok hareket listesi
    """
    try:
        query = StokHareket.query.options(
            # Ürün ve grup bilgisini eager load et
            joinedload(StokHareket.urun).joinedload(Urun.grup),
            # İşlem yapan bilgisini eager load et
            joinedload(StokHareket.islem_yapan)
        )
        
        if urun_id:
            query = query.filter_by(urun_id=urun_id)
        
        if hareket_tipi:
            query = query.filter_by(hareket_tipi=hareket_tipi)
        
        query = query.order_by(StokHareket.islem_tarihi.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
        
    except Exception as e:
        logger.error(f"Stok hareket query hatası: {e}")
        return []


def get_urunler_with_stok_optimized(grup_id=None, aktif=True):
    """
    Ürünleri stok bilgileriyle birlikte getir
    
    Args:
        grup_id: Ürün grubu ID filtresi
        aktif: Sadece aktif ürünler
    
    Returns:
        List[Urun]: Optimize edilmiş ürün listesi
    """
    try:
        query = Urun.query.options(
            # Grup bilgisini eager load et
            joinedload(Urun.grup),
            # Stok bilgisini eager load et
            joinedload(Urun.stok)
        )
        
        if aktif:
            query = query.filter_by(aktif=True)
        
        if grup_id:
            query = query.filter_by(grup_id=grup_id)
        
        query = query.order_by(Urun.urun_adi)
        
        return query.all()
        
    except Exception as e:
        logger.error(f"Ürün query hatası: {e}")
        return []


def get_odalar_with_relations_optimized(kat_id=None, aktif=True):
    """
    Odaları ilişkili verilerle birlikte getir
    
    Args:
        kat_id: Kat ID filtresi
        aktif: Sadece aktif odalar
    
    Returns:
        List[Oda]: Optimize edilmiş oda listesi
    """
    try:
        query = Oda.query.options(
            # Kat bilgisini eager load et
            joinedload(Oda.kat),
            # Oda tipi bilgisini eager load et
            joinedload(Oda.oda_tipi_rel)
        )
        
        if aktif:
            query = query.filter_by(aktif=True)
        
        if kat_id:
            query = query.filter_by(kat_id=kat_id)
        
        query = query.order_by(Oda.oda_no)
        
        return query.all()
        
    except Exception as e:
        logger.error(f"Oda query hatası: {e}")
        return []


def bulk_insert_stok_hareketleri(hareket_data_list, session):
    """
    Toplu stok hareketi ekleme - Performans optimizasyonu
    
    Args:
        hareket_data_list: List[dict] - Stok hareket verileri
        session: SQLAlchemy session
    
    Returns:
        int: Eklenen kayıt sayısı
    """
    try:
        if not hareket_data_list:
            return 0
        
        # Bulk insert kullan
        session.bulk_insert_mappings(StokHareket, hareket_data_list)
        session.commit()
        
        logger.info(f"✅ {len(hareket_data_list)} stok hareketi toplu eklendi")
        return len(hareket_data_list)
        
    except Exception as e:
        session.rollback()
        logger.error(f"Bulk insert hatası: {e}")
        return 0


def paginate_cursor_based(model, order_column, last_id=None, limit=50):
    """
    Cursor-based pagination - OFFSET yerine daha hızlı
    
    Args:
        model: SQLAlchemy model
        order_column: Sıralama kolonu (örn: Urun.id)
        last_id: Son görülen ID (cursor)
        limit: Sayfa başına kayıt sayısı
    
    Returns:
        dict: {
            'items': List[Model],
            'next_cursor': int,
            'has_next': bool
        }
    """
    try:
        query = model.query
        
        if last_id:
            query = query.filter(order_column > last_id)
        
        query = query.order_by(order_column).limit(limit + 1)
        items = query.all()
        
        has_next = len(items) > limit
        if has_next:
            items = items[:limit]
        
        next_cursor = getattr(items[-1], order_column.key) if items else None
        
        return {
            'items': items,
            'next_cursor': next_cursor,
            'has_next': has_next
        }
        
    except Exception as e:
        logger.error(f"Pagination hatası: {e}")
        return {
            'items': [],
            'next_cursor': None,
            'has_next': False
        }


def get_minibar_durumlari_optimized(kat_id=None, oda_id=None):
    """
    Minibar durumlarını optimize edilmiş şekilde getir
    
    Args:
        kat_id: Kat ID filtresi
        oda_id: Oda ID filtresi
    
    Returns:
        dict: Minibar durum bilgileri
    """
    try:
        # Katları getir
        katlar = Kat.query.filter_by(aktif=True).order_by(Kat.kat_no).all()
        
        # Odaları getir (eager loading ile)
        odalar = []
        if kat_id:
            odalar = Oda.query.options(
                joinedload(Oda.kat)
            ).filter_by(
                kat_id=kat_id,
                aktif=True
            ).order_by(Oda.oda_no).all()
        
        # Minibar bilgisi
        minibar_bilgisi = None
        if oda_id:
            # Son minibar işlemini getir (eager loading ile)
            son_islem = MinibarIslem.query.options(
                joinedload(MinibarIslem.oda).joinedload(Oda.kat),
                joinedload(MinibarIslem.personel),
                selectinload(MinibarIslem.detaylar).joinedload(MinibarIslemDetay.urun).joinedload(Urun.grup)
            ).filter_by(
                oda_id=oda_id
            ).order_by(
                MinibarIslem.islem_tarihi.desc()
            ).first()
            
            if son_islem:
                # Tüm işlemleri getir (eager loading ile)
                tum_islemler = MinibarIslem.query.options(
                    selectinload(MinibarIslem.detaylar).joinedload(MinibarIslemDetay.urun)
                ).filter_by(
                    oda_id=oda_id
                ).order_by(
                    MinibarIslem.islem_tarihi.asc()
                ).all()
                
                # Ürün toplamlarını hesapla
                urun_toplam = {}
                ilk_dolum_yapildi = set()
                
                for islem in tum_islemler:
                    for detay in islem.detaylar:
                        urun_id = detay.urun_id
                        if urun_id not in urun_toplam:
                            urun_toplam[urun_id] = {
                                'urun': detay.urun,
                                'toplam_eklenen_ilk_dolum': 0,
                                'toplam_eklenen_doldurma': 0,
                                'toplam_tuketim': 0,
                                'ilk_baslangic': detay.baslangic_stok,
                                'son_bitis': detay.bitis_stok
                            }
                        
                        if islem.islem_tipi == 'ilk_dolum' and urun_id not in ilk_dolum_yapildi:
                            urun_toplam[urun_id]['toplam_eklenen_ilk_dolum'] += detay.eklenen_miktar
                            ilk_dolum_yapildi.add(urun_id)
                        elif islem.islem_tipi in ['doldurma', 'kontrol']:
                            urun_toplam[urun_id]['toplam_eklenen_doldurma'] += detay.eklenen_miktar
                            urun_toplam[urun_id]['toplam_tuketim'] += detay.eklenen_miktar
                        
                        urun_toplam[urun_id]['son_bitis'] = detay.bitis_stok
                
                # Minibar ürünlerini hazırla
                minibar_urunler = []
                for detay in son_islem.detaylar:
                    urun_id = detay.urun_id
                    urun_data = urun_toplam.get(urun_id, {})
                    
                    ilk_dolum_eklenen = urun_data.get('toplam_eklenen_ilk_dolum', 0)
                    doldurma_eklenen = urun_data.get('toplam_eklenen_doldurma', 0)
                    toplam_eklenen = ilk_dolum_eklenen + doldurma_eklenen
                    toplam_tuketim = urun_data.get('toplam_tuketim', 0)
                    mevcut_miktar = urun_data.get('son_bitis', 0)
                    
                    minibar_urunler.append({
                        'urun': detay.urun,
                        'baslangic_stok': urun_data.get('ilk_baslangic', 0),
                        'bitis_stok': urun_data.get('son_bitis', 0),
                        'eklenen_miktar': toplam_eklenen,
                        'tuketim': toplam_tuketim,
                        'mevcut_miktar': mevcut_miktar
                    })
                
                minibar_bilgisi = {
                    'oda': son_islem.oda,
                    'son_islem': son_islem,
                    'urunler': minibar_urunler,
                    'toplam_urun': len(minibar_urunler),
                    'toplam_miktar': sum(u['mevcut_miktar'] for u in minibar_urunler)
                }
        
        return {
            'katlar': katlar,
            'odalar': odalar,
            'minibar_bilgisi': minibar_bilgisi
        }
        
    except Exception as e:
        logger.error(f"Minibar durum query hatası: {e}")
        return {
            'katlar': [],
            'odalar': [],
            'minibar_bilgisi': None
        }
