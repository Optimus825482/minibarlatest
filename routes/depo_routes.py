"""
Depo Sorumlusu Route'ları

Bu modül depo sorumlusu ile ilgili endpoint'leri içerir.

Endpoint'ler:
- /stok-giris - Stok giriş işlemi
- /stok-duzenle/<int:hareket_id> - Stok hareket düzenleme
- /stok-sil/<int:hareket_id> - Stok hareket silme
- /personel-zimmet - Personel zimmet atama
- /api/depo/bekleyen-siparisler - Bekleyen kat sorumlusu sipariş talepleri
- /depo-stoklarim - Depo stok takip
- /kat-sorumlusu-siparisler - Kat sorumlusu sipariş talepleri
- /ana-depo-tedarik - Ana depo tedarik işlemleri

Roller:
- depo_sorumlusu
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify
from models import (db, StokHareket, Urun, UrunGrup, Kullanici, PersonelZimmet, PersonelZimmetDetay,
                   UrunStok,
                   KatSorumlusuSiparisTalebi, KatSorumlusuSiparisTalepDetay,
                   AnaDepoTedarik, AnaDepoTedarikDetay, StokFifoKayit, StokFifoKullanim)
from sqlalchemy import desc
from sqlalchemy.orm import joinedload
from utils.decorators import login_required, role_required
from utils.helpers import log_islem, log_hata, get_stok_toplamlari
from utils.audit import audit_create, audit_update, audit_delete, serialize_model
from utils.query_helpers_optimized import get_stok_hareketleri_optimized
from models.base import get_kktc_now, KKTC_TZ
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)

# Sabitler
DEFAULT_QUERY_LIMIT = 50
DEFAULT_KRITIK_STOK_SEVIYESI = 10


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
                
                if miktar <= 0:
                    flash('Miktar sıfırdan büyük olmalıdır.', 'warning')
                    return redirect(url_for('stok_giris'))
                
                urun = db.session.get(Urun, urun_id)
                if not urun:
                    flash('Geçersiz ürün seçimi.', 'danger')
                    return redirect(url_for('stok_giris'))
                
                stok_hareket = StokHareket(
                    urun_id=urun_id,
                    hareket_tipi=hareket_tipi,
                    miktar=miktar,
                    aciklama=aciklama,
                    islem_yapan_id=session.get('kullanici_id')
                )
                db.session.add(stok_hareket)
                db.session.flush()
                
                # Audit Trail (flush sonrası id mevcut)
                audit_create('stok_hareket', stok_hareket.id, stok_hareket)
                
                db.session.commit()
                
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
                
            except (ValueError, KeyError):
                flash('Geçersiz form verisi. Lütfen alanları kontrol edin.', 'danger')
            except Exception as e:
                db.session.rollback()
                log_hata(e, modul='stok_giris')
                flash('Stok girişi sırasında bir hata oluştu.', 'danger')
        
        # Aktif ürün gruplarını getir
        gruplar = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
        
        # Aktif ürünleri grup ile birlikte getir
        urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
        
        # Son stok hareketlerini getir (optimized - N+1 problemi çözüldü)
        stok_hareketleri = get_stok_hareketleri_optimized(limit=DEFAULT_QUERY_LIMIT)
        
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
                yeni_miktar = int(request.form['miktar'])
                if yeni_miktar <= 0:
                    flash('Miktar sıfırdan büyük olmalıdır.', 'warning')
                    return redirect(url_for('stok_duzenle', hareket_id=hareket_id))
                
                eski_deger = serialize_model(hareket)
                
                hareket.miktar = yeni_miktar
                hareket.hareket_tipi = request.form['hareket_tipi']
                hareket.aciklama = request.form.get('aciklama', '')
                
                db.session.commit()
                
                audit_update('stok_hareket', hareket.id, eski_deger, hareket)
                
                log_islem('guncelleme', 'stok', {
                    'hareket_id': hareket.id,
                    'urun_id': hareket.urun_id,
                    'urun_adi': hareket.urun.urun_adi if hareket.urun else 'Bilinmeyen',
                    'hareket_tipi': hareket.hareket_tipi,
                    'miktar': hareket.miktar
                })
                
                flash('Stok hareketi başarıyla güncellendi.', 'success')
                return redirect(url_for('stok_giris'))
                
            except (ValueError, KeyError):
                flash('Geçersiz form verisi. Lütfen alanları kontrol edin.', 'danger')
            except Exception as e:
                db.session.rollback()
                log_hata(e, modul='stok_duzenle')
                flash('Güncelleme sırasında bir hata oluştu.', 'danger')
        
        urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
        return render_template('depo_sorumlusu/stok_duzenle.html', hareket=hareket, urunler=urunler)

    @app.route('/stok-sil/<int:hareket_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def stok_sil(hareket_id):
        """Stok hareket silme"""
        try:
            hareket = StokHareket.query.get_or_404(hareket_id)
            
            urun_adi = hareket.urun.urun_adi if hareket.urun else 'Bilinmeyen'
            hareket_tipi = hareket.hareket_tipi
            miktar = hareket.miktar
            
            eski_deger = serialize_model(hareket)
            
            db.session.delete(hareket)
            db.session.commit()
            
            audit_delete('stok_hareket', hareket_id, eski_deger)
            
            log_islem('silme', 'stok', {
                'hareket_id': hareket_id,
                'urun_adi': urun_adi,
                'hareket_tipi': hareket_tipi,
                'miktar': miktar
            })
            
            flash('Stok hareketi başarıyla silindi.', 'success')
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='stok_sil')
            flash('Silme işlemi sırasında bir hata oluştu.', 'danger')
        
        return redirect(url_for('stok_giris'))

    @app.route('/personel-zimmet', methods=['GET', 'POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def personel_zimmet():
        """Personel zimmet atama - FIFO entegrasyonlu"""
        from utils.authorization import get_kullanici_otelleri, get_otel_filtreleme_secenekleri
        from utils.fifo_servisler import FifoStokServisi
        
        kullanici_otelleri = get_kullanici_otelleri()
        otel_secenekleri = get_otel_filtreleme_secenekleri()
        
        secili_otel_id = request.args.get('otel_id', type=int)
        if not secili_otel_id and kullanici_otelleri:
            secili_otel_id = kullanici_otelleri[0].id
        
        if request.method == 'POST':
            try:
                personel_id = int(request.form['personel_id'])
                aciklama = request.form.get('aciklama', '')
                urun_ids = request.form.getlist('urun_ids')
                
                personel = db.session.get(Kullanici, personel_id)
                if not personel or not personel.otel_id:
                    flash('Personel veya otel bilgisi bulunamadı.', 'danger')
                    return redirect(url_for('personel_zimmet'))
                
                otel_id = personel.otel_id

                if not urun_ids:
                    flash('En az bir ürün seçmelisiniz.', 'warning')
                    return redirect(url_for('personel_zimmet'))

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

                fifo_stoklar = FifoStokServisi.toplu_stok_getir(otel_id, list(urun_miktarlari.keys()))
                urun_kayitlari = {
                    urun.id: urun for urun in Urun.query.filter(Urun.id.in_(urun_miktarlari.keys())).all()
                }

                yetersiz_stok = []
                for uid, talep_miktari in urun_miktarlari.items():
                    mevcut = fifo_stoklar.get(uid, 0)
                    if talep_miktari > mevcut:
                        urun = urun_kayitlari.get(uid)
                        urun_adi = f"{urun.urun_adi} ({urun.birim})" if urun else f'ID {uid}'
                        yetersiz_stok.append((urun_adi, talep_miktari, mevcut))

                if yetersiz_stok:
                    detay_mesaji = '; '.join(
                        f"{urun_adi}: istenen {talep}, mevcut {mevcut}" for urun_adi, talep, mevcut in yetersiz_stok
                    )
                    flash(f'Otel deposunda stok yetersiz: {detay_mesaji}', 'danger')
                    return redirect(url_for('personel_zimmet'))

                zimmet = PersonelZimmet(
                    personel_id=personel_id,
                    teslim_eden_id=session.get('kullanici_id'),
                    aciklama=aciklama
                )
                db.session.add(zimmet)
                db.session.flush()

                for uid, miktar in urun_miktarlari.items():
                    detay = PersonelZimmetDetay(
                        zimmet_id=zimmet.id,
                        urun_id=uid,
                        miktar=miktar,
                        kalan_miktar=miktar
                    )
                    db.session.add(detay)
                    db.session.flush()

                    fifo_sonuc = FifoStokServisi.fifo_stok_cikis(
                        otel_id=otel_id,
                        urun_id=uid,
                        miktar=miktar,
                        islem_tipi='zimmet',
                        referans_id=detay.id,
                        kullanici_id=session.get('kullanici_id')
                    )
                    
                    if not fifo_sonuc['success']:
                        raise Exception(f"FIFO stok çıkışı hatası: {fifo_sonuc['message']}")
                
                db.session.commit()
                
                audit_create('personel_zimmet', zimmet.id, zimmet)
                
                flash('Zimmet başarıyla atandı (FIFO ile stok düşüldü).', 'success')
                return redirect(url_for('personel_zimmet'))
                
            except Exception as e:
                db.session.rollback()
                log_hata(e, modul='personel_zimmet')
                flash('Zimmet atama sırasında bir hata oluştu.', 'danger')
        
        if secili_otel_id:
            kat_sorumlulari = Kullanici.query.filter_by(rol='kat_sorumlusu', aktif=True, otel_id=secili_otel_id).all()
        else:
            kat_sorumlulari = Kullanici.query.filter_by(rol='kat_sorumlusu', aktif=True).all()
        
        urun_gruplari = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
        aktif_zimmetler = PersonelZimmet.query.options(
            joinedload(PersonelZimmet.personel),
            joinedload(PersonelZimmet.teslim_eden),
            joinedload(PersonelZimmet.detaylar).joinedload(PersonelZimmetDetay.urun)
        ).filter(
            PersonelZimmet.durum.in_(['aktif', 'iade_edildi'])
        ).order_by(PersonelZimmet.zimmet_tarihi.desc()).all()
        
        return render_template('depo_sorumlusu/personel_zimmet.html', 
                             kat_sorumlulari=kat_sorumlulari, 
                             urun_gruplari=urun_gruplari, 
                             aktif_zimmetler=aktif_zimmetler,
                             otel_secenekleri=otel_secenekleri,
                             secili_otel_id=secili_otel_id,
                             current_month=get_kktc_now().month,
                             current_year=get_kktc_now().year)

    # ==================== KAT SORUMLUSU SİPARİŞ TALEPLERİ ====================
    
    @app.route('/api/depo/bekleyen-siparisler')
    @login_required
    @role_required('depo_sorumlusu')
    def api_depo_bekleyen_siparisler():
        """Depo sorumlusu için bekleyen kat sorumlusu sipariş taleplerini listele"""
        try:
            from utils.authorization import get_kullanici_otelleri
            
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [otel.id for otel in kullanici_otelleri]
            
            query = KatSorumlusuSiparisTalebi.query.options(
                joinedload(KatSorumlusuSiparisTalebi.detaylar),
                joinedload(KatSorumlusuSiparisTalebi.kat_sorumlusu).joinedload(Kullanici.otel)
            ).join(
                Kullanici, KatSorumlusuSiparisTalebi.kat_sorumlusu_id == Kullanici.id
            ).filter(
                KatSorumlusuSiparisTalebi.durum == 'beklemede'
            )
            
            if otel_ids:
                query = query.filter(Kullanici.otel_id.in_(otel_ids))
            
            siparisler = query.order_by(
                KatSorumlusuSiparisTalebi.talep_tarihi.desc()
            ).limit(DEFAULT_QUERY_LIMIT).all()
            
            siparis_listesi = []
            for siparis in siparisler:
                kat_sorumlusu = siparis.kat_sorumlusu if hasattr(siparis, 'kat_sorumlusu') else None
                otel_adi = kat_sorumlusu.otel.ad if kat_sorumlusu and kat_sorumlusu.otel else 'Bilinmeyen'
                
                siparis_listesi.append({
                    'id': siparis.id,
                    'talep_no': siparis.talep_no,
                    'talep_tarihi': siparis.talep_tarihi.strftime('%d.%m.%Y %H:%M'),
                    'personel': f"{kat_sorumlusu.ad} {kat_sorumlusu.soyad}" if kat_sorumlusu else 'Bilinmeyen',
                    'otel': otel_adi,
                    'toplam_urun': len(siparis.detaylar) if siparis.detaylar else 0,
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
                'error': 'Bekleyen siparişler yüklenirken bir hata oluştu'
            }), 500

    @app.route('/depo-stoklarim')
    @login_required
    @role_required('depo_sorumlusu')
    def depo_stoklarim():
        """Depo sorumlusu stok takip sayfası - Otel bazlı"""
        try:
            from utils.authorization import get_kullanici_otelleri, get_otel_filtreleme_secenekleri
            from sqlalchemy import func
            
            kullanici_otelleri = get_kullanici_otelleri()
            otel_secenekleri = get_otel_filtreleme_secenekleri()
            otel_ids = [o.id for o in kullanici_otelleri]
            
            secili_otel_id = request.args.get('otel_id', type=int)
            
            secili_otel_adi = None
            if secili_otel_id:
                for otel in otel_secenekleri:
                    if otel.id == secili_otel_id:
                        secili_otel_adi = otel.ad
                        break
            
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            otel_stok_map = {}
            if secili_otel_id:
                otel_stoklar = UrunStok.query.filter_by(otel_id=secili_otel_id).all()
                otel_stok_map = {stok.urun_id: stok.mevcut_stok for stok in otel_stoklar}
            else:
                toplam_stoklar = db.session.query(
                    UrunStok.urun_id,
                    func.sum(UrunStok.mevcut_stok).label('toplam')
                ).filter(
                    UrunStok.otel_id.in_(otel_ids)
                ).group_by(UrunStok.urun_id).all()
                otel_stok_map = {row.urun_id: row.toplam or 0 for row in toplam_stoklar}
            
            stok_bilgileri = []
            for urun in urunler:
                mevcut_stok = otel_stok_map.get(urun.id, 0)
                
                kritik_seviye = urun.kritik_stok_seviyesi or DEFAULT_KRITIK_STOK_SEVIYESI
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
                                 secili_otel_id=secili_otel_id,
                                 secili_otel_adi=secili_otel_adi)
                                 
        except Exception as e:
            log_hata(e, modul='depo_stoklarim')
            flash('Stoklar yüklenirken bir hata oluştu.', 'danger')
            return redirect(url_for('dashboard'))
    
    @app.route('/kat-sorumlusu-siparisler')
    @login_required
    @role_required('depo_sorumlusu')
    def kat_sorumlusu_siparisler():
        """Kat sorumlusu sipariş talepleri sayfası"""
        try:
            from utils.authorization import get_kullanici_otelleri
            
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [otel.id for otel in kullanici_otelleri]
            
            query = KatSorumlusuSiparisTalebi.query.options(
                joinedload(KatSorumlusuSiparisTalebi.kat_sorumlusu).joinedload(Kullanici.otel),
                joinedload(KatSorumlusuSiparisTalebi.detaylar).joinedload(KatSorumlusuSiparisTalepDetay.urun)
            ).join(
                Kullanici, KatSorumlusuSiparisTalebi.kat_sorumlusu_id == Kullanici.id
            ).filter(
                KatSorumlusuSiparisTalebi.durum == 'beklemede'
            )
            
            if otel_ids:
                query = query.filter(Kullanici.otel_id.in_(otel_ids))
            
            siparisler = query.order_by(
                KatSorumlusuSiparisTalebi.talep_tarihi.desc()
            ).limit(DEFAULT_QUERY_LIMIT).all()
            
            # Tüm detaylardaki ürün id'lerini topla ve stokları tek sorguda getir
            tum_urun_ids = set()
            for siparis in siparisler:
                siparis.personel = siparis.kat_sorumlusu
                siparis.detaylar_list = siparis.detaylar if siparis.detaylar else []
                for detay in siparis.detaylar_list:
                    tum_urun_ids.add(detay.urun_id)
            
            stok_map = get_stok_toplamlari(list(tum_urun_ids)) if tum_urun_ids else {}
            
            for siparis in siparisler:
                for detay in siparis.detaylar_list:
                    detay.mevcut_stok = stok_map.get(detay.urun_id, 0)
                    detay.stok_uygun = detay.mevcut_stok >= detay.talep_miktari
                    detay.miktar = detay.talep_miktari
            
            return render_template('depo_sorumlusu/kat_sorumlusu_siparisler.html', 
                                 siparisler=siparisler)
                                 
        except Exception as e:
            log_hata(e, modul='kat_sorumlusu_siparisler')
            flash('Siparişler yüklenirken bir hata oluştu.', 'danger')
            return redirect(url_for('dashboard'))

    @app.route('/api/depo/siparis-kabul/<int:siparis_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def api_depo_siparis_kabul(siparis_id):
        """Kat sorumlusu siparişini kabul et (zimmet onaylama ve stok çıkışı)"""
        try:
            zimmet = db.session.get(PersonelZimmet, siparis_id)
            
            if not zimmet:
                return jsonify({'success': False, 'error': 'Sipariş bulunamadı'}), 404
            
            if zimmet.durum != 'aktif':
                return jsonify({'success': False, 'error': 'Bu sipariş zaten işlenmiş'}), 400
            
            detaylar = PersonelZimmetDetay.query.filter_by(zimmet_id=zimmet.id).all()
            
            # Tüm ürünlerin stok kontrolünü tek sorguda yap
            urun_ids = [detay.urun_id for detay in detaylar]
            stok_toplam = get_stok_toplamlari(urun_ids)
            
            for detay in detaylar:
                mevcut_stok = stok_toplam.get(detay.urun_id, 0)
                
                if mevcut_stok < detay.miktar:
                    urun = db.session.get(Urun, detay.urun_id)
                    urun_adi = urun.urun_adi if urun else 'Bilinmeyen'
                    return jsonify({
                        'success': False,
                        'error': f'{urun_adi} için stok yetersiz! Mevcut: {mevcut_stok}, Talep: {detay.miktar}'
                    }), 400
            
            for detay in detaylar:
                stok_hareket = StokHareket(
                    urun_id=detay.urun_id,
                    hareket_tipi='cikis',
                    miktar=detay.miktar,
                    aciklama=f'Zimmet atama - {zimmet.personel.ad} {zimmet.personel.soyad}',
                    islem_yapan_id=session.get('kullanici_id')
                )
                db.session.add(stok_hareket)
            
            db.session.flush()
            
            # Audit trail — flush sonrası id'ler mevcut
            for detay in detaylar:
                hareket = StokHareket.query.filter_by(
                    urun_id=detay.urun_id,
                    aciklama=f'Zimmet atama - {zimmet.personel.ad} {zimmet.personel.soyad}'
                ).order_by(desc(StokHareket.id)).first()
                if hareket:
                    audit_create('stok_hareket', hareket.id, hareket)
            
            zimmet.teslim_eden_id = session.get('kullanici_id')
            db.session.commit()
            
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
            return jsonify({'success': False, 'error': 'Sipariş kabul sırasında bir hata oluştu'}), 500
    
    @app.route('/api/depo/siparis-iptal/<int:siparis_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def api_depo_siparis_iptal(siparis_id):
        """Kat sorumlusu siparişini iptal et (Sadece bekleyen siparişler)"""
        try:
            zimmet = db.session.get(PersonelZimmet, siparis_id)
            
            if not zimmet:
                return jsonify({'success': False, 'error': 'Sipariş bulunamadı'}), 404
            
            if zimmet.durum != 'aktif':
                return jsonify({'success': False, 'error': 'Sadece bekleyen siparişler iptal edilebilir'}), 400
            
            if zimmet.teslim_eden_id is not None:
                return jsonify({'success': False, 'error': 'Bu bir zimmet kaydıdır, sipariş değil'}), 400
            
            detaylar = PersonelZimmetDetay.query.filter_by(zimmet_id=zimmet.id).all()
            
            zimmet.durum = 'iptal'
            zimmet.iade_tarihi = get_kktc_now()
            
            db.session.commit()
            
            log_islem('iptal', 'kat_sorumlusu_siparis', {
                'siparis_id': zimmet.id,
                'personel_id': zimmet.personel_id,
                'iptal_eden_id': session.get('kullanici_id'),
                'toplam_urun': len(detaylar)
            })
            
            return jsonify({'success': True, 'message': 'Sipariş başarıyla iptal edildi.'})
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='depo_siparis_iptal')
            return jsonify({'success': False, 'error': 'Sipariş iptal sırasında bir hata oluştu'}), 500

    @app.route('/api/depo/kat-sorumlusu-siparis-reddet/<int:talep_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def api_kat_sorumlusu_siparis_reddet(talep_id):
        """Kat sorumlusu sipariş talebini reddet"""
        try:
            talep = db.session.get(KatSorumlusuSiparisTalebi, talep_id)
            if not talep:
                return jsonify({'success': False, 'message': 'Sipariş talebi bulunamadı'}), 404
            
            if talep.durum != 'beklemede':
                return jsonify({'success': False, 'message': f'Sadece bekleyen talepler reddedilebilir. Mevcut durum: {talep.durum}'}), 400
            
            data = request.get_json() or {}
            red_nedeni = data.get('red_nedeni', 'Belirtilmemiş')
            
            talep.durum = 'reddedildi'
            talep.red_nedeni = red_nedeni
            talep.islem_tarihi = get_kktc_now()
            talep.islem_yapan_id = session.get('kullanici_id')
            
            db.session.commit()
            
            log_islem('reddet', 'kat_sorumlusu_siparis_talep', {
                'talep_id': talep.id,
                'kat_sorumlusu_id': talep.kat_sorumlusu_id,
                'red_nedeni': red_nedeni,
                'depo_sorumlusu_id': session.get('kullanici_id')
            })
            
            return jsonify({'success': True, 'message': 'Sipariş talebi başarıyla reddedildi'})
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='kat_sorumlusu_siparis_reddet')
            return jsonify({'success': False, 'message': 'Red işlemi sırasında bir hata oluştu'}), 500
    
    @app.route('/api/depo/kat-sorumlusu-siparis-onayla/<int:talep_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def api_kat_sorumlusu_siparis_onayla(talep_id):
        """Kat sorumlusu sipariş talebini onayla ve zimmet oluştur"""
        try:
            talep = db.session.get(KatSorumlusuSiparisTalebi, talep_id)
            if not talep:
                return jsonify({'success': False, 'message': 'Sipariş talebi bulunamadı'}), 404
            
            if talep.durum != 'beklemede':
                return jsonify({'success': False, 'message': f'Sadece bekleyen talepler onaylanabilir. Mevcut durum: {talep.durum}'}), 400
            
            zimmet = PersonelZimmet(
                personel_id=talep.kat_sorumlusu_id,
                durum='aktif',
                talep_tarihi=get_kktc_now(),
                aciklama=f'Kat sorumlusu sipariş talebinden oluşturuldu (Talep #{talep.id})'
            )
            db.session.add(zimmet)
            db.session.flush()
            
            for detay in talep.detaylar:
                zimmet_detay = PersonelZimmetDetay(
                    zimmet_id=zimmet.id,
                    urun_id=detay.urun_id,
                    miktar=detay.talep_miktari
                )
                db.session.add(zimmet_detay)
            
            talep.durum = 'onaylandi'
            talep.islem_tarihi = get_kktc_now()
            talep.islem_yapan_id = session.get('kullanici_id')
            talep.zimmet_id = zimmet.id
            
            db.session.commit()
            
            log_islem('onayla', 'kat_sorumlusu_siparis_talep', {
                'talep_id': talep.id,
                'kat_sorumlusu_id': talep.kat_sorumlusu_id,
                'zimmet_id': zimmet.id,
                'depo_sorumlusu_id': session.get('kullanici_id')
            })
            
            return jsonify({
                'success': True,
                'message': 'Sipariş talebi onaylandı ve zimmet oluşturuldu',
                'zimmet_id': zimmet.id
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='kat_sorumlusu_siparis_onayla')
            return jsonify({'success': False, 'message': 'Onay işlemi sırasında bir hata oluştu'}), 500

    # ==================== MANUEL RAPOR GÖNDERİM ROUTE'LARI ====================
    
    @app.route('/api/rapor/gorev-tamamlanma-gonder', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def manuel_gorev_raporu_gonder():
        """Manuel görev tamamlanma raporu gönderimi - Tek veya Toplu"""
        try:
            from utils.rapor_email_service import RaporEmailService
            from utils.authorization import get_kullanici_otelleri
            
            data = request.get_json() or {}
            rapor_tarihi_str = data.get('tarih')
            kat_sorumlusu_id = data.get('kat_sorumlusu_id')
            toplu_gonder = data.get('toplu', False)
            
            if rapor_tarihi_str:
                rapor_tarihi = datetime.strptime(rapor_tarihi_str, '%Y-%m-%d').date()
            else:
                rapor_tarihi = get_kktc_now().date() - timedelta(days=1)
            
            if toplu_gonder:
                result = RaporEmailService.send_toplu_gorev_raporu(rapor_tarihi)
                
                log_islem('rapor_gonder', 'toplu_gorev_tamamlanma', {
                    'tarih': rapor_tarihi.isoformat(),
                    'personel_sayisi': result.get('personel_sayisi', 0),
                    'basarili': result.get('success')
                })
                
                return jsonify({
                    'success': result.get('success'),
                    'message': result.get('message'),
                    'toplu': True,
                    'personel_sayisi': result.get('personel_sayisi', 0)
                })
            
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [o.id for o in kullanici_otelleri]
            
            gonderilen = 0
            hatali = 0
            sonuclar = []
            
            if kat_sorumlusu_id:
                ks = db.session.get(Kullanici, kat_sorumlusu_id)
                if ks and ks.rol == 'kat_sorumlusu' and (session.get('rol') == 'sistem_yoneticisi' or ks.otel_id in otel_ids):
                    result = RaporEmailService.send_gorev_raporu(ks.id, rapor_tarihi)
                    if result.get('success'):
                        gonderilen += 1
                        sonuclar.append({'ad': f"{ks.ad} {ks.soyad}", 'durum': 'başarılı'})
                    else:
                        hatali += 1
                        sonuclar.append({'ad': f"{ks.ad} {ks.soyad}", 'durum': result.get('message', 'hata')})
            else:
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
            return jsonify({'success': False, 'message': 'Rapor gönderimi sırasında bir hata oluştu'}), 500
    
    @app.route('/api/rapor/minibar-sarfiyat-gonder', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def manuel_minibar_raporu_gonder():
        """Manuel minibar sarfiyat raporu gönderimi - Tek veya Toplu"""
        try:
            from utils.rapor_email_service import RaporEmailService
            from models import Otel
            from utils.authorization import get_kullanici_otelleri
            
            data = request.get_json() or {}
            rapor_tarihi_str = data.get('tarih')
            otel_id = data.get('otel_id')
            toplu_gonder = data.get('toplu', False)
            
            if rapor_tarihi_str:
                rapor_tarihi = datetime.strptime(rapor_tarihi_str, '%Y-%m-%d').date()
            else:
                rapor_tarihi = get_kktc_now().date() - timedelta(days=1)
            
            if toplu_gonder:
                result = RaporEmailService.send_toplu_minibar_raporu(rapor_tarihi)
                
                log_islem('rapor_gonder', 'toplu_minibar_sarfiyat', {
                    'tarih': rapor_tarihi.isoformat(),
                    'otel_sayisi': result.get('otel_sayisi', 0),
                    'basarili': result.get('success')
                })
                
                return jsonify({
                    'success': result.get('success'),
                    'message': result.get('message'),
                    'toplu': True,
                    'otel_sayisi': result.get('otel_sayisi', 0)
                })
            
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [o.id for o in kullanici_otelleri]
            
            gonderilen = 0
            hatali = 0
            sonuclar = []
            
            if otel_id:
                otel = db.session.get(Otel, otel_id)
                if otel and (session.get('rol') == 'sistem_yoneticisi' or otel.id in otel_ids):
                    result = RaporEmailService.send_minibar_raporu(otel.id, rapor_tarihi)
                    if result.get('success'):
                        gonderilen += 1
                        sonuclar.append({'ad': otel.ad, 'durum': 'başarılı'})
                    else:
                        hatali += 1
                        sonuclar.append({'ad': otel.ad, 'durum': result.get('message', 'hata')})
            else:
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
            return jsonify({'success': False, 'message': 'Minibar raporu gönderimi sırasında bir hata oluştu'}), 500

    # ==================== ANA DEPO TEDARİK ROUTE'LARI ====================
    
    @app.route('/ana-depo-tedarik')
    @login_required
    @role_required('depo_sorumlusu')
    def ana_depo_tedarik():
        """Ana depo tedarik listesi - Ay/Yıl filtreli"""
        from utils.authorization import get_kullanici_otelleri, get_otel_filtreleme_secenekleri
        from calendar import monthrange
        
        try:
            kullanici_otelleri = get_kullanici_otelleri()
            otel_secenekleri = get_otel_filtreleme_secenekleri()
            
            otel_id_param = request.args.get('otel_id', '')
            if otel_id_param == '' or otel_id_param is None:
                secili_otel_id = None
            else:
                try:
                    secili_otel_id = int(otel_id_param)
                except (ValueError, TypeError):
                    secili_otel_id = None
            
            bugun = get_kktc_now()
            secili_ay = request.args.get('ay', type=int, default=bugun.month)
            secili_yil = request.args.get('yil', type=int, default=bugun.year)
            tum_islemler = request.args.get('tum', type=int, default=0)
            
            query = AnaDepoTedarik.query.options(
                joinedload(AnaDepoTedarik.otel),
                joinedload(AnaDepoTedarik.depo_sorumlusu),
                joinedload(AnaDepoTedarik.detaylar).joinedload(AnaDepoTedarikDetay.urun)
            )
            
            otel_ids = [o.id for o in kullanici_otelleri]
            query = query.filter(AnaDepoTedarik.otel_id.in_(otel_ids))
            
            if secili_otel_id:
                query = query.filter(AnaDepoTedarik.otel_id == secili_otel_id)
            
            if not tum_islemler:
                ay_basi = datetime(secili_yil, secili_ay, 1, tzinfo=KKTC_TZ)
                _, son_gun = monthrange(secili_yil, secili_ay)
                ay_sonu = datetime(secili_yil, secili_ay, son_gun, 23, 59, 59, tzinfo=KKTC_TZ)
                query = query.filter(AnaDepoTedarik.islem_tarihi >= ay_basi)
                query = query.filter(AnaDepoTedarik.islem_tarihi <= ay_sonu)
            
            tedarikler = query.order_by(desc(AnaDepoTedarik.islem_tarihi)).all()
            
            urun_gruplari = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            urun_ids = [u.id for u in urunler]
            stok_map = get_stok_toplamlari(urun_ids) if urun_ids else {}
            
            urunler_json = []
            for urun in urunler:
                urunler_json.append({
                    'id': urun.id,
                    'urun_adi': urun.urun_adi,
                    'birim': urun.birim,
                    'grup_id': urun.grup_id,
                    'grup_adi': urun.grup.grup_adi if urun.grup else None,
                    'mevcut_stok': stok_map.get(urun.id, 0),
                    'kritik_stok': urun.kritik_stok_seviyesi or 0
                })
            
            aylar = [
                (1, 'Ocak'), (2, 'Şubat'), (3, 'Mart'), (4, 'Nisan'),
                (5, 'Mayıs'), (6, 'Haziran'), (7, 'Temmuz'), (8, 'Ağustos'),
                (9, 'Eylül'), (10, 'Ekim'), (11, 'Kasım'), (12, 'Aralık')
            ]
            
            yillar = list(range(bugun.year - 2, bugun.year + 1))
            
            return render_template('depo_sorumlusu/ana_depo_tedarik.html',
                                 tedarikler=tedarikler,
                                 urun_gruplari=urun_gruplari,
                                 urunler=urunler,
                                 urunler_json=urunler_json,
                                 stok_map=stok_map,
                                 otel_secenekleri=otel_secenekleri,
                                 secili_otel_id=secili_otel_id,
                                 aylar=aylar,
                                 yillar=yillar,
                                 secili_ay=secili_ay,
                                 secili_yil=secili_yil,
                                 tum_islemler=tum_islemler,
                                 bugun=bugun)
                                 
        except Exception as e:
            log_hata(e, 'ana_depo_tedarik')
            flash('Sayfa yüklenirken bir hata oluştu.', 'danger')
            return redirect(url_for('depo_dashboard'))

    @app.route('/ana-depo-tedarik-tamamla', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def ana_depo_tedarik_tamamla():
        """Ana depodan tedarik işlemini tamamla - FIFO ile"""
        from utils.authorization import get_kullanici_otelleri
        from sqlalchemy import func
        
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Veri bulunamadı'}), 400
            
            urunler = data.get('urunler', [])
            aciklama = data.get('aciklama', '')
            otel_id = data.get('otel_id')
            
            if not urunler:
                return jsonify({'success': False, 'error': 'En az bir ürün seçmelisiniz'}), 400
            
            kullanici_otelleri = get_kullanici_otelleri()
            otel_ids = [o.id for o in kullanici_otelleri]
            
            if not otel_id:
                otel_id = otel_ids[0] if otel_ids else None
            
            if not otel_id or otel_id not in otel_ids:
                return jsonify({'success': False, 'error': 'Geçersiz otel seçimi'}), 400
            
            bugun = get_kktc_now().date()
            bugun_baslangic = datetime.combine(bugun, datetime.min.time())
            bugun_bitis = datetime.combine(bugun, datetime.max.time())
            
            mevcut_tedarik = AnaDepoTedarik.query.filter(
                AnaDepoTedarik.otel_id == otel_id,
                AnaDepoTedarik.depo_sorumlusu_id == session.get('kullanici_id'),
                AnaDepoTedarik.durum == 'aktif',
                AnaDepoTedarik.islem_tarihi >= bugun_baslangic,
                AnaDepoTedarik.islem_tarihi <= bugun_bitis
            ).first()
            
            yeni_kayit = False
            
            if mevcut_tedarik:
                tedarik = mevcut_tedarik
                tedarik_no = tedarik.tedarik_no
            else:
                yeni_kayit = True
                tarih_str = get_kktc_now().strftime('%Y%m%d')
                
                max_retry = 5
                tedarik = None
                
                for retry in range(max_retry):
                    try:
                        son_tedarik = db.session.query(AnaDepoTedarik).filter(
                            AnaDepoTedarik.tedarik_no.like(f'ADT-{tarih_str}-%'),
                            AnaDepoTedarik.otel_id == otel_id
                        ).order_by(desc(AnaDepoTedarik.tedarik_no)).with_for_update().first()
                        
                        if son_tedarik:
                            son_no = int(son_tedarik.tedarik_no.split('-')[-1])
                            yeni_no = son_no + 1
                        else:
                            yeni_no = 1
                        
                        yeni_no += retry
                        
                        tedarik_no = f'ADT-{tarih_str}-{yeni_no:03d}'
                        
                        tedarik = AnaDepoTedarik(
                            tedarik_no=tedarik_no,
                            otel_id=otel_id,
                            depo_sorumlusu_id=session.get('kullanici_id'),
                            aciklama=aciklama,
                            toplam_urun_sayisi=0,
                            toplam_miktar=0,
                            durum='aktif'
                        )
                        db.session.add(tedarik)
                        db.session.flush()
                        break
                        
                    except Exception as retry_exc:
                        exc_msg = str(retry_exc).lower()
                        if 'duplicate key' in exc_msg or 'unique' in exc_msg:
                            db.session.rollback()
                            if retry == max_retry - 1:
                                raise Exception(f'Tedarik numarası oluşturulamadı. Lütfen tekrar deneyin.')
                            continue
                        else:
                            raise
                
                if not tedarik:
                    return jsonify({'success': False, 'error': 'Tedarik kaydı oluşturulamadı'}), 500
            
            eklenen_urun_sayisi = 0
            eklenen_miktar = 0
            
            for urun_data in urunler:
                urun_id = urun_data.get('urun_id')
                miktar = urun_data.get('miktar', 0)
                
                if not urun_id or miktar <= 0:
                    continue
                
                mevcut_detay = AnaDepoTedarikDetay.query.filter_by(
                    tedarik_id=tedarik.id,
                    urun_id=urun_id
                ).first()
                
                if mevcut_detay:
                    mevcut_detay.miktar += miktar
                    detay = mevcut_detay
                    
                    mevcut_fifo = StokFifoKayit.query.filter_by(tedarik_detay_id=detay.id).first()
                    if mevcut_fifo:
                        mevcut_fifo.giris_miktari += miktar
                        mevcut_fifo.kalan_miktar += miktar
                else:
                    detay = AnaDepoTedarikDetay(
                        tedarik_id=tedarik.id,
                        urun_id=urun_id,
                        miktar=miktar
                    )
                    db.session.add(detay)
                    db.session.flush()
                    
                    fifo_kayit = StokFifoKayit(
                        otel_id=otel_id,
                        urun_id=urun_id,
                        tedarik_detay_id=detay.id,
                        giris_miktari=miktar,
                        kalan_miktar=miktar,
                        kullanilan_miktar=0,
                        tukendi=False
                    )
                    db.session.add(fifo_kayit)
                    eklenen_urun_sayisi += 1
                
                stok_hareket = StokHareket(
                    urun_id=urun_id,
                    hareket_tipi='giris',
                    miktar=miktar,
                    aciklama=f'Ana Depo Tedarik - {tedarik_no}',
                    islem_yapan_id=session.get('kullanici_id')
                )
                db.session.add(stok_hareket)
                
                urun_stok = UrunStok.query.filter_by(otel_id=otel_id, urun_id=urun_id).first()
                if urun_stok:
                    urun_stok.mevcut_stok += miktar
                    urun_stok.son_giris_tarihi = get_kktc_now()
                    urun_stok.son_guncelleme_tarihi = get_kktc_now()
                    urun_stok.son_guncelleyen_id = session.get('kullanici_id')
                else:
                    urun_stok = UrunStok(
                        otel_id=otel_id,
                        urun_id=urun_id,
                        mevcut_stok=miktar,
                        son_giris_tarihi=get_kktc_now(),
                        son_guncelleme_tarihi=get_kktc_now(),
                        son_guncelleyen_id=session.get('kullanici_id')
                    )
                    db.session.add(urun_stok)
                
                eklenen_miktar += miktar
            
            tedarik.toplam_urun_sayisi = AnaDepoTedarikDetay.query.filter_by(tedarik_id=tedarik.id).count()
            tedarik.toplam_miktar = db.session.query(func.sum(AnaDepoTedarikDetay.miktar)).filter_by(tedarik_id=tedarik.id).scalar() or 0
            
            db.session.commit()
            
            if yeni_kayit:
                audit_create('ana_depo_tedarik', tedarik.id, tedarik)
                mesaj = f'Tedarik işlemi başarıyla tamamlandı. Tedarik No: {tedarik_no}'
            else:
                audit_update('ana_depo_tedarik', tedarik.id, {}, tedarik)
                mesaj = f'Mevcut tedarike ({tedarik_no}) ürünler eklendi. +{eklenen_miktar} adet'
            
            log_islem('ekleme', 'ana_depo_tedarik', {
                'tedarik_no': tedarik_no,
                'otel_id': otel_id,
                'yeni_kayit': yeni_kayit,
                'eklenen_urun_sayisi': eklenen_urun_sayisi,
                'eklenen_miktar': eklenen_miktar
            })
            
            return jsonify({
                'success': True,
                'message': mesaj,
                'tedarik_no': tedarik_no,
                'tedarik_id': tedarik.id,
                'mevcut_tedarike_eklendi': not yeni_kayit
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'ana_depo_tedarik_tamamla')
            return jsonify({'success': False, 'error': 'Tedarik işlemi sırasında bir hata oluştu'}), 500

    @app.route('/ana-depo-tedarik-iptal/<int:tedarik_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def ana_depo_tedarik_iptal(tedarik_id):
        """Ana depo tedarik işlemini iptal et"""
        
        try:
            tedarik = db.session.get(AnaDepoTedarik, tedarik_id)
            if not tedarik:
                return jsonify({'success': False, 'error': 'Tedarik bulunamadı'}), 404
            
            kullanici_rol = session.get('rol')
            kullanici_id = session.get('kullanici_id')
            
            iptal_edilebilir, hata_mesaji = tedarik.iptal_edilebilir_mi(kullanici_rol, kullanici_id)
            if not iptal_edilebilir:
                return jsonify({'success': False, 'error': hata_mesaji}), 400
            
            data = request.get_json() or {}
            iptal_nedeni = data.get('neden', 'Kullanıcı tarafından iptal edildi')
            
            iptal_edilen_zimmetler = []
            
            for detay in tedarik.detaylar:
                fifo = StokFifoKayit.query.filter_by(tedarik_detay_id=detay.id).first()
                
                if fifo and fifo.kullanilan_miktar > 0:
                    kullanim_kayitlari = StokFifoKullanim.query.filter_by(
                        fifo_kayit_id=fifo.id,
                        islem_tipi='zimmet'
                    ).all()
                    
                    for kullanim in kullanim_kayitlari:
                        zimmet_detay = db.session.get(PersonelZimmetDetay, kullanim.referans_id)
                        if zimmet_detay:
                            zimmet = db.session.get(PersonelZimmet, zimmet_detay.zimmet_id)
                            
                            if zimmet and zimmet.durum == 'aktif':
                                if zimmet_detay.kullanilan_miktar > 0:
                                    return jsonify({
                                        'success': False,
                                        'error': f'Tedarik edilen ürünler minibar işlemlerinde kullanılmış. İptal edilemez.'
                                    }), 400
                                
                                zimmet.durum = 'iptal'
                                zimmet.aciklama = f'Ana Depo Tedarik İptali nedeniyle otomatik iptal - {tedarik.tedarik_no}'
                                
                                for zd in zimmet.detaylar:
                                    stok_iade = StokHareket(
                                        urun_id=zd.urun_id,
                                        hareket_tipi='giris',
                                        miktar=zd.miktar,
                                        aciklama=f'Zimmet İptal İadesi - Tedarik İptali: {tedarik.tedarik_no}',
                                        islem_yapan_id=kullanici_id
                                    )
                                    db.session.add(stok_iade)
                                    
                                    fifo_kullanim = StokFifoKullanim.query.filter_by(
                                        referans_id=zd.id,
                                        islem_tipi='zimmet'
                                    ).first()
                                    if fifo_kullanim:
                                        ilgili_fifo = db.session.get(StokFifoKayit, fifo_kullanim.fifo_kayit_id)
                                        if ilgili_fifo:
                                            ilgili_fifo.kullanilan_miktar -= fifo_kullanim.miktar
                                        db.session.delete(fifo_kullanim)
                                
                                iptal_edilen_zimmetler.append(zimmet.id)
                                
                                log_islem('iptal', 'personel_zimmet', {
                                    'zimmet_id': zimmet.id,
                                    'neden': f'Ana Depo Tedarik İptali: {tedarik.tedarik_no}'
                                })
            
            tedarik_no = tedarik.tedarik_no
            
            for detay in tedarik.detaylar:
                stok_hareket = StokHareket(
                    urun_id=detay.urun_id,
                    hareket_tipi='cikis',
                    miktar=detay.miktar,
                    aciklama=f'Ana Depo Tedarik Silme - {tedarik_no}',
                    islem_yapan_id=kullanici_id
                )
                db.session.add(stok_hareket)
                
                urun_stok = UrunStok.query.filter_by(otel_id=tedarik.otel_id, urun_id=detay.urun_id).first()
                if urun_stok:
                    urun_stok.mevcut_stok = max(0, urun_stok.mevcut_stok - detay.miktar)
                    urun_stok.son_cikis_tarihi = get_kktc_now()
                    urun_stok.son_guncelleme_tarihi = get_kktc_now()
                    urun_stok.son_guncelleyen_id = kullanici_id
                
                StokFifoKayit.query.filter_by(tedarik_detay_id=detay.id).delete()
            
            db.session.delete(tedarik)
            db.session.commit()
            
            mesaj = 'Tedarik işlemi silindi.'
            if iptal_edilen_zimmetler:
                mesaj += f' {len(iptal_edilen_zimmetler)} adet zimmet de otomatik iptal edildi.'
            
            log_islem('silme', 'ana_depo_tedarik', {
                'tedarik_no': tedarik_no,
                'iptal_nedeni': iptal_nedeni,
                'iptal_edilen_zimmetler': iptal_edilen_zimmetler
            })
            
            return jsonify({'success': True, 'message': mesaj})
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'ana_depo_tedarik_iptal')
            return jsonify({'success': False, 'error': 'Tedarik iptal sırasında bir hata oluştu'}), 500

    @app.route('/ana-depo-tedarik-detay-sil/<int:detay_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def ana_depo_tedarik_detay_sil(detay_id):
        """Ana depo tedarik detayından tek ürün sil/iptal et"""
        
        try:
            detay = db.session.get(AnaDepoTedarikDetay, detay_id)
            if not detay:
                return jsonify({'success': False, 'error': 'Detay bulunamadı'}), 404
            
            tedarik = detay.tedarik
            
            if tedarik.durum != 'aktif':
                return jsonify({'success': False, 'error': 'Bu tedarik zaten iptal edilmiş'}), 400
            
            if tedarik.depo_sorumlusu_id != session.get('kullanici_id'):
                return jsonify({'success': False, 'error': 'Sadece kendi işlemlerinizden ürün silebilirsiniz'}), 400
            
            fifo = StokFifoKayit.query.filter_by(tedarik_detay_id=detay.id).first()
            if fifo and fifo.kullanilan_miktar > 0:
                return jsonify({'success': False, 'error': 'Bu ürün zimmetlenmiş, silinemez. Önce zimmeti iptal edin.'}), 400
            
            stok_hareket = StokHareket(
                urun_id=detay.urun_id,
                hareket_tipi='cikis',
                miktar=detay.miktar,
                aciklama=f'Ana Depo Tedarik Detay Silme - {tedarik.tedarik_no}',
                islem_yapan_id=session.get('kullanici_id')
            )
            db.session.add(stok_hareket)
            
            urun_stok = UrunStok.query.filter_by(otel_id=tedarik.otel_id, urun_id=detay.urun_id).first()
            if urun_stok:
                urun_stok.mevcut_stok = max(0, urun_stok.mevcut_stok - detay.miktar)
                urun_stok.son_cikis_tarihi = get_kktc_now()
                urun_stok.son_guncelleme_tarihi = get_kktc_now()
                urun_stok.son_guncelleyen_id = session.get('kullanici_id')
            
            if fifo:
                db.session.delete(fifo)
            
            tedarik.toplam_urun_sayisi -= 1
            tedarik.toplam_miktar -= detay.miktar
            
            db.session.delete(detay)
            
            tedarik_silindi = False
            tedarik_no = tedarik.tedarik_no
            
            if tedarik.toplam_urun_sayisi <= 0:
                db.session.delete(tedarik)
                tedarik_silindi = True
            
            db.session.commit()
            
            log_islem('silme', 'ana_depo_tedarik_detay', {
                'detay_id': detay_id,
                'tedarik_no': tedarik_no,
                'tedarik_silindi': tedarik_silindi
            })
            
            return jsonify({
                'success': True, 
                'message': 'Ürün silindi',
                'tedarik_silindi': tedarik_silindi
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'ana_depo_tedarik_detay_sil')
            return jsonify({'success': False, 'error': 'Detay silme sırasında bir hata oluştu'}), 500
    
    @app.route('/api/ana-depo-tedarik-detay/<int:tedarik_id>')
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi')
    def ana_depo_tedarik_detay_api(tedarik_id):
        """Tedarik detaylarını JSON olarak döndür"""
        
        try:
            tedarik = db.session.get(AnaDepoTedarik, tedarik_id)
            if not tedarik:
                return jsonify({'success': False, 'error': 'Tedarik bulunamadı'}), 404
            
            detaylar = []
            for d in tedarik.detaylar:
                detay_tarihi = d.created_at if d.created_at else tedarik.islem_tarihi
                detaylar.append({
                    'id': d.id,
                    'urun_id': d.urun_id,
                    'urun_adi': d.urun.urun_adi if d.urun else 'Bilinmeyen',
                    'birim': d.urun.birim if d.urun else '',
                    'miktar': d.miktar,
                    'created_at': detay_tarihi.strftime('%d.%m.%Y %H:%M') if detay_tarihi else '-'
                })
            
            return jsonify({
                'success': True,
                'tedarik': {
                    'id': tedarik.id,
                    'tedarik_no': tedarik.tedarik_no,
                    'islem_tarihi': tedarik.islem_tarihi.strftime('%d.%m.%Y %H:%M'),
                    'durum': tedarik.durum,
                    'toplam_urun_sayisi': tedarik.toplam_urun_sayisi,
                    'toplam_miktar': tedarik.toplam_miktar,
                    'aciklama': tedarik.aciklama,
                    'ayni_gun': tedarik.ayni_gun_mu()
                },
                'detaylar': detaylar
            })
            
        except Exception as e:
            log_hata(e, modul='ana_depo_tedarik_detay_api')
            return jsonify({'success': False, 'error': 'Tedarik detayları yüklenirken bir hata oluştu'}), 500

    @app.route('/api/ana-depo-tedarik-bildirim-sayisi')
    @login_required
    @role_required('sistem_yoneticisi')
    def ana_depo_tedarik_bildirim_sayisi():
        """Sistem yöneticisi için görülmemiş tedarik sayısı"""
        
        try:
            sayi = AnaDepoTedarik.query.filter_by(sistem_yoneticisi_goruldu=False).count()
            return jsonify({'success': True, 'sayi': sayi})
        except Exception as e:
            log_hata(e, modul='ana_depo_tedarik_bildirim_sayisi')
            return jsonify({'success': False, 'error': 'Bildirim sayısı alınırken bir hata oluştu'}), 500
