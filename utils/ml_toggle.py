"""
ML Toggle Helper - ML Analiz Sistemi Açma/Kapama

In-memory cache ile DB hit'i minimize eder.
SistemAyar tablosundaki 'ml_sistem_aktif' anahtarını kullanır.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# In-memory cache
_ml_cache = {
    'enabled': None,
    'last_check': None
}

CACHE_TTL_SECONDS = 30  # 30 saniye cache


def is_ml_enabled():
    """
    ML sistemi aktif mi kontrol et.
    In-memory cache kullanır, TTL dolunca DB'den okur.
    Returns: bool
    """
    import time
    
    now = time.time()
    
    # Cache geçerli mi?
    if (_ml_cache['enabled'] is not None and 
        _ml_cache['last_check'] is not None and
        (now - _ml_cache['last_check']) < CACHE_TTL_SECONDS):
        return _ml_cache['enabled']
    
    # DB'den oku
    try:
        from models import SistemAyar
        ayar = SistemAyar.query.filter_by(anahtar='ml_sistem_aktif').first()
        
        if ayar:
            enabled = ayar.deger.lower() in ('true', '1', 'evet', 'aktif')
        else:
            # Ayar yoksa default aktif
            enabled = True
        
        _ml_cache['enabled'] = enabled
        _ml_cache['last_check'] = now
        
        return enabled
        
    except Exception as e:
        logger.error(f"ML toggle DB okuma hatası: {e}")
        # Hata durumunda cache varsa onu kullan, yoksa aktif say
        return _ml_cache['enabled'] if _ml_cache['enabled'] is not None else True


def set_ml_enabled(enabled: bool, user_id: int = None):
    """
    ML sistemini aç/kapat.
    Args:
        enabled: True=aktif, False=devre dışı
        user_id: İşlemi yapan kullanıcı ID
    Returns: dict with success/message
    """
    try:
        from models import db, SistemAyar
        from utils.helpers import log_islem
        
        ayar = SistemAyar.query.filter_by(anahtar='ml_sistem_aktif').first()
        
        if not ayar:
            ayar = SistemAyar(
                anahtar='ml_sistem_aktif',
                deger=str(enabled).lower(),
                aciklama='ML Analiz Sistemi aktif/pasif durumu'
            )
            db.session.add(ayar)
        else:
            ayar.deger = str(enabled).lower()
        
        db.session.commit()
        
        # Cache güncelle
        import time
        _ml_cache['enabled'] = enabled
        _ml_cache['last_check'] = time.time()
        
        # Log
        durum = 'aktif' if enabled else 'devre dışı'
        log_islem('guncelleme', 'ml_sistem_toggle', {
            'durum': durum,
            'kullanici_id': user_id
        })
        
        logger.info(f"ML sistemi {durum} yapıldı (kullanıcı: {user_id})")
        
        return {'success': True, 'message': f'ML Analiz Sistemi {durum}'}
        
    except Exception as e:
        logger.error(f"ML toggle güncelleme hatası: {e}")
        return {'success': False, 'message': str(e)}


def get_ml_status():
    """
    ML sistem durumu detayları.
    Returns: dict
    """
    try:
        from models import SistemAyar
        
        ayar = SistemAyar.query.filter_by(anahtar='ml_sistem_aktif').first()
        
        enabled = True
        if ayar:
            enabled = ayar.deger.lower() in ('true', '1', 'evet', 'aktif')
        
        return {
            'enabled': enabled,
            'status_text': 'Aktif' if enabled else 'Devre Dışı',
            'db_value': ayar.deger if ayar else 'N/A',
            'cache_value': _ml_cache['enabled'],
        }
        
    except Exception as e:
        logger.error(f"ML status hatası: {e}")
        return {
            'enabled': True,
            'status_text': 'Bilinmiyor',
            'db_value': 'error',
            'cache_value': _ml_cache['enabled'],
        }


def invalidate_cache():
    """Cache'i temizle, sonraki çağrıda DB'den okur."""
    _ml_cache['enabled'] = None
    _ml_cache['last_check'] = None
