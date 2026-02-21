"""
Superadmin Routes

Superadmin rolüne özel endpoint'ler.
Tüm kullanıcıları görüntüleme, şifre hash'leri, roller ve yetkiler.

Endpoint'ler:
- /superadmin/users - Tüm kullanıcıları listeleme
- /api/superadmin/users - Kullanıcı verileri API
"""

from flask import render_template, jsonify, request, session
from utils.decorators import login_required, role_required
from models import db, Kullanici, Otel, KullaniciOtel
import logging

logger = logging.getLogger(__name__)


def register_superadmin_routes(app):
    """Superadmin route'larını register et"""

    @app.route('/superadmin/users')
    @login_required
    @role_required('superadmin')
    def superadmin_users():
        """Superadmin - Tüm kullanıcıları görüntüleme"""
        try:
            kullanicilar = Kullanici.query.order_by(
                Kullanici.aktif.desc(),
                Kullanici.olusturma_tarihi.desc()
            ).all()

            user_data = []
            for k in kullanicilar:
                otel_bilgisi = _get_otel_bilgisi(k)
                user_data.append({
                    'kullanici': k,
                    'otel_bilgisi': otel_bilgisi
                })

            oteller = Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()
            roller = ['superadmin', 'sistem_yoneticisi', 'admin', 'depo_sorumlusu', 'kat_sorumlusu']

            return render_template(
                'sistem_yoneticisi/superadmin_users.html',
                user_data=user_data,
                oteller=oteller,
                roller=roller,
                toplam=len(kullanicilar),
                aktif=sum(1 for k in kullanicilar if k.aktif),
                pasif=sum(1 for k in kullanicilar if not k.aktif)
            )
        except Exception as e:
            logger.error(f"Superadmin users hatası: {e}")
            return render_template(
                'sistem_yoneticisi/superadmin_users.html',
                user_data=[], oteller=[], roller=[],
                toplam=0, aktif=0, pasif=0
            )

    @app.route('/api/superadmin/users')
    @login_required
    @role_required('superadmin')
    def api_superadmin_users():
        """Superadmin - Kullanıcı verileri API"""
        try:
            kullanicilar = Kullanici.query.order_by(
                Kullanici.olusturma_tarihi.desc()
            ).all()

            data = []
            for k in kullanicilar:
                data.append({
                    'id': k.id,
                    'kullanici_adi': k.kullanici_adi,
                    'ad': k.ad,
                    'soyad': k.soyad,
                    'email': k.email or '-',
                    'telefon': k.telefon or '-',
                    'rol': k.rol,
                    'aktif': k.aktif,
                    'sifre_hash': k.sifre_hash[:20] + '...' if k.sifre_hash else '-',
                    'sifre_hash_full': k.sifre_hash or '-',
                    'otel_bilgisi': _get_otel_bilgisi(k),
                    'son_giris': k.son_giris.strftime('%d.%m.%Y %H:%M') if k.son_giris else 'Hiç giriş yapmadı',
                    'olusturma_tarihi': k.olusturma_tarihi.strftime('%d.%m.%Y %H:%M') if k.olusturma_tarihi else '-'
                })

            return jsonify({'success': True, 'data': data, 'toplam': len(data)})
        except Exception as e:
            logger.error(f"Superadmin users API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


def _get_otel_bilgisi(kullanici):
    """Kullanıcının otel bilgisini döndür"""
    try:
        if kullanici.rol in ['superadmin', 'sistem_yoneticisi', 'admin']:
            return 'Tüm Oteller'
        elif kullanici.rol == 'depo_sorumlusu':
            oteller_list = [atama.otel.ad for atama in kullanici.atanan_oteller if atama.otel]
            return ', '.join(oteller_list) if oteller_list else '-'
        elif kullanici.rol == 'kat_sorumlusu':
            return kullanici.otel.ad if kullanici.otel else '-'
        return '-'
    except Exception:
        return '⚠️ Hata'
