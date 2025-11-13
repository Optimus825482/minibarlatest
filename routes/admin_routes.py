"""
Admin Route'ları

Bu modül admin rolü ile ilgili endpoint'leri içerir.

Endpoint'ler:
- /personel-tanimla - Personel tanımlama ve listeleme
- /personel-duzenle/<int:personel_id> - Personel düzenleme
- /personel-pasif-yap/<int:personel_id> - Personel pasif yapma
- /personel-aktif-yap/<int:personel_id> - Personel aktif yapma
- /urun-gruplari - Ürün grupları tanımlama ve listeleme
- /grup-duzenle/<int:grup_id> - Ürün grubu düzenleme
- /grup-sil/<int:grup_id> - Ürün grubu silme
- /grup-pasif-yap/<int:grup_id> - Ürün grubu pasif yapma
- /grup-aktif-yap/<int:grup_id> - Ürün grubu aktif yapma
- /urunler - Ürün tanımlama ve listeleme
- /urun-duzenle/<int:urun_id> - Ürün düzenleme
- /urun-sil/<int:urun_id> - Ürün silme
- /urun-pasif-yap/<int:urun_id> - Ürün pasif yapma
- /urun-aktif-yap/<int:urun_id> - Ürün aktif yapma

Roller:
- sistem_yoneticisi
- admin
"""

from flask import render_template, request, redirect, url_for, flash, session
from models import db, Kullanici, UrunGrup, Urun, StokHareket
from utils.decorators import login_required, role_required
from utils.helpers import log_islem, log_hata
from utils.audit import audit_create, audit_update, audit_delete, serialize_model


def register_admin_routes(app):
    """Admin route'larını kaydet"""
    
    # ============================================================================
    # PERSONEL YÖNETİMİ
    # ============================================================================
    
    @app.route('/personel-tanimla', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def personel_tanimla():
        """Personel tanımlama ve listeleme - Rol bazlı form gösterimi"""
        from forms import PersonelForm, DepoSorumlusuForm, KatSorumlusuForm
        from models import Otel, KullaniciOtel
        from sqlalchemy.exc import IntegrityError
        from flask import jsonify
        from werkzeug.security import generate_password_hash

        # AJAX POST isteği kontrolü
        if request.method == 'POST' and request.is_json:
            try:
                data = request.get_json()
                
                # Validasyon
                required_fields = ['kullanici_adi', 'sifre', 'ad', 'soyad', 'rol']
                for field in required_fields:
                    if not data.get(field):
                        return jsonify({'success': False, 'message': f'{field} zorunludur'}), 400
                
                # Kullanıcı adı kontrolü
                if Kullanici.query.filter_by(kullanici_adi=data['kullanici_adi']).first():
                    return jsonify({'success': False, 'message': 'Bu kullanıcı adı zaten kullanılıyor'}), 400
                
                # Yeni kullanıcı oluştur
                yeni_kullanici = Kullanici(
                    kullanici_adi=data['kullanici_adi'],
                    sifre=generate_password_hash(data['sifre']),
                    ad=data['ad'],
                    soyad=data['soyad'],
                    rol=data['rol'],
                    aktif=True
                )
                
                db.session.add(yeni_kullanici)
                db.session.flush()
                
                # Rol bazlı işlemler
                if data['rol'] == 'depo_sorumlusu':
                    otel_ids = data.get('otel_ids', [])
                    if not otel_ids:
                        db.session.rollback()
                        return jsonify({'success': False, 'message': 'Depo sorumlusu için en az bir otel seçilmelidir'}), 400
                    
                    for otel_id in otel_ids:
                        atama = KullaniciOtel(
                            kullanici_id=yeni_kullanici.id,
                            otel_id=int(otel_id)
                        )
                        db.session.add(atama)
                
                elif data['rol'] == 'kat_sorumlusu':
                    otel_id = data.get('otel_id')
                    if not otel_id:
                        db.session.rollback()
                        return jsonify({'success': False, 'message': 'Kat sorumlusu için otel seçilmelidir'}), 400
                    
                    yeni_kullanici.otel_id = int(otel_id)
                    
                    # Depo sorumlusu opsiyonel
                    depo_sorumlusu_id = data.get('depo_sorumlusu_id')
                    if depo_sorumlusu_id:
                        yeni_kullanici.depo_sorumlusu_id = int(depo_sorumlusu_id)
                
                db.session.commit()
                
                # Audit Trail
                audit_create('kullanici', yeni_kullanici.id, yeni_kullanici)
                
                return jsonify({'success': True, 'message': 'Kullanıcı başarıyla eklendi'}), 200
                
            except Exception as e:
                db.session.rollback()
                log_hata(e, modul='personel_tanimla_ajax')
                return jsonify({'success': False, 'message': 'Bir hata oluştu'}), 500

        # Rol seçimi için basit form
        rol_secimi = request.form.get('rol_secimi') or request.args.get('rol')
        
        # Otelleri yükle
        oteller = Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()
        
        form = None
        if rol_secimi == 'depo_sorumlusu':
            form = DepoSorumlusuForm()
            form.otel_ids.choices = [(o.id, o.ad) for o in oteller]
        elif rol_secimi == 'kat_sorumlusu':
            form = KatSorumlusuForm()
            form.otel_id.choices = [(0, 'Otel Seçin...')] + [(o.id, o.ad) for o in oteller]
            # Depo sorumlularını yükle
            depo_sorumlular = Kullanici.query.filter_by(rol='depo_sorumlusu', aktif=True).order_by(Kullanici.ad, Kullanici.soyad).all()
            form.depo_sorumlusu_id.choices = [(0, 'Seçiniz (Opsiyonel)')] + [(d.id, f"{d.ad} {d.soyad}") for d in depo_sorumlular]
        else:
            form = PersonelForm()

        if form and form.validate_on_submit():
            try:
                # Ortak alanlar
                personel = Kullanici(
                    kullanici_adi=form.kullanici_adi.data,
                    ad=form.ad.data,
                    soyad=form.soyad.data,
                    email=form.email.data or '',
                    telefon=form.telefon.data or '',
                    aktif=form.aktif.data if hasattr(form, 'aktif') else True
                )
                
                # Rol bazlı işlemler
                if rol_secimi == 'depo_sorumlusu':
                    personel.rol = 'depo_sorumlusu'
                    personel.sifre_belirle(form.sifre.data)
                    db.session.add(personel)
                    db.session.flush()
                    
                    # Çoklu otel ataması
                    for otel_id in form.otel_ids.data:
                        atama = KullaniciOtel(
                            kullanici_id=personel.id,
                            otel_id=otel_id
                        )
                        db.session.add(atama)
                    
                elif rol_secimi == 'kat_sorumlusu':
                    personel.rol = 'kat_sorumlusu'
                    personel.otel_id = form.otel_id.data
                    personel.depo_sorumlusu_id = form.depo_sorumlusu_id.data if form.depo_sorumlusu_id.data != 0 else None
                    personel.sifre_belirle(form.sifre.data)
                    db.session.add(personel)
                    
                else:
                    personel.rol = form.rol.data
                    personel.sifre_belirle(form.sifre.data)
                    db.session.add(personel)
                
                db.session.commit()

                # Audit Trail
                audit_create('kullanici', personel.id, personel)

                flash('Kullanıcı başarıyla eklendi.', 'success')
                return redirect(url_for('personel_tanimla'))

            except IntegrityError as e:
                db.session.rollback()
                error_msg = str(e)
                if 'kullanici_adi' in error_msg:
                    flash('Bu kullanıcı adı zaten kullanılıyor.', 'danger')
                elif 'email' in error_msg:
                    flash('Bu e-posta adresi zaten kullanılıyor.', 'danger')
                else:
                    flash('Kayıt sırasında bir hata oluştu.', 'danger')
                log_hata(e, modul='personel_tanimla')

            except Exception as e:
                db.session.rollback()
                flash('Beklenmeyen bir hata oluştu.', 'danger')
                log_hata(e, modul='personel_tanimla')

        # Personel listesi - otel bilgileri ile
        personeller = Kullanici.query.filter(
            Kullanici.rol.in_(['admin', 'depo_sorumlusu', 'kat_sorumlusu']),
            Kullanici.aktif.is_(True)
        ).order_by(Kullanici.olusturma_tarihi.desc()).all()
        
        # Her personel için otel bilgilerini hazırla
        personel_data = []
        for p in personeller:
            try:
                otel_bilgisi = ''
                if p.rol == 'depo_sorumlusu':
                    oteller_list = [atama.otel.ad for atama in p.atanan_oteller]
                    otel_bilgisi = ', '.join(oteller_list) if oteller_list else '-'
                elif p.rol == 'kat_sorumlusu':
                    otel_bilgisi = p.otel.ad if p.otel else '-'
                else:
                    otel_bilgisi = 'Tüm Oteller'
                
                personel_data.append({
                    'personel': p,
                    'otel_bilgisi': otel_bilgisi
                })
            except Exception as e:
                # Hata durumunda bile kullanıcıyı listeye ekle
                logger.error(f"Otel bilgisi hazırlanırken hata: {p.kullanici_adi} - {str(e)}")
                personel_data.append({
                    'personel': p,
                    'otel_bilgisi': '⚠️ Hata'
                })
        
        return render_template('admin/personel_tanimla.html', 
                             form=form, 
                             personel_data=personel_data,
                             rol_secimi=rol_secimi,
                             oteller=oteller)

    @app.route('/personel-duzenle/<int:personel_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def personel_duzenle(personel_id):
        """Personel düzenleme - Rol bazlı form gösterimi"""
        from forms import PersonelDuzenleForm, DepoSorumlusuDuzenleForm, KatSorumlusuDuzenleForm
        from models import Otel, KullaniciOtel
        from sqlalchemy.exc import IntegrityError

        personel = Kullanici.query.get_or_404(personel_id)
        
        # Otelleri yükle
        oteller = Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()
        
        # Rol bazlı form seçimi
        if personel.rol == 'depo_sorumlusu':
            form = DepoSorumlusuDuzenleForm(obj=personel)
            form.otel_ids.choices = [(o.id, o.ad) for o in oteller]
            # Mevcut otel atamalarını yükle
            if request.method == 'GET':
                mevcut_oteller = [atama.otel_id for atama in personel.atanan_oteller]
                form.otel_ids.data = mevcut_oteller
        elif personel.rol == 'kat_sorumlusu':
            form = KatSorumlusuDuzenleForm(obj=personel)
            form.otel_id.choices = [(0, 'Otel Seçin...')] + [(o.id, o.ad) for o in oteller]
            # Depo sorumlularını yükle
            depo_sorumlular = Kullanici.query.filter_by(rol='depo_sorumlusu', aktif=True).order_by(Kullanici.ad, Kullanici.soyad).all()
            form.depo_sorumlusu_id.choices = [(0, 'Seçiniz (Opsiyonel)')] + [(d.id, f"{d.ad} {d.soyad}") for d in depo_sorumlular]
        else:
            form = PersonelDuzenleForm(obj=personel)

        if form.validate_on_submit():
            try:
                # Eski değerleri kaydet
                eski_deger = serialize_model(personel)

                personel.kullanici_adi = form.kullanici_adi.data
                personel.ad = form.ad.data
                personel.soyad = form.soyad.data
                personel.email = form.email.data or ''
                personel.telefon = form.telefon.data or ''
                
                # Rol değişikliği (sadece PersonelDuzenleForm'da)
                if hasattr(form, 'rol'):
                    personel.rol = form.rol.data
                
                # Otel atamaları güncelle
                if personel.rol == 'depo_sorumlusu' and hasattr(form, 'otel_ids'):
                    # Mevcut atamaları sil
                    KullaniciOtel.query.filter_by(kullanici_id=personel.id).delete()
                    # Yeni atamaları ekle
                    for otel_id in form.otel_ids.data:
                        atama = KullaniciOtel(
                            kullanici_id=personel.id,
                            otel_id=otel_id
                        )
                        db.session.add(atama)
                
                elif personel.rol == 'kat_sorumlusu' and hasattr(form, 'otel_id'):
                    personel.otel_id = form.otel_id.data
                    personel.depo_sorumlusu_id = form.depo_sorumlusu_id.data if form.depo_sorumlusu_id.data != 0 else None

                # Şifre değiştirilmişse
                if form.yeni_sifre.data:
                    personel.sifre_belirle(form.yeni_sifre.data)

                db.session.commit()

                # Audit Trail
                audit_update('kullanici', personel.id, eski_deger, personel)

                flash('Kullanıcı başarıyla güncellendi.', 'success')
                return redirect(url_for('personel_tanimla'))

            except IntegrityError as e:
                db.session.rollback()
                error_msg = str(e)

                # Kullanıcı dostu hata mesajları
                if 'kullanici_adi' in error_msg:
                    flash('Bu kullanıcı adı zaten kullanılıyor. Lütfen farklı bir kullanıcı adı seçin.', 'danger')
                elif 'email' in error_msg:
                    flash('Bu e-posta adresi zaten kullanılıyor. Lütfen farklı bir e-posta adresi seçin.', 'danger')
                else:
                    flash('Güncelleme sırasında bir hata oluştu.', 'danger')
                log_hata(e, modul='personel_duzenle')

            except Exception as e:
                db.session.rollback()
                flash('Beklenmeyen bir hata oluştu. Lütfen sistem yöneticisine başvurun.', 'danger')
                log_hata(e, modul='personel_duzenle')

        return render_template('admin/personel_duzenle.html', form=form, personel=personel, oteller=oteller)

    @app.route('/personel-pasif-yap/<int:personel_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def personel_pasif_yap(personel_id):
        """Personel pasif yapma"""
        try:
            personel = Kullanici.query.get_or_404(personel_id)
            eski_deger = serialize_model(personel)
            personel.aktif = False
            db.session.commit()
            
            # Audit Trail
            audit_update('kullanici', personel.id, eski_deger, personel)
            
            flash('Kullanıcı başarıyla pasif yapıldı.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('personel_tanimla'))

    @app.route('/personel-aktif-yap/<int:personel_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def personel_aktif_yap(personel_id):
        """Personel aktif yapma"""
        try:
            personel = Kullanici.query.get_or_404(personel_id)
            eski_deger = serialize_model(personel)
            personel.aktif = True
            db.session.commit()
            
            # Audit Trail
            audit_update('kullanici', personel.id, eski_deger, personel)
            
            flash('Kullanıcı başarıyla aktif yapıldı.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('personel_tanimla'))

    # ============================================================================
    # ÜRÜN GRUBU YÖNETİMİ
    # ============================================================================

    @app.route('/urun-gruplari', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def urun_gruplari():
        """Ürün grupları tanımlama ve listeleme"""
        from forms import UrunGrupForm
        from sqlalchemy.exc import IntegrityError

        form = UrunGrupForm()

        if form.validate_on_submit():
            try:
                grup = UrunGrup(
                    grup_adi=form.grup_adi.data,
                    aciklama=form.aciklama.data or ''
                )
                db.session.add(grup)
                db.session.commit()

                # Audit Trail
                audit_create('urun_grup', grup.id, grup)

                flash('Ürün grubu başarıyla eklendi.', 'success')
                return redirect(url_for('urun_gruplari'))

            except IntegrityError as e:
                db.session.rollback()
                flash('Bu grup adı zaten kullanılıyor. Lütfen farklı bir ad girin.', 'danger')
                log_hata(e, modul='urun_gruplari')

            except Exception as e:
                db.session.rollback()
                flash('Beklenmeyen bir hata oluştu. Lütfen sistem yöneticisine başvurun.', 'danger')
                log_hata(e, modul='urun_gruplari')

        gruplar = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
        return render_template('admin/urun_gruplari.html', form=form, gruplar=gruplar)

    @app.route('/grup-duzenle/<int:grup_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def grup_duzenle(grup_id):
        """Ürün grubu düzenleme"""
        from forms import UrunGrupForm
        from sqlalchemy.exc import IntegrityError

        grup = UrunGrup.query.get_or_404(grup_id)
        form = UrunGrupForm(obj=grup)

        if form.validate_on_submit():
            try:
                eski_deger = serialize_model(grup)
                grup.grup_adi = form.grup_adi.data
                grup.aciklama = form.aciklama.data or ''
                db.session.commit()

                # Audit Trail
                audit_update('urun_grup', grup.id, eski_deger, grup)

                flash('Ürün grubu başarıyla güncellendi.', 'success')
                return redirect(url_for('urun_gruplari'))

            except IntegrityError as e:
                db.session.rollback()
                flash('Bu grup adı zaten kullanılıyor. Lütfen farklı bir ad girin.', 'danger')
                log_hata(e, modul='grup_duzenle')

            except Exception as e:
                db.session.rollback()
                flash('Beklenmeyen bir hata oluştu. Lütfen sistem yöneticisine başvurun.', 'danger')
                log_hata(e, modul='grup_duzenle')

        return render_template('admin/grup_duzenle.html', form=form, grup=grup)

    @app.route('/grup-sil/<int:grup_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def grup_sil(grup_id):
        """Ürün grubu silme"""
        try:
            grup = UrunGrup.query.get_or_404(grup_id)
            
            # Gruba ait ürün var mı kontrol et
            urun_sayisi = Urun.query.filter_by(grup_id=grup_id).count()
            if urun_sayisi > 0:
                flash(f'Bu gruba ait {urun_sayisi} ürün bulunmaktadır. Önce ürünleri silin veya başka gruba taşıyın.', 'danger')
                return redirect(url_for('urun_gruplari'))
            
            eski_deger = serialize_model(grup)
            db.session.delete(grup)
            db.session.commit()
            
            # Audit Trail
            audit_delete('urun_grup', grup_id, eski_deger)
            
            flash('Ürün grubu başarıyla silindi.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('urun_gruplari'))

    @app.route('/grup-pasif-yap/<int:grup_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def grup_pasif_yap(grup_id):
        """Ürün grubu pasif yapma"""
        try:
            grup = UrunGrup.query.get_or_404(grup_id)
            eski_deger = serialize_model(grup)
            grup.aktif = False
            db.session.commit()
            
            # Audit Trail
            audit_update('urun_grup', grup.id, eski_deger, grup)
            
            flash('Ürün grubu başarıyla pasif yapıldı.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('urun_gruplari'))

    @app.route('/grup-aktif-yap/<int:grup_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def grup_aktif_yap(grup_id):
        """Ürün grubu aktif yapma"""
        try:
            grup = UrunGrup.query.get_or_404(grup_id)
            eski_deger = serialize_model(grup)
            grup.aktif = True
            db.session.commit()
            
            # Audit Trail
            audit_update('urun_grup', grup.id, eski_deger, grup)
            
            flash('Ürün grubu başarıyla aktif yapıldı.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('urun_gruplari'))

    # ============================================================================
    # ÜRÜN YÖNETİMİ
    # ============================================================================

    @app.route('/urunler', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def urunler():
        """Ürün tanımlama ve listeleme"""
        from forms import UrunForm
        from sqlalchemy.exc import IntegrityError

        # Grup seçeneklerini doldur (form oluşturmadan önce)
        gruplar = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
        grup_choices = [(g.id, g.grup_adi) for g in gruplar]
        
        form = UrunForm()
        form.grup_id.choices = grup_choices

        if form.validate_on_submit():
            try:
                urun = Urun(
                    grup_id=form.grup_id.data,
                    urun_adi=form.urun_adi.data,
                    barkod=form.barkod.data or None,
                    birim=form.birim.data or 'Adet',
                    kritik_stok_seviyesi=form.kritik_stok_seviyesi.data or 10
                )
                db.session.add(urun)
                db.session.commit()

                # Audit Trail
                audit_create('urun', urun.id, urun)

                # Log kaydı
                log_islem('ekleme', 'urun', {
                    'urun_adi': urun.urun_adi,
                    'barkod': urun.barkod,
                    'grup_id': urun.grup_id,
                    'birim': urun.birim
                })

                flash('Ürün başarıyla eklendi.', 'success')
                return redirect(url_for('urunler'))

            except IntegrityError as e:
                db.session.rollback()
                error_msg = str(e)
                if 'barkod' in error_msg:
                    flash('Bu barkod numarası zaten kullanılıyor. Lütfen farklı bir barkod girin veya boş bırakın.', 'danger')
                else:
                    flash('Kayıt sırasında bir hata oluştu.', 'danger')
                log_hata(e, modul='urunler')

            except Exception as e:
                db.session.rollback()
                flash('Beklenmeyen bir hata oluştu. Lütfen sistem yöneticisine başvurun.', 'danger')
                log_hata(e, modul='urunler')

        # Tüm ürünleri getir (aktif ve pasif)
        urunler = Urun.query.order_by(Urun.aktif.desc(), Urun.urun_adi).all()
        return render_template('admin/urunler.html', form=form, gruplar=gruplar, urunler=urunler)

    @app.route('/urun-duzenle/<int:urun_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def urun_duzenle(urun_id):
        """Ürün düzenleme"""
        from forms import UrunForm
        from sqlalchemy.exc import IntegrityError

        urun = Urun.query.get_or_404(urun_id)
        gruplar = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
        grup_choices = [(g.id, g.grup_adi) for g in gruplar]

        form = UrunForm(obj=urun)
        form.grup_id.choices = grup_choices

        if form.validate_on_submit():
            try:
                # Eski değerleri kaydet
                eski_deger = serialize_model(urun)
                eski_urun_adi = urun.urun_adi

                urun.urun_adi = form.urun_adi.data
                urun.grup_id = form.grup_id.data
                urun.barkod = form.barkod.data or None
                urun.birim = form.birim.data or 'Adet'
                urun.kritik_stok_seviyesi = form.kritik_stok_seviyesi.data or 10

                db.session.commit()

                # Audit Trail
                audit_update('urun', urun.id, eski_deger, urun)

                # Log kaydı
                log_islem('guncelleme', 'urun', {
                    'urun_id': urun.id,
                    'eski_urun_adi': eski_urun_adi,
                    'yeni_urun_adi': urun.urun_adi,
                    'barkod': urun.barkod
                })

                flash('Ürün başarıyla güncellendi.', 'success')
                return redirect(url_for('urunler'))

            except IntegrityError as e:
                db.session.rollback()
                error_msg = str(e)
                if 'barkod' in error_msg:
                    flash('Bu barkod numarası zaten kullanılıyor. Lütfen farklı bir barkod girin veya boş bırakın.', 'danger')
                else:
                    flash('Güncelleme sırasında bir hata oluştu.', 'danger')
                log_hata(e, modul='urun_duzenle')

            except Exception as e:
                db.session.rollback()
                flash('Beklenmeyen bir hata oluştu. Lütfen sistem yöneticisine başvurun.', 'danger')
                log_hata(e, modul='urun_duzenle')

        return render_template('admin/urun_duzenle.html', form=form, urun=urun, gruplar=gruplar)

    @app.route('/urun-sil/<int:urun_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def urun_sil(urun_id):
        """Ürün silme"""
        try:
            urun = Urun.query.get_or_404(urun_id)
            urun_adi = urun.urun_adi
            
            # Ürüne ait stok hareketi var mı kontrol et
            stok_hareketi = StokHareket.query.filter_by(urun_id=urun_id).first()
            if stok_hareketi:
                flash('Bu ürüne ait stok hareketi bulunmaktadır. Ürün silinemez.', 'danger')
                return redirect(url_for('urunler'))
            
            # Eski değerleri kaydet (silme öncesi)
            eski_deger = serialize_model(urun)
            
            db.session.delete(urun)
            db.session.commit()
            
            # Audit Trail
            audit_delete('urun', urun_id, eski_deger)
            
            # Log kaydı
            log_islem('silme', 'urun', {
                'urun_id': urun_id,
                'urun_adi': urun_adi
            })
            
            flash('Ürün başarıyla silindi.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('urunler'))

    @app.route('/urun-pasif-yap/<int:urun_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def urun_pasif_yap(urun_id):
        """Ürün pasif yapma"""
        try:
            urun = Urun.query.get_or_404(urun_id)
            eski_deger = serialize_model(urun)
            urun.aktif = False
            db.session.commit()
            
            # Audit Trail
            audit_update('urun', urun.id, eski_deger, urun)
            
            flash('Ürün başarıyla pasif yapıldı.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('urunler'))

    @app.route('/urun-aktif-yap/<int:urun_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def urun_aktif_yap(urun_id):
        """Ürün aktif yapma"""
        try:
            urun = Urun.query.get_or_404(urun_id)
            eski_deger = serialize_model(urun)
            urun.aktif = True
            db.session.commit()
            
            # Audit Trail
            audit_update('urun', urun.id, eski_deger, urun)
            
            flash('Ürün başarıyla aktif yapıldı.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('urunler'))


    # ============================================================================
    # OTEL YÖNETİMİ
    # ============================================================================
    
    @app.route('/oteller', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def otel_listesi():
        """Otel listesi"""
        try:
            from models import Otel, Kat, Oda
            from sqlalchemy import func
            
            # Pagination
            page = request.args.get('page', 1, type=int)
            per_page = 20
            
            # Otel listesi ile kat ve oda sayılarını al
            oteller_query = db.session.query(
                Otel,
                func.count(Kat.id.distinct()).label('kat_sayisi'),
                func.count(Oda.id.distinct()).label('oda_sayisi')
            ).outerjoin(Kat, Otel.id == Kat.otel_id)\
             .outerjoin(Oda, Kat.id == Oda.kat_id)\
             .group_by(Otel.id)\
             .order_by(Otel.olusturma_tarihi.desc())
            
            pagination = oteller_query.paginate(page=page, per_page=per_page, error_out=False)
            
            # Her otel için personel sayılarını hesapla
            oteller_data = []
            for otel, kat_sayisi, oda_sayisi in pagination.items:
                depo_sorumlu_sayisi = otel.get_depo_sorumlu_sayisi()
                kat_sorumlu_sayisi = otel.get_kat_sorumlu_sayisi()
                
                oteller_data.append({
                    'otel': otel,
                    'kat_sayisi': kat_sayisi,
                    'oda_sayisi': oda_sayisi,
                    'personel_sayisi': depo_sorumlu_sayisi + kat_sorumlu_sayisi
                })
            
            return render_template('admin/otel_listesi.html', 
                                 oteller_data=oteller_data,
                                 pagination=pagination)
                                 
        except Exception as e:
            flash(f'Hata oluştu: {str(e)}', 'danger')
            log_hata(e, modul='otel_listesi')
            return redirect(url_for('dashboard'))
    
    @app.route('/oteller/ekle', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def otel_ekle():
        """Otel ekleme"""
        from forms import OtelForm
        from models import Otel
        from sqlalchemy.exc import IntegrityError
        
        form = OtelForm()
        
        if form.validate_on_submit():
            try:
                otel = Otel(
                    ad=form.ad.data,
                    adres=form.adres.data or '',
                    telefon=form.telefon.data or '',
                    email=form.email.data or '',
                    vergi_no=form.vergi_no.data or '',
                    aktif=form.aktif.data
                )
                db.session.add(otel)
                db.session.commit()
                
                # Audit Trail
                audit_create('otel', otel.id, otel)
                
                flash('Otel başarıyla eklendi.', 'success')
                log_islem('ekleme', 'otel', f'Otel eklendi: {otel.ad}')
                return redirect(url_for('otel_listesi'))
                
            except IntegrityError as e:
                db.session.rollback()
                flash('Bu otel adı zaten kullanılıyor. Lütfen farklı bir ad seçin.', 'danger')
                log_hata(e, modul='otel_ekle')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Hata oluştu: {str(e)}', 'danger')
                log_hata(e, modul='otel_ekle')
        
        return render_template('admin/otel_ekle.html', form=form)
    
    @app.route('/oteller/<int:id>/duzenle', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def otel_duzenle(id):
        """Otel düzenleme"""
        from forms import OtelForm
        from models import Otel
        
        otel = Otel.query.get_or_404(id)
        form = OtelForm(obj=otel)
        
        if form.validate_on_submit():
            try:
                eski_deger = serialize_model(otel)
                
                # Logo işleme
                import base64
                if form.logo.data:
                    logo_file = form.logo.data
                    logo_bytes = logo_file.read()
                    otel.logo = base64.b64encode(logo_bytes).decode('utf-8')
                
                otel.ad = form.ad.data
                otel.adres = form.adres.data or ''
                otel.telefon = form.telefon.data or ''
                otel.email = form.email.data or ''
                otel.vergi_no = form.vergi_no.data or ''
                otel.aktif = form.aktif.data
                
                db.session.commit()
                
                # Audit Trail
                audit_update('otel', otel.id, eski_deger, otel)
                
                flash('Otel başarıyla güncellendi.', 'success')
                log_islem('guncelleme', 'otel', f'Otel güncellendi: {otel.ad}')
                return redirect(url_for('otel_listesi'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Hata oluştu: {str(e)}', 'danger')
                log_hata(e, modul='otel_duzenle')
        
        return render_template('admin/otel_duzenle.html', form=form, otel=otel)
    
    @app.route('/oteller/<int:id>/aktif-pasif', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def otel_aktif_pasif(id):
        """Otel aktif/pasif yapma"""
        from models import Otel
        
        try:
            otel = Otel.query.get_or_404(id)
            eski_deger = serialize_model(otel)
            
            # Otele ait kat var mı kontrol et
            if otel.katlar and not otel.aktif:
                flash('Bu otele ait katlar bulunuyor. Önce katları silin veya başka otele taşıyın!', 'warning')
                return redirect(url_for('otel_listesi'))
            
            # Otele atanmış personel var mı kontrol et
            depo_sorumlu_sayisi = otel.get_depo_sorumlu_sayisi()
            kat_sorumlu_sayisi = otel.get_kat_sorumlu_sayisi()
            
            if (depo_sorumlu_sayisi > 0 or kat_sorumlu_sayisi > 0) and not otel.aktif:
                flash('Bu otele atanmış personel bulunuyor. Önce personel atamalarını kaldırın!', 'warning')
                return redirect(url_for('otel_listesi'))
            
            # Aktif/Pasif değiştir
            otel.aktif = not otel.aktif
            db.session.commit()
            
            # Audit Trail
            audit_update('otel', otel.id, eski_deger, otel)
            
            durum = 'aktif' if otel.aktif else 'pasif'
            flash(f'Otel başarıyla {durum} yapıldı.', 'success')
            log_islem('guncelleme', 'otel', f'Otel {durum} yapıldı: {otel.ad}')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Hata oluştu: {str(e)}', 'danger')
            log_hata(e, modul='otel_aktif_pasif')
        
        return redirect(url_for('otel_listesi'))




    # ============================================================================
    # FİYAT YÖNETİMİ UI
    # ============================================================================
    
    @app.route('/urun-fiyat-yonetimi', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin', 'depo_sorumlusu')
    def urun_fiyat_yonetimi():
        """
        Ürün fiyat yönetimi sayfası
        
        Özellikler:
        - Fiyat güncelleme formu
        - Tedarikçi seçimi
        - Güncel fiyatlar tablosu
        - Fiyat geçmişi tablosu
        """
        try:
            from models import Urun, Tedarikci, Otel
            
            # Aktif ürünleri getir
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            # Aktif tedarikçileri getir
            tedarikciler = Tedarikci.query.filter_by(aktif=True).order_by(Tedarikci.tedarikci_adi).all()
            
            # Otelleri getir (filtre için)
            oteller = Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()
            
            log_islem('goruntuleme', 'urun_fiyat_yonetimi', 'Fiyat yönetimi sayfası görüntülendi')
            
            return render_template(
                'admin/urun_fiyat_yonetimi.html',
                urunler=urunler,
                tedarikciler=tedarikciler,
                oteller=oteller
            )
            
        except Exception as e:
            log_hata(e, modul='urun_fiyat_yonetimi')
            flash('Sayfa yüklenirken bir hata oluştu', 'danger')
            return redirect(url_for('sistem_yoneticisi_dashboard'))
    
    
    @app.route('/karlilik-dashboard', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def karlilik_dashboard():
        """
        Karlılık dashboard sayfası
        
        Özellikler:
        - Özet kartlar (Günlük kar, Aylık kar, Kar marjı, ROI)
        - Trend grafikleri
        - En karlı ürünler tablosu
        """
        try:
            from models import Otel
            
            # Otelleri getir (filtre için)
            oteller = Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()
            
            log_islem('goruntuleme', 'karlilik_dashboard', 'Karlılık dashboard görüntülendi')
            
            return render_template(
                'admin/karlilik_dashboard.html',
                oteller=oteller
            )
            
        except Exception as e:
            log_hata(e, modul='karlilik_dashboard')
            flash('Sayfa yüklenirken bir hata oluştu', 'danger')
            return redirect(url_for('sistem_yoneticisi_dashboard'))
    
    
    @app.route('/kampanya-yonetimi', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def kampanya_yonetimi():
        """
        Kampanya yönetimi sayfası
        
        Özellikler:
        - Kampanya oluşturma formu
        - Aktif kampanyalar tablosu
        - Kampanya performans metrikleri
        - Tüm kampanyalar listesi
        """
        try:
            from models import Urun, Tedarikci
            
            # Ürünleri getir (kampanya için)
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            # Tedarikçileri getir
            tedarikciler = Tedarikci.query.filter_by(aktif=True).order_by(Tedarikci.tedarikci_adi).all()
            
            log_islem('goruntuleme', 'kampanya_yonetimi', 'Kampanya yönetimi sayfası görüntülendi')
            
            return render_template(
                'admin/kampanya_yonetimi.html',
                urunler=urunler,
                tedarikciler=tedarikciler
            )
            
        except Exception as e:
            log_hata(e, modul='kampanya_yonetimi')
            flash('Sayfa yüklenirken bir hata oluştu', 'danger')
            return redirect(url_for('sistem_yoneticisi_dashboard'))
    
    
    @app.route('/bedelsiz-limit-yonetimi', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def bedelsiz_limit_yonetimi():
        """
        Bedelsiz limit yönetimi sayfası
        
        Özellikler:
        - Limit tanımlama formu
        - Oda bazlı limit listesi
        - Kullanım takibi
        - Limit tipi yönetimi (misafir, kampanya, personel)
        """
        try:
            from models import Oda, Urun, Kampanya, Otel
            
            # Aktif odaları getir
            odalar = Oda.query.filter_by(aktif=True).order_by(Oda.oda_no).all()
            
            # Aktif ürünleri getir
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            # Aktif kampanyaları getir
            kampanyalar = Kampanya.query.filter_by(aktif=True).order_by(Kampanya.kampanya_adi).all()
            
            # Otelleri getir (filtre için)
            oteller = Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()
            
            log_islem('goruntuleme', 'bedelsiz_limit_yonetimi', 'Bedelsiz limit yönetimi sayfası görüntülendi')
            
            return render_template(
                'admin/bedelsiz_limit_yonetimi.html',
                odalar=odalar,
                urunler=urunler,
                kampanyalar=kampanyalar,
                oteller=oteller
            )
            
        except Exception as e:
            log_hata(e, modul='bedelsiz_limit_yonetimi')
            flash('Sayfa yüklenirken bir hata oluştu', 'danger')
            return redirect(url_for('sistem_yoneticisi_dashboard'))
