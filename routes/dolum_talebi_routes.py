"""
Dolum Talebi Yönetimi Route'ları
"""

from flask import jsonify, request
from models import db, MinibarDolumTalebi, Oda
from utils.helpers import log_islem, log_hata
from utils.decorators import login_required, role_required
from datetime import datetime, timezone, timedelta


def register_dolum_talebi_routes(app):
    """Dolum talebi route'larını kaydet"""
    
    @app.route('/api/dolum-talepleri')
    @login_required
    @role_required('kat_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_dolum_talepleri():
        """Bekleyen dolum taleplerini listele"""
        try:
            # Bekleyen talepleri getir
            talepler = MinibarDolumTalebi.query.filter_by(
                durum='beklemede'
            ).order_by(
                MinibarDolumTalebi.talep_tarihi.desc()
            ).all()
            
            talep_listesi = []
            # Kıbrıs/Türkiye saat dilimi (UTC+3, yaz saati uygulaması yok)
            local_tz = timezone(timedelta(hours=3))
            
            for talep in talepler:
                # UTC'den yerel saate çevir
                talep_tarihi_local = talep.talep_tarihi.replace(tzinfo=timezone.utc).astimezone(local_tz)
                
                talep_listesi.append({
                    'id': talep.id,
                    'oda_id': talep.oda_id,
                    'oda_no': talep.oda.oda_no,
                    'kat_adi': talep.oda.kat.kat_adi,
                    'talep_tarihi': talep_tarihi_local.isoformat(),  # ISO format with local timezone
                    'notlar': talep.notlar or ''
                })
            
            return jsonify({
                'success': True,
                'talepler': talep_listesi,
                'count': len(talep_listesi)
            })
            
        except Exception as e:
            log_hata(e, modul='dolum_talepleri_api')
            return jsonify({
                'success': False,
                'message': 'Talepler yüklenirken hata oluştu'
            }), 500
    
    
    @app.route('/api/dolum-talebi-tamamla/<int:talep_id>', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_dolum_talebi_tamamla(talep_id):
        """Dolum talebini tamamla"""
        try:
            talep = db.session.get(MinibarDolumTalebi, talep_id)
            
            if not talep:
                return jsonify({
                    'success': False,
                    'message': 'Talep bulunamadı'
                }), 404
            
            if talep.durum != 'beklemede':
                return jsonify({
                    'success': False,
                    'message': 'Bu talep zaten işlenmiş'
                }), 400
            
            # Talebi tamamla
            talep.durum = 'tamamlandi'
            talep.tamamlanma_tarihi = datetime.utcnow()
            db.session.commit()
            
            # Log kaydı
            log_islem('guncelleme', 'dolum_talebi', {
                'talep_id': talep.id,
                'oda_id': talep.oda_id,
                'oda_no': talep.oda.oda_no,
                'durum': 'tamamlandi'
            })
            
            return jsonify({
                'success': True,
                'message': 'Talep tamamlandı olarak işaretlendi'
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='dolum_talebi_tamamla', extra_info={'talep_id': talep_id})
            return jsonify({
                'success': False,
                'message': 'Talep güncellenirken hata oluştu'
            }), 500
    
    
    @app.route('/api/dolum-talebi-iptal/<int:talep_id>', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_dolum_talebi_iptal(talep_id):
        """Dolum talebini iptal et"""
        try:
            talep = db.session.get(MinibarDolumTalebi, talep_id)
            
            if not talep:
                return jsonify({
                    'success': False,
                    'message': 'Talep bulunamadı'
                }), 404
            
            # Notları al
            data = request.get_json() or {}
            notlar = data.get('notlar', '')
            
            # Talebi iptal et
            talep.durum = 'iptal'
            talep.notlar = notlar
            talep.tamamlanma_tarihi = datetime.utcnow()
            db.session.commit()
            
            # Log kaydı
            log_islem('guncelleme', 'dolum_talebi', {
                'talep_id': talep.id,
                'oda_id': talep.oda_id,
                'durum': 'iptal',
                'notlar': notlar
            })
            
            return jsonify({
                'success': True,
                'message': 'Talep iptal edildi'
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='dolum_talebi_iptal', extra_info={'talep_id': talep_id})
            return jsonify({
                'success': False,
                'message': 'Talep iptal edilirken hata oluştu'
            }), 500
    
    
    # Admin API'leri
    @app.route('/api/dolum-talepleri-admin')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_dolum_talepleri_admin():
        """Admin için tüm dolum taleplerini listele"""
        try:
            durum = request.args.get('durum', 'tumu')
            
            query = MinibarDolumTalebi.query
            
            if durum != 'tumu':
                query = query.filter_by(durum=durum)
            
            talepler = query.order_by(
                MinibarDolumTalebi.talep_tarihi.desc()
            ).limit(100).all()
            
            talep_listesi = []
            # Kıbrıs/Türkiye saat dilimi (UTC+3)
            local_tz = timezone(timedelta(hours=3))
            
            for talep in talepler:
                # UTC'den yerel saate çevir
                talep_tarihi_local = talep.talep_tarihi.replace(tzinfo=timezone.utc).astimezone(local_tz)
                
                talep_dict = {
                    'id': talep.id,
                    'oda_id': talep.oda_id,
                    'oda_no': talep.oda.oda_no,
                    'kat_adi': talep.oda.kat.kat_adi,
                    'talep_tarihi': talep_tarihi_local.isoformat(),
                    'durum': talep.durum,
                    'notlar': talep.notlar or ''
                }
                
                if talep.tamamlanma_tarihi:
                    tamamlanma_local = talep.tamamlanma_tarihi.replace(tzinfo=timezone.utc).astimezone(local_tz)
                    talep_dict['tamamlanma_tarihi'] = tamamlanma_local.isoformat()
                else:
                    talep_dict['tamamlanma_tarihi'] = None
                
                talep_listesi.append(talep_dict)
            
            return jsonify({
                'success': True,
                'talepler': talep_listesi
            })
            
        except Exception as e:
            log_hata(e, modul='dolum_talepleri_admin_api')
            return jsonify({
                'success': False,
                'message': 'Talepler yüklenirken hata oluştu'
            }), 500
    
    
    @app.route('/api/dolum-talepleri-tamamlanan')
    @login_required
    @role_required('kat_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_dolum_talepleri_tamamlanan():
        """Son 7 gün içinde tamamlanan dolum taleplerini listele"""
        try:
            from datetime import date
            from models import Kullanici
            
            # Son 7 günün başlangıcı
            yedi_gun_once = datetime.combine(date.today() - timedelta(days=7), datetime.min.time())
            
            # Tamamlanan talepleri getir
            talepler = MinibarDolumTalebi.query.filter(
                MinibarDolumTalebi.durum == 'tamamlandi',
                MinibarDolumTalebi.tamamlanma_tarihi >= yedi_gun_once
            ).order_by(
                MinibarDolumTalebi.tamamlanma_tarihi.desc()
            ).all()
            
            talep_listesi = []
            # Kıbrıs/Türkiye saat dilimi (UTC+3)
            local_tz = timezone(timedelta(hours=3))
            
            for talep in talepler:
                # UTC'den yerel saate çevir
                talep_tarihi_local = talep.talep_tarihi.replace(tzinfo=timezone.utc).astimezone(local_tz)
                tamamlanma_tarihi_local = talep.tamamlanma_tarihi.replace(tzinfo=timezone.utc).astimezone(local_tz)
                
                # Tamamlayan kişiyi bul (session'dan)
                tamamlayan_ad = "-"
                if hasattr(talep, 'tamamlayan_id') and talep.tamamlayan_id:
                    tamamlayan = db.session.get(Kullanici, talep.tamamlayan_id)
                    if tamamlayan:
                        tamamlayan_ad = f"{tamamlayan.ad} {tamamlayan.soyad}"
                
                talep_listesi.append({
                    'id': talep.id,
                    'oda_id': talep.oda_id,
                    'oda_no': talep.oda.oda_no,
                    'kat_adi': talep.oda.kat.kat_adi,
                    'talep_tarihi': talep_tarihi_local.isoformat(),
                    'tamamlanma_tarihi': tamamlanma_tarihi_local.isoformat(),
                    'tamamlayan_ad': tamamlayan_ad,
                    'notlar': talep.notlar or ''
                })
            
            return jsonify({
                'success': True,
                'talepler': talep_listesi,
                'count': len(talep_listesi)
            })
            
        except Exception as e:
            log_hata(e, modul='dolum_talepleri_tamamlanan_api')
            return jsonify({
                'success': False,
                'message': 'Tamamlanan talepler yüklenirken hata oluştu'
            }), 500
    
    
    @app.route('/api/dolum-talepleri-istatistik')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_dolum_talepleri_istatistik():
        """Dolum talepleri istatistikleri"""
        try:
            from datetime import date
            
            # Bekleyen talepler
            bekleyen = MinibarDolumTalebi.query.filter_by(durum='beklemede').count()
            
            # Bugün tamamlanan
            bugun_baslangic = datetime.combine(date.today(), datetime.min.time())
            tamamlanan_bugun = MinibarDolumTalebi.query.filter(
                MinibarDolumTalebi.durum == 'tamamlandi',
                MinibarDolumTalebi.tamamlanma_tarihi >= bugun_baslangic
            ).count()
            
            # Bugün iptal edilen
            iptal_bugun = MinibarDolumTalebi.query.filter(
                MinibarDolumTalebi.durum == 'iptal',
                MinibarDolumTalebi.tamamlanma_tarihi >= bugun_baslangic
            ).count()
            
            return jsonify({
                'success': True,
                'bekleyen': bekleyen,
                'tamamlanan_bugun': tamamlanan_bugun,
                'iptal_bugun': iptal_bugun
            })
            
        except Exception as e:
            log_hata(e, modul='dolum_talepleri_istatistik')
            return jsonify({
                'success': False,
                'message': 'İstatistikler yüklenirken hata oluştu'
            }), 500
