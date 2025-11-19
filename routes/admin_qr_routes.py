"""
Admin QR Kod Yönetimi Route'ları
"""

from flask import jsonify, request, send_file, session
from models import db, Oda, Kat
from utils.qr_service import QRKodService
from utils.rate_limiter import QRRateLimiter
from utils.helpers import log_islem, log_hata
from utils.audit import audit_create, audit_update, serialize_model
from utils.decorators import login_required, role_required
import bleach
import zipfile
import io
from datetime import datetime


def register_admin_qr_routes(app):
    """Admin QR route'larını kaydet"""
    
    @app.route('/admin/oda-qr-olustur/<int:oda_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_oda_qr_olustur(oda_id):
        """Tek oda için QR kod oluştur"""
        try:
            # Rate limit kontrolü
            ip = request.remote_addr
            if not QRRateLimiter.check_qr_generate_limit(ip):
                return jsonify({
                    'success': False,
                    'message': 'Çok fazla QR oluşturma denemesi. Lütfen 1 dakika bekleyin.'
                }), 429
            
            # Oda kontrolü
            oda = db.session.get(Oda, oda_id)
            if not oda:
                return jsonify({
                    'success': False,
                    'message': 'Oda bulunamadı'
                }), 404
            
            # QR kod oluştur
            result = QRKodService.create_qr_for_oda(oda)
            
            if result['success']:
                db.session.commit()
                
                # Audit log
                audit_create(
                    tablo_adi='odalar',
                    kayit_id=oda.id,
                    yeni_deger={'qr_kod_token': result['token'][:10] + '...'},
                    aciklama=f'QR kod oluşturuldu - Oda {oda.oda_no}'
                )
                
                # Log kaydı
                log_islem('ekleme', 'qr_kod', {
                    'oda_id': oda.id,
                    'oda_no': oda.oda_no
                })
                
                return jsonify({
                    'success': True,
                    'message': f'QR kod başarıyla oluşturuldu - Oda {oda.oda_no}',
                    'data': {
                        'oda_id': oda.id,
                        'oda_no': oda.oda_no,
                        'qr_image': result['image']
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'QR kod oluşturulamadı: {result.get("error", "Bilinmeyen hata")}'
                }), 500
                
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='admin_qr', extra_info={'oda_id': oda_id})
            return jsonify({
                'success': False,
                'message': 'QR kod oluşturulurken hata oluştu'
            }), 500
    
    
    @app.route('/admin/toplu-qr-olustur', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_toplu_qr_olustur():
        """Tüm odalar veya QR'sız odalar için toplu QR oluştur"""
        try:
            data = request.get_json() or {}
            mod = data.get('mod', 'qrsiz')  # 'tumu' veya 'qrsiz'
            
            # Rate limit kontrolü
            ip = request.remote_addr
            if not QRRateLimiter.check_qr_generate_limit(ip):
                return jsonify({
                    'success': False,
                    'message': 'Çok fazla QR oluşturma denemesi. Lütfen 1 dakika bekleyin.'
                }), 429
            
            # Odaları getir
            if mod == 'tumu':
                odalar = Oda.query.filter_by(aktif=True).all()
            else:  # qrsiz
                odalar = Oda.query.filter_by(aktif=True, qr_kod_token=None).all()
            
            if not odalar:
                return jsonify({
                    'success': False,
                    'message': 'İşlem yapılacak oda bulunamadı'
                }), 404
            
            # Toplu QR oluştur
            basarili = 0
            basarisiz = 0
            
            for oda in odalar:
                try:
                    result = QRKodService.create_qr_for_oda(oda)
                    if result['success']:
                        basarili += 1
                    else:
                        basarisiz += 1
                    
                    # Her 50 odada bir commit
                    if (basarili + basarisiz) % 50 == 0:
                        db.session.commit()
                        
                except Exception as e:
                    basarisiz += 1
                    log_hata(e, modul='admin_qr_toplu', extra_info={'oda_id': oda.id})
            
            # Final commit
            db.session.commit()
            
            # Log kaydı
            log_islem('ekleme', 'qr_kod_toplu', {
                'mod': mod,
                'basarili': basarili,
                'basarisiz': basarisiz,
                'toplam': len(odalar)
            })
            
            return jsonify({
                'success': True,
                'message': f'Toplu QR oluşturma tamamlandı',
                'data': {
                    'basarili': basarili,
                    'basarisiz': basarisiz,
                    'toplam': len(odalar)
                }
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='admin_qr_toplu')
            return jsonify({
                'success': False,
                'message': 'Toplu QR oluşturma sırasında hata oluştu'
            }), 500
    
    
    @app.route('/admin/oda-qr-goruntule/<int:oda_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_oda_qr_goruntule(oda_id):
        """QR kodu görüntüle (JSON)"""
        try:
            oda = db.session.get(Oda, oda_id)
            if not oda:
                return jsonify({
                    'success': False,
                    'message': 'Oda bulunamadı'
                }), 404
            
            if not oda.qr_kod_token:
                return jsonify({
                    'success': False,
                    'message': 'Bu oda için QR kod oluşturulmamış'
                }), 404
            
            # Log kaydı
            log_islem('goruntuleme', 'qr_kod', {
                'oda_id': oda.id,
                'oda_no': oda.oda_no
            })
            
            return jsonify({
                'success': True,
                'data': {
                    'oda_id': oda.id,
                    'oda_no': oda.oda_no,
                    'kat_adi': oda.kat.kat_adi,
                    'qr_image': oda.qr_kod_gorsel,
                    'olusturma_tarihi': oda.qr_kod_olusturma_tarihi.strftime('%d.%m.%Y %H:%M') if oda.qr_kod_olusturma_tarihi else None
                }
            })
            
        except Exception as e:
            log_hata(e, modul='admin_qr', extra_info={'oda_id': oda_id})
            return jsonify({
                'success': False,
                'message': 'QR kod görüntülenirken hata oluştu'
            }), 500
    
    
    @app.route('/admin/oda-qr-indir/<int:oda_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_oda_qr_indir(oda_id):
        """QR kodu SVG olarak indir"""
        try:
            oda = db.session.get(Oda, oda_id)
            if not oda or not oda.qr_kod_gorsel:
                return jsonify({
                    'success': False,
                    'message': 'QR kod bulunamadı'
                }), 404
            
            # SVG string'i al
            svg_data = oda.qr_kod_gorsel
            
            # Log kaydı
            log_islem('export', 'qr_kod', {
                'oda_id': oda.id,
                'oda_no': oda.oda_no
            })
            
            # Dosya adı
            filename = f'QR_Oda_{oda.oda_no}.svg'
            
            return send_file(
                io.BytesIO(svg_data.encode('utf-8')),
                mimetype='image/svg+xml',
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            log_hata(e, modul='admin_qr', extra_info={'oda_id': oda_id})
            return jsonify({
                'success': False,
                'message': 'QR kod indirilirken hata oluştu'
            }), 500
    
    
    @app.route('/admin/toplu-qr-indir')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_toplu_qr_indir():
        """Tüm QR kodları ZIP olarak indir"""
        try:
            # QR'ı olan odaları getir
            odalar = Oda.query.filter(
                Oda.aktif == True,
                Oda.qr_kod_token.isnot(None)
            ).all()
            
            if not odalar:
                return jsonify({
                    'success': False,
                    'message': 'QR kodu olan oda bulunamadı'
                }), 404
            
            # ZIP dosyası oluştur
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                import base64
                
                for oda in odalar:
                    try:
                        # Base64'ten PNG'ye çevir
                        img_data = oda.qr_kod_gorsel.split(',')[1]
                        img_bytes = base64.b64decode(img_data)
                        
                        # ZIP'e ekle
                        filename = f'Oda_{oda.oda_no}_QR.png'
                        zip_file.writestr(filename, img_bytes)
                        
                    except Exception as e:
                        log_hata(e, modul='admin_qr_zip', extra_info={'oda_id': oda.id})
                        continue
            
            zip_buffer.seek(0)
            
            # Log kaydı
            log_islem('export', 'qr_kod_toplu', {
                'oda_sayisi': len(odalar)
            })
            
            # Dosya adı
            filename = f'QR_Kodlari_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
            
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name=filename
            )
            
        except Exception as e:
            log_hata(e, modul='admin_qr_zip')
            return jsonify({
                'success': False,
                'message': 'ZIP dosyası oluşturulurken hata oluştu'
            }), 500
    
    
    @app.route('/admin/oda-misafir-mesaji/<int:oda_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_oda_misafir_mesaji(oda_id):
        """Oda misafir mesajını düzenle"""
        try:
            oda = db.session.get(Oda, oda_id)
            if not oda:
                return jsonify({
                    'success': False,
                    'message': 'Oda bulunamadı'
                }), 404
            
            if request.method == 'POST':
                data = request.get_json() or {}
                mesaj = data.get('mesaj', '').strip()
                
                # Input sanitization
                if mesaj:
                    mesaj = bleach.clean(mesaj, tags=[], strip=True)
                    if len(mesaj) > 500:
                        return jsonify({
                            'success': False,
                            'message': 'Mesaj maksimum 500 karakter olabilir'
                        }), 400
                
                # Eski değeri sakla
                eski_deger = serialize_model(oda)
                
                # Güncelle
                oda.misafir_mesaji = mesaj if mesaj else None
                db.session.commit()
                
                # Audit log
                audit_update(
                    tablo_adi='odalar',
                    kayit_id=oda.id,
                    eski_deger=eski_deger,
                    yeni_deger=serialize_model(oda),
                    aciklama=f'Misafir mesajı güncellendi - Oda {oda.oda_no}'
                )
                
                # Log kaydı
                log_islem('guncelleme', 'oda_misafir_mesaji', {
                    'oda_id': oda.id,
                    'oda_no': oda.oda_no
                })
                
                return jsonify({
                    'success': True,
                    'message': 'Misafir mesajı başarıyla güncellendi',
                    'data': {
                        'mesaj': oda.misafir_mesaji
                    }
                })
            
            else:  # GET
                return jsonify({
                    'success': True,
                    'data': {
                        'oda_id': oda.id,
                        'oda_no': oda.oda_no,
                        'mesaj': oda.misafir_mesaji or ''
                    }
                })
                
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='admin_qr', extra_info={'oda_id': oda_id})
            return jsonify({
                'success': False,
                'message': 'İşlem sırasında hata oluştu'
            }), 500


    @app.route('/admin/tum-qr-temizle', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_tum_qr_temizle():
        """Tüm odaların QR kodlarını temizle"""
        try:
            # Tüm aktif odaları getir
            odalar = Oda.query.filter_by(aktif=True).all()
            
            temizlenen_adet = 0
            
            for oda in odalar:
                if oda.qr_kod_token or oda.qr_kod_gorsel:
                    # QR bilgilerini temizle
                    oda.qr_kod_token = None
                    oda.qr_kod_gorsel = None
                    oda.qr_kod_olusturma_tarihi = None
                    temizlenen_adet += 1
            
            db.session.commit()
            
            # Audit log
            audit_create(
                tablo_adi='odalar',
                kayit_id=None,
                yeni_deger={'temizlenen_adet': temizlenen_adet},
                aciklama=f'Tüm QR kodları temizlendi - {temizlenen_adet} oda'
            )
            
            # Log kaydı
            log_islem('silme', 'qr_kod_toplu', {
                'temizlenen_adet': temizlenen_adet,
                'islem': 'tum_qr_temizle'
            })
            
            return jsonify({
                'success': True,
                'message': f'{temizlenen_adet} odanın QR kodu başarıyla temizlendi',
                'temizlenen_adet': temizlenen_adet
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='admin_tum_qr_temizle')
            return jsonify({
                'success': False,
                'message': 'QR kodları temizlenirken hata oluştu'
            }), 500
