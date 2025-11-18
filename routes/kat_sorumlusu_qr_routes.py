"""
Kat Sorumlusu QR Kod Route'ları
"""

from flask import jsonify, request, render_template, session
from models import db, Oda
from utils.qr_service import QRKodService
from utils.rate_limiter import QRRateLimiter
from utils.helpers import log_islem, log_hata
from utils.decorators import login_required, role_required


def register_kat_sorumlusu_qr_routes(app):
    """Kat sorumlusu QR route'larını kaydet"""
    
    @app.route('/kat-sorumlusu/qr-okuyucu')
    @login_required
    @role_required('kat_sorumlusu')
    def kat_sorumlusu_qr_okuyucu():
        """QR okuyucu sayfası"""
        try:
            return render_template('kat_sorumlusu/qr_okuyucu.html')
        except Exception as e:
            log_hata(e, modul='kat_sorumlusu_qr')
            return "QR okuyucu sayfası yüklenemedi", 500
    
    
    @app.route('/api/kat-sorumlusu/qr-parse', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_kat_sorumlusu_qr_parse():
        """QR koddan oda bilgilerini parse et"""
        try:
            data = request.get_json() or {}
            token = data.get('token', '').strip()
            
            if not token:
                return jsonify({
                    'success': False,
                    'message': 'Token bulunamadı'
                }), 400
            
            # Rate limit kontrolü
            ip = request.remote_addr
            if not QRRateLimiter.check_qr_scan_limit(ip):
                return jsonify({
                    'success': False,
                    'message': 'Çok fazla QR okutma denemesi. Lütfen 1 dakika bekleyin.'
                }), 429
            
            # Token'ı doğrula
            oda = QRKodService.validate_token(token)
            
            if not oda:
                # Başarısız okutma logu
                QRKodService.log_qr_scan(
                    oda_id=None,
                    okutma_tipi='personel_kontrol',
                    kullanici_id=session.get('kullanici_id'),
                    basarili=False,
                    hata_mesaji='Geçersiz token'
                )
                
                return jsonify({
                    'success': False,
                    'message': 'Geçersiz veya tanınmayan QR kod'
                }), 404
            
            # Kat sorumlusunun otelini kontrol et
            from utils.authorization import get_kat_sorumlusu_otel
            kullanici_id = session['kullanici_id']
            kullanici_oteli = get_kat_sorumlusu_otel(kullanici_id)
            
            if not kullanici_oteli:
                QRKodService.log_qr_scan(
                    oda_id=oda.id,
                    okutma_tipi='personel_kontrol',
                    kullanici_id=kullanici_id,
                    basarili=False,
                    hata_mesaji='Otel ataması bulunamadı'
                )
                return jsonify({
                    'success': False,
                    'message': 'Otel atamanız bulunamadı'
                }), 403
            
            # Odanın bu otele ait olduğunu kontrol et
            if oda.kat.otel_id != kullanici_oteli.id:
                QRKodService.log_qr_scan(
                    oda_id=oda.id,
                    okutma_tipi='personel_kontrol',
                    kullanici_id=kullanici_id,
                    basarili=False,
                    hata_mesaji='Bu odaya erişim yetkiniz yok'
                )
                return jsonify({
                    'success': False,
                    'message': 'Bu oda size ait otelde değil'
                }), 403
            
            # Başarılı okutma logu
            QRKodService.log_qr_scan(
                oda_id=oda.id,
                okutma_tipi='personel_kontrol',
                kullanici_id=session.get('kullanici_id'),
                basarili=True
            )
            
            # Log kaydı
            log_islem('qr_okutma', 'kat_sorumlusu', {
                'oda_id': oda.id,
                'oda_no': oda.oda_no,
                'kat_id': oda.kat_id
            })
            
            return jsonify({
                'success': True,
                'message': f'Oda {oda.oda_no} tanındı',
                'data': {
                    'oda_id': oda.id,
                    'oda_no': oda.oda_no,
                    'kat_id': oda.kat_id,
                    'kat_adi': oda.kat.kat_adi
                }
            })
            
        except Exception as e:
            log_hata(e, modul='kat_sorumlusu_qr_parse')
            return jsonify({
                'success': False,
                'message': 'QR kod işlenirken hata oluştu'
            }), 500
