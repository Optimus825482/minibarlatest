"""
Query Helper Functions
PostgreSQL için optimize edilmiş query helper'ları
"""

from sqlalchemy.orm import joinedload, selectinload
from models import (
    PersonelZimmet, PersonelZimmetDetay, MinibarIslem, MinibarIslemDetay,
    Urun, StokHareket, Oda
)


def get_zimmetler_optimized(personel_id=None, durum=None):
    """
    Optimized zimmet query with eager loading
    N+1 query problemini önler
    """
    query = PersonelZimmet.query.options(
        # Load related personel
        joinedload(PersonelZimmet.personel),
        joinedload(PersonelZimmet.teslim_eden),
        
        # Load detaylar with their urun and grup
        selectinload(PersonelZimmet.detaylar).joinedload(
            PersonelZimmetDetay.urun
        ).joinedload(Urun.grup)
    )
    
    if personel_id:
        query = query.filter_by(personel_id=personel_id)
    if durum:
        query = query.filter_by(durum=durum)
    
    return query.all()


def get_minibar_islemler_optimized(oda_id, limit=10):
    """Optimized minibar query"""
    return MinibarIslem.query.options(
        joinedload(MinibarIslem.oda).joinedload(Oda.kat),
        joinedload(MinibarIslem.personel),
        selectinload(MinibarIslem.detaylar).joinedload(
            MinibarIslemDetay.urun
        ).joinedload(Urun.grup)
    ).filter_by(oda_id=oda_id)\
     .order_by(MinibarIslem.islem_tarihi.desc())\
     .limit(limit)\
     .all()


def get_stok_hareketleri_optimized(urun_id=None, limit=50):
    """Optimized stok hareket query"""
    query = StokHareket.query.options(
        joinedload(StokHareket.urun).joinedload(Urun.grup),
        joinedload(StokHareket.islem_yapan)
    )
    
    if urun_id:
        query = query.filter_by(urun_id=urun_id)
    
    return query.order_by(StokHareket.islem_tarihi.desc()).limit(limit).all()


def paginate_cursor_based(model, cursor_field, cursor_value, limit=50):
    """
    Cursor-based pagination (faster than OFFSET)
    
    Args:
        model: SQLAlchemy model
        cursor_field: Field to use as cursor (e.g., Urun.id)
        cursor_value: Last cursor value from previous page
        limit: Items per page
        
    Returns:
        dict with items, next_cursor, has_next
    """
    query = model.query
    
    if cursor_value:
        query = query.filter(cursor_field > cursor_value)
    
    items = query.order_by(cursor_field).limit(limit + 1).all()
    
    has_next = len(items) > limit
    if has_next:
        items = items[:limit]
    
    next_cursor = getattr(items[-1], cursor_field.key) if items else None
    
    return {
        'items': items,
        'next_cursor': next_cursor,
        'has_next': has_next
    }


def bulk_insert_stok_hareketleri(hareketler_data, session):
    """
    Bulk insert for better performance
    
    Args:
        hareketler_data: List of dicts with hareket data
        session: Database session
    """
    from models import StokHareket
    
    hareketler = [
        StokHareket(**data) for data in hareketler_data
    ]
    
    session.bulk_save_objects(hareketler)
    session.commit()
    
    return len(hareketler)


def bulk_update_zimmet_detay(updates, session):
    """
    Bulk update using CASE statement
    
    Args:
        updates: List of dicts with id and kalan_miktar
        session: Database session
    """
    from sqlalchemy import case, update
    from models import PersonelZimmetDetay
    
    # Build CASE statement
    when_clauses = {
        update['id']: update['kalan_miktar'] 
        for update in updates
    }
    
    stmt = update(PersonelZimmetDetay).where(
        PersonelZimmetDetay.id.in_(when_clauses.keys())
    ).values(
        kalan_miktar=case(when_clauses, value=PersonelZimmetDetay.id)
    )
    
    session.execute(stmt)
    session.commit()
