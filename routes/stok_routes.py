"""
Stok Yönetimi API Route'ları
Stok durumu, kritik stoklar, sayım ve raporlama
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, date
from decimal import Decimal
from models import db
from utils.fiyatlandirma_servisler import StokYonetimServisi
from utils.decorators import login_required, role_required
from utils.helpers import log_islem

# Blueprint tanımla
stok_bp = Blueprint('stok', __name__, url_prefix='/api/v1/stok')


# ============================================
# STOK DURUMU API'LERİ
# ============================================

@stok_bp.route('/durum/<int:urun_id>', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'depo_sorumlusu', 'kat_sorumlusu'])
def stok_durumu(urun_id):
    """
    Belirli bir ürünün stok durumunu getir
    
    Query Parameters:
        - otel_id: Otel ID (required)
    
    Returns:
        200: Stok durumu bilgileri
        400: Geçersiz parametreler
        500: Sunucu hatası
    """
    try:
        # Otel ID kontrolü
        otel_id = request.args.get('otel_id', type=int)
        
        if not otel_id:
            return jsonify({
                'success': False,
                'error': 'otel_id parametresi zorunludur'
            }), 400
        
        # Stok durumunu getir
        stok_listesi = StokYonetimServisi.stok_durumu_getir(
            otel_id=otel_id,
            urun_id=urun_id
        )
        
        if not stok_listesi:
            return jsonify({
                'success': False,
                'error': 'Stok kaydı bulunamadı'
            }), 404
        
        # Log kaydı
        log_islem('goruntuleme', 'urun_stok', {
            'urun_id': urun_id,
            'otel_id': otel_id
        })
        
        return jsonify({
            'success': True,
            'stok': stok_listesi[0] if stok_listesi else None
        }), 200
        
    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Stok durumu getirme hatası: {str(e)}'
        }), 500


@stok_bp.route('/durum', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'depo_sorumlusu', 'kat_sorumlusu'])
def tum_stok_durumu():
    """
    Oteldeki tüm ürünlerin stok durumunu getir
    
    Query Parameters:
        - otel_id: Otel ID (required)
    
    Returns:
        200: Stok durumu listesi
        400: Geçersiz parametreler
        500: Sunucu hatası
    """
    try:
        # Otel ID kontrolü
        otel_id = request.args.get('otel_id', type=int)
        
        if not otel_id:
            return jsonify({
                'success': False,
                'error': 'otel_id parametresi zorunludur'
            }), 400
        
        # Tüm stokları getir
        stok_listesi = StokYonetimServisi.stok_durumu_getir(otel_id=otel_id)
        
        # Log kaydı
        log_islem('goruntuleme', 'urun_stok', {
            'otel_id': otel_id,
            'toplam_urun': len(stok_listesi)
        })
        
        return jsonify({
            'success': True,
            'otel_id': otel_id,
            'toplam_urun': len(stok_listesi),
            'stoklar': stok_listesi
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Stok durumu getirme hatası: {str(e)}'
        }), 500


@stok_bp.route('/kritik', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'depo_sorumlusu'])
def kritik_stoklar():
    """
    Kritik seviyedeki stokları getir
    
    Query Parameters:
        - otel_id: Otel ID (required)
    
    Returns:
        200: Kritik stok listesi
        400: Geçersiz parametreler
        500: Sunucu hatası
    """
    try:
        # Otel ID kontrolü
        otel_id = request.args.get('otel_id', type=int)
        
        if not otel_id:
            return jsonify({
                'success': False,
                'error': 'otel_id parametresi zorunludur'
            }), 400
        
        # Kritik stokları getir
        kritik_stok_listesi = StokYonetimServisi.kritik_stoklar_getir(otel_id)
        
        # Log kaydı
        log_islem('goruntuleme', 'kritik_stoklar', {
            'otel_id': otel_id,
            'kritik_stok_sayisi': len(kritik_stok_listesi)
        })
        
        return jsonify({
            'success': True,
            'otel_id': otel_id,
            'kritik_stok_sayisi': len(kritik_stok_listesi),
            'kritik_stoklar': kritik_stok_listesi
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Kritik stoklar getirme hatası: {str(e)}'
        }), 500


@stok_bp.route('/sayim', methods=['POST'])
@login_required
@role_required(['admin', 'sistem_yoneticisi', 'depo_sorumlusu'])
def stok_sayimi():
    """
    Stok sayımı yap ve farkları kaydet
    
    Body:
        - otel_id: Otel ID (required)
        - sayim_verileri: [{'urun_id': int, 'sayilan_miktar': int}, ...] (required)
    
    Returns:
        200: Sayım başarılı
        400: Geçersiz parametreler
        403: Yetki hatası
        500: Sunucu hatası
    """
    try:
        data = request.get_json()
        
        # Validasyon
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body boş olamaz'
            }), 400
        
        otel_id = data.get('otel_id')
        sayim_verileri = data.get('sayim_verileri', [])
        
        if not otel_id:
            return jsonify({
                'success': False,
                'error': 'otel_id zorunludur'
            }), 400
        
        if not sayim_verileri or not isinstance(sayim_verileri, list):
            return jsonify({
                'success': False,
                'error': 'sayim_verileri listesi zorunludur'
            }), 400
        
        # Her bir sayım verisini kontrol et
        for veri in sayim_verileri:
            if 'urun_id' not in veri or 'sayilan_miktar' not in veri:
                return jsonify({
                    'success': False,
                    'error': 'Her sayım verisi urun_id ve sayilan_miktar içermelidir'
                }), 400
            
            if not isinstance(veri['sayilan_miktar'], int) or veri['sayilan_miktar'] < 0:
                return jsonify({
                    'success': False,
                    'error': 'sayilan_miktar pozitif bir tam sayı olmalıdır'
                }), 400
        
        # Stok sayımı yap
        sonuc = StokYonetimServisi.stok_sayim_yap(
            otel_id=otel_id,
            sayim_verileri=sayim_verileri,
            kullanici_id=request.current_user.id
        )
        
        # Log kaydı
        log_islem('guncelleme', 'stok_sayim', {
            'otel_id': otel_id,
            'toplam_urun': sonuc['toplam_urun'],
            'farkli_urun_sayisi': sonuc['farkli_urun_sayisi']
        })
        
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
            'error': f'Stok sayımı hatası: {str(e)}'
        }), 500


@stok_bp.route('/devir-raporu', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'depo_sorumlusu'])
def stok_devir_raporu():
    """
    Stok devir hızı raporu
    
    Query Parameters:
        - otel_id: Otel ID (required)
        - baslangic: Başlangıç tarihi YYYY-MM-DD (required)
        - bitis: Bitiş tarihi YYYY-MM-DD (required)
    
    Returns:
        200: Stok devir raporu
        400: Geçersiz parametreler
        500: Sunucu hatası
    """
    try:
        # Parametreleri al
        otel_id = request.args.get('otel_id', type=int)
        baslangic_str = request.args.get('baslangic')
        bitis_str = request.args.get('bitis')
        
        # Validasyon
        if not otel_id:
            return jsonify({
                'success': False,
                'error': 'otel_id parametresi zorunludur'
            }), 400
        
        if not baslangic_str or not bitis_str:
            return jsonify({
                'success': False,
                'error': 'baslangic ve bitis tarihleri zorunludur'
            }), 400
        
        # Tarihleri parse et
        try:
            baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date()
            bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Tarih formatı YYYY-MM-DD olmalıdır'
            }), 400
        
        if baslangic > bitis:
            return jsonify({
                'success': False,
                'error': 'Başlangıç tarihi bitiş tarihinden sonra olamaz'
            }), 400
        
        # Stok devir raporu
        rapor = StokYonetimServisi.stok_devir_raporu(
            otel_id=otel_id,
            baslangic=baslangic,
            bitis=bitis
        )
        
        # Log kaydı
        log_islem('goruntuleme', 'stok_devir_raporu', {
            'otel_id': otel_id,
            'baslangic': baslangic_str,
            'bitis': bitis_str
        })
        
        return jsonify({
            'success': True,
            'otel_id': otel_id,
            'baslangic': baslangic_str,
            'bitis': bitis_str,
            'toplam_urun': len(rapor),
            'rapor': rapor
        }), 200
        
    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Stok devir raporu hatası: {str(e)}'
        }), 500


@stok_bp.route('/deger-raporu', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'depo_sorumlusu'])
def stok_deger_raporu():
    """
    Stok değer raporu
    
    Query Parameters:
        - otel_id: Otel ID (required)
    
    Returns:
        200: Stok değer raporu
        400: Geçersiz parametreler
        500: Sunucu hatası
    """
    try:
        # Otel ID kontrolü
        otel_id = request.args.get('otel_id', type=int)
        
        if not otel_id:
            return jsonify({
                'success': False,
                'error': 'otel_id parametresi zorunludur'
            }), 400
        
        # Stok değer raporu
        rapor = StokYonetimServisi.stok_deger_raporu(otel_id)
        
        # Log kaydı
        log_islem('goruntuleme', 'stok_deger_raporu', {
            'otel_id': otel_id
        })
        
        return jsonify({
            'success': True,
            **rapor
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Stok değer raporu hatası: {str(e)}'
        }), 500


# ============================================
# STOK GÜNCELLEME (Ek Endpoint)
# ============================================

@stok_bp.route('/guncelle', methods=['POST'])
@login_required
@role_required(['admin', 'sistem_yoneticisi', 'depo_sorumlusu'])
def stok_guncelle():
    """
    Manuel stok güncelleme
    
    Body:
        - otel_id: Otel ID (required)
        - urun_id: Ürün ID (required)
        - miktar: Miktar (pozitif veya negatif) (required)
        - islem_tipi: 'giris', 'cikis', 'devir', 'fire' (required)
        - aciklama: Açıklama (opsiyonel)
    
    Returns:
        200: Güncelleme başarılı
        400: Geçersiz parametreler
        403: Yetki hatası
        500: Sunucu hatası
    """
    try:
        data = request.get_json()
        
        # Validasyon
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body boş olamaz'
            }), 400
        
        otel_id = data.get('otel_id')
        urun_id = data.get('urun_id')
        miktar = data.get('miktar')
        islem_tipi = data.get('islem_tipi')
        aciklama = data.get('aciklama')
        
        # Zorunlu alan kontrolü
        if not all([otel_id, urun_id, miktar is not None, islem_tipi]):
            return jsonify({
                'success': False,
                'error': 'otel_id, urun_id, miktar ve islem_tipi zorunludur'
            }), 400
        
        # İşlem tipi kontrolü
        gecerli_islem_tipleri = ['giris', 'cikis', 'devir', 'fire']
        if islem_tipi not in gecerli_islem_tipleri:
            return jsonify({
                'success': False,
                'error': f'islem_tipi şunlardan biri olmalıdır: {", ".join(gecerli_islem_tipleri)}'
            }), 400
        
        # Miktar kontrolü
        if not isinstance(miktar, (int, float)):
            return jsonify({
                'success': False,
                'error': 'miktar sayısal bir değer olmalıdır'
            }), 400
        
        # Stok güncelle
        sonuc = StokYonetimServisi.stok_guncelle(
            otel_id=otel_id,
            urun_id=urun_id,
            miktar=int(miktar),
            islem_tipi=islem_tipi,
            kullanici_id=request.current_user.id,
            aciklama=aciklama
        )
        
        # Log kaydı
        log_islem('guncelleme', 'stok_guncelleme', {
            'urun_id': urun_id,
            'otel_id': otel_id,
            'islem_tipi': islem_tipi,
            'miktar': miktar
        })
        
        return jsonify(sonuc), 200
        
    except ValueError as ve:
        return jsonify({
            'success': False,
            'error': str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Stok güncelleme hatası: {str(e)}'
        }), 500


# ============================================
# HATA YÖNETİMİ
# ============================================

@stok_bp.errorhandler(404)
def not_found(error):
    """404 hatası"""
    return jsonify({
        'success': False,
        'error': 'Endpoint bulunamadı'
    }), 404


@stok_bp.errorhandler(405)
def method_not_allowed(error):
    """405 hatası"""
    return jsonify({
        'success': False,
        'error': 'HTTP metodu desteklenmiyor'
    }), 405


@stok_bp.errorhandler(500)
def internal_error(error):
    """500 hatası"""
    return jsonify({
        'success': False,
        'error': 'Sunucu hatası'
    }), 500
