"""
Authentication Route'ları

Bu modül kimlik doğrulama ve yetkilendirme endpoint'lerini içerir.

Endpoint'ler:
- / - Ana sayfa (yönlendirme)
- /setup - İlk kurulum
- /login - Kullanıcı girişi
- /logout - Kullanıcı çıkışı

Roller:
- Herkese açık (setup, login)
- Giriş yapmış kullanıcılar (logout)
"""

from flask import render_template, request, redirect, url_for, flash, session
from datetime import datetime, timezone
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
from sqlalchemy.exc import IntegrityError, OperationalError

from models import db, Otel, Kullanici, SistemAyar
from utils.decorators import setup_not_completed, setup_required
from utils.helpers import log_islem, log_hata
from utils.audit import audit_login, audit_logout


def register_auth_routes(app):
    """Auth route'larını kaydet"""
    
    @app.route('/')
    def index():
        """Ana sayfa yönlendirmesi"""
        # Setup kontrolü
        setup_tamamlandi = SistemAyar.query.filter_by(anahtar='setup_tamamlandi').first()
        
        if not setup_tamamlandi or setup_tamamlandi.deger != '1':
            return redirect(url_for('setup'))
        
        # Giriş yapmış kullanıcı varsa panele yönlendir
        if 'kullanici_id' in session:
            return redirect(url_for('dashboard'))
        
        return redirect(url_for('login'))
    
    
    @app.route('/setup', methods=['GET', 'POST'])
    @setup_not_completed
    def setup():
        """İlk kurulum sayfası"""
        from forms import SetupForm

        form = SetupForm()

        if form.validate_on_submit():
            try:
                # Otel bilgileri
                otel = Otel(
                    ad=form.otel_adi.data,
                    adres=form.adres.data,
                    telefon=form.telefon.data,
                    email=form.email.data,
                    vergi_no=form.vergi_no.data or ''
                )
                db.session.add(otel)
                db.session.flush()  # ID'yi almak için

                # Sistem yöneticisi oluştur
                sistem_yoneticisi = Kullanici(
                    kullanici_adi=form.kullanici_adi.data,
                    ad=form.ad.data,
                    soyad=form.soyad.data,
                    email=form.admin_email.data,
                    telefon=form.admin_telefon.data or '',
                    rol='sistem_yoneticisi'
                )
                sistem_yoneticisi.sifre_belirle(form.sifre.data)
                db.session.add(sistem_yoneticisi)

                # Setup tamamlandı işaretle
                setup_ayar = SistemAyar(
                    anahtar='setup_tamamlandi',
                    deger='1',
                    aciklama='İlk kurulum tamamlandı'
                )
                db.session.add(setup_ayar)

                db.session.commit()

                flash('İlk kurulum başarıyla tamamlandı! Giriş yapabilirsiniz.', 'success')
                return redirect(url_for('login'))

            except IntegrityError:
                db.session.rollback()
                flash('Bu kullanıcı adı zaten kullanılıyor. Lütfen farklı bir kullanıcı adı deneyin.', 'danger')
                log_hata(Exception('Setup IntegrityError'), modul='setup')
            except OperationalError as e:
                db.session.rollback()
                flash('Veritabanı bağlantı hatası. Lütfen daha sonra tekrar deneyin.', 'danger')
                log_hata(e, modul='setup')
            except Exception as e:
                db.session.rollback()
                flash('Beklenmeyen bir hata oluştu. Sistem yöneticisine bildirildi.', 'danger')
                log_hata(e, modul='setup', extra_info={'form_data': form.data})

        # Eğer POST yapıldı fakat form doğrulama başarısızsa, hata detaylarını loglayalım
        if request.method == 'POST' and not form.validate_on_submit():
            try:
                # form.errors JSON-serializable olmayabilir, bu yüzden güvenli hale getir
                errors = {k: v for k, v in (form.errors or {}).items()}
                form_data = request.form.to_dict()
                log_hata(Exception('Setup validation failed'), modul='setup', extra_info={'errors': errors, 'form_data': form_data})
                flash('Form doğrulama hatası. Girdi alanlarını kontrol edin ve tekrar deneyin.', 'danger')
            except Exception as e:
                # Log kaydında da hata olursa yakala ama işlemi bozma
                log_hata(e, modul='setup', extra_info={'note': 'logging_failed_on_validation'})

        return render_template('setup.html', form=form)
    
    
    @app.route('/login', methods=['GET', 'POST'])
    @setup_required
    def login():
        """Kullanıcı giriş sayfası"""
        from forms import LoginForm

        form = LoginForm()

        if form.validate_on_submit():
            kullanici = Kullanici.query.filter_by(
                kullanici_adi=form.kullanici_adi.data,
                aktif=True
            ).first()

            if kullanici and kullanici.sifre_kontrol(form.sifre.data):
                session.clear()
                session.permanent = form.remember_me.data

                session['kullanici_id'] = kullanici.id
                session['kullanici_adi'] = kullanici.kullanici_adi
                session['ad'] = kullanici.ad
                session['soyad'] = kullanici.soyad
                session['rol'] = kullanici.rol

                # Son giriş tarihini güncelle
                try:
                    kullanici.son_giris = get_kktc_now()
                    db.session.commit()
                except Exception as e:
                    # Son giriş güncelleme hatası login'i engellemez
                    log_hata(e, modul='login', extra_info={'action': 'son_giris_guncelleme'})

                # Log kaydı
                log_islem('giris', 'sistem', {
                    'kullanici_adi': kullanici.kullanici_adi,
                    'ad_soyad': f'{kullanici.ad} {kullanici.soyad}',
                    'rol': kullanici.rol
                })

                # Audit Trail
                audit_login(
                    kullanici_id=kullanici.id,
                    kullanici_adi=kullanici.kullanici_adi,
                    kullanici_rol=kullanici.rol,
                    basarili=True
                )

                # Cache temizleme flag'i - tarayıcı cache'ini temizlemek için
                session['clear_cache'] = True

                flash(f'Hoş geldiniz, {kullanici.ad} {kullanici.soyad}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                # Başarısız login denemesini logla
                audit_login(
                    kullanici_id=None,
                    kullanici_adi=form.kullanici_adi.data,
                    kullanici_rol='unknown',
                    basarili=False,
                    hata_mesaji='Geçersiz kullanıcı adı veya şifre'
                )
                flash('Kullanıcı adı veya şifre hatalı!', 'danger')

        return render_template('login.html', form=form)
    
    
    @app.route('/logout')
    def logout():
        """Kullanıcı çıkışı"""
        # Log kaydı (session temizlenmeden önce)
        kullanici_id = session.get('kullanici_id')
        if kullanici_id:
            kullanici = db.session.get(Kullanici, kullanici_id)
            if kullanici:
                log_islem('cikis', 'sistem', {
                    'kullanici_adi': kullanici.kullanici_adi,
                    'ad_soyad': f'{kullanici.ad} {kullanici.soyad}',
                    'rol': kullanici.rol
                })
                
                # Audit Trail
                audit_logout()
        
        session.clear()
        flash('Başarıyla çıkış yaptınız.', 'info')
        return redirect(url_for('login'))

