"""
Kullanıcı Ayarları Routes
Tema, renk ve kişisel tercihler
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models.base import db
from models.kullanici import Kullanici

def register_kullanici_ayarlari_routes(app):
    """Kullanıcı ayarları route'larını kaydet"""
    
    @app.route('/kullanici/ayarlar')
    @login_required
    def kullanici_ayarlari():
        """Kullanıcı ayarları sayfası"""
        return render_template('kullanici/ayarlar.html')
    
    @app.route('/api/kullanici/tema-renkleri', methods=['GET'])
    @login_required
    def api_tema_renkleri():
        """Kullanıcının tema renklerini getir"""
        try:
            return jsonify({
                'success': True,
                'tema_renk_1': current_user.tema_renk_1 or '#2563EB',
                'tema_renk_2': current_user.tema_renk_2 or '#0284C7'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
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
            
            # Renk formatını kontrol et (#RRGGBB)
            import re
            if not re.match(r'^#[0-9A-Fa-f]{6}$', tema_renk_1) or not re.match(r'^#[0-9A-Fa-f]{6}$', tema_renk_2):
                return jsonify({
                    'success': False,
                    'message': 'Geçersiz renk formatı! (#RRGGBB formatında olmalı)'
                }), 400
            
            # Kullanıcının tema renklerini güncelle
            kullanici = Kullanici.query.get(current_user.id)
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
