"""
Depo Sorumlusu Route'ları

Bu modül depo sorumlusu ile ilgili endpoint'leri içerir.

Endpoint'ler:
- /stok-giris - Stok giriş işlemi
- /stok-duzenle/<int:hareket_id> - Stok hareket düzenleme
- /stok-sil/<int:hareket_id> - Stok hareket silme
- /personel-zimmet - Personel zimmet atama
- /satin-alma-siparis - Satın alma siparişi oluşturma
- /siparis-listesi - Sipariş listesi ve takip
- /siparis-detay/<int:siparis_id> - Sipariş detayları
- /siparis-durum-guncelle/<int:siparis_id> - Sipariş durum güncelleme
- /siparis-stok-giris/<int:siparis_id> - Sipariş teslimatından stok girişi
- /otomatik-siparis-onerileri - Otomatik sipariş önerileri
- /siparis-onerisi-onayla - Sipariş önerisi onaylama
- /tedarikci-iletisim/<int:tedarikci_id> - Tedarikçi iletişim kayıtları
- /tedarikci-dokuman-yukle - Tedarikçi belge yükleme
- /tedarikci-dokuman-indir/<int:dokuman_id> - Tedarikçi belge indirme

Roller:
- depo_sorumlusu
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.utils import secure_filename
from models import (db, StokHareket, Urun, UrunGrup, Kullanici, PersonelZimmet, PersonelZimmetDetay,
                   SatinAlmaSiparisi, SatinAlmaSiparisDetay, SatinAlmaIslem, SatinAlmaIslemDetay,
                   Tedarikci, TedarikciIletisim, TedarikciDokuman, UrunStok,
                   KatSorumlusuSiparisTalebi, KatSorumlusuSiparisTalepDetay)
from sqlalchemy import desc
from utils.decorators import login_required, role_required
from utils.helpers import log_islem, log_hata, get_stok_toplamlari
from utils.audit import audit_create, audit_update, audit_delete, serialize_model
from utils.satin_alma_servisleri import SatinAlmaServisi
from utils.tedarikci_servisleri import TedarikciServisi
from datetime import datetime, date, timedelta
import os


def register_depo_routes(app):
    """Depo sorumlusu route'larını kaydet"""
    
    @app.route('/stok-giris', methods=['GET', 'POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def stok_giris():
        """Depo sorumlusu stok giriş sayfası"""
        from utils.authorization import get_kullanici_otelleri, get_otel_filtreleme_secenekleri
        
        # Kullanıcının erişebileceği oteller
        kullanici_otelleri = get_kullanici_otelleri()
        otel_secenekleri = get_otel_filtreleme_secenekleri()
        
        # Seçili otel (query string'den veya ilk otel)
        secili_otel_id = request.args.get('otel_id', type=int)
        if not secili_otel_id and kullanici_otelleri:
            secili_otel_id = kullanici_otelleri[0].id
        
        if request.method == 'POST':
            try:
                urun_id = int(request.form['urun_id'])
                miktar = int(request.form['miktar'])
                hareket_tipi = request.form['hareket_tipi']
                aciklama = request.form.get('aciklama', '')
                
                urun = db.session.get(Urun, urun_id)
                stok_hareket = StokHareket(
                    urun_id=urun_id,
                    hareket_tipi=hareket_tipi,
                    miktar=miktar,
                    aciklama=aciklama,
                    islem_yapan_id=session['kullanici_id']
                )
                db.session.add(stok_hareket)
                db.session.commit()
                
                # Audit Trail
                audit_create('stok_hareket', stok_hareket.id, stok_hareket)
                
                # Log kaydı
                log_islem('ekleme', 'stok', {
                    'urun_id': urun_id,
                    'urun_adi': urun.urun_adi if urun else 'Bilinmeyen',
                    'hareket_tipi': hareket_tipi,
                    'miktar': miktar,
                    'aciklama': aciklama
                })
                
                flash('Stok girişi başarıyla yapıldı.', 'success')
                return redirect(url_for('stok_giris'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Hata oluştu: {str(e)}', 'danger')
        
        # Aktif ürün gruplarını getir
        gruplar = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
        
        # Aktif ürünleri grup ile birlikte getir
        urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
        
        # Son stok hareketlerini getir (otel filtrelemesi olmadan - tüm stok hareketleri)
        stok_hareketleri = StokHareket.query.order_by(StokHareket.islem_tarihi.desc()).limit(50).all()
        
        return render_template('depo_sorumlusu/stok_giris.html', 
                             gruplar=gruplar,
                             urunler=urunler, 
                             stok_hareketleri=stok_hareketleri,
                             otel_secenekleri=otel_secenekleri,
                             secili_otel_id=secili_otel_id)

    @app.route('/stok-duzenle/<int:hareket_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def stok_duzenle(hareket_id):
        """Stok hareket düzenleme"""
        hareket = StokHareket.query.get_or_404(hareket_id)
        
        if request.method == 'POST':
            try:
                # Eski değerleri kaydet
                eski_deger = serialize_model(hareket)
                
                hareket.miktar = int(request.form['miktar'])
                hareket.hareket_tipi = request.form['hareket_tipi']
                hareket.aciklama = request.form.get('aciklama', '')
                
                db.session.commit()
                
                # Audit Trail
                audit_update('stok_hareket', hareket.id, eski_deger, hareket)
                
                # Log kaydı
                log_islem('guncelleme', 'stok', {
                    'hareket_id': hareket.id,
                    'urun_id': hareket.urun_id,
                    'urun_adi': hareket.urun.urun_adi,
                    'hareket_tipi': hareket.hareket_tipi,
                    'miktar': hareket.miktar
                })
                
                flash('Stok hareketi başarıyla güncellendi.', 'success')
                return redirect(url_for('stok_giris'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Hata oluştu: {str(e)}', 'danger')
        
        urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
        return render_template('depo_sorumlusu/stok_duzenle.html', hareket=hareket, urunler=urunler)

    @app.route('/stok-sil/<int:hareket_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def stok_sil(hareket_id):
        """Stok hareket silme"""
        try:
            hareket = StokHareket.query.get_or_404(hareket_id)
            
            # Log kaydı için bilgileri sakla
            urun_adi = hareket.urun.urun_adi if hareket.urun else 'Bilinmeyen'
            hareket_tipi = hareket.hareket_tipi
            miktar = hareket.miktar
            
            # Eski değeri kaydet
            eski_deger = serialize_model(hareket)
            
            # Hareketi sil
            db.session.delete(hareket)
            db.session.commit()
            
            # Audit Trail
            audit_delete('stok_hareket', hareket_id, eski_deger)
            
            # Log kaydı
            log_islem('silme', 'stok', {
                'hareket_id': hareket_id,
                'urun_adi': urun_adi,
                'hareket_tipi': hareket_tipi,
                'miktar': miktar
            })
            
            flash('Stok hareketi başarıyla silindi.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('stok_giris'))

    @app.route('/personel-zimmet', methods=['GET', 'POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def personel_zimmet():
        """Personel zimmet atama"""
        from utils.authorization import get_kullanici_otelleri, get_otel_filtreleme_secenekleri
        
        # Kullanıcının erişebileceği oteller
        kullanici_otelleri = get_kullanici_otelleri()
        otel_secenekleri = get_otel_filtreleme_secenekleri()
        
        # Seçili otel
        secili_otel_id = request.args.get('otel_id', type=int)
        if not secili_otel_id and kullanici_otelleri:
            secili_otel_id = kullanici_otelleri[0].id
        
        if request.method == 'POST':
            try:
                personel_id = int(request.form['personel_id'])
                aciklama = request.form.get('aciklama', '')
                urun_ids = request.form.getlist('urun_ids')

                if not urun_ids:
                    flash('En az bir ürün seçmelisiniz.', 'warning')
                    return redirect(url_for('personel_zimmet'))

                # İstenen ürün miktarlarını topla
                urun_miktarlari = {}
                for urun_id in urun_ids:
                    try:
                        miktar = int(request.form.get(f'miktar_{urun_id}', 0))
                    except (TypeError, ValueError):
                        miktar = 0

                    if miktar > 0:
                        uid = int(urun_id)
                        urun_miktarlari[uid] = urun_miktarlari.get(uid, 0) + miktar

                if not urun_miktarlari:
                    flash('Seçilen ürünler için geçerli bir miktar giriniz.', 'warning')
                    return redirect(url_for('personel_zimmet'))

                # Stok uygunluğunu kontrol et
                stok_map = get_stok_toplamlari(list(urun_miktarlari.keys()))
                urun_kayitlari = {
                    urun.id: urun for urun in Urun.query.filter(Urun.id.in_(urun_miktarlari.keys())).all()
                }

                yetersiz_stok = []
                for uid, talep_miktari in urun_miktarlari.items():
                    mevcut = stok_map.get(uid, 0)
                    if talep_miktari > mevcut:
                        urun = urun_kayitlari.get(uid)
                        urun_adi = f"{urun.urun_adi} ({urun.birim})" if urun else f'ID {uid}'
                        yetersiz_stok.append((urun_adi, talep_miktari, mevcut))

                if yetersiz_stok:
                    detay_mesaji = '; '.join(
                        f"{urun_adi}: istenen {talep}, mevcut {mevcut}" for urun_adi, talep, mevcut in yetersiz_stok
                    )
                    flash(f'Stok yetersiz: {detay_mesaji}', 'danger')
                    return redirect(url_for('personel_zimmet'))

                # Zimmet başlık oluştur
                zimmet = PersonelZimmet(
                    personel_id=personel_id,
                    teslim_eden_id=session['kullanici_id'],
                    aciklama=aciklama
                )
                db.session.add(zimmet)
                db.session.flush()  # ID'yi almak için

                # Zimmet detayları oluştur
                for uid, miktar in urun_miktarlari.items():
                    detay = PersonelZimmetDetay(
                        zimmet_id=zimmet.id,
                        urun_id=uid,
                        miktar=miktar,
                        kalan_miktar=miktar
                    )
                    db.session.add(detay)

                    # Stok çıkışı kaydet
                    stok_hareket = StokHareket(
                        urun_id=uid,
                        hareket_tipi='cikis',
                        miktar=miktar,
                        aciklama=f'Zimmet atama - {aciklama}',
                        islem_yapan_id=session['kullanici_id']
                    )
                    db.session.add(stok_hareket)
                
                db.session.commit()
                
                # Audit Trail
                audit_create('personel_zimmet', zimmet.id, zimmet)
                
                flash('Zimmet başarıyla atandı.', 'success')
                return redirect(url_for('personel_zimmet'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Hata oluştu: {str(e)}', 'danger')
        
        # Kat sorumlularını otel bazlı filtrele
        if secili_otel_id:
            kat_sorumlulari = Kullanici.query.filter_by(rol='kat_sorumlusu', aktif=True, otel_id=secili_otel_id).all()
        else:
            kat_sorumlulari = Kullanici.query.filter_by(rol='kat_sorumlusu', aktif=True).all()
        
        urun_gruplari = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
        # Aktif ve iade edilmiş zimmetleri göster (iptal edilenleri gösterme)
        aktif_zimmetler = PersonelZimmet.query.filter(
            PersonelZimmet.durum.in_(['aktif', 'iade_edildi'])
        ).order_by(PersonelZimmet.zimmet_tarihi.desc()).all()
        
        return render_template('depo_sorumlusu/personel_zimmet.html', 
                             kat_sorumlulari=kat_sorumlulari, 
                             urun_gruplari=urun_gruplari, 
                             aktif_zimmetler=aktif_zimmetler,
                             otel_secenekleri=otel_secenekleri,
                             secili_otel_id=secili_otel_id)

    # ==================== SATIN ALMA SİPARİŞ ROUTE'LARI ====================
    
    @app.route('/satin-alma-siparis', methods=['GET', 'POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def satin_alma_siparis():
        """Satın alma siparişi oluşturma"""
        from utils.authorization import get_kullanici_otelleri, get_otel_filtreleme_secenekleri
        
        try:
            # Kullanıcının erişebileceği oteller
            kullanici_otelleri = get_kullanici_otelleri()
            otel_secenekleri = get_otel_filtreleme_secenekleri()
            
            # Seçili otel
            secili_otel_id = request.args.get('otel_id', type=int)
            if not secili_otel_id and kullanici_otelleri:
                secili_otel_id = kullanici_otelleri[0].id
            
            if request.method == 'POST':
                try:
                    # Form verilerini al
                    tedarikci_id = request.form.get('tedarikci_id')
                    if tedarikci_id:
                        tedarikci_id = int(tedarikci_id)
                    else:
                        tedarikci_id = None  # Tedarikçi seçilmemiş
                    
                    siparis_tarihi_str = request.form.get('siparis_tarihi')
                    aciklama = request.form.get('aciklama', '')
                    
                    # Otel ID'yi kullanıcının otelinden al
                    if not secili_otel_id and kullanici_otelleri:
                        secili_otel_id = kullanici_otelleri[0].id
                    otel_id = secili_otel_id
                    
                    # Tarih dönüşümü
                    if siparis_tarihi_str:
                        siparis_tarihi = datetime.strptime(siparis_tarihi_str, '%Y-%m-%d').date()
                    else:
                        siparis_tarihi = date.today()
                    
                    tahmini_teslimat_tarihi = siparis_tarihi  # Sipariş tarihi ile aynı
                    
                    # Ürün listesini al
                    urun_ids = request.form.getlist('urun_ids[]')
                    miktarlar = request.form.getlist('miktarlar[]')
                    
                    if not urun_ids:
                        flash('En az bir ürün seçmelisiniz.', 'warning')
                        return redirect(url_for('siparis_listesi'))
                    
                    # Ürün listesini hazırla (birim fiyat olmadan)
                    urunler = []
                    for i in range(len(urun_ids)):
                        try:
                            urunler.append({
                                'urun_id': int(urun_ids[i]),
                                'miktar': int(miktarlar[i]),
                                'birim_fiyat': 0.0  # Sipariş aşamasında fiyat yok
                            })
                        except (ValueError, IndexError) as e:
                            flash(f'Ürün bilgilerinde hata: {str(e)}', 'danger')
                            return redirect(url_for('siparis_listesi'))
                    
                    # Sipariş verilerini hazırla
                    siparis_data = {
                        'tedarikci_id': tedarikci_id,
                        'otel_id': otel_id,
                        'urunler': urunler,
                        'tahmini_teslimat_tarihi': tahmini_teslimat_tarihi,
                        'aciklama': aciklama
                    }
                    
                    # Siparişi oluştur
                    sonuc = SatinAlmaServisi.siparis_olustur(siparis_data, session['kullanici_id'])
                    
                    if sonuc['success']:
                        flash(f"Sipariş başarıyla oluşturuldu. Sipariş No: {sonuc['siparis_no']}", 'success')
                        return redirect(url_for('siparis_listesi', otel_id=otel_id))
                    else:
                        flash(f"Sipariş oluşturulamadı: {sonuc['message']}", 'danger')
                        
                except ValueError as e:
                    flash(f'Geçersiz veri formatı: {str(e)}', 'danger')
                except Exception as e:
                    db.session.rollback()
                    log_hata(e, 'satin_alma_siparis')
                    flash(f'Sipariş oluşturulurken hata oluştu: {str(e)}', 'danger')
            
            # Aktif tedarikçileri getir
            tedarikciler = Tedarikci.query.filter_by(aktif=True).order_by(Tedarikci.tedarikci_adi).all()
            
            # Aktif ürünleri getir
            urunler_query = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            # Ürünleri JSON-serializable formata çevir
            urunler = []
            for urun in urunler_query:
                urunler.append({
                    'id': urun.id,
                    'urun_adi': urun.urun_adi,
                    'birim': urun.birim,
                    'grup_id': urun.grup_id,
                    'grup_adi': urun.grup.grup_adi if urun.grup else None
                })
            
            # Tedarikçi fiyatlarını hazırla (tedarikci_id -> urun_id -> fiyat)
            from models import UrunTedarikciFiyat
            tedarikci_fiyatlar = {}
            for tedarikci in tedarikciler:
                tedarikci_fiyatlar[tedarikci.id] = {}
                tedarikci_urunler = UrunTedarikciFiyat.query.filter_by(
                    tedarikci_id=tedarikci.id,
                    aktif=True
                ).all()
                for tu in tedarikci_urunler:
                    tedarikci_fiyatlar[tedarikci.id][tu.urun_id] = float(tu.birim_fiyat)
            
            # Otomatik sipariş önerilerini getir
            oneriler = []
            if secili_otel_id:
                try:
                    oneriler = SatinAlmaServisi.otomatik_siparis_onerisi_olustur(secili_otel_id)
                except Exception as e:
                    log_hata(e, 'otomatik_siparis_onerisi')
            
            return render_template('depo_sorumlusu/satin_alma_siparis.html',
                                 tedarikciler=tedarikciler,
                                 urunler=urunler,
                                 tedarikci_fiyatlar=tedarikci_fiyatlar,
                                 siparis_onerileri=oneriler,
                                 otel_secenekleri=otel_secenekleri,
                                 secili_otel_id=secili_otel_id)
                                 
        except Exception as e:
            log_hata(e, 'satin_alma_siparis')
            flash(f'Sayfa yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
    
    @app.route('/siparis-listesi')
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def siparis_listesi():
        """Sipariş listesi ve takip"""
        from utils.authorization import get_kullanici_otelleri, get_otel_filtreleme_secenekleri
        
        try:
            # Kullanıcının erişebileceği oteller
            kullanici_otelleri = get_kullanici_otelleri()
            otel_secenekleri = get_otel_filtreleme_secenekleri()
            
            # Seçili otel
            secili_otel_id = request.args.get('otel_id', type=int)
            durum_filtre = request.args.get('durum')
            
            # Siparişleri getir - Direkt query ile obje listesi
            query = SatinAlmaSiparisi.query.options(
                db.joinedload(SatinAlmaSiparisi.tedarikci),
                db.joinedload(SatinAlmaSiparisi.otel),
                db.joinedload(SatinAlmaSiparisi.olusturan)
            )
            
            if secili_otel_id:
                query = query.filter_by(otel_id=secili_otel_id)
            
            if durum_filtre:
                query = query.filter_by(durum=durum_filtre)
            
            siparisler = query.order_by(desc(SatinAlmaSiparisi.siparis_tarihi)).all()
            
            # Geciken siparişleri kontrol et
            geciken_siparisler = SatinAlmaServisi.geciken_siparisler_kontrol()
            geciken_ids = [s['siparis_id'] for s in geciken_siparisler]
            
            # İstatistikleri hesapla
            istatistikler = {
                'toplam': len(siparisler),
                'beklemede': sum(1 for s in siparisler if s.durum == 'beklemede'),
                'onaylandi': sum(1 for s in siparisler if s.durum == 'onaylandi'),
                'teslim_alindi': sum(1 for s in siparisler if s.durum == 'teslim_alindi'),
                'iptal': sum(1 for s in siparisler if s.durum == 'iptal'),
                'geciken': len(geciken_ids)
            }
            
            # Modal için gerekli veriler
            tedarikciler = Tedarikci.query.filter_by(aktif=True).order_by(Tedarikci.tedarikci_adi).all()
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            return render_template('depo_sorumlusu/siparis_listesi.html',
                                 siparisler=siparisler,
                                 geciken_ids=geciken_ids,
                                 istatistikler=istatistikler,
                                 otel_secenekleri=otel_secenekleri,
                                 secili_otel_id=secili_otel_id,
                                 durum_filtre=durum_filtre,
                                 tedarikciler=tedarikciler,
                                 urunler=urunler)
                                 
        except Exception as e:
            log_hata(e, 'siparis_listesi')
            flash(f'Sipariş listesi yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
    
    @app.route('/siparis-detay/<int:siparis_id>')
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def siparis_detay(siparis_id):
        """Sipariş detayları"""
        try:
            siparis = SatinAlmaSiparisi.query.get_or_404(siparis_id)
            
            # Yetki kontrolü - kullanıcı bu otele erişebilir mi?
            from utils.authorization import get_kullanici_otelleri
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [otel.id for otel in kullanici_otelleri]
            
            if session.get('rol') != 'sistem_yoneticisi' and siparis.otel_id not in otel_ids:
                flash('Bu siparişe erişim yetkiniz yok.', 'danger')
                return redirect(url_for('siparis_listesi'))
            
            # Sipariş detaylarını getir
            detaylar = SatinAlmaSiparisDetay.query.filter_by(siparis_id=siparis_id).all()
            
            # Tedarikçi iletişim kayıtlarını getir
            iletisim_kayitlari = TedarikciIletisim.query.filter_by(
                siparis_id=siparis_id
            ).order_by(TedarikciIletisim.iletisim_tarihi.desc()).all()
            
            # Tedarikçi dokümanlarını getir
            dokumanlar = TedarikciDokuman.query.filter_by(
                siparis_id=siparis_id
            ).order_by(TedarikciDokuman.yuklenme_tarihi.desc()).all()
            
            # İlgili satın alma işlemlerini getir
            from models import SatinAlmaIslem
            satin_alma_islemleri = SatinAlmaIslem.query.filter_by(
                siparis_id=siparis_id
            ).order_by(SatinAlmaIslem.islem_tarihi.desc()).all()
            
            # İlgili stok hareketlerini getir (sipariş numarasına göre)
            stok_hareketleri = StokHareket.query.filter(
                StokHareket.aciklama.like(f'%{siparis.siparis_no}%')
            ).order_by(StokHareket.islem_tarihi.desc()).all()
            
            return render_template('depo_sorumlusu/siparis_detay.html',
                                 siparis=siparis,
                                 detaylar=detaylar,
                                 iletisim_kayitlari=iletisim_kayitlari,
                                 dokumanlar=dokumanlar,
                                 satin_alma_islemleri=satin_alma_islemleri,
                                 stok_hareketleri=stok_hareketleri)
                                 
        except Exception as e:
            log_hata(e, 'siparis_detay')
            flash(f'Sipariş detayı yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('siparis_listesi'))
    
    @app.route('/siparis-durum-guncelle/<int:siparis_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def siparis_durum_guncelle(siparis_id):
        """Sipariş durum güncelleme"""
        try:
            yeni_durum = request.form.get('durum')
            
            if not yeni_durum:
                flash('Durum bilgisi eksik.', 'warning')
                return redirect(url_for('siparis_detay', siparis_id=siparis_id))
            
            # Durumu güncelle
            basarili = SatinAlmaServisi.siparis_durum_guncelle(
                siparis_id,
                yeni_durum,
                session['kullanici_id']
            )
            
            if basarili:
                flash('Sipariş durumu başarıyla güncellendi.', 'success')
                
                # Eğer durum "teslim_alindi" ise stok giriş sayfasına yönlendir
                if yeni_durum == 'teslim_alindi':
                    return redirect(url_for('siparis_stok_giris', siparis_id=siparis_id))
            else:
                flash('Sipariş durumu güncellenemedi.', 'danger')
                
        except Exception as e:
            log_hata(e, 'siparis_durum_guncelle')
            flash(f'Durum güncellenirken hata oluştu: {str(e)}', 'danger')
        
        return redirect(url_for('siparis_detay', siparis_id=siparis_id))

    # ==================== STOK GİRİŞ ENTEGRASYON ROUTE'LARI ====================
    
    @app.route('/siparis-stok-giris/<int:siparis_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def siparis_stok_giris(siparis_id):
        """Sipariş teslimatından stok girişi"""
        try:
            siparis = SatinAlmaSiparisi.query.get_or_404(siparis_id)
            
            # Yetki kontrolü
            from utils.authorization import get_kullanici_otelleri
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [otel.id for otel in kullanici_otelleri]
            
            if session.get('rol') != 'sistem_yoneticisi' and siparis.otel_id not in otel_ids:
                flash('Bu siparişe erişim yetkiniz yok.', 'danger')
                return redirect(url_for('siparis_listesi'))
            
            # Sipariş durumu kontrolü
            if siparis.durum not in ['onaylandi', 'teslim_alindi', 'kismi_teslim']:
                flash('Bu sipariş için stok girişi yapılamaz. Sipariş durumu uygun değil.', 'warning')
                return redirect(url_for('siparis_detay', siparis_id=siparis_id))
            
            if request.method == 'POST':
                try:
                    # Teslimat tarihini al
                    gerceklesen_teslimat_tarihi_str = request.form.get('gerceklesen_teslimat_tarihi')
                    if gerceklesen_teslimat_tarihi_str:
                        gerceklesen_teslimat_tarihi = datetime.strptime(
                            gerceklesen_teslimat_tarihi_str, '%Y-%m-%d'
                        ).date()
                    else:
                        gerceklesen_teslimat_tarihi = date.today()
                    
                    # Teslim alınan ürünleri al
                    urun_ids = request.form.getlist('urun_ids[]')
                    teslim_miktarlari = request.form.getlist('teslim_miktarlari[]')
                    
                    if not urun_ids:
                        flash('En az bir ürün için miktar girilmelidir.', 'warning')
                        return redirect(url_for('siparis_stok_giris', siparis_id=siparis_id))
                    
                    # Teslim alınan ürün listesini hazırla
                    teslim_alinan_urunler = []
                    for i in range(len(urun_ids)):
                        try:
                            miktar = int(teslim_miktarlari[i])
                            if miktar > 0:
                                teslim_alinan_urunler.append({
                                    'urun_id': int(urun_ids[i]),
                                    'miktar': miktar
                                })
                        except (ValueError, IndexError):
                            continue
                    
                    if not teslim_alinan_urunler:
                        flash('Geçerli bir teslimat miktarı girilmelidir.', 'warning')
                        return redirect(url_for('siparis_stok_giris', siparis_id=siparis_id))
                    
                    # Stok girişi oluştur
                    sonuc = SatinAlmaServisi.stok_giris_olustur(
                        siparis_id,
                        teslim_alinan_urunler,
                        session['kullanici_id']
                    )
                    
                    if sonuc['success']:
                        # Gerçekleşen teslimat tarihini güncelle
                        siparis.gerceklesen_teslimat_tarihi = gerceklesen_teslimat_tarihi
                        db.session.commit()
                        
                        flash(f"Stok girişi başarıyla tamamlandı. Sipariş durumu: {sonuc['siparis_durumu']}", 'success')
                        return redirect(url_for('siparis_detay', siparis_id=siparis_id))
                    else:
                        flash(f"Stok girişi başarısız: {sonuc['message']}", 'danger')
                        
                except ValueError as e:
                    flash(f'Geçersiz veri formatı: {str(e)}', 'danger')
                except Exception as e:
                    db.session.rollback()
                    log_hata(e, 'siparis_stok_giris')
                    flash(f'Stok girişi sırasında hata oluştu: {str(e)}', 'danger')
            
            # Sipariş detaylarını getir (otomatik form doldurma için)
            detaylar = SatinAlmaSiparisDetay.query.filter_by(siparis_id=siparis_id).all()
            
            # Her ürün için kalan miktar hesapla
            urun_bilgileri = []
            for detay in detaylar:
                kalan_miktar = detay.miktar - detay.teslim_alinan_miktar
                if kalan_miktar > 0:
                    urun_bilgileri.append({
                        'detay': detay,
                        'kalan_miktar': kalan_miktar
                    })
            
            return render_template('depo_sorumlusu/siparis_stok_giris.html',
                                 siparis=siparis,
                                 urun_bilgileri=urun_bilgileri)
                                 
        except Exception as e:
            log_hata(e, 'siparis_stok_giris')
            flash(f'Stok giriş sayfası yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('siparis_detay', siparis_id=siparis_id))

    # ==================== OTOMATİK SİPARİŞ ÖNERİLERİ ROUTE'LARI ====================
    
    @app.route('/otomatik-siparis-onerileri')
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def otomatik_siparis_onerileri():
        """Otomatik sipariş önerileri listesi"""
        from utils.authorization import get_kullanici_otelleri, get_otel_filtreleme_secenekleri
        
        try:
            # Kullanıcının erişebileceği oteller
            kullanici_otelleri = get_kullanici_otelleri()
            otel_secenekleri = get_otel_filtreleme_secenekleri()
            
            # Seçili otel
            secili_otel_id = request.args.get('otel_id', type=int)
            if not secili_otel_id and kullanici_otelleri:
                secili_otel_id = kullanici_otelleri[0].id
            
            # Otomatik sipariş önerilerini getir
            oneriler = []
            if secili_otel_id:
                try:
                    oneriler = SatinAlmaServisi.otomatik_siparis_onerisi_olustur(secili_otel_id)
                except Exception as e:
                    log_hata(e, 'otomatik_siparis_onerileri')
                    flash(f'Öneriler oluşturulurken hata oluştu: {str(e)}', 'warning')
            
            # İstatistikleri hesapla
            istatistikler = {
                'kritik': sum(1 for o in oneriler if o.get('oncelik') == 'kritik'),
                'dikkat': sum(1 for o in oneriler if o.get('oncelik') == 'dikkat'),
                'toplam': len(oneriler)
            }
            
            return render_template('depo_sorumlusu/otomatik_siparis_onerileri.html',
                                 oneriler=oneriler,
                                 otel_secenekleri=otel_secenekleri,
                                 secili_otel_id=secili_otel_id,
                                 istatistikler=istatistikler)
                                 
        except Exception as e:
            log_hata(e, 'otomatik_siparis_onerileri')
            flash(f'Sayfa yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
    
    @app.route('/siparis-onerisi-onayla', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def siparis_onerisi_onayla():
        """Sipariş önerisini onaylayarak sipariş oluştur"""
        try:
            # Form verilerini al
            otel_id = int(request.form['otel_id'])
            tedarikci_id = int(request.form['tedarikci_id'])
            tahmini_teslimat_tarihi_str = request.form['tahmini_teslimat_tarihi']
            aciklama = request.form.get('aciklama', 'Otomatik sipariş önerisi')
            
            # Tarih dönüşümü
            tahmini_teslimat_tarihi = datetime.strptime(tahmini_teslimat_tarihi_str, '%Y-%m-%d').date()
            
            # Ürün listesini al
            urun_ids = request.form.getlist('urun_ids[]')
            miktarlar = request.form.getlist('miktarlar[]')
            birim_fiyatlar = request.form.getlist('birim_fiyatlar[]')
            
            if not urun_ids:
                return jsonify({
                    'success': False,
                    'message': 'En az bir ürün seçmelisiniz.'
                }), 400
            
            # Ürün listesini hazırla
            urunler = []
            for i in range(len(urun_ids)):
                try:
                    urunler.append({
                        'urun_id': int(urun_ids[i]),
                        'miktar': int(miktarlar[i]),
                        'birim_fiyat': float(birim_fiyatlar[i])
                    })
                except (ValueError, IndexError) as e:
                    return jsonify({
                        'success': False,
                        'message': f'Ürün bilgilerinde hata: {str(e)}'
                    }), 400
            
            # Sipariş verilerini hazırla
            siparis_data = {
                'tedarikci_id': tedarikci_id,
                'otel_id': otel_id,
                'urunler': urunler,
                'tahmini_teslimat_tarihi': tahmini_teslimat_tarihi,
                'aciklama': aciklama
            }
            
            # Siparişi oluştur
            sonuc = SatinAlmaServisi.siparis_olustur(siparis_data, session['kullanici_id'])
            
            if sonuc['success']:
                return jsonify({
                    'success': True,
                    'message': f"Sipariş başarıyla oluşturuldu. Sipariş No: {sonuc['siparis_no']}",
                    'siparis_id': sonuc['siparis_id'],
                    'siparis_no': sonuc['siparis_no']
                })
            else:
                return jsonify({
                    'success': False,
                    'message': sonuc['message']
                }), 400
                
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': f'Geçersiz veri formatı: {str(e)}'
            }), 400
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'siparis_onerisi_onayla')
            return jsonify({
                'success': False,
                'message': f'Sipariş oluşturulurken hata oluştu: {str(e)}'
            }), 500

    # ==================== TEDARİKÇİ İLETİŞİM VE BELGE YÖNETİMİ ROUTE'LARI ====================
    
    @app.route('/tedarikci-iletisim/<int:tedarikci_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def tedarikci_iletisim(tedarikci_id):
        """Tedarikçi iletişim kayıtları"""
        try:
            tedarikci = Tedarikci.query.get_or_404(tedarikci_id)
            
            if request.method == 'POST':
                try:
                    # Form verilerini al
                    siparis_id = request.form.get('siparis_id')
                    konu = request.form['konu']
                    aciklama = request.form['aciklama']
                    iletisim_tarihi_str = request.form.get('iletisim_tarihi')
                    
                    # Tarih dönüşümü
                    if iletisim_tarihi_str:
                        iletisim_tarihi = datetime.strptime(iletisim_tarihi_str, '%Y-%m-%dT%H:%M')
                    else:
                        iletisim_tarihi = datetime.now()
                    
                    # İletişim kaydı oluştur
                    iletisim = TedarikciIletisim(
                        tedarikci_id=tedarikci_id,
                        siparis_id=int(siparis_id) if siparis_id else None,
                        iletisim_tarihi=iletisim_tarihi,
                        konu=konu,
                        aciklama=aciklama,
                        kullanici_id=session['kullanici_id']
                    )
                    
                    db.session.add(iletisim)
                    db.session.commit()
                    
                    # Audit Trail
                    audit_create('tedarikci_iletisim', iletisim.id, iletisim)
                    
                    # Log kaydı
                    log_islem('ekleme', 'tedarikci_iletisim', {
                        'tedarikci_id': tedarikci_id,
                        'tedarikci_adi': tedarikci.tedarikci_adi,
                        'konu': konu
                    })
                    
                    flash('İletişim kaydı başarıyla eklendi.', 'success')
                    return redirect(url_for('tedarikci_iletisim', tedarikci_id=tedarikci_id))
                    
                except Exception as e:
                    db.session.rollback()
                    log_hata(e, 'tedarikci_iletisim')
                    flash(f'İletişim kaydı eklenirken hata oluştu: {str(e)}', 'danger')
            
            # İletişim kayıtlarını getir
            iletisim_kayitlari = TedarikciIletisim.query.filter_by(
                tedarikci_id=tedarikci_id
            ).order_by(TedarikciIletisim.iletisim_tarihi.desc()).all()
            
            # Tedarikçinin siparişlerini getir (iletişim kaydı için)
            siparisler = SatinAlmaSiparisi.query.filter_by(
                tedarikci_id=tedarikci_id
            ).order_by(SatinAlmaSiparisi.siparis_tarihi.desc()).all()
            
            # Tedarikçi dokümanlarını getir
            dokumanlar = TedarikciDokuman.query.filter_by(
                tedarikci_id=tedarikci_id
            ).order_by(TedarikciDokuman.yuklenme_tarihi.desc()).all()
            
            return render_template('depo_sorumlusu/tedarikci_iletisim.html',
                                 tedarikci=tedarikci,
                                 iletisim_kayitlari=iletisim_kayitlari,
                                 siparisler=siparisler,
                                 dokumanlar=dokumanlar)
                                 
        except Exception as e:
            log_hata(e, 'tedarikci_iletisim')
            flash(f'Sayfa yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
    
    @app.route('/tedarikci-dokuman-yukle', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def tedarikci_dokuman_yukle():
        """Tedarikçi belge yükleme"""
        try:
            # Form verilerini al
            tedarikci_id = int(request.form['tedarikci_id'])
            siparis_id = request.form.get('siparis_id')
            dokuman_tipi = request.form['dokuman_tipi']
            
            # Dosya kontrolü
            if 'dosya' not in request.files:
                return jsonify({
                    'success': False,
                    'message': 'Dosya seçilmedi.'
                }), 400
            
            dosya = request.files['dosya']
            
            if dosya.filename == '':
                return jsonify({
                    'success': False,
                    'message': 'Dosya seçilmedi.'
                }), 400
            
            # Dosya uzantısı kontrolü
            ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'jpg', 'jpeg', 'png', 'doc', 'docx'}
            
            def allowed_file(filename):
                return '.' in filename and \
                       filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
            
            if not allowed_file(dosya.filename):
                return jsonify({
                    'success': False,
                    'message': 'Geçersiz dosya formatı. İzin verilen formatlar: PDF, Excel, Word, Resim'
                }), 400
            
            # Dosya boyutu kontrolü (10 MB)
            MAX_FILE_SIZE = 10 * 1024 * 1024
            dosya.seek(0, os.SEEK_END)
            dosya_boyutu = dosya.tell()
            
            if dosya_boyutu > MAX_FILE_SIZE:
                return jsonify({
                    'success': False,
                    'message': 'Dosya boyutu çok büyük. Maksimum 10 MB olmalıdır.'
                }), 400
            
            dosya.seek(0)
            
            # Güvenli dosya adı oluştur
            filename = secure_filename(dosya.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{tedarikci_id}_{timestamp}_{filename}"
            
            # Yükleme klasörünü oluştur
            upload_folder = os.path.join('uploads', 'tedarikci_dokumanlar')
            os.makedirs(upload_folder, exist_ok=True)
            
            # Dosyayı kaydet
            dosya_yolu = os.path.join(upload_folder, unique_filename)
            dosya.save(dosya_yolu)
            
            # Veritabanına kaydet
            dokuman = TedarikciDokuman(
                tedarikci_id=tedarikci_id,
                siparis_id=int(siparis_id) if siparis_id else None,
                dokuman_tipi=dokuman_tipi,
                dosya_adi=filename,
                dosya_yolu=dosya_yolu,
                dosya_boyutu=dosya_boyutu,
                yuklenme_tarihi=datetime.now(),
                yuklenen_kullanici_id=session['kullanici_id']
            )
            
            db.session.add(dokuman)
            db.session.commit()
            
            # Audit Trail
            audit_create('tedarikci_dokuman', dokuman.id, dokuman)
            
            # Log kaydı
            tedarikci = Tedarikci.query.get(tedarikci_id)
            log_islem('ekleme', 'tedarikci_dokuman', {
                'tedarikci_id': tedarikci_id,
                'tedarikci_adi': tedarikci.tedarikci_adi if tedarikci else 'Bilinmeyen',
                'dosya_adi': filename,
                'dokuman_tipi': dokuman_tipi
            })
            
            return jsonify({
                'success': True,
                'message': 'Belge başarıyla yüklendi.',
                'dokuman_id': dokuman.id
            })
            
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': f'Geçersiz veri formatı: {str(e)}'
            }), 400
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'tedarikci_dokuman_yukle')
            return jsonify({
                'success': False,
                'message': f'Belge yüklenirken hata oluştu: {str(e)}'
            }), 500
    
    @app.route('/tedarikci-dokuman-indir/<int:dokuman_id>')
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def tedarikci_dokuman_indir(dokuman_id):
        """Tedarikçi belge indirme"""
        try:
            dokuman = TedarikciDokuman.query.get_or_404(dokuman_id)
            
            # Dosya varlığını kontrol et
            if not os.path.exists(dokuman.dosya_yolu):
                flash('Dosya bulunamadı.', 'danger')
                return redirect(url_for('tedarikci_iletisim', tedarikci_id=dokuman.tedarikci_id))
            
            # Log kaydı
            log_islem('indirme', 'tedarikci_dokuman', {
                'dokuman_id': dokuman_id,
                'dosya_adi': dokuman.dosya_adi,
                'tedarikci_id': dokuman.tedarikci_id
            })
            
            return send_file(
                dokuman.dosya_yolu,
                as_attachment=True,
                download_name=dokuman.dosya_adi
            )
            
        except Exception as e:
            log_hata(e, 'tedarikci_dokuman_indir')
            flash(f'Dosya indirilirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))

    # ==================== DİREKT SATIN ALMA İŞLEMLERİ ROUTE'LARI ====================
    
    @app.route('/satin-alma', methods=['GET', 'POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def satin_alma():
        """Direkt satın alma işlemi - Redirect to list page with modal"""
        # Satın alma listesi sayfasına yönlendir (modal sistemi orada)
        if request.method == 'GET':
            return redirect(url_for('satin_alma_listesi'))
        
        # POST işlemi için devam et
        from utils.authorization import get_kullanici_otelleri, get_otel_filtreleme_secenekleri
        
        try:
            # Kullanıcının erişebileceği oteller
            kullanici_otelleri = get_kullanici_otelleri()
            otel_secenekleri = get_otel_filtreleme_secenekleri()
            
            # Seçili otel
            secili_otel_id = request.args.get('otel_id', type=int)
            if not secili_otel_id and kullanici_otelleri:
                secili_otel_id = kullanici_otelleri[0].id
            
            if request.method == 'POST':
                try:
                    # Form verilerini al
                    tedarikci_id = int(request.form['tedarikci_id'])
                    otel_id = int(request.form['otel_id'])
                    satin_alma_tarihi_str = request.form.get('satin_alma_tarihi')
                    fatura_no = request.form.get('fatura_no', '')
                    fatura_tarihi_str = request.form.get('fatura_tarihi')
                    aciklama = request.form.get('aciklama', '')
                    
                    # Tarih dönüşümleri
                    satin_alma_tarihi = datetime.now()
                    if satin_alma_tarihi_str:
                        satin_alma_tarihi = datetime.strptime(satin_alma_tarihi_str, '%Y-%m-%d')
                    
                    fatura_tarihi = None
                    if fatura_tarihi_str:
                        fatura_tarihi = datetime.strptime(fatura_tarihi_str, '%Y-%m-%d').date()
                    
                    # Ürün listesini al
                    urun_ids = request.form.getlist('urun_ids[]')
                    miktarlar = request.form.getlist('miktarlar[]')
                    birim_fiyatlar = request.form.getlist('birim_fiyatlar[]')
                    kdv_oranlari = request.form.getlist('kdv_oranlari[]')
                    
                    if not urun_ids:
                        flash('En az bir ürün eklemelisiniz.', 'warning')
                        return redirect(url_for('satin_alma', otel_id=otel_id))
                    
                    # İşlem numarası oluştur
                    from datetime import datetime
                    islem_no = f"SA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    # Satın alma işlemi oluştur
                    satin_alma_islem = SatinAlmaIslem(
                        islem_no=islem_no,
                        tedarikci_id=tedarikci_id,
                        otel_id=otel_id,
                        islem_tarihi=satin_alma_tarihi,
                        fatura_no=fatura_no,
                        fatura_tarihi=fatura_tarihi,
                        odeme_sekli=odeme_sekli,
                        odeme_durumu=odeme_durumu,
                        aciklama=aciklama,
                        olusturan_id=session['kullanici_id']
                    )
                    
                    db.session.add(satin_alma_islem)
                    db.session.flush()  # ID'yi almak için
                    
                    # Toplam tutarları hesapla
                    toplam_tutar = 0
                    toplam_kdv = 0
                    
                    # Ürün detaylarını ekle ve stok girişi yap
                    for i in range(len(urun_ids)):
                        try:
                            urun_id = int(urun_ids[i])
                            miktar = int(miktarlar[i])
                            birim_fiyat = float(birim_fiyatlar[i])
                            kdv_orani = float(kdv_oranlari[i]) if i < len(kdv_oranlari) else 0
                            
                            # Hesaplamalar
                            ara_toplam = miktar * birim_fiyat
                            kdv_tutari = ara_toplam * (kdv_orani / 100)
                            toplam_fiyat = ara_toplam + kdv_tutari
                            
                            toplam_tutar += ara_toplam
                            toplam_kdv += kdv_tutari
                            
                            # Stok hareketi oluştur
                            stok_hareket = StokHareket(
                                urun_id=urun_id,
                                hareket_tipi='giris',
                                miktar=miktar,
                                aciklama=f'Satın alma - {islem_no} - Fatura: {fatura_no}',
                                islem_yapan_id=session['kullanici_id']
                            )
                            db.session.add(stok_hareket)
                            db.session.flush()
                            
                            # Satın alma detayı oluştur
                            detay = SatinAlmaIslemDetay(
                                islem_id=satin_alma_islem.id,
                                urun_id=urun_id,
                                miktar=miktar,
                                birim_fiyat=birim_fiyat,
                                kdv_orani=kdv_orani,
                                kdv_tutari=kdv_tutari,
                                toplam_fiyat=toplam_fiyat,
                                stok_hareket_id=stok_hareket.id
                            )
                            db.session.add(detay)
                            
                        except (ValueError, IndexError) as e:
                            flash(f'Ürün bilgilerinde hata: {str(e)}', 'danger')
                            db.session.rollback()
                            return redirect(url_for('satin_alma', otel_id=otel_id))
                    
                    # Toplam tutarları güncelle
                    satin_alma_islem.toplam_tutar = toplam_tutar
                    satin_alma_islem.kdv_tutari = toplam_kdv
                    satin_alma_islem.genel_toplam = toplam_tutar + toplam_kdv
                    
                    db.session.commit()
                    
                    # Audit Trail
                    audit_create('satin_alma_islem', satin_alma_islem.id, satin_alma_islem)
                    
                    # Log kaydı
                    log_islem('ekleme', 'satin_alma', {
                        'islem_no': islem_no,
                        'tedarikci_id': tedarikci_id,
                        'otel_id': otel_id,
                        'urun_sayisi': len(urun_ids),
                        'toplam_tutar': float(toplam_tutar + toplam_kdv)
                    })
                    
                    flash(f'Satın alma işlemi başarıyla kaydedildi. İşlem No: {islem_no}', 'success')
                    return redirect(url_for('satin_alma_listesi', otel_id=otel_id))
                    
                except ValueError as e:
                    flash(f'Geçersiz veri formatı: {str(e)}', 'danger')
                except Exception as e:
                    db.session.rollback()
                    log_hata(e, 'satin_alma')
                    flash(f'Satın alma işlemi sırasında hata oluştu: {str(e)}', 'danger')
            
            # Aktif tedarikçileri getir
            tedarikciler = Tedarikci.query.filter_by(aktif=True).order_by(Tedarikci.tedarikci_adi).all()
            
            # Aktif ürünleri getir
            urunler_query = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            # Ürünleri JSON-serializable formata çevir
            urunler = []
            for urun in urunler_query:
                urunler.append({
                    'id': urun.id,
                    'urun_adi': urun.urun_adi,
                    'birim': urun.birim,
                    'grup_id': urun.grup_id,
                    'grup_adi': urun.grup.grup_adi if urun.grup else None
                })
            
            # Tedarikçi fiyatlarını hazırla
            from models import UrunTedarikciFiyat
            tedarikci_fiyatlar = {}
            for tedarikci in tedarikciler:
                tedarikci_fiyatlar[tedarikci.id] = {}
                tedarikci_urunler = UrunTedarikciFiyat.query.filter_by(
                    tedarikci_id=tedarikci.id,
                    aktif=True
                ).all()
                for tu in tedarikci_urunler:
                    tedarikci_fiyatlar[tedarikci.id][tu.urun_id] = float(tu.birim_fiyat)
            
            return render_template('depo_sorumlusu/satin_alma.html',
                                 tedarikciler=tedarikciler,
                                 urunler=urunler,
                                 tedarikci_fiyatlar=tedarikci_fiyatlar,
                                 otel_secenekleri=otel_secenekleri,
                                 secili_otel_id=secili_otel_id)
                                 
        except Exception as e:
            log_hata(e, 'satin_alma')
            flash(f'Sayfa yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
    
    @app.route('/satin-alma-listesi')
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def satin_alma_listesi():
        """Satın alma işlemleri listesi"""
        from utils.authorization import get_kullanici_otelleri, get_otel_filtreleme_secenekleri
        
        try:
            # Kullanıcının erişebileceği oteller
            kullanici_otelleri = get_kullanici_otelleri()
            otel_secenekleri = get_otel_filtreleme_secenekleri()
            
            # Seçili otel
            secili_otel_id = request.args.get('otel_id', type=int)
            
            # Satın alma işlemlerini getir
            query = SatinAlmaIslem.query.options(
                db.joinedload(SatinAlmaIslem.tedarikci),
                db.joinedload(SatinAlmaIslem.otel),
                db.joinedload(SatinAlmaIslem.olusturan)
            )
            
            if secili_otel_id:
                query = query.filter_by(otel_id=secili_otel_id)
            
            islemler = query.order_by(SatinAlmaIslem.islem_tarihi.desc()).limit(100).all()
            
            # İstatistikleri hesapla
            istatistikler = {
                'toplam': len(islemler),
                'bu_ay': sum(1 for i in islemler if i.islem_tarihi.month == datetime.now().month),
                'toplam_tutar': sum(float(i.genel_toplam) for i in islemler)
            }
            
            # Modal için gerekli veriler
            tedarikciler = Tedarikci.query.filter_by(aktif=True).order_by(Tedarikci.tedarikci_adi).all()
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            return render_template('depo_sorumlusu/satin_alma_listesi.html',
                                 islemler=islemler,
                                 istatistikler=istatistikler,
                                 otel_secenekleri=otel_secenekleri,
                                 secili_otel_id=secili_otel_id,
                                 tedarikciler=tedarikciler,
                                 urunler=urunler)
                                 
        except Exception as e:
            log_hata(e, 'satin_alma_listesi')
            flash(f'Satın alma listesi yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
    
    @app.route('/satin-alma-detay/<int:islem_id>')
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def satin_alma_detay(islem_id):
        """Satın alma işlem detayları"""
        try:
            islem = SatinAlmaIslem.query.get_or_404(islem_id)
            
            # Yetki kontrolü
            from utils.authorization import get_kullanici_otelleri
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [otel.id for otel in kullanici_otelleri]
            
            if session.get('rol') != 'sistem_yoneticisi' and islem.otel_id not in otel_ids:
                flash('Bu işleme erişim yetkiniz yok.', 'danger')
                return redirect(url_for('satin_alma_listesi'))
            
            # İşlem detaylarını getir
            detaylar = SatinAlmaIslemDetay.query.filter_by(islem_id=islem_id).all()
            
            return render_template('depo_sorumlusu/satin_alma_detay.html',
                                 islem=islem,
                                 detaylar=detaylar)
                                 
        except Exception as e:
            log_hata(e, 'satin_alma_detay')
            flash(f'Satın alma detayı yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('satin_alma_listesi'))

    
    @app.route('/satin-alma-excel', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def     satin_alma_excel():
        """Excel ile toplu satın alma işlemi"""
        try:
            # Form verilerini al
            tedarikci_id = int(request.form['tedarikci_id'])
            otel_id = int(request.form['otel_id'])
            
            # Excel dosyasını kontrol et
            if 'excel_file' not in request.files:
                flash('Excel dosyası seçilmedi.', 'warning')
                return redirect(url_for('satin_alma', otel_id=otel_id))
            
            excel_file = request.files['excel_file']
            
            if excel_file.filename == '':
                flash('Excel dosyası seçilmedi.', 'warning')
                return redirect(url_for('satin_alma', otel_id=otel_id))
            
            # Dosya uzantısı kontrolü
            if not excel_file.filename.lower().endswith(('.xlsx', '.xls')):
                flash('Geçersiz dosya formatı. Sadece Excel dosyaları (.xlsx, .xls) kabul edilir.', 'danger')
                return redirect(url_for('satin_alma', otel_id=otel_id))
            
            # Excel dosyasını işle
            import pandas as pd
            from io import BytesIO
            
            try:
                # Excel dosyasını oku
                df = pd.read_excel(BytesIO(excel_file.read()))
                
                # Gerekli sütunları kontrol et
                required_columns = ['urun_adi', 'satin_alinan_miktar', 'birim_fiyat']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    flash(f'Excel dosyasında eksik sütunlar: {", ".join(missing_columns)}', 'danger')
                    return redirect(url_for('satin_alma', otel_id=otel_id))
                
                # Boş satırları temizle
                df = df.dropna(subset=['urun_adi', 'satin_alinan_miktar'])
                
                if len(df) == 0:
                    flash('Excel dosyasında geçerli ürün bulunamadı.', 'warning')
                    return redirect(url_for('satin_alma', otel_id=otel_id))
                
                # İşlem numarası oluştur
                islem_no = f"SA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Satın alma işlemi oluştur
                satin_alma_islem = SatinAlmaIslem(
                    islem_no=islem_no,
                    tedarikci_id=tedarikci_id,
                    otel_id=otel_id,
                    aciklama=f'Excel ile toplu satın alma - {excel_file.filename}',
                    olusturan_id=session['kullanici_id']
                )
                
                db.session.add(satin_alma_islem)
                db.session.flush()
                
                # Toplam tutarları hesapla
                toplam_tutar = 0
                toplam_kdv = 0
                basarili_sayisi = 0
                hatali_satirlar = []
                
                # Her satırı işle
                for index, row in df.iterrows():
                    try:
                        urun_adi = str(row['urun_adi']).strip()
                        miktar = int(row['satin_alinan_miktar'])
                        birim_fiyat = float(row['birim_fiyat'])
                        kdv_orani = float(row.get('kdv_orani', 18))
                        
                        # Miktar kontrolü
                        if miktar <= 0:
                            hatali_satirlar.append(f"Satır {index + 2}: Satın alınan miktar 0 veya boş")
                            continue
                        
                        # Ürünü bul (ürün adına göre)
                        urun = Urun.query.filter_by(urun_adi=urun_adi, aktif=True).first()
                        
                        if not urun:
                            hatali_satirlar.append(f"Satır {index + 2}: Ürün '{urun_adi}' bulunamadı")
                            continue
                        
                        # Hesaplamalar
                        ara_toplam = miktar * birim_fiyat
                        kdv_tutari = ara_toplam * (kdv_orani / 100)
                        toplam_fiyat = ara_toplam + kdv_tutari
                        
                        toplam_tutar += ara_toplam
                        toplam_kdv += kdv_tutari
                        
                        # Stok hareketi oluştur
                        stok_hareket = StokHareket(
                            urun_id=urun.id,
                            hareket_tipi='giris',
                            miktar=miktar,
                            aciklama=f'Excel ile satın alma - {islem_no}',
                            islem_yapan_id=session['kullanici_id']
                        )
                        db.session.add(stok_hareket)
                        db.session.flush()
                        
                        # Satın alma detayı oluştur
                        detay = SatinAlmaIslemDetay(
                            islem_id=satin_alma_islem.id,
                            urun_id=urun.id,
                            miktar=miktar,
                            birim_fiyat=birim_fiyat,
                            kdv_orani=kdv_orani,
                            kdv_tutari=kdv_tutari,
                            toplam_fiyat=toplam_fiyat,
                            stok_hareket_id=stok_hareket.id
                        )
                        db.session.add(detay)
                        basarili_sayisi += 1
                        
                    except Exception as e:
                        hatali_satirlar.append(f"Satır {index + 2}: {str(e)}")
                        continue
                
                if basarili_sayisi == 0:
                    db.session.rollback()
                    flash('Excel dosyasında işlenebilir ürün bulunamadı.', 'danger')
                    if hatali_satirlar:
                        for hata in hatali_satirlar[:5]:  # İlk 5 hatayı göster
                            flash(hata, 'warning')
                    return redirect(url_for('satin_alma', otel_id=otel_id))
                
                # Toplam tutarları güncelle
                satin_alma_islem.toplam_tutar = toplam_tutar
                satin_alma_islem.kdv_tutari = toplam_kdv
                satin_alma_islem.genel_toplam = toplam_tutar + toplam_kdv
                
                db.session.commit()
                
                # Audit Trail
                audit_create('satin_alma_islem', satin_alma_islem.id, satin_alma_islem)
                
                # Log kaydı
                log_islem('ekleme', 'satin_alma_excel', {
                    'islem_no': islem_no,
                    'tedarikci_id': tedarikci_id,
                    'otel_id': otel_id,
                    'basarili_sayisi': basarili_sayisi,
                    'hatali_sayisi': len(hatali_satirlar),
                    'toplam_tutar': float(toplam_tutar + toplam_kdv)
                })
                
                flash(f'Excel ile satın alma işlemi başarıyla kaydedildi. İşlem No: {islem_no}', 'success')
                flash(f'{basarili_sayisi} ürün başarıyla işlendi.', 'success')
                
                if hatali_satirlar:
                    flash(f'{len(hatali_satirlar)} satırda hata oluştu.', 'warning')
                
                return redirect(url_for('satin_alma_detay', islem_id=satin_alma_islem.id))
                
            except Exception as e:
                db.session.rollback()
                log_hata(e, 'satin_alma_excel_parse')
                flash(f'Excel dosyası işlenirken hata oluştu: {str(e)}', 'danger')
                return redirect(url_for('satin_alma', otel_id=otel_id))
                
        except ValueError as e:
            flash(f'Geçersiz veri formatı: {str(e)}', 'danger')
            return redirect(url_for('satin_alma'))
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'satin_alma_excel')
            flash(f'Excel ile satın alma işlemi sırasında hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('satin_alma'))

    
    @app.route('/siparis-excel-export/<int:siparis_id>')
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def siparis_excel_export(siparis_id):
        """Siparişi Excel formatında indir (Satın alma için)"""
        try:
            siparis = SatinAlmaSiparisi.query.get_or_404(siparis_id)
            
            # Yetki kontrolü
            from utils.authorization import get_kullanici_otelleri
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [otel.id for otel in kullanici_otelleri]
            
            if session.get('rol') != 'sistem_yoneticisi' and siparis.otel_id not in otel_ids:
                flash('Bu siparişe erişim yetkiniz yok.', 'danger')
                return redirect(url_for('siparis_listesi'))
            
            # Sipariş detaylarını al
            detaylar = SatinAlmaSiparisDetay.query.filter_by(siparis_id=siparis_id).all()
            
            # Excel için veri hazırla
            import pandas as pd
            from io import BytesIO
            
            data = []
            for detay in detaylar:
                data.append({
                    'urun_adi': detay.urun.urun_adi,
                    'birim': detay.urun.birim,
                    'siparis_miktari': detay.miktar,
                    'teslim_alinan': detay.teslim_alinan_miktar,
                    'kalan_miktar': detay.miktar - detay.teslim_alinan_miktar,
                    'satin_alinan_miktar': '',  # Kullanıcı dolduracak
                    'birim_fiyat': '',  # Kullanıcı dolduracak
                    'kdv_orani': 18
                })
            
            df = pd.DataFrame(data)
            
            # Excel dosyası oluştur
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Satın Alma', index=False)
                
                # Worksheet'i al ve düzenle
                worksheet = writer.sheets['Satın Alma']
                
                # Sütun genişlikleri
                worksheet.column_dimensions['A'].width = 30  # urun_adi
                worksheet.column_dimensions['B'].width = 12  # birim
                worksheet.column_dimensions['C'].width = 15  # siparis_miktari
                worksheet.column_dimensions['D'].width = 15  # teslim_alinan
                worksheet.column_dimensions['E'].width = 15  # kalan_miktar
                worksheet.column_dimensions['F'].width = 18  # satin_alinan_miktar
                worksheet.column_dimensions['G'].width = 15  # birim_fiyat
                worksheet.column_dimensions['H'].width = 12  # kdv_orani
                
                # Başlık stili
                from openpyxl.styles import Font, PatternFill, Alignment
                
                header_font = Font(bold=True, color='FFFFFF')
                header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
                header_alignment = Alignment(horizontal='center', vertical='center')
                
                for cell in worksheet[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment
                
                # Bilgi sayfası ekle
                info_data = {
                    'Bilgi': ['Sipariş No', 'Tedarikçi', 'Sipariş Tarihi', 'Otel'],
                    'Değer': [
                        siparis.siparis_no,
                        siparis.tedarikci.tedarikci_adi if siparis.tedarikci else 'Belirtilmemiş',
                        siparis.siparis_tarihi.strftime('%d.%m.%Y'),
                        siparis.otel.ad
                    ]
                }
                info_df = pd.DataFrame(info_data)
                info_df.to_excel(writer, sheet_name='Sipariş Bilgileri', index=False)
                
                info_sheet = writer.sheets['Sipariş Bilgileri']
                info_sheet.column_dimensions['A'].width = 20
                info_sheet.column_dimensions['B'].width = 40
                
                for cell in info_sheet[1]:
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment
            
            output.seek(0)
            
            # Log kaydı
            log_islem('export', 'siparis_excel', {
                'siparis_id': siparis_id,
                'siparis_no': siparis.siparis_no
            })
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'siparis_{siparis.siparis_no}_satin_alma.xlsx'
            )
            
        except Exception as e:
            log_hata(e, 'siparis_excel_export')
            flash(f'Excel dosyası oluşturulurken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('siparis_detay', siparis_id=siparis_id))
    
    
    # ==================== SATIN ALMA GİRİŞİ ROUTE'LARI ====================
    
    @app.route('/satin-alma-giris/<int:siparis_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def satin_alma_giris(siparis_id):
        """Onaylanan sipariş için satın alma girişi - Aşama 1: Tarih ve Tedarikçi"""
        try:
            siparis = SatinAlmaSiparisi.query.get_or_404(siparis_id)
            
            # Yetki kontrolü
            from utils.authorization import get_kullanici_otelleri
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [otel.id for otel in kullanici_otelleri]
            
            if session.get('rol') not in ['sistem_yoneticisi', 'admin'] and siparis.otel_id not in otel_ids:
                flash('Bu siparişe erişim yetkiniz yok.', 'danger')
                return redirect(url_for('siparis_listesi'))
            
            # Sadece onaylanmış siparişler için satın alma girişi yapılabilir
            if siparis.durum != 'onaylandi':
                flash('Sadece onaylanmış siparişler için satın alma girişi yapılabilir.', 'warning')
                return redirect(url_for('siparis_detay', siparis_id=siparis_id))
            
            if request.method == 'POST':
                try:
                    # Form verilerini al
                    islem_tarihi_str = request.form.get('islem_tarihi')
                    tedarikci_id = request.form.get('tedarikci_id', type=int)
                    
                    if not islem_tarihi_str:
                        flash('İşlem tarihi zorunludur.', 'warning')
                        return redirect(url_for('satin_alma_giris', siparis_id=siparis_id))
                    
                    if not tedarikci_id:
                        flash('Tedarikçi seçimi zorunludur.', 'warning')
                        return redirect(url_for('satin_alma_giris', siparis_id=siparis_id))
                    
                    # Tarihi parse et
                    islem_tarihi = datetime.strptime(islem_tarihi_str, '%Y-%m-%d').date()
                    
                    # Session'a kaydet ve ürün fiyat girişi sayfasına yönlendir
                    return redirect(url_for('satin_alma_urun_giris', 
                                          siparis_id=siparis_id,
                                          tedarikci_id=tedarikci_id,
                                          islem_tarihi=islem_tarihi.strftime('%Y-%m-%d')))
                    
                except Exception as e:
                    log_hata(e, 'satin_alma_giris_post')
                    flash(f'Hata oluştu: {str(e)}', 'danger')
            
            # Aktif tedarikçileri getir
            tedarikciler = Tedarikci.query.filter_by(aktif=True).order_by(Tedarikci.tedarikci_adi).all()
            
            # Sipariş detaylarını getir
            detaylar = SatinAlmaSiparisDetay.query.filter_by(siparis_id=siparis_id).all()
            
            return render_template('depo_sorumlusu/satin_alma_giris.html',
                                 siparis=siparis,
                                 detaylar=detaylar,
                                 tedarikciler=tedarikciler)
                                 
        except Exception as e:
            log_hata(e, 'satin_alma_giris')
            flash(f'Sayfa yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('siparis_listesi'))
    
    
    @app.route('/satin-alma-urun-giris/<int:siparis_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def satin_alma_urun_giris(siparis_id):
        """Satın alma girişi - Aşama 2: Ürün fiyatları ve işlem tamamlama"""
        try:
            siparis = SatinAlmaSiparisi.query.get_or_404(siparis_id)
            
            # Yetki kontrolü
            from utils.authorization import get_kullanici_otelleri
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [otel.id for otel in kullanici_otelleri]
            
            if session.get('rol') not in ['sistem_yoneticisi', 'admin'] and siparis.otel_id not in otel_ids:
                flash('Bu siparişe erişim yetkiniz yok.', 'danger')
                return redirect(url_for('siparis_listesi'))
            
            # Query parametrelerinden bilgileri al
            tedarikci_id = request.args.get('tedarikci_id', type=int)
            islem_tarihi_str = request.args.get('islem_tarihi')
            
            if not tedarikci_id or not islem_tarihi_str:
                flash('Eksik bilgi. Lütfen tekrar deneyin.', 'warning')
                return redirect(url_for('satin_alma_giris', siparis_id=siparis_id))
            
            islem_tarihi = datetime.strptime(islem_tarihi_str, '%Y-%m-%d').date()
            tedarikci = Tedarikci.query.get_or_404(tedarikci_id)
            
            if request.method == 'POST':
                try:
                    # Ürün fiyatlarını al
                    urun_ids = request.form.getlist('urun_ids[]')
                    miktarlar = request.form.getlist('miktarlar[]')
                    birim_fiyatlar = request.form.getlist('birim_fiyatlar[]')
                    
                    if not urun_ids:
                        flash('En az bir ürün için fiyat girilmelidir.', 'warning')
                        return redirect(url_for('satin_alma_urun_giris', 
                                              siparis_id=siparis_id,
                                              tedarikci_id=tedarikci_id,
                                              islem_tarihi=islem_tarihi_str))
                    
                    # Satın alma işlemi oluştur
                    from models import SatinAlmaIslem, SatinAlmaIslemDetay
                    from decimal import Decimal
                    
                    # İşlem numarası üret
                    def islem_no_uret():
                        bugun = datetime.now()
                        tarih_str = bugun.strftime('%Y%m%d')
                        
                        # Bugün oluşturulan son işlem numarasını bul
                        son_islem = SatinAlmaIslem.query.filter(
                            SatinAlmaIslem.islem_no.like(f'SA-{tarih_str}-%')
                        ).order_by(desc(SatinAlmaIslem.islem_no)).first()
                        
                        if son_islem:
                            son_no = int(son_islem.islem_no.split('-')[-1])
                            yeni_no = son_no + 1
                        else:
                            yeni_no = 1
                        
                        return f'SA-{tarih_str}-{yeni_no:04d}'
                    
                    toplam_tutar = Decimal('0')
                    urun_listesi = []
                    
                    for i in range(len(urun_ids)):
                        try:
                            urun_id = int(urun_ids[i])
                            miktar = int(miktarlar[i])
                            birim_fiyat = Decimal(str(birim_fiyatlar[i]))
                            
                            if miktar > 0 and birim_fiyat > 0:
                                toplam_fiyat = miktar * birim_fiyat
                                toplam_tutar += toplam_fiyat
                                
                                urun_listesi.append({
                                    'urun_id': urun_id,
                                    'miktar': miktar,
                                    'birim_fiyat': birim_fiyat,
                                    'toplam_fiyat': toplam_fiyat
                                })
                        except (ValueError, IndexError):
                            continue
                    
                    if not urun_listesi:
                        flash('Geçerli ürün bilgisi girilmelidir.', 'warning')
                        return redirect(url_for('satin_alma_urun_giris', 
                                              siparis_id=siparis_id,
                                              tedarikci_id=tedarikci_id,
                                              islem_tarihi=islem_tarihi_str))
                    
                    # Satın alma işlemi oluştur
                    satin_alma = SatinAlmaIslem(
                        islem_no=islem_no_uret(),
                        tedarikci_id=tedarikci_id,
                        otel_id=siparis.otel_id,
                        siparis_id=siparis_id,
                        islem_tarihi=datetime.combine(islem_tarihi, datetime.min.time()),
                        toplam_tutar=toplam_tutar,
                        genel_toplam=toplam_tutar,  # KDV hesabı yapılmadığı için aynı
                        aciklama=f'Sipariş No: {siparis.siparis_no} - Satın Alma Girişi',
                        olusturan_id=session['kullanici_id']
                    )
                    db.session.add(satin_alma)
                    db.session.flush()
                    
                    # Detayları ekle ve stok girişi yap
                    for urun_data in urun_listesi:
                        # Satın alma işlem detayı
                        detay = SatinAlmaIslemDetay(
                            islem_id=satin_alma.id,
                            urun_id=urun_data['urun_id'],
                            miktar=urun_data['miktar'],
                            birim_fiyat=urun_data['birim_fiyat'],
                            toplam_fiyat=urun_data['toplam_fiyat']
                        )
                        db.session.add(detay)
                        
                        # Sipariş detayını güncelle (fiyat ve teslim alınan miktar)
                        siparis_detay = SatinAlmaSiparisDetay.query.filter_by(
                            siparis_id=siparis_id,
                            urun_id=urun_data['urun_id']
                        ).first()
                        
                        if siparis_detay:
                            # Birim fiyatı güncelle
                            siparis_detay.birim_fiyat = urun_data['birim_fiyat']
                            siparis_detay.toplam_fiyat = urun_data['toplam_fiyat']
                            # Teslim alınan miktarı güncelle
                            siparis_detay.teslim_alinan_miktar += urun_data['miktar']
                        
                        # Stok girişi yap
                        stok_hareket = StokHareket(
                            urun_id=urun_data['urun_id'],
                            hareket_tipi='giris',
                            miktar=urun_data['miktar'],
                            aciklama=f"Satın Alma - {tedarikci.tedarikci_adi} - Sipariş: {siparis.siparis_no}",
                            islem_yapan_id=session['kullanici_id']
                        )
                        db.session.add(stok_hareket)
                    
                    # Sipariş toplam tutarını güncelle
                    siparis.toplam_tutar = toplam_tutar
                    
                    # Sipariş durumunu güncelle
                    siparis.durum = 'teslim_alindi'
                    siparis.gerceklesen_teslimat_tarihi = islem_tarihi
                    
                    db.session.commit()
                    
                    # Audit log
                    audit_create(
                        tablo_adi='satin_alma_islemler',
                        kayit_id=satin_alma.id,
                        yeni_deger=serialize_model(satin_alma),
                        aciklama=f'Satın alma işlemi oluşturuldu - Sipariş: {siparis.siparis_no}'
                    )
                    
                    # Log kaydı
                    log_islem('ekleme', 'satin_alma', {
                        'islem_id': satin_alma.id,
                        'siparis_id': siparis_id,
                        'tedarikci_id': tedarikci_id,
                        'toplam_tutar': float(toplam_tutar)
                    })
                    
                    # Satış fiyatı olmayan ürünleri kontrol et
                    fiyatsiz_urunler = []
                    
                    for urun_data in urun_listesi:
                        urun_id = urun_data['urun_id']
                        urun = Urun.query.get(urun_id)
                        
                        # Satış fiyatı var mı kontrol et (hasattr ile güvenli kontrol)
                        satis_fiyati = getattr(urun, 'satis_fiyati', None)
                        if not satis_fiyati or satis_fiyati <= 0:
                            fiyatsiz_urunler.append({
                                'urun_id': urun_id,
                                'urun_adi': urun.urun_adi,
                                'birim': urun.birim,
                                'alis_fiyati': float(urun_data['birim_fiyat'])
                            })
                    
                    flash('Satın alma işlemi başarıyla tamamlandı ve stok girişi yapıldı.', 'success')
                    
                    # Eğer satış fiyatı olmayan ürünler varsa, fiyat girişi sayfasına yönlendir
                    if fiyatsiz_urunler:
                        session['fiyatsiz_urunler'] = fiyatsiz_urunler
                        session['satin_alma_id'] = satin_alma.id
                        flash(f'{len(fiyatsiz_urunler)} ürün için satış fiyatı belirlemeniz gerekiyor.', 'warning')
                        return redirect(url_for('satis_fiyat_giris', satin_alma_id=satin_alma.id))
                    
                    return redirect(url_for('siparis_detay', siparis_id=siparis_id))
                    
                except Exception as e:
                    db.session.rollback()
                    log_hata(e, 'satin_alma_urun_giris_post')
                    flash(f'Satın alma işlemi sırasında hata oluştu: {str(e)}', 'danger')
            
            # Sipariş detaylarını getir
            detaylar = SatinAlmaSiparisDetay.query.filter_by(siparis_id=siparis_id).all()
            
            return render_template('depo_sorumlusu/satin_alma_urun_giris.html',
                                 siparis=siparis,
                                 detaylar=detaylar,
                                 tedarikci=tedarikci,
                                 islem_tarihi=islem_tarihi,
                                 islem_tarihi_str=islem_tarihi_str)
                                 
        except Exception as e:
            log_hata(e, 'satin_alma_urun_giris')
            flash(f'Sayfa yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('siparis_listesi'))
    
    
    # ==================== SATIŞ FİYATI GİRİŞİ ROUTE'LARI ====================
    
    @app.route('/satis-fiyat-giris/<int:satin_alma_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def satis_fiyat_giris(satin_alma_id):
        """Satın alma sonrası satış fiyatı girişi"""
        try:
            from models import SatinAlmaIslem
            from decimal import Decimal
            
            satin_alma = SatinAlmaIslem.query.get_or_404(satin_alma_id)
            
            # Session'dan fiyatsız ürünleri al
            fiyatsiz_urunler = session.get('fiyatsiz_urunler', [])
            
            if not fiyatsiz_urunler:
                flash('Satış fiyatı girilmesi gereken ürün bulunamadı.', 'info')
                if satin_alma.siparis_id:
                    return redirect(url_for('siparis_detay', siparis_id=satin_alma.siparis_id))
                return redirect(url_for('siparis_listesi'))
            
            if request.method == 'POST':
                try:
                    urun_ids = request.form.getlist('urun_ids[]')
                    satis_fiyatlari = request.form.getlist('satis_fiyatlari[]')
                    kar_marjlari = request.form.getlist('kar_marjlari[]')
                    
                    kayit_sayisi = 0
                    
                    for i in range(len(urun_ids)):
                        try:
                            urun_id = int(urun_ids[i])
                            satis_fiyati = Decimal(str(satis_fiyatlari[i]))
                            kar_marji = Decimal(str(kar_marjlari[i]))
                            
                            if satis_fiyati > 0:
                                # Ürünün satış fiyatını güncelle
                                urun = Urun.query.get(urun_id)
                                if urun:
                                    # Eski değeri sakla (fiyat geçmişi için)
                                    eski_satis_fiyati = getattr(urun, 'satis_fiyati', None)
                                    
                                    # Yeni fiyatları kaydet (setattr ile güvenli)
                                    setattr(urun, 'satis_fiyati', satis_fiyati)
                                    setattr(urun, 'kar_orani', kar_marji)
                                    
                                    # Alış fiyatını da güncelle (bu satın almadan)
                                    for fiyatsiz in fiyatsiz_urunler:
                                        if fiyatsiz['urun_id'] == urun_id:
                                            alis_fiyati_deger = Decimal(str(fiyatsiz['alis_fiyati']))
                                            setattr(urun, 'alis_fiyati', alis_fiyati_deger)
                                            setattr(urun, 'kar_tutari', satis_fiyati - alis_fiyati_deger)
                                            break
                                    
                                    # Fiyat geçmişi kaydı oluştur (Satış fiyatı için)
                                    from models import UrunFiyatGecmisi
                                    fiyat_gecmis = UrunFiyatGecmisi(
                                        urun_id=urun_id,
                                        eski_fiyat=eski_satis_fiyati or Decimal('0'),
                                        yeni_fiyat=satis_fiyati,
                                        degisiklik_tipi='satis_fiyati',
                                        degisiklik_sebebi=f'Satın alma işlemi sonrası fiyat belirleme - İşlem No: {satin_alma.islem_no}',
                                        olusturan_id=session['kullanici_id']
                                    )
                                    db.session.add(fiyat_gecmis)
                                    
                                    # ✅ Alış fiyatı geçmişi de kaydet
                                    for fiyatsiz in fiyatsiz_urunler:
                                        if fiyatsiz['urun_id'] == urun_id:
                                            alis_fiyati_deger = Decimal(str(fiyatsiz['alis_fiyati']))
                                            eski_alis_fiyati = urun.alis_fiyati or Decimal('0')
                                            
                                            # Alış fiyatı değiştiyse geçmişe kaydet
                                            if eski_alis_fiyati != alis_fiyati_deger:
                                                alis_fiyat_gecmis = UrunFiyatGecmisi(
                                                    urun_id=urun_id,
                                                    eski_fiyat=eski_alis_fiyati,
                                                    yeni_fiyat=alis_fiyati_deger,
                                                    degisiklik_tipi='alis_fiyati',
                                                    degisiklik_sebebi=f'Satın alma işlemi - İşlem No: {satin_alma.islem_no}',
                                                    olusturan_id=session['kullanici_id']
                                                )
                                                db.session.add(alis_fiyat_gecmis)
                                            break
                                    
                                    kayit_sayisi += 1
                        except (ValueError, IndexError) as e:
                            log_hata(e, 'satis_fiyat_giris_item')
                            continue
                    
                    if kayit_sayisi > 0:
                        db.session.commit()
                        
                        # Session'ı temizle
                        session.pop('fiyatsiz_urunler', None)
                        session.pop('satin_alma_id', None)
                        
                        # Audit log
                        audit_create(
                            tablo_adi='urunler',
                            kayit_id=0,
                            yeni_deger={'kayit_sayisi': kayit_sayisi},
                            aciklama=f'{kayit_sayisi} ürün için satış fiyatı belirlendi - Satın Alma: {satin_alma.islem_no}'
                        )
                        
                        flash(f'{kayit_sayisi} ürün için satış fiyatı başarıyla kaydedildi.', 'success')
                        
                        if satin_alma.siparis_id:
                            return redirect(url_for('siparis_detay', siparis_id=satin_alma.siparis_id))
                        return redirect(url_for('siparis_listesi'))
                    else:
                        flash('Geçerli satış fiyatı girilmedi.', 'warning')
                        
                except Exception as e:
                    db.session.rollback()
                    log_hata(e, 'satis_fiyat_giris_post')
                    flash(f'Satış fiyatları kaydedilirken hata oluştu: {str(e)}', 'danger')
            
            return render_template('depo_sorumlusu/satis_fiyat_giris.html',
                                 satin_alma=satin_alma,
                                 fiyatsiz_urunler=fiyatsiz_urunler)
                                 
        except Exception as e:
            log_hata(e, 'satis_fiyat_giris')
            flash(f'Sayfa yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('siparis_listesi'))

    
    @app.route('/api/depo/bekleyen-siparisler')
    @login_required
    @role_required('depo_sorumlusu')
    def api_depo_bekleyen_siparisler():
        """Depo sorumlusu için bekleyen kat sorumlusu sipariş taleplerini listele"""
        try:
            from utils.authorization import get_kullanici_otelleri
            
            # Kullanıcının erişebileceği oteller
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [otel.id for otel in kullanici_otelleri]
            
            # Bekleyen sipariş taleplerini getir
            query = KatSorumlusuSiparisTalebi.query.join(
                Kullanici, KatSorumlusuSiparisTalebi.kat_sorumlusu_id == Kullanici.id
            ).filter(
                KatSorumlusuSiparisTalebi.durum == 'beklemede'
            )
            
            # Otel filtrelemesi (kat sorumlusunun oteli üzerinden)
            if otel_ids:
                query = query.filter(Kullanici.otel_id.in_(otel_ids))
            
            siparisler = query.order_by(
                KatSorumlusuSiparisTalebi.talep_tarihi.desc()
            ).limit(50).all()
            
            siparis_listesi = []
            for siparis in siparisler:
                # Sipariş detaylarını al
                detaylar = KatSorumlusuSiparisTalepDetay.query.filter_by(
                    talep_id=siparis.id
                ).all()
                
                # Kat sorumlusu bilgisi
                kat_sorumlusu = db.session.get(Kullanici, siparis.kat_sorumlusu_id)
                otel_adi = kat_sorumlusu.otel.ad if kat_sorumlusu and kat_sorumlusu.otel else 'Bilinmeyen'
                
                siparis_listesi.append({
                    'id': siparis.id,
                    'talep_no': siparis.talep_no,
                    'talep_tarihi': siparis.talep_tarihi.strftime('%d.%m.%Y %H:%M'),
                    'personel': f"{kat_sorumlusu.ad} {kat_sorumlusu.soyad}" if kat_sorumlusu else 'Bilinmeyen',
                    'otel': otel_adi,
                    'toplam_urun': len(detaylar),
                    'durum': siparis.durum
                })
            
            return jsonify({
                'success': True,
                'siparisler': siparis_listesi
            })
            
        except Exception as e:
            log_hata(e, modul='depo_bekleyen_siparisler_api')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    
    @app.route('/depo-stoklarim')
    @login_required
    @role_required('depo_sorumlusu')
    def depo_stoklarim():
        """Depo sorumlusu stok takip sayfası"""
        try:
            from utils.authorization import get_kullanici_otelleri, get_otel_filtreleme_secenekleri
            
            # Kullanıcının erişebileceği oteller
            kullanici_otelleri = get_kullanici_otelleri()
            otel_secenekleri = get_otel_filtreleme_secenekleri()
            
            # Seçili otel
            secili_otel_id = request.args.get('otel_id', type=int)
            if not secili_otel_id and kullanici_otelleri:
                secili_otel_id = kullanici_otelleri[0].id
            
            # Tüm ürünleri ve stok durumlarını getir
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            # Her ürün için stok bilgilerini hesapla
            stok_bilgileri = []
            for urun in urunler:
                stok_toplam = get_stok_toplamlari([urun.id])
                mevcut_stok = stok_toplam.get(urun.id, 0)
                
                # Kritik seviye kontrolü (varsayılan 10)
                kritik_seviye = 10
                durum = 'yeterli'
                if mevcut_stok == 0:
                    durum = 'tukendi'
                elif mevcut_stok <= kritik_seviye:
                    durum = 'kritik'
                
                stok_bilgileri.append({
                    'urun': urun,
                    'mevcut_stok': mevcut_stok,
                    'kritik_seviye': kritik_seviye,
                    'durum': durum
                })
            
            return render_template('depo_sorumlusu/stoklarim.html',
                                 stok_bilgileri=stok_bilgileri,
                                 otel_secenekleri=otel_secenekleri,
                                 secili_otel_id=secili_otel_id)
                                 
        except Exception as e:
            log_hata(e, modul='depo_stoklarim')
            flash(f'Stoklar yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
    
    @app.route('/kat-sorumlusu-siparisler')
    @login_required
    @role_required('depo_sorumlusu')
    def kat_sorumlusu_siparisler():
        """Kat sorumlusu sipariş talepleri sayfası"""
        try:
            from utils.authorization import get_kullanici_otelleri
            
            # Kullanıcının erişebileceği oteller
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [otel.id for otel in kullanici_otelleri]
            
            # Bekleyen sipariş taleplerini getir
            query = KatSorumlusuSiparisTalebi.query.join(
                Kullanici, KatSorumlusuSiparisTalebi.kat_sorumlusu_id == Kullanici.id
            ).filter(
                KatSorumlusuSiparisTalebi.durum == 'beklemede'
            )
            
            # Otel filtrelemesi
            if otel_ids:
                query = query.filter(Kullanici.otel_id.in_(otel_ids))
            
            siparisler = query.order_by(
                KatSorumlusuSiparisTalebi.talep_tarihi.desc()
            ).all()
            
            # Her sipariş için stok durumunu kontrol et
            for siparis in siparisler:
                # Kat sorumlusu bilgisini yükle
                siparis.personel = db.session.get(Kullanici, siparis.kat_sorumlusu_id)
                
                # Detayları yükle
                siparis.detaylar_list = KatSorumlusuSiparisTalepDetay.query.filter_by(
                    talep_id=siparis.id
                ).all()
                
                # Her ürün için stok kontrolü
                for detay in siparis.detaylar_list:
                    # Mevcut stok miktarını al
                    stok_toplam = get_stok_toplamlari([detay.urun_id])
                    detay.mevcut_stok = stok_toplam.get(detay.urun_id, 0)
                    detay.stok_uygun = detay.mevcut_stok >= detay.talep_miktari
                    # Template için miktar alias'ı ekle
                    detay.miktar = detay.talep_miktari
            
            return render_template('depo_sorumlusu/kat_sorumlusu_siparisler.html', 
                                 siparisler=siparisler)
                                 
        except Exception as e:
            log_hata(e, modul='kat_sorumlusu_siparisler')
            flash(f'Siparişler yüklenirken hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('dashboard'))
    
    @app.route('/api/depo/siparis-kabul/<int:siparis_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def api_depo_siparis_kabul(siparis_id):
        """Kat sorumlusu siparişini kabul et (zimmet onaylama ve stok çıkışı)"""
        try:
            zimmet = db.session.get(PersonelZimmet, siparis_id)
            
            if not zimmet:
                return jsonify({
                    'success': False,
                    'error': 'Sipariş bulunamadı'
                }), 404
            
            # Zimmet zaten onaylanmış mı kontrol et
            if zimmet.durum != 'aktif':
                return jsonify({
                    'success': False,
                    'error': 'Bu sipariş zaten işlenmiş'
                }), 400
            
            # Zimmet detaylarını al
            detaylar = PersonelZimmetDetay.query.filter_by(zimmet_id=zimmet.id).all()
            
            # Stok kontrolü yap
            for detay in detaylar:
                stok_toplam = get_stok_toplamlari([detay.urun_id])
                mevcut_stok = stok_toplam.get(detay.urun_id, 0)
                
                if mevcut_stok < detay.miktar:
                    urun = db.session.get(Urun, detay.urun_id)
                    return jsonify({
                        'success': False,
                        'error': f'{urun.urun_adi} için stok yetersiz! Mevcut: {mevcut_stok}, Talep: {detay.miktar}'
                    }), 400
            
            # Stok çıkışlarını yap
            for detay in detaylar:
                stok_hareket = StokHareket(
                    urun_id=detay.urun_id,
                    hareket_tipi='cikis',
                    miktar=detay.miktar,
                    aciklama=f'Zimmet atama - {zimmet.personel.ad} {zimmet.personel.soyad}',
                    islem_yapan_id=session['kullanici_id']
                )
                db.session.add(stok_hareket)
                
                # Audit Trail
                audit_create('stok_hareket', stok_hareket.id, stok_hareket)
            
            # Teslim eden olarak depo sorumlusunu kaydet (durum aktif kalır)
            zimmet.teslim_eden_id = session['kullanici_id']
            db.session.commit()
            
            # Log kaydı
            log_islem('guncelleme', 'personel_zimmet', {
                'zimmet_id': zimmet.id,
                'personel_id': zimmet.personel_id,
                'durum': 'onaylandi',
                'toplam_urun': len(detaylar)
            })
            
            return jsonify({
                'success': True,
                'message': f'Zimmet başarıyla onaylandı! {len(detaylar)} ürün için stok çıkışı yapıldı.'
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='depo_siparis_kabul')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/depo/siparis-iptal/<int:siparis_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def api_depo_siparis_iptal(siparis_id):
        """Kat sorumlusu siparişini iptal et (Sadece bekleyen siparişler)"""
        try:
            zimmet = db.session.get(PersonelZimmet, siparis_id)
            
            if not zimmet:
                return jsonify({
                    'success': False,
                    'error': 'Sipariş bulunamadı'
                }), 404
            
            # Sadece aktif (bekleyen) siparişler iptal edilebilir
            if zimmet.durum != 'aktif':
                return jsonify({
                    'success': False,
                    'error': 'Sadece bekleyen siparişler iptal edilebilir'
                }), 400
            
            # Teslim eden yoksa bu bir sipariştir (zimmet değil)
            if zimmet.teslim_eden_id is not None:
                return jsonify({
                    'success': False,
                    'error': 'Bu bir zimmet kaydıdır, sipariş değil'
                }), 400
            
            # Zimmet detaylarını al
            detaylar = PersonelZimmetDetay.query.filter_by(zimmet_id=zimmet.id).all()
            
            # Sipariş durumunu iptal et
            zimmet.durum = 'iptal'
            zimmet.iade_tarihi = datetime.now()
            
            db.session.commit()
            
            # Log kaydı
            log_islem('iptal', 'kat_sorumlusu_siparis', {
                'siparis_id': zimmet.id,
                'personel_id': zimmet.personel_id,
                'iptal_eden_id': session['kullanici_id'],
                'toplam_urun': len(detaylar)
            })
            
            return jsonify({
                'success': True,
                'message': 'Sipariş başarıyla iptal edildi.'
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='depo_siparis_iptal')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/depo/kat-sorumlusu-siparis-reddet/<int:talep_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def api_kat_sorumlusu_siparis_reddet(talep_id):
        """Kat sorumlusu sipariş talebini reddet"""
        try:
            from models import KatSorumlusuSiparisTalebi
            
            # Sipariş talebini bul
            talep = KatSorumlusuSiparisTalebi.query.get(talep_id)
            if not talep:
                return jsonify({
                    'success': False,
                    'message': 'Sipariş talebi bulunamadı'
                }), 404
            
            # Sadece bekleyen talepler reddedilebilir
            if talep.durum != 'beklemede':
                return jsonify({
                    'success': False,
                    'message': f'Sadece bekleyen talepler reddedilebilir. Mevcut durum: {talep.durum}'
                }), 400
            
            # Red nedeni al
            red_nedeni = request.json.get('red_nedeni', 'Belirtilmemiş')
            
            # Talebi reddet
            talep.durum = 'reddedildi'
            talep.red_nedeni = red_nedeni
            talep.islem_tarihi = datetime.utcnow()
            talep.islem_yapan_id = session['kullanici_id']
            
            db.session.commit()
            
            # Log kaydı
            log_islem('reddet', 'kat_sorumlusu_siparis_talep', {
                'talep_id': talep.id,
                'kat_sorumlusu_id': talep.kat_sorumlusu_id,
                'red_nedeni': red_nedeni,
                'depo_sorumlusu_id': session['kullanici_id']
            })
            
            return jsonify({
                'success': True,
                'message': 'Sipariş talebi başarıyla reddedildi'
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='kat_sorumlusu_siparis_reddet')
            return jsonify({
                'success': False,
                'message': f'Hata oluştu: {str(e)}'
            }), 500
    
    @app.route('/api/depo/kat-sorumlusu-siparis-onayla/<int:talep_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def api_kat_sorumlusu_siparis_onayla(talep_id):
        """Kat sorumlusu sipariş talebini onayla ve zimmet oluştur"""
        try:
            from models import KatSorumlusuSiparisTalebi, KatSorumlusuSiparisTalepDetay
            
            # Sipariş talebini bul
            talep = KatSorumlusuSiparisTalebi.query.get(talep_id)
            if not talep:
                return jsonify({
                    'success': False,
                    'message': 'Sipariş talebi bulunamadı'
                }), 404
            
            # Sadece bekleyen talepler onaylanabilir
            if talep.durum != 'beklemede':
                return jsonify({
                    'success': False,
                    'message': f'Sadece bekleyen talepler onaylanabilir. Mevcut durum: {talep.durum}'
                }), 400
            
            # Zimmet oluştur
            zimmet = PersonelZimmet(
                personel_id=talep.kat_sorumlusu_id,
                durum='aktif',
                talep_tarihi=datetime.utcnow(),
                aciklama=f'Kat sorumlusu sipariş talebinden oluşturuldu (Talep #{talep.id})'
            )
            db.session.add(zimmet)
            db.session.flush()
            
            # Zimmet detaylarını oluştur
            for detay in talep.detaylar:
                zimmet_detay = PersonelZimmetDetay(
                    zimmet_id=zimmet.id,
                    urun_id=detay.urun_id,
                    miktar=detay.talep_miktari
                )
                db.session.add(zimmet_detay)
            
            # Talebi onayla
            talep.durum = 'onaylandi'
            talep.islem_tarihi = datetime.utcnow()
            talep.islem_yapan_id = session['kullanici_id']
            talep.zimmet_id = zimmet.id
            
            db.session.commit()
            
            # Log kaydı
            log_islem('onayla', 'kat_sorumlusu_siparis_talep', {
                'talep_id': talep.id,
                'kat_sorumlusu_id': talep.kat_sorumlusu_id,
                'zimmet_id': zimmet.id,
                'depo_sorumlusu_id': session['kullanici_id']
            })
            
            return jsonify({
                'success': True,
                'message': 'Sipariş talebi onaylandı ve zimmet oluşturuldu',
                'zimmet_id': zimmet.id
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='kat_sorumlusu_siparis_onayla')
            return jsonify({
                'success': False,
                'message': f'Hata oluştu: {str(e)}'
            }), 500

    # ==================== MANUEL RAPOR GÖNDERİM ROUTE'LARI ====================
    
    @app.route('/api/rapor/gorev-tamamlanma-gonder', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def manuel_gorev_raporu_gonder():
        """Manuel görev tamamlanma raporu gönderimi"""
        try:
            from utils.rapor_email_service import RaporEmailService
            from models import Kullanici
            from utils.authorization import get_kullanici_otelleri
            
            data = request.get_json() or {}
            rapor_tarihi_str = data.get('tarih')
            kat_sorumlusu_id = data.get('kat_sorumlusu_id')
            
            # Tarih parse
            if rapor_tarihi_str:
                rapor_tarihi = datetime.strptime(rapor_tarihi_str, '%Y-%m-%d').date()
            else:
                rapor_tarihi = date.today() - timedelta(days=1)
            
            # Kullanıcının erişebileceği oteller
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [o.id for o in kullanici_otelleri]
            
            gonderilen = 0
            hatali = 0
            sonuclar = []
            
            if kat_sorumlusu_id:
                # Tek kat sorumlusu için rapor gönder
                ks = Kullanici.query.get(kat_sorumlusu_id)
                if ks and ks.rol == 'kat_sorumlusu' and (session.get('rol') == 'sistem_yoneticisi' or ks.otel_id in otel_ids):
                    result = RaporEmailService.send_gorev_raporu(ks.id, rapor_tarihi)
                    if result.get('success'):
                        gonderilen += 1
                        sonuclar.append({'ad': f"{ks.ad} {ks.soyad}", 'durum': 'başarılı'})
                    else:
                        hatali += 1
                        sonuclar.append({'ad': f"{ks.ad} {ks.soyad}", 'durum': result.get('message', 'hata')})
            else:
                # Tüm kat sorumluları için rapor gönder
                if session.get('rol') == 'sistem_yoneticisi':
                    kat_sorumlulari = Kullanici.query.filter(
                        Kullanici.rol == 'kat_sorumlusu',
                        Kullanici.aktif == True
                    ).all()
                else:
                    kat_sorumlulari = Kullanici.query.filter(
                        Kullanici.rol == 'kat_sorumlusu',
                        Kullanici.aktif == True,
                        Kullanici.otel_id.in_(otel_ids)
                    ).all()
                
                for ks in kat_sorumlulari:
                    result = RaporEmailService.send_gorev_raporu(ks.id, rapor_tarihi)
                    if result.get('success'):
                        gonderilen += 1
                        sonuclar.append({'ad': f"{ks.ad} {ks.soyad}", 'durum': 'başarılı'})
                    else:
                        hatali += 1
                        sonuclar.append({'ad': f"{ks.ad} {ks.soyad}", 'durum': result.get('message', 'hata')})
            
            log_islem('rapor_gonder', 'gorev_tamamlanma', {
                'tarih': rapor_tarihi.isoformat(),
                'gonderilen': gonderilen,
                'hatali': hatali
            })
            
            return jsonify({
                'success': gonderilen > 0,
                'message': f'{gonderilen} rapor gönderildi, {hatali} hata',
                'gonderilen': gonderilen,
                'hatali': hatali,
                'sonuclar': sonuclar
            })
            
        except Exception as e:
            log_hata(e, modul='manuel_gorev_raporu_gonder')
            return jsonify({
                'success': False,
                'message': f'Hata oluştu: {str(e)}'
            }), 500
    
    @app.route('/api/rapor/minibar-sarfiyat-gonder', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def manuel_minibar_raporu_gonder():
        """Manuel minibar sarfiyat raporu gönderimi"""
        try:
            from utils.rapor_email_service import RaporEmailService
            from models import Otel
            from utils.authorization import get_kullanici_otelleri
            
            data = request.get_json() or {}
            rapor_tarihi_str = data.get('tarih')
            otel_id = data.get('otel_id')
            
            # Tarih parse
            if rapor_tarihi_str:
                rapor_tarihi = datetime.strptime(rapor_tarihi_str, '%Y-%m-%d').date()
            else:
                rapor_tarihi = date.today() - timedelta(days=1)
            
            # Kullanıcının erişebileceği oteller
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [o.id for o in kullanici_otelleri]
            
            gonderilen = 0
            hatali = 0
            sonuclar = []
            
            if otel_id:
                # Tek otel için rapor gönder
                otel = Otel.query.get(otel_id)
                if otel and (session.get('rol') == 'sistem_yoneticisi' or otel.id in otel_ids):
                    result = RaporEmailService.send_minibar_raporu(otel.id, rapor_tarihi)
                    if result.get('success'):
                        gonderilen += 1
                        sonuclar.append({'ad': otel.ad, 'durum': 'başarılı'})
                    else:
                        hatali += 1
                        sonuclar.append({'ad': otel.ad, 'durum': result.get('message', 'hata')})
            else:
                # Tüm oteller için rapor gönder
                if session.get('rol') == 'sistem_yoneticisi':
                    oteller = Otel.query.filter_by(aktif=True).all()
                else:
                    oteller = [o for o in kullanici_otelleri if o.aktif]
                
                for otel in oteller:
                    result = RaporEmailService.send_minibar_raporu(otel.id, rapor_tarihi)
                    if result.get('success'):
                        gonderilen += 1
                        sonuclar.append({'ad': otel.ad, 'durum': 'başarılı'})
                    else:
                        hatali += 1
                        sonuclar.append({'ad': otel.ad, 'durum': result.get('message', 'hata')})
            
            log_islem('rapor_gonder', 'minibar_sarfiyat', {
                'tarih': rapor_tarihi.isoformat(),
                'gonderilen': gonderilen,
                'hatali': hatali
            })
            
            return jsonify({
                'success': gonderilen > 0,
                'message': f'{gonderilen} rapor gönderildi, {hatali} hata',
                'gonderilen': gonderilen,
                'hatali': hatali,
                'sonuclar': sonuclar
            })
            
        except Exception as e:
            log_hata(e, modul='manuel_minibar_raporu_gonder')
            return jsonify({
                'success': False,
                'message': f'Hata oluştu: {str(e)}'
            }), 500
