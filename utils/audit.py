"""
Audit Trail - Denetim İzi Yardımcı Fonksiyonları
Her veri değişikliğini otomatik olarak kaydeder
"""

import json
import logging
from datetime import datetime
from flask import request, session
from models import db, AuditLog
from functools import wraps

logger = logging.getLogger(__name__)


def get_client_info():
    """İstemci bilgilerini al"""
    try:
        if request:
            return {
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
                'method': request.method,
                'url': request.url,
                'endpoint': request.endpoint
            }
    except RuntimeError:
        # Request context yoksa
        pass
    
    return {
        'ip': None,
        'user_agent': 'Test/Script',
        'method': None,
        'url': None,
        'endpoint': None
    }


def get_user_info():
    """Oturumdaki kullanıcı bilgilerini al"""
    from models import Kullanici
    
    try:
        if session:
            kullanici_id = session.get('kullanici_id')
            if kullanici_id:
                kullanici = Kullanici.query.get(kullanici_id)
                if kullanici:
                    return kullanici.id, kullanici.kullanici_adi, kullanici.rol
                return kullanici_id, 'Bilinmeyen', 'bilinmeyen'
    except RuntimeError:
        # Session context yoksa (test/script durumu)
        pass
    
    return None, 'System', 'sistem'


def serialize_model(model_instance):
    """Model instance'ını JSON'a çevir"""
    if model_instance is None:
        return None
    
    # Eğer zaten dict ise, direkt dön (test/script durumları için)
    if isinstance(model_instance, dict):
        return model_instance
    
    result = {}
    for column in model_instance.__table__.columns:
        value = getattr(model_instance, column.name)
        
        # DateTime objelerini string'e çevir
        if isinstance(value, datetime):
            value = value.isoformat()
        # Diğer serializable olmayan tipleri string'e çevir
        elif not isinstance(value, (str, int, float, bool, type(None))):
            value = str(value)
        
        result[column.name] = value
    
    return result


def create_change_summary(eski_deger, yeni_deger, tablo_adi):
    """Değişikliklerin okunabilir özetini oluştur"""
    if not eski_deger and not yeni_deger:
        return None
    
    # Yeni kayıt oluşturma
    if not eski_deger:
        return f"Yeni {tablo_adi} kaydı oluşturuldu"
    
    # Kayıt silme
    if not yeni_deger:
        return f"{tablo_adi} kaydı silindi"
    
    # Güncelleme - değişen alanları bul
    eski = json.loads(eski_deger) if isinstance(eski_deger, str) else eski_deger
    yeni = json.loads(yeni_deger) if isinstance(yeni_deger, str) else yeni_deger
    
    degisiklikler = []
    for key in yeni.keys():
        if key not in eski:
            degisiklikler.append(f"'{key}' eklendi: {yeni[key]}")
        elif eski[key] != yeni[key]:
            degisiklikler.append(f"'{key}': {eski[key]} → {yeni[key]}")
    
    if degisiklikler:
        return "; ".join(degisiklikler[:5])  # İlk 5 değişiklik
    
    return "Değişiklik yok"


def log_audit(
    islem_tipi,
    tablo_adi,
    kayit_id=None,
    eski_deger=None,
    yeni_deger=None,
    aciklama=None,
    basarili=True,
    hata_mesaji=None
):
    """
    Audit log kaydı oluştur
    
    Args:
        islem_tipi: 'create', 'update', 'delete', 'login', 'logout', 'view', 'export', 'import'
        tablo_adi: Etkilenen tablo adı
        kayit_id: Etkilenen kayıt ID'si
        eski_deger: Eski değerler (dict veya model instance)
        yeni_deger: Yeni değerler (dict veya model instance)
        aciklama: Ek açıklama
        basarili: İşlem başarılı mı?
        hata_mesaji: Hata mesajı (varsa)
    """
    try:
        # Kullanıcı bilgilerini al
        kullanici_id, kullanici_adi, kullanici_rol = get_user_info()
        
        # İstemci bilgilerini al
        client_info = get_client_info()
        
        # Değerleri serialize et
        if eski_deger and not isinstance(eski_deger, str):
            eski_deger_json = json.dumps(serialize_model(eski_deger), ensure_ascii=False)
        else:
            eski_deger_json = eski_deger
        
        if yeni_deger and not isinstance(yeni_deger, str):
            yeni_deger_json = json.dumps(serialize_model(yeni_deger), ensure_ascii=False)
        else:
            yeni_deger_json = yeni_deger
        
        # Değişiklik özetini oluştur
        degisiklik_ozeti = create_change_summary(eski_deger_json, yeni_deger_json, tablo_adi)
        
        # Audit log kaydı oluştur
        audit = AuditLog(
            kullanici_id=kullanici_id,
            kullanici_adi=kullanici_adi,
            kullanici_rol=kullanici_rol,
            islem_tipi=islem_tipi,
            tablo_adi=tablo_adi,
            kayit_id=kayit_id,
            eski_deger=eski_deger_json,
            yeni_deger=yeni_deger_json,
            degisiklik_ozeti=degisiklik_ozeti,
            http_method=client_info['method'],
            url=client_info['url'],
            endpoint=client_info['endpoint'],
            ip_adresi=client_info['ip'],
            user_agent=client_info['user_agent'],
            aciklama=aciklama,
            basarili=basarili,
            hata_mesaji=hata_mesaji
        )
        
        db.session.add(audit)
        db.session.commit()
        
        return audit
        
    except Exception as e:
        # Audit log hatası ana işlemi etkilememeli
        print(f"⚠️ Audit log hatası: {str(e)}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return None


def audit_trail(islem_tipi, tablo_adi):
    """
    Decorator: Fonksiyonu audit trail ile sarmallar
    
    Kullanım:
        @audit_trail('create', 'urunler')
        def urun_ekle():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            try:
                # Fonksiyonu çalıştır
                result = func(*args, **kwargs)
                
                # Başarılı işlemi logla
                log_audit(
                    islem_tipi=islem_tipi,
                    tablo_adi=tablo_adi,
                    basarili=True
                )
                
                return result
                
            except Exception as e:
                # Hatalı işlemi logla
                hata_mesaji = str(e)

                log_audit(
                    islem_tipi=islem_tipi,
                    tablo_adi=tablo_adi,
                    basarili=False,
                    hata_mesaji=hata_mesaji
                )
                
                # Hatayı tekrar fırlat
                raise
        
        return wrapper
    return decorator


# Özel audit fonksiyonları

def audit_login(kullanici_id, kullanici_adi, kullanici_rol, basarili=True, hata_mesaji=None):
    """Login işlemini logla"""
    client_info = get_client_info()
    
    audit = AuditLog(
        kullanici_id=kullanici_id,
        kullanici_adi=kullanici_adi,
        kullanici_rol=kullanici_rol,
        islem_tipi='login',
        tablo_adi='kullanicilar',
        kayit_id=kullanici_id,
        degisiklik_ozeti='Kullanıcı sisteme giriş yaptı',
        http_method=client_info['method'],
        url=client_info['url'],
        endpoint=client_info['endpoint'],
        ip_adresi=client_info['ip'],
        user_agent=client_info['user_agent'],
        basarili=basarili,
        hata_mesaji=hata_mesaji
    )
    
    db.session.add(audit)
    db.session.commit()


def audit_logout():
    """Logout işlemini logla"""
    kullanici_id, kullanici_adi, kullanici_rol = get_user_info()
    client_info = get_client_info()
    
    audit = AuditLog(
        kullanici_id=kullanici_id,
        kullanici_adi=kullanici_adi,
        kullanici_rol=kullanici_rol,
        islem_tipi='logout',
        tablo_adi='kullanicilar',
        kayit_id=kullanici_id,
        degisiklik_ozeti='Kullanıcı sistemden çıkış yaptı',
        http_method=client_info['method'],
        url=client_info['url'],
        endpoint=client_info['endpoint'],
        ip_adresi=client_info['ip'],
        user_agent=client_info['user_agent'],
        basarili=True
    )
    
    db.session.add(audit)
    db.session.commit()


def audit_create(tablo_adi, kayit_id, yeni_deger, aciklama=None):
    """Kayıt oluşturma işlemini logla"""
    log_audit(
        islem_tipi='create',
        tablo_adi=tablo_adi,
        kayit_id=kayit_id,
        yeni_deger=yeni_deger,
        aciklama=aciklama
    )


def audit_update(tablo_adi, kayit_id, eski_deger, yeni_deger, aciklama=None):
    """Kayıt güncelleme işlemini logla"""
    log_audit(
        islem_tipi='update',
        tablo_adi=tablo_adi,
        kayit_id=kayit_id,
        eski_deger=eski_deger,
        yeni_deger=yeni_deger,
        aciklama=aciklama
    )


def audit_delete(tablo_adi, kayit_id, eski_deger, aciklama=None):
    """Kayıt silme işlemini logla"""
    log_audit(
        islem_tipi='delete',
        tablo_adi=tablo_adi,
        kayit_id=kayit_id,
        eski_deger=eski_deger,
        aciklama=aciklama
    )


def audit_view(tablo_adi, kayit_id=None, aciklama=None):
    """Görüntüleme işlemini logla (hassas veriler için)"""
    log_audit(
        islem_tipi='view',
        tablo_adi=tablo_adi,
        kayit_id=kayit_id,
        aciklama=aciklama
    )


def audit_export(tablo_adi, aciklama=None):
    """Export işlemini logla"""
    log_audit(
        islem_tipi='export',
        tablo_adi=tablo_adi,
        aciklama=aciklama
    )


def audit_import(tablo_adi, aciklama=None):
    """Import işlemini logla"""
    log_audit(
        islem_tipi='import',
        tablo_adi=tablo_adi,
        aciklama=aciklama
    )


def log_fiyat_degisiklik(
    urun_id: int,
    eski_fiyat,
    yeni_fiyat,
    degisiklik_tipi: str,
    sebep: str = None,
    kullanici_id: int = None
):
    """
    Fiyat değişikliklerini hem UrunFiyatGecmisi hem de AuditLog'a kaydet
    
    Bu fonksiyon Requirements 16.1, 16.2, 16.3 ve 19.5'i karşılar:
    - Tüm fiyat değişikliklerini UrunFiyatGecmisi tablosuna kaydeder
    - Tüm fiyat değişikliklerini AuditLog tablosuna kaydeder
    - Değişiklik tipini, sebebini ve yapan kullanıcıyı kaydeder
    - Eski ve yeni fiyat bilgilerini saklar
    
    Args:
        urun_id: Ürün ID
        eski_fiyat: Eski fiyat (Decimal veya None)
        yeni_fiyat: Yeni fiyat (Decimal)
        degisiklik_tipi: 'alis_fiyati', 'satis_fiyati', 'kampanya'
        sebep: Değişiklik sebebi (opsiyonel)
        kullanici_id: İşlemi yapan kullanıcı ID (opsiyonel, session'dan alınır)
    
    Returns:
        tuple: (UrunFiyatGecmisi instance, AuditLog instance)
    
    Raises:
        ValueError: Geçersiz parametreler için
        Exception: Veritabanı hataları için
    """
    from models import UrunFiyatGecmisi, FiyatDegisiklikTipi, Kullanici, Urun
    from decimal import Decimal
    
    try:
        # Validasyon
        if not urun_id:
            raise ValueError("Ürün ID zorunludur")
        
        if not yeni_fiyat:
            raise ValueError("Yeni fiyat zorunludur")
        
        if degisiklik_tipi not in ['alis_fiyati', 'satis_fiyati', 'kampanya']:
            raise ValueError(f"Geçersiz değişiklik tipi: {degisiklik_tipi}")
        
        # Kullanıcı bilgilerini al
        if kullanici_id is None:
            kullanici_id, kullanici_adi, kullanici_rol = get_user_info()
        else:
            kullanici = Kullanici.query.get(kullanici_id)
            if kullanici:
                kullanici_adi = kullanici.kullanici_adi
                kullanici_rol = kullanici.rol
            else:
                kullanici_adi = 'Bilinmeyen'
                kullanici_rol = 'bilinmeyen'
        
        # Ürün bilgisini al
        urun = Urun.query.get(urun_id)
        if not urun:
            raise ValueError(f"Ürün {urun_id} bulunamadı")
        
        # Fiyatları Decimal'e çevir
        if eski_fiyat is not None and not isinstance(eski_fiyat, Decimal):
            eski_fiyat = Decimal(str(eski_fiyat))
        
        if not isinstance(yeni_fiyat, Decimal):
            yeni_fiyat = Decimal(str(yeni_fiyat))
        
        # 1. UrunFiyatGecmisi kaydı oluştur
        # Enum instance oluştur - value kullan (küçük harf)
        if isinstance(degisiklik_tipi, str):
            degisiklik_tipi_value = degisiklik_tipi
        else:
            degisiklik_tipi_value = degisiklik_tipi.value if hasattr(degisiklik_tipi, 'value') else str(degisiklik_tipi)
        
        fiyat_gecmisi = UrunFiyatGecmisi(
            urun_id=urun_id,
            eski_fiyat=eski_fiyat,
            yeni_fiyat=yeni_fiyat,
            degisiklik_tipi=degisiklik_tipi_value,  # String value kullan
            degisiklik_sebebi=sebep,
            olusturan_id=kullanici_id
        )
        
        db.session.add(fiyat_gecmisi)
        
        # ✅ URUNLER TABLOSUNU GUNCELLE
        if degisiklik_tipi_value == 'alis_fiyati':
            urun.alis_fiyati = yeni_fiyat
        
        # 2. AuditLog kaydı oluştur
        eski_deger_dict = {
            'urun_id': urun_id,
            'urun_adi': urun.urun_adi,
            'fiyat': float(eski_fiyat) if eski_fiyat else None,
            'degisiklik_tipi': degisiklik_tipi
        }
        
        yeni_deger_dict = {
            'urun_id': urun_id,
            'urun_adi': urun.urun_adi,
            'fiyat': float(yeni_fiyat),
            'degisiklik_tipi': degisiklik_tipi
        }
        
        # Değişiklik özetini oluştur
        if eski_fiyat:
            degisiklik_ozeti = f"{urun.urun_adi} - {degisiklik_tipi}: ₺{eski_fiyat} → ₺{yeni_fiyat}"
            if sebep:
                degisiklik_ozeti += f" (Sebep: {sebep})"
        else:
            degisiklik_ozeti = f"{urun.urun_adi} - {degisiklik_tipi}: İlk fiyat ₺{yeni_fiyat}"
            if sebep:
                degisiklik_ozeti += f" (Sebep: {sebep})"
        
        # İstemci bilgilerini al
        client_info = get_client_info()
        
        audit_log = AuditLog(
            kullanici_id=kullanici_id,
            kullanici_adi=kullanici_adi,
            kullanici_rol=kullanici_rol,
            islem_tipi='update',
            tablo_adi='urun_fiyat',
            kayit_id=urun_id,
            eski_deger=json.dumps(eski_deger_dict, ensure_ascii=False),
            yeni_deger=json.dumps(yeni_deger_dict, ensure_ascii=False),
            degisiklik_ozeti=degisiklik_ozeti,
            http_method=client_info['method'],
            url=client_info['url'],
            endpoint=client_info['endpoint'],
            ip_adresi=client_info['ip'],
            user_agent=client_info['user_agent'],
            aciklama=sebep,
            basarili=True
        )
        
        db.session.add(audit_log)
        
        # Commit işlemi
        db.session.commit()
        
        logger.info(f"✅ Fiyat değişikliği kaydedildi: Ürün {urun_id} - {degisiklik_tipi}")
        
        return (fiyat_gecmisi, audit_log)
        
    except ValueError as ve:
        db.session.rollback()
        logger.error(f"❌ Fiyat değişikliği validasyon hatası: {str(ve)}")
        raise ve
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Fiyat değişikliği kaydetme hatası: {str(e)}")
        raise Exception(f"Fiyat değişikliği kaydetme hatası: {str(e)}")
