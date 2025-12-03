"""
Admin Minibar Route'ları

Bu modül admin minibar yönetimi ile ilgili endpoint'leri içerir.

Endpoint'ler:
- /admin/depo-stoklari - Depo stok durumları
- /admin/oda-minibar-stoklari - Oda minibar stokları
- /admin/oda-minibar-detay/<int:oda_id> - Oda minibar detay
- /admin/minibar-sifirla - Minibar sıfırlama
- /admin/minibar-islemleri - Minibar işlemleri listesi
- /admin/minibar-islem-sil/<int:islem_id> - Minibar işlem silme
- /admin/minibar-durumlari - Minibar durumları özet
- /api/minibar-islem-detay/<int:islem_id> - Minibar işlem detay API
- /api/admin/verify-password - Şifre doğrulama API

Roller:
- sistem_yoneticisi
- admin
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_file
from models import db, Kullanici, Oda, Kat, MinibarIslem, MinibarIslemDetay, StokHareket, UrunGrup
from utils.decorators import login_required, role_required
from utils.helpers import log_islem, log_hata
from utils.audit import serialize_model


def register_admin_minibar_routes(app):
    """Admin minibar route'larını kaydet"""
    
    # ============================================================================
    # DEPO STOK YÖNETİMİ
    # ============================================================================
    
    @app.route('/admin/depo-stoklari')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_depo_stoklari():
        """Depo stok durumlarını gösterir"""
        try:
            from utils.helpers import get_depo_stok_durumu, export_depo_stok_excel
            
            # Filtre parametreleri
            otel_id = request.args.get('otel_id', type=int)
            depo_id = request.args.get('depo_sorumlusu_id', type=int)
            grup_id = request.args.get('grup_id', type=int)
            export_format = request.args.get('format', '')
            
            # Filtre için gerekli verileri getir
            from models import Otel
            oteller = Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()
            gruplar = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
            
            # Otel seçilmeden stok listesi gösterme
            stok_listesi = []
            if otel_id:
                # Stok durumlarını getir (depo + zimmet) - Otel bazlı
                stok_listesi = get_depo_stok_durumu(grup_id=grup_id, depo_sorumlusu_id=depo_id, otel_id=otel_id)
                
                # Excel export
                if export_format == 'excel':
                    excel_buffer = export_depo_stok_excel(stok_listesi)
                    if excel_buffer:
                        from datetime import datetime
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
                        filename = f'depo_stoklari_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                        
                        # Log kaydı
                        log_islem('export', 'depo_stoklari', {
                            'format': 'excel',
                            'otel_id': otel_id,
                            'kayit_sayisi': len(stok_listesi)
                        })
                        
                        return send_file(
                            excel_buffer,
                            as_attachment=True,
                            download_name=filename,
                            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                    else:
                        flash('Excel dosyası oluşturulamadı.', 'danger')
                        return redirect(url_for('admin_depo_stoklari'))
                
                # Log kaydı
                log_islem('goruntuleme', 'depo_stoklari', {
                    'otel_id': otel_id,
                    'depo_id': depo_id,
                    'kayit_sayisi': len(stok_listesi)
                })
            
            return render_template('sistem_yoneticisi/depo_stoklari.html',
                                 stok_listesi=stok_listesi,
                                 oteller=oteller,
                                 gruplar=gruplar,
                                 secili_otel_id=otel_id,
                                 secili_depo_id=depo_id,
                                 secili_grup_id=grup_id)
            
        except Exception as e:
            log_hata(e, modul='admin_minibar')
            flash('Depo stokları yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('sistem_yoneticisi_dashboard'))

    # ============================================================================
    # İLK STOK YÜKLEME
    # ============================================================================

    @app.route('/admin/ilk-stok-yukleme/<int:otel_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi')
    def ilk_stok_yukleme(otel_id):
        """İlk stok yükleme - Excel'den ürün ve adet bilgisi alarak stok girişi yapar"""
        from models import Otel, Urun, SatinAlmaIslem, SatinAlmaIslemDetay, UrunStok, Tedarikci
        from datetime import datetime, timezone
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
        import pandas as pd
        import io
        
        try:
            otel = Otel.query.get_or_404(otel_id)
            
            # Zaten yükleme yapılmış mı kontrol et
            if otel.ilk_stok_yuklendi:
                return jsonify({
                    'success': False,
                    'message': f'{otel.ad} için ilk stok yüklemesi zaten yapılmış.'
                }), 400
            
            if request.method == 'POST':
                # Excel dosyasını al
                if 'excel_file' not in request.files:
                    return jsonify({'success': False, 'message': 'Excel dosyası seçilmedi.'}), 400
                
                file = request.files['excel_file']
                if file.filename == '':
                    return jsonify({'success': False, 'message': 'Dosya seçilmedi.'}), 400
                
                # Dosya uzantısı kontrolü
                if not file.filename.endswith(('.xlsx', '.xls')):
                    return jsonify({'success': False, 'message': 'Sadece Excel dosyaları (.xlsx, .xls) kabul edilir.'}), 400
                
                # Önizleme mi yoksa kayıt mı?
                action = request.form.get('action', 'preview')
                
                try:
                    # Excel'i oku
                    df = pd.read_excel(io.BytesIO(file.read()))
                    
                    # Sütun kontrolü
                    required_columns = ['urun_adi', 'adet']
                    df.columns = df.columns.str.lower().str.strip()
                    
                    missing_cols = [col for col in required_columns if col not in df.columns]
                    if missing_cols:
                        return jsonify({
                            'success': False,
                            'message': f'Eksik sütunlar: {", ".join(missing_cols)}. Excel dosyasında "urun_adi" ve "adet" sütunları olmalıdır.'
                        }), 400
                    
                    # Boş satırları temizle
                    df = df.dropna(subset=['urun_adi', 'adet'])
                    df['adet'] = pd.to_numeric(df['adet'], errors='coerce').fillna(0).astype(int)
                    df = df[df['adet'] > 0]
                    
                    if df.empty:
                        return jsonify({'success': False, 'message': 'Excel dosyasında geçerli ürün bulunamadı.'}), 400
                    
                    # Ürünleri eşleştir
                    urunler = Urun.query.filter_by(aktif=True).all()
                    urun_map = {u.urun_adi.lower().strip(): u for u in urunler}
                    
                    eslesen_urunler = []
                    eslesmeyen_urunler = []
                    
                    for _, row in df.iterrows():
                        urun_adi = str(row['urun_adi']).strip()
                        adet = int(row['adet'])
                        
                        # Tam eşleşme dene
                        urun = urun_map.get(urun_adi.lower())
                        
                        if urun:
                            eslesen_urunler.append({
                                'urun_id': urun.id,
                                'urun_adi': urun.urun_adi,
                                'excel_urun_adi': urun_adi,
                                'adet': adet,
                                'birim': urun.birim
                            })
                        else:
                            eslesmeyen_urunler.append({
                                'excel_urun_adi': urun_adi,
                                'adet': adet
                            })
                    
                    # Önizleme modunda sonuçları döndür
                    if action == 'preview':
                        return jsonify({
                            'success': True,
                            'preview': True,
                            'eslesen_urunler': eslesen_urunler,
                            'eslesmeyen_urunler': eslesmeyen_urunler,
                            'toplam_eslesen': len(eslesen_urunler),
                            'toplam_eslesmeyen': len(eslesmeyen_urunler)
                        })
                    
                    # Kayıt modunda işlemi gerçekleştir
                    if action == 'confirm':
                        if not eslesen_urunler:
                            return jsonify({'success': False, 'message': 'Eşleşen ürün bulunamadı.'}), 400
                        
                        # Tedarikçi ID=1 kontrolü
                        tedarikci = Tedarikci.query.get(1)
                        if not tedarikci:
                            return jsonify({'success': False, 'message': 'Varsayılan tedarikçi (ID=1) bulunamadı.'}), 400
                        
                        # Satın alma işlemi oluştur
                        islem_no = f"ILK-{otel_id}-{get_kktc_now().strftime('%Y%m%d%H%M%S')}"
                        
                        satin_alma = SatinAlmaIslem(
                            islem_no=islem_no,
                            tedarikci_id=1,  # Varsayılan tedarikçi
                            otel_id=otel_id,
                            fatura_no=f'ILK-STOK-{otel_id}',
                            fatura_tarihi=get_kktc_now().date(),
                            odeme_sekli='diger',
                            odeme_durumu='odendi',
                            toplam_tutar=0,  # 0 TL
                            kdv_tutari=0,
                            genel_toplam=0,
                            aciklama=f'{otel.ad} için ilk stok yüklemesi',
                            durum='aktif',
                            olusturan_id=session['kullanici_id']
                        )
                        db.session.add(satin_alma)
                        db.session.flush()
                        
                        # Detayları ve stokları ekle
                        for item in eslesen_urunler:
                            # Satın alma detayı
                            detay = SatinAlmaIslemDetay(
                                islem_id=satin_alma.id,
                                urun_id=item['urun_id'],
                                miktar=item['adet'],
                                birim_fiyat=0,  # 0 TL
                                kdv_orani=0,
                                kdv_tutari=0,
                                toplam_fiyat=0
                            )
                            db.session.add(detay)
                            
                            # Stok girişi - UrunStok tablosuna
                            urun_stok = UrunStok.query.filter_by(
                                urun_id=item['urun_id'],
                                otel_id=otel_id
                            ).first()
                            
                            if urun_stok:
                                urun_stok.mevcut_stok += item['adet']
                                urun_stok.son_giris_tarihi = get_kktc_now()
                                urun_stok.son_guncelleme_tarihi = get_kktc_now()
                                urun_stok.son_guncelleyen_id = session['kullanici_id']
                            else:
                                urun_stok = UrunStok(
                                    urun_id=item['urun_id'],
                                    otel_id=otel_id,
                                    mevcut_stok=item['adet'],
                                    son_giris_tarihi=get_kktc_now(),
                                    son_guncelleme_tarihi=get_kktc_now(),
                                    son_guncelleyen_id=session['kullanici_id']
                                )
                                db.session.add(urun_stok)
                            
                            # Stok hareketi kaydet
                            stok_hareket = StokHareket(
                                urun_id=item['urun_id'],
                                hareket_tipi='giris',
                                miktar=item['adet'],
                                aciklama=f'İlk stok yüklemesi - {otel.ad}',
                                islem_yapan_id=session['kullanici_id']
                            )
                            db.session.add(stok_hareket)
                        
                        # Oteli güncelle - ilk stok yüklendi olarak işaretle
                        otel.ilk_stok_yuklendi = True
                        otel.ilk_stok_yukleme_tarihi = get_kktc_now()
                        otel.ilk_stok_yukleyen_id = session['kullanici_id']
                        
                        db.session.commit()
                        
                        # Log kaydı
                        log_islem('ilk_stok_yukleme', 'depo_stoklari', {
                            'otel_id': otel_id,
                            'otel_adi': otel.ad,
                            'urun_sayisi': len(eslesen_urunler),
                            'toplam_adet': sum(u['adet'] for u in eslesen_urunler),
                            'islem_no': islem_no
                        })
                        
                        return jsonify({
                            'success': True,
                            'message': f'{len(eslesen_urunler)} ürün başarıyla stoka eklendi.',
                            'islem_no': islem_no
                        })
                    
                except Exception as e:
                    db.session.rollback()
                    log_hata(e, modul='ilk_stok_yukleme')
                    return jsonify({'success': False, 'message': f'Excel işlenirken hata: {str(e)}'}), 500
            
            return jsonify({'success': False, 'message': 'Geçersiz istek.'}), 400
            
        except Exception as e:
            log_hata(e, modul='ilk_stok_yukleme')
            return jsonify({'success': False, 'message': f'Hata: {str(e)}'}), 500

    @app.route('/api/otel-ilk-stok-durumu/<int:otel_id>')
    @login_required
    @role_required('sistem_yoneticisi')
    def otel_ilk_stok_durumu(otel_id):
        """Otelin ilk stok yükleme durumunu döndürür"""
        from models import Otel
        
        try:
            otel = Otel.query.get_or_404(otel_id)
            return jsonify({
                'success': True,
                'otel_id': otel.id,
                'otel_adi': otel.ad,
                'ilk_stok_yuklendi': otel.ilk_stok_yuklendi,
                'ilk_stok_yukleme_tarihi': otel.ilk_stok_yukleme_tarihi.isoformat() if otel.ilk_stok_yukleme_tarihi else None
            })
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ============================================================================
    # ODA MİNİBAR YÖNETİMİ
    # ============================================================================

    @app.route('/admin/oda-minibar-stoklari')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_oda_minibar_stoklari():
        """Tüm odaların minibar stok durumlarını listeler"""
        try:
            from utils.helpers import get_oda_minibar_stoklari
            
            # Filtre parametresi
            kat_id = request.args.get('kat_id', type=int)
            
            # Oda minibar stoklarını getir
            oda_listesi = get_oda_minibar_stoklari(kat_id=kat_id)
            
            # Boş ve dolu odaları ayır
            dolu_odalar = [oda for oda in oda_listesi if not oda['bos_mu']]
            bos_odalar = [oda for oda in oda_listesi if oda['bos_mu']]
            
            # Katları getir (filtre için)
            katlar = Kat.query.filter_by(aktif=True).order_by(Kat.kat_no).all()
            
            # Log kaydı
            log_islem('goruntuleme', 'oda_minibar_stoklari', {
                'kat_id': kat_id,
                'toplam_oda': len(oda_listesi),
                'dolu_oda': len(dolu_odalar),
                'bos_oda': len(bos_odalar)
            })
            
            return render_template('sistem_yoneticisi/oda_minibar_stoklari.html',
                                 dolu_odalar=dolu_odalar,
                                 bos_odalar=bos_odalar,
                                 katlar=katlar,
                                 secili_kat_id=kat_id)
            
        except Exception as e:
            log_hata(e, modul='admin_minibar')
            flash('Oda minibar stokları yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('sistem_yoneticisi_dashboard'))

    @app.route('/admin/oda-minibar-detay/<int:oda_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_oda_minibar_detay(oda_id):
        """Belirli bir odanın minibar detaylarını gösterir"""
        try:
            from utils.helpers import get_oda_minibar_detay
            
            # Oda detaylarını getir
            detay = get_oda_minibar_detay(oda_id)
            
            if not detay:
                flash('Oda bulunamadı.', 'danger')
                return redirect(url_for('admin_oda_minibar_stoklari'))
            
            # Log kaydı
            log_islem('goruntuleme', 'oda_minibar_detay', {
                'oda_id': oda_id,
                'oda_no': detay['oda'].oda_no
            })
            
            return render_template('sistem_yoneticisi/oda_minibar_detay.html',
                                 detay=detay)
            
        except Exception as e:
            log_hata(e, modul='admin_minibar', extra_info={'oda_id': oda_id})
            flash('Oda detayları yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('admin_oda_minibar_stoklari'))

    # ============================================================================
    # MİNİBAR SIFIRLAMA
    # ============================================================================

    @app.route('/admin/minibar-sifirla', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_minibar_sifirla():
        """Minibar sıfırlama sayfası"""
        try:
            from utils.helpers import get_minibar_sifirlama_ozeti, sifirla_minibar_stoklari
            
            if request.method == 'POST':
                # Şifre doğrulama
                sifre = request.form.get('password', '')
                
                if not sifre:
                    flash('Şifre alanı boş bırakılamaz.', 'danger')
                    return redirect(url_for('admin_minibar_sifirla'))
                
                # Kullanıcıyı getir
                kullanici = Kullanici.query.get(session['kullanici_id'])
                
                # Şifre kontrolü
                if not kullanici.sifre_kontrol(sifre):
                    # Başarısız deneme logla
                    log_islem('sifre_hatasi', 'minibar_sifirlama', {
                        'kullanici_id': kullanici.id,
                        'kullanici_adi': kullanici.kullanici_adi
                    })
                    flash('Şifre hatalı, lütfen tekrar deneyin.', 'danger')
                    return redirect(url_for('admin_minibar_sifirla'))
                
                # Sıfırlama işlemini yap
                sonuc = sifirla_minibar_stoklari(kullanici.id)
                
                if sonuc['success']:
                    flash(sonuc['message'], 'success')
                    flash(f"✅ {sonuc['etkilenen_oda_sayisi']} oda etkilendi", 'info')
                    flash(f"📦 Toplam {sonuc['toplam_sifirlanan_stok']} ürün sıfırlandı", 'info')
                else:
                    flash(sonuc['message'], 'danger')
                
                return redirect(url_for('admin_minibar_sifirla'))
            
            # GET request - Özet bilgileri göster
            ozet = get_minibar_sifirlama_ozeti()
            
            # Log kaydı
            log_islem('goruntuleme', 'minibar_sifirlama_sayfa', {
                'toplam_oda': ozet['toplam_oda_sayisi'],
                'dolu_oda': ozet['dolu_oda_sayisi']
            })
            
            return render_template('sistem_yoneticisi/minibar_sifirla.html',
                                 ozet=ozet)
            
        except Exception as e:
            log_hata(e, modul='admin_minibar')
            flash('Sayfa yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('sistem_yoneticisi_dashboard'))

    # ============================================================================
    # MİNİBAR İŞLEMLERİ
    # ============================================================================

    @app.route('/admin/minibar-islemleri')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_minibar_islemleri():
        """Tüm minibar işlemlerini listele"""
        try:
            # Filtreler
            oda_id = request.args.get('oda_id', type=int)
            personel_id = request.args.get('personel_id', type=int)
            islem_tipi = request.args.get('islem_tipi', '')
            baslangic_tarih = request.args.get('baslangic_tarih', '')
            bitis_tarih = request.args.get('bitis_tarih', '')
            
            # Sayfalama
            sayfa = request.args.get('sayfa', 1, type=int)
            per_page = 50
            
            # Sorgu oluştur - Eager loading kaldırıldı (DB kolon hatası için geçici çözüm)
            query = MinibarIslem.query.options(
                db.joinedload(MinibarIslem.oda).joinedload(Oda.kat),
                db.joinedload(MinibarIslem.personel)
                # detaylar eager loading kaldırıldı - satis_fiyati kolonu DB'de yok
            )
            
            if oda_id:
                query = query.filter(MinibarIslem.oda_id == oda_id)
            if personel_id:
                query = query.filter(MinibarIslem.personel_id == personel_id)
            if islem_tipi:
                query = query.filter(MinibarIslem.islem_tipi == islem_tipi)
            if baslangic_tarih:
                query = query.filter(MinibarIslem.islem_tarihi >= baslangic_tarih)
            if bitis_tarih:
                query = query.filter(MinibarIslem.islem_tarihi <= bitis_tarih)
            
            # Sayfalama
            islemler = query.order_by(MinibarIslem.islem_tarihi.desc()).paginate(
                page=sayfa, per_page=per_page, error_out=False
            )
            
            # Odalar ve personeller (filtre için)
            odalar = Oda.query.filter_by(aktif=True).order_by(Oda.oda_no).all()
            personeller = Kullanici.query.filter(
                Kullanici.rol.in_(['depo_sorumlusu', 'kat_sorumlusu']),
                Kullanici.aktif.is_(True)
            ).order_by(Kullanici.ad, Kullanici.soyad).all()
            
            # Log kaydı
            log_islem('goruntuleme', 'minibar_islemleri', {
                'sayfa': sayfa,
                'kayit_sayisi': islemler.total
            })
            
            return render_template('sistem_yoneticisi/admin_minibar_islemleri.html',
                                 islemler=islemler,
                                 odalar=odalar,
                                 personeller=personeller,
                                 oda_id=oda_id,
                                 personel_id=personel_id,
                                 islem_tipi=islem_tipi,
                                 baslangic_tarih=baslangic_tarih,
                                 bitis_tarih=bitis_tarih)
            
        except Exception as e:
            log_hata(e, modul='admin_minibar_islemleri')
            flash('Minibar işlemleri yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('sistem_yoneticisi_dashboard'))

    @app.route('/admin/minibar-islem-sil/<int:islem_id>', methods=['DELETE', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_minibar_islem_sil(islem_id):
        """Minibar işlem kaydını sil ve stok hareketlerini geri al"""
        try:
            islem = db.session.get(MinibarIslem, islem_id)
            if not islem:
                return jsonify({'success': False, 'message': 'İşlem bulunamadı'}), 404
            
            # Eski değeri sakla
            eski_deger = serialize_model(islem)
            
            # Stok hareketlerini geri al
            for detay in islem.detaylar:
                if detay.eklenen_miktar > 0:
                    # Eklenen miktarı depoya geri ekle
                    hareket = StokHareket(
                        urun_id=detay.urun_id,
                        hareket_tipi='giris',
                        miktar=detay.eklenen_miktar,
                        aciklama=f'Minibar işlem iptali - Oda {islem.oda.oda_no}',
                        islem_yapan_id=session['kullanici_id']
                    )
                    db.session.add(hareket)
            
            # İşlemi sil
            db.session.delete(islem)
            db.session.commit()
            
            # Audit log
            from utils.audit import audit_delete
            audit_delete(
                tablo_adi='minibar_islemleri',
                kayit_id=islem_id,
                eski_deger=eski_deger,
                aciklama='Admin minibar işlem silme'
            )
            
            # Log kaydı
            log_islem('silme', 'minibar_islem', {
                'islem_id': islem_id,
                'oda_id': islem.oda_id
            })
            
            flash('Minibar işlemi başarıyla silindi ve stoklar geri alındı.', 'success')
            return jsonify({'success': True, 'message': 'İşlem silindi'})
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='admin_minibar_islem_sil')
            return jsonify({'success': False, 'message': 'Silme işlemi başarısız'}), 500

    @app.route('/admin/minibar-durumlari')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_minibar_durumlari():
        """Tüm odaların minibar durumlarını özet olarak göster"""
        try:
            # Kat filtresi
            kat_id = request.args.get('kat_id', type=int)
            
            # Odaları getir
            query = Oda.query.options(
                db.joinedload(Oda.kat)
            ).filter_by(aktif=True)
            
            if kat_id:
                query = query.filter(Oda.kat_id == kat_id)
            
            odalar = query.order_by(Oda.oda_no).all()
            
            # Her oda için son minibar işlemini getir
            oda_durumlari = []
            for oda in odalar:
                son_islem = MinibarIslem.query.filter_by(oda_id=oda.id).order_by(
                    MinibarIslem.islem_tarihi.desc()
                ).first()
                
                oda_durumlari.append({
                    'oda': oda,
                    'son_islem': son_islem
                })
            
            # Katlar (filtre için)
            katlar = Kat.query.filter_by(aktif=True).order_by(Kat.kat_no).all()
            
            # Log kaydı
            log_islem('goruntuleme', 'minibar_durumlari', {
                'kat_id': kat_id,
                'oda_sayisi': len(odalar)
            })
            
            return render_template('sistem_yoneticisi/admin_minibar_durumlari.html',
                                 oda_durumlari=oda_durumlari,
                                 katlar=katlar,
                                 kat_id=kat_id)
            
        except Exception as e:
            log_hata(e, modul='admin_minibar_durumlari')
            flash('Minibar durumları yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('sistem_yoneticisi_dashboard'))

    # ============================================================================
    # API ENDPOINT'LERİ
    # ============================================================================

    @app.route('/api/minibar-islem-detay/<int:islem_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_minibar_islem_detay(islem_id):
        """Minibar işlem detaylarını JSON olarak döndür"""
        try:
            islem = db.session.query(MinibarIslem).options(
                db.joinedload(MinibarIslem.oda).joinedload(Oda.kat),
                db.joinedload(MinibarIslem.personel),
                db.joinedload(MinibarIslem.detaylar).joinedload(MinibarIslemDetay.urun)
            ).filter_by(id=islem_id).first()
            
            if not islem:
                return jsonify({'success': False, 'message': 'Minibar işlemi bulunamadı'}), 404
            
            # Log kaydı
            log_islem('goruntuleme', 'minibar_islem_detay', {
                'islem_id': islem_id,
                'oda_id': islem.oda_id
            })
            
            # JSON formatında döndür
            return jsonify({
                'success': True,
                'islem': {
                    'id': islem.id,
                    'oda_no': islem.oda.oda_no,
                    'kat_adi': islem.oda.kat.kat_adi,
                    'islem_tipi': islem.islem_tipi,
                    'islem_tarihi': islem.islem_tarihi.strftime('%d.%m.%Y %H:%M'),
                    'personel': f"{islem.personel.ad} {islem.personel.soyad}",
                    'aciklama': islem.aciklama or '',
                    'detaylar': [
                        {
                            'urun_adi': detay.urun.urun_adi,
                            'baslangic_stok': detay.baslangic_stok,
                            'eklenen_miktar': detay.eklenen_miktar,
                            'tuketim': detay.tuketim,
                            'bitis_stok': detay.bitis_stok
                        }
                        for detay in islem.detaylar
                    ]
                }
            })
            
        except Exception as e:
            log_hata(e, modul='api_minibar_islem_detay')
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/admin/verify-password', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_admin_verify_password():
        """AJAX ile admin şifresini doğrular"""
        try:
            data = request.get_json()
            password = data.get('password', '')
            
            if not password:
                return jsonify({
                    'success': False,
                    'message': 'Şifre alanı boş bırakılamaz'
                }), 400
            
            # Kullanıcıyı getir
            kullanici = Kullanici.query.get(session['kullanici_id'])
            
            # Şifre kontrolü
            if kullanici.sifre_kontrol(password):
                return jsonify({
                    'success': True,
                    'message': 'Şifre doğrulandı'
                })
            else:
                # Başarısız deneme logla
                log_islem('sifre_hatasi', 'minibar_sifirlama_api', {
                    'kullanici_id': kullanici.id,
                    'kullanici_adi': kullanici.kullanici_adi
                })
                
                return jsonify({
                    'success': False,
                    'message': 'Şifre hatalı'
                }), 401
            
        except Exception as e:
            log_hata(e, modul='admin_minibar')
            return jsonify({
                'success': False,
                'message': 'Bir hata oluştu'
            }), 500

