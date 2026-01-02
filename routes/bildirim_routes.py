"""
Bildirim Routes - Real-time bildirim API endpoint'leri

Endpoint'ler:
- GET  /api/bildirimler              - Kullanıcının bildirimlerini getir
- GET  /api/bildirimler/sayac        - Okunmamış bildirim sayısı
- POST /api/bildirimler/{id}/okundu  - Bildirimi okundu işaretle
- POST /api/bildirimler/tumunu-oku   - Tümünü okundu işaretle
- GET  /api/bildirimler/poll         - Yeni bildirimleri kontrol et (polling)
"""

from flask import jsonify, request, session
from datetime import datetime
import pytz

from utils.decorators import login_required
from utils.bildirim_service import BildirimService

KKTC_TZ = pytz.timezone('Europe/Nicosia')


def register_bildirim_routes(app):
    """Bildirim route'larını kaydet"""
    
    @app.route('/api/bildirimler', methods=['GET'])
    @login_required
    def api_bildirimler():
        """Kullanıcının bildirimlerini getirir"""
        try:
            kullanici_id = session.get('kullanici_id')
            kullanici_rol = session.get('rol')
            otel_id = session.get('otel_id')
            
            sadece_okunmamis = request.args.get('sadece_okunmamis', 'false').lower() == 'true'
            limit = min(int(request.args.get('limit', 50)), 100)
            
            bildirimler = BildirimService.kullanici_bildirimlerini_getir(
                kullanici_id=kullanici_id,
                kullanici_rol=kullanici_rol,
                otel_id=otel_id,
                sadece_okunmamis=sadece_okunmamis,
                limit=limit
            )
            
            okunmamis_sayisi = BildirimService.okunmamis_sayisi(
                kullanici_id=kullanici_id,
                kullanici_rol=kullanici_rol,
                otel_id=otel_id
            )
            
            return jsonify({
                'success': True,
                'bildirimler': bildirimler,
                'okunmamis_sayisi': okunmamis_sayisi
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/bildirimler/sayac', methods=['GET'])
    @login_required
    def api_bildirim_sayac():
        """Okunmamış bildirim sayısını döndürür"""
        try:
            kullanici_id = session.get('kullanici_id')
            kullanici_rol = session.get('rol')
            otel_id = session.get('otel_id')
            
            sayac = BildirimService.okunmamis_sayisi(
                kullanici_id=kullanici_id,
                kullanici_rol=kullanici_rol,
                otel_id=otel_id
            )
            
            return jsonify({
                'success': True,
                'okunmamis_sayisi': sayac
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/bildirimler/<int:bildirim_id>/okundu', methods=['POST'])
    @login_required
    def api_bildirim_okundu(bildirim_id):
        """Bildirimi okundu olarak işaretler"""
        try:
            success = BildirimService.okundu_isaretle(bildirim_id)
            
            if success:
                return jsonify({'success': True})
            else:
                return jsonify({
                    'success': False,
                    'error': 'Bildirim işaretlenemedi'
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/bildirimler/tumunu-oku', methods=['POST'])
    @login_required
    def api_tumunu_okundu():
        """Tüm bildirimleri okundu olarak işaretler"""
        try:
            kullanici_id = session.get('kullanici_id')
            kullanici_rol = session.get('rol')
            otel_id = session.get('otel_id')
            
            success = BildirimService.tumunu_okundu_isaretle(
                kullanici_id=kullanici_id,
                kullanici_rol=kullanici_rol,
                otel_id=otel_id
            )
            
            if success:
                return jsonify({'success': True})
            else:
                return jsonify({
                    'success': False,
                    'error': 'Bildirimler işaretlenemedi'
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/bildirimler/poll', methods=['GET'])
    @login_required
    def api_bildirim_poll():
        """
        Yeni bildirimleri kontrol eder (polling için)
        Son kontrol zamanından sonra gelen bildirimleri döndürür
        """
        try:
            kullanici_id = session.get('kullanici_id')
            kullanici_rol = session.get('rol')
            otel_id = session.get('otel_id')
            
            # Son kontrol zamanı (ISO format)
            son_kontrol_str = request.args.get('son_kontrol')
            son_kontrol = None
            
            if son_kontrol_str:
                try:
                    son_kontrol = datetime.fromisoformat(son_kontrol_str.replace('Z', '+00:00'))
                except:
                    pass
            
            yeni_bildirimler = BildirimService.yeni_bildirimler_var_mi(
                kullanici_id=kullanici_id,
                kullanici_rol=kullanici_rol,
                otel_id=otel_id,
                son_kontrol=son_kontrol
            )
            
            okunmamis_sayisi = BildirimService.okunmamis_sayisi(
                kullanici_id=kullanici_id,
                kullanici_rol=kullanici_rol,
                otel_id=otel_id
            )
            
            return jsonify({
                'success': True,
                'yeni_bildirimler': yeni_bildirimler,
                'okunmamis_sayisi': okunmamis_sayisi,
                'kontrol_zamani': datetime.now(KKTC_TZ).isoformat()
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/gorevler/ozet', methods=['GET'])
    @login_required
    def api_gorev_ozet():
        """
        Görev özeti - Real-time dashboard için
        Depo sorumlusu panelinde görev durumlarını gösterir
        """
        try:
            from models import db, GunlukGorev, GorevDetay, Otel
            from datetime import date
            from sqlalchemy import func
            
            kullanici_rol = session.get('rol')
            
            if kullanici_rol not in ['depo_sorumlusu', 'admin', 'sistem_yoneticisi']:
                return jsonify({
                    'success': False,
                    'error': 'Yetkiniz yok'
                }), 403
            
            bugun = date.today()
            
            # Otel bazlı görev özeti
            ozet = db.session.query(
                Otel.id.label('otel_id'),
                Otel.ad.label('otel_adi'),
                GunlukGorev.gorev_tipi,
                func.count(GorevDetay.id).label('toplam'),
                func.sum(func.cast(GorevDetay.durum == 'completed', db.Integer)).label('tamamlanan'),
                func.sum(func.cast(GorevDetay.durum == 'pending', db.Integer)).label('bekleyen'),
                func.sum(func.cast(GorevDetay.durum == 'in_progress', db.Integer)).label('devam_eden'),
                func.sum(func.cast(GorevDetay.durum == 'dnd_pending', db.Integer)).label('dnd')
            ).join(
                GunlukGorev, GunlukGorev.otel_id == Otel.id
            ).join(
                GorevDetay, GorevDetay.gorev_id == GunlukGorev.id
            ).filter(
                GunlukGorev.gorev_tarihi == bugun,
                Otel.aktif == True
            ).group_by(
                Otel.id, Otel.ad, GunlukGorev.gorev_tipi
            ).all()
            
            # Sonuçları düzenle
            sonuc = {}
            for row in ozet:
                otel_id = row.otel_id
                if otel_id not in sonuc:
                    sonuc[otel_id] = {
                        'otel_id': otel_id,
                        'otel_adi': row.otel_adi,
                        'gorevler': {}
                    }
                
                sonuc[otel_id]['gorevler'][row.gorev_tipi] = {
                    'toplam': row.toplam or 0,
                    'tamamlanan': row.tamamlanan or 0,
                    'bekleyen': row.bekleyen or 0,
                    'devam_eden': row.devam_eden or 0,
                    'dnd': row.dnd or 0
                }
            
            return jsonify({
                'success': True,
                'tarih': bugun.isoformat(),
                'oteller': list(sonuc.values())
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
