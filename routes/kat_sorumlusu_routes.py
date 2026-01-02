"""
Kat Sorumlusu Routes Modülü

Bu modül kat sorumlusu ile ilgili endpoint'leri içerir.

Endpoint'ler:
- /dolum-talepleri - Dolum talepleri sayfası
- /minibar-kontrol - Minibar kontrol işlemleri
- /kat-odalari - Kata göre oda listesi (JSON)
- /minibar-urunler - Minibar ürünleri (JSON)
- /toplu-oda-doldurma - Toplu oda doldurma sayfası
- /kat-bazli-rapor - Kat bazlı rapor
- /zimmetim - Zimmet görüntüleme
- /kat-raporlar - Kat sorumlusu raporları
- /kat-sorumlusu/zimmet-stoklarim - Zimmet stokları
- /kat-sorumlusu/kritik-stoklar - Kritik stoklar
- /kat-sorumlusu/siparis-hazirla - Sipariş hazırlama
- /kat-sorumlusu/urun-gecmisi/<int:urun_id> - Ürün geçmişi
- /kat-sorumlusu/zimmet-export - Zimmet export
- /kat-sorumlusu/ilk-dolum - İlk dolum sayfası
- /kat-sorumlusu/oda-kontrol - Oda kontrol sayfası

Roller:
- kat_sorumlusu
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timedelta, timezone
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import pytz

from models import (
    db, Kat, Oda, UrunGrup, Urun, PersonelZimmet, PersonelZimmetDetay,
    MinibarIslem, MinibarIslemDetay, Kullanici
)
from sqlalchemy.orm import joinedload, selectinload
from utils.decorators import login_required, role_required
from utils.helpers import log_islem, log_hata
from utils.audit import audit_create
from utils.query_helpers_optimized import get_minibar_islemler_optimized

# KKTC Timezone (Kıbrıs - Europe/Nicosia)
KKTC_TZ = pytz.timezone('Europe/Nicosia')

def get_kktc_now():
    """Kıbrıs saat diliminde şu anki zamanı döndürür."""
    return datetime.now(KKTC_TZ)

def register_kat_sorumlusu_routes(app):
    """Kat sorumlusu route'larını kaydet"""
    
    # CSRF protection instance'ını al
    csrf = app.extensions.get('csrf')
    
    @app.route('/kat-sorumlusu/minibar-islemlerim')
    @login_required
    @role_required('kat_sorumlusu')
    def minibar_islemlerim():
        """Minibar işlemlerimi görüntüleme sayfası"""
        return render_template('kat_sorumlusu/minibar_islemleri.html')
    
    @app.route('/kat-sorumlusu/oda-kontrol')
    @login_required
    @role_required('kat_sorumlusu')
    def oda_kontrol():
        """Setup bazlı oda kontrol sayfası"""
        try:
            kullanici_id = session.get('kullanici_id')
            
            # Kat sorumlusunun otelini kontrol et
            from utils.authorization import get_kat_sorumlusu_otel
            kullanici_oteli = get_kat_sorumlusu_otel(kullanici_id)
            
            if not kullanici_oteli:
                flash('Otel atamanız bulunamadı. Lütfen yöneticinizle iletişime geçin.', 'danger')
                return redirect(url_for('dashboard'))
            
            # Otele ait katları getir
            katlar = Kat.query.filter_by(
                otel_id=kullanici_oteli.id,
                aktif=True
            ).order_by(Kat.kat_no).all()
            
            return render_template(
                'kat_sorumlusu/oda_kontrol.html',
                katlar=katlar
            )
            
        except Exception as e:
            log_hata(e, modul='oda_kontrol')
            flash('Sayfa yüklenirken hata oluştu', 'danger')
            return redirect(url_for('dashboard'))
    
    @app.route('/dolum-talepleri')
    @login_required
    @role_required('kat_sorumlusu', 'sistem_yoneticisi', 'admin')
    def dolum_talepleri():
        """Dolum talepleri sayfası"""
        return render_template('kat_sorumlusu/dolum_talepleri.html')
    
    @app.route('/minibar-kontrol', methods=['GET', 'POST'])
    @login_required
    @role_required('kat_sorumlusu')
    def minibar_kontrol():
        """Minibar kontrol işlemleri"""
        if request.method == 'POST':
            try:
                oda_id = int(request.form['oda_id'])
                islem_tipi = request.form['islem_tipi']
                aciklama = request.form.get('aciklama', '')
                kullanici_id = session['kullanici_id']
                
                # Kat sorumlusunun otelini kontrol et
                from utils.authorization import get_kat_sorumlusu_otel
                kullanici_oteli = get_kat_sorumlusu_otel(kullanici_id)
                if not kullanici_oteli:
                    flash('Otel atamanız bulunamadı. Lütfen yöneticinizle iletişime geçin.', 'danger')
                    return redirect(url_for('minibar_kontrol'))
                
                # Odanın bu otele ait olduğunu kontrol et
                oda = db.session.get(Oda, oda_id)
                if not oda or oda.kat.otel_id != kullanici_oteli.id:
                    flash('Bu odaya erişim yetkiniz yok.', 'danger')
                    return redirect(url_for('minibar_kontrol'))
                
                # KONTROL İŞLEMİNDE KAYIT OLUŞTURMA - Sadece Görüntüleme
                if islem_tipi == 'kontrol':
                    flash('Kontrol işlemi tamamlandı. (Sadece görüntüleme - kayıt oluşturulmadı)', 'info')
                    log_islem(
                        kullanici_id=kullanici_id,
                        modul='minibar',
                        islem_tipi='kontrol',
                        aciklama=f'Oda {oda_id} minibar kontrolü yapıldı (görüntüleme)'
                    )
                    return redirect(url_for('minibar_kontrol'))
                
                # İlk dolum ve doldurma işlemleri için minibar kaydı oluştur
                islem = MinibarIslem(
                    oda_id=oda_id,
                    personel_id=kullanici_id,
                    islem_tipi=islem_tipi,
                    aciklama=aciklama
                )
                db.session.add(islem)
                db.session.flush()
                
                # Ürün detaylarını işle
                for key, value in request.form.items():
                    if key.startswith('miktar_') and value and int(value) > 0:
                        urun_id = int(key.split('_')[1])
                        miktar = int(value)
                        
                        if islem_tipi in ['ilk_dolum', 'doldurma']:
                            zimmet_detaylar = db.session.query(PersonelZimmetDetay).join(
                                PersonelZimmet, PersonelZimmetDetay.zimmet_id == PersonelZimmet.id
                            ).filter(
                                PersonelZimmet.personel_id == kullanici_id,
                                PersonelZimmet.durum == 'aktif',
                                PersonelZimmetDetay.urun_id == urun_id
                            ).all()
                            
                            if not zimmet_detaylar:
                                urun = db.session.get(Urun, urun_id)
                                urun_adi = urun.urun_adi if urun else 'Bilinmeyen ürün'
                                raise Exception(f'Zimmetinizde bu ürün bulunmuyor: {urun_adi}')
                            
                            toplam_kalan = sum(detay.miktar - detay.kullanilan_miktar for detay in zimmet_detaylar)
                            
                            if toplam_kalan < miktar:
                                urun = db.session.get(Urun, urun_id)
                                urun_adi = urun.urun_adi if urun else 'Bilinmeyen ürün'
                                raise Exception(f'Zimmetinizde yeterli ürün yok: {urun_adi}. Kalan: {toplam_kalan}')
                            
                            # Zimmetlerden sırayla düş (FIFO)
                            kalan_miktar = miktar
                            for zimmet_detay in zimmet_detaylar:
                                if kalan_miktar <= 0:
                                    break
                                detay_kalan = zimmet_detay.miktar - zimmet_detay.kullanilan_miktar
                                if detay_kalan > 0:
                                    kullanilacak = min(detay_kalan, kalan_miktar)
                                    zimmet_detay.kullanilan_miktar += kullanilacak
                                    zimmet_detay.kalan_miktar = zimmet_detay.miktar - zimmet_detay.kullanilan_miktar
                                    kalan_miktar -= kullanilacak
                        
                        detay = MinibarIslemDetay(
                            islem_id=islem.id,
                            urun_id=urun_id,
                            baslangic_stok=0,
                            eklenen_miktar=miktar,
                            bitis_stok=miktar,
                            tuketim=0
                        )
                        db.session.add(detay)
                            
                    elif key.startswith('baslangic_') and value:
                        urun_id = int(key.split('_')[1])
                        baslangic = int(value)
                        bitis = int(request.form.get(f'bitis_{urun_id}', 0))
                        tuketim = max(0, baslangic - bitis)
                        
                        detay = MinibarIslemDetay(
                            islem_id=islem.id,
                            urun_id=urun_id,
                            baslangic_stok=baslangic,
                            bitis_stok=bitis,
                            tuketim=tuketim
                        )
                        db.session.add(detay)
                        
                        if islem_tipi == 'doldurma' and tuketim > 0:
                            zimmet_detaylar = db.session.query(PersonelZimmetDetay).join(
                                PersonelZimmet, PersonelZimmetDetay.zimmet_id == PersonelZimmet.id
                            ).filter(
                                PersonelZimmet.personel_id == kullanici_id,
                                PersonelZimmet.durum == 'aktif',
                                PersonelZimmetDetay.urun_id == urun_id
                            ).all()
                            
                            if zimmet_detaylar:
                                toplam_kalan = sum(d.miktar - d.kullanilan_miktar for d in zimmet_detaylar)
                                if toplam_kalan >= tuketim:
                                    kalan_tuketim = tuketim
                                    for zimmet_detay in zimmet_detaylar:
                                        if kalan_tuketim <= 0:
                                            break
                                        detay_kalan = zimmet_detay.miktar - zimmet_detay.kullanilan_miktar
                                        if detay_kalan > 0:
                                            kullanilacak = min(detay_kalan, kalan_tuketim)
                                            zimmet_detay.kullanilan_miktar += kullanilacak
                                            zimmet_detay.kalan_miktar = zimmet_detay.miktar - zimmet_detay.kullanilan_miktar
                                            kalan_tuketim -= kullanilacak
                
                db.session.commit()
                audit_create('minibar_islem', islem.id, islem)
                
                # GÖREV TAMAMLAMA ENTEGRASYONu - Minibar işlemi yapıldığında ilgili görevi tamamla
                try:
                    from utils.gorev_service import GorevService
                    from models import GorevDetay, GunlukGorev
                    from datetime import date
                    
                    # Bugünkü görevlerde bu oda var mı kontrol et
                    gorev_detay = GorevDetay.query.join(GunlukGorev).filter(
                        GunlukGorev.otel_id == kullanici_oteli.id,
                        GunlukGorev.gorev_tarihi == date.today(),
                        GorevDetay.oda_id == oda_id,
                        GorevDetay.durum.in_(['pending', 'in_progress', 'dnd_pending'])
                    ).first()
                    
                    if gorev_detay:
                        # Görevi tamamla
                        GorevService.complete_task(gorev_detay.id, kullanici_id, f'Minibar {islem_tipi} işlemi yapıldı')
                        flash('Minibar işlemi başarıyla kaydedildi ve görev tamamlandı. ✓', 'success')
                    else:
                        flash('Minibar işlemi başarıyla kaydedildi. Zimmetinizden düşürülen ürünler güncellendi.', 'success')
                except Exception as gorev_err:
                    # Görev tamamlama hatası ana işlemi etkilemesin
                    print(f"Görev tamamlama hatası: {str(gorev_err)}")
                    flash('Minibar işlemi başarıyla kaydedildi. Zimmetinizden düşürülen ürünler güncellendi.', 'success')
                
                log_islem(
                    kullanici_id=kullanici_id,
                    modul='minibar',
                    islem_tipi=islem_tipi,
                    aciklama=f'Oda {oda_id} - {islem_tipi} işlemi'
                )
                return redirect(url_for('minibar_kontrol'))
                
            except Exception as e:
                db.session.rollback()
                log_hata(
                    exception=e,
                    modul='minibar',
                    extra_info={
                        'oda_id': request.form.get('oda_id'),
                        'islem_tipi': request.form.get('islem_tipi'),
                        'kullanici_id': session.get('kullanici_id')
                    }
                )
                flash(f'Hata oluştu: {str(e)}', 'danger')
        
        # Kat sorumlusunun sadece kendi otelindeki katları göster
        from utils.authorization import get_kat_sorumlusu_otel
        kullanici_id = session['kullanici_id']
        kullanici_oteli = get_kat_sorumlusu_otel(kullanici_id)
        
        if kullanici_oteli:
            katlar = Kat.query.filter_by(
                otel_id=kullanici_oteli.id,
                aktif=True
            ).order_by(Kat.kat_no).all()
        else:
            katlar = []
            flash('Otel atamanız bulunamadı. Lütfen yöneticinizle iletişime geçin.', 'warning')
        
        urun_gruplari = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
        return render_template('kat_sorumlusu/minibar_kontrol.html', 
                             katlar=katlar,
                             urun_gruplari=urun_gruplari)
    
    @app.route('/kat-odalari')
    @login_required
    @role_required('kat_sorumlusu')
    def kat_odalari():
        """Seçilen kata ait odaları JSON olarak döndür"""
        try:
            kat_id = request.args.get('kat_id', type=int)
            if not kat_id:
                return jsonify({'success': False, 'error': 'Kat ID gerekli'})
            
            # Kat sorumlusunun otelini kontrol et
            from utils.authorization import get_kat_sorumlusu_otel
            kullanici_id = session['kullanici_id']
            kullanici_oteli = get_kat_sorumlusu_otel(kullanici_id)
            
            if not kullanici_oteli:
                return jsonify({'success': False, 'error': 'Otel atamanız bulunamadı'})
            
            # Katın bu otele ait olduğunu kontrol et
            kat = db.session.get(Kat, kat_id)
            if not kat or kat.otel_id != kullanici_oteli.id:
                return jsonify({'success': False, 'error': 'Bu kata erişim yetkiniz yok'})
            
            odalar = Oda.query.filter_by(kat_id=kat_id, aktif=True).order_by(Oda.oda_no).all()
            
            oda_listesi = []
            for oda in odalar:
                oda_listesi.append({
                    'id': oda.id,
                    'oda_no': oda.oda_no
                })
            
            return jsonify({'success': True, 'odalar': oda_listesi})
        except Exception as e:
            log_hata(e, modul='kat_odalari')
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/minibar-urunler')
    @login_required
    @role_required('kat_sorumlusu')
    def minibar_urunler():
        """Minibar ürünlerini JSON olarak döndür"""
        try:
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.grup_id, Urun.urun_adi).all()
            
            # Kullanıcının zimmet bilgilerini getir
            kullanici_id = session.get('kullanici_id')
            aktif_zimmetler = PersonelZimmet.query.filter_by(
                personel_id=kullanici_id,
                durum='aktif'
            ).all()
            
            # Her ürün için toplam zimmet miktarını hesapla
            zimmet_dict = {}
            for zimmet in aktif_zimmetler:
                for detay in zimmet.detaylar:
                    if detay.urun_id not in zimmet_dict:
                        zimmet_dict[detay.urun_id] = 0
                    zimmet_dict[detay.urun_id] += (detay.kalan_miktar or 0)
            
            urun_listesi = []
            for urun in urunler:
                urun_listesi.append({
                    'id': urun.id,
                    'urun_adi': urun.urun_adi,
                    'grup_id': urun.grup_id,
                    'grup_adi': urun.grup.grup_adi,
                    'birim': urun.birim,
                    'zimmet_miktari': zimmet_dict.get(urun.id, 0)
                })
            
            return jsonify({'success': True, 'urunler': urun_listesi})
        except Exception as e:
            log_hata(e, modul='minibar_urunler')
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/toplu-oda-doldurma', methods=['GET'])
    @login_required
    @role_required('kat_sorumlusu')
    def toplu_oda_doldurma():
        """Toplu oda doldurma sayfası"""
        # Kat sorumlusunun sadece kendi otelindeki katları göster
        from utils.authorization import get_kat_sorumlusu_otel
        kullanici_id = session['kullanici_id']
        kullanici_oteli = get_kat_sorumlusu_otel(kullanici_id)
        
        if kullanici_oteli:
            katlar = Kat.query.filter_by(
                otel_id=kullanici_oteli.id,
                aktif=True
            ).order_by(Kat.kat_no).all()
        else:
            katlar = []
            flash('Otel atamanız bulunamadı. Lütfen yöneticinizle iletişime geçin.', 'warning')
        
        urun_gruplari = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
        return render_template('kat_sorumlusu/toplu_oda_doldurma.html',
                             katlar=katlar,
                             urun_gruplari=urun_gruplari)


    @app.route('/kat-bazli-rapor', methods=['GET'])
    @login_required
    @role_required('kat_sorumlusu', 'admin', 'depo_sorumlusu')
    def kat_bazli_rapor():
        """Kat bazlı tüketim raporu sayfası"""
        from utils.authorization import get_kullanici_otelleri
        from models import Otel
        kullanici_id = session['kullanici_id']
        kullanici_rol = session.get('rol')
        
        # Kullanıcının erişebileceği otelleri getir
        kullanici_otelleri = get_kullanici_otelleri(kullanici_id)
        otel_idleri = [otel.id for otel in kullanici_otelleri]
        
        # Otelleri template'e gönder
        if otel_idleri:
            oteller = Otel.query.filter(
                Otel.id.in_(otel_idleri),
                Otel.aktif == True
            ).order_by(Otel.ad).all()
        else:
            oteller = []
            if kullanici_rol == 'kat_sorumlusu':
                flash('Otel atamanız bulunamadı. Lütfen yöneticinizle iletişime geçin.', 'warning')
        
        return render_template('raporlar/kat_bazli_rapor.html', oteller=oteller)
    
    @app.route('/api/otelin-katlari', methods=['GET'])
    @login_required
    @role_required('kat_sorumlusu', 'admin', 'depo_sorumlusu')
    def api_otelin_katlari():
        """Seçilen otele ait katları JSON olarak döndür"""
        try:
            otel_id = request.args.get('otel_id', type=int)
            if not otel_id:
                return jsonify({'success': False, 'error': 'Otel ID gerekli'})
            
            # Kullanıcının bu otele erişim yetkisi var mı kontrol et
            from utils.authorization import get_kullanici_otelleri
            kullanici_id = session['kullanici_id']
            kullanici_otelleri = get_kullanici_otelleri(kullanici_id)
            otel_idleri = [otel.id for otel in kullanici_otelleri]
            
            if otel_id not in otel_idleri:
                return jsonify({'success': False, 'error': 'Bu otele erişim yetkiniz yok'})
            
            katlar = Kat.query.filter_by(
                otel_id=otel_id,
                aktif=True
            ).order_by(Kat.kat_no).all()
            
            kat_listesi = []
            for kat in katlar:
                kat_listesi.append({
                    'id': kat.id,
                    'kat_adi': f"{kat.kat_no}. Kat" if kat.kat_no else kat.kat_adi,
                    'kat_no': kat.kat_no
                })
            
            return jsonify({'success': True, 'katlar': kat_listesi})
        except Exception as e:
            log_hata(e, modul='api_otelin_katlari')
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/zimmetim')
    @login_required
    @role_required('kat_sorumlusu')
    def zimmetim():
        """Zimmet görüntüleme"""
        kullanici_id = session['kullanici_id']
        
        aktif_zimmetler = PersonelZimmet.query.filter_by(
            personel_id=kullanici_id, 
            durum='aktif'
        ).order_by(PersonelZimmet.zimmet_tarihi.desc()).all()
        
        toplam_zimmet = 0
        kalan_zimmet = 0
        kullanilan_zimmet = 0
        
        for zimmet in aktif_zimmetler:
            for detay in zimmet.detaylar:
                toplam_zimmet += detay.miktar
                kullanilan_zimmet += detay.kullanilan_miktar
                kalan = detay.kalan_miktar or (detay.miktar - detay.kullanilan_miktar)
                kalan_zimmet += kalan
        
        return render_template('kat_sorumlusu/zimmetim.html',
                             aktif_zimmetler=aktif_zimmetler,
                             toplam_zimmet=toplam_zimmet,
                             kalan_zimmet=kalan_zimmet,
                             kullanilan_zimmet=kullanilan_zimmet)
    
    @app.route('/kat-raporlar')
    @login_required
    @role_required('kat_sorumlusu')
    def kat_raporlar():
        """Kat sorumlusu raporları"""
        rapor_tipi = request.args.get('rapor_tipi', 'minibar_islem')
        baslangic_tarihi = request.args.get('baslangic_tarihi')
        bitis_tarihi = request.args.get('bitis_tarihi')
        
        rapor_verisi = []
        rapor_baslik = ""
        kullanici_id = session['kullanici_id']
        
        if rapor_tipi == 'minibar_islem':
            rapor_baslik = "Minibar İşlem Raporu"
            # Optimized query - N+1 problemi çözüldü
            query = MinibarIslem.query.options(
                joinedload(MinibarIslem.oda).joinedload(Oda.kat),
                joinedload(MinibarIslem.personel),
                selectinload(MinibarIslem.detaylar).joinedload(MinibarIslemDetay.urun)
            ).filter_by(personel_id=kullanici_id)
            
            if baslangic_tarihi:
                query = query.filter(MinibarIslem.islem_tarihi >= datetime.strptime(baslangic_tarihi, '%Y-%m-%d'))
            if bitis_tarihi:
                query = query.filter(MinibarIslem.islem_tarihi <= datetime.strptime(bitis_tarihi, '%Y-%m-%d') + timedelta(days=1))
            
            rapor_verisi = query.order_by(MinibarIslem.islem_tarihi.desc()).all()
        
        return render_template('kat_sorumlusu/raporlar.html', 
                             rapor_verisi=rapor_verisi, 
                             rapor_baslik=rapor_baslik,
                             rapor_tipi=rapor_tipi)
    
    @app.route('/kat-sorumlusu/siparis-listesi')
    @login_required
    @role_required('kat_sorumlusu')
    def kat_sorumlusu_siparis_listesi():
        """Kat sorumlusu sipariş talepleri listesi"""
        try:
            from models import KatSorumlusuSiparisTalebi, KatSorumlusuSiparisTalepDetay
            
            kullanici_id = session['kullanici_id']
            
            # Kat sorumlusunun tüm sipariş taleplerini getir
            siparisler = KatSorumlusuSiparisTalebi.query.filter_by(
                kat_sorumlusu_id=kullanici_id
            ).order_by(
                KatSorumlusuSiparisTalebi.talep_tarihi.desc()
            ).all()
            
            # Her sipariş için detayları yükle
            for siparis in siparisler:
                siparis.detaylar_list = KatSorumlusuSiparisTalepDetay.query.filter_by(
                    talep_id=siparis.id
                ).all()
            
            return render_template('kat_sorumlusu/siparis_listesi.html', 
                                 siparisler=siparisler)
                                 
        except Exception as e:
            log_hata(e, modul='kat_sorumlusu_siparis_listesi')
            flash(f'Sipariş listesi yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))


    # ============================================================================
    # SETUP BAZLI MİNİBAR KONTROL API ENDPOINT'LERİ
    # ============================================================================
    
    @app.route('/api/kat-sorumlusu/oda-setup/<int:oda_id>', methods=['GET'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_oda_setup_durumu(oda_id):
        """
        Odanın setup durumunu ve ürün listesini getirir
        
        Args:
            oda_id (int): Oda ID
            
        Returns:
            JSON: Oda bilgileri, setup'lar ve ürün durumları
        """
        try:
            from utils.minibar_servisleri import (
                oda_setup_durumu_getir,
                OdaTipiNotFoundError,
                SetupNotFoundError
            )
            from models import OtelZimmetStok, GorevDetay, GunlukGorev
            from datetime import date
            
            # Oda setup durumunu getir
            sonuc = oda_setup_durumu_getir(oda_id)
            
            # Kat sorumlusunun OTEL BAZLI zimmet stoklarını getir
            kullanici_id = session.get('kullanici_id')
            kullanici = Kullanici.query.get(kullanici_id)
            
            zimmet_stoklar = {}
            
            if kullanici and kullanici.otel_id:
                # Otel bazlı ortak zimmet deposundan stokları çek
                otel_stoklar = OtelZimmetStok.query.filter_by(
                    otel_id=kullanici.otel_id
                ).filter(OtelZimmetStok.kalan_miktar > 0).all()
                
                for stok in otel_stoklar:
                    urun_key = str(stok.urun_id)
                    zimmet_stoklar[urun_key] = {
                        'miktar': stok.kalan_miktar,
                        'otel_zimmet_stok_id': stok.id
                    }
            
            sonuc['kat_sorumlusu_stok'] = zimmet_stoklar
            
            # Bugünkü minibar işlemlerini getir
            bugun = date.today()
            bugunun_islemleri = MinibarIslem.query.options(
                selectinload(MinibarIslem.detaylar).joinedload(MinibarIslemDetay.urun)
            ).filter(
                MinibarIslem.oda_id == oda_id,
                db.func.date(MinibarIslem.islem_tarihi) == bugun
            ).order_by(MinibarIslem.islem_tarihi.desc()).all()
            
            gunluk_islemler = []
            for islem in bugunun_islemleri:
                islem_detaylari = []
                for detay in islem.detaylar:
                    islem_detaylari.append({
                        'urun_id': detay.urun_id,
                        'urun_adi': detay.urun.urun_adi if detay.urun else 'Bilinmiyor',
                        'eklenen_miktar': detay.eklenen_miktar or 0,
                        'tuketim': detay.tuketim or 0,
                        'ekstra_miktar': detay.ekstra_miktar or 0
                    })
                
                gunluk_islemler.append({
                    'islem_id': islem.id,
                    'islem_tipi': islem.islem_tipi,
                    'islem_tarihi': islem.islem_tarihi.strftime('%H:%M') if islem.islem_tarihi else None,
                    'aciklama': islem.aciklama,
                    'detaylar': islem_detaylari
                })
            
            sonuc['gunluk_islemler'] = gunluk_islemler
            sonuc['bugun_islem_yapildi'] = len(gunluk_islemler) > 0
            
            # Görev durumunu getir (OTEL BAZLI)
            gorev_durumu = None
            if kullanici and kullanici.otel_id:
                gorev_detay = GorevDetay.query.join(GunlukGorev).filter(
                    GunlukGorev.otel_id == kullanici.otel_id,
                    GunlukGorev.gorev_tarihi == bugun,
                    GorevDetay.oda_id == oda_id
                ).first()
                
                if gorev_detay:
                    gorev_durumu = {
                        'detay_id': gorev_detay.id,
                        'durum': gorev_detay.durum,
                        'gorev_tipi': gorev_detay.gorev.gorev_tipi if gorev_detay.gorev else None,
                        'dnd_sayisi': gorev_detay.dnd_sayisi,
                        'kontrol_zamani': gorev_detay.kontrol_zamani.strftime('%H:%M') if gorev_detay.kontrol_zamani else None
                    }
            
            sonuc['gorev_durumu'] = gorev_durumu
            
            # Bugünkü kontrol durumunu getir (oda_kontrol_kayitlari + gorev_detaylari)
            from models import OdaKontrolKaydi, OdaDNDKayit
            
            kontrol_durumu = None
            
            # 1. Önce görev detaylarından kontrol et (DND veya completed)
            if gorev_durumu:
                if gorev_durumu['durum'] == 'completed':
                    kontrol_durumu = {
                        'durum': 'completed',
                        'saat': gorev_durumu['kontrol_zamani'],
                        'tip': 'Kontrol Edildi'
                    }
                elif gorev_durumu['durum'] == 'dnd_pending' and gorev_durumu['dnd_sayisi'] > 0:
                    kontrol_durumu = {
                        'durum': 'dnd',
                        'saat': gorev_durumu['kontrol_zamani'],
                        'tip': f"DND ({gorev_durumu['dnd_sayisi']}. deneme)"
                    }
            
            # 2. Bağımsız DND kayıtlarını kontrol et
            if not kontrol_durumu:
                dnd_kayit = OdaDNDKayit.query.filter(
                    OdaDNDKayit.oda_id == oda_id,
                    OdaDNDKayit.kayit_tarihi == bugun
                ).first()
                
                if dnd_kayit:
                    kontrol_durumu = {
                        'durum': 'dnd',
                        'saat': dnd_kayit.son_kontrol_zamani.strftime('%H:%M') if dnd_kayit.son_kontrol_zamani else None,
                        'tip': f"DND ({dnd_kayit.kontrol_sayisi}. deneme)"
                    }
            
            # 3. Oda kontrol kayıtlarından kontrol et (sarfiyat_yok veya urun_eklendi)
            if not kontrol_durumu:
                kontrol_kayit = OdaKontrolKaydi.query.filter(
                    OdaKontrolKaydi.oda_id == oda_id,
                    OdaKontrolKaydi.kontrol_tarihi == bugun,
                    OdaKontrolKaydi.bitis_zamani.isnot(None)
                ).order_by(OdaKontrolKaydi.bitis_zamani.desc()).first()
                
                if kontrol_kayit:
                    if kontrol_kayit.kontrol_tipi == 'sarfiyat_yok':
                        kontrol_durumu = {
                            'durum': 'sarfiyat_yok',
                            'saat': kontrol_kayit.bitis_zamani.strftime('%H:%M') if kontrol_kayit.bitis_zamani else None,
                            'tip': 'Sarfiyat Yok'
                        }
                    else:
                        kontrol_durumu = {
                            'durum': 'completed',
                            'saat': kontrol_kayit.bitis_zamani.strftime('%H:%M') if kontrol_kayit.bitis_zamani else None,
                            'tip': 'Kontrol Edildi'
                        }
            
            # 4. Bugünkü minibar işlemlerinden kontrol et
            if not kontrol_durumu and len(gunluk_islemler) > 0:
                son_islem = gunluk_islemler[0]  # En son işlem
                kontrol_durumu = {
                    'durum': 'completed',
                    'saat': son_islem['islem_tarihi'],
                    'tip': 'Kontrol Edildi'
                }
            
            sonuc['kontrol_durumu'] = kontrol_durumu
            
            # Audit log
            audit_create(
                tablo_adi='oda_setup',
                kayit_id=oda_id,
                yeni_deger={'oda_no': sonuc['oda']['oda_no']},
                aciklama=f"Oda {sonuc['oda']['oda_no']} setup durumu görüntülendi"
            )
            
            return jsonify({
                'success': True,
                **sonuc
            })
            
        except OdaTipiNotFoundError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 404
            
        except SetupNotFoundError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 404
            
        except Exception as e:
            log_hata(e, modul='api_oda_setup_durumu')
            return jsonify({
                'success': False,
                'error': 'Oda setup durumu getirilirken hata oluştu'
            }), 500
    
    
    @app.route('/api/kat-sorumlusu/urun-ekle', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_urun_ekle():
        """
        Eksik ürün ekleme ve tüketim kaydetme
        
        Request Body:
            {
                "oda_id": 101,
                "urun_id": 5,
                "setup_id": 1,
                "eklenen_miktar": 1,
                "zimmet_detay_id": 45
            }
            
        Returns:
            JSON: İşlem sonucu
        """
        try:
            from utils.minibar_servisleri import (
                tuketim_hesapla,
                zimmet_stok_kontrol,
                zimmet_stok_dusu,
                tuketim_kaydet,
                ZimmetStokYetersizError
            )
            
            # Request validasyonu
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Geçersiz istek'
                }), 400
            
            oda_id = data.get('oda_id')
            urun_id = data.get('urun_id')
            setup_id = data.get('setup_id')
            eklenen_miktar = data.get('eklenen_miktar')
            zimmet_detay_id = data.get('zimmet_detay_id')
            
            # Validasyon
            if not all([oda_id, urun_id, setup_id, eklenen_miktar]):
                return jsonify({
                    'success': False,
                    'error': 'Eksik parametreler'
                }), 400
            
            if eklenen_miktar <= 0:
                return jsonify({
                    'success': False,
                    'error': 'Eklenen miktar 0\'dan büyük olmalıdır'
                }), 400
            
            kullanici_id = session.get('kullanici_id')
            
            # Transaction başlat
            try:
                # Setup miktarını bul
                from models import SetupIcerik
                setup_icerik = SetupIcerik.query.filter_by(
                    setup_id=setup_id,
                    urun_id=urun_id
                ).first()
                
                if not setup_icerik:
                    return jsonify({
                        'success': False,
                        'error': 'Ürün bu setup\'ta bulunamadı'
                    }), 404
                
                setup_miktari = setup_icerik.adet
                
                # Tüketim hesapla
                tuketim = tuketim_hesapla(oda_id, urun_id, setup_miktari, eklenen_miktar)
                
                # Zimmet stok kontrolü
                zimmet_stok_kontrol(kullanici_id, urun_id, eklenen_miktar)
                
                # Zimmet stoğundan düş (Otel bazlı sistem - kullanım kaydı otomatik oluşur)
                otel_stok = zimmet_stok_dusu(
                    kullanici_id,
                    urun_id,
                    eklenen_miktar
                )
                
                # Tüketimi kaydet (zimmet_detay_id artık kullanılmıyor, kullanım personel_zimmet_kullanim'da)
                # tuketim_kaydet artık görev tamamlama işlemini de yapıyor
                islem = tuketim_kaydet(
                    oda_id=oda_id,
                    urun_id=urun_id,
                    miktar=tuketim,
                    personel_id=kullanici_id,
                    islem_tipi='setup_kontrol',
                    eklenen_miktar=eklenen_miktar,
                    ekstra_miktar=0,
                    zimmet_detay_id=None
                )
                
                # Oda ve ürün bilgilerini getir
                oda = Oda.query.get(oda_id)
                urun = Urun.query.get(urun_id)
                
                # Görev tamamlama durumunu al
                gorev_tamamlandi = getattr(islem, 'gorev_tamamlandi', False)
                
                # Audit log
                audit_create(
                    tablo_adi='minibar_islem',
                    kayit_id=oda_id,
                    yeni_deger={'oda_no': oda.oda_no, 'urun': urun.urun_adi, 'miktar': eklenen_miktar},
                    aciklama=f"Oda {oda.oda_no} - {urun.urun_adi} eklendi (Miktar: {eklenen_miktar}, Tüketim: {tuketim})"
                )
                
                mesaj = 'Ürün başarıyla eklendi'
                if gorev_tamamlandi:
                    mesaj += ' - Görev tamamlandı!'
                
                # otel_stok'tan kalan miktarı al (OtelZimmetStok objesi)
                zimmet_kalan = otel_stok.kalan_miktar if otel_stok else 0
                
                return jsonify({
                    'success': True,
                    'message': mesaj,
                    'tuketim': tuketim,
                    'yeni_miktar': setup_miktari,
                    'zimmet_kalan': zimmet_kalan,
                    'gorev_tamamlandi': gorev_tamamlandi
                })
                
            except ZimmetStokYetersizError as e:
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'zimmet_mevcut': e.mevcut,
                    'gereken_miktar': e.gereken
                }), 400
                
            except Exception as e:
                db.session.rollback()
                raise
            
        except Exception as e:
            log_hata(e, modul='api_urun_ekle')
            return jsonify({
                'success': False,
                'error': 'Ürün eklenirken hata oluştu'
            }), 500
    
    
    @app.route('/api/kat-sorumlusu/ekstra-ekle', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_ekstra_ekle():
        """
        Setup üstü ekstra ürün ekleme
        
        Request Body:
            {
                "oda_id": 101,
                "urun_id": 8,
                "setup_id": 1,
                "ekstra_miktar": 2,
                "zimmet_detay_id": 46
            }
            
        Returns:
            JSON: İşlem sonucu
        """
        try:
            from utils.minibar_servisleri import (
                zimmet_stok_kontrol,
                zimmet_stok_dusu,
                tuketim_kaydet,
                minibar_stok_guncelle,
                ZimmetStokYetersizError
            )
            from models import SetupIcerik
            
            # Request validasyonu
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Geçersiz istek'
                }), 400
            
            oda_id = data.get('oda_id')
            urun_id = data.get('urun_id')
            setup_id = data.get('setup_id')
            ekstra_miktar = data.get('ekstra_miktar')
            zimmet_detay_id = data.get('zimmet_detay_id')
            
            # Validasyon
            if not all([oda_id, urun_id, setup_id, ekstra_miktar]):
                return jsonify({
                    'success': False,
                    'error': 'Eksik parametreler'
                }), 400
            
            if ekstra_miktar <= 0:
                return jsonify({
                    'success': False,
                    'error': 'Ekstra miktar 0\'dan büyük olmalıdır'
                }), 400
            
            kullanici_id = session.get('kullanici_id')
            
            # Transaction başlat
            try:
                # Zimmet stok kontrolü
                zimmet_stok_kontrol(kullanici_id, urun_id, ekstra_miktar)
                
                # Zimmet stoğundan düş (Otel bazlı sistem)
                otel_stok = zimmet_stok_dusu(
                    kullanici_id,
                    urun_id,
                    ekstra_miktar
                )
                
                # Mevcut stok durumunu getir
                stok_durumu = minibar_stok_guncelle(
                    oda_id,
                    urun_id,
                    ekstra_miktar,
                    ekstra_miktar
                )
                
                # Ekstra eklemeyi kaydet (tüketim=0)
                tuketim_kaydet(
                    oda_id=oda_id,
                    urun_id=urun_id,
                    miktar=0,  # Tüketim yok
                    personel_id=kullanici_id,
                    islem_tipi='ekstra_ekleme',
                    eklenen_miktar=ekstra_miktar,
                    ekstra_miktar=ekstra_miktar,
                    zimmet_detay_id=None
                )
                
                # Oda ve ürün bilgilerini getir
                oda = Oda.query.get(oda_id)
                urun = Urun.query.get(urun_id)
                
                # Audit log
                audit_create(
                    tablo_adi='minibar_islem',
                    kayit_id=oda_id,
                    yeni_deger={'oda_id': oda_id, 'urun_id': urun_id, 'ekstra_miktar': ekstra_miktar},
                    aciklama=f"Oda {oda.oda_no} - {urun.urun_adi} ekstra eklendi (Miktar: {ekstra_miktar})"
                )
                
                yeni_miktar = stok_durumu['baslangic_stok'] + ekstra_miktar
                
                # otel_stok'tan kalan miktarı al
                zimmet_kalan = otel_stok.kalan_miktar if otel_stok else 0
                
                return jsonify({
                    'success': True,
                    'message': 'Ekstra ürün başarıyla eklendi',
                    'yeni_miktar': yeni_miktar,
                    'ekstra_miktar': ekstra_miktar,
                    'zimmet_kalan': zimmet_kalan
                })
                
            except ZimmetStokYetersizError as e:
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'zimmet_mevcut': e.mevcut,
                    'gereken_miktar': e.gereken
                }), 400
                
            except Exception as e:
                db.session.rollback()
                raise
            
        except Exception as e:
            log_hata(
                e,
                modul='api_ekstra_ekle',
                extra_info={
                    'oda_id': data.get('oda_id'),
                    'urun_id': data.get('urun_id'),
                    'ekstra_miktar': data.get('ekstra_miktar')
                }
            )
            return jsonify({
                'success': False,
                'error': 'Ekstra ürün eklenirken hata oluştu'
            }), 500
    
    
    @app.route('/api/kat-sorumlusu/ekstra-sifirla', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_ekstra_sifirla():
        """
        Ekstra ürün tüketimini kaydet ve sıfırla
        
        Request Body:
            {
                "oda_id": 101,
                "urun_id": 8,
                "setup_id": 1
            }
            
        Returns:
            JSON: İşlem sonucu
        """
        try:
            from utils.minibar_servisleri import tuketim_kaydet
            from sqlalchemy import desc
            
            # Request validasyonu
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Geçersiz istek'
                }), 400
            
            oda_id = data.get('oda_id')
            urun_id = data.get('urun_id')
            setup_id = data.get('setup_id')
            
            # Validasyon
            if not all([oda_id, urun_id, setup_id]):
                return jsonify({
                    'success': False,
                    'error': 'Eksik parametreler'
                }), 400
            
            kullanici_id = session.get('kullanici_id')
            
            # Transaction başlat
            try:
                # Son ekstra miktarı bul
                son_islem_detay = MinibarIslemDetay.query.join(
                    MinibarIslem
                ).filter(
                    MinibarIslem.oda_id == oda_id,
                    MinibarIslemDetay.urun_id == urun_id
                ).order_by(desc(MinibarIslem.islem_tarihi)).first()
                
                if not son_islem_detay or son_islem_detay.ekstra_miktar == 0:
                    return jsonify({
                        'success': False,
                        'error': 'Sıfırlanacak ekstra ürün bulunamadı'
                    }), 404
                
                ekstra_miktar = son_islem_detay.ekstra_miktar
                mevcut_miktar = son_islem_detay.bitis_stok
                
                # Ekstra tüketimi kaydet
                tuketim_kaydet(
                    oda_id=oda_id,
                    urun_id=urun_id,
                    miktar=ekstra_miktar,  # Ekstra miktar tüketim olarak kaydedilir
                    personel_id=kullanici_id,
                    islem_tipi='ekstra_tuketim',
                    eklenen_miktar=0,
                    ekstra_miktar=0,  # Sıfırlandı
                    zimmet_detay_id=None
                )
                
                # Oda ve ürün bilgilerini getir
                oda = Oda.query.get(oda_id)
                urun = Urun.query.get(urun_id)
                
                # Audit log
                audit_create(
                    tablo_adi='minibar_islem',
                    kayit_id=oda_id,
                    yeni_deger={'oda_id': oda_id, 'urun_id': urun_id, 'ekstra_tuketim': ekstra_miktar},
                    aciklama=f"Oda {oda.oda_no} - {urun.urun_adi} ekstra tüketimi kaydedildi (Miktar: {ekstra_miktar})"
                )
                
                yeni_miktar = mevcut_miktar
                
                return jsonify({
                    'success': True,
                    'message': 'Ekstra ürün tüketimi kaydedildi',
                    'tuketim': ekstra_miktar,
                    'yeni_miktar': yeni_miktar,
                    'ekstra_miktar': 0
                })
                
            except Exception as e:
                db.session.rollback()
                raise
            
        except Exception as e:
            log_hata(
                e,
                modul='api_ekstra_sifirla',
                extra_info={
                    'oda_id': data.get('oda_id'),
                    'urun_id': data.get('urun_id')
                }
            )
            return jsonify({
                'success': False,
                'error': 'Ekstra ürün sıfırlanırken hata oluştu'
            }), 500


    # ============================================================================
    # MİNİBAR İŞLEMLERİM API
    # ============================================================================
    
    @app.route('/api/kat-sorumlusu/minibar-islemlerim', methods=['GET'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_minibar_islemlerim():
        """Kat sorumlusunun yaptığı minibar işlemlerini listele (DND kayıtları dahil)"""
        try:
            from datetime import date, datetime
            from models import OdaDNDKayit, OdaDNDKontrol
            
            kullanici_id = session.get('kullanici_id')
            kullanici = Kullanici.query.get(kullanici_id)
            
            # Filtreler
            tarih_str = request.args.get('tarih')
            oda_no = request.args.get('oda')
            islem_tipi = request.args.get('islem_tipi')
            
            # Bugünün tarihi
            bugun = date.today()
            
            # Sonuçları hazırla
            sonuc = []
            
            # ============================================
            # 1. MİNİBAR İŞLEMLERİ
            # ============================================
            if islem_tipi != 'dnd':  # DND filtresi değilse minibar işlemlerini getir
                query = MinibarIslem.query.options(
                    joinedload(MinibarIslem.oda).joinedload(Oda.kat),
                    joinedload(MinibarIslem.personel),
                    selectinload(MinibarIslem.detaylar).joinedload(MinibarIslemDetay.urun)
                ).filter_by(personel_id=kullanici_id)
                
                # Tarih filtresi
                if tarih_str:
                    tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
                    query = query.filter(db.func.date(MinibarIslem.islem_tarihi) == tarih)
                
                # Oda filtresi
                if oda_no:
                    query = query.join(Oda).filter(Oda.oda_no.ilike(f'%{oda_no}%'))
                
                # İşlem tipi filtresi
                if islem_tipi:
                    query = query.filter(MinibarIslem.islem_tipi == islem_tipi)
                
                # Sıralama
                islemler = query.order_by(MinibarIslem.islem_tarihi.desc()).all()
                
                for islem in islemler:
                    islem_tarihi = islem.islem_tarihi.date() if hasattr(islem.islem_tarihi, 'date') else islem.islem_tarihi
                    ayni_gun = islem_tarihi == bugun
                    
                    # Detayları getir
                    detaylar = []
                    for detay in islem.detaylar:
                        detaylar.append({
                            'urun_adi': detay.urun.urun_adi,
                            'setup_miktari': detay.setup_miktari or 0,
                            'baslangic_stok': detay.baslangic_stok,
                            'eklenen_miktar': detay.eklenen_miktar,
                            'tuketim': detay.tuketim,
                            'bitis_stok': detay.bitis_stok
                        })
                    
                    sonuc.append({
                        'id': islem.id,
                        'kayit_tipi': 'minibar',
                        'oda_no': islem.oda.oda_no,
                        'islem_tipi': islem.islem_tipi,
                        'islem_tarihi': islem.islem_tarihi.isoformat(),
                        'aciklama': islem.aciklama,
                        'urun_sayisi': len(detaylar),
                        'detaylar': detaylar,
                        'ayni_gun': ayni_gun
                    })
            
            # ============================================
            # 2. DND KAYITLARI
            # ============================================
            if not islem_tipi or islem_tipi == 'dnd':  # Tümü veya DND filtresi
                # Kullanıcının kontrol ettiği DND kayıtlarını getir
                dnd_query = db.session.query(OdaDNDKayit).join(
                    OdaDNDKontrol, OdaDNDKayit.id == OdaDNDKontrol.dnd_kayit_id
                ).filter(
                    OdaDNDKontrol.kontrol_eden_id == kullanici_id
                ).options(
                    joinedload(OdaDNDKayit.oda),
                    joinedload(OdaDNDKayit.otel)
                ).distinct()
                
                # Tarih filtresi
                if tarih_str:
                    tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
                    dnd_query = dnd_query.filter(OdaDNDKayit.kayit_tarihi == tarih)
                
                # Oda filtresi
                if oda_no:
                    dnd_query = dnd_query.join(Oda, OdaDNDKayit.oda_id == Oda.id).filter(
                        Oda.oda_no.ilike(f'%{oda_no}%')
                    )
                
                dnd_kayitlari = dnd_query.order_by(OdaDNDKayit.olusturma_tarihi.desc()).all()
                
                for dnd in dnd_kayitlari:
                    # Bu kullanıcının yaptığı kontrolleri getir
                    kontroller = OdaDNDKontrol.query.filter_by(
                        dnd_kayit_id=dnd.id,
                        kontrol_eden_id=kullanici_id
                    ).order_by(OdaDNDKontrol.kontrol_no).all()
                    
                    ayni_gun = dnd.kayit_tarihi == bugun
                    
                    # Kontrol detayları
                    kontrol_detaylari = []
                    for k in kontroller:
                        kontrol_detaylari.append({
                            'kontrol_no': k.kontrol_no,
                            'kontrol_zamani': k.kontrol_zamani.isoformat() if k.kontrol_zamani else None,
                            'notlar': k.notlar
                        })
                    
                    sonuc.append({
                        'id': dnd.id,
                        'kayit_tipi': 'dnd',
                        'oda_no': dnd.oda.oda_no if dnd.oda else 'Bilinmiyor',
                        'islem_tipi': 'dnd',
                        'islem_tarihi': dnd.olusturma_tarihi.isoformat() if dnd.olusturma_tarihi else dnd.kayit_tarihi.isoformat(),
                        'aciklama': f'DND - {dnd.dnd_sayisi}/3 kontrol yapıldı',
                        'urun_sayisi': 0,
                        'dnd_sayisi': dnd.dnd_sayisi,
                        'dnd_durum': dnd.durum,
                        'kontroller': kontrol_detaylari,
                        'detaylar': [],
                        'ayni_gun': ayni_gun
                    })
            
            # Tarihe göre sırala (en yeni en üstte)
            sonuc.sort(key=lambda x: x['islem_tarihi'], reverse=True)
            
            return jsonify({
                'success': True,
                'islemler': sonuc
            })
            
        except Exception as e:
            log_hata(e, modul='api_minibar_islemlerim')
            return jsonify({
                'success': False,
                'error': 'İşlemler yüklenirken hata oluştu'
            }), 500
    
    
    @app.route('/api/kat-sorumlusu/minibar-islem-sil/<int:islem_id>', methods=['DELETE'])
    @csrf.exempt
    @login_required
    @role_required('kat_sorumlusu')
    def api_minibar_islem_sil(islem_id):
        """Minibar işlemini sil (sadece aynı gün) - Otel zimmet deposuna iade yapar"""
        try:
            from datetime import date
            from utils.otel_zimmet_servisleri import OtelZimmetServisi
            
            kullanici_id = session.get('kullanici_id')
            kullanici = Kullanici.query.get(kullanici_id)
            
            if not kullanici or not kullanici.otel_id:
                return jsonify({
                    'success': False,
                    'error': 'Otel atamanız bulunamadı'
                }), 400
            
            # İşlemi bul
            islem = MinibarIslem.query.filter_by(
                id=islem_id,
                personel_id=kullanici_id
            ).first()
            
            if not islem:
                return jsonify({
                    'success': False,
                    'error': 'İşlem bulunamadı'
                }), 404
            
            # Aynı gün kontrolü
            islem_tarihi = islem.islem_tarihi.date() if hasattr(islem.islem_tarihi, 'date') else islem.islem_tarihi
            bugun = date.today()
            
            if islem_tarihi != bugun:
                return jsonify({
                    'success': False,
                    'error': 'Sadece bugün yapılan işlemler silinebilir'
                }), 403
            
            # Transaction başlat
            try:
                # Otel zimmet deposuna stok iade et
                for detay in islem.detaylar:
                    iade_miktar = detay.eklenen_miktar or 0
                    if iade_miktar > 0:
                        # Otel zimmet deposuna iade
                        OtelZimmetServisi.stok_iade(
                            otel_id=kullanici.otel_id,
                            urun_id=detay.urun_id,
                            miktar=iade_miktar,
                            personel_id=kullanici_id,
                            referans_id=islem_id,
                            aciklama=f"Minibar işlemi silindi - İade"
                        )
                
                # Oda numarasını önceden al (session kapatılmadan önce)
                oda_no = islem.oda.oda_no
                
                # İşlemi sil
                db.session.delete(islem)
                db.session.commit()
                
                # Audit log
                audit_create(
                    tablo_adi='minibar_islem',
                    kayit_id=islem_id,
                    yeni_deger={'silindi': True},
                    aciklama=f"Minibar işlemi silindi (Oda: {oda_no}) - Stok otel zimmet deposuna iade edildi"
                )
                
                return jsonify({
                    'success': True,
                    'message': 'İşlem başarıyla silindi ve stok iade edildi'
                })
                
            except Exception as e:
                db.session.rollback()
                raise
            
        except Exception as e:
            log_hata(e, modul='api_minibar_islem_sil')
            return jsonify({
                'success': False,
                'error': 'İşlem silinirken hata oluştu'
            }), 500

    
    # ============================================================================
    # SETUP BAZLI MİNİBAR KONTROL - YENİ API ENDPOINT'LERİ
    # ============================================================================
    
    @app.route('/api/kat-sorumlusu/urun-tuketim-ekle', methods=['POST'])
    @csrf.exempt
    @login_required
    @role_required('kat_sorumlusu')
    def api_urun_tuketim_ekle():
        """
        Ürün tüketimi ekle (Ekle butonu)
        Minibar her zaman dolu kabul edilir, tüketim kaydedilir
        
        YENİ SİSTEM: Otel bazlı ortak zimmet deposundan düşer
        
        Request Body:
            {
                "oda_id": 1154,
                "urun_id": 10,
                "miktar": 2
            }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Geçersiz istek'
                }), 400
            
            oda_id = data.get('oda_id')
            urun_id = data.get('urun_id')
            miktar = data.get('miktar')
            
            if not all([oda_id, urun_id, miktar]):
                return jsonify({
                    'success': False,
                    'error': 'Eksik parametreler'
                }), 400
            
            if miktar <= 0:
                return jsonify({
                    'success': False,
                    'error': 'Miktar 0\'dan büyük olmalıdır'
                }), 400
            
            kullanici_id = session.get('kullanici_id')
            
            # Transaction başlat
            try:
                # Ürün bilgilerini getir
                urun = Urun.query.get(urun_id)
                if not urun:
                    return jsonify({
                        'success': False,
                        'error': 'Ürün bulunamadı'
                    }), 404
                
                # Otel bazlı zimmet kontrolü
                from utils.otel_zimmet_servisleri import OtelZimmetServisi, OtelZimmetStokYetersizError
                from models import Kullanici
                
                personel = Kullanici.query.get(kullanici_id)
                if not personel or not personel.otel_id:
                    return jsonify({
                        'success': False,
                        'error': 'Otel atamanız bulunamadı'
                    }), 404
                
                otel_id = personel.otel_id
                
                # Otel zimmet stoğunu kontrol et
                otel_stok = OtelZimmetServisi.get_otel_zimmet_stok(otel_id, urun_id)
                
                if not otel_stok or otel_stok.kalan_miktar < miktar:
                    kalan = otel_stok.kalan_miktar if otel_stok else 0
                    return jsonify({
                        'success': False,
                        'error': f'Otel zimmet deposunda yeterli {urun.urun_adi} bulunmuyor. Kalan: {kalan} {urun.birim}'
                    }), 400
                
                # Son stok durumunu al
                from sqlalchemy import desc
                son_islem_detay = MinibarIslemDetay.query.join(
                    MinibarIslem
                ).filter(
                    MinibarIslem.oda_id == oda_id,
                    MinibarIslemDetay.urun_id == urun_id
                ).order_by(desc(MinibarIslem.islem_tarihi)).first()
                
                baslangic_stok = 0
                if son_islem_detay:
                    baslangic_stok = son_islem_detay.bitis_stok or 0
                
                # Setup miktarını bul (Otel bazlı)
                from models import OdaTipi, SetupIcerik, Kat, oda_tipi_setup
                from sqlalchemy import and_
                oda = Oda.query.get(oda_id)
                setup_miktari = 0
                
                if oda and oda.oda_tipi_id:
                    oda_tipi = OdaTipi.query.get(oda.oda_tipi_id)
                    if oda_tipi:
                        # Odanın otelini bul
                        kat = Kat.query.get(oda.kat_id)
                        if kat:
                            # Otel bazlı setup'ları getir
                            setup_rows = db.session.execute(
                                db.select(oda_tipi_setup.c.setup_id).where(
                                    and_(
                                        oda_tipi_setup.c.otel_id == kat.otel_id,
                                        oda_tipi_setup.c.oda_tipi_id == oda_tipi.id
                                    )
                                )
                            ).fetchall()
                            setup_ids = [row[0] for row in setup_rows]
                            
                            if setup_ids:
                                setuplar = Setup.query.filter(Setup.id.in_(setup_ids), Setup.aktif == True).all()
                            else:
                                # Geriye uyumluluk
                                setuplar = [s for s in oda_tipi.setuplar if s.aktif]
                            
                            for setup in setuplar:
                                setup_icerik = SetupIcerik.query.filter_by(
                                    setup_id=setup.id,
                                    urun_id=urun_id
                                ).first()
                                if setup_icerik:
                                    setup_miktari = setup_icerik.adet
                                    break
                
                # Tüketim hesapla: Setup'ta olması gereken - Başlangıçta olan
                tuketim_miktari = max(0, setup_miktari - baslangic_stok)
                tuketim_miktari = min(tuketim_miktari, miktar)  # Eklenen miktardan fazla olamaz
                
                # Bitiş stok hesapla
                bitis_stok = baslangic_stok + miktar
                
                # Otel zimmet stoğundan düş ve kullanım kaydı oluştur
                otel_stok, kullanim = OtelZimmetServisi.stok_dusu(
                    otel_id=otel_id,
                    urun_id=urun_id,
                    miktar=miktar,
                    personel_id=kullanici_id,
                    islem_tipi='minibar_kullanim',
                    aciklama=f'Tüketim ikamesi - Oda: {oda.oda_no if oda else oda_id}'
                )
                
                # Minibar işlemi oluştur
                islem = MinibarIslem(
                    oda_id=oda_id,
                    personel_id=kullanici_id,
                    islem_tipi='setup_kontrol',
                    islem_tarihi=get_kktc_now(),
                    aciklama=f'{urun.urun_adi} tüketim ikamesi'
                )
                db.session.add(islem)
                db.session.flush()
                
                # İşlem detayı oluştur
                detay = MinibarIslemDetay(
                    islem_id=islem.id,
                    urun_id=urun_id,
                    baslangic_stok=baslangic_stok,
                    bitis_stok=bitis_stok,
                    tuketim=tuketim_miktari,
                    eklenen_miktar=miktar,
                    ekstra_miktar=0,
                    setup_miktari=setup_miktari,
                    zimmet_detay_id=None,  # Artık otel bazlı sistem kullanılıyor
                    satis_fiyati=urun.satis_fiyati or 0,
                    alis_fiyati=urun.alis_fiyati or 0
                )
                db.session.add(detay)
                db.session.commit()
                
                # Audit log
                audit_create(
                    tablo_adi='minibar_islem',
                    kayit_id=islem.id,
                    yeni_deger={
                        'oda_id': oda_id,
                        'urun_id': urun_id,
                        'miktar': miktar,
                        'islem_tipi': 'setup_kontrol'
                    },
                    aciklama=f"Tüketim ikamesi: {urun.urun_adi} x{miktar}"
                )
                
                return jsonify({
                    'success': True,
                    'message': f'{miktar} {urun.birim} {urun.urun_adi} tüketim olarak kaydedildi'
                })
                
            except Exception as e:
                db.session.rollback()
                raise
            
        except Exception as e:
            log_hata(e, modul='api_urun_tuketim_ekle')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    
    @app.route('/api/kat-sorumlusu/urun-ekstra-ekle', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_urun_ekstra_ekle():
        """
        Ekstra ürün ekle (Ekstra butonu)
        Setup dışı ekstra ürün, zimmet stoğundan düşer ama tüketim kaydedilmez
        
        YENİ SİSTEM: Otel bazlı ortak zimmet deposundan düşer
        
        Request Body:
            {
                "oda_id": 1154,
                "urun_id": 10,
                "miktar": 1
            }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Geçersiz istek'
                }), 400
            
            oda_id = data.get('oda_id')
            urun_id = data.get('urun_id')
            miktar = data.get('miktar')
            
            if not all([oda_id, urun_id, miktar]):
                return jsonify({
                    'success': False,
                    'error': 'Eksik parametreler'
                }), 400
            
            if miktar <= 0:
                return jsonify({
                    'success': False,
                    'error': 'Miktar 0\'dan büyük olmalıdır'
                }), 400
            
            kullanici_id = session.get('kullanici_id')
            
            # Transaction başlat
            try:
                # Ürün bilgilerini getir
                urun = Urun.query.get(urun_id)
                if not urun:
                    return jsonify({
                        'success': False,
                        'error': 'Ürün bulunamadı'
                    }), 404
                
                # Otel bazlı zimmet kontrolü
                from utils.otel_zimmet_servisleri import OtelZimmetServisi, OtelZimmetStokYetersizError
                from models import Kullanici
                
                personel = Kullanici.query.get(kullanici_id)
                if not personel or not personel.otel_id:
                    return jsonify({
                        'success': False,
                        'error': 'Otel atamanız bulunamadı'
                    }), 404
                
                otel_id = personel.otel_id
                
                # Otel zimmet stoğunu kontrol et
                otel_stok = OtelZimmetServisi.get_otel_zimmet_stok(otel_id, urun_id)
                
                if not otel_stok or otel_stok.kalan_miktar < miktar:
                    kalan = otel_stok.kalan_miktar if otel_stok else 0
                    return jsonify({
                        'success': False,
                        'error': f'Otel zimmet deposunda yeterli {urun.urun_adi} bulunmuyor. Kalan: {kalan} {urun.birim}'
                    }), 400
                
                # Oda bilgisini al
                oda = Oda.query.get(oda_id)
                
                # Otel zimmet stoğundan düş ve kullanım kaydı oluştur
                otel_stok, kullanim = OtelZimmetServisi.stok_dusu(
                    otel_id=otel_id,
                    urun_id=urun_id,
                    miktar=miktar,
                    personel_id=kullanici_id,
                    islem_tipi='ekstra_ekleme',
                    aciklama=f'Ekstra ekleme - Oda: {oda.oda_no if oda else oda_id}'
                )
                
                # Minibar işlemi oluştur
                islem = MinibarIslem(
                    oda_id=oda_id,
                    personel_id=kullanici_id,
                    islem_tipi='ekstra_ekleme',
                    islem_tarihi=get_kktc_now(),
                    aciklama=f'{urun.urun_adi} ekstra ekleme'
                )
                db.session.add(islem)
                db.session.flush()
                
                # İşlem detayı oluştur (tüketim yok, sadece ekstra)
                detay = MinibarIslemDetay(
                    islem_id=islem.id,
                    urun_id=urun_id,
                    baslangic_stok=0,
                    bitis_stok=0,
                    tuketim=0,  # Tüketim kaydedilmez
                    eklenen_miktar=0,
                    ekstra_miktar=miktar,  # Ekstra olarak kaydedilir
                    zimmet_detay_id=None,  # Artık otel bazlı sistem kullanılıyor
                    satis_fiyati=urun.satis_fiyati or 0,
                    alis_fiyati=urun.alis_fiyati or 0
                )
                db.session.add(detay)
                db.session.commit()
                
                # Audit log
                audit_create(
                    tablo_adi='minibar_islem',
                    kayit_id=islem.id,
                    yeni_deger={
                        'oda_id': oda_id,
                        'urun_id': urun_id,
                        'miktar': miktar,
                        'islem_tipi': 'ekstra_ekleme'
                    },
                    aciklama=f"Ekstra eklendi: {urun.urun_adi} x{miktar}"
                )
                
                return jsonify({
                    'success': True,
                    'message': f'{miktar} {urun.birim} {urun.urun_adi} ekstra olarak eklendi'
                })
                
            except Exception as e:
                db.session.rollback()
                raise
            
        except Exception as e:
            log_hata(e, modul='api_urun_ekstra_ekle')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    

    @app.route('/api/kat-sorumlusu/sarfiyat-yok', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_sarfiyat_yok():
        """
        Sarfiyat yok kaydı - Oda kontrolü yapıldı ama tüketim yok
        Görev varsa otomatik tamamlanır
        
        Request Body:
            {
                "oda_id": 101,
                "gorev_detay_id": 45 (opsiyonel)
            }
            
        Returns:
            JSON: İşlem sonucu
        """
        try:
            from datetime import date
            
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Geçersiz istek'
                }), 400
            
            oda_id = data.get('oda_id')
            gorev_detay_id = data.get('gorev_detay_id')
            
            if not oda_id:
                return jsonify({
                    'success': False,
                    'error': 'Oda ID gerekli'
                }), 400
            
            kullanici_id = session.get('kullanici_id')
            
            # Oda bilgilerini al
            oda = Oda.query.get(oda_id)
            if not oda:
                return jsonify({
                    'success': False,
                    'error': 'Oda bulunamadı'
                }), 404
            
            # Minibar kontrol kaydı oluştur (sarfiyat yok)
            islem = MinibarIslem(
                oda_id=oda_id,
                personel_id=kullanici_id,
                islem_tipi='sarfiyat_yok',
                islem_tarihi=get_kktc_now(),
                aciklama='Sarfiyat yok - Oda kontrol edildi, tüketim tespit edilmedi'
            )
            db.session.add(islem)
            db.session.flush()
            
            # Görev varsa tamamla
            gorev_tamamlandi = False
            if gorev_detay_id:
                try:
                    from models import GorevDetay, GorevDurumLog, GunlukGorev
                    
                    detay = GorevDetay.query.get(gorev_detay_id)
                    if detay and detay.durum != 'completed':
                        onceki_durum = detay.durum
                        detay.durum = 'completed'
                        detay.kontrol_zamani = get_kktc_now()
                        detay.notlar = 'Sarfiyat yok - Oda kontrol ile tamamlandı'
                        
                        # Log kaydı
                        log = GorevDurumLog(
                            gorev_detay_id=gorev_detay_id,
                            onceki_durum=onceki_durum,
                            yeni_durum='completed',
                            degistiren_id=kullanici_id,
                            aciklama='Sarfiyat yok - Oda kontrol ile tamamlandı'
                        )
                        db.session.add(log)
                        
                        # Ana görev durumunu güncelle
                        gorev = detay.gorev
                        if gorev:
                            tamamlanan = sum(1 for d in gorev.detaylar if d.durum == 'completed')
                            if tamamlanan == len(gorev.detaylar):
                                gorev.durum = 'completed'
                                gorev.tamamlanma_tarihi = get_kktc_now()
                            elif tamamlanan > 0:
                                gorev.durum = 'in_progress'
                        
                        gorev_tamamlandi = True
                except Exception as e:
                    print(f"Görev tamamlama hatası: {str(e)}")
            else:
                # Görev detay ID verilmemişse, bugünkü OTEL BAZLI görevi bul ve tamamla
                try:
                    from models import GorevDetay, GorevDurumLog, GunlukGorev
                    from utils.authorization import get_kat_sorumlusu_otel
                    
                    bugun = date.today()
                    
                    # Kullanıcının otelini al (OTEL BAZLI görevler için)
                    kullanici_oteli = get_kat_sorumlusu_otel(kullanici_id)
                    
                    if kullanici_oteli:
                        # Debug log
                        print(f"🔍 Sarfiyat Yok - Görev Arama: Otel={kullanici_oteli.id}, Tarih={bugun}, Oda={oda_id}")
                        
                        # OTEL BAZLI görevlerde personel_id NULL olabilir, otel_id ile sorgula
                        detay = GorevDetay.query.join(GunlukGorev).filter(
                            GunlukGorev.otel_id == kullanici_oteli.id,
                            GunlukGorev.gorev_tarihi == bugun,
                            GorevDetay.oda_id == oda_id,
                            GorevDetay.durum.in_(['pending', 'in_progress', 'dnd_pending'])
                        ).first()
                        
                        if detay:
                            print(f"✅ Görev detay bulundu: ID={detay.id}, Durum={detay.durum}")
                            onceki_durum = detay.durum
                            detay.durum = 'completed'
                            detay.kontrol_zamani = get_kktc_now()
                            detay.notlar = 'Sarfiyat yok - Oda kontrol ile tamamlandı'
                            
                            log = GorevDurumLog(
                                gorev_detay_id=detay.id,
                                onceki_durum=onceki_durum,
                                yeni_durum='completed',
                                degistiren_id=kullanici_id,
                                aciklama='Sarfiyat yok - Oda kontrol ile tamamlandı'
                            )
                            db.session.add(log)
                            
                            gorev = detay.gorev
                            if gorev:
                                tamamlanan = sum(1 for d in gorev.detaylar if d.durum == 'completed')
                                if tamamlanan == len(gorev.detaylar):
                                    gorev.durum = 'completed'
                                    gorev.tamamlanma_tarihi = get_kktc_now()
                                elif tamamlanan > 0:
                                    gorev.durum = 'in_progress'
                            
                            gorev_tamamlandi = True
                        else:
                            # Görev var mı kontrol et
                            gorev_sayisi = GunlukGorev.query.filter(
                                GunlukGorev.otel_id == kullanici_oteli.id,
                                GunlukGorev.gorev_tarihi == bugun
                            ).count()
                            print(f"⚠️ Görev detay bulunamadı! Otel {kullanici_oteli.id} için bugün {gorev_sayisi} görev var.")
                except Exception as e:
                    print(f"Otomatik görev tamamlama hatası: {str(e)}")
            
            db.session.commit()
            
            # Audit log
            audit_create(
                tablo_adi='minibar_islem',
                kayit_id=islem.id,
                yeni_deger={
                    'oda_id': oda_id,
                    'islem_tipi': 'kontrol',
                    'sarfiyat_yok': True,
                    'gorev_tamamlandi': gorev_tamamlandi
                },
                aciklama=f"Oda {oda.oda_no} - Sarfiyat yok kontrolü"
            )
            
            mesaj = f'Oda {oda.oda_no} kontrolü kaydedildi.'
            if gorev_tamamlandi:
                mesaj += ' Görev tamamlandı!'
            
            return jsonify({
                'success': True,
                'message': mesaj,
                'gorev_tamamlandi': gorev_tamamlandi
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_sarfiyat_yok')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/kat-sorumlusu/kontrol-baslat', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_kontrol_baslat():
        """
        Oda kontrolü başlatma - Varış kaydı oluşturur
        Eğer tamamlanmamış bir kayıt varsa önce onu siler
        """
        try:
            from models import OdaKontrolKaydi
            from datetime import date
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Geçersiz istek'}), 400
            
            oda_id = data.get('oda_id')
            if not oda_id:
                return jsonify({'success': False, 'error': 'Oda ID gerekli'}), 400
            
            kullanici_id = session.get('kullanici_id')
            bugun = date.today()
            simdi = get_kktc_now()
            
            # Tamamlanmamış (bitis_zamani NULL) kayıtları sil
            tamamlanmamis = OdaKontrolKaydi.query.filter(
                OdaKontrolKaydi.personel_id == kullanici_id,
                OdaKontrolKaydi.kontrol_tarihi == bugun,
                OdaKontrolKaydi.bitis_zamani.is_(None)
            ).all()
            
            for kayit in tamamlanmamis:
                db.session.delete(kayit)
            
            # Yeni kontrol kaydı oluştur
            yeni_kayit = OdaKontrolKaydi(
                oda_id=oda_id,
                personel_id=kullanici_id,
                kontrol_tarihi=bugun,
                baslangic_zamani=simdi
            )
            db.session.add(yeni_kayit)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Kontrol başlatıldı',
                'kayit_id': yeni_kayit.id,
                'baslangic_zamani': simdi.isoformat()
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_kontrol_baslat')
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/kat-sorumlusu/kontrol-tamamla', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_kontrol_tamamla():
        """
        Oda kontrolünü tamamla - Bitiş zamanını kaydeder
        """
        try:
            from models import OdaKontrolKaydi
            from datetime import date
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Geçersiz istek'}), 400
            
            oda_id = data.get('oda_id')
            kontrol_tipi = data.get('kontrol_tipi', 'sarfiyat_yok')
            
            if not oda_id:
                return jsonify({'success': False, 'error': 'Oda ID gerekli'}), 400
            
            kullanici_id = session.get('kullanici_id')
            bugun = date.today()
            simdi = get_kktc_now()
            
            # Bugünkü tamamlanmamış kaydı bul
            kayit = OdaKontrolKaydi.query.filter(
                OdaKontrolKaydi.oda_id == oda_id,
                OdaKontrolKaydi.personel_id == kullanici_id,
                OdaKontrolKaydi.kontrol_tarihi == bugun,
                OdaKontrolKaydi.bitis_zamani.is_(None)
            ).first()
            
            if kayit:
                kayit.bitis_zamani = simdi
                kayit.kontrol_tipi = kontrol_tipi
            else:
                # Kayıt yoksa yeni oluştur (başlangıç ve bitiş aynı)
                kayit = OdaKontrolKaydi(
                    oda_id=oda_id,
                    personel_id=kullanici_id,
                    kontrol_tarihi=bugun,
                    baslangic_zamani=simdi,
                    bitis_zamani=simdi,
                    kontrol_tipi=kontrol_tipi
                )
                db.session.add(kayit)
            
            db.session.commit()
            
            # Bildirim gönder - Sarfiyat yok ise depo sorumlusuna
            if kontrol_tipi == 'sarfiyat_yok':
                try:
                    from utils.bildirim_service import sarfiyat_yok_bildirimi
                    from models import Oda, Kullanici, Kat
                    oda = Oda.query.get(oda_id)
                    personel = Kullanici.query.get(kullanici_id)
                    if oda and personel:
                        # Kat üzerinden otel_id al
                        kat = Kat.query.get(oda.kat_id)
                        otel_id = kat.otel_id if kat else None
                        if otel_id:
                            sarfiyat_yok_bildirimi(
                                otel_id=otel_id,
                                oda_no=oda.oda_no,
                                personel_adi=personel.ad_soyad,
                                oda_id=oda_id,
                                gonderen_id=kullanici_id
                            )
                            print(f"✅ Sarfiyat yok bildirimi gönderildi: Oda {oda.oda_no}")
                        else:
                            print(f"⚠️ Otel ID bulunamadı: oda_id={oda_id}")
                except Exception as bildirim_err:
                    print(f"❌ Sarfiyat yok bildirim hatası: {bildirim_err}")
                    import traceback
                    traceback.print_exc()
            
            return jsonify({
                'success': True,
                'message': 'Kontrol tamamlandı',
                'kayit_id': kayit.id,
                'bitis_zamani': simdi.isoformat()
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_kontrol_tamamla')
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/kat-sorumlusu/dnd-kaydet', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_dnd_kaydet():
        """
        Oda için DND kaydı oluşturur - BAĞIMSIZ DND SİSTEMİ
        
        Görev atanmamış odalar için de DND kaydı yapılabilir.
        Görev varsa otomatik olarak bağlanır ve senkronize edilir.
        3 kez DND kontrolü yapılırsa kayıt tamamlanır.
        
        Request Body:
            {
                "oda_id": 101,
                "gorev_detay_id": 45,  // Opsiyonel
                "notlar": "Kapıda tabela var"  // Opsiyonel
            }
        
        Returns:
            JSON: İşlem sonucu
        """
        try:
            from utils.dnd_service import DNDService, OdaNotFoundError, DNDServiceError
            from utils.authorization import get_kat_sorumlusu_otel
            from models import GorevDetay, GunlukGorev
            from datetime import date
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Geçersiz istek'}), 400
            
            oda_id = data.get('oda_id')
            gorev_detay_id = data.get('gorev_detay_id')
            notlar = data.get('notlar')
            
            if not oda_id:
                return jsonify({'success': False, 'error': 'Oda ID gerekli'}), 400
            
            kullanici_id = session.get('kullanici_id')
            bugun = date.today()
            
            # Kullanıcının otelini al (OTEL BAZLI görevler için)
            kullanici_oteli = get_kat_sorumlusu_otel(kullanici_id)
            if not kullanici_oteli:
                return jsonify({'success': False, 'error': 'Otel atamanız bulunamadı'}), 400
            
            # Görev detay ID verilmediyse, bugünkü OTEL BAZLI görevi bulmaya çalış
            if not gorev_detay_id:
                # OTEL BAZLI görevlerde personel_id NULL olabilir, otel_id ile sorgula
                detay = GorevDetay.query.join(GunlukGorev).filter(
                    GunlukGorev.otel_id == kullanici_oteli.id,
                    GunlukGorev.gorev_tarihi == bugun,
                    GorevDetay.oda_id == oda_id,
                    GorevDetay.durum.in_(['pending', 'in_progress', 'dnd_pending'])
                ).first()
                
                # Debug log
                print(f"🔍 DND Görev Arama - Otel: {kullanici_oteli.id}, Tarih: {bugun}, Oda: {oda_id}")
                if detay:
                    print(f"✅ Görev detay bulundu: ID={detay.id}, Durum={detay.durum}")
                    gorev_detay_id = detay.id
                else:
                    # Görev var mı kontrol et
                    gorev_sayisi = GunlukGorev.query.filter(
                        GunlukGorev.otel_id == kullanici_oteli.id,
                        GunlukGorev.gorev_tarihi == bugun
                    ).count()
                    print(f"⚠️ Görev detay bulunamadı! Otel {kullanici_oteli.id} için bugün {gorev_sayisi} görev var.")
            
            # Bağımsız DND servisini kullan
            result = DNDService.kaydet(
                oda_id=oda_id,
                personel_id=kullanici_id,
                notlar=notlar,
                gorev_detay_id=gorev_detay_id
            )
            
            # Audit log
            audit_create(
                tablo_adi='oda_dnd_kayitlari',
                kayit_id=result['dnd_kayit_id'],
                yeni_deger={
                    'oda_id': oda_id,
                    'dnd_sayisi': result['dnd_sayisi'],
                    'durum': result['durum'],
                    'gorev_bagli': gorev_detay_id is not None
                },
                aciklama=result['mesaj']
            )
            
            # Depo sorumlusuna bildirim gönder
            try:
                from utils.bildirim_service import bildirim_olustur
                from models import Oda
                oda = Oda.query.get(oda_id)
                oda_no = oda.oda_no if oda else str(oda_id)
                
                bildirim_olustur(
                    hedef_rol='depo_sorumlusu',
                    hedef_otel_id=kullanici_oteli.id,
                    bildirim_tipi='dnd_kayit',
                    baslik=f'🚫 Oda {oda_no} DND',
                    mesaj=f'Oda {oda_no} için DND kaydı yapıldı ({result["dnd_sayisi"]}/3)',
                    oda_id=oda_id,
                    gonderen_id=kullanici_id
                )
                print(f"✅ DND bildirimi gönderildi: Oda {oda_no}")
            except Exception as bildirim_err:
                print(f"❌ DND bildirim hatası: {bildirim_err}")
                import traceback
                traceback.print_exc()
            
            return jsonify({
                'success': True,
                'message': result['mesaj'],
                'dnd_sayisi': result['dnd_sayisi'],
                'min_kontrol_tamamlandi': result['min_kontrol_tamamlandi'],
                'otomatik_tamamlandi': result['min_kontrol_tamamlandi'],
                'gorev_guncellendi': result.get('gorev_guncellendi', False)
            })
            
        except OdaNotFoundError as e:
            return jsonify({'success': False, 'error': str(e)}), 404
            
        except DNDServiceError as e:
            log_hata(e, modul='api_dnd_kaydet')
            return jsonify({'success': False, 'error': str(e)}), 500
            
        except Exception as e:
            log_hata(e, modul='api_dnd_kaydet')
            return jsonify({'success': False, 'error': f'Beklenmeyen hata: {str(e)}'}), 500
    
    
    @app.route('/api/kat-sorumlusu/dnd-durum/<int:oda_id>', methods=['GET'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_dnd_durum(oda_id):
        """
        Odanın güncel DND durumunu getirir.
        
        Args:
            oda_id: Oda ID
            
        Returns:
            JSON: DND durumu veya null
        """
        try:
            from utils.dnd_service import DNDService
            
            durum = DNDService.oda_durumu(oda_id)
            
            return jsonify({
                'success': True,
                'dnd_durumu': durum
            })
            
        except Exception as e:
            log_hata(e, modul='api_dnd_durum')
            return jsonify({'success': False, 'error': str(e)}), 500
    
    
    @app.route('/api/kat-sorumlusu/dnd-liste', methods=['GET'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_dnd_liste():
        """
        Kat sorumlusunun otelindeki günlük DND listesini getirir.
        
        Query Params:
            tarih: YYYY-MM-DD formatında tarih (opsiyonel, varsayılan: bugün)
            sadece_aktif: true/false (opsiyonel, varsayılan: false)
            
        Returns:
            JSON: DND kayıtları listesi
        """
        try:
            from utils.dnd_service import DNDService
            from utils.authorization import get_kat_sorumlusu_otel
            from datetime import datetime
            
            kullanici_id = session.get('kullanici_id')
            kullanici_oteli = get_kat_sorumlusu_otel(kullanici_id)
            
            if not kullanici_oteli:
                return jsonify({'success': False, 'error': 'Otel atamanız bulunamadı'}), 403
            
            # Tarih parametresi
            tarih_str = request.args.get('tarih')
            if tarih_str:
                tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
            else:
                tarih = None  # Bugün
            
            # Sadece aktif filtresi
            sadece_aktif = request.args.get('sadece_aktif', 'false').lower() == 'true'
            
            liste = DNDService.gunluk_liste(
                otel_id=kullanici_oteli.id,
                tarih=tarih,
                sadece_aktif=sadece_aktif
            )
            
            return jsonify({
                'success': True,
                'dnd_kayitlari': liste,
                'toplam': len(liste)
            })
            
        except Exception as e:
            log_hata(e, modul='api_dnd_liste')
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/kat-sorumlusu/bugun-eklemeler/<int:oda_id>', methods=['GET'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_bugun_eklemeler(oda_id):
        """
        Bugün bu odaya eklenen ürün miktarlarını getirir
        
        Args:
            oda_id (int): Oda ID
            
        Returns:
            JSON: Ürün ID -> Eklenen miktar dictionary
        """
        try:
            from datetime import date
            from sqlalchemy import func
            
            kullanici_id = session.get('kullanici_id')
            bugun = date.today()
            
            # Bugünkü minibar işlem detaylarını getir
            eklemeler = db.session.query(
                MinibarIslemDetay.urun_id,
                func.sum(MinibarIslemDetay.eklenen_miktar).label('toplam')
            ).join(
                MinibarIslem, MinibarIslemDetay.islem_id == MinibarIslem.id
            ).filter(
                MinibarIslem.oda_id == oda_id,
                MinibarIslem.personel_id == kullanici_id,
                func.date(MinibarIslem.islem_tarihi) == bugun
            ).group_by(MinibarIslemDetay.urun_id).all()
            
            eklemeler_dict = {}
            for ekleme in eklemeler:
                if ekleme.toplam and ekleme.toplam > 0:
                    eklemeler_dict[ekleme.urun_id] = int(ekleme.toplam)
            
            return jsonify({
                'success': True,
                'eklemeler': eklemeler_dict
            })
            
        except Exception as e:
            log_hata(e, modul='api_bugun_eklemeler')
            return jsonify({
                'success': False,
                'error': str(e),
                'eklemeler': {}
            })


    # ============================================================================
    # GÖREV LİSTESİ SAYFASI
    # ============================================================================
    
    @app.route('/kat-sorumlusu/gorev-listesi')
    @login_required
    @role_required('kat_sorumlusu', 'depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def kat_sorumlusu_gorev_listesi():
        """
        Günlük görev listesi sayfası - Kata göre gruplu
        GET /kat-sorumlusu/gorev-listesi
        """
        try:
            from utils.gorev_service import GorevService
            from utils.authorization import get_kullanici_otelleri
            from datetime import date
            
            kullanici_id = session.get('kullanici_id')
            kullanici = Kullanici.query.get(kullanici_id)
            
            # Kullanıcının otelini al (OTEL BAZLI görevler için)
            kullanici_otelleri = get_kullanici_otelleri()
            otel_id = kullanici_otelleri[0].id if kullanici_otelleri else None
            
            tarih_str = request.args.get('tarih', date.today().isoformat())
            tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
            
            if not otel_id:
                flash('Otel atamanız bulunamadı.', 'danger')
                return redirect(url_for('dashboard'))
            
            # Görev özetini al (OTEL BAZLI)
            ozet = GorevService.get_task_summary(otel_id, tarih)
            
            # Bekleyen görevleri al (OTEL BAZLI)
            bekleyen = GorevService.get_pending_tasks(otel_id, tarih)
            
            # Öncelik sıralaması: Önce kata göre, sonra Arrivals/Departures zamana göre
            def oncelik_sirala(g):
                kat = g.get('kat_no') or 999
                tip = g.get('gorev_tipi', '')
                if tip == 'arrival_kontrol' and g.get('varis_saati'):
                    return (kat, 0, g.get('varis_saati', '99:99:99'))
                elif tip == 'departure_kontrol' and g.get('cikis_saati'):
                    return (kat, 0, g.get('cikis_saati', '99:99:99'))
                return (kat, 1, str(g.get('oncelik_sirasi') or 999).zfill(5))
            
            bekleyen.sort(key=oncelik_sirala)
            
            # Tamamlanan görevleri al (OTEL BAZLI)
            tamamlanan = GorevService.get_completed_tasks(otel_id, tarih)
            
            # DND görevleri al (OTEL BAZLI)
            dnd_gorevler = GorevService.get_dnd_tasks(otel_id, tarih)
            
            return render_template(
                'kat_sorumlusu/gorev_listesi.html',
                ozet=ozet,
                bekleyen=bekleyen,
                tamamlanan=tamamlanan,
                dnd_gorevler=dnd_gorevler,
                tarih=tarih,
                kullanici=kullanici
            )
            
        except Exception as e:
            log_hata(e, modul='kat_sorumlusu_gorev_listesi')
            flash(f'Görev listesi yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
