"""
Kullanıcı Ayarları Routes
Tema, renk ve kişisel tercihler
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from models.base import db
from models.kullanici import Kullanici
from utils.decorators import login_required

def register_kullanici_ayarlari_routes(app):
    """Kullanıcı ayarları route'larını kaydet"""
    
    @app.route('/kullanici/ayarlar')
    @login_required
    def kullanici_ayarlari():
        """Kullanıcı ayarları sayfası"""
        from flask import session
        from models.kullanici import Kullanici
        
        # Session'dan kullanıcı bilgilerini al
        kullanici_id = session.get('kullanici_id')
        if not kullanici_id:
            flash('Giriş yapmalısınız.', 'warning')
            return redirect(url_for('login'))
        
        # Kullanıcıyı veritabanından çek
        kullanici = Kullanici.query.get(kullanici_id)
        if not kullanici:
            flash('Kullanıcı bulunamadı.', 'danger')
            return redirect(url_for('dashboard'))
        
        return render_template('kullanici/ayarlar.html', current_user=kullanici)
    
    @app.route('/api/kullanici/tema-renkleri', methods=['GET'])
    @login_required
    def api_tema_renkleri():
        """Kullanıcının tema renklerini getir"""
        try:
            from flask import session
            from models.kullanici import Kullanici
            
            kullanici_id = session.get('kullanici_id')
            if not kullanici_id:
                return jsonify({
                    'success': True,
                    'tema_renk_1': '#2563EB',
                    'tema_renk_2': '#0284C7'
                })
            
            kullanici = Kullanici.query.get(kullanici_id)
            
            if not kullanici:
                return jsonify({
                    'success': True,
                    'tema_renk_1': '#2563EB',
                    'tema_renk_2': '#0284C7'
                })
            
            return jsonify({
                'success': True,
                'tema_renk_1': kullanici.tema_renk_1 or '#2563EB',
                'tema_renk_2': kullanici.tema_renk_2 or '#0284C7'
            })
        except Exception as e:
            import traceback
            print(f"❌ Tema renkleri hatası: {str(e)}")
            print(traceback.format_exc())
            # Hata olsa bile default renkleri dön
            return jsonify({
                'success': True,
                'tema_renk_1': '#2563EB',
                'tema_renk_2': '#0284C7'
            })
    
    @app.route('/api/kullanici/tema-kaydet', methods=['POST'])
    @login_required
    def api_tema_kaydet():
        """Tema renklerini kaydet"""
        try:
            from flask import session
            from models.kullanici import Kullanici
            
            data = request.get_json()
            tema_renk_1 = data.get('tema_renk_1')
            tema_renk_2 = data.get('tema_renk_2')
            
            if not tema_renk_1 or not tema_renk_2:
                return jsonify({
                    'success': False,
                    'message': 'Tema renkleri eksik!'
                }), 400
            
            # Renk formatını kontrol et (#RRGGBB)
            import re
            if not re.match(r'^#[0-9A-Fa-f]{6}$', tema_renk_1) or not re.match(r'^#[0-9A-Fa-f]{6}$', tema_renk_2):
                return jsonify({
                    'success': False,
                    'message': 'Geçersiz renk formatı! (#RRGGBB formatında olmalı)'
                }), 400
            
            # Kullanıcının tema renklerini güncelle
            kullanici_id = session.get('kullanici_id')
            kullanici = Kullanici.query.get(kullanici_id)
            
            if not kullanici:
                return jsonify({
                    'success': False,
                    'message': 'Kullanıcı bulunamadı!'
                }), 404
            
            kullanici.tema_renk_1 = tema_renk_1
            kullanici.tema_renk_2 = tema_renk_2
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': '✅ Tema renkleri kaydedildi!'
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Hata: {str(e)}'
            }), 500
