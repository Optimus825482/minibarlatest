"""
Karlılık Analizi ve ROI API Route'ları
"""

from flask import Blueprint, request, jsonify, render_template, session
from datetime import datetime, date, timedelta
from models import db, Otel
from utils.decorators import login_required, role_required
from utils.audit_logger import get_audit_logger
import logging

logger = logging.getLogger(__name__)


# ============================================
# MOCK SERVİSLER (Geçici - Gerçek servisler eklenecek)
# ============================================

class KarHesaplamaServisi:
    """Karlılık hesaplama servisi - Mock implementation"""
    
    @staticmethod
    def urun_karliligi_analizi(urun_id, baslangic=None, bitis=None):
        """Ürün karlılık analizi"""
        return {
            'urun_id': urun_id,
            'toplam_satis': 0,
            'toplam_maliyet': 0,
            'kar': 0,
            'kar_orani': 0
        }
    
    @staticmethod
    def oda_karliligi_analizi(oda_id, baslangic=None, bitis=None):
        """Oda karlılık analizi"""
        return {
            'oda_id': oda_id,
            'toplam_satis': 0,
            'toplam_maliyet': 0,
            'kar': 0,
            'kar_orani': 0
        }
    
    @staticmethod
    def donemsel_kar_analizi(otel_id, baslangic, bitis, donem_tipi='gunluk'):
        """Dönemsel kar analizi"""
        return {
            'donemler': [],
            'toplam_satis': 0,
            'toplam_maliyet': 0,
            'toplam_kar': 0,
            'ortalama_kar_orani': 0
        }
    
    @staticmethod
    def kar_trend_analizi(otel_id, baslangic, bitis):
        """Kar trend analizi"""
        return {
            'trend_data': [],
            'trend_yonu': 'sabit',
            'degisim_orani': 0
        }
    
    @staticmethod
    def urun_bazli_kar_analizi(otel_id, baslangic, bitis):
        """Ürün bazlı kar analizi"""
        return {
            'urunler': [],
            'en_karli_urun': None,
            'en_dusuk_karli_urun': None
        }


class MLEntegrasyonServisi:
    """ML entegrasyon servisi - Mock implementation"""
    
    @staticmethod
    def kar_tahmini(otel_id, gelecek_gun_sayisi=7):
        """Kar tahmini"""
        return {
            'tahminler': [],
            'guven_araligi': 0.95
        }

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

# Blueprint tanımla
karlilik_bp = Blueprint('karlilik', __name__, url_prefix='/api/v1/kar')


# ============================================
# DASHBOARD UI
# ============================================

@karlilik_bp.route('/dashboard', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def karlilik_dashboard():
    """Karlılık Dashboard UI"""
    try:
        # Otel listesi
        oteller = Otel.query.filter_by(aktif=True).all()
        
        return render_template(
            'admin/karlilik_dashboard.html',
            oteller=oteller
        )
    except Exception as e:
        return f"Hata: {str(e)}", 500


# ============================================
# KARLILIK HESAPLAMA API'LERİ
# ============================================

@karlilik_bp.route('/urun/<int:urun_id>', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'kat_sorumlusu'])
def urun_karliligi(urun_id):
    """
    Ürün karlılık bilgisi
    
    Query Parameters:
        - baslangic: Başlangıç tarihi (YYYY-MM-DD, opsiyonel)
        - bitis: Bitiş tarihi (YYYY-MM-DD, opsiyonel)
    """
    try:
        baslangic_str = request.args.get('baslangic')
        bitis_str = request.args.get('bitis')
        
        # Tarih parse
        baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date() if baslangic_str else None
        bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date() if bitis_str else None
        
        # Karlılık analizi
        sonuc = KarHesaplamaServisi.urun_karliligi_analizi(
            urun_id=urun_id,
            baslangic=baslangic,
            bitis=bitis
        )
        
        log_action(
            kullanici_id=session.get("kullanici_id"),
            islem_tipi='view',
            tablo_adi='urun_karlilik',
            kayit_id=urun_id,
            aciklama=f"Ürün {urun_id} karlılık analizi görüntülendi"
        )
        
        return jsonify({
            'success': True,
            **sonuc
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@karlilik_bp.route('/oda/<int:oda_id>', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'kat_sorumlusu'])
def oda_karliligi(oda_id):
    """
    Oda karlılık bilgisi
    
    Query Parameters:
        - baslangic: Başlangıç tarihi (YYYY-MM-DD, opsiyonel)
        - bitis: Bitiş tarihi (YYYY-MM-DD, opsiyonel)
    """
    try:
        baslangic_str = request.args.get('baslangic')
        bitis_str = request.args.get('bitis')
        
        # Tarih parse
        baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date() if baslangic_str else None
        bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date() if bitis_str else None
        
        # Karlılık analizi
        sonuc = KarHesaplamaServisi.oda_karliligi_analizi(
            oda_id=oda_id,
            baslangic=baslangic,
            bitis=bitis
        )
        
        log_action(
            kullanici_id=session.get("kullanici_id"),
            islem_tipi='view',
            tablo_adi='oda_karlilik',
            kayit_id=oda_id,
            aciklama=f"Oda {oda_id} karlılık analizi görüntülendi"
        )
        
        return jsonify({
            'success': True,
            **sonuc
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@karlilik_bp.route('/donemsel', methods=['GET'])
@login_required
@role_required(['admin', 'sistem_yoneticisi'])
def donemsel_kar():
    """
    Dönemsel kar raporu
    
    Query Parameters:
        - otel_id: Otel ID (required)
        - baslangic: Başlangıç tarihi (YYYY-MM-DD, required)
        - bitis: Bitiş tarihi (YYYY-MM-DD, required)
        - donem_tipi: 'gunluk', 'haftalik', 'aylik' (varsayılan: gunluk)
    """
    try:
        otel_id_str = request.args.get('otel_id', '')
        otel_id = int(otel_id_str) if otel_id_str else None
        baslangic_str = request.args.get('baslangic')
        bitis_str = request.args.get('bitis')
        donem_tipi = request.args.get('donem', 'gunluk')  # 'donem' parametresi kullanılıyor
        
        # Validasyon - otel_id opsiyonel (tüm oteller için)
        if not all([baslangic_str, bitis_str]):
            return jsonify({
                'success': False,
                'error': 'baslangic ve bitis zorunludur'
            }), 400
        
        # Tarih parse
        baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date()
        bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date()
        
        # Dönemsel analiz
        sonuc = KarHesaplamaServisi.donemsel_kar_analizi(
            otel_id=otel_id,
            baslangic=baslangic,
            bitis=bitis,
            donem_tipi=donem_tipi
        )
        
        log_action(
            kullanici_id=session.get("kullanici_id"),
            islem_tipi='view',
            tablo_adi='donemsel_kar',
            kayit_id=otel_id,
            aciklama=f"Otel {otel_id} dönemsel kar analizi görüntülendi"
        )
        
        return jsonify({
            'success': True,
            **sonuc
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@karlilik_bp.route('/hesapla', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'kat_sorumlusu'])
def kar_hesapla():
    """
    Gerçek zamanlı kar hesaplama
    
    Body:
        - islem_detay_ids: MinibarIslemDetay ID listesi (required)
    """
    try:
        data = request.get_json()
        
        if not data.get('islem_detay_ids'):
            return jsonify({
                'success': False,
                'error': 'islem_detay_ids zorunludur'
            }), 400
        
        islem_detay_ids = data['islem_detay_ids']
        
        # Kar hesapla
        sonuc = KarHesaplamaServisi.gercek_zamanli_kar_hesapla(islem_detay_ids)
        
        # Decimal'leri float'a çevir
        for key in ['toplam_gelir', 'toplam_maliyet', 'net_kar', 'bedelsiz_tuketim', 'kampanyali_tuketim']:
            if key in sonuc:
                sonuc[key] = float(sonuc[key])
        
        return jsonify({
            'success': True,
            **sonuc
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# ROI VE ANALİZ API'LERİ
# ============================================

@karlilik_bp.route('/roi/<int:urun_id>', methods=['GET'])
@login_required
@role_required(['admin', 'sistem_yoneticisi'])
def roi_hesapla(urun_id):
    """
    ROI hesaplama
    
    Query Parameters:
        - baslangic: Başlangıç tarihi (YYYY-MM-DD, required)
        - bitis: Bitiş tarihi (YYYY-MM-DD, required)
    """
    try:
        baslangic_str = request.args.get('baslangic')
        bitis_str = request.args.get('bitis')
        
        if not all([baslangic_str, bitis_str]):
            return jsonify({
                'success': False,
                'error': 'baslangic ve bitis zorunludur'
            }), 400
        
        # Tarih parse
        baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date()
        bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date()
        
        # ROI hesapla
        sonuc = KarHesaplamaServisi.roi_hesapla(
            urun_id=urun_id,
            baslangic=baslangic,
            bitis=bitis
        )
        
        log_action(
            kullanici_id=session.get("kullanici_id"),
            islem_tipi='view',
            tablo_adi='roi',
            kayit_id=urun_id,
            aciklama=f"Ürün {urun_id} ROI hesaplandı"
        )
        
        return jsonify({
            'success': True,
            **sonuc
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@karlilik_bp.route('/analitik', methods=['GET'])
@login_required
@role_required(['admin', 'sistem_yoneticisi'])
def karlilik_analitik():
    """
    Karlılık analitikleri
    
    Query Parameters:
        - otel_id: Otel ID (opsiyonel)
        - baslangic: Başlangıç tarihi (YYYY-MM-DD, opsiyonel)
        - bitis: Bitiş tarihi (YYYY-MM-DD, opsiyonel)
        - limit: Maksimum sonuç sayısı (varsayılan: 10)
    """
    try:
        otel_id = request.args.get('otel_id', type=int)
        baslangic_str = request.args.get('baslangic')
        bitis_str = request.args.get('bitis')
        limit = request.args.get('limit', 10, type=int)
        
        # Tarih parse
        baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date() if baslangic_str else None
        bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date() if bitis_str else None
        
        # En karlı ürünler
        en_karli_urunler = KarHesaplamaServisi.en_karlı_urunler(
            otel_id=otel_id,
            baslangic=baslangic,
            bitis=bitis,
            limit=limit
        )
        
        log_action(
            kullanici_id=session.get("kullanici_id"),
            islem_tipi='view',
            tablo_adi='karlilik_analitik',
            kayit_id=otel_id or 0,
            aciklama="Karlılık analitikleri görüntülendi"
        )
        
        return jsonify({
            'success': True,
            'en_karli_urunler': en_karli_urunler
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@karlilik_bp.route('/trend', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'kat_sorumlusu'])
def trend_analizi():
    """
    Trend analizi - Dashboard için kar trend verisi
    
    Query Parameters:
        - otel_id: Otel ID (opsiyonel, dashboard için)
        - urun_id: Ürün ID (opsiyonel, ürün bazlı analiz için)
        - baslangic: Başlangıç tarihi (YYYY-MM-DD)
        - bitis: Bitiş tarihi (YYYY-MM-DD)
        - donem: 'gunluk', 'haftalik', 'aylik' (varsayılan: gunluk)
    """
    try:
        # Dashboard için mi yoksa ürün bazlı mı?
        urun_id_str = request.args.get('urun_id', '')
        urun_id = int(urun_id_str) if urun_id_str else None
        
        if urun_id:
            # Ürün bazlı trend analizi (eski davranış)
            donem = request.args.get('donem', 'aylik')
            donem_sayisi = request.args.get('donem_sayisi', 6, type=int)
            
            sonuc = MLEntegrasyonServisi.trend_analizi(
                urun_id=urun_id,
                donem=donem,
                donem_sayisi=donem_sayisi
            )
            
            log_action(
                kullanici_id=session.get("kullanici_id"),
                islem_tipi='view',
                tablo_adi='trend_analiz',
                kayit_id=urun_id,
                aciklama=f"Ürün {urun_id} trend analizi görüntülendi"
            )
            
            return jsonify({
                'success': True,
                **sonuc
            }), 200
        else:
            # Dashboard için kar trend verisi
            from models import MinibarIslem, MinibarIslemDetay, Oda
            from sqlalchemy import func
            from datetime import timedelta
            
            otel_id_str = request.args.get('otel_id', '')
            otel_id = int(otel_id_str) if otel_id_str else None
            baslangic_str = request.args.get('baslangic')
            bitis_str = request.args.get('bitis')
            
            if not all([baslangic_str, bitis_str]):
                return jsonify({
                    'success': False,
                    'error': 'baslangic ve bitis zorunludur'
                }), 400
            
            # Tarih parse
            baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date()
            bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date()
            
            # Günlük trend verisi
            trend_data = []
            current_date = baslangic
            
            while current_date <= bitis:
                query = db.session.query(
                    func.sum(MinibarIslemDetay.satis_fiyati * MinibarIslemDetay.tuketim).label('toplam_gelir'),
                    func.sum(MinibarIslemDetay.alis_fiyati * MinibarIslemDetay.tuketim).label('toplam_maliyet'),
                    func.sum(MinibarIslemDetay.kar_tutari).label('net_kar')
                ).join(
                    MinibarIslem, MinibarIslem.id == MinibarIslemDetay.islem_id
                ).filter(
                    func.date(MinibarIslem.islem_tarihi) == current_date
                )
                
                if otel_id:
                    query = query.join(Oda, Oda.id == MinibarIslem.oda_id).filter(Oda.otel_id == otel_id)
                
                result = query.first()
                
                trend_data.append({
                    'tarih': current_date.isoformat(),
                    'toplam_gelir': float(result.toplam_gelir or 0),
                    'toplam_maliyet': float(result.toplam_maliyet or 0),
                    'net_kar': float(result.net_kar or 0)
                })
                
                current_date += timedelta(days=1)
            
            return jsonify({
                'success': True,
                'trend_data': trend_data
            }), 200
        
        # Trend analizi
        sonuc = MLEntegrasyonServisi.trend_analizi(
            urun_id=urun_id,
            donem=donem,
            donem_sayisi=donem_sayisi
        )
        
        log_action(
            kullanici_id=session.get("kullanici_id"),
            islem_tipi='view',
            tablo_adi='trend_analiz',
            kayit_id=urun_id,
            aciklama=f"Ürün {urun_id} trend analizi görüntülendi"
        )
        
        return jsonify({
            'success': True,
            **sonuc
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@karlilik_bp.route('/anomali/gelir', methods=['GET'])
@login_required
@role_required(['admin', 'sistem_yoneticisi'])
def gelir_anomali():
    """
    Gelir anomali tespiti
    
    Query Parameters:
        - otel_id: Otel ID (required)
        - baslangic: Başlangıç tarihi (YYYY-MM-DD, required)
        - bitis: Bitiş tarihi (YYYY-MM-DD, required)
        - esik_deger: Z-score eşik değeri (varsayılan: 2.0)
    """
    try:
        otel_id = request.args.get('otel_id', type=int)
        baslangic_str = request.args.get('baslangic')
        bitis_str = request.args.get('bitis')
        esik_deger = request.args.get('esik_deger', 2.0, type=float)
        
        if not all([otel_id, baslangic_str, bitis_str]):
            return jsonify({
                'success': False,
                'error': 'otel_id, baslangic ve bitis zorunludur'
            }), 400
        
        # Tarih parse
        baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date()
        bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date()
        
        # Anomali tespiti
        anomaliler = MLEntegrasyonServisi.gelir_anomali_tespit(
            otel_id=otel_id,
            baslangic=baslangic,
            bitis=bitis,
            esik_deger=esik_deger
        )
        
        log_action(
            kullanici_id=session.get("kullanici_id"),
            islem_tipi='view',
            tablo_adi='gelir_anomali',
            kayit_id=otel_id,
            aciklama=f"Otel {otel_id} gelir anomali tespiti yapıldı"
        )
        
        return jsonify({
            'success': True,
            'otel_id': otel_id,
            'anomali_sayisi': len(anomaliler),
            'anomaliler': anomaliler
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@karlilik_bp.route('/anomali/karlilik', methods=['GET'])
@login_required
@role_required(['admin', 'sistem_yoneticisi'])
def karlilik_anomali():
    """
    Karlılık anomali tespiti
    
    Query Parameters:
        - otel_id: Otel ID (required)
        - baslangic: Başlangıç tarihi (YYYY-MM-DD, required)
        - bitis: Bitiş tarihi (YYYY-MM-DD, required)
        - esik_deger: Z-score eşik değeri (varsayılan: 2.0)
    """
    try:
        otel_id = request.args.get('otel_id', type=int)
        baslangic_str = request.args.get('baslangic')
        bitis_str = request.args.get('bitis')
        esik_deger = request.args.get('esik_deger', 2.0, type=float)
        
        if not all([otel_id, baslangic_str, bitis_str]):
            return jsonify({
                'success': False,
                'error': 'otel_id, baslangic ve bitis zorunludur'
            }), 400
        
        # Tarih parse
        baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date()
        bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date()
        
        # Anomali tespiti
        anomaliler = MLEntegrasyonServisi.karlilik_anomali_tespit(
            otel_id=otel_id,
            baslangic=baslangic,
            bitis=bitis,
            esik_deger=esik_deger
        )
        
        log_action(
            kullanici_id=session.get("kullanici_id"),
            islem_tipi='view',
            tablo_adi='karlilik_anomali',
            kayit_id=otel_id,
            aciklama=f"Otel {otel_id} karlılık anomali tespiti yapıldı"
        )
        
        return jsonify({
            'success': True,
            'otel_id': otel_id,
            'anomali_sayisi': len(anomaliler),
            'anomaliler': anomaliler
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@karlilik_bp.route('/optimizasyon/fiyat', methods=['GET'])
@login_required
@role_required(['admin', 'sistem_yoneticisi'])
def fiyat_optimizasyon():
    """
    Fiyat optimizasyon önerisi
    
    Query Parameters:
        - urun_id: Ürün ID (required)
        - hedef_kar_marji: Hedef kar marjı % (varsayılan: 50)
    """
    try:
        urun_id = request.args.get('urun_id', type=int)
        hedef_kar_marji = request.args.get('hedef_kar_marji', 50.0, type=float)
        
        if not urun_id:
            return jsonify({
                'success': False,
                'error': 'urun_id zorunludur'
            }), 400
        
        # Optimizasyon önerisi
        sonuc = MLEntegrasyonServisi.fiyat_optimizasyon_onerisi(
            urun_id=urun_id,
            hedef_kar_marji=hedef_kar_marji
        )
        
        log_action(
            kullanici_id=session.get("kullanici_id"),
            islem_tipi='view',
            tablo_adi='fiyat_optimizasyon',
            kayit_id=urun_id,
            aciklama=f"Ürün {urun_id} fiyat optimizasyon önerisi alındı"
        )
        
        return jsonify({
            'success': True,
            **sonuc
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# DASHBOARD ÖZEL API'LER
# ============================================

@karlilik_bp.route('/trend-data', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def kar_trend_data():
    """
    Kar trend verisi (Dashboard için)
    
    Query Parameters:
        - otel_id: Otel ID (opsiyonel)
        - baslangic: Başlangıç tarihi (YYYY-MM-DD, required)
        - bitis: Bitiş tarihi (YYYY-MM-DD, required)
    """
    try:
        from models import MinibarIslem, MinibarIslemDetay
        from sqlalchemy import func
        from datetime import timedelta
        
        otel_id_str = request.args.get('otel_id', '')
        otel_id = int(otel_id_str) if otel_id_str else None
        baslangic_str = request.args.get('baslangic')
        bitis_str = request.args.get('bitis')
        
        if not all([baslangic_str, bitis_str]):
            return jsonify({
                'success': False,
                'error': 'baslangic ve bitis zorunludur'
            }), 400
        
        # Tarih parse
        baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date()
        bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date()
        
        # Günlük trend verisi
        trend_data = []
        current_date = baslangic
        
        while current_date <= bitis:
            # O günün verilerini al
            query = db.session.query(
                func.sum(MinibarIslemDetay.satis_fiyati * MinibarIslemDetay.miktar).label('toplam_gelir'),
                func.sum(MinibarIslemDetay.alis_fiyati * MinibarIslemDetay.miktar).label('toplam_maliyet'),
                func.sum(MinibarIslemDetay.kar_tutari).label('net_kar')
            ).join(
                MinibarIslem, MinibarIslem.id == MinibarIslemDetay.islem_id
            ).filter(
                func.date(MinibarIslem.islem_tarihi) == current_date
            )
            
            if otel_id:
                from models import Oda
                query = query.join(Oda, Oda.id == MinibarIslem.oda_id).filter(Oda.otel_id == otel_id)
            
            result = query.first()
            
            trend_data.append({
                'tarih': current_date.isoformat(),
                'toplam_gelir': float(result.toplam_gelir or 0),
                'toplam_maliyet': float(result.toplam_maliyet or 0),
                'net_kar': float(result.net_kar or 0)
            })
            
            current_date += timedelta(days=1)
        
        return jsonify({
            'success': True,
            'trend_data': trend_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@karlilik_bp.route('/urunler', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'kat_sorumlusu'])
def en_karli_urunler():
    """
    En karlı ürünler listesi (Dashboard için)
    
    Query Parameters:
        - otel_id: Otel ID (opsiyonel)
        - baslangic: Başlangıç tarihi (YYYY-MM-DD, required)
        - bitis: Bitiş tarihi (YYYY-MM-DD, required)
        - limit: Maksimum sonuç sayısı (varsayılan: 10)
    """
    try:
        from models import MinibarIslem, MinibarIslemDetay, Urun, Oda
        from sqlalchemy import func
        
        otel_id_str = request.args.get('otel_id', '')
        otel_id = int(otel_id_str) if otel_id_str else None
        baslangic_str = request.args.get('baslangic')
        bitis_str = request.args.get('bitis')
        limit = request.args.get('limit', 10, type=int)
        
        if not all([baslangic_str, bitis_str]):
            return jsonify({
                'success': False,
                'error': 'baslangic ve bitis zorunludur'
            }), 400
        
        # Tarih parse
        baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date()
        bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date()
        
        # Ürün bazlı karlılık sorgusu
        query = db.session.query(
            Urun.urun_adi,
            func.sum(MinibarIslemDetay.tuketim).label('satis_adedi'),
            func.sum(MinibarIslemDetay.satis_fiyati * MinibarIslemDetay.tuketim).label('toplam_gelir'),
            func.sum(MinibarIslemDetay.alis_fiyati * MinibarIslemDetay.tuketim).label('toplam_maliyet'),
            func.sum(MinibarIslemDetay.kar_tutari).label('net_kar')
        ).join(
            MinibarIslemDetay, MinibarIslemDetay.urun_id == Urun.id
        ).join(
            MinibarIslem, MinibarIslem.id == MinibarIslemDetay.islem_id
        ).filter(
            func.date(MinibarIslem.islem_tarihi) >= baslangic,
            func.date(MinibarIslem.islem_tarihi) <= bitis
        )
        
        if otel_id:
            query = query.join(Oda, Oda.id == MinibarIslem.oda_id).filter(Oda.otel_id == otel_id)
        
        query = query.group_by(Urun.id, Urun.urun_adi).order_by(func.sum(MinibarIslemDetay.kar_tutari).desc()).limit(limit)
        
        results = query.all()
        
        urunler = []
        for row in results:
            toplam_gelir = float(row.toplam_gelir or 0)
            toplam_maliyet = float(row.toplam_maliyet or 0)
            net_kar = float(row.net_kar or 0)
            kar_marji = (net_kar / toplam_gelir * 100) if toplam_gelir > 0 else 0
            
            urunler.append({
                'urun_adi': row.urun_adi,
                'satis_adedi': int(row.satis_adedi or 0),
                'toplam_gelir': toplam_gelir,
                'toplam_maliyet': toplam_maliyet,
                'net_kar': net_kar,
                'kar_marji': kar_marji
            })
        
        return jsonify({
            'success': True,
            'urunler': urunler
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



