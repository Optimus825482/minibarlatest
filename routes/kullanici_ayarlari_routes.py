"""
Kullanıcı Ayarları Routes
Tema, renk ve kişisel tercihler
"""

from flask import render_template, request, jsonify, flash, redirect, url_for, session
from models import db, Kullanici  # Ana models.py'den import
from utils.decorators import login_required
import re
import traceback

def register_kullanici_ayarlari_routes(app):
    """Kullanıcı ayarları route'larını kaydet"""
    
    @app.route('/kullanici/ayarlar')
    @login_required
    def kullanici_ayarlari():
        """Kullanıcı ayarları sayfası"""
        kullanici_id = session.get('kullanici_id')
        if not kullanici_id:
            flash('Giriş yapmalısınız.', 'warning')
            return redirect(url_for('login'))
        
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
            print(f"❌ Tema renkleri hatası: {str(e)}")
            print(traceback.format_exc())
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
            data = request.get_json()
            tema_renk_1 = data.get('tema_renk_1')
            tema_renk_2 = data.get('tema_renk_2')
            
            if not tema_renk_1 or not tema_renk_2:
                return jsonify({
                    'success': False,
                    'message': 'Tema renkleri eksik!'
                }), 400
            
            # Renk formatını kontrol et
            if not re.match(r'^#[0-9A-Fa-f]{6}$', tema_renk_1) or not re.match(r'^#[0-9A-Fa-f]{6}$', tema_renk_2):
                return jsonify({
                    'success': False,
                    'message': 'Geçersiz renk formatı!'
                }), 400
            
            # Kullanıcıyı güncelle
            kullanici_id = session.get('kullanici_id')
            if not kullanici_id:
                return jsonify({
                    'success': False,
                    'message': 'Oturum bulunamadı!'
                }), 401
            
            kullanici = Kullanici.query.get(kullanici_id)
            if not kullanici:
                return jsonify({
                    'success': False,
                    'message': 'Kullanıcı bulunamadı!'
                }), 404
            
            kullanici.tema_renk_1 = tema_renk_1
            kullanici.tema_renk_2 = tema_renk_2
            db.session.commit()
            
            print(f"✅ Tema kaydedildi - Kullanıcı: {kullanici.kullanici_adi}, Badge: {tema_renk_1}, Buton: {tema_renk_2}")
            
            return jsonify({
                'success': True,
                'message': '✅ Tema renkleri kaydedildi!'
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Tema kaydetme hatası: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                'success': False,
                'message': f'Hata: {str(e)}'
            }), 500
