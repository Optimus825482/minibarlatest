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
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from models import (
    db, Kat, Oda, UrunGrup, Urun, PersonelZimmet, PersonelZimmetDetay,
    MinibarIslem, MinibarIslemDetay, Kullanici
)
from utils.decorators import login_required, role_required
from utils.helpers import log_islem, log_hata
from utils.audit import audit_create

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
        kullanici_id = session['kullanici_id']
        kullanici_rol = session.get('rol')
        
        # Kullanıcının erişebileceği otellerin katlarını getir
        kullanici_otelleri = get_kullanici_otelleri(kullanici_id)
        otel_idleri = [otel.id for otel in kullanici_otelleri]
        
        if otel_idleri:
            katlar = Kat.query.options(
                db.joinedload(Kat.otel)
            ).filter(
                Kat.otel_id.in_(otel_idleri),
                Kat.aktif == True
            ).order_by(Kat.otel_id, Kat.kat_no).all()
        else:
            katlar = []
            if kullanici_rol == 'kat_sorumlusu':
                flash('Otel atamanız bulunamadı. Lütfen yöneticinizle iletişime geçin.', 'warning')
        
        return render_template('raporlar/kat_bazli_rapor.html', katlar=katlar)
    
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
            query = MinibarIslem.query.filter_by(personel_id=kullanici_id)
            
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
            
            # Oda setup durumunu getir
            sonuc = oda_setup_durumu_getir(oda_id)
            
            # Kat sorumlusunun zimmet stoklarını getir
            kullanici_id = session.get('kullanici_id')
            
            # Tüm aktif zimmetleri bul (birden fazla olabilir)
            aktif_zimmetler = PersonelZimmet.query.filter_by(
                personel_id=kullanici_id,
                durum='aktif'
            ).all()
            
            zimmet_stoklar = {}
            for aktif_zimmet in aktif_zimmetler:
                zimmet_detaylar = PersonelZimmetDetay.query.filter_by(
                    zimmet_id=aktif_zimmet.id
                ).all()
                
                for detay in zimmet_detaylar:
                    kalan = detay.kalan_miktar if detay.kalan_miktar is not None else (detay.miktar - detay.kullanilan_miktar)
                    urun_key = str(detay.urun_id)
                    
                    # Aynı üründen birden fazla zimmet varsa topla
                    if urun_key in zimmet_stoklar:
                        zimmet_stoklar[urun_key]['miktar'] += kalan
                    else:
                        zimmet_stoklar[urun_key] = {
                            'miktar': kalan,
                            'zimmet_detay_id': detay.id
                        }
            
            sonuc['kat_sorumlusu_stok'] = zimmet_stoklar
            
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
                
                # Zimmet stoğundan düş
                zimmet_detay = zimmet_stok_dusu(
                    kullanici_id,
                    urun_id,
                    eklenen_miktar,
                    zimmet_detay_id
                )
                
                # Tüketimi kaydet
                tuketim_kaydet(
                    oda_id=oda_id,
                    urun_id=urun_id,
                    miktar=tuketim,
                    personel_id=kullanici_id,
                    islem_tipi='setup_kontrol',
                    eklenen_miktar=eklenen_miktar,
                    ekstra_miktar=0,
                    zimmet_detay_id=zimmet_detay.id
                )
                
                # Oda ve ürün bilgilerini getir
                oda = Oda.query.get(oda_id)
                urun = Urun.query.get(urun_id)
                
                # Görev tamamlama - Ürün eklendiğinde görev tamamlanır
                gorev_tamamlandi = False
                try:
                    from models import GorevDetay, GorevDurumLog, GunlukGorev
                    from datetime import date
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
                    
                    bugun = date.today()
                    detay = GorevDetay.query.join(GunlukGorev).filter(
                        GunlukGorev.personel_id == kullanici_id,
                        GunlukGorev.gorev_tarihi == bugun,
                        GorevDetay.oda_id == oda_id,
                        GorevDetay.durum != 'completed'
                    ).first()
                    
                    if detay:
                        onceki_durum = detay.durum
                        detay.durum = 'completed'
                        detay.kontrol_zamani = get_kktc_now()
                        detay.notlar = f'Ürün eklendi: {urun.urun_adi} x{eklenen_miktar}'
                        
                        log = GorevDurumLog(
                            gorev_detay_id=detay.id,
                            onceki_durum=onceki_durum,
                            yeni_durum='completed',
                            degistiren_id=kullanici_id,
                            aciklama=f'Ürün eklendi: {urun.urun_adi} x{eklenen_miktar} - Oda kontrol ile tamamlandı'
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
                except Exception as e:
                    print(f"Görev tamamlama hatası: {str(e)}")
                
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
                
                return jsonify({
                    'success': True,
                    'message': mesaj,
                    'tuketim': tuketim,
                    'yeni_miktar': setup_miktari,
                    'zimmet_kalan': zimmet_detay.kalan_miktar,
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
                
                # Zimmet stoğundan düş
                zimmet_detay = zimmet_stok_dusu(
                    kullanici_id,
                    urun_id,
                    ekstra_miktar,
                    zimmet_detay_id
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
                    zimmet_detay_id=zimmet_detay.id
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
                
                return jsonify({
                    'success': True,
                    'message': 'Ekstra ürün başarıyla eklendi',
                    'yeni_miktar': yeni_miktar,
                    'ekstra_miktar': ekstra_miktar,
                    'zimmet_kalan': zimmet_detay.kalan_miktar
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
        """Kat sorumlusunun yaptığı minibar işlemlerini listele"""
        try:
            from datetime import date, datetime
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
            
            kullanici_id = session.get('kullanici_id')
            
            # Filtreler
            tarih_str = request.args.get('tarih')
            oda_no = request.args.get('oda')
            islem_tipi = request.args.get('islem_tipi')
            
            # Query oluştur
            query = MinibarIslem.query.filter_by(personel_id=kullanici_id)
            
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
            
            # Bugünün tarihi
            bugun = date.today()
            
            # Sonuçları hazırla
            sonuc = []
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
                    'oda_no': islem.oda.oda_no,
                    'islem_tipi': islem.islem_tipi,
                    'islem_tarihi': islem.islem_tarihi.isoformat(),
                    'aciklama': islem.aciklama,
                    'urun_sayisi': len(detaylar),
                    'detaylar': detaylar,
                    'ayni_gun': ayni_gun
                })
            
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
        """Minibar işlemini sil (sadece aynı gün)"""
        try:
            from datetime import date
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
            
            kullanici_id = session.get('kullanici_id')
            
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
                # Zimmet stoklarını geri yükle
                for detay in islem.detaylar:
                    if detay.zimmet_detay_id:
                        zimmet_detay = PersonelZimmetDetay.query.get(detay.zimmet_detay_id)
                        if zimmet_detay:
                            zimmet_detay.kullanilan_miktar -= detay.eklenen_miktar
                            zimmet_detay.kalan_miktar = zimmet_detay.miktar - zimmet_detay.kullanilan_miktar
                
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
                    aciklama=f"Minibar işlemi silindi (Oda: {oda_no})"
                )
                
                return jsonify({
                    'success': True,
                    'message': 'İşlem başarıyla silindi'
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
                
                # Zimmet kontrolü
                aktif_zimmet = PersonelZimmet.query.filter_by(
                    personel_id=kullanici_id,
                    durum='aktif'
                ).first()
                
                if not aktif_zimmet:
                    return jsonify({
                        'success': False,
                        'error': 'Aktif zimmetiniz bulunamadı'
                    }), 404
                
                zimmet_detay = PersonelZimmetDetay.query.filter_by(
                    zimmet_id=aktif_zimmet.id,
                    urun_id=urun_id
                ).first()
                
                if not zimmet_detay:
                    return jsonify({
                        'success': False,
                        'error': f'Zimmetinizde {urun.urun_adi} bulunmuyor'
                    }), 400
                
                kalan_miktar = zimmet_detay.miktar - zimmet_detay.kullanilan_miktar
                
                if kalan_miktar < miktar:
                    return jsonify({
                        'success': False,
                        'error': f'Yetersiz zimmet! Kalan: {kalan_miktar} {urun.birim}'
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
                
                # Setup miktarını bul
                from models import OdaTipi, SetupIcerik
                oda = Oda.query.get(oda_id)
                setup_miktari = 0
                
                if oda and oda.oda_tipi_id:
                    oda_tipi = OdaTipi.query.get(oda.oda_tipi_id)
                    if oda_tipi:
                        for setup in oda_tipi.setuplar:
                            if not setup.aktif:
                                continue
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
                
                # Zimmet stoğundan düş
                zimmet_detay.kullanilan_miktar += miktar
                zimmet_detay.kalan_miktar = zimmet_detay.miktar - zimmet_detay.kullanilan_miktar
                
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
                    zimmet_detay_id=zimmet_detay.id,
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
                
                # Zimmet kontrolü
                aktif_zimmet = PersonelZimmet.query.filter_by(
                    personel_id=kullanici_id,
                    durum='aktif'
                ).first()
                
                if not aktif_zimmet:
                    return jsonify({
                        'success': False,
                        'error': 'Aktif zimmetiniz bulunamadı'
                    }), 404
                
                zimmet_detay = PersonelZimmetDetay.query.filter_by(
                    zimmet_id=aktif_zimmet.id,
                    urun_id=urun_id
                ).first()
                
                if not zimmet_detay:
                    return jsonify({
                        'success': False,
                        'error': f'Zimmetinizde {urun.urun_adi} bulunmuyor'
                    }), 400
                
                kalan_miktar = zimmet_detay.miktar - zimmet_detay.kullanilan_miktar
                
                if kalan_miktar < miktar:
                    return jsonify({
                        'success': False,
                        'error': f'Yetersiz zimmet! Kalan: {kalan_miktar} {urun.birim}'
                    }), 400
                
                # Zimmet stoğundan düş
                zimmet_detay.kullanilan_miktar += miktar
                zimmet_detay.kalan_miktar = zimmet_detay.miktar - zimmet_detay.kullanilan_miktar
                
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
                    zimmet_detay_id=zimmet_detay.id,
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
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
            
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
                islem_tipi='kontrol',
                islem_tarihi=get_kktc_now(),
                aciklama='Sarfiyat yok - Kontrol tamamlandı'
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
                # Görev detay ID verilmemişse, bugünkü görevi bul ve tamamla
                try:
                    from models import GorevDetay, GorevDurumLog, GunlukGorev
                    
                    bugun = date.today()
                    detay = GorevDetay.query.join(GunlukGorev).filter(
                        GunlukGorev.personel_id == kullanici_id,
                        GunlukGorev.gorev_tarihi == bugun,
                        GorevDetay.oda_id == oda_id,
                        GorevDetay.durum != 'completed'
                    ).first()
                    
                    if detay:
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
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
            
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
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
            
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
        Oda için DND kaydı oluşturur
        3 kez DND kaydı yapılırsa görev otomatik tamamlanır
        """
        try:
            from models import GorevDetay, GunlukGorev, DNDKontrol, GorevDurumLog
            from datetime import date
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Geçersiz istek'}), 400
            
            oda_id = data.get('oda_id')
            gorev_detay_id = data.get('gorev_detay_id')
            
            if not oda_id:
                return jsonify({'success': False, 'error': 'Oda ID gerekli'}), 400
            
            kullanici_id = session.get('kullanici_id')
            bugun = date.today()
            simdi = get_kktc_now()
            
            # Oda bilgisini al
            oda = db.session.get(Oda, oda_id)
            if not oda:
                return jsonify({'success': False, 'error': 'Oda bulunamadı'}), 404
            
            # Görev detayını bul veya oluştur
            detay = None
            if gorev_detay_id:
                detay = GorevDetay.query.get(gorev_detay_id)
            
            if not detay:
                # Bugünkü görevi bul
                detay = GorevDetay.query.join(GunlukGorev).filter(
                    GunlukGorev.personel_id == kullanici_id,
                    GunlukGorev.gorev_tarihi == bugun,
                    GorevDetay.oda_id == oda_id
                ).first()
            
            if not detay:
                return jsonify({'success': False, 'error': 'Bu oda için görev bulunamadı'}), 404
            
            # DND sayısını artır
            onceki_durum = detay.durum
            detay.dnd_sayisi += 1
            detay.son_dnd_zamani = simdi
            detay.durum = 'dnd_pending'
            
            # DND kontrol kaydı oluştur
            dnd_kontrol = DNDKontrol(
                gorev_detay_id=detay.id,
                kontrol_eden_id=kullanici_id,
                notlar=f'DND kontrolü #{detay.dnd_sayisi}'
            )
            db.session.add(dnd_kontrol)
            
            mesaj = f'Oda {oda.oda_no} DND olarak işaretlendi ({detay.dnd_sayisi}/3)'
            otomatik_tamamlandi = False
            
            # 3 kez DND kontrolü yapıldıysa otomatik tamamla
            if detay.dnd_sayisi >= 3:
                detay.durum = 'completed'
                detay.kontrol_zamani = simdi
                detay.notlar = '3 kez DND kontrolü yapıldı - Otomatik tamamlandı (Kontrol edilmedi)'
                mesaj = f'Oda {oda.oda_no} - 3. DND kontrolü tamamlandı!'
                otomatik_tamamlandi = True
                
                # Ana görevin durumunu güncelle
                gorev = detay.gorev
                if gorev:
                    tamamlanan = sum(1 for d in gorev.detaylar if d.durum == 'completed')
                    if tamamlanan == len(gorev.detaylar):
                        gorev.durum = 'completed'
                        gorev.tamamlanma_tarihi = simdi
                    elif tamamlanan > 0:
                        gorev.durum = 'in_progress'
            
            # Log kaydı oluştur
            log = GorevDurumLog(
                gorev_detay_id=detay.id,
                onceki_durum=onceki_durum,
                yeni_durum=detay.durum,
                degistiren_id=kullanici_id,
                aciklama=f'DND kontrolü #{detay.dnd_sayisi}'
            )
            db.session.add(log)
            
            db.session.commit()
            
            # Audit log
            audit_create(
                tablo_adi='gorev_detay',
                kayit_id=detay.id,
                yeni_deger={
                    'oda_id': oda_id,
                    'dnd_sayisi': detay.dnd_sayisi,
                    'durum': detay.durum
                },
                aciklama=f"Oda {oda.oda_no} - DND kontrolü #{detay.dnd_sayisi}"
            )
            
            return jsonify({
                'success': True,
                'message': mesaj,
                'dnd_sayisi': detay.dnd_sayisi,
                'otomatik_tamamlandi': otomatik_tamamlandi
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_dnd_kaydet')
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
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
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
            from datetime import date
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
            
            kullanici_id = session.get('kullanici_id')
            kullanici = Kullanici.query.get(kullanici_id)
            
            tarih_str = request.args.get('tarih', date.today().isoformat())
            tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
            
            # Görev özetini al
            ozet = GorevService.get_task_summary(kullanici_id, tarih)
            
            # Bekleyen görevleri al
            bekleyen = GorevService.get_pending_tasks(kullanici_id, tarih)
            
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
            
            # Tamamlanan görevleri al
            tamamlanan = GorevService.get_completed_tasks(kullanici_id, tarih)
            
            # DND görevleri al
            dnd_gorevler = GorevService.get_dnd_tasks(kullanici_id, tarih)
            
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

