"""
Admin Zimmet Route'ları

Bu modül admin zimmet yönetimi ile ilgili endpoint'leri içerir.

Endpoint'ler:
- /admin/personel-zimmetleri - Personel zimmet kayıtlarını listeleme
- /admin/zimmet-detay/<int:zimmet_id> - Zimmet detaylarını görüntüleme
- /admin/zimmet-iade/<int:zimmet_id> - Zimmet iade işlemi
- /admin/zimmet-iptal/<int:zimmet_id> - Zimmet iptal işlemi

Roller:
- sistem_yoneticisi
- admin
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify
from models import db, PersonelZimmet, PersonelZimmetDetay, Kullanici, StokHareket
from utils.decorators import login_required, role_required
from utils.helpers import log_islem, log_hata
from utils.audit import serialize_model, audit_update


def register_admin_zimmet_routes(app):
    """Admin zimmet route'larını kaydet"""
    
    @app.route('/admin/personel-zimmetleri')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_personel_zimmetleri():
        """Tüm personel zimmet kayıtlarını listele"""
        try:
            # Filtreler
            personel_id = request.args.get('personel_id', type=int)
            durum = request.args.get('durum', '')
            
            # Sayfalama
            sayfa = request.args.get('sayfa', 1, type=int)
            per_page = 50
            
            # Sorgu oluştur
            query = PersonelZimmet.query.options(
                db.joinedload(PersonelZimmet.personel),
                db.joinedload(PersonelZimmet.teslim_eden),
                db.joinedload(PersonelZimmet.detaylar).joinedload(PersonelZimmetDetay.urun)
            )
            
            if personel_id:
                query = query.filter(PersonelZimmet.personel_id == personel_id)
            if durum:
                query = query.filter(PersonelZimmet.durum == durum)
            
            # Sayfalama
            zimmetler = query.order_by(PersonelZimmet.zimmet_tarihi.desc()).paginate(
                page=sayfa, per_page=per_page, error_out=False
            )
            
            # Personeller (filtre için)
            personeller = Kullanici.query.filter(
                Kullanici.rol.in_(['depo_sorumlusu', 'kat_sorumlusu']),
                Kullanici.aktif.is_(True)
            ).order_by(Kullanici.ad, Kullanici.soyad).all()
            
            # Log kaydı
            log_islem('goruntuleme', 'personel_zimmetleri', {
                'sayfa': sayfa,
                'kayit_sayisi': zimmetler.total
            })
            
            return render_template('sistem_yoneticisi/admin_personel_zimmetleri.html',
                                 zimmetler=zimmetler,
                                 personeller=personeller,
                                 personel_id=personel_id,
                                 durum=durum)
            
        except Exception as e:
            log_hata(e, modul='admin_personel_zimmetleri')
            flash('Zimmet kayıtları yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('sistem_yoneticisi_dashboard'))

    @app.route('/admin/zimmet-detay/<int:zimmet_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_zimmet_detay(zimmet_id):
        """Zimmet detaylarını görüntüle"""
        try:
            zimmet = db.session.get(PersonelZimmet, zimmet_id)
            if not zimmet:
                flash('Zimmet kaydı bulunamadı.', 'danger')
                return redirect(url_for('admin_personel_zimmetleri'))
            
            # Detayları eager load ile getir
            zimmet = PersonelZimmet.query.options(
                db.joinedload(PersonelZimmet.personel),
                db.joinedload(PersonelZimmet.teslim_eden),
                db.joinedload(PersonelZimmet.detaylar).joinedload(PersonelZimmetDetay.urun)
            ).get(zimmet_id)
            
            # Log kaydı
            log_islem('goruntuleme', 'zimmet_detay', {
                'zimmet_id': zimmet_id,
                'personel_id': zimmet.personel_id
            })
            
            return render_template('sistem_yoneticisi/admin_zimmet_detay.html',
                                 zimmet=zimmet)
            
        except Exception as e:
            log_hata(e, modul='admin_zimmet_detay')
            flash('Zimmet detayları yüklenirken hata oluştu.', 'danger')
            return redirect(url_for('admin_personel_zimmetleri'))

    @app.route('/admin/zimmet-iade/<int:zimmet_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_zimmet_iade(zimmet_id):
        """Zimmet iade işlemi"""
        try:
            zimmet = db.session.get(PersonelZimmet, zimmet_id)
            if not zimmet:
                return jsonify({'success': False, 'message': 'Zimmet bulunamadı'}), 404
            
            if zimmet.durum != 'aktif':
                return jsonify({'success': False, 'message': 'Sadece aktif zimmetler iade edilebilir'}), 400
            
            # İade edilen miktarları al
            data = request.get_json()
            iade_miktarlari = data.get('iade_miktarlari', {})
            
            # Her detay için iade işlemi
            for detay in zimmet.detaylar:
                detay_id = str(detay.id)
                if detay_id in iade_miktarlari:
                    iade_miktar = int(iade_miktarlari[detay_id])
                    if iade_miktar > 0:
                        # İade miktarını güncelle
                        detay.iade_edilen_miktar += iade_miktar
                        detay.kalan_miktar = detay.miktar - detay.kullanilan_miktar - detay.iade_edilen_miktar
                        
                        # Stok hareketine ekle
                        hareket = StokHareket(
                            urun_id=detay.urun_id,
                            hareket_tipi='giris',
                            miktar=iade_miktar,
                            aciklama=f'Zimmet iadesi - {zimmet.personel.ad} {zimmet.personel.soyad}',
                            islem_yapan_id=session['kullanici_id']
                        )
                        db.session.add(hareket)
            
            # Zimmet durumunu güncelle
            zimmet.durum = 'tamamlandi'
            db.session.commit()
            
            # Audit log
            audit_update(
                tablo_adi='personel_zimmet',
                kayit_id=zimmet_id,
                eski_deger={'durum': 'aktif'},
                yeni_deger={'durum': 'tamamlandi'},
                aciklama='Admin zimmet iade işlemi'
            )
            
            # Log kaydı
            log_islem('guncelleme', 'zimmet_iade', {
                'zimmet_id': zimmet_id,
                'personel_id': zimmet.personel_id
            })
            
            flash('Zimmet iade işlemi başarıyla tamamlandı.', 'success')
            return jsonify({'success': True, 'message': 'İade işlemi tamamlandı'})
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='admin_zimmet_iade')
            return jsonify({'success': False, 'message': 'İade işlemi başarısız'}), 500

    @app.route('/admin/zimmet-iptal/<int:zimmet_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def admin_zimmet_iptal(zimmet_id):
        """Zimmet kaydını iptal et - FIFO kayıtlarını geri al"""
        try:
            from models import UrunStok, StokFifoKayit, StokFifoKullanim
            
            zimmet = db.session.get(PersonelZimmet, zimmet_id)
            if not zimmet:
                return jsonify({'success': False, 'message': 'Zimmet bulunamadı'}), 404
            
            if zimmet.durum != 'aktif':
                return jsonify({'success': False, 'message': 'Sadece aktif zimmetler iptal edilebilir'}), 400
            
            # Eski değeri sakla
            eski_deger = serialize_model(zimmet)
            otel_id = zimmet.personel.otel_id if zimmet.personel else None
            
            # Stok hareketlerini ve FIFO kayıtlarını geri al
            for detay in zimmet.detaylar:
                # Kullanılmayan miktarı depoya geri ekle
                geri_alinacak = detay.miktar - detay.kullanilan_miktar - detay.iade_edilen_miktar
                if geri_alinacak > 0:
                    # Stok hareketi
                    hareket = StokHareket(
                        urun_id=detay.urun_id,
                        hareket_tipi='giris',
                        miktar=geri_alinacak,
                        aciklama=f'Zimmet iptali - {zimmet.personel.ad} {zimmet.personel.soyad}',
                        islem_yapan_id=session['kullanici_id']
                    )
                    db.session.add(hareket)
                    
                    # UrunStok güncelle
                    urun_stok = UrunStok.query.filter_by(otel_id=otel_id, urun_id=detay.urun_id).first()
                    if urun_stok:
                        urun_stok.mevcut_stok += geri_alinacak
                        urun_stok.son_giris_tarihi = get_kktc_now()
                        urun_stok.son_guncelleyen_id = session['kullanici_id']
                
                # FIFO kullanım kayıtlarını geri al
                fifo_kullanimlar = StokFifoKullanim.query.filter_by(
                    referans_id=detay.id,
                    islem_tipi='zimmet'
                ).all()
                
                for kullanim in fifo_kullanimlar:
                    fifo_kayit = db.session.get(StokFifoKayit, kullanim.fifo_kayit_id)
                    if fifo_kayit:
                        fifo_kayit.kalan_miktar += kullanim.miktar
                        fifo_kayit.kullanilan_miktar -= kullanim.miktar
                        fifo_kayit.tukendi = False
                    db.session.delete(kullanim)
            
            # Zimmet durumunu iptal et
            zimmet.durum = 'iptal'
            db.session.commit()
            
            # Audit log
            audit_update(
                tablo_adi='personel_zimmet',
                kayit_id=zimmet_id,
                eski_deger=eski_deger,
                yeni_deger=serialize_model(zimmet),
                aciklama='Admin zimmet iptal işlemi'
            )
            
            # Log kaydı
            log_islem('guncelleme', 'zimmet_iptal', {
                'zimmet_id': zimmet_id,
                'personel_id': zimmet.personel_id
            })
            
            flash('Zimmet kaydı başarıyla iptal edildi.', 'success')
            return jsonify({'success': True, 'message': 'Zimmet iptal edildi, stoklar geri eklendi'})
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='admin_zimmet_iptal')
            return jsonify({'success': False, 'message': 'İptal işlemi başarısız'}), 500
