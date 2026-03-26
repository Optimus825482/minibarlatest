# -*- coding: utf-8 -*-
"""
Otel bazlı oda tipleri tanımları
"""

# Otellere göre oda tipleri
OTEL_ODA_TIPLERI = {
    'Merit Royal Diamond': [
        'Standard Room',
        'Deluxe Room',
        'Junior Suite',
        'Queen Suite',
        'King Suite',
        'Royal Suite'
    ],
    'Merit Royal Premium': [
        'QUEEN DÜZ SUITE ODA',
        'STANDART FRENCH ODA',
        'STANDART TWİN CONNECTION ODA',
        'STANDART FRENCH CONNECTION ODA',
        'STANDART SINGLE ODA',
        'STANDART TWIN ODA',
        'JUNIOR SUIT ODA',
        'SINGLE JUNIOR SUIT ODA',
        'KING SUIT ODA',
        'STANDART DÜZ CONNECTION ODA'
    ],
    'Merit Royal Hotel': [
        'STANDART EĞRİSEL ODA',
        'QUEEN DÜZ SUITE ODA',
        'JUNIOR SUITE ODA',
        'KİNG SUITE ODA',
        'STANDART EĞRİSEL CONNECTION ODA',
        'QUEEN EĞRİSEL CONNECTION ODA',
        'QUEEN EĞRİSEL SUIT ODA',
        '5. KAT ROYAL SUIT ODA',
        '5.KAT KING SUIT'
    ]
}

def get_oda_tipleri_by_otel(otel_adi):
    """
    Otel adına göre oda tiplerini döndür
    
    Args:
        otel_adi (str): Otel adı
        
    Returns:
        list: Oda tipleri listesi
    """
    return OTEL_ODA_TIPLERI.get(otel_adi, [])

def get_oda_tipleri_by_otel_id(otel_id):
    """
    Otel ID'sine göre oda tiplerini döndür
    
    Args:
        otel_id (int): Otel ID
        
    Returns:
        list: Oda tipleri listesi
    """
    from models import db, Otel
    
    try:
        otel = db.session.get(Otel, otel_id)
        if otel:
            return get_oda_tipleri_by_otel(otel.ad)
        return []
    except Exception:
        return []

def get_tum_oda_tipleri():
    """
    Tüm oda tiplerini döndür (tekrarsız)
    
    Returns:
        list: Tüm oda tipleri listesi
    """
    tum_tipler = []
    for tipler in OTEL_ODA_TIPLERI.values():
        tum_tipler.extend(tipler)
    return sorted(list(set(tum_tipler)))
