"""
Fiyatlandırma ve Kampanya Yönetimi API Route'ları
"""

from flask import Blueprint, request, jsonify
from functools import wraps
from datetime import datetime, date
from decimal import Decimal
from models import db, Kullanici
from utils.fiyatlandirma_servisler import (
    FiyatYonetimServisi,
    KampanyaServisi,
    BedelsizServisi
)
from utils.decorators import login_required, role_required
from utils.audit_logger import get_audit_logger

# Audit logger instance
audit_logger = get_audit_logger()

def log_action(kullanici_id, islem_tipi, tablo_adi, kayit_id, aciklama=None, **kwargs):
    """Audit log wrapper fonksiyonu"""
    try:
        audit_logger.log_event(
            event_type=islem_tipi,
            user_id=kullanici_id,
            table_name=tablo_adi,
            record_id=kayit_id,
            description=aciklama,
            **kwargs
        )
    except Exception as e:
        logger.warning(f"Audit log hatası: {e}")
from utils.cache_manager import FiyatCache, CacheStats
import logging

logger = logging.getLogger(__name__)

# Blueprint tanımla
fiyatlandirma_bp = Blueprint('fiyatlandirma', __name__, url_prefix='/api/v1/fiyat')


# ============================================
# TEMEL FİYAT API'LERİ
# ============================================

@fiyatlandirma_bp.route('/urun/<int:urun_id>', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def urun_fiyat_bilgileri(urun_id):
    """
    Ürün fiyat bilgilerini getir
    
    Query Parameters:
        - oda_tipi: Oda tipi (opsiyonel)
        - tarih: Tarih (YYYY-MM-DD, opsiyonel)
    """
    try:
        oda_tipi = request.args.get('oda_tipi', 'Standard')
        tarih_str = request.args.get('tarih')
        
        # Tarih parse
        if tarih_str:
            tarih = datetime.strptime(tarih_str, '%Y-%m-%d')
        else:
            tarih = None
        
        # Alış fiyatı
        alis_fiyati = FiyatYonetimServisi.guncel_alis_fiyati_getir(urun_id)
        
        # Satış fiyatı
        satis_fiyati = FiyatYonetimServisi.oda_tipi_fiyati_getir(
            urun_id, oda_tipi, tarih
        )
        
        # En uygun tedarikçi
        tedarikci = FiyatYonetimServisi.en_uygun_tedarikci_bul(urun_id)
        
        # Aktif kampanyalar
        kampanyalar = KampanyaServisi.aktif_kampanyalar_getir(urun_id, tarih)
        
        log_action(
            kullanici_id=request.current_user.id,
            islem_tipi='view',
            tablo_adi='urun_fiyat',
            kayit_id=urun_id,
            aciklama=f"Ürün {urun_id} fiyat bilgileri görüntülendi"
        )
        
        return jsonify({
            'success': True,
            'urun_id': urun_id,
            'alis_fiyati': float(alis_fiyati) if alis_fiyati else None,
            'satis_fiyati': float(satis_fiyati) if satis_fiyati else None,
            'oda_tipi': oda_tipi,
            'tedarikci': tedarikci,
            'aktif_kampanyalar': kampanyalar
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/urun/<int:urun_id>/guncelle', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def fiyat_guncelle(urun_id):
    """
    Ürün fiyatını güncelle
    
    Body:
        - yeni_fiyat: Yeni fiyat (required)
        - degisiklik_tipi: 'alis_fiyati' veya 'satis_fiyati' (required)
        - sebep: Değişiklik sebebi (opsiyonel)
    """
    try:
        data = request.get_json()
        
        # Validasyon
        if not data.get('yeni_fiyat'):
            return jsonify({
                'success': False,
                'error': 'Yeni fiyat zorunludur'
            }), 400
        
        if not data.get('degisiklik_tipi'):
            return jsonify({
                'success': False,
                'error': 'Değişiklik tipi zorunludur'
            }), 400
        
        yeni_fiyat = Decimal(str(data['yeni_fiyat']))
        degisiklik_tipi = data['degisiklik_tipi']
        sebep = data.get('sebep')
        
        # Fiyat güncelle
        FiyatYonetimServisi.fiyat_guncelle(
            urun_id=urun_id,
            yeni_fiyat=yeni_fiyat,
            degisiklik_tipi=degisiklik_tipi,
            kullanici_id=request.current_user.id,
            sebep=sebep
        )
        
        log_action(
            kullanici_id=request.current_user.id,
            islem_tipi='update',
            tablo_adi='urun_fiyat',
            kayit_id=urun_id,
            yeni_deger={'yeni_fiyat': float(yeni_fiyat), 'tip': degisiklik_tipi},
            aciklama=f"Ürün {urun_id} fiyatı güncellendi"
        )
        
        return jsonify({
            'success': True,
            'message': 'Fiyat başarıyla güncellendi',
            'urun_id': urun_id,
            'yeni_fiyat': float(yeni_fiyat),
            'degisiklik_tipi': degisiklik_tipi
        }), 200
        
    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/tedarikci/<int:tedarikci_id>', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'depo_sorumlusu'])
def tedarikci_fiyatlari(tedarikci_id):
    """
    Tedarikçi fiyatlarını getir
    
    Query Parameters:
        - aktif: Sadece aktif fiyatlar (true/false, varsayılan: true)
    """
    try:
        from models import UrunTedarikciFiyat, Urun
        
        aktif = request.args.get('aktif', 'true').lower() == 'true'
        
        query = UrunTedarikciFiyat.query.filter_by(tedarikci_id=tedarikci_id)
        
        if aktif:
            simdi = datetime.now()
            query = query.filter(
                UrunTedarikciFiyat.aktif == True,
                UrunTedarikciFiyat.baslangic_tarihi <= simdi
            )
        
        fiyatlar = query.all()
        
        sonuc = []
        for fiyat in fiyatlar:
            sonuc.append({
                'id': fiyat.id,
                'urun_id': fiyat.urun_id,
                'urun_adi': fiyat.urun.urun_adi if fiyat.urun else None,
                'alis_fiyati': float(fiyat.alis_fiyati),
                'minimum_miktar': fiyat.minimum_miktar,
                'baslangic_tarihi': fiyat.baslangic_tarihi.isoformat(),
                'bitis_tarihi': fiyat.bitis_tarihi.isoformat() if fiyat.bitis_tarihi else None,
                'aktif': fiyat.aktif
            })
        
        log_action(
            kullanici_id=request.current_user.id,
            islem_tipi='view',
            tablo_adi='tedarikci_fiyat',
            kayit_id=tedarikci_id,
            aciklama=f"Tedarikçi {tedarikci_id} fiyatları görüntülendi"
        )
        
        return jsonify({
            'success': True,
            'tedarikci_id': tedarikci_id,
            'fiyatlar': sonuc
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/dinamik-hesapla', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def dinamik_fiyat_hesapla():
    """
    Dinamik fiyat hesaplama
    
    Body:
        - urun_id: Ürün ID (required)
        - oda_id: Oda ID (required)
        - oda_tipi: Oda tipi (required)
        - miktar: Miktar (varsayılan: 1)
        - tarih: Tarih (YYYY-MM-DD, opsiyonel)
    """
    try:
        data = request.get_json()
        
        # Validasyon
        if not all(k in data for k in ['urun_id', 'oda_id', 'oda_tipi']):
            return jsonify({
                'success': False,
                'error': 'urun_id, oda_id ve oda_tipi zorunludur'
            }), 400
        
        urun_id = data['urun_id']
        oda_id = data['oda_id']
        oda_tipi = data['oda_tipi']
        miktar = data.get('miktar', 1)
        
        # Tarih parse
        tarih_str = data.get('tarih')
        if tarih_str:
            tarih = datetime.strptime(tarih_str, '%Y-%m-%d')
        else:
            tarih = None
        
        # Dinamik fiyat hesapla
        sonuc = FiyatYonetimServisi.dinamik_fiyat_hesapla(
            urun_id=urun_id,
            oda_id=oda_id,
            oda_tipi=oda_tipi,
            miktar=miktar,
            tarih=tarih
        )
        
        # Decimal'leri float'a çevir
        for key in ['alis_fiyati', 'satis_fiyati', 'kar_tutari', 'sezon_carpani']:
            if key in sonuc:
                sonuc[key] = float(sonuc[key])
        
        if 'detaylar' in sonuc:
            for key in sonuc['detaylar']:
                if isinstance(sonuc['detaylar'][key], Decimal):
                    sonuc['detaylar'][key] = float(sonuc['detaylar'][key])
        
        log_action(
            kullanici_id=request.current_user.id,
            islem_tipi='view',
            tablo_adi='dinamik_fiyat',
            kayit_id=urun_id,
            aciklama=f"Ürün {urun_id} için dinamik fiyat hesaplandı"
        )
        
        return jsonify({
            'success': True,
            **sonuc
        }), 200
        
    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# KAMPANYA API'LERİ
# ============================================

@fiyatlandirma_bp.route('/kampanya', methods=['POST'])
@login_required
@role_required(['admin', 'sistem_yoneticisi'])
def kampanya_olustur():
    """
    Yeni kampanya oluştur
    
    Body:
        - kampanya_adi: Kampanya adı (required)
        - baslangic_tarihi: Başlangıç tarihi (YYYY-MM-DD, required)
        - bitis_tarihi: Bitiş tarihi (YYYY-MM-DD, required)
        - urun_id: Ürün ID (opsiyonel)
        - indirim_tipi: 'yuzde' veya 'tutar' (required)
        - indirim_degeri: İndirim değeri (required)
        - min_siparis_miktari: Minimum sipariş miktarı (varsayılan: 1)
        - max_kullanim_sayisi: Maksimum kullanım sayısı (opsiyonel)
    """
    try:
        data = request.get_json()
        
        # Tarih parse
        data['baslangic_tarihi'] = datetime.strptime(data['baslangic_tarihi'], '%Y-%m-%d')
        data['bitis_tarihi'] = datetime.strptime(data['bitis_tarihi'], '%Y-%m-%d')
        data['indirim_degeri'] = Decimal(str(data['indirim_degeri']))
        
        # Kampanya oluştur
        sonuc = KampanyaServisi.kampanya_olustur(
            kampanya_data=data,
            kullanici_id=request.current_user.id
        )
        
        log_action(
            kullanici_id=request.current_user.id,
            islem_tipi='create',
            tablo_adi='kampanyalar',
            kayit_id=sonuc['kampanya_id'],
            yeni_deger=data,
            aciklama=f"Kampanya oluşturuldu: {data['kampanya_adi']}"
        )
        
        return jsonify(sonuc), 201
        
    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/kampanya/<int:kampanya_id>', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def kampanya_detay(kampanya_id):
    """Kampanya detaylarını getir"""
    try:
        from models import Kampanya
        
        kampanya = Kampanya.query.get(kampanya_id)
        
        if not kampanya:
            return jsonify({
                'success': False,
                'error': 'Kampanya bulunamadı'
            }), 404
        
        # İstatistikleri al
        istatistikler = KampanyaServisi.kampanya_istatistikleri(kampanya_id)
        
        return jsonify({
            'success': True,
            'kampanya': {
                'id': kampanya.id,
                'kampanya_adi': kampanya.kampanya_adi,
                'baslangic_tarihi': kampanya.baslangic_tarihi.isoformat(),
                'bitis_tarihi': kampanya.bitis_tarihi.isoformat(),
                'urun_id': kampanya.urun_id,
                'indirim_tipi': kampanya.indirim_tipi.value,
                'indirim_degeri': float(kampanya.indirim_degeri),
                'min_siparis_miktari': kampanya.min_siparis_miktari,
                'max_kullanim_sayisi': kampanya.max_kullanim_sayisi,
                'kullanilan_sayisi': kampanya.kullanilan_sayisi,
                'aktif': kampanya.aktif
            },
            'istatistikler': istatistikler
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/kampanya/<int:kampanya_id>', methods=['PUT'])
@login_required
@role_required(['admin', 'sistem_yoneticisi'])
def kampanya_guncelle(kampanya_id):
    """Kampanya güncelle"""
    try:
        from models import Kampanya
        
        data = request.get_json()
        kampanya = Kampanya.query.get(kampanya_id)
        
        if not kampanya:
            return jsonify({
                'success': False,
                'error': 'Kampanya bulunamadı'
            }), 404
        
        # Güncellenebilir alanlar
        if 'kampanya_adi' in data:
            kampanya.kampanya_adi = data['kampanya_adi']
        
        if 'aktif' in data:
            kampanya.aktif = data['aktif']
        
        if 'max_kullanim_sayisi' in data:
            kampanya.max_kullanim_sayisi = data['max_kullanim_sayisi']
        
        db.session.commit()
        
        log_action(
            kullanici_id=request.current_user.id,
            islem_tipi='update',
            tablo_adi='kampanyalar',
            kayit_id=kampanya_id,
            yeni_deger=data,
            aciklama=f"Kampanya {kampanya_id} güncellendi"
        )
        
        return jsonify({
            'success': True,
            'message': 'Kampanya başarıyla güncellendi'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/kampanya/<int:kampanya_id>', methods=['DELETE'])
@login_required
@role_required(['admin', 'sistem_yoneticisi'])
def kampanya_sil(kampanya_id):
    """Kampanya sil (soft delete)"""
    try:
        KampanyaServisi.kampanya_sil(
            kampanya_id=kampanya_id,
            kullanici_id=request.current_user.id
        )
        
        log_action(
            kullanici_id=request.current_user.id,
            islem_tipi='delete',
            tablo_adi='kampanyalar',
            kayit_id=kampanya_id,
            aciklama=f"Kampanya {kampanya_id} silindi"
        )
        
        return jsonify({
            'success': True,
            'message': 'Kampanya başarıyla silindi'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/kampanya/aktif', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def aktif_kampanyalar():
    """Aktif kampanyaları listele"""
    try:
        urun_id = request.args.get('urun_id', type=int)
        
        kampanyalar = KampanyaServisi.aktif_kampanyalar_getir(urun_id=urun_id)
        
        return jsonify({
            'success': True,
            'kampanyalar': kampanyalar
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



# ============================================
# FİYAT YÖNETİMİ UI DESTEK API'LERİ
# ============================================

@fiyatlandirma_bp.route('/guncel-fiyatlar', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def guncel_fiyatlar_listesi():
    """
    Güncel fiyatları listele (UI için)
    
    Query Parameters:
        - otel_id: Otel ID (opsiyonel)
    """
    try:
        from models import UrunTedarikciFiyat, Urun, Tedarikci, OdaTipiSatisFiyati
        from sqlalchemy import and_
        
        otel_id = request.args.get('otel_id', type=int)
        simdi = datetime.now()
        
        # Aktif alış fiyatlarını getir
        query = db.session.query(
            UrunTedarikciFiyat,
            Urun,
            Tedarikci
        ).join(
            Urun, UrunTedarikciFiyat.urun_id == Urun.id
        ).join(
            Tedarikci, UrunTedarikciFiyat.tedarikci_id == Tedarikci.id
        ).filter(
            and_(
                UrunTedarikciFiyat.aktif == True,
                UrunTedarikciFiyat.baslangic_tarihi <= simdi,
                Urun.aktif == True,
                Tedarikci.aktif == True
            )
        )
        
        # Bitiş tarihi kontrolü
        query = query.filter(
            db.or_(
                UrunTedarikciFiyat.bitis_tarihi == None,
                UrunTedarikciFiyat.bitis_tarihi >= simdi
            )
        )
        
        fiyatlar_data = query.all()
        
        sonuc = []
        for fiyat, urun, tedarikci in fiyatlar_data:
            # Satış fiyatını getir (Standard oda tipi için)
            satis_fiyati_obj = OdaTipiSatisFiyati.query.filter_by(
                urun_id=urun.id,
                oda_tipi='Standard',
                aktif=True
            ).filter(
                OdaTipiSatisFiyati.baslangic_tarihi <= simdi
            ).filter(
                db.or_(
                    OdaTipiSatisFiyati.bitis_tarihi == None,
                    OdaTipiSatisFiyati.bitis_tarihi >= simdi
                )
            ).first()
            
            satis_fiyati = satis_fiyati_obj.satis_fiyati if satis_fiyati_obj else fiyat.alis_fiyati * Decimal('1.5')
            
            sonuc.append({
                'id': fiyat.id,
                'urun_id': urun.id,
                'urun_adi': urun.urun_adi,
                'tedarikci_id': tedarikci.id,
                'tedarikci_adi': tedarikci.tedarikci_adi,
                'alis_fiyati': float(fiyat.alis_fiyati),
                'satis_fiyati': float(satis_fiyati),
                'baslangic_tarihi': fiyat.baslangic_tarihi.isoformat(),
                'bitis_tarihi': fiyat.bitis_tarihi.isoformat() if fiyat.bitis_tarihi else None
            })
        
        return jsonify({
            'success': True,
            'fiyatlar': sonuc
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/gecmis', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def fiyat_gecmisi():
    """
    Fiyat değişiklik geçmişini listele (UI için)
    
    Query Parameters:
        - urun_id: Ürün ID (opsiyonel)
        - limit: Kayıt sayısı limiti (varsayılan: 100)
    """
    try:
        from models import UrunFiyatGecmisi, Urun, Kullanici
        
        urun_id = request.args.get('urun_id', type=int)
        limit = request.args.get('limit', type=int, default=100)
        
        query = db.session.query(
            UrunFiyatGecmisi,
            Urun,
            Kullanici
        ).join(
            Urun, UrunFiyatGecmisi.urun_id == Urun.id
        ).join(
            Kullanici, UrunFiyatGecmisi.olusturan_id == Kullanici.id
        )
        
        if urun_id:
            query = query.filter(UrunFiyatGecmisi.urun_id == urun_id)
        
        gecmis_data = query.order_by(
            UrunFiyatGecmisi.degisiklik_tarihi.desc()
        ).limit(limit).all()
        
        sonuc = []
        for gecmis, urun, kullanici in gecmis_data:
            sonuc.append({
                'id': gecmis.id,
                'urun_id': urun.id,
                'urun_adi': urun.urun_adi,
                'eski_fiyat': float(gecmis.eski_fiyat) if gecmis.eski_fiyat else None,
                'yeni_fiyat': float(gecmis.yeni_fiyat),
                'degisiklik_tipi': gecmis.degisiklik_tipi.value,
                'degisiklik_tarihi': gecmis.degisiklik_tarihi.isoformat(),
                'degisiklik_sebebi': gecmis.degisiklik_sebebi,
                'olusturan_id': kullanici.id,
                'olusturan_adi': f"{kullanici.ad} {kullanici.soyad}"
            })
        
        return jsonify({
            'success': True,
            'gecmis': sonuc
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



# ============================================================================
# BEDELSİZ LİMİT YÖNETİMİ API'LERİ
# ============================================================================

@fiyatlandirma_bp.route('/bedelsiz', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def bedelsiz_limit_tanimla():
    """
    Yeni bedelsiz limit tanımla
    
    Request Body:
        - oda_id: Oda ID (zorunlu)
        - urun_id: Ürün ID (zorunlu)
        - max_miktar: Maksimum miktar (zorunlu)
        - limit_tipi: Limit tipi (misafir, kampanya, personel) (zorunlu)
        - kampanya_id: Kampanya ID (opsiyonel, kampanya tipi için)
        - baslangic_tarihi: Başlangıç tarihi (zorunlu)
        - bitis_tarihi: Bitiş tarihi (opsiyonel)
        - aktif: Aktif durumu (varsayılan: True)
    """
    try:
        data = request.get_json()
        
        # Validasyon
        required_fields = ['oda_id', 'urun_id', 'max_miktar', 'limit_tipi', 'baslangic_tarihi']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'{field} zorunludur'
                }), 400
        
        # Limit tanımla
        sonuc = BedelsizServisi.limit_tanimla(
            oda_id=data['oda_id'],
            urun_id=data['urun_id'],
            max_miktar=data['max_miktar'],
            limit_tipi=data['limit_tipi'],
            kampanya_id=data.get('kampanya_id'),
            baslangic_tarihi=data['baslangic_tarihi'],
            bitis_tarihi=data.get('bitis_tarihi'),
            aktif=data.get('aktif', True)
        )
        
        if sonuc['success']:
            return jsonify(sonuc), 201
        else:
            return jsonify(sonuc), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/bedelsiz/<int:limit_id>', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def bedelsiz_limit_detay(limit_id):
    """Bedelsiz limit detayını getir"""
    try:
        from models import BedelsizLimit, Oda, Urun, Kampanya
        
        limit = db.session.query(
            BedelsizLimit,
            Oda,
            Urun
        ).join(
            Oda, BedelsizLimit.oda_id == Oda.id
        ).join(
            Urun, BedelsizLimit.urun_id == Urun.id
        ).filter(
            BedelsizLimit.id == limit_id
        ).first()
        
        if not limit:
            return jsonify({
                'success': False,
                'message': 'Limit bulunamadı'
            }), 404
        
        limit_obj, oda, urun = limit
        
        kampanya_adi = None
        if limit_obj.kampanya_id:
            kampanya = Kampanya.query.get(limit_obj.kampanya_id)
            kampanya_adi = kampanya.kampanya_adi if kampanya else None
        
        return jsonify({
            'success': True,
            'limit': {
                'id': limit_obj.id,
                'oda_id': oda.id,
                'oda_no': oda.oda_no,
                'urun_id': urun.id,
                'urun_adi': urun.urun_adi,
                'max_miktar': limit_obj.max_miktar,
                'kullanilan_miktar': limit_obj.kullanilan_miktar,
                'limit_tipi': limit_obj.limit_tipi.value,
                'kampanya_id': limit_obj.kampanya_id,
                'kampanya_adi': kampanya_adi,
                'baslangic_tarihi': limit_obj.baslangic_tarihi.isoformat(),
                'bitis_tarihi': limit_obj.bitis_tarihi.isoformat() if limit_obj.bitis_tarihi else None,
                'aktif': limit_obj.aktif
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/bedelsiz/<int:limit_id>', methods=['PUT'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def bedelsiz_limit_guncelle(limit_id):
    """Bedelsiz limit güncelle"""
    try:
        from models import BedelsizLimit
        
        data = request.get_json()
        limit = BedelsizLimit.query.get(limit_id)
        
        if not limit:
            return jsonify({
                'success': False,
                'message': 'Limit bulunamadı'
            }), 404
        
        # Güncellenebilir alanlar
        if 'max_miktar' in data:
            limit.max_miktar = data['max_miktar']
        if 'limit_tipi' in data:
            limit.limit_tipi = data['limit_tipi']
        if 'kampanya_id' in data:
            limit.kampanya_id = data['kampanya_id']
        if 'baslangic_tarihi' in data:
            limit.baslangic_tarihi = datetime.fromisoformat(data['baslangic_tarihi'].replace('Z', '+00:00'))
        if 'bitis_tarihi' in data:
            if data['bitis_tarihi']:
                limit.bitis_tarihi = datetime.fromisoformat(data['bitis_tarihi'].replace('Z', '+00:00'))
            else:
                limit.bitis_tarihi = None
        if 'aktif' in data:
            limit.aktif = data['aktif']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Limit başarıyla güncellendi'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/bedelsiz/<int:limit_id>', methods=['DELETE'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def bedelsiz_limit_sil(limit_id):
    """Bedelsiz limit sil"""
    try:
        from models import BedelsizLimit
        
        limit = BedelsizLimit.query.get(limit_id)
        
        if not limit:
            return jsonify({
                'success': False,
                'message': 'Limit bulunamadı'
            }), 404
        
        db.session.delete(limit)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Limit başarıyla silindi'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/bedelsiz/<int:limit_id>/aktif-yap', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def bedelsiz_limit_aktif_yap(limit_id):
    """Bedelsiz limiti aktif yap"""
    try:
        from models import BedelsizLimit
        
        limit = BedelsizLimit.query.get(limit_id)
        
        if not limit:
            return jsonify({
                'success': False,
                'message': 'Limit bulunamadı'
            }), 404
        
        limit.aktif = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Limit aktif edildi'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/bedelsiz/<int:limit_id>/pasif-yap', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def bedelsiz_limit_pasif_yap(limit_id):
    """Bedelsiz limiti pasif yap"""
    try:
        from models import BedelsizLimit
        
        limit = BedelsizLimit.query.get(limit_id)
        
        if not limit:
            return jsonify({
                'success': False,
                'message': 'Limit bulunamadı'
            }), 404
        
        limit.aktif = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Limit pasif edildi'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/bedelsiz/oda-limitler', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def bedelsiz_oda_limitler():
    """
    Oda bazlı bedelsiz limitleri listele
    
    Query Parameters:
        - otel_id: Otel ID (opsiyonel)
    """
    try:
        from models import BedelsizLimit, Oda, Urun, Otel
        
        otel_id = request.args.get('otel_id', type=int)
        
        query = db.session.query(
            BedelsizLimit,
            Oda,
            Urun,
            Otel
        ).join(
            Oda, BedelsizLimit.oda_id == Oda.id
        ).join(
            Urun, BedelsizLimit.urun_id == Urun.id
        ).join(
            Otel, Oda.otel_id == Otel.id
        ).filter(
            BedelsizLimit.aktif == True
        )
        
        if otel_id:
            query = query.filter(Oda.otel_id == otel_id)
        
        limitler_data = query.order_by(Oda.oda_no).all()
        
        sonuc = []
        for limit, oda, urun, otel in limitler_data:
            sonuc.append({
                'id': limit.id,
                'oda_id': oda.id,
                'oda_no': oda.oda_no,
                'otel_adi': otel.otel_adi,
                'urun_id': urun.id,
                'urun_adi': urun.urun_adi,
                'max_miktar': limit.max_miktar,
                'kullanilan_miktar': limit.kullanilan_miktar,
                'limit_tipi': limit.limit_tipi.value,
                'baslangic_tarihi': limit.baslangic_tarihi.isoformat(),
                'bitis_tarihi': limit.bitis_tarihi.isoformat() if limit.bitis_tarihi else None,
                'aktif': limit.aktif
            })
        
        return jsonify({
            'success': True,
            'limitler': sonuc
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/bedelsiz/tumu', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def bedelsiz_tum_limitler():
    """
    Tüm bedelsiz limitleri listele
    
    Query Parameters:
        - durum: Durum filtresi (aktif, pasif, dolmus)
        - tip: Limit tipi filtresi (misafir, kampanya, personel)
    """
    try:
        from models import BedelsizLimit, Oda, Urun, Otel
        
        durum = request.args.get('durum')
        tip = request.args.get('tip')
        
        query = db.session.query(
            BedelsizLimit,
            Oda,
            Urun,
            Otel
        ).join(
            Oda, BedelsizLimit.oda_id == Oda.id
        ).join(
            Urun, BedelsizLimit.urun_id == Urun.id
        ).join(
            Otel, Oda.otel_id == Otel.id
        )
        
        if durum == 'aktif':
            query = query.filter(BedelsizLimit.aktif == True)
            query = query.filter(BedelsizLimit.kullanilan_miktar < BedelsizLimit.max_miktar)
        elif durum == 'pasif':
            query = query.filter(BedelsizLimit.aktif == False)
        elif durum == 'dolmus':
            query = query.filter(BedelsizLimit.kullanilan_miktar >= BedelsizLimit.max_miktar)
        
        if tip:
            query = query.filter(BedelsizLimit.limit_tipi == tip)
        
        limitler_data = query.order_by(Oda.oda_no).all()
        
        sonuc = []
        for limit, oda, urun, otel in limitler_data:
            sonuc.append({
                'id': limit.id,
                'oda_id': oda.id,
                'oda_no': oda.oda_no,
                'otel_adi': otel.otel_adi,
                'urun_id': urun.id,
                'urun_adi': urun.urun_adi,
                'max_miktar': limit.max_miktar,
                'kullanilan_miktar': limit.kullanilan_miktar,
                'limit_tipi': limit.limit_tipi.value,
                'baslangic_tarihi': limit.baslangic_tarihi.isoformat(),
                'bitis_tarihi': limit.bitis_tarihi.isoformat() if limit.bitis_tarihi else None,
                'aktif': limit.aktif
            })
        
        return jsonify({
            'success': True,
            'limitler': sonuc
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/bedelsiz/istatistikler', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def bedelsiz_istatistikler():
    """Bedelsiz limit istatistikleri"""
    try:
        from models import BedelsizLimit
        from sqlalchemy import func
        
        # Aktif limit sayısı
        aktif_limit_sayisi = BedelsizLimit.query.filter_by(aktif=True).count()
        
        # Toplam kullanım
        toplam_kullanim = db.session.query(
            func.sum(BedelsizLimit.kullanilan_miktar)
        ).filter_by(aktif=True).scalar() or 0
        
        # Toplam limit
        toplam_limit = db.session.query(
            func.sum(BedelsizLimit.max_miktar)
        ).filter_by(aktif=True).scalar() or 1
        
        # Kullanım oranı
        kullanim_orani = (toplam_kullanim / toplam_limit * 100) if toplam_limit > 0 else 0
        
        # Dolmuş limit sayısı
        dolmus_limit_sayisi = BedelsizLimit.query.filter(
            BedelsizLimit.aktif == True,
            BedelsizLimit.kullanilan_miktar >= BedelsizLimit.max_miktar
        ).count()
        
        return jsonify({
            'success': True,
            'aktif_limit_sayisi': aktif_limit_sayisi,
            'toplam_kullanim': int(toplam_kullanim),
            'kullanim_orani': float(kullanim_orani),
            'dolmus_limit_sayisi': dolmus_limit_sayisi
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/bedelsiz/kullanim-takibi', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def bedelsiz_kullanim_takibi():
    """Bedelsiz limit kullanım takibi"""
    try:
        from models import BedelsizLimit, Oda, Urun
        
        # En çok kullanılan limitler
        en_cok_kullanilan = db.session.query(
            BedelsizLimit,
            Oda,
            Urun
        ).join(
            Oda, BedelsizLimit.oda_id == Oda.id
        ).join(
            Urun, BedelsizLimit.urun_id == Urun.id
        ).filter(
            BedelsizLimit.aktif == True
        ).order_by(
            BedelsizLimit.kullanilan_miktar.desc()
        ).limit(5).all()
        
        en_cok_kullanilan_list = []
        for limit, oda, urun in en_cok_kullanilan:
            kullanim_orani = (limit.kullanilan_miktar / limit.max_miktar * 100) if limit.max_miktar > 0 else 0
            en_cok_kullanilan_list.append({
                'oda_no': oda.oda_no,
                'urun_adi': urun.urun_adi,
                'kullanilan_miktar': limit.kullanilan_miktar,
                'max_miktar': limit.max_miktar,
                'kullanim_orani': round(kullanim_orani, 2)
            })
        
        # Dolmak üzere olan limitler (>80% kullanım)
        dolmak_uzere = db.session.query(
            BedelsizLimit,
            Oda,
            Urun
        ).join(
            Oda, BedelsizLimit.oda_id == Oda.id
        ).join(
            Urun, BedelsizLimit.urun_id == Urun.id
        ).filter(
            BedelsizLimit.aktif == True,
            BedelsizLimit.kullanilan_miktar >= BedelsizLimit.max_miktar * 0.8,
            BedelsizLimit.kullanilan_miktar < BedelsizLimit.max_miktar
        ).order_by(
            (BedelsizLimit.kullanilan_miktar / BedelsizLimit.max_miktar).desc()
        ).limit(5).all()
        
        dolmak_uzere_list = []
        for limit, oda, urun in dolmak_uzere:
            kalan_miktar = limit.max_miktar - limit.kullanilan_miktar
            dolmak_uzere_list.append({
                'oda_no': oda.oda_no,
                'urun_adi': urun.urun_adi,
                'kullanilan_miktar': limit.kullanilan_miktar,
                'max_miktar': limit.max_miktar,
                'kalan_miktar': kalan_miktar
            })
        
        return jsonify({
            'success': True,
            'en_cok_kullanilan': en_cok_kullanilan_list,
            'dolmak_uzere': dolmak_uzere_list
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# CACHE YÖNETİMİ API'LERİ
# ============================================

@fiyatlandirma_bp.route('/cache/stats', methods=['GET'])
@login_required
@role_required(['admin', 'sistem_yoneticisi'])
def cache_istatistikleri():
    """
    Cache performans istatistiklerini getir
    """
    try:
        stats = CacheStats.get_cache_info()
        
        log_action(
            kullanici_id=request.current_user.id,
            islem_tipi='view',
            tablo_adi='cache_stats',
            kayit_id=0,
            aciklama="Cache istatistikleri görüntülendi"
        )
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Cache stats hatası: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/cache/clear/urun/<int:urun_id>', methods=['POST'])
@login_required
@role_required(['admin', 'sistem_yoneticisi'])
def cache_urun_temizle(urun_id):
    """
    Belirli bir ürünün cache'ini temizle
    """
    try:
        count = FiyatCache.invalidate_urun_fiyat(urun_id)
        
        log_action(
            kullanici_id=request.current_user.id,
            islem_tipi='delete',
            tablo_adi='cache',
            kayit_id=urun_id,
            aciklama=f"Ürün {urun_id} cache'i temizlendi ({count} key)"
        )
        
        return jsonify({
            'success': True,
            'message': f'{count} cache key temizlendi',
            'urun_id': urun_id
        }), 200
        
    except Exception as e:
        logger.error(f"Cache temizleme hatası: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fiyatlandirma_bp.route('/cache/clear/all', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi'])
def cache_tum_temizle():
    """
    Tüm fiyat cache'ini temizle (Dikkatli kullan!)
    """
    try:
        count = FiyatCache.invalidate_all_fiyat()
        
        log_action(
            kullanici_id=request.current_user.id,
            islem_tipi='delete',
            tablo_adi='cache',
            kayit_id=0,
            aciklama=f"Tüm fiyat cache'i temizlendi ({count} key)"
        )
        
        return jsonify({
            'success': True,
            'message': f'Tüm fiyat cache temizlendi ({count} key)',
            'warning': 'Cache yeniden oluşturulacak, performans geçici düşebilir'
        }), 200
        
    except Exception as e:
        logger.error(f"Tüm cache temizleme hatası: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
