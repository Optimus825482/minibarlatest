"""
Admin Kullanıcı Yönetimi Route'ları
"""

from flask import render_template, request, redirect, url_for, flash
from functools import wraps
from models import db, Kullanici, AuditLog
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def login_required(f):
    """Login kontrolü"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'kullanici_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Rol kontrolü"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import session
            if 'kullanici_rol' not in session or session['kullanici_rol'] not in roles:
                flash('Bu sayfaya erişim yetkiniz yok!', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def register_admin_user_routes(app):
    """Admin kullanıcı yönetimi route'larını kaydet"""
    
    @app.route('/admin-ata', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_ata():
        """Admin kullanıcıları listele ve yeni admin ekle"""
        try:
            if request.method == 'POST':
                # Form verilerini al
                kullanici_adi = request.form.get('kullanici_adi', '').strip()
                sifre = request.form.get('sifre', '').strip()
                ad = request.form.get('ad', '').strip()
                soyad = request.form.get('soyad', '').strip()
                email = request.form.get('email', '').strip()
                telefon = request.form.get('telefon', '').strip()
                
                # Validasyon
                if not all([kullanici_adi, sifre, ad, soyad]):
                    flash('Kullanıcı adı, şifre, ad ve soyad zorunludur!', 'error')
                    return redirect(url_for('admin_ata'))
                
                # Kullanıcı adı kontrolü
                mevcut = Kullanici.query.filter_by(kullanici_adi=kullanici_adi).first()
                if mevcut:
                    flash('Bu kullanıcı adı zaten kullanılıyor!', 'error')
                    return redirect(url_for('admin_ata'))
                
                # Yeni admin oluştur
                from werkzeug.security import generate_password_hash
                yeni_admin = Kullanici(
                    kullanici_adi=kullanici_adi,
                    sifre=generate_password_hash(sifre),
                    ad=ad,
                    soyad=soyad,
                    email=email if email else None,
                    telefon=telefon if telefon else None,
                    rol='admin',
                    aktif=True,
                    olusturma_tarihi=datetime.utcnow()
                )
                
                db.session.add(yeni_admin)
                db.session.commit()
                
                # Audit log
                from flask import session
                audit = AuditLog(
                    kullanici_id=session.get('kullanici_id'),
                    kullanici_adi=session.get('kullanici_adi'),
                    kullanici_rol=session.get('kullanici_rol'),
                    islem_tipi='create',
                    tablo_adi='kullanicilar',
                    kayit_id=yeni_admin.id,
                    degisiklik_ozeti=f'Yeni admin kullanıcısı oluşturuldu: {kullanici_adi}',
                    ip_adresi=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    basarili=True
                )
                db.session.add(audit)
                db.session.commit()
                
                flash(f'{kullanici_adi} admin kullanıcısı başarıyla eklendi!', 'success')
                return redirect(url_for('admin_ata'))
            
            # Admin kullanıcıları listele
            adminler = Kullanici.query.filter_by(rol='admin').order_by(Kullanici.ad, Kullanici.soyad).all()
            
            return render_template('sistem_yoneticisi/admin_ata.html', adminler=adminler)
            
        except Exception as e:
            logger.error(f"Admin ata hatası: {str(e)}")
            db.session.rollback()
            flash('Bir hata oluştu!', 'error')
            return redirect(url_for('sistem_yoneticisi_dashboard'))
    
    
    @app.route('/admin-duzenle/<int:admin_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_duzenle(admin_id):
        """Admin kullanıcısını düzenle"""
        try:
            admin = Kullanici.query.get_or_404(admin_id)
            
            # Sadece admin rolündeki kullanıcılar düzenlenebilir
            if admin.rol != 'admin':
                flash('Bu kullanıcı admin değil!', 'error')
                return redirect(url_for('admin_ata'))
            
            if request.method == 'POST':
                # Form verilerini al
                kullanici_adi = request.form.get('kullanici_adi', '').strip()
                ad = request.form.get('ad', '').strip()
                soyad = request.form.get('soyad', '').strip()
                email = request.form.get('email', '').strip()
                telefon = request.form.get('telefon', '').strip()
                yeni_sifre = request.form.get('yeni_sifre', '').strip()
                
                # Validasyon
                if not all([kullanici_adi, ad, soyad]):
                    flash('Kullanıcı adı, ad ve soyad zorunludur!', 'error')
                    return redirect(url_for('admin_duzenle', admin_id=admin_id))
                
                # Kullanıcı adı kontrolü (başka biri kullanıyor mu?)
                mevcut = Kullanici.query.filter(
                    Kullanici.kullanici_adi == kullanici_adi,
                    Kullanici.id != admin_id
                ).first()
                if mevcut:
                    flash('Bu kullanıcı adı başka biri tarafından kullanılıyor!', 'error')
                    return redirect(url_for('admin_duzenle', admin_id=admin_id))
                
                # Güncelle
                degisiklikler = []
                if admin.kullanici_adi != kullanici_adi:
                    degisiklikler.append(f"Kullanıcı adı: {admin.kullanici_adi} → {kullanici_adi}")
                    admin.kullanici_adi = kullanici_adi
                
                if admin.ad != ad:
                    degisiklikler.append(f"Ad: {admin.ad} → {ad}")
                    admin.ad = ad
                
                if admin.soyad != soyad:
                    degisiklikler.append(f"Soyad: {admin.soyad} → {soyad}")
                    admin.soyad = soyad
                
                if admin.email != email:
                    degisiklikler.append("Email güncellendi")
                    admin.email = email if email else None
                
                if admin.telefon != telefon:
                    degisiklikler.append("Telefon güncellendi")
                    admin.telefon = telefon if telefon else None
                
                # Şifre değişikliği
                if yeni_sifre:
                    from werkzeug.security import generate_password_hash
                    admin.sifre = generate_password_hash(yeni_sifre)
                    degisiklikler.append("Şifre güncellendi")
                
                db.session.commit()
                
                # Audit log
                if degisiklikler:
                    from flask import session
                    audit = AuditLog(
                        kullanici_id=session.get('kullanici_id'),
                        kullanici_adi=session.get('kullanici_adi'),
                        kullanici_rol=session.get('kullanici_rol'),
                        islem_tipi='update',
                        tablo_adi='kullanicilar',
                        kayit_id=admin.id,
                        degisiklik_ozeti=f"Admin güncellendi: {', '.join(degisiklikler)}",
                        ip_adresi=request.remote_addr,
                        user_agent=request.headers.get('User-Agent'),
                        basarili=True
                    )
                    db.session.add(audit)
                    db.session.commit()
                
                flash('Admin kullanıcısı başarıyla güncellendi!', 'success')
                return redirect(url_for('admin_ata'))
            
            return render_template('sistem_yoneticisi/admin_duzenle.html', admin=admin)
            
        except Exception as e:
            logger.error(f"Admin düzenle hatası: {str(e)}")
            db.session.rollback()
            flash('Bir hata oluştu!', 'error')
            return redirect(url_for('admin_ata'))
    
    
    @app.route('/admin-sil/<int:admin_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_sil(admin_id):
        """Admin kullanıcısını pasif yap"""
        try:
            from flask import session
            
            # Kendi kendini silemesin
            if admin_id == session.get('kullanici_id'):
                flash('Kendi hesabınızı silemezsiniz!', 'error')
                return redirect(url_for('admin_ata'))
            
            admin = Kullanici.query.get_or_404(admin_id)
            
            # Sadece admin rolündeki kullanıcılar silinebilir
            if admin.rol != 'admin':
                flash('Bu kullanıcı admin değil!', 'error')
                return redirect(url_for('admin_ata'))
            
            # Pasif yap (silme)
            admin.aktif = False
            db.session.commit()
            
            # Audit log
            audit = AuditLog(
                kullanici_id=session.get('kullanici_id'),
                kullanici_adi=session.get('kullanici_adi'),
                kullanici_rol=session.get('kullanici_rol'),
                islem_tipi='delete',
                tablo_adi='kullanicilar',
                kayit_id=admin.id,
                degisiklik_ozeti=f'Admin kullanıcısı pasif yapıldı: {admin.kullanici_adi}',
                ip_adresi=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                basarili=True
            )
            db.session.add(audit)
            db.session.commit()
            
            flash(f'{admin.kullanici_adi} admin kullanıcısı pasif yapıldı!', 'success')
            return redirect(url_for('admin_ata'))
            
        except Exception as e:
            logger.error(f"Admin sil hatası: {str(e)}")
            db.session.rollback()
            flash('Bir hata oluştu!', 'error')
            return redirect(url_for('admin_ata'))

    
    @app.route('/depo-sorumlusu-duzenle/<int:kullanici_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def depo_sorumlusu_duzenle(kullanici_id):
        """Depo sorumlusu düzenle (çoklu otel)"""
        from models import Otel, KullaniciOtel
        from werkzeug.security import generate_password_hash
        from flask import session
        
        try:
            kullanici = Kullanici.query.get_or_404(kullanici_id)
            
            # Sadece depo sorumlusu düzenlenebilir
            if kullanici.rol != 'depo_sorumlusu':
                flash('Bu kullanıcı depo sorumlusu değil!', 'error')
                return redirect(url_for('personel_tanimla'))
            
            # Otelleri yükle
            oteller = db.session.query(Otel).filter_by(aktif=True).order_by(Otel.ad).all()
            
            if request.method == 'POST':
                kullanici_adi = request.form.get('kullanici_adi', '').strip()
                ad = request.form.get('ad', '').strip()
                soyad = request.form.get('soyad', '').strip()
                otel_ids = request.form.getlist('otel_ids')
                yeni_sifre = request.form.get('yeni_sifre', '').strip()
                
                # Validasyon
                if not all([kullanici_adi, ad, soyad]):
                    flash('Kullanıcı adı, ad ve soyad zorunludur!', 'error')
                    return redirect(url_for('depo_sorumlusu_duzenle', kullanici_id=kullanici_id))
                
                if not otel_ids:
                    flash('En az bir otel seçilmelidir!', 'error')
                    return redirect(url_for('depo_sorumlusu_duzenle', kullanici_id=kullanici_id))
                
                # Kullanıcı adı kontrolü
                mevcut = Kullanici.query.filter(
                    Kullanici.kullanici_adi == kullanici_adi,
                    Kullanici.id != kullanici_id
                ).first()
                if mevcut:
                    flash('Bu kullanıcı adı başka biri tarafından kullanılıyor!', 'error')
                    return redirect(url_for('depo_sorumlusu_duzenle', kullanici_id=kullanici_id))
                
                # Güncelle
                degisiklikler = []
                if kullanici.kullanici_adi != kullanici_adi:
                    degisiklikler.append(f"Kullanıcı adı: {kullanici.kullanici_adi} → {kullanici_adi}")
                    kullanici.kullanici_adi = kullanici_adi
                
                if kullanici.ad != ad:
                    degisiklikler.append(f"Ad: {kullanici.ad} → {ad}")
                    kullanici.ad = ad
                
                if kullanici.soyad != soyad:
                    degisiklikler.append(f"Soyad: {kullanici.soyad} → {soyad}")
                    kullanici.soyad = soyad
                
                # Otel atamalarını güncelle
                KullaniciOtel.query.filter_by(kullanici_id=kullanici_id).delete()
                for otel_id in otel_ids:
                    atama = KullaniciOtel(kullanici_id=kullanici_id, otel_id=int(otel_id))
                    db.session.add(atama)
                degisiklikler.append("Otel atamaları güncellendi")
                
                # Şifre değişikliği
                if yeni_sifre:
                    kullanici.sifre = generate_password_hash(yeni_sifre)
                    degisiklikler.append("Şifre güncellendi")
                
                db.session.commit()
                
                # Audit log
                if degisiklikler:
                    audit = AuditLog(
                        kullanici_id=session.get('kullanici_id'),
                        kullanici_adi=session.get('kullanici_adi'),
                        kullanici_rol=session.get('kullanici_rol'),
                        islem_tipi='update',
                        tablo_adi='kullanicilar',
                        kayit_id=kullanici.id,
                        degisiklik_ozeti=f"Depo sorumlusu güncellendi: {', '.join(degisiklikler)}",
                        ip_adresi=request.remote_addr,
                        user_agent=request.headers.get('User-Agent'),
                        basarili=True
                    )
                    db.session.add(audit)
                    db.session.commit()
                
                flash('Depo sorumlusu başarıyla güncellendi!', 'success')
                return redirect(url_for('personel_tanimla'))
            
            # Mevcut otel atamalarını al
            mevcut_otel_ids = [atama.otel_id for atama in kullanici.atanan_oteller]
            
            return render_template('admin/depo_sorumlusu_duzenle.html', 
                                 kullanici=kullanici, 
                                 oteller=oteller,
                                 mevcut_otel_ids=mevcut_otel_ids)
            
        except Exception as e:
            logger.error(f"Depo sorumlusu düzenle hatası: {str(e)}")
            db.session.rollback()
            flash('Bir hata oluştu!', 'error')
            return redirect(url_for('personel_tanimla'))