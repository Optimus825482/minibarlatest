"""
Sistem Yöneticisi Route'ları

Bu modül sistem yöneticisi ve admin rolüne ait endpoint'leri içerir.

Endpoint'ler:
- /sistem-loglari - Sistem logları
- /otel-tanimla - Otel bilgileri
- /kat-tanimla - Kat tanımlama
- /kat-duzenle/<int:kat_id> - Kat düzenleme
- /kat-sil/<int:kat_id> - Kat silme
- /oda-tanimla - Oda tanımlama
- /oda-duzenle/<int:oda_id> - Oda düzenleme
- /oda-sil/<int:oda_id> - Oda silme

Roller:
- sistem_yoneticisi
- admin
"""

from flask import render_template, request, redirect, url_for, flash, session
from datetime import datetime, date
from models import db, Otel, Kat, Oda, Kullanici, SistemLog
from utils.decorators import login_required, role_required
from utils.helpers import log_islem, log_hata
from utils.audit import audit_create, audit_update, audit_delete, serialize_model


def register_sistem_yoneticisi_routes(app):
    """Sistem yöneticisi route'larını kaydet"""
    
    @app.route('/sistem-loglari')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def sistem_loglari():
        """Sistem logları listesi"""
        # Sayfa parametreleri
        sayfa = request.args.get('sayfa', 1, type=int)
        limit = 50
        
        # Filtreler
        islem_tipi = request.args.get('islem_tipi', '')
        modul = request.args.get('modul', '')
        kullanici_id = request.args.get('kullanici_id', type=int)
        
        # Sorgu oluştur
        query = SistemLog.query
        
        if islem_tipi:
            query = query.filter(SistemLog.islem_tipi == islem_tipi)
        if modul:
            query = query.filter(SistemLog.modul == modul)
        if kullanici_id:
            query = query.filter(SistemLog.kullanici_id == kullanici_id)
        
        # Sayfalama
        loglar = query.order_by(SistemLog.islem_tarihi.desc()).paginate(
            page=sayfa, per_page=limit, error_out=False
        )
        
        # Filtre seçenekleri
        kullanicilar = Kullanici.query.filter(Kullanici.aktif.is_(True)).order_by(Kullanici.ad, Kullanici.soyad).all()
        
        return render_template('sistem_yoneticisi/sistem_loglari.html',
                             loglar=loglar,
                             kullanicilar=kullanicilar,
                             islem_tipi=islem_tipi,
                             modul=modul,
                             kullanici_id=kullanici_id)
    
    
    @app.route('/otel-tanimla', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def otel_tanimla():
        """Otel bilgileri tanımlama/düzenleme"""
        from forms import OtelForm
        
        otel = Otel.query.first()
        form = OtelForm(obj=otel)
        
        if form.validate_on_submit():
            try:
                # Logo işleme
                import base64
                logo_data = None
                if form.logo.data:
                    logo_file = form.logo.data
                    logo_bytes = logo_file.read()
                    logo_data = base64.b64encode(logo_bytes).decode('utf-8')
                
                if otel:
                    # Eski değeri sakla
                    eski_deger = serialize_model(otel)
                    
                    # Güncelle
                    otel.ad = form.ad.data
                    otel.adres = form.adres.data
                    otel.telefon = form.telefon.data
                    otel.email = form.email.data
                    otel.vergi_no = form.vergi_no.data or ''
                    
                    # Logo güncelle (sadece yeni logo yüklendiyse)
                    if logo_data:
                        otel.logo = logo_data
                    
                    # Audit log
                    audit_update(
                        tablo_adi='oteller',
                        kayit_id=otel.id,
                        eski_deger=eski_deger,
                        yeni_deger=serialize_model(otel),
                        aciklama='Otel bilgileri güncellendi'
                    )
                else:
                    # Yeni oluştur
                    otel = Otel(
                        ad=form.ad.data,
                        adres=form.adres.data,
                        telefon=form.telefon.data,
                        email=form.email.data,
                        vergi_no=form.vergi_no.data or '',
                        logo=logo_data
                    )
                    db.session.add(otel)
                    db.session.flush()
                    
                    # Audit log
                    audit_create(
                        tablo_adi='oteller',
                        kayit_id=otel.id,
                        yeni_deger=serialize_model(otel),
                        aciklama='Otel bilgileri oluşturuldu'
                    )
                
                db.session.commit()
                
                # Log kaydı
                log_islem('guncelleme' if otel else 'ekleme', 'otel', {
                    'otel_id': otel.id,
                    'otel_adi': otel.ad
                })
                
                flash('Otel bilgileri başarıyla kaydedildi.', 'success')
                return redirect(url_for('otel_tanimla'))
            except Exception as e:
                db.session.rollback()
                log_hata(e, modul='otel_tanimla')
                flash('Otel bilgileri kaydedilirken hata oluştu.', 'danger')
        
        return render_template('sistem_yoneticisi/otel_tanimla.html', otel=otel, form=form)
    
    
    @app.route('/kat-tanimla', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def kat_tanimla():
        """Kat tanımlama"""
        from forms import KatForm
        from models import Otel
        
        form = KatForm()
        
        # Otel listesini form'a yükle
        form.otel_id.choices = [(0, 'Otel Seçin...')] + [(o.id, o.ad) for o in Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()]
        
        if form.validate_on_submit():
            try:
                # Otel seçimi kontrolü
                if not form.otel_id.data or form.otel_id.data == 0:
                    flash('Lütfen bir otel seçin!', 'danger')
                    return render_template('sistem_yoneticisi/kat_tanimla.html', katlar=[], form=form)
                
                kat = Kat(
                    otel_id=form.otel_id.data,
                    kat_adi=form.kat_adi.data,
                    kat_no=form.kat_no.data,
                    aciklama=form.aciklama.data,
                    aktif=form.aktif.data
                )
                db.session.add(kat)
                db.session.flush()
                
                # Audit log
                audit_create(
                    tablo_adi='katlar',
                    kayit_id=kat.id,
                    yeni_deger=serialize_model(kat),
                    aciklama=f'Kat oluşturuldu - {kat.kat_adi}'
                )
                
                db.session.commit()
                
                # Log kaydı
                log_islem('ekleme', 'kat', {
                    'kat_id': kat.id,
                    'otel_id': kat.otel_id,
                    'kat_adi': kat.kat_adi,
                    'kat_no': kat.kat_no
                })
                
                flash(f'{kat.kat_adi} başarıyla eklendi.', 'success')
                return redirect(url_for('kat_tanimla'))
            except Exception as e:
                db.session.rollback()
                log_hata(e, modul='kat_tanimla')
                flash('Kat eklenirken hata oluştu.', 'danger')
        
        # Mevcut katları listele (otel bilgisi ile)
        katlar = Kat.query.filter_by(aktif=True).order_by(Kat.kat_no).all()
        
        return render_template('sistem_yoneticisi/kat_tanimla.html', katlar=katlar, form=form)
    
    
    @app.route('/kat-duzenle/<int:kat_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def kat_duzenle(kat_id):
        """Kat düzenleme"""
        from forms import KatForm
        from models import Otel
        
        kat = db.session.get(Kat, kat_id)
        if not kat:
            flash('Kat bulunamadı.', 'danger')
            return redirect(url_for('kat_tanimla'))
        
        # Eski değeri sakla
        eski_deger = serialize_model(kat)
        
        form = KatForm(obj=kat)
        
        # Otel listesini form'a yükle
        form.otel_id.choices = [(o.id, o.ad) for o in Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()]
        
        if form.validate_on_submit():
            try:
                kat.otel_id = form.otel_id.data
                kat.kat_adi = form.kat_adi.data
                kat.kat_no = form.kat_no.data
                kat.aciklama = form.aciklama.data
                kat.aktif = form.aktif.data
                
                db.session.commit()
                
                # Audit log
                audit_update(
                    tablo_adi='katlar',
                    kayit_id=kat.id,
                    eski_deger=eski_deger,
                    yeni_deger=serialize_model(kat),
                    aciklama=f'Kat güncellendi - {kat.kat_adi}'
                )
                
                # Log kaydı
                log_islem('guncelleme', 'kat', {
                    'kat_id': kat.id,
                    'kat_adi': kat.kat_adi
                })
                
                flash(f'{kat.kat_adi} başarıyla güncellendi.', 'success')
                return redirect(url_for('kat_tanimla'))
            except Exception as e:
                db.session.rollback()
                log_hata(e, modul='kat_duzenle')
                flash('Kat güncellenirken hata oluştu.', 'danger')
        
        return render_template('sistem_yoneticisi/kat_duzenle.html', kat=kat, form=form)
    
    
    @app.route('/kat-sil/<int:kat_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def kat_sil(kat_id):
        """Kat silme (pasif yapma)"""
        try:
            kat = db.session.get(Kat, kat_id)
            if not kat:
                flash('Kat bulunamadı.', 'danger')
                return redirect(url_for('kat_tanimla'))
            
            # Eski değeri sakla
            eski_deger = serialize_model(kat)
            
            # Pasif yap
            kat.aktif = False
            db.session.commit()
            
            # Audit log
            audit_delete(
                tablo_adi='katlar',
                kayit_id=kat.id,
                eski_deger=eski_deger,
                aciklama=f'Kat pasif yapıldı - {kat.kat_adi}'
            )
            
            # Log kaydı
            log_islem('silme', 'kat', {
                'kat_id': kat.id,
                'kat_adi': kat.kat_adi
            })
            
            flash(f'{kat.kat_adi} başarıyla silindi.', 'success')
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='kat_sil')
            flash('Kat silinirken hata oluştu.', 'danger')
        
        return redirect(url_for('kat_tanimla'))
    
    
    @app.route('/oda-tanimla', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def oda_tanimla():
        """Oda tanımlama"""
        from forms import OdaForm
        from models import Otel
        from flask import send_file
        from datetime import datetime
        import io
        
        # Excel export kontrolü
        export_format = request.args.get('format', '')
        if export_format == 'excel':
            try:
                from openpyxl import Workbook
                from openpyxl.styles import Font, Alignment, PatternFill
                
                # Tüm odaları getir
                odalar = Oda.query.options(
                    db.joinedload(Oda.kat).joinedload(Kat.otel)
                ).filter_by(aktif=True).order_by(Oda.oda_no).all()
                
                # Excel workbook oluştur
                wb = Workbook()
                ws = wb.active
                ws.title = "Odalar"
                
                # Başlık satırı
                headers = ['Otel Adı', 'Kat No', 'Oda No']
                ws.append(headers)
                
                # Başlık stilini ayarla
                header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                header_font = Font(bold=True, color="FFFFFF")
                
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                
                # Veri satırları
                for oda in odalar:
                    otel_adi = oda.kat.otel.ad if oda.kat and oda.kat.otel else '-'
                    kat_no = oda.kat.kat_no if oda.kat else '-'
                    
                    ws.append([
                        otel_adi,
                        kat_no,
                        oda.oda_no
                    ])
                
                # Sütun genişliklerini ayarla
                ws.column_dimensions['A'].width = 30
                ws.column_dimensions['B'].width = 15
                ws.column_dimensions['C'].width = 15
                
                # Excel dosyasını memory'ye kaydet
                excel_buffer = io.BytesIO()
                wb.save(excel_buffer)
                excel_buffer.seek(0)
                
                filename = f'odalar_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                
                # Log kaydı
                log_islem('export', 'odalar', {
                    'format': 'excel',
                    'kayit_sayisi': len(odalar)
                })
                
                return send_file(
                    excel_buffer,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
            except Exception as e:
                log_hata(e, modul='oda_tanimla_excel')
                flash('Excel dosyası oluşturulamadı.', 'danger')
                return redirect(url_for('oda_tanimla'))
        
        form = OdaForm()
        
        # Otel listesini form'a yükle
        oteller = Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()
        form.otel_id.choices = [(0, 'Otel Seçin...')] + [(o.id, o.ad) for o in oteller]
        form.kat_id.choices = [(0, 'Önce otel seçin...')]
        
        if form.validate_on_submit():
            try:
                # Otel ve kat seçimi kontrolü
                if not form.otel_id.data or form.otel_id.data == 0:
                    flash('Lütfen bir otel seçin!', 'danger')
                    return render_template('sistem_yoneticisi/oda_tanimla.html', katlar=[], odalar=[], form=form)
                
                if not form.kat_id.data or form.kat_id.data == 0:
                    flash('Lütfen bir kat seçin!', 'danger')
                    return render_template('sistem_yoneticisi/oda_tanimla.html', katlar=[], odalar=[], form=form)
                
                # Kat'ın seçilen otele ait olduğunu kontrol et
                kat = Kat.query.get(form.kat_id.data)
                if not kat or kat.otel_id != form.otel_id.data:
                    flash('Seçilen kat, seçilen otele ait değil!', 'danger')
                    return render_template('sistem_yoneticisi/oda_tanimla.html', katlar=[], odalar=[], form=form)
                
                oda = Oda(
                    oda_no=form.oda_no.data,
                    kat_id=form.kat_id.data,
                    oda_tipi=form.oda_tipi.data,
                    kapasite=form.kapasite.data,
                    aktif=form.aktif.data
                )
                db.session.add(oda)
                db.session.flush()
                
                # Audit log
                audit_create(
                    tablo_adi='odalar',
                    kayit_id=oda.id,
                    yeni_deger=serialize_model(oda),
                    aciklama=f'Oda oluşturuldu - {oda.oda_no}'
                )
                
                db.session.commit()
                
                # Log kaydı
                log_islem('ekleme', 'oda', {
                    'oda_id': oda.id,
                    'oda_no': oda.oda_no,
                    'kat_id': oda.kat_id
                })
                
                flash(f'Oda {oda.oda_no} başarıyla eklendi.', 'success')
                return redirect(url_for('oda_tanimla'))
            except Exception as e:
                db.session.rollback()
                log_hata(e, modul='oda_tanimla')
                flash('Oda eklenirken hata oluştu.', 'danger')
        
        # Katlar ve odalar (eager loading ile otel bilgisini de çek)
        katlar = Kat.query.filter_by(aktif=True).order_by(Kat.kat_no).all()
        odalar = Oda.query.options(
            db.joinedload(Oda.kat).joinedload(Kat.otel)
        ).filter_by(aktif=True).order_by(Oda.oda_no).all()
        
        return render_template('sistem_yoneticisi/oda_tanimla.html', katlar=katlar, odalar=odalar, form=form, oteller=oteller)
    
    
    @app.route('/oda-duzenle/<int:oda_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def oda_duzenle(oda_id):
        """Oda düzenleme"""
        from forms import OdaForm
        from models import Otel
        
        oda = db.session.get(Oda, oda_id)
        if not oda:
            flash('Oda bulunamadı.', 'danger')
            return redirect(url_for('oda_tanimla'))
        
        # Eski değeri sakla
        eski_deger = serialize_model(oda)
        
        form = OdaForm(obj=oda)
        
        # Otel listesini yükle
        oteller = Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()
        form.otel_id.choices = [(o.id, o.ad) for o in oteller]
        
        # Mevcut otel seçimini ayarla
        if oda.kat and oda.kat.otel_id:
            form.otel_id.data = oda.kat.otel_id
        
        # Kat listesini yükle (mevcut otel için)
        if oda.kat:
            katlar = Kat.query.filter_by(otel_id=oda.kat.otel_id, aktif=True).order_by(Kat.kat_no).all()
            form.kat_id.choices = [(k.id, k.kat_adi) for k in katlar]
        
        if form.validate_on_submit():
            try:
                # Kat'ın seçilen otele ait olduğunu kontrol et
                kat = Kat.query.get(form.kat_id.data)
                if not kat or kat.otel_id != form.otel_id.data:
                    flash('Seçilen kat, seçilen otele ait değil!', 'danger')
                    return render_template('sistem_yoneticisi/oda_duzenle.html', oda=oda, form=form, oteller=oteller)
                
                oda.oda_no = form.oda_no.data
                oda.kat_id = form.kat_id.data
                oda.oda_tipi = form.oda_tipi.data
                oda.kapasite = form.kapasite.data
                oda.aktif = form.aktif.data
                
                db.session.commit()
                
                # Audit log
                audit_update(
                    tablo_adi='odalar',
                    kayit_id=oda.id,
                    eski_deger=eski_deger,
                    yeni_deger=serialize_model(oda),
                    aciklama=f'Oda güncellendi - {oda.oda_no}'
                )
                
                # Log kaydı
                log_islem('guncelleme', 'oda', {
                    'oda_id': oda.id,
                    'oda_no': oda.oda_no
                })
                
                flash(f'Oda {oda.oda_no} başarıyla güncellendi.', 'success')
                return redirect(url_for('oda_tanimla'))
            except Exception as e:
                db.session.rollback()
                log_hata(e, modul='oda_duzenle')
                flash('Oda güncellenirken hata oluştu.', 'danger')
        
        return render_template('sistem_yoneticisi/oda_duzenle.html', oda=oda, form=form, oteller=oteller)
    
    
    @app.route('/oda-sil/<int:oda_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def oda_sil(oda_id):
        """Oda silme (pasif yapma)"""
        try:
            oda = db.session.get(Oda, oda_id)
            if not oda:
                flash('Oda bulunamadı.', 'danger')
                return redirect(url_for('oda_tanimla'))
            
            # Eski değeri sakla
            eski_deger = serialize_model(oda)
            
            # Pasif yap
            oda.aktif = False
            db.session.commit()
            
            # Audit log
            audit_delete(
                tablo_adi='odalar',
                kayit_id=oda.id,
                eski_deger=eski_deger,
                aciklama=f'Oda pasif yapıldı - {oda.oda_no}'
            )
            
            # Log kaydı
            log_islem('silme', 'oda', {
                'oda_id': oda.id,
                'oda_no': oda.oda_no
            })
            
            flash(f'Oda {oda.oda_no} başarıyla silindi.', 'success')
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='oda_sil')
            flash('Oda silinirken hata oluştu.', 'danger')
        
        return redirect(url_for('oda_tanimla'))
    
    
    # ============================================================================
    # TEDARİKÇİ YÖNETİMİ ROUTE'LARI
    # ============================================================================
    
    @app.route('/tedarikci-yonetimi', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def tedarikci_yonetimi():
        """Tedarikçi tanımlama ve listeleme"""
        from forms import TedarikciForm
        from models import Tedarikci
        from utils.tedarikci_servisleri import TedarikciServisi
        from flask import session
        
        form = TedarikciForm()
        
        if form.validate_on_submit():
            try:
                # Tedarikçi verilerini hazırla
                tedarikci_data = {
                    'tedarikci_adi': form.tedarikci_adi.data,
                    'telefon': form.telefon.data,
                    'email': form.email.data,
                    'adres': form.adres.data,
                    'vergi_no': form.vergi_no.data,
                    'odeme_kosullari': form.odeme_kosullari.data,
                    'aktif': form.aktif.data
                }
                
                # Tedarikçi oluştur
                sonuc = TedarikciServisi.tedarikci_olustur(
                    tedarikci_data=tedarikci_data,
                    kullanici_id=session.get('kullanici_id')
                )
                
                if sonuc['success']:
                    flash(sonuc['message'], 'success')
                    return redirect(url_for('tedarikci_yonetimi'))
                else:
                    flash(sonuc['message'], 'danger')
                    
            except Exception as e:
                db.session.rollback()
                log_hata(e, modul='tedarikci_yonetimi')
                flash('Tedarikçi eklenirken hata oluştu.', 'danger')
        
        # Tedarikçi listesini getir
        try:
            # Filtre parametreleri
            aktif_filtre = request.args.get('aktif', 'true')
            arama = request.args.get('arama', '')
            
            # Sorgu oluştur
            query = Tedarikci.query
            
            # Aktif/pasif filtresi
            if aktif_filtre == 'true':
                query = query.filter(Tedarikci.aktif.is_(True))
            elif aktif_filtre == 'false':
                query = query.filter(Tedarikci.aktif.is_(False))
            # 'all' ise filtre uygulanmaz
            
            # Arama filtresi
            if arama:
                arama_pattern = f'%{arama}%'
                query = query.filter(
                    db.or_(
                        Tedarikci.tedarikci_adi.ilike(arama_pattern),
                        Tedarikci.telefon.ilike(arama_pattern),
                        Tedarikci.email.ilike(arama_pattern)
                    )
                )
            
            # Sayfalama
            sayfa = request.args.get('sayfa', 1, type=int)
            per_page = 20
            tedarikciler = query.order_by(Tedarikci.tedarikci_adi).paginate(
                page=sayfa, per_page=per_page, error_out=False
            )
            
        except Exception as e:
            log_hata(e, modul='tedarikci_yonetimi_listele')
            tedarikciler = None
            flash('Tedarikçi listesi yüklenirken hata oluştu.', 'danger')
        
        return render_template('sistem_yoneticisi/tedarikci_yonetimi.html',
                             form=form,
                             tedarikciler=tedarikciler,
                             aktif_filtre=aktif_filtre,
                             arama=arama)
    
    
    @app.route('/tedarikci-duzenle/<int:tedarikci_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def tedarikci_duzenle(tedarikci_id):
        """Tedarikçi bilgilerini düzenle"""
        from forms import TedarikciForm
        from models import Tedarikci
        from utils.tedarikci_servisleri import TedarikciServisi
        
        tedarikci = db.session.get(Tedarikci, tedarikci_id)
        if not tedarikci:
            flash('Tedarikçi bulunamadı.', 'danger')
            return redirect(url_for('tedarikci_yonetimi'))
        
        form = TedarikciForm(obj=tedarikci)
        
        if form.validate_on_submit():
            try:
                # Güncellenecek verileri hazırla
                tedarikci_data = {
                    'tedarikci_adi': form.tedarikci_adi.data,
                    'telefon': form.telefon.data,
                    'email': form.email.data,
                    'adres': form.adres.data,
                    'vergi_no': form.vergi_no.data,
                    'odeme_kosullari': form.odeme_kosullari.data,
                    'aktif': form.aktif.data
                }
                
                # Tedarikçi güncelle
                if TedarikciServisi.tedarikci_guncelle(tedarikci_id, tedarikci_data):
                    flash('Tedarikçi bilgileri başarıyla güncellendi.', 'success')
                    return redirect(url_for('tedarikci_yonetimi'))
                else:
                    flash('Tedarikçi güncellenirken hata oluştu.', 'danger')
                    
            except Exception as e:
                db.session.rollback()
                log_hata(e, modul='tedarikci_duzenle')
                flash('Tedarikçi güncellenirken hata oluştu.', 'danger')
        
        return render_template('sistem_yoneticisi/tedarikci_duzenle.html',
                             tedarikci=tedarikci,
                             form=form)
    
    
    @app.route('/tedarikci-pasif-yap/<int:tedarikci_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def tedarikci_pasif_yap(tedarikci_id):
        """Tedarikçiyi pasif yap"""
        from models import Tedarikci, SatinAlmaSiparisi
        
        try:
            tedarikci = db.session.get(Tedarikci, tedarikci_id)
            if not tedarikci:
                flash('Tedarikçi bulunamadı.', 'danger')
                return redirect(url_for('tedarikci_yonetimi'))
            
            # Aktif sipariş kontrolü
            aktif_siparis_sayisi = SatinAlmaSiparisi.query.filter(
                SatinAlmaSiparisi.tedarikci_id == tedarikci_id,
                SatinAlmaSiparisi.durum.in_(['beklemede', 'onaylandi', 'kısmi_teslim'])
            ).count()
            
            if aktif_siparis_sayisi > 0:
                flash(f'Tedarikçinin {aktif_siparis_sayisi} adet aktif siparişi bulunmaktadır. Önce siparişleri tamamlayın.', 'warning')
                return redirect(url_for('tedarikci_yonetimi'))
            
            # Eski değeri sakla
            eski_deger = serialize_model(tedarikci)
            
            # Pasif yap
            tedarikci.aktif = False
            db.session.commit()
            
            # Audit log
            audit_update(
                tablo_adi='tedarikciler',
                kayit_id=tedarikci.id,
                eski_deger=eski_deger,
                yeni_deger=serialize_model(tedarikci),
                aciklama=f'Tedarikçi pasif yapıldı - {tedarikci.tedarikci_adi}'
            )
            
            # Log kaydı
            log_islem('guncelleme', 'tedarikci', {
                'tedarikci_id': tedarikci.id,
                'tedarikci_adi': tedarikci.tedarikci_adi,
                'islem': 'pasif_yap'
            })
            
            flash(f'{tedarikci.tedarikci_adi} başarıyla pasif yapıldı.', 'success')
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='tedarikci_pasif_yap')
            flash('Tedarikçi pasif yapılırken hata oluştu.', 'danger')
        
        return redirect(url_for('tedarikci_yonetimi'))
    
    
    @app.route('/tedarikci-aktif-yap/<int:tedarikci_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def tedarikci_aktif_yap(tedarikci_id):
        """Tedarikçiyi aktif yap"""
        from models import Tedarikci
        
        try:
            tedarikci = db.session.get(Tedarikci, tedarikci_id)
            if not tedarikci:
                flash('Tedarikçi bulunamadı.', 'danger')
                return redirect(url_for('tedarikci_yonetimi'))
            
            # Eski değeri sakla
            eski_deger = serialize_model(tedarikci)
            
            # Aktif yap
            tedarikci.aktif = True
            db.session.commit()
            
            # Audit log
            audit_update(
                tablo_adi='tedarikciler',
                kayit_id=tedarikci.id,
                eski_deger=eski_deger,
                yeni_deger=serialize_model(tedarikci),
                aciklama=f'Tedarikçi aktif yapıldı - {tedarikci.tedarikci_adi}'
            )
            
            # Log kaydı
            log_islem('guncelleme', 'tedarikci', {
                'tedarikci_id': tedarikci.id,
                'tedarikci_adi': tedarikci.tedarikci_adi,
                'islem': 'aktif_yap'
            })
            
            flash(f'{tedarikci.tedarikci_adi} başarıyla aktif yapıldı.', 'success')
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='tedarikci_aktif_yap')
            flash('Tedarikçi aktif yapılırken hata oluştu.', 'danger')
        
        return redirect(url_for('tedarikci_yonetimi'))
    
    
    # ============================================================================
    # ÜRÜN-TEDARİKÇİ FİYAT YÖNETİMİ ROUTE'LARI
    # ============================================================================
    
    @app.route('/urun-tedarikci-fiyat', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def urun_tedarikci_fiyat():
        """Ürün-tedarikçi fiyat tanımlama ve listeleme"""
        from forms import UrunTedarikciFiyatForm
        from models import UrunTedarikciFiyat, Urun, Tedarikci
        from datetime import date
        from flask import session
        
        form = UrunTedarikciFiyatForm()
        
        # Form seçeneklerini doldur
        form.urun_id.choices = [(0, 'Ürün Seçin...')] + [
            (u.id, f'{u.urun_adi} ({u.barkod})') 
            for u in Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
        ]
        form.tedarikci_id.choices = [(0, 'Tedarikçi Seçin...')] + [
            (t.id, t.tedarikci_adi) 
            for t in Tedarikci.query.filter_by(aktif=True).order_by(Tedarikci.tedarikci_adi).all()
        ]
        
        if form.validate_on_submit():
            try:
                # Ürün ve tedarikçi seçimi kontrolü
                if not form.urun_id.data or form.urun_id.data == 0:
                    flash('Lütfen bir ürün seçin!', 'danger')
                    return render_template('sistem_yoneticisi/urun_tedarikci_fiyat.html', 
                                         form=form, fiyatlar=None)
                
                if not form.tedarikci_id.data or form.tedarikci_id.data == 0:
                    flash('Lütfen bir tedarikçi seçin!', 'danger')
                    return render_template('sistem_yoneticisi/urun_tedarikci_fiyat.html', 
                                         form=form, fiyatlar=None)
                
                # Aynı ürün-tedarikçi için aktif fiyat var mı kontrol et
                mevcut_fiyat = UrunTedarikciFiyat.query.filter(
                    UrunTedarikciFiyat.urun_id == form.urun_id.data,
                    UrunTedarikciFiyat.tedarikci_id == form.tedarikci_id.data,
                    UrunTedarikciFiyat.aktif.is_(True),
                    db.or_(
                        UrunTedarikciFiyat.bitis_tarihi.is_(None),
                        UrunTedarikciFiyat.bitis_tarihi >= date.today()
                    )
                ).first()
                
                if mevcut_fiyat:
                    flash('Bu ürün-tedarikçi kombinasyonu için aktif bir fiyat zaten mevcut. Önce mevcut fiyatı güncelleyin veya pasif yapın.', 'warning')
                    return render_template('sistem_yoneticisi/urun_tedarikci_fiyat.html', 
                                         form=form, fiyatlar=None)
                
                # Yeni fiyat kaydı oluştur
                fiyat = UrunTedarikciFiyat(
                    urun_id=form.urun_id.data,
                    tedarikci_id=form.tedarikci_id.data,
                    alis_fiyati=form.alis_fiyati.data,
                    minimum_miktar=form.minimum_miktar.data,
                    baslangic_tarihi=form.baslangic_tarihi.data,
                    bitis_tarihi=form.bitis_tarihi.data,
                    aktif=form.aktif.data
                )
                db.session.add(fiyat)
                db.session.flush()
                
                # Audit log
                audit_create(
                    tablo_adi='urun_tedarikci_fiyat',
                    kayit_id=fiyat.id,
                    yeni_deger=serialize_model(fiyat),
                    aciklama=f'Ürün-tedarikçi fiyat oluşturuldu'
                )
                
                db.session.commit()
                
                # Cache invalidation - Yeni fiyat eklendiğinde ilgili cache'leri temizle
                try:
                    from utils.cache_manager import TedarikciCache
                    TedarikciCache.invalidate_fiyat_karsilastirma(fiyat.urun_id)
                    TedarikciCache.invalidate_en_uygun_tedarikci(fiyat.urun_id)
                    logger.debug(f"Ürün {fiyat.urun_id} için fiyat cache'leri temizlendi")
                except Exception as cache_error:
                    logger.warning(f"Cache temizleme hatası: {cache_error}")
                
                # Log kaydı
                log_islem('ekleme', 'urun_tedarikci_fiyat', {
                    'fiyat_id': fiyat.id,
                    'urun_id': fiyat.urun_id,
                    'tedarikci_id': fiyat.tedarikci_id,
                    'alis_fiyati': float(fiyat.alis_fiyati)
                })
                
                flash('Ürün-tedarikçi fiyat bilgisi başarıyla eklendi.', 'success')
                return redirect(url_for('urun_tedarikci_fiyat'))
                
            except Exception as e:
                db.session.rollback()
                log_hata(e, modul='urun_tedarikci_fiyat')
                flash('Fiyat bilgisi eklenirken hata oluştu.', 'danger')
        
        # Fiyat listesini getir
        try:
            # Filtre parametreleri
            urun_filtre = request.args.get('urun_id', type=int)
            tedarikci_filtre = request.args.get('tedarikci_id', type=int)
            aktif_filtre = request.args.get('aktif', 'true')
            
            # Sorgu oluştur (eager loading ile)
            query = UrunTedarikciFiyat.query.options(
                db.joinedload(UrunTedarikciFiyat.urun),
                db.joinedload(UrunTedarikciFiyat.tedarikci)
            )
            
            # Filtreler
            if urun_filtre:
                query = query.filter(UrunTedarikciFiyat.urun_id == urun_filtre)
            if tedarikci_filtre:
                query = query.filter(UrunTedarikciFiyat.tedarikci_id == tedarikci_filtre)
            if aktif_filtre == 'true':
                query = query.filter(UrunTedarikciFiyat.aktif.is_(True))
            elif aktif_filtre == 'false':
                query = query.filter(UrunTedarikciFiyat.aktif.is_(False))
            
            # Sayfalama
            sayfa = request.args.get('sayfa', 1, type=int)
            per_page = 20
            fiyatlar = query.order_by(
                UrunTedarikciFiyat.baslangic_tarihi.desc()
            ).paginate(page=sayfa, per_page=per_page, error_out=False)
            
        except Exception as e:
            log_hata(e, modul='urun_tedarikci_fiyat_listele')
            # Boş pagination objesi oluştur
            from flask_sqlalchemy.pagination import Pagination
            fiyatlar = Pagination(query=None, page=1, per_page=20, total=0, items=[])
            flash('Fiyat listesi yüklenirken hata oluştu.', 'danger')
        
        # Filtre için ürün ve tedarikçi listelerini hazırla
        urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
        tedarikciler = Tedarikci.query.filter_by(aktif=True).order_by(Tedarikci.tedarikci_adi).all()
        
        return render_template('sistem_yoneticisi/urun_tedarikci_fiyat.html',
                             form=form,
                             fiyatlar=fiyatlar,
                             urunler=urunler,
                             tedarikciler=tedarikciler,
                             urun_filtre=urun_filtre,
                             tedarikci_filtre=tedarikci_filtre,
                             aktif_filtre=aktif_filtre)
    
    
    @app.route('/fiyat-karsilastirma/<int:urun_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def fiyat_karsilastirma(urun_id):
        """Ürün için tedarikçi fiyat karşılaştırması"""
        from models import Urun, UrunTedarikciFiyat
        from datetime import date
        from utils.tedarikci_servisleri import TedarikciServisi
        
        try:
            # Ürün bilgisini getir
            urun = db.session.get(Urun, urun_id)
            if not urun:
                flash('Ürün bulunamadı.', 'danger')
                return redirect(url_for('urun_tedarikci_fiyat'))
            
            # Aktif fiyatları getir (performans bilgileri ile)
            fiyatlar = UrunTedarikciFiyat.query.options(
                db.joinedload(UrunTedarikciFiyat.tedarikci)
            ).filter(
                UrunTedarikciFiyat.urun_id == urun_id,
                UrunTedarikciFiyat.aktif.is_(True),
                db.or_(
                    UrunTedarikciFiyat.bitis_tarihi.is_(None),
                    UrunTedarikciFiyat.bitis_tarihi >= date.today()
                )
            ).order_by(UrunTedarikciFiyat.alis_fiyati).all()
            
            # Her tedarikçi için performans bilgilerini ekle
            fiyat_listesi = []
            for fiyat in fiyatlar:
                # Son 6 ay performans bilgisi
                from datetime import datetime, timedelta
                donem_bitis = date.today()
                donem_baslangic = donem_bitis - timedelta(days=180)
                
                performans = TedarikciServisi.tedarikci_performans_hesapla(
                    tedarikci_id=fiyat.tedarikci_id,
                    donem_baslangic=donem_baslangic,
                    donem_bitis=donem_bitis
                )
                
                fiyat_listesi.append({
                    'fiyat': fiyat,
                    'performans': performans
                })
            
            # En düşük fiyatı bul
            en_dusuk_fiyat = min([f['fiyat'].alis_fiyati for f in fiyat_listesi]) if fiyat_listesi else None
            
        except Exception as e:
            log_hata(e, modul='fiyat_karsilastirma')
            flash('Fiyat karşılaştırması yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('urun_tedarikci_fiyat'))
        
        return render_template('sistem_yoneticisi/fiyat_karsilastirma.html',
                             urun=urun,
                             fiyat_listesi=fiyat_listesi,
                             en_dusuk_fiyat=en_dusuk_fiyat)
    
    
    @app.route('/fiyat-guncelle/<int:fiyat_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def fiyat_guncelle(fiyat_id):
        """Ürün-tedarikçi fiyat güncelleme"""
        from models import UrunTedarikciFiyat
        from decimal import Decimal
        
        try:
            fiyat = db.session.get(UrunTedarikciFiyat, fiyat_id)
            if not fiyat:
                flash('Fiyat kaydı bulunamadı.', 'danger')
                return redirect(url_for('urun_tedarikci_fiyat'))
            
            # Form verilerini al
            yeni_alis_fiyati = request.form.get('alis_fiyati', type=Decimal)
            yeni_minimum_miktar = request.form.get('minimum_miktar', type=int)
            yeni_aktif = request.form.get('aktif') == 'true'
            
            if not yeni_alis_fiyati or yeni_alis_fiyati <= 0:
                flash('Geçerli bir alış fiyatı girin.', 'danger')
                return redirect(url_for('urun_tedarikci_fiyat'))
            
            if not yeni_minimum_miktar or yeni_minimum_miktar <= 0:
                flash('Geçerli bir minimum miktar girin.', 'danger')
                return redirect(url_for('urun_tedarikci_fiyat'))
            
            # Eski değeri sakla
            eski_deger = serialize_model(fiyat)
            
            # Güncelle
            fiyat.alis_fiyati = yeni_alis_fiyati
            fiyat.minimum_miktar = yeni_minimum_miktar
            fiyat.aktif = yeni_aktif
            
            db.session.commit()
            
            # Cache invalidation - Fiyat değiştiğinde ilgili cache'leri temizle
            try:
                from utils.cache_manager import TedarikciCache
                TedarikciCache.invalidate_fiyat_karsilastirma(fiyat.urun_id)
                TedarikciCache.invalidate_en_uygun_tedarikci(fiyat.urun_id)
                logger.debug(f"Ürün {fiyat.urun_id} için fiyat cache'leri temizlendi")
            except Exception as cache_error:
                logger.warning(f"Cache temizleme hatası: {cache_error}")
            
            # Audit log
            audit_update(
                tablo_adi='urun_tedarikci_fiyat',
                kayit_id=fiyat.id,
                eski_deger=eski_deger,
                yeni_deger=serialize_model(fiyat),
                aciklama=f'Ürün-tedarikçi fiyat güncellendi'
            )
            
            # Log kaydı
            log_islem('guncelleme', 'urun_tedarikci_fiyat', {
                'fiyat_id': fiyat.id,
                'urun_id': fiyat.urun_id,
                'tedarikci_id': fiyat.tedarikci_id,
                'yeni_fiyat': float(yeni_alis_fiyati)
            })
            
            flash('Fiyat bilgisi başarıyla güncellendi.', 'success')
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='fiyat_guncelle')
            flash('Fiyat güncellenirken hata oluştu.', 'danger')
        
        return redirect(url_for('urun_tedarikci_fiyat'))
    
    
    # ============================================================================
    # TEDARİKÇİ PERFORMANS ROUTE'LARI
    # ============================================================================
    
    @app.route('/tedarikci-performans/<int:tedarikci_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def tedarikci_performans(tedarikci_id):
        """Tedarikçi performans detay raporu"""
        from models import Tedarikci, SatinAlmaSiparisi
        from utils.tedarikci_servisleri import TedarikciServisi
        from datetime import date, timedelta
        
        try:
            # Tedarikçi bilgisini getir
            tedarikci = db.session.get(Tedarikci, tedarikci_id)
            if not tedarikci:
                flash('Tedarikçi bulunamadı.', 'danger')
                return redirect(url_for('tedarikci_yonetimi'))
            
            # Dönem parametreleri (varsayılan: son 6 ay)
            donem_ay = request.args.get('donem', 6, type=int)
            donem_bitis = date.today()
            donem_baslangic = donem_bitis - timedelta(days=donem_ay * 30)
            
            # Performans metriklerini hesapla
            performans = TedarikciServisi.tedarikci_performans_hesapla(
                tedarikci_id=tedarikci_id,
                donem_baslangic=donem_baslangic,
                donem_bitis=donem_bitis
            )
            
            # Sipariş geçmişini getir
            siparisler = SatinAlmaSiparisi.query.options(
                db.joinedload(SatinAlmaSiparisi.otel),
                db.joinedload(SatinAlmaSiparisi.detaylar)
            ).filter(
                SatinAlmaSiparisi.tedarikci_id == tedarikci_id,
                SatinAlmaSiparisi.siparis_tarihi >= donem_baslangic,
                SatinAlmaSiparisi.siparis_tarihi <= donem_bitis
            ).order_by(SatinAlmaSiparisi.siparis_tarihi.desc()).all()
            
            # Aylık performans trendi (grafik için)
            aylik_performans = []
            for i in range(donem_ay):
                ay_bitis = donem_bitis - timedelta(days=i * 30)
                ay_baslangic = ay_bitis - timedelta(days=30)
                
                ay_performans = TedarikciServisi.tedarikci_performans_hesapla(
                    tedarikci_id=tedarikci_id,
                    donem_baslangic=ay_baslangic,
                    donem_bitis=ay_bitis
                )
                
                aylik_performans.insert(0, {
                    'ay': ay_baslangic.strftime('%Y-%m'),
                    'performans_skoru': ay_performans.get('performans_skoru', 0),
                    'zamaninda_teslimat_orani': ay_performans.get('zamaninda_teslimat_orani', 0),
                    'toplam_siparis': ay_performans.get('toplam_siparis', 0)
                })
            
        except Exception as e:
            log_hata(e, modul='tedarikci_performans')
            flash('Performans raporu yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('tedarikci_yonetimi'))
        
        return render_template('sistem_yoneticisi/tedarikci_performans.html',
                             tedarikci=tedarikci,
                             performans=performans,
                             siparisler=siparisler,
                             aylik_performans=aylik_performans,
                             donem_ay=donem_ay,
                             donem_baslangic=donem_baslangic,
                             donem_bitis=donem_bitis)
    
    
    @app.route('/tedarikci-performans-raporu')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def tedarikci_performans_raporu():
        """Tüm tedarikçiler için karşılaştırmalı performans raporu"""
        from models import Tedarikci
        from utils.tedarikci_servisleri import TedarikciServisi
        from datetime import date, timedelta
        
        try:
            # Dönem parametreleri (varsayılan: son 6 ay)
            donem_ay = request.args.get('donem', 6, type=int)
            donem_bitis = date.today()
            donem_baslangic = donem_bitis - timedelta(days=donem_ay * 30)
            
            # Aktif tedarikçileri getir
            tedarikciler = Tedarikci.query.filter_by(aktif=True).order_by(Tedarikci.tedarikci_adi).all()
            
            # Her tedarikçi için performans hesapla
            performans_listesi = []
            for tedarikci in tedarikciler:
                performans = TedarikciServisi.tedarikci_performans_hesapla(
                    tedarikci_id=tedarikci.id,
                    donem_baslangic=donem_baslangic,
                    donem_bitis=donem_bitis
                )
                
                # Sadece sipariş geçmişi olan tedarikçileri ekle
                if performans.get('toplam_siparis', 0) > 0:
                    performans_listesi.append({
                        'tedarikci': tedarikci,
                        'performans': performans
                    })
            
            # Performans skoruna göre sırala (yüksekten düşüğe)
            performans_listesi.sort(
                key=lambda x: x['performans'].get('performans_skoru', 0),
                reverse=True
            )
            
            # İstatistikler
            if performans_listesi:
                ortalama_performans = sum(
                    p['performans'].get('performans_skoru', 0) 
                    for p in performans_listesi
                ) / len(performans_listesi)
                
                ortalama_teslimat_orani = sum(
                    p['performans'].get('zamaninda_teslimat_orani', 0) 
                    for p in performans_listesi
                ) / len(performans_listesi)
            else:
                ortalama_performans = 0
                ortalama_teslimat_orani = 0
            
        except Exception as e:
            log_hata(e, modul='tedarikci_performans_raporu')
            flash('Performans raporu yüklenirken hata oluştu.', 'danger')
            performans_listesi = []
            ortalama_performans = 0
            ortalama_teslimat_orani = 0
        
        return render_template('sistem_yoneticisi/tedarikci_performans_raporu.html',
                             performans_listesi=performans_listesi,
                             ortalama_performans=ortalama_performans,
                             ortalama_teslimat_orani=ortalama_teslimat_orani,
                             donem_ay=donem_ay,
                             donem_baslangic=donem_baslangic,
                             donem_bitis=donem_bitis)
    
    
    # ============================================================================
    # SİPARİŞ YÖNETİMİ ROUTE'LARI (SİSTEM YÖNETİCİSİ)
    # ============================================================================
    
    @app.route('/yonetici-siparis-listesi')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def yonetici_siparis_listesi():
        """Sistem yöneticisi için sipariş listesi ve onaylama"""
        from models import SatinAlmaSiparisi, Tedarikci, Urun, Otel
        from sqlalchemy import desc
        
        try:
            # Filtre parametreleri
            durum_filtre = request.args.get('durum')
            otel_filtre = request.args.get('otel_id', type=int)
            
            # Siparişleri getir
            query = SatinAlmaSiparisi.query.options(
                db.joinedload(SatinAlmaSiparisi.tedarikci),
                db.joinedload(SatinAlmaSiparisi.otel),
                db.joinedload(SatinAlmaSiparisi.olusturan)
            )
            
            if durum_filtre:
                query = query.filter_by(durum=durum_filtre)
            
            if otel_filtre:
                query = query.filter_by(otel_id=otel_filtre)
            
            siparisler = query.order_by(desc(SatinAlmaSiparisi.siparis_tarihi)).all()
            
            # İstatistikler
            istatistikler = {
                'toplam': len(siparisler),
                'beklemede': sum(1 for s in siparisler if s.durum == 'beklemede'),
                'onaylandi': sum(1 for s in siparisler if s.durum == 'onaylandi'),
                'teslim_alindi': sum(1 for s in siparisler if s.durum == 'teslim_alindi'),
                'iptal': sum(1 for s in siparisler if s.durum == 'iptal')
            }
            
            # Modal için gerekli veriler
            tedarikciler = Tedarikci.query.filter_by(aktif=True).order_by(Tedarikci.tedarikci_adi).all()
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            oteller = Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()
            
            return render_template('sistem_yoneticisi/siparis_listesi.html',
                                 siparisler=siparisler,
                                 istatistikler=istatistikler,
                                 durum_filtre=durum_filtre,
                                 otel_filtre=otel_filtre,
                                 tedarikciler=tedarikciler,
                                 urunler=urunler,
                                 oteller=oteller)
                                 
        except Exception as e:
            log_hata(e, 'yonetici_siparis_listesi')
            flash(f'Sipariş listesi yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
    
    
    @app.route('/yonetici-siparis-detay/<int:siparis_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def yonetici_siparis_detay(siparis_id):
        """Sistem yöneticisi için sipariş detayı"""
        from models import SatinAlmaSiparisi, SatinAlmaSiparisDetay
        
        try:
            siparis = SatinAlmaSiparisi.query.get_or_404(siparis_id)
            
            # Sipariş detaylarını getir
            detaylar = SatinAlmaSiparisDetay.query.filter_by(siparis_id=siparis_id).all()
            
            return render_template('sistem_yoneticisi/siparis_detay.html',
                                 siparis=siparis,
                                 detaylar=detaylar)
                                 
        except Exception as e:
            log_hata(e, 'yonetici_siparis_detay')
            flash(f'Sipariş detayı yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('yonetici_siparis_listesi'))
    
    
    @app.route('/yonetici-siparis-onayla/<int:siparis_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def yonetici_siparis_onayla(siparis_id):
        """Sistem yöneticisi sipariş onaylama"""
        from models import SatinAlmaSiparisi
        from utils.satin_alma_servisleri import SatinAlmaServisi
        
        try:
            siparis = SatinAlmaSiparisi.query.get_or_404(siparis_id)
            
            # Sadece beklemede olan siparişler onaylanabilir
            if siparis.durum != 'beklemede':
                flash('Sadece beklemede olan siparişler onaylanabilir.', 'warning')
                return redirect(url_for('yonetici_siparis_detay', siparis_id=siparis_id))
            
            # Sipariş durumunu güncelle
            sonuc = SatinAlmaServisi.siparis_durum_guncelle(
                siparis_id=siparis_id,
                yeni_durum='onaylandi',
                kullanici_id=session['kullanici_id']
            )
            
            if sonuc['success']:
                flash('Sipariş başarıyla onaylandı.', 'success')
                
                # Audit log
                audit_update(
                    tablo_adi='satin_alma_siparisleri',
                    kayit_id=siparis.id,
                    eski_deger={'durum': 'beklemede'},
                    yeni_deger={'durum': 'onaylandi', 'onaylayan_id': session['kullanici_id']},
                    aciklama=f'Sipariş onaylandı - {siparis.siparis_no}'
                )
                
                # Log kaydı
                log_islem('onaylama', 'siparis', {
                    'siparis_id': siparis.id,
                    'siparis_no': siparis.siparis_no,
                    'onaylayan_id': session['kullanici_id']
                })
            else:
                flash(f'Sipariş onaylanamadı: {sonuc["message"]}', 'danger')
                
        except Exception as e:
            log_hata(e, 'yonetici_siparis_onayla')
            flash(f'Sipariş onaylanırken hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('yonetici_siparis_detay', siparis_id=siparis_id))
    
    
    @app.route('/yonetici-siparis-durum-guncelle/<int:siparis_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def yonetici_siparis_durum_guncelle(siparis_id):
        """Sistem yöneticisi sipariş durum güncelleme"""
        from utils.satin_alma_servisleri import SatinAlmaServisi
        
        try:
            yeni_durum = request.form.get('durum')
            
            if not yeni_durum:
                flash('Durum bilgisi eksik.', 'warning')
                return redirect(url_for('yonetici_siparis_detay', siparis_id=siparis_id))
            
            # Durumu güncelle
            sonuc = SatinAlmaServisi.siparis_durum_guncelle(
                siparis_id=siparis_id,
                yeni_durum=yeni_durum,
                kullanici_id=session['kullanici_id']
            )
            
            if sonuc['success']:
                flash('Sipariş durumu başarıyla güncellendi.', 'success')
            else:
                flash(f'Sipariş durumu güncellenemedi: {sonuc["message"]}', 'danger')
                
        except Exception as e:
            log_hata(e, 'yonetici_siparis_durum_guncelle')
            flash(f'Durum güncellenirken hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('yonetici_siparis_detay', siparis_id=siparis_id))
    
    
    @app.route('/yonetici-siparis-iptal/<int:siparis_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def yonetici_siparis_iptal(siparis_id):
        """Sistem yöneticisi sipariş iptal etme"""
        from models import SatinAlmaSiparisi, SatinAlmaIslem, StokHareket
        from utils.satin_alma_servisleri import SatinAlmaServisi
        
        try:
            siparis = SatinAlmaSiparisi.query.get_or_404(siparis_id)
            iptal_nedeni = request.form.get('iptal_nedeni', '')
            
            # Sadece beklemede, onaylandı veya teslim alındı durumundaki siparişler iptal edilebilir
            if siparis.durum == 'iptal':
                flash('Bu sipariş zaten iptal edilmiş.', 'warning')
                return redirect(url_for('yonetici_siparis_detay', siparis_id=siparis_id))
            
            # Eğer sipariş teslim alındıysa, stok hareketlerini geri al
            if siparis.durum == 'teslim_alindi':
                # İlgili satın alma işlemlerini bul
                satin_alma_islemleri = SatinAlmaIslem.query.filter_by(siparis_id=siparis_id).all()
                
                for satin_alma in satin_alma_islemleri:
                    # Her satın alma işlemi için stok çıkışı yap (geri alma)
                    for detay in satin_alma.detaylar:
                        # Stok çıkışı (iptal)
                        stok_hareket = StokHareket(
                            urun_id=detay.urun_id,
                            hareket_tipi='cikis',
                            miktar=detay.miktar,
                            aciklama=f"Sipariş İptali - {siparis.siparis_no} - Satın Alma: {satin_alma.islem_no}",
                            islem_yapan_id=session['kullanici_id']
                        )
                        db.session.add(stok_hareket)
                    
                    # Satın alma işlemini pasif yap veya işaretle
                    satin_alma.aciklama = (satin_alma.aciklama or '') + f'\n\n[İPTAL EDİLDİ - {datetime.now().strftime("%d.%m.%Y %H:%M")}]'
                
                flash('Sipariş iptal edildi ve stok hareketleri geri alındı.', 'success')
            
            # Sipariş durumunu iptal et
            sonuc = SatinAlmaServisi.siparis_iptal(
                siparis_id=siparis_id,
                kullanici_id=session['kullanici_id'],
                iptal_nedeni=iptal_nedeni
            )
            
            if sonuc['success']:
                db.session.commit()
                
                # Audit log
                audit_update(
                    tablo_adi='satin_alma_siparisleri',
                    kayit_id=siparis.id,
                    eski_deger={'durum': siparis.durum},
                    yeni_deger={'durum': 'iptal', 'iptal_nedeni': iptal_nedeni},
                    aciklama=f'Sipariş iptal edildi - {siparis.siparis_no}'
                )
                
                # Log kaydı
                log_islem('iptal', 'siparis', {
                    'siparis_id': siparis.id,
                    'siparis_no': siparis.siparis_no,
                    'iptal_eden_id': session['kullanici_id'],
                    'iptal_nedeni': iptal_nedeni
                })
                
                flash('Sipariş başarıyla iptal edildi.', 'success')
            else:
                flash(f'Sipariş iptal edilemedi: {sonuc["message"]}', 'danger')
                
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'yonetici_siparis_iptal')
            flash(f'Sipariş iptal edilirken hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('yonetici_siparis_detay', siparis_id=siparis_id))

    # ============================================================================
    # API ENDPOINTS - Kat Oda Tipleri
    # ============================================================================
    
    @app.route('/api/katlar/<int:kat_id>/oda-tipleri', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_kat_oda_tipleri(kat_id):
        """Bir kattaki oda tiplerini ve sayılarını getir"""
        try:
            from sqlalchemy import func
            
            # Kat kontrolü
            kat = Kat.query.get_or_404(kat_id)
            
            # Oda tiplerini grupla ve say
            oda_tipleri = db.session.query(
                Oda.oda_tipi,
                func.count(Oda.id).label('sayi')
            ).filter(
                Oda.kat_id == kat_id,
                Oda.aktif == True
            ).group_by(
                Oda.oda_tipi
            ).order_by(
                func.count(Oda.id).desc()
            ).all()
            
            # Sonuçları formatla
            sonuc = []
            for oda_tipi, sayi in oda_tipleri:
                sonuc.append({
                    'oda_tipi': oda_tipi if oda_tipi else 'Belirtilmemiş',
                    'sayi': sayi
                })
            
            return {
                'success': True,
                'oda_tipleri': sonuc,
                'kat': {
                    'id': kat.id,
                    'kat_adi': kat.kat_adi,
                    'otel_adi': kat.otel.ad if kat.otel else None
                }
            }
            
        except Exception as e:
            log_hata(e, 'api_kat_oda_tipleri')
            return {
                'success': False,
                'error': str(e)
            }, 500
