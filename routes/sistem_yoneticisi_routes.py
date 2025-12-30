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

from flask import render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, date, timezone
import pytz
import logging
from models import db, Otel, Kat, Oda, OdaTipi, Kullanici, SistemLog
from utils.decorators import login_required, role_required
from utils.helpers import log_islem, log_hata
from utils.audit import audit_create, audit_update, audit_delete, serialize_model

# Logger tanımla
logger = logging.getLogger(__name__)

# KKTC Timezone (Kıbrıs - Europe/Nicosia)
KKTC_TZ = pytz.timezone('Europe/Nicosia')

def get_kktc_now():
    """Kıbrıs saat diliminde şu anki zamanı döndürür."""
    return datetime.now(KKTC_TZ)


def register_sistem_yoneticisi_routes(app):
    """Sistem yöneticisi route'larını kaydet"""
    
    # CSRF protection instance'ını al
    csrf = app.extensions.get('csrf')
    
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
        try:
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
                    # Exception durumunda da katları listele
                    katlar = Kat.query.filter_by(aktif=True).order_by(Kat.kat_no).all()
                    return render_template('sistem_yoneticisi/kat_tanimla.html', katlar=katlar, form=form)
            
            # Mevcut katları listele (otel bilgisi ile)
            katlar = Kat.query.filter_by(aktif=True).order_by(Kat.kat_no).all()
            
            return render_template('sistem_yoneticisi/kat_tanimla.html', katlar=katlar, form=form)
        except Exception as e:
            import traceback
            print(f"❌ KAT TANIMLA HATASI: {e}")
            print(traceback.format_exc())
            flash('Sayfa yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('dashboard'))
    
    
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
                headers = ['Otel Adı', 'Kat No', 'Oda No', 'Oda Tipi']
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
                    oda_tipi = oda.oda_tipi_adi if oda.oda_tipi_adi else '-'
                    
                    # Oda numarasını sayıya çevir (mümkünse)
                    try:
                        oda_no_sayi = int(oda.oda_no)
                    except (ValueError, TypeError):
                        oda_no_sayi = oda.oda_no
                    
                    ws.append([
                        otel_adi,
                        kat_no,
                        oda_no_sayi,
                        oda_tipi
                    ])
                
                # Sütun genişliklerini ayarla
                ws.column_dimensions['A'].width = 30  # Otel Adı
                ws.column_dimensions['B'].width = 15  # Kat No
                ws.column_dimensions['C'].width = 15  # Oda No
                ws.column_dimensions['D'].width = 20  # Oda Tipi
                
                # Oda No sütununu sayı formatına çevir (C sütunu, 2. satırdan itibaren)
                for row in range(2, ws.max_row + 1):
                    cell = ws.cell(row=row, column=3)  # C sütunu (Oda No)
                    if isinstance(cell.value, int):
                        cell.number_format = '0'  # Sayı formatı (ondalık yok)
                
                # Excel dosyasını memory'ye kaydet
                excel_buffer = io.BytesIO()
                wb.save(excel_buffer)
                excel_buffer.seek(0)
                
                filename = f'odalar_{get_kktc_now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                
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
        
        # Oda tipi listesini form'a yükle
        from models import OdaTipi
        oda_tipleri = OdaTipi.query.filter_by(aktif=True).order_by(OdaTipi.ad).all()
        form.oda_tipi_id.choices = [(0, 'Oda Tipi Seçin...')] + [(t.id, t.ad) for t in oda_tipleri]
        
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
                
                # Oda numarası duplikasyon kontrolü
                mevcut_oda = Oda.query.filter_by(oda_no=form.oda_no.data, aktif=True).first()
                if mevcut_oda:
                    flash(f'Oda numarası "{form.oda_no.data}" zaten kullanılıyor! Lütfen farklı bir oda numarası girin.', 'warning')
                    return render_template('sistem_yoneticisi/oda_tanimla.html', katlar=[], odalar=[], form=form)
                
                oda = Oda(
                    oda_no=form.oda_no.data,
                    kat_id=form.kat_id.data,
                    oda_tipi_id=form.oda_tipi_id.data if form.oda_tipi_id.data else None,
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
        
        # Oda tipi listesini yükle
        from models import OdaTipi
        oda_tipleri = OdaTipi.query.filter_by(aktif=True).order_by(OdaTipi.ad).all()
        form.oda_tipi_id.choices = [(0, 'Oda Tipi Seçin...')] + [(t.id, t.ad) for t in oda_tipleri]
        
        if form.validate_on_submit():
            try:
                # Kat'ın seçilen otele ait olduğunu kontrol et
                kat = Kat.query.get(form.kat_id.data)
                if not kat or kat.otel_id != form.otel_id.data:
                    flash('Seçilen kat, seçilen otele ait değil!', 'danger')
                    return render_template('sistem_yoneticisi/oda_duzenle.html', oda=oda, form=form, oteller=oteller)
                
                oda.oda_no = form.oda_no.data
                oda.kat_id = form.kat_id.data
                oda.oda_tipi_id = form.oda_tipi_id.data if form.oda_tipi_id.data else None
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
        """Ürün için satın alma geçmişi"""
        from models import Urun, SatinAlmaSiparisi, SatinAlmaSiparisDetay
        from datetime import date, timedelta
        
        try:
            # Ürün bilgisini getir
            urun = db.session.get(Urun, urun_id)
            if not urun:
                flash('Ürün bulunamadı.', 'danger')
                return redirect(url_for('urun_tedarikci_fiyat'))
            
            # Toplam stok hesapla
            toplam_stok = 0
            if urun.depo_stoklari:
                toplam_stok = sum(stok.miktar for stok in urun.depo_stoklari)
            
            # Bu ürün için yapılan satın almaları getir (son 1 yıl)
            bir_yil_once = date.today() - timedelta(days=365)
            
            satin_almalar = db.session.query(
                SatinAlmaSiparisDetay
            ).join(
                SatinAlmaSiparisi
            ).options(
                db.joinedload(SatinAlmaSiparisDetay.siparis).joinedload(SatinAlmaSiparisi.tedarikci),
                db.joinedload(SatinAlmaSiparisDetay.siparis).joinedload(SatinAlmaSiparisi.otel)
            ).filter(
                SatinAlmaSiparisDetay.urun_id == urun_id,
                SatinAlmaSiparisi.siparis_tarihi >= bir_yil_once
            ).order_by(
                SatinAlmaSiparisi.siparis_tarihi.desc()
            ).all()
            
        except Exception as e:
            log_hata(e, modul='fiyat_karsilastirma')
            flash('Satın alma geçmişi yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('urun_tedarikci_fiyat'))
        
        return render_template('sistem_yoneticisi/fiyat_karsilastirma.html',
                             urun=urun,
                             satin_almalar=satin_almalar,
                             toplam_stok=toplam_stok)
    
    
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
            
            # Grafik için veri hazırla
            aylar = [ap['ay'] for ap in aylik_performans]
            siparis_sayilari = [ap['toplam_siparis'] for ap in aylik_performans]
            
        except Exception as e:
            log_hata(e, modul='tedarikci_performans')
            flash('Performans raporu yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('tedarikci_yonetimi'))
        
        return render_template('sistem_yoneticisi/tedarikci_performans.html',
                             tedarikci=tedarikci,
                             performans=performans,
                             siparisler=siparisler,
                             aylik_performans=aylik_performans,
                             aylar=aylar,
                             siparis_sayilari=siparis_sayilari,
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
        from models import SatinAlmaSiparisi, SatinAlmaSiparisDetay, SatinAlmaIslem
        
        try:
            siparis = SatinAlmaSiparisi.query.get_or_404(siparis_id)
            
            # Sipariş detaylarını getir
            detaylar = SatinAlmaSiparisDetay.query.filter_by(siparis_id=siparis_id).all()
            
            # Satın alma işlemi var mı kontrol et
            satin_alma_var = SatinAlmaIslem.query.filter_by(
                siparis_id=siparis_id,
                durum='aktif'
            ).first() is not None
            
            return render_template('sistem_yoneticisi/siparis_detay.html',
                                 siparis=siparis,
                                 detaylar=detaylar,
                                 satin_alma_var=satin_alma_var)
                                 
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
                    satin_alma.aciklama = (satin_alma.aciklama or '') + f'\n\n[İPTAL EDİLDİ - {get_kktc_now().strftime("%d.%m.%Y %H:%M")}]'
                
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
    # SATIN ALMA İŞLEMLERİ ROUTE'LARI
    # ============================================================================
    
    @app.route('/yonetici-satin-alma-islemleri')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def yonetici_satin_alma_islemleri():
        """Satın alma işlemleri listesi"""
        from models import SatinAlmaIslem, SatinAlmaSiparisi
        from sqlalchemy import desc
        
        try:
            # Filtre parametreleri
            durum_filtre = request.args.get('durum')
            
            # Satın alma işlemlerini getir
            query = SatinAlmaIslem.query.options(
                db.joinedload(SatinAlmaIslem.siparis).joinedload(SatinAlmaSiparisi.tedarikci),
                db.joinedload(SatinAlmaIslem.siparis).joinedload(SatinAlmaSiparisi.otel),
                db.joinedload(SatinAlmaIslem.olusturan)
            )
            
            if durum_filtre:
                query = query.filter_by(durum=durum_filtre)
            
            islemler = query.order_by(desc(SatinAlmaIslem.islem_tarihi)).all()
            
            # İstatistikler
            istatistikler = {
                'toplam': len(islemler),
                'aktif': sum(1 for i in islemler if i.durum == 'aktif'),
                'iptal': sum(1 for i in islemler if i.durum == 'iptal'),
                'toplam_tutar': sum(i.toplam_tutar for i in islemler if i.durum == 'aktif')
            }
            
            return render_template('sistem_yoneticisi/satin_alma_islemleri.html',
                                 islemler=islemler,
                                 istatistikler=istatistikler,
                                 durum_filtre=durum_filtre)
                                 
        except Exception as e:
            log_hata(e, 'satin_alma_islemleri')
            flash(f'Satın alma işlemleri yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
    
    
    @app.route('/yonetici-satin-alma-detay/<int:islem_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def yonetici_satin_alma_detay(islem_id):
        """Satın alma işlemi detayı"""
        from models import SatinAlmaIslem, SatinAlmaIslemDetay, SatinAlmaSiparisi
        
        try:
            islem = SatinAlmaIslem.query.options(
                db.joinedload(SatinAlmaIslem.siparis).joinedload(SatinAlmaSiparisi.tedarikci),
                db.joinedload(SatinAlmaIslem.siparis).joinedload(SatinAlmaSiparisi.otel),
                db.joinedload(SatinAlmaIslem.olusturan)
            ).get_or_404(islem_id)
            
            # İşlem detaylarını getir
            detaylar = SatinAlmaIslemDetay.query.options(
                db.joinedload(SatinAlmaIslemDetay.urun)
            ).filter_by(islem_id=islem_id).all()
            
            return render_template('sistem_yoneticisi/satin_alma_detay.html',
                                 islem=islem,
                                 detaylar=detaylar)
                                 
        except Exception as e:
            log_hata(e, 'satin_alma_detay')
            flash(f'Satın alma detayı yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('yonetici_satin_alma_islemleri'))
    
    
    @app.route('/satin-alma-iptal/<int:islem_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def satin_alma_iptal(islem_id):
        """Satın alma işlemini iptal et ve stoktan düş"""
        from models import SatinAlmaIslem, SatinAlmaIslemDetay, DepoStok, StokHareket, SatinAlmaSiparisi
        
        try:
            islem = SatinAlmaIslem.query.get_or_404(islem_id)
            
            # Sadece aktif işlemler iptal edilebilir
            if islem.durum != 'aktif':
                flash('Sadece aktif satın alma işlemleri iptal edilebilir.', 'warning')
                return redirect(url_for('satin_alma_detay', islem_id=islem_id))
            
            # İşlem detaylarını getir
            detaylar = SatinAlmaIslemDetay.query.filter_by(islem_id=islem_id).all()
            
            # Her ürün için stoktan düş
            for detay in detaylar:
                # Depo stoğunu bul
                depo_stok = DepoStok.query.filter_by(
                    urun_id=detay.urun_id,
                    otel_id=islem.siparis.otel_id
                ).first()
                
                if depo_stok and depo_stok.miktar >= detay.miktar:
                    # Stoktan düş
                    depo_stok.miktar -= detay.miktar
                    
                    # Stok hareketi kaydet
                    stok_hareket = StokHareket(
                        urun_id=detay.urun_id,
                        otel_id=islem.siparis.otel_id,
                        hareket_tipi='cikis',
                        miktar=detay.miktar,
                        aciklama=f'Satın alma işlemi iptal edildi: {islem.islem_no}',
                        kullanici_id=current_user.id
                    )
                    db.session.add(stok_hareket)
                else:
                    flash(f'{detay.urun.urun_adi} için yeterli stok yok. İptal işlemi tamamlanamadı.', 'danger')
                    db.session.rollback()
                    return redirect(url_for('satin_alma_detay', islem_id=islem_id))
            
            # İşlemi iptal et
            islem.durum = 'iptal'
            islem.iptal_tarihi = get_kktc_now()
            islem.iptal_eden_id = current_user.id
            islem.iptal_aciklama = request.form.get('iptal_aciklama', 'Sistem yöneticisi tarafından iptal edildi')
            
            # İlgili siparişi de iptal edilebilir duruma getir
            if islem.siparis:
                islem.siparis.durum = 'onaylandi'  # Sipariş tekrar iptal edilebilir hale gelir
            
            db.session.commit()
            
            log_islem('iptal', 'satin_alma_islem', {
                'islem_id': islem.id,
                'islem_no': islem.islem_no,
                'iptal_eden': current_user.ad_soyad
            })
            
            flash('Satın alma işlemi başarıyla iptal edildi ve stoktan düşüldü.', 'success')
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'satin_alma_iptal')
            flash(f'Satın alma işlemi iptal edilirken hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('satin_alma_detay', islem_id=islem_id))

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
                OdaTipi.ad,
                func.count(Oda.id).label('sayi')
            ).join(
                Oda, Oda.oda_tipi_id == OdaTipi.id
            ).filter(
                Oda.kat_id == kat_id,
                Oda.aktif == True
            ).group_by(
                OdaTipi.ad
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

    # ============================================================================
    # API ENDPOINTS - Oda Tipi Yönetimi
    # ============================================================================
    
    @app.route('/api/oda-tipleri', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_oda_tipleri_listele():
        """Tüm oda tiplerini listele (otel bazlı setup bilgisi ile)"""
        try:
            from models import OdaTipi, oda_tipi_setup, Setup
            from sqlalchemy import and_
            
            otel_id = request.args.get('otel_id', type=int)
            
            oda_tipleri = OdaTipi.query.filter_by(aktif=True).order_by(OdaTipi.ad).all()
            
            result = []
            for tip in oda_tipleri:
                # Otel ID verilmişse, o otele ait setup'ları getir
                if otel_id:
                    setup_rows = db.session.execute(
                        db.select(oda_tipi_setup.c.setup_id).where(
                            and_(
                                oda_tipi_setup.c.otel_id == otel_id,
                                oda_tipi_setup.c.oda_tipi_id == tip.id
                            )
                        )
                    ).fetchall()
                    setup_ids = [row[0] for row in setup_rows]
                    
                    # Setup adlarını al
                    setup_adlari = []
                    for sid in setup_ids:
                        setup = Setup.query.get(sid)
                        if setup:
                            setup_adlari.append(setup.ad)
                else:
                    # Otel ID yoksa, global ilişkiden al (geriye uyumluluk)
                    setup_ids = [s.id for s in tip.setuplar]
                    setup_adlari = [s.ad for s in tip.setuplar]
                
                result.append({
                    'id': tip.id,
                    'ad': tip.ad,
                    'dolap_sayisi': tip.dolap_sayisi,
                    'setup_ids': setup_ids,
                    'setup_adlari': setup_adlari,
                    'olusturma_tarihi': tip.olusturma_tarihi.isoformat() if tip.olusturma_tarihi else None
                })
            
            return jsonify({
                'success': True,
                'oda_tipleri': result
            })
            
        except Exception as e:
            log_hata(e, 'api_oda_tipleri_listele')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/oda-tipleri', methods=['POST'])
    @csrf.exempt
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_oda_tipi_ekle():
        """Yeni oda tipi ekle"""
        try:
            from models import OdaTipi, Setup
            
            data = request.get_json()
            ad = data.get('ad', '').strip()
            dolap_sayisi = data.get('dolap_sayisi', 0)
            setup_ids = data.get('setup_ids', [])
            
            if not ad:
                return {
                    'success': False,
                    'error': 'Oda tipi adı boş olamaz'
                }, 400
            
            if not setup_ids or len(setup_ids) == 0:
                return {
                    'success': False,
                    'error': 'En az bir setup seçimi zorunludur'
                }, 400
            
            # Aynı isimde oda tipi var mı kontrol et
            mevcut = OdaTipi.query.filter_by(ad=ad).first()
            if mevcut:
                if mevcut.aktif:
                    return {
                        'success': False,
                        'error': 'Bu oda tipi zaten mevcut'
                    }, 400
                else:
                    # Pasif oda tipini aktif et ve güncelle
                    mevcut.aktif = True
                    mevcut.dolap_sayisi = dolap_sayisi
                    
                    # Setup'ları güncelle (many-to-many)
                    mevcut.setuplar.clear()
                    for setup_id in setup_ids:
                        setup = Setup.query.get(setup_id)
                        if setup:
                            mevcut.setuplar.append(setup)
                    
                    db.session.commit()
                    
                    audit_update(
                        'OdaTipi',
                        mevcut.id,
                        {'aktif': False},
                        {'aktif': True, 'dolap_sayisi': dolap_sayisi, 'setup_ids': setup_ids},
                        session.get('kullanici_id')
                    )
                    
                    log_islem('oda_tipi_aktif', f'Oda tipi aktif edildi: {ad}')
                    
                    return {
                        'success': True,
                        'oda_tipi': {
                            'id': mevcut.id,
                            'ad': mevcut.ad,
                            'dolap_sayisi': mevcut.dolap_sayisi,
                            'setup_ids': [s.id for s in mevcut.setuplar],
                            'setup_adlari': [s.ad for s in mevcut.setuplar]
                        }
                    }
            
            # Yeni oda tipi oluştur
            yeni_tip = OdaTipi(ad=ad, dolap_sayisi=dolap_sayisi)
            
            # Setup'ları ekle (many-to-many)
            for setup_id in setup_ids:
                setup = Setup.query.get(setup_id)
                if setup:
                    yeni_tip.setuplar.append(setup)
            
            db.session.add(yeni_tip)
            db.session.commit()
            
            audit_create('OdaTipi', yeni_tip.id, serialize_model(yeni_tip), session.get('kullanici_id'))
            log_islem('oda_tipi_ekle', f'Yeni oda tipi eklendi: {ad}')
            
            return {
                'success': True,
                'oda_tipi': {
                    'id': yeni_tip.id,
                    'ad': yeni_tip.ad,
                    'dolap_sayisi': yeni_tip.dolap_sayisi,
                    'setup_ids': [s.id for s in yeni_tip.setuplar],
                    'setup_adlari': [s.ad for s in yeni_tip.setuplar]
                }
            }
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'api_oda_tipi_ekle')
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    @app.route('/api/oda-tipleri/<int:tip_id>', methods=['PUT'])
    @csrf.exempt
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_oda_tipi_guncelle(tip_id):
        """Oda tipi güncelle"""
        try:
            from models import OdaTipi, Setup
            
            oda_tipi = OdaTipi.query.get_or_404(tip_id)
            data = request.get_json()
            ad = data.get('ad', '').strip()
            dolap_sayisi = data.get('dolap_sayisi', 0)
            setup_ids = data.get('setup_ids', [])
            
            if not ad:
                return {
                    'success': False,
                    'error': 'Oda tipi adı boş olamaz'
                }, 400
            
            if not setup_ids or len(setup_ids) == 0:
                return {
                    'success': False,
                    'error': 'En az bir setup seçimi zorunludur'
                }, 400
            
            # Aynı isimde başka oda tipi var mı kontrol et
            mevcut = OdaTipi.query.filter(
                OdaTipi.ad == ad,
                OdaTipi.id != tip_id
            ).first()
            
            if mevcut:
                return {
                    'success': False,
                    'error': 'Bu isimde başka bir oda tipi mevcut'
                }, 400
            
            eski_deger = serialize_model(oda_tipi)
            oda_tipi.ad = ad
            oda_tipi.dolap_sayisi = dolap_sayisi
            
            # Setup'ları güncelle (many-to-many)
            oda_tipi.setuplar.clear()
            for setup_id in setup_ids:
                setup = Setup.query.get(setup_id)
                if setup:
                    oda_tipi.setuplar.append(setup)
            
            db.session.commit()
            
            audit_update('OdaTipi', tip_id, eski_deger, serialize_model(oda_tipi), session.get('kullanici_id'))
            log_islem('oda_tipi_guncelle', f'Oda tipi güncellendi: {ad}')
            
            return {
                'success': True,
                'oda_tipi': {
                    'id': oda_tipi.id,
                    'ad': oda_tipi.ad,
                    'dolap_sayisi': oda_tipi.dolap_sayisi,
                    'setup_ids': [s.id for s in oda_tipi.setuplar],
                    'setup_adlari': [s.ad for s in oda_tipi.setuplar]
                }
            }
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'api_oda_tipi_guncelle')
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    @app.route('/api/oda-tipleri/<int:tip_id>', methods=['DELETE'])
    @csrf.exempt
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_oda_tipi_sil(tip_id):
        """Oda tipi sil (soft delete)"""
        try:
            from models import OdaTipi
            
            oda_tipi = OdaTipi.query.get_or_404(tip_id)
            
            # Bu oda tipini kullanan oda var mı kontrol et
            kullanan_oda_sayisi = Oda.query.filter_by(oda_tipi_id=oda_tipi.id, aktif=True).count()
            
            if kullanan_oda_sayisi > 0:
                return {
                    'success': False,
                    'error': f'Bu oda tipi {kullanan_oda_sayisi} oda tarafından kullanılıyor. Önce odaların tipini değiştirin.'
                }, 400
            
            eski_deger = serialize_model(oda_tipi)
            oda_tipi.aktif = False
            db.session.commit()
            
            audit_delete('OdaTipi', tip_id, eski_deger, session.get('kullanici_id'))
            log_islem('oda_tipi_sil', f'Oda tipi silindi: {oda_tipi.ad}')
            
            return {
                'success': True,
                'message': 'Oda tipi başarıyla silindi'
            }
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'api_oda_tipi_sil')
            return {
                'success': False,
                'error': str(e)
            }, 500

    # ============================================================================
    # SETUP YÖNETİMİ
    # ============================================================================
    
    @app.route('/setup-yonetimi', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def setup_yonetimi():
        """Setup yönetim sayfası"""
        return render_template('sistem_yoneticisi/setup_yonetimi.html')
    
    # ============================================================================
    # API ENDPOINTS - Setup Yönetimi
    # ============================================================================
    
    @app.route('/api/setuplar', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_setuplar_listele():
        """Tüm setup'ları listele"""
        try:
            from models import Setup, SetupIcerik, OdaTipi, Otel, oda_tipi_setup
            from sqlalchemy import distinct
            
            # Sadece aktif setup'ları getir
            setuplar = Setup.query.filter_by(aktif=True).all()
            
            sonuc = []
            for setup in setuplar:
                # Ürün sayısını hesapla
                urun_sayisi = SetupIcerik.query.filter_by(setup_id=setup.id).count()
                
                # Bu setup'a atanmış oda tiplerini al (otel bazlı tablodan, sadece aktif oda tipleri)
                # Otel adı ile birlikte getir
                atamalar = db.session.execute(
                    db.select(
                        oda_tipi_setup.c.otel_id,
                        oda_tipi_setup.c.oda_tipi_id
                    ).where(
                        oda_tipi_setup.c.setup_id == setup.id
                    )
                ).fetchall()
                
                # Otel bazlı oda tipleri dict'i oluştur
                otel_oda_tipleri = {}  # {otel_adi: [oda_tipi_adlari]}
                oda_tipi_adlari = []  # Geriye uyumluluk için
                
                for row in atamalar:
                    otel_id = row[0]
                    oda_tipi_id = row[1]
                    
                    # Aktif oda tipini al
                    oda_tipi = OdaTipi.query.filter_by(id=oda_tipi_id, aktif=True).first()
                    if not oda_tipi:
                        continue
                    
                    # Otel adını al
                    otel = Otel.query.get(otel_id) if otel_id else None
                    otel_adi = otel.ad if otel else "Bilinmeyen Otel"
                    
                    # Dict'e ekle
                    if otel_adi not in otel_oda_tipleri:
                        otel_oda_tipleri[otel_adi] = []
                    
                    if oda_tipi.ad not in otel_oda_tipleri[otel_adi]:
                        otel_oda_tipleri[otel_adi].append(oda_tipi.ad)
                    
                    # Geriye uyumluluk için
                    if oda_tipi.ad not in oda_tipi_adlari:
                        oda_tipi_adlari.append(oda_tipi.ad)
                
                # Toplam maliyeti hesapla (ürün alış fiyatı * adet)
                toplam_maliyet = 0
                setup_icerikler = SetupIcerik.query.filter_by(setup_id=setup.id).all()
                for icerik in setup_icerikler:
                    if icerik.urun and icerik.urun.alis_fiyati:
                        toplam_maliyet += icerik.urun.alis_fiyati * icerik.adet
                
                sonuc.append({
                    'id': setup.id,
                    'ad': setup.ad,
                    'aciklama': setup.aciklama,
                    'dolap_ici': setup.dolap_ici if hasattr(setup, 'dolap_ici') else True,
                    'urun_sayisi': urun_sayisi,
                    'oda_tipleri': oda_tipi_adlari,  # Geriye uyumluluk
                    'otel_oda_tipleri': otel_oda_tipleri,  # Yeni: Otel bazlı
                    'toplam_maliyet': round(toplam_maliyet, 2)
                })
            
            return {
                'success': True,
                'setuplar': sonuc
            }
            
        except Exception as e:
            log_hata(e, 'api_setuplar_listele')
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    @app.route('/api/setuplar', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_setup_ekle():
        """Yeni setup ekle"""
        try:
            from models import Setup
            
            data = request.get_json()
            ad = data.get('ad', '').strip()
            aciklama = data.get('aciklama', '').strip()
            dolap_ici = data.get('dolap_ici', True)  # Varsayılan: Dolap İçi
            
            if not ad:
                return {
                    'success': False,
                    'error': 'Setup adı boş olamaz'
                }, 400
            
            # Aynı isimde setup var mı kontrol et
            mevcut = Setup.query.filter_by(ad=ad).first()
            if mevcut:
                return {
                    'success': False,
                    'error': 'Bu isimde setup zaten mevcut'
                }, 400
            
            yeni_setup = Setup(ad=ad, aciklama=aciklama, dolap_ici=dolap_ici)
            db.session.add(yeni_setup)
            db.session.commit()
            
            audit_create('Setup', yeni_setup.id, serialize_model(yeni_setup), session.get('kullanici_id'))
            log_islem('setup_ekle', f'Yeni setup eklendi: {ad}')
            
            return {
                'success': True,
                'setup': {
                    'id': yeni_setup.id,
                    'ad': yeni_setup.ad
                }
            }
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'api_setup_ekle')
            return {
                'success': False,
                'error': str(e)
            }, 500

    @app.route('/api/setuplar/<int:setup_id>', methods=['PUT', 'PATCH', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_setup_guncelle(setup_id):
        """Setup güncelle"""
        try:
            from models import Setup, Oda
            
            data = request.get_json()
            ad = data.get('ad', '').strip()
            aciklama = data.get('aciklama', '').strip()
            dolap_ici = data.get('dolap_ici', True)
            
            # Validasyon
            if not ad:
                return {
                    'success': False,
                    'error': 'Setup adı boş olamaz'
                }, 400
            
            # Setup bul
            setup = Setup.query.get_or_404(setup_id)
            eski_ad = setup.ad
            eski_deger = serialize_model(setup)
            
            # Aynı isimde başka setup var mı kontrol et
            existing = Setup.query.filter(
                Setup.ad == ad,
                Setup.id != setup_id
            ).first()
            
            if existing:
                return {
                    'success': False,
                    'error': 'Bu isimde bir setup zaten var'
                }, 400
            
            # Güncelle
            setup.ad = ad
            setup.aciklama = aciklama
            setup.dolap_ici = dolap_ici
            db.session.commit()
            
            # NOT: Oda tipi atamaları artık Many-to-Many ilişki ile yönetiliyor
            # oda_tipi_setup ara tablosu kullanılıyor, Oda tablosunda setup kolonu yok
            
            # Audit log
            yeni_deger = serialize_model(setup)
            audit_update('Setup', setup_id, eski_deger, yeni_deger, session.get('kullanici_id'))
            log_islem('setup_guncelle', f'Setup güncellendi: {eski_ad} → {ad}')
            
            return {
                'success': True,
                'message': 'Setup başarıyla güncellendi'
            }
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'api_setup_guncelle')
            return {
                'success': False,
                'error': str(e)
            }, 500

    @app.route('/api/setuplar/<int:setup_id>', methods=['DELETE'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_setup_sil(setup_id):
        """Setup sil"""
        try:
            from models import Setup
            
            setup = Setup.query.get_or_404(setup_id)
            
            eski_deger = serialize_model(setup)
            setup.aktif = False
            db.session.commit()
            
            audit_delete('Setup', setup_id, eski_deger, session.get('kullanici_id'))
            log_islem('setup_sil', f'Setup silindi: {setup.ad}')
            
            return {
                'success': True,
                'message': 'Setup başarıyla silindi'
            }
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'api_setup_sil')
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    @app.route('/api/setuplar/<int:setup_id>/icerik', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_setup_icerik_listele(setup_id):
        """Setup içeriğini listele"""
        try:
            from models import SetupIcerik
            
            icerikler = SetupIcerik.query.filter_by(setup_id=setup_id).all()
            
            sonuc = []
            toplam_maliyet = 0
            
            for icerik in icerikler:
                # Ürün alış fiyatını fiyat geçmişinden çek
                alis_fiyati = 0
                try:
                    from models import UrunFiyatGecmisi, FiyatDegisiklikTipi
                    fiyat_kaydi = UrunFiyatGecmisi.query.filter_by(
                        urun_id=icerik.urun_id,
                        degisiklik_tipi=FiyatDegisiklikTipi.ALIS_FIYATI
                    ).order_by(UrunFiyatGecmisi.degisiklik_tarihi.desc()).first()
                    
                    if fiyat_kaydi:
                        alis_fiyati = float(fiyat_kaydi.yeni_fiyat)
                except Exception as fiyat_hata:
                    print(f"Fiyat çekme hatası: {fiyat_hata}")
                
                tutar = alis_fiyati * icerik.adet
                toplam_maliyet += tutar
                
                sonuc.append({
                    'id': icerik.id,
                    'urun_id': icerik.urun_id,
                    'urun_ad': icerik.urun.urun_adi if icerik.urun else 'Bilinmeyen',
                    'adet': icerik.adet,
                    'alis_fiyati': float(alis_fiyati),
                    'tutar': float(tutar)
                })
            
            return {
                'success': True,
                'icerikler': sonuc,
                'toplam_maliyet': float(toplam_maliyet)
            }
            
        except Exception as e:
            log_hata(e, 'api_setup_icerik_listele')
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    @app.route('/api/setuplar/<int:setup_id>/icerik', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_setup_icerik_ekle(setup_id):
        """Setup'a ürün ekle"""
        try:
            from models import SetupIcerik
            
            data = request.get_json()
            urun_id = data.get('urun_id')
            adet = data.get('adet', 1)
            
            if not urun_id:
                return {
                    'success': False,
                    'error': 'Ürün seçimi zorunludur'
                }, 400
            
            # Aynı ürün zaten ekli mi kontrol et
            mevcut = SetupIcerik.query.filter_by(setup_id=setup_id, urun_id=urun_id).first()
            if mevcut:
                return {
                    'success': False,
                    'error': 'Bu ürün zaten ekli'
                }, 400
            
            yeni_icerik = SetupIcerik(setup_id=setup_id, urun_id=urun_id, adet=adet)
            db.session.add(yeni_icerik)
            db.session.commit()
            
            log_islem('setup_icerik_ekle', f'Setup içeriğine ürün eklendi: Setup ID {setup_id}, Ürün ID {urun_id}')
            
            return {
                'success': True,
                'icerik': {
                    'id': yeni_icerik.id
                }
            }
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'api_setup_icerik_ekle')
            return {
                'success': False,
                'error': str(e)
            }, 500

    @app.route('/api/setup-icerik/<int:icerik_id>', methods=['DELETE'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_setup_icerik_sil(icerik_id):
        """Setup içeriğinden ürün sil"""
        try:
            from models import SetupIcerik
            
            icerik = SetupIcerik.query.get_or_404(icerik_id)
            
            db.session.delete(icerik)
            db.session.commit()
            
            log_islem('setup_icerik_sil', f'Setup içeriğinden ürün silindi: İçerik ID {icerik_id}')
            
            return {
                'success': True,
                'message': 'Ürün başarıyla silindi'
            }
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'api_setup_icerik_sil')
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    @app.route('/api/setup-atama', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_setup_atama():
        """Setup'ları oda tiplerine ata (Otel bazlı Many-to-Many)"""
        try:
            from models import OdaTipi, Setup, Otel, oda_tipi_setup
            from sqlalchemy import and_
            
            data = request.get_json()
            
            if not data:
                return {
                    'success': False,
                    'error': 'Veri gönderilmedi'
                }, 400
            
            otel_id = data.get('otel_id')
            oda_tipi_id = data.get('oda_tipi_id')
            setup_ids = data.get('setup_ids', [])
            
            if not otel_id:
                return {
                    'success': False,
                    'error': 'Otel ID belirtilmedi'
                }, 400
            
            if not oda_tipi_id:
                return {
                    'success': False,
                    'error': 'Oda tipi ID belirtilmedi'
                }, 400
            
            # Otel kontrolü
            otel = Otel.query.get(otel_id)
            if not otel:
                return {
                    'success': False,
                    'error': f'Otel bulunamadı: {otel_id}'
                }, 404
            
            # Oda tipini bul
            oda_tipi = OdaTipi.query.get(oda_tipi_id)
            if not oda_tipi:
                return {
                    'success': False,
                    'error': f'Oda tipi bulunamadı: {oda_tipi_id}'
                }, 404
            
            # Bu otel ve oda tipi için mevcut atamaları sil
            db.session.execute(
                oda_tipi_setup.delete().where(
                    and_(
                        oda_tipi_setup.c.otel_id == otel_id,
                        oda_tipi_setup.c.oda_tipi_id == oda_tipi_id
                    )
                )
            )
            
            # Yeni setup'ları ekle
            if setup_ids:
                for setup_id in setup_ids:
                    setup = Setup.query.get(setup_id)
                    if setup:
                        db.session.execute(
                            oda_tipi_setup.insert().values(
                                otel_id=otel_id,
                                oda_tipi_id=oda_tipi_id,
                                setup_id=setup_id
                            )
                        )
            
            db.session.commit()
            
            log_islem('setup_atama', f'Otel bazlı setup ataması güncellendi: {otel.ad} - {oda_tipi.ad} -> {len(setup_ids)} setup')
            
            return {
                'success': True,
                'message': 'Atama başarıyla kaydedildi'
            }
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'api_setup_atama')
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    @app.route('/api/urunler-liste', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_urunler_liste():
        """Tüm ürünleri listele"""
        try:
            from models import Urun
            
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            return {
                'success': True,
                'urunler': [{
                    'id': urun.id,
                    'ad': urun.urun_adi,
                    'grup_id': urun.grup_id,
                    'alis_fiyati': float(urun.alis_fiyati) if urun.alis_fiyati else 0
                } for urun in urunler]
            }
            
        except Exception as e:
            log_hata(e, 'api_urunler_liste')
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    @app.route('/api/urun-gruplari-liste', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_urun_gruplari_liste():
        """Tüm ürün gruplarını listele"""
        try:
            from models import UrunGrup
            
            gruplar = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
            
            return {
                'success': True,
                'gruplar': [{
                    'id': grup.id,
                    'ad': grup.grup_adi
                } for grup in gruplar]
            }
            
        except Exception as e:
            log_hata(e, 'api_urun_gruplari_liste')
            return {
                'success': False,
                'error': str(e)
            }, 500

    # ============================================
    # FİYAT YÖNETİMİ
    # ============================================
    
    @app.route('/fiyat-yonetimi')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def fiyat_yonetimi():
        """Ürün fiyat yönetimi sayfası"""
        try:
            from models import Urun, UrunGrup, SatinAlmaIslemDetay
            from sqlalchemy import func, desc
            
            # Tüm ürünleri gruplarıyla birlikte getir
            urunler = db.session.query(
                Urun.id,
                Urun.urun_adi,
                Urun.urun_kodu,
                Urun.barkod,
                Urun.birim,
                Urun.satis_fiyati,
                Urun.alis_fiyati,
                Urun.kar_tutari,
                Urun.kar_orani,
                UrunGrup.grup_adi
            ).join(
                UrunGrup, Urun.grup_id == UrunGrup.id
            ).filter(
                Urun.aktif == True
            ).order_by(
                UrunGrup.grup_adi, Urun.urun_adi
            ).all()
            
            # Her ürün için son alım fiyatını bul
            urun_listesi = []
            for urun in urunler:
                # Son alım fiyatını bul
                son_alim = db.session.query(
                    SatinAlmaIslemDetay.birim_fiyat,
                    SatinAlmaIslemDetay.olusturma_tarihi
                ).filter(
                    SatinAlmaIslemDetay.urun_id == urun.id
                ).order_by(
                    desc(SatinAlmaIslemDetay.olusturma_tarihi)
                ).first()
                
                son_alim_fiyati = float(son_alim.birim_fiyat) if son_alim else None
                son_alim_tarihi = son_alim.olusturma_tarihi if son_alim else None
                
                urun_listesi.append({
                    'id': urun.id,
                    'urun_adi': urun.urun_adi,
                    'urun_kodu': urun.urun_kodu,
                    'barkod': urun.barkod,
                    'birim': urun.birim,
                    'grup_adi': urun.grup_adi,
                    'satis_fiyati': float(urun.satis_fiyati) if urun.satis_fiyati else 0,
                    'alis_fiyati': float(urun.alis_fiyati) if urun.alis_fiyati else 0,
                    'kar_tutari': float(urun.kar_tutari) if urun.kar_tutari else 0,
                    'kar_orani': float(urun.kar_orani) if urun.kar_orani else 0,
                    'son_alim_fiyati': son_alim_fiyati,
                    'son_alim_tarihi': son_alim_tarihi.strftime('%d.%m.%Y %H:%M') if son_alim_tarihi else None
                })
            
            return render_template(
                'sistem_yoneticisi/fiyat_yonetimi.html',
                urunler=urun_listesi
            )
            
        except Exception as e:
            log_hata(e, 'fiyat_yonetimi')
            flash('Fiyat yönetimi sayfası yüklenirken hata oluştu', 'danger')
            return redirect(url_for('sistem_yoneticisi_dashboard'))
    
    @app.route('/api/fiyat-guncelle/<int:urun_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_fiyat_guncelle(urun_id):
        """Ürün fiyatlarını güncelle"""
        try:
            from models import Urun, UrunFiyatGecmisi, FiyatDegisiklikTipi
            
            data = request.get_json()
            
            # Validasyon
            if not data:
                return jsonify({'success': False, 'error': 'Veri gönderilmedi'}), 400
            
            urun = Urun.query.get_or_404(urun_id)
            
            # Eski değerleri sakla
            eski_alis = urun.alis_fiyati
            eski_satis = urun.satis_fiyati
            
            # Yeni değerleri al
            yeni_alis = data.get('alis_fiyati')
            yeni_satis = data.get('satis_fiyati')
            degisiklik_sebebi = data.get('sebep', 'Manuel güncelleme')
            
            degisiklikler = []
            
            # Alış fiyatı güncelleme
            if yeni_alis is not None:
                yeni_alis = float(yeni_alis)
                if yeni_alis < 0:
                    return jsonify({'success': False, 'error': 'Alış fiyatı negatif olamaz'}), 400
                
                if eski_alis != yeni_alis:
                    urun.alis_fiyati = yeni_alis
                    
                    # Geçmişe kaydet
                    gecmis = UrunFiyatGecmisi(
                        urun_id=urun_id,
                        eski_fiyat=eski_alis,
                        yeni_fiyat=yeni_alis,
                        degisiklik_tipi=FiyatDegisiklikTipi.ALIS_FIYATI,
                        degisiklik_sebebi=degisiklik_sebebi,
                        olusturan_id=session['kullanici_id']
                    )
                    db.session.add(gecmis)
                    degisiklikler.append('alış fiyatı')
            
            # Satış fiyatı güncelleme
            if yeni_satis is not None:
                yeni_satis = float(yeni_satis)
                if yeni_satis < 0:
                    return jsonify({'success': False, 'error': 'Satış fiyatı negatif olamaz'}), 400
                
                if eski_satis != yeni_satis:
                    urun.satis_fiyati = yeni_satis
                    
                    # Geçmişe kaydet
                    gecmis = UrunFiyatGecmisi(
                        urun_id=urun_id,
                        eski_fiyat=eski_satis,
                        yeni_fiyat=yeni_satis,
                        degisiklik_tipi=FiyatDegisiklikTipi.SATIS_FIYATI,
                        degisiklik_sebebi=degisiklik_sebebi,
                        olusturan_id=session['kullanici_id']
                    )
                    db.session.add(gecmis)
                    degisiklikler.append('satış fiyatı')
            
            # Kar hesaplama
            if urun.alis_fiyati and urun.satis_fiyati:
                urun.kar_tutari = urun.satis_fiyati - urun.alis_fiyati
                if urun.alis_fiyati > 0:
                    urun.kar_orani = (urun.kar_tutari / urun.alis_fiyati) * 100
                else:
                    urun.kar_orani = 0
            
            if degisiklikler:
                db.session.commit()
                
                log_islem(
                    'fiyat_guncelleme',
                    f"{urun.urun_adi} ürününün {', '.join(degisiklikler)} güncellendi",
                    session['kullanici_id']
                )
                
                return jsonify({
                    'success': True,
                    'message': f"{', '.join(degisiklikler).capitalize()} başarıyla güncellendi",
                    'kar_tutari': float(urun.kar_tutari) if urun.kar_tutari else 0,
                    'kar_orani': float(urun.kar_orani) if urun.kar_orani else 0
                })
            else:
                return jsonify({
                    'success': True,
                    'message': 'Değişiklik yapılmadı'
                })
            
        except ValueError as e:
            return jsonify({'success': False, 'error': 'Geçersiz fiyat formatı'}), 400
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'api_fiyat_guncelle')
            return jsonify({'success': False, 'error': str(e)}), 500
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    # ============================================================================
    # İLK STOK YÜKLEME ROUTE'LARI
    # ============================================================================
    
    @app.route('/otel-ilk-stok-yukleme', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi')
    def otel_ilk_stok_yukleme():
        """İlk stok yükleme sayfası - Her otel için 1 kez (FIFO)"""
        from models import Urun, UrunGrup
        
        try:
            # Otelleri getir
            oteller = Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()
            
            # Otel durumlarını hazırla
            otel_durumlari = []
            for otel in oteller:
                # Yükleyen kullanıcı bilgisini al
                yukleyen_adi = None
                if otel.ilk_stok_yukleyen_id:
                    yukleyen = db.session.get(Kullanici, otel.ilk_stok_yukleyen_id)
                    if yukleyen:
                        yukleyen_adi = f"{yukleyen.ad} {yukleyen.soyad}"
                
                otel_durumlari.append({
                    'id': otel.id,
                    'ad': otel.ad,
                    'ilk_stok_yuklendi': otel.ilk_stok_yuklendi,
                    'yukleme_tarihi': otel.ilk_stok_yukleme_tarihi.strftime('%d.%m.%Y %H:%M') if otel.ilk_stok_yukleme_tarihi else None,
                    'yukleyen': yukleyen_adi
                })
            
            # Ürün grupları ve ürünler
            gruplar = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            return render_template('sistem_yoneticisi/ilk_stok_yukleme.html',
                                 otel_durumlari=otel_durumlari,
                                 gruplar=gruplar,
                                 urunler=urunler)
                                 
        except Exception as e:
            log_hata(e, 'ilk_stok_yukleme')
            flash('Sayfa yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('sistem_yoneticisi_dashboard'))
    
    
    @app.route('/otel-ilk-stok-yukleme-kaydet', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi')
    def otel_ilk_stok_yukleme_kaydet():
        """İlk stok yükleme işlemini kaydet (FIFO)"""
        from utils.fifo_servisler import FifoStokServisi
        
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'error': 'Veri bulunamadı'}), 400
            
            otel_id = data.get('otel_id')
            stok_verileri = data.get('stok_verileri', [])
            
            if not otel_id:
                return jsonify({'success': False, 'error': 'Otel seçilmedi'}), 400
            
            if not stok_verileri:
                return jsonify({'success': False, 'error': 'Stok verisi girilmedi'}), 400
            
            # Otel kontrolü
            otel = db.session.get(Otel, otel_id)
            if not otel:
                return jsonify({'success': False, 'error': 'Otel bulunamadı'}), 404
            
            if otel.ilk_stok_yuklendi:
                return jsonify({
                    'success': False, 
                    'error': f'Bu otel için ilk stok yüklemesi zaten yapılmış ({otel.ilk_stok_yukleme_tarihi.strftime("%d.%m.%Y")})'
                }), 400
            
            # İlk stok yükle
            sonuc = FifoStokServisi.ilk_stok_yukle(
                otel_id=otel_id,
                stok_verileri=stok_verileri,
                kullanici_id=session['kullanici_id']
            )
            
            if sonuc['success']:
                return jsonify({
                    'success': True,
                    'message': sonuc['message'],
                    'yuklenen_urun_sayisi': sonuc.get('yuklenen_urun_sayisi', 0)
                })
            else:
                return jsonify({
                    'success': False,
                    'error': sonuc['message'],
                    'hatalar': sonuc.get('hatalar', [])
                }), 400
                
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'ilk_stok_yukleme_kaydet')
            return jsonify({'success': False, 'error': f'Kayıt hatası: {str(e)}'}), 500
    
    
    @app.route('/api/otel-stok-durumu/<int:otel_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin', 'depo_sorumlusu')
    def api_otel_stok_durumu(otel_id):
        """Otel bazlı FIFO stok durumunu getir"""
        from utils.fifo_servisler import FifoStokServisi
        
        try:
            otel = db.session.get(Otel, otel_id)
            if not otel:
                return jsonify({'success': False, 'error': 'Otel bulunamadı'}), 404
            
            stok_durumu = FifoStokServisi.fifo_stok_durumu(otel_id)
            
            return jsonify({
                'success': True,
                'otel_id': otel_id,
                'otel_adi': otel.ad,
                'ilk_stok_yuklendi': otel.ilk_stok_yuklendi,
                'stok_durumu': stok_durumu
            })
            
        except Exception as e:
            log_hata(e, 'api_otel_stok_durumu')
            return jsonify({'success': False, 'error': str(e)}), 500


    # ==================== ANA DEPO TEDARİK GEÇMİŞİ ====================
    
    @app.route('/admin/ana-depo-tedarik-gecmisi')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_ana_depo_tedarik_gecmisi():
        """Sistem yöneticisi için tüm otellerin ana depo tedarik geçmişi"""
        from models import AnaDepoTedarik, AnaDepoTedarikDetay, Urun
        from datetime import datetime
        
        try:
            # Filtreler
            otel_id = request.args.get('otel_id', type=int)
            ay = request.args.get('ay', type=int, default=datetime.now().month)
            yil = request.args.get('yil', type=int, default=datetime.now().year)
            durum = request.args.get('durum', '')
            
            # Tedarik sorgusu
            query = AnaDepoTedarik.query
            
            # Otel filtresi
            if otel_id:
                query = query.filter(AnaDepoTedarik.otel_id == otel_id)
            
            # Ay/Yıl filtresi
            from sqlalchemy import extract
            query = query.filter(
                extract('month', AnaDepoTedarik.islem_tarihi) == ay,
                extract('year', AnaDepoTedarik.islem_tarihi) == yil
            )
            
            # Durum filtresi
            if durum:
                query = query.filter(AnaDepoTedarik.durum == durum)
            
            # Sıralama ve sonuçlar
            tedarikler = query.order_by(AnaDepoTedarik.islem_tarihi.desc()).all()
            
            # Oteller listesi (filtre için)
            oteller = Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()
            
            # İstatistikler
            toplam_tedarik = len(tedarikler)
            aktif_sayi = sum(1 for t in tedarikler if t.durum == 'aktif')
            iptal_sayi = sum(1 for t in tedarikler if t.durum == 'iptal')
            
            # Tedarik detayları
            tedarik_listesi = []
            for tedarik in tedarikler:
                detaylar = AnaDepoTedarikDetay.query.filter_by(tedarik_id=tedarik.id).all()
                toplam_urun = sum(d.miktar for d in detaylar)
                
                # Otel bilgisi
                otel = db.session.get(Otel, tedarik.otel_id)
                
                # Kullanıcı bilgisi (depo sorumlusu)
                kullanici = db.session.get(Kullanici, tedarik.depo_sorumlusu_id) if tedarik.depo_sorumlusu_id else None
                
                tedarik_listesi.append({
                    'id': tedarik.id,
                    'otel_adi': otel.ad if otel else 'Bilinmiyor',
                    'tarih': tedarik.islem_tarihi,
                    'durum': tedarik.durum,
                    'toplam_urun': toplam_urun,
                    'detay_sayisi': len(detaylar),
                    'kullanici': f"{kullanici.ad} {kullanici.soyad}" if kullanici else 'Bilinmiyor',
                    'aciklama': tedarik.aciklama,
                    'detaylar': [{
                        'urun_adi': db.session.get(Urun, d.urun_id).urun_adi if db.session.get(Urun, d.urun_id) else 'Bilinmiyor',
                        'miktar': d.miktar
                    } for d in detaylar]
                })
            
            return render_template(
                'sistem_yoneticisi/ana_depo_tedarik_gecmisi.html',
                tedarikler=tedarik_listesi,
                oteller=oteller,
                secili_otel_id=otel_id,
                secili_ay=ay,
                secili_yil=yil,
                secili_durum=durum,
                istatistikler={
                    'toplam': toplam_tedarik,
                    'aktif': aktif_sayi,
                    'iptal': iptal_sayi
                }
            )
            
        except Exception as e:
            log_hata(e, 'admin_ana_depo_tedarik_gecmisi')
            flash('Tedarik geçmişi yüklenirken hata oluştu.', 'error')
            return redirect(url_for('sistem_yoneticisi_dashboard'))
