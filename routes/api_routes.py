"""
API Routes Modülü

Bu modül tüm API endpoint'lerini içerir.

Endpoint'ler:
- /api/odalar - Tüm odaları getir
- /api/odalar-by-kat/<int:kat_id> - Kata göre odaları getir
- /api/urun-gruplari - Ürün gruplarını getir
- /api/urunler - Tüm ürünleri getir
- /api/urunler-by-grup/<int:grup_id> - Gruba göre ürünleri getir
- /api/stok-giris - Stok girişi yap
- /api/minibar-islem-kaydet - Minibar işlemi kaydet
- /api/minibar-ilk-dolum - İlk dolum işlemi
- /api/minibar-ilk-dolum-kontrol/<int:oda_id> - İlk dolum kontrolü
- /api/urun-stok/<int:urun_id> - Ürün stok bilgisi
- /api/zimmetim - Kat sorumlusunun zimmet bilgileri
- /api/minibar-icerigi/<int:oda_id> - Minibar içeriği
- /api/minibar-doldur - Minibar doldur
- /api/toplu-oda-mevcut-durum - Toplu oda mevcut durum
- /api/toplu-oda-doldur - Toplu oda doldur
- /api/kat-rapor-veri - Kat bazlı rapor verisi
- /api/son-aktiviteler - Son aktiviteler
- /api/tuketim-trendleri - Tüketim trendleri
- /api/kat-sorumlusu/kritik-seviye-guncelle - Kritik seviye güncelle
- /api/kat-sorumlusu/siparis-kaydet - Sipariş kaydet
- /api/kat-sorumlusu/minibar-urunler - Minibar ürünler
- /api/kat-sorumlusu/yeniden-dolum - Yeniden dolum

Roller:
- sistem_yoneticisi
- admin
- depo_sorumlusu
- kat_sorumlusu
"""

from flask import jsonify, request, session
from datetime import datetime, timedelta
from models import (
    db, Oda, Kat, OdaTipi, UrunGrup, Urun, StokHareket, 
    PersonelZimmet, PersonelZimmetDetay, MinibarIslem, MinibarIslemDetay,
    Kullanici
)
from utils.decorators import login_required, role_required
from utils.helpers import log_islem, log_hata
from utils.audit import audit_create, serialize_model

def register_api_routes(app):
    """API route'larını kaydet"""
    
    # AJAX endpoint - Tüm odaları getir
    @app.route('/api/odalar')
    @login_required
    @role_required('sistem_yoneticisi', 'admin', 'kat_sorumlusu', 'depo_sorumlusu')
    def api_odalar():
        """Tüm aktif odaları getir"""
        try:
            odalar = Oda.query.options(
                db.joinedload(Oda.kat)
            ).filter_by(aktif=True).order_by(Oda.oda_no).all()
            return jsonify([{
                'id': oda.id,
                'oda_no': oda.oda_no,
                'kat_adi': oda.kat.kat_adi
            } for oda in odalar])
        except Exception as e:
            log_hata(e, modul='api_odalar')
            return jsonify({'success': False, 'error': str(e)}), 500

    # AJAX endpoint - Kata göre odaları getir
    @app.route('/api/odalar-by-kat/<int:kat_id>')
    @login_required
    @role_required('kat_sorumlusu', 'sistem_yoneticisi', 'admin')
    def odalar_by_kat(kat_id):
        """Kata göre odaları getir"""
        try:
            odalar = Oda.query.filter_by(kat_id=kat_id, aktif=True).order_by(Oda.oda_no).all()
            return jsonify([{
                'id': oda.id,
                'oda_numarasi': oda.oda_no
            } for oda in odalar])
        except Exception as e:
            log_hata(e, modul='odalar_by_kat')
            return jsonify({'success': False, 'error': str(e)}), 500

    # AJAX endpoint - Ürün gruplarını getir
    @app.route('/api/urun-gruplari')
    @login_required
    @role_required('sistem_yoneticisi', 'admin', 'depo_sorumlusu', 'kat_sorumlusu')
    def api_urun_gruplari():
        """Tüm aktif ürün gruplarını getir"""
        try:
            gruplar = UrunGrup.query.filter_by(aktif=True).order_by(UrunGrup.grup_adi).all()
            return jsonify([{
                'id': grup.id,
                'grup_adi': grup.grup_adi
            } for grup in gruplar])
        except Exception as e:
            log_hata(e, modul='api_urun_gruplari')
            return jsonify({'success': False, 'error': str(e)}), 500

    # AJAX endpoint - Tüm ürünleri getir
    @app.route('/api/urunler')
    @login_required
    @role_required('sistem_yoneticisi', 'admin', 'depo_sorumlusu', 'kat_sorumlusu')
    def api_urunler():
        """Tüm aktif ürünleri stok miktarlarıyla getir"""
        try:
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            # Her ürün için stok miktarını hesapla
            urun_listesi = []
            for urun in urunler:
                giris_toplam = db.session.query(db.func.sum(StokHareket.miktar)).filter(
                    StokHareket.urun_id == urun.id,
                    StokHareket.hareket_tipi.in_(['giris', 'devir', 'sayim'])
                ).scalar() or 0
                
                cikis_toplam = db.session.query(db.func.sum(StokHareket.miktar)).filter(
                    StokHareket.urun_id == urun.id,
                    StokHareket.hareket_tipi == 'cikis'
                ).scalar() or 0
                
                stok_miktari = giris_toplam - cikis_toplam
                
                urun_listesi.append({
                    'id': urun.id,
                    'urun_adi': urun.urun_adi,
                    'grup_adi': urun.grup.grup_adi if urun.grup else '',
                    'birim': urun.birim,
                    'kritik_stok_seviyesi': urun.kritik_stok_seviyesi,
                    'stok_miktari': stok_miktari
                })
            
            return jsonify(urun_listesi)
        except Exception as e:
            log_hata(e, modul='api_urunler')
            return jsonify({'success': False, 'error': str(e)}), 500

    # AJAX endpoint - Gruba göre ürünleri getir
    @app.route('/api/urunler-by-grup/<int:grup_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin', 'depo_sorumlusu', 'kat_sorumlusu')
    def urunler_by_grup(grup_id):
        """Gruba göre ürünleri stok miktarlarıyla getir"""
        try:
            urunler = Urun.query.filter_by(grup_id=grup_id, aktif=True).order_by(Urun.urun_adi).all()
            
            # Her ürün için stok miktarını hesapla
            urun_listesi = []
            for urun in urunler:
                giris_toplam = db.session.query(db.func.sum(StokHareket.miktar)).filter(
                    StokHareket.urun_id == urun.id,
                    StokHareket.hareket_tipi.in_(['giris', 'devir', 'sayim'])
                ).scalar() or 0
                
                cikis_toplam = db.session.query(db.func.sum(StokHareket.miktar)).filter(
                    StokHareket.urun_id == urun.id,
                    StokHareket.hareket_tipi == 'cikis'
                ).scalar() or 0
                
                stok_miktari = giris_toplam - cikis_toplam
                
                urun_listesi.append({
                    'id': urun.id,
                    'urun_adi': urun.urun_adi,
                    'birim': urun.birim,
                    'kritik_stok_seviyesi': urun.kritik_stok_seviyesi,
                    'stok_miktari': stok_miktari
                })
            
            return jsonify(urun_listesi)
        except Exception as e:
            log_hata(e, modul='urunler_by_grup')
            return jsonify({'success': False, 'error': str(e)}), 500

    # AJAX endpoint - Stok girişi yap
    @app.route('/api/stok-giris', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_stok_giris():
        """API üzerinden stok girişi yap"""
        try:
            data = request.get_json()
            
            urun_id = data.get('urun_id')
            miktar = data.get('miktar')
            aciklama = data.get('aciklama', '')
            
            if not urun_id or not miktar:
                return jsonify({'success': False, 'message': 'Ürün ve miktar zorunludur'}), 400
            
            # Ürün kontrolü
            urun = db.session.get(Urun, urun_id)
            if not urun:
                return jsonify({'success': False, 'message': 'Ürün bulunamadı'}), 404
            
            # Stok hareketi oluştur
            hareket = StokHareket(
                urun_id=urun_id,
                hareket_tipi='giris',
                miktar=miktar,
                aciklama=aciklama,
                islem_yapan_id=session['kullanici_id']
            )
            db.session.add(hareket)
            db.session.commit()
            
            # Audit log
            audit_create(
                tablo_adi='stok_hareketleri',
                kayit_id=hareket.id,
                yeni_deger=serialize_model(hareket),
                aciklama='API üzerinden stok girişi'
            )
            
            # Log kaydı
            log_islem('ekleme', 'stok_giris_api', {
                'urun_id': urun_id,
                'miktar': miktar,
                'aciklama': aciklama
            })
            
            return jsonify({
                'success': True,
                'message': 'Stok girişi başarıyla kaydedildi',
                'hareket_id': hareket.id
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_stok_giris')
            return jsonify({'success': False, 'message': str(e)}), 500

    # AJAX endpoint - Minibar işlemi kaydet
    @app.route('/api/minibar-islem-kaydet', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_minibar_islem_kaydet():
        """API üzerinden minibar işlemi kaydet"""
        try:
            data = request.get_json()
            
            oda_id = data.get('oda_id')
            islem_tipi = data.get('islem_tipi')
            aciklama = data.get('aciklama', '')
            detaylar = data.get('detaylar', [])
            
            if not oda_id or not islem_tipi:
                return jsonify({'success': False, 'message': 'Oda ve işlem tipi zorunludur'}), 400
            
            # Oda kontrolü
            oda = db.session.get(Oda, oda_id)
            if not oda:
                return jsonify({'success': False, 'message': 'Oda bulunamadı'}), 404
            
            # Minibar işlemi oluştur
            minibar_islem = MinibarIslem(
                oda_id=oda_id,
                personel_id=session['kullanici_id'],
                islem_tipi=islem_tipi,
                aciklama=aciklama
            )
            db.session.add(minibar_islem)
            db.session.flush()
            
            # Detayları kaydet ve stok hareketleri oluştur
            for detay_data in detaylar:
                urun_id = detay_data.get('urun_id')
                baslangic_stok = detay_data.get('baslangic_stok', 0)
                bitis_stok = detay_data.get('bitis_stok', 0)
                tuketim = detay_data.get('tuketim', 0)
                
                # Minibar işlem detayı
                detay = MinibarIslemDetay(
                    islem_id=minibar_islem.id,
                    urun_id=urun_id,
                    baslangic_stok=baslangic_stok,
                    bitis_stok=bitis_stok,
                    tuketim=tuketim
                )
                db.session.add(detay)
                
                # Tüketim varsa stok hareketi oluştur
                if tuketim > 0:
                    stok_hareket = StokHareket(
                        urun_id=urun_id,
                        hareket_tipi='cikis',
                        miktar=tuketim,
                        aciklama=f'Minibar tüketimi - Oda: {oda.oda_no}',
                        islem_yapan_id=session['kullanici_id']
                    )
                    db.session.add(stok_hareket)
            
            db.session.commit()
            
            # Audit log
            audit_create(
                tablo_adi='minibar_islemleri',
                kayit_id=minibar_islem.id,
                yeni_deger=serialize_model(minibar_islem),
                aciklama='API üzerinden minibar işlemi'
            )
            
            # Log kaydı
            log_islem('ekleme', 'minibar_islem_api', {
                'oda_id': oda_id,
                'islem_tipi': islem_tipi,
                'detay_sayisi': len(detaylar)
            })
            
            return jsonify({
                'success': True,
                'message': 'Minibar işlemi başarıyla kaydedildi',
                'islem_id': minibar_islem.id
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_minibar_islem_kaydet')
            return jsonify({'success': False, 'message': str(e)}), 500

    # AJAX endpoint - İlk Dolum İşlemi (Her oda için sadece bir kez)
    @app.route('/api/minibar-ilk-dolum', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin', 'depo_sorumlusu')
    def api_minibar_ilk_dolum():
        """İlk dolum işlemi - Her oda için sadece bir kez"""
        try:
            data = request.get_json()
            
            oda_id = data.get('oda_id')
            aciklama = data.get('aciklama', '')
            urunler = data.get('urunler', [])  # [{'urun_id': 1, 'miktar': 5}, ...]
            
            if not oda_id:
                return jsonify({'success': False, 'message': 'Oda seçimi zorunludur'}), 400
            
            if not urunler:
                return jsonify({'success': False, 'message': 'En az bir ürün seçmelisiniz'}), 400
            
            # Oda kontrolü
            oda = db.session.get(Oda, oda_id)
            if not oda:
                return jsonify({'success': False, 'message': 'Oda bulunamadı'}), 404
            
            # Bu oda için hangi ürünlere ilk dolum yapılmış kontrol et
            mevcut_ilk_dolumlar = db.session.query(MinibarIslemDetay.urun_id).join(
                MinibarIslem
            ).filter(
                MinibarIslem.oda_id == oda_id,
                MinibarIslem.islem_tipi == 'ilk_dolum'
            ).all()
            
            mevcut_urun_idler = {detay.urun_id for detay in mevcut_ilk_dolumlar}
            
            # Gelen ürünlerden hangilerine daha önce ilk dolum yapılmış kontrol et
            tekrar_urunler = []
            for urun_data in urunler:
                urun_id = urun_data.get('urun_id')
                if urun_id in mevcut_urun_idler:
                    urun = db.session.get(Urun, urun_id)
                    if urun:
                        tekrar_urunler.append(urun.urun_adi)
            
            if tekrar_urunler:
                return jsonify({
                    'success': False,
                    'message': f'Bu oda için şu ürünlere daha önce ilk dolum yapılmış: {", ".join(tekrar_urunler)}'
                }), 400
            
            # Minibar işlemi oluştur
            minibar_islem = MinibarIslem(
                oda_id=oda_id,
                personel_id=session['kullanici_id'],
                islem_tipi='ilk_dolum',
                aciklama=aciklama or 'İlk dolum işlemi'
            )
            db.session.add(minibar_islem)
            db.session.flush()
            
            # Her ürün için detay ve stok hareketi oluştur
            for urun_data in urunler:
                urun_id = urun_data.get('urun_id')
                miktar = urun_data.get('miktar', 0)
                
                if miktar <= 0:
                    continue
                
                # Ürün kontrolü
                urun = db.session.get(Urun, urun_id)
                if not urun:
                    continue
                
                # Depo stok miktarını hesapla
                giris_toplam = db.session.query(db.func.sum(StokHareket.miktar)).filter(
                    StokHareket.urun_id == urun_id,
                    StokHareket.hareket_tipi.in_(['giris', 'devir', 'sayim'])
                ).scalar() or 0
                
                cikis_toplam = db.session.query(db.func.sum(StokHareket.miktar)).filter(
                    StokHareket.urun_id == urun_id,
                    StokHareket.hareket_tipi == 'cikis'
                ).scalar() or 0
                
                mevcut_stok = giris_toplam - cikis_toplam
                
                # Depo stok kontrolü
                if mevcut_stok < miktar:
                    db.session.rollback()
                    return jsonify({
                        'success': False,
                        'message': f'{urun.urun_adi} için yeterli stok yok (Mevcut: {mevcut_stok}, İstenen: {miktar})'
                    }), 400
                
                # Minibar işlem detayı
                detay = MinibarIslemDetay(
                    islem_id=minibar_islem.id,
                    urun_id=urun_id,
                    baslangic_stok=0,
                    bitis_stok=miktar,
                    tuketim=0,
                    eklenen_miktar=miktar
                )
                db.session.add(detay)
                
                # Depodan çıkış hareketi
                stok_hareket = StokHareket(
                    urun_id=urun_id,
                    hareket_tipi='cikis',
                    miktar=miktar,
                    aciklama=f'İlk dolum - Oda: {oda.oda_no}',
                    islem_yapan_id=session['kullanici_id']
                )
                db.session.add(stok_hareket)
            
            db.session.commit()
            
            # Audit log
            audit_create(
                tablo_adi='minibar_islemleri',
                kayit_id=minibar_islem.id,
                yeni_deger=serialize_model(minibar_islem),
                aciklama='İlk dolum işlemi'
            )
            
            # Log kaydı
            log_islem('ekleme', 'minibar_ilk_dolum', {
                'oda_id': oda_id,
                'urun_sayisi': len(urunler)
            })
            
            return jsonify({
                'success': True,
                'message': f'{oda.oda_no} numaralı oda için ilk dolum başarıyla tamamlandı',
                'islem_id': minibar_islem.id
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_minibar_ilk_dolum')
            return jsonify({'success': False, 'message': str(e)}), 500

    # AJAX endpoint - İlk dolum yapılmış ürünleri getir
    @app.route('/api/minibar-ilk-dolum-kontrol/<int:oda_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin', 'depo_sorumlusu')
    def api_minibar_ilk_dolum_kontrol(oda_id):
        """İlk dolum yapılmış ürünleri kontrol et"""
        try:
            # Bu oda için hangi ürünlere ilk dolum yapılmış?
            ilk_dolum_detaylar = db.session.query(
                MinibarIslemDetay.urun_id,
                Urun.urun_adi,
                MinibarIslem.islem_tarihi
            ).join(
                MinibarIslem, MinibarIslemDetay.islem_id == MinibarIslem.id
            ).join(
                Urun, MinibarIslemDetay.urun_id == Urun.id
            ).filter(
                MinibarIslem.oda_id == oda_id,
                MinibarIslem.islem_tipi == 'ilk_dolum'
            ).all()
            
            ilk_dolum_urunler = [
                {
                    'urun_id': detay.urun_id,
                    'urun_adi': detay.urun_adi,
                    'tarih': detay.islem_tarihi.strftime('%d.%m.%Y %H:%M')
                }
                for detay in ilk_dolum_detaylar
            ]
            
            return jsonify({
                'success': True,
                'ilk_dolum_urunler': ilk_dolum_urunler
            })
            
        except Exception as e:
            log_hata(e, modul='api_minibar_ilk_dolum_kontrol')
            return jsonify({'success': False, 'message': str(e)}), 500

    # AJAX endpoint - Ürün stok bilgisini getir
    @app.route('/api/urun-stok/<int:urun_id>')
    @login_required
    @role_required('depo_sorumlusu', 'kat_sorumlusu')
    def urun_stok(urun_id):
        """Ürün stok bilgisini getir"""
        try:
            urun = Urun.query.get_or_404(urun_id)
            
            # Mevcut stok hesapla
            giris_toplam = db.session.query(db.func.sum(StokHareket.miktar)).filter(
                StokHareket.urun_id == urun_id,
                StokHareket.hareket_tipi.in_(['giris', 'devir', 'sayim'])
            ).scalar() or 0
            
            cikis_toplam = db.session.query(db.func.sum(StokHareket.miktar)).filter(
                StokHareket.urun_id == urun_id,
                StokHareket.hareket_tipi == 'cikis'
            ).scalar() or 0
            
            mevcut_stok = giris_toplam - cikis_toplam
            
            return jsonify({
                'urun_adi': urun.urun_adi,
                'birim': urun.birim,
                'grup_adi': urun.grup.grup_adi,
                'kritik_stok_seviyesi': urun.kritik_stok_seviyesi,
                'mevcut_stok': mevcut_stok,
                'stok_durumu': 'Yeterli' if mevcut_stok > urun.kritik_stok_seviyesi else ('Kritik' if mevcut_stok > 0 else 'Tükendi')
            })
        except Exception as e:
            log_hata(e, modul='urun_stok')
            return jsonify({'success': False, 'error': str(e)}), 500

    # AJAX endpoint - Kat sorumlusunun zimmet bilgileri
    @app.route('/api/zimmetim')
    @login_required
    @role_required('kat_sorumlusu')
    def api_zimmetim():
        """Kat sorumlusunun zimmet bilgilerini getir"""
        try:
            kullanici_id = session['kullanici_id']
            
            # Aktif zimmetlerdeki ürünleri getir
            zimmet_detaylar = db.session.query(
                PersonelZimmetDetay.urun_id,
                Urun.urun_adi,
                Urun.birim,
                db.func.sum(PersonelZimmetDetay.miktar).label('toplam_miktar'),
                db.func.sum(PersonelZimmetDetay.kullanilan_miktar).label('kullanilan_miktar'),
                db.func.sum(PersonelZimmetDetay.kalan_miktar).label('kalan_miktar')
            ).join(Urun, PersonelZimmetDetay.urun_id == Urun.id).join(
                PersonelZimmet, PersonelZimmetDetay.zimmet_id == PersonelZimmet.id
            ).filter(
                PersonelZimmet.personel_id == kullanici_id,
                PersonelZimmet.durum == 'aktif'
            ).group_by(PersonelZimmetDetay.urun_id, Urun.urun_adi, Urun.birim).all()
            
            return jsonify([{
                'urun_id': detay.urun_id,
                'urun_adi': detay.urun_adi,
                'birim': detay.birim,
                'toplam_miktar': float(detay.toplam_miktar or 0),
                'kullanilan_miktar': float(detay.kullanilan_miktar or 0),
                'kalan_miktar': float(detay.kalan_miktar or 0)
            } for detay in zimmet_detaylar])
        except Exception as e:
            log_hata(e, modul='api_zimmetim')
            return jsonify({'success': False, 'error': str(e)}), 500

    # AJAX endpoint - Minibar içeriği
    @app.route('/api/minibar-icerigi/<int:oda_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin', 'kat_sorumlusu')
    def api_minibar_icerigi(oda_id):
        """Odanın mevcut minibar içeriğini döndür"""
        try:
            # Son minibar işlemini bul
            son_islem = MinibarIslem.query.filter_by(oda_id=oda_id).order_by(MinibarIslem.id.desc()).first()
            
            if not son_islem:
                return jsonify({'success': True, 'urunler': [], 'ilk_dolum': True})
            
            # Son işlemdeki ürünleri ve miktarlarını getir
            urunler = []
            for detay in son_islem.detaylar:
                urun = db.session.get(Urun, detay.urun_id)
                if urun:
                    # Mevcut stok hesaplama
                    if detay.bitis_stok is not None and detay.bitis_stok >= 0:
                        mevcut_stok = detay.bitis_stok
                    else:
                        mevcut_stok = (detay.baslangic_stok or 0) + (detay.eklenen_miktar or 0) - (detay.tuketim or 0)
                    
                    urunler.append({
                        'urun_id': urun.id,
                        'urun_adi': urun.urun_adi,
                        'grup_adi': urun.grup.grup_adi if urun.grup else '',
                        'birim': urun.birim,
                        'mevcut_stok': mevcut_stok,
                        'son_islem_tarihi': son_islem.islem_tarihi.strftime('%d.%m.%Y %H:%M')
                    })
            
            return jsonify({
                'success': True,
                'urunler': urunler,
                'ilk_dolum': False,
                'son_islem_tipi': son_islem.islem_tipi
            })
            
        except Exception as e:
            log_hata(e, modul='api_minibar_icerigi')
            return jsonify({'success': False, 'error': str(e)}), 500

    # AJAX endpoint - Minibar doldur
    @app.route('/api/minibar-doldur', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_minibar_doldur():
        """Tek bir ürünü minibar'a doldur - Gerçek stok girişi ile"""
        try:
            data = request.get_json()
            oda_id = data.get('oda_id')
            urun_id = data.get('urun_id')
            gercek_mevcut_stok = float(data.get('gercek_mevcut_stok', 0))
            eklenen_miktar = float(data.get('eklenen_miktar', 0))
            islem_tipi = data.get('islem_tipi', 'doldurma')
            kullanici_id = session['kullanici_id']
            
            # Validasyon
            if not oda_id or not urun_id:
                return jsonify({'success': False, 'error': 'Geçersiz parametreler'})
            
            if gercek_mevcut_stok < 0:
                return jsonify({'success': False, 'error': 'Mevcut stok negatif olamaz'})
                
            if eklenen_miktar <= 0:
                return jsonify({'success': False, 'error': 'Eklenecek miktar 0\'dan büyük olmalı'})
            
            urun = db.session.get(Urun, urun_id)
            if not urun:
                return jsonify({'success': False, 'error': 'Ürün bulunamadı'})
            
            # Zimmet kontrolü
            zimmet_detaylar = db.session.query(PersonelZimmetDetay).join(
                PersonelZimmet, PersonelZimmetDetay.zimmet_id == PersonelZimmet.id
            ).filter(
                PersonelZimmet.personel_id == kullanici_id,
                PersonelZimmet.durum == 'aktif',
                PersonelZimmetDetay.urun_id == urun_id
            ).all()
            
            if not zimmet_detaylar:
                return jsonify({'success': False, 'error': f'Zimmetinizde {urun.urun_adi} bulunmuyor'})
            
            toplam_kalan = sum(d.miktar - d.kullanilan_miktar for d in zimmet_detaylar)
            if toplam_kalan < eklenen_miktar:
                return jsonify({'success': False, 'error': f'Yetersiz zimmet! Kalan: {toplam_kalan} {urun.birim}'})
            
            # Son işlemi bul
            son_islem = MinibarIslem.query.filter_by(oda_id=oda_id).order_by(MinibarIslem.id.desc()).first()
            
            if not son_islem:
                return jsonify({'success': False, 'error': 'Bu odada henüz işlem yapılmamış. Önce ilk dolum yapınız.'})
            
            # Son işlemdeki kayıtlı stok
            son_detay = MinibarIslemDetay.query.filter_by(
                islem_id=son_islem.id,
                urun_id=urun_id
            ).first()
            
            if not son_detay:
                return jsonify({'success': False, 'error': 'Bu ürün için kayıt bulunamadı'})
            
            kayitli_stok = son_detay.bitis_stok if son_detay.bitis_stok is not None else 0
            
            # Tüketim hesaplama
            tuketim = max(0, kayitli_stok - gercek_mevcut_stok)
            
            # Yeni stok
            yeni_stok = gercek_mevcut_stok + eklenen_miktar
            
            # Yeni işlem oluştur
            islem = MinibarIslem(
                oda_id=oda_id,
                personel_id=kullanici_id,
                islem_tipi=islem_tipi,
                aciklama=f'Gerçek Sayım: {gercek_mevcut_stok}, Eklenen: {eklenen_miktar}, Tüketim: {tuketim} {urun.birim} {urun.urun_adi}'
            )
            db.session.add(islem)
            db.session.flush()
            
            # Diğer ürünleri kopyala (değişmeden)
            if son_islem:
                for son_detay_item in son_islem.detaylar:
                    if son_detay_item.urun_id != urun_id:
                        mevcut = son_detay_item.bitis_stok if son_detay_item.bitis_stok is not None else 0
                        
                        yeni_detay = MinibarIslemDetay(
                            islem_id=islem.id,
                            urun_id=son_detay_item.urun_id,
                            baslangic_stok=mevcut,
                            bitis_stok=mevcut,
                            tuketim=0,
                            eklenen_miktar=0,
                            zimmet_detay_id=None
                        )
                        db.session.add(yeni_detay)
            
            # Zimmetten düş (FIFO)
            kalan_miktar = eklenen_miktar
            kullanilan_zimmet_id = None
            
            for zimmet_detay in zimmet_detaylar:
                if kalan_miktar <= 0:
                    break
                
                detay_kalan = zimmet_detay.miktar - zimmet_detay.kullanilan_miktar
                if detay_kalan > 0:
                    kullanilacak = min(detay_kalan, kalan_miktar)
                    zimmet_detay.kullanilan_miktar += kullanilacak
                    zimmet_detay.kalan_miktar = zimmet_detay.miktar - zimmet_detay.kullanilan_miktar
                    kalan_miktar -= kullanilacak
                    
                    if not kullanilan_zimmet_id:
                        kullanilan_zimmet_id = zimmet_detay.id
            
            # Eklenen ürün için minibar detayı kaydet
            detay = MinibarIslemDetay(
                islem_id=islem.id,
                urun_id=urun_id,
                baslangic_stok=gercek_mevcut_stok,
                bitis_stok=yeni_stok,
                tuketim=tuketim,
                eklenen_miktar=eklenen_miktar,
                zimmet_detay_id=kullanilan_zimmet_id
            )
            db.session.add(detay)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'✅ Başarılı!\n\nTüketim: {tuketim} {urun.birim}\nEklenen: {eklenen_miktar} {urun.birim}\nYeni Stok: {yeni_stok} {urun.birim}',
                'yeni_stok': yeni_stok,
                'tuketim': tuketim
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_minibar_doldur')
            return jsonify({'success': False, 'error': str(e)}), 500

    # AJAX endpoint - Toplu oda mevcut durum
    @app.route('/api/toplu-oda-mevcut-durum', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_toplu_oda_mevcut_durum():
        """Seçilen odalardaki belirli bir ürünün mevcut stok durumunu döndür"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'error': 'Geçersiz JSON verisi'}), 400
            
            oda_ids = data.get('oda_ids', [])
            urun_id = data.get('urun_id')
            
            if not oda_ids or not urun_id:
                return jsonify({'success': False, 'error': 'Eksik parametreler'}), 400
            
            # Tip dönüşümü
            try:
                urun_id = int(urun_id)
                oda_ids = [int(oid) for oid in oda_ids]
            except (ValueError, TypeError) as e:
                return jsonify({'success': False, 'error': f'Geçersiz parametre tipi: {str(e)}'}), 400
            
            durum_listesi = []
            
            for oda_id in oda_ids:
                oda = db.session.get(Oda, oda_id)
                if not oda:
                    continue
                
                # Son işlemi bul
                son_islem = MinibarIslem.query.filter_by(oda_id=oda_id).order_by(
                    MinibarIslem.id.desc()
                ).first()
                
                mevcut_stok = 0
                if son_islem:
                    son_detay = next((d for d in son_islem.detaylar if d.urun_id == urun_id), None)
                    if son_detay:
                        mevcut_stok = son_detay.bitis_stok if son_detay.bitis_stok is not None else 0
                
                durum_listesi.append({
                    'oda_id': oda_id,
                    'oda_no': oda.oda_no,
                    'mevcut_stok': mevcut_stok
                })
            
            return jsonify({'success': True, 'durum': durum_listesi})
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"Mevcut durum hatası: {error_detail}")
            log_hata(e, modul='api_toplu_oda_mevcut_durum')
            return jsonify({'success': False, 'error': str(e)}), 500

    # AJAX endpoint - Toplu oda doldur
    @app.route('/api/toplu-oda-doldur', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu')
    def api_toplu_oda_doldur():
        """Seçilen odalara toplu olarak ürün doldur"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'error': 'Geçersiz JSON verisi'}), 400
            
            oda_ids = data.get('oda_ids', [])
            urun_id = data.get('urun_id')
            eklenen_miktar = data.get('eklenen_miktar')
            kullanici_id = session.get('kullanici_id')
            
            if not kullanici_id:
                return jsonify({'success': False, 'error': 'Kullanıcı oturumu bulunamadı'}), 401

            # Validasyon ve tip dönüşümü
            if not oda_ids or not urun_id or not eklenen_miktar:
                return jsonify({'success': False, 'error': 'Eksik parametreler'}), 400
            
            try:
                urun_id = int(urun_id)
                oda_ids = [int(oid) for oid in oda_ids]
                eklenen_miktar = float(eklenen_miktar)
            except (ValueError, TypeError) as e:
                return jsonify({'success': False, 'error': f'Geçersiz parametre tipi: {str(e)}'}), 400
            
            if eklenen_miktar <= 0:
                return jsonify({'success': False, 'error': 'Eklenecek miktar 0\'dan büyük olmalıdır'}), 400

            # Ürün bilgisi
            urun = db.session.get(Urun, urun_id)
            if not urun:
                return jsonify({'success': False, 'error': 'Ürün bulunamadı'})

            # Zimmetten toplam gereken miktar
            toplam_gerekli = eklenen_miktar * len(oda_ids)

            # Kullanıcının zimmetini kontrol et
            zimmet_detaylar = db.session.query(PersonelZimmetDetay).join(
                PersonelZimmet, PersonelZimmetDetay.zimmet_id == PersonelZimmet.id
            ).filter(
                PersonelZimmet.personel_id == kullanici_id,
                PersonelZimmet.durum == 'aktif',
                PersonelZimmetDetay.urun_id == urun_id
            ).order_by(PersonelZimmet.zimmet_tarihi).all()

            # Toplam kalan zimmet
            toplam_kalan = sum(detay.miktar - detay.kullanilan_miktar for detay in zimmet_detaylar)

            if toplam_kalan < toplam_gerekli:
                return jsonify({
                    'success': False,
                    'error': f'Zimmetinizde yeterli ürün yok! Gereken: {toplam_gerekli} {urun.birim}, Mevcut: {toplam_kalan} {urun.birim}'
                })

            # Her oda için işlem oluştur
            basarili_odalar = []
            hatali_odalar = []

            for oda_id in oda_ids:
                try:
                    oda = db.session.get(Oda, oda_id)
                    if not oda:
                        hatali_odalar.append({'oda_id': oda_id, 'hata': 'Oda bulunamadı'})
                        continue

                    # Son işlemi bul
                    son_islem = MinibarIslem.query.filter_by(oda_id=oda_id).order_by(
                        MinibarIslem.id.desc()
                    ).first()

                    # Mevcut stok
                    mevcut_stok = 0
                    if son_islem:
                        son_detay = next((d for d in son_islem.detaylar if d.urun_id == urun_id), None)
                        if son_detay:
                            mevcut_stok = son_detay.bitis_stok if son_detay.bitis_stok is not None else 0

                    # Yeni stok
                    yeni_stok = mevcut_stok + eklenen_miktar

                    # Yeni işlem oluştur
                    islem = MinibarIslem(
                        oda_id=oda_id,
                        personel_id=kullanici_id,
                        islem_tipi='doldurma',
                        aciklama=f'TOPLU DOLDURMA - Mevcut: {mevcut_stok}, Eklenen: {eklenen_miktar} {urun.birim} {urun.urun_adi}'
                    )
                    db.session.add(islem)
                    db.session.flush()

                    # Diğer ürünleri kopyala
                    if son_islem:
                        for son_detay_item in son_islem.detaylar:
                            if son_detay_item.urun_id != urun_id:
                                mevcut = son_detay_item.bitis_stok if son_detay_item.bitis_stok is not None else 0
                                yeni_detay = MinibarIslemDetay(
                                    islem_id=islem.id,
                                    urun_id=son_detay_item.urun_id,
                                    baslangic_stok=mevcut,
                                    bitis_stok=mevcut,
                                    tuketim=0,
                                    eklenen_miktar=0,
                                    zimmet_detay_id=son_detay_item.zimmet_detay_id
                                )
                                db.session.add(yeni_detay)

                    # Doldurma detayını ekle
                    doldurma_detay = MinibarIslemDetay(
                        islem_id=islem.id,
                        urun_id=urun_id,
                        baslangic_stok=mevcut_stok,
                        bitis_stok=yeni_stok,
                        tuketim=0,
                        eklenen_miktar=eklenen_miktar,
                        zimmet_detay_id=None
                    )
                    db.session.add(doldurma_detay)

                    # Zimmetten düş (FIFO)
                    kalan_miktar = eklenen_miktar
                    for zimmet_detay in zimmet_detaylar:
                        if kalan_miktar <= 0:
                            break
                        detay_kalan = zimmet_detay.miktar - zimmet_detay.kullanilan_miktar
                        if detay_kalan > 0:
                            kullanilacak = min(detay_kalan, kalan_miktar)
                            zimmet_detay.kullanilan_miktar += kullanilacak
                            zimmet_detay.kalan_miktar = zimmet_detay.miktar - zimmet_detay.kullanilan_miktar
                            kalan_miktar -= kullanilacak

                            if not doldurma_detay.zimmet_detay_id:
                                doldurma_detay.zimmet_detay_id = zimmet_detay.id

                    basarili_odalar.append({'oda_id': oda_id, 'oda_no': oda.oda_no})

                except Exception as oda_hata:
                    hatali_odalar.append({'oda_id': oda_id, 'hata': str(oda_hata)})
                    db.session.rollback()
                    continue

            # Tüm işlemleri kaydet
            if basarili_odalar:
                db.session.commit()
                
                # Audit Trail
                audit_create('minibar_toplu_doldurma', None, {
                    'urun_id': urun_id,
                    'urun_adi': urun.urun_adi,
                    'eklenen_miktar': eklenen_miktar,
                    'oda_sayisi': len(basarili_odalar),
                    'toplam_miktar': toplam_gerekli,
                    'basarili_odalar': [o['oda_no'] for o in basarili_odalar],
                    'islem_tipi': 'toplu_doldurma'
                })

            return jsonify({
                'success': True,
                'basarili_sayisi': len(basarili_odalar),
                'hatali_sayisi': len(hatali_odalar),
                'basarili_odalar': basarili_odalar,
                'hatali_odalar': hatali_odalar,
                'mesaj': f'{len(basarili_odalar)} odaya başarıyla ürün eklendi!'
            })

        except Exception as e:
            db.session.rollback()
            import traceback
            error_detail = traceback.format_exc()
            print(f"Toplu doldurma hatası: {error_detail}")
            log_hata(e, modul='api_toplu_oda_doldur')
            return jsonify({'success': False, 'error': str(e)}), 500

    # AJAX endpoint - Kat rapor verisi
    @app.route('/api/kat-rapor-veri', methods=['GET'])
    @login_required
    @role_required('kat_sorumlusu', 'admin', 'depo_sorumlusu')
    def api_kat_rapor_veri():
        """Kat bazlı rapor verilerini getir"""
        try:
            kat_id = request.args.get('kat_id', type=int)
            baslangic_tarih = request.args.get('baslangic_tarih')
            bitis_tarih = request.args.get('bitis_tarih')

            if not kat_id:
                return jsonify({'success': False, 'error': 'Kat ID gerekli'})

            # Kat bilgisi
            kat = db.session.get(Kat, kat_id)
            if not kat:
                return jsonify({'success': False, 'error': 'Kat bulunamadı'})

            # Kattaki odalar
            odalar = Oda.query.filter_by(kat_id=kat_id, aktif=True).order_by(Oda.oda_no).all()

            if not odalar:
                return jsonify({'success': True, 'kat_adi': kat.kat_adi, 'odalar': [], 'urun_ozeti': []})

            # Tarih filtresi oluştur
            query_filter = []
            if baslangic_tarih:
                query_filter.append(MinibarIslem.islem_tarihi >= baslangic_tarih)
            if bitis_tarih:
                bitis_dt = datetime.strptime(bitis_tarih, '%Y-%m-%d') + timedelta(days=1)
                query_filter.append(MinibarIslem.islem_tarihi < bitis_dt)

            # Her oda için rapor verisi
            oda_raporlari = []
            urun_toplam_tuketim = {}

            for oda in odalar:
                # Son işlem
                son_islem_query = MinibarIslem.query.filter_by(oda_id=oda.id)
                if query_filter:
                    son_islem_query = son_islem_query.filter(*query_filter)
                son_islem = son_islem_query.order_by(MinibarIslem.id.desc()).first()

                oda_veri = {
                    'oda_no': oda.oda_no,
                    'oda_id': oda.id,
                    'son_islem_tarih': son_islem.islem_tarihi.strftime('%d.%m.%Y %H:%M') if son_islem else '-',
                    'urunler': [],
                    'toplam_tuketim_adedi': 0
                }

                if son_islem:
                    for detay in son_islem.detaylar:
                        urun = detay.urun
                        oda_veri['urunler'].append({
                            'urun_adi': urun.urun_adi,
                            'mevcut_stok': detay.bitis_stok or 0,
                            'tuketim': detay.tuketim or 0,
                            'birim': urun.birim
                        })
                        oda_veri['toplam_tuketim_adedi'] += (detay.tuketim or 0)

                        # Ürün toplam tüketim
                        if urun.id not in urun_toplam_tuketim:
                            urun_toplam_tuketim[urun.id] = {
                                'urun_adi': urun.urun_adi,
                                'birim': urun.birim,
                                'toplam': 0
                            }
                        urun_toplam_tuketim[urun.id]['toplam'] += (detay.tuketim or 0)

                oda_raporlari.append(oda_veri)

            # Ürün özeti listesi
            urun_ozeti = [
                {
                    'urun_adi': v['urun_adi'],
                    'toplam_tuketim': v['toplam'],
                    'birim': v['birim']
                }
                for v in urun_toplam_tuketim.values()
            ]

            # Toplam tüketim özeti sırala
            urun_ozeti.sort(key=lambda x: x['toplam_tuketim'], reverse=True)

            return jsonify({
                'success': True,
                'kat_adi': kat.kat_adi,
                'oda_sayisi': len(odalar),
                'odalar': oda_raporlari,
                'urun_ozeti': urun_ozeti
            })

        except Exception as e:
            log_hata(e, modul='api_kat_rapor_veri')
            return jsonify({'success': False, 'error': str(e)}), 500

    # ============================================================================
    # OTEL YÖNETİMİ API
    # ============================================================================
    
    @app.route('/api/oteller/<int:otel_id>/katlar', methods=['GET'])
    @login_required
    def api_otel_katlar(otel_id):
        """Otele ait katları getir"""
        try:
            from models import Otel, Kat
            
            # Otel var mı kontrol et
            otel = Otel.query.get_or_404(otel_id)
            
            # Sadece aktif katları getir
            katlar = Kat.query.filter_by(
                otel_id=otel_id,
                aktif=True
            ).order_by(Kat.kat_no).all()
            
            return jsonify([{
                'id': kat.id,
                'kat_adi': kat.kat_adi,
                'kat_no': kat.kat_no
            } for kat in katlar])
            
        except Exception as e:
            log_hata(e, modul='api_otel_katlar')
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/oteller/<int:otel_id>/odalar', methods=['GET'])
    @login_required
    def api_otel_odalar(otel_id):
        """Otele ait odaları getir"""
        try:
            from models import Otel, Kat, Oda
            
            # Otel var mı kontrol et
            otel = Otel.query.get_or_404(otel_id)
            
            # Otele ait tüm odaları getir (kat üzerinden)
            odalar = db.session.query(Oda).join(Kat).filter(
                Kat.otel_id == otel_id,
                Oda.aktif == True
            ).order_by(Kat.kat_no, Oda.oda_no).all()
            
            return jsonify([{
                'id': oda.id,
                'oda_no': oda.oda_no,
                'kat_id': oda.kat_id,
                'kat_adi': oda.kat.kat_adi
            } for oda in odalar])
            
        except Exception as e:
            log_hata(e, modul='api_otel_odalar')
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/katlar/<int:kat_id>/odalar', methods=['GET'])
    @login_required
    def api_kat_odalar(kat_id):
        """Kata ait odaları getir"""
        try:
            from models import Kat, Oda
            
            # Kat var mı kontrol et
            kat = Kat.query.get_or_404(kat_id)
            
            # Sadece aktif odaları getir
            odalar = Oda.query.filter_by(
                kat_id=kat_id,
                aktif=True
            ).order_by(Oda.oda_no).all()
            
            return jsonify([{
                'id': oda.id,
                'oda_no': oda.oda_no,
                'oda_tipi': oda.oda_tipi_adi,
                'kapasite': oda.kapasite
            } for oda in odalar])
            
        except Exception as e:
            log_hata(e, modul='api_kat_odalar')
            return jsonify({'error': str(e)}), 500
    

    # AJAX endpoint - Kat bilgisini getir (otel_id dahil)
    @app.route('/api/kat-bilgi/<int:kat_id>')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_kat_bilgi(kat_id):
        """Kat bilgisini getir"""
        try:
            from models import Kat
            
            # Kat var mı kontrol et
            kat = Kat.query.get_or_404(kat_id)
            
            return jsonify({
                'success': True,
                'id': kat.id,
                'kat_adi': kat.kat_adi,
                'kat_no': kat.kat_no,
                'otel_id': kat.otel_id,
                'otel_adi': kat.otel.ad if kat.otel else None
            })
            
        except Exception as e:
            log_hata(e, modul='api_kat_bilgi')
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # AJAX endpoint - Otele göre depo sorumlularını getir
    @app.route('/api/oteller/<int:otel_id>/depo-sorumluları')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_otel_depo_sorumluları(otel_id):
        """Otele atanmış depo sorumlularını getir"""
        try:
            from models import Otel, Kullanici, KullaniciOtel
            
            # Otel var mı kontrol et
            otel = Otel.query.get_or_404(otel_id)
            
            # Bu otele atanmış depo sorumlularını getir
            depo_sorumlular = db.session.query(Kullanici).join(
                KullaniciOtel, Kullanici.id == KullaniciOtel.kullanici_id
            ).filter(
                KullaniciOtel.otel_id == otel_id,
                Kullanici.rol == 'depo_sorumlusu',
                Kullanici.aktif == True
            ).order_by(Kullanici.ad, Kullanici.soyad).all()
            
            return jsonify([{
                'id': depo.id,
                'ad': depo.ad,
                'soyad': depo.soyad,
                'kullanici_adi': depo.kullanici_adi
            } for depo in depo_sorumlular])
            
        except Exception as e:
            log_hata(e, modul='api_otel_depo_sorumluları')
            return jsonify({'error': str(e)}), 500

    # AJAX endpoint - Otele göre oda tiplerini getir
    @app.route('/api/oteller/<int:otel_id>/oda-tipleri', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_otel_oda_tipleri(otel_id):
        """Bir oteldeki oda tiplerini getir"""
        try:
            from sqlalchemy import func, distinct
            from models import Otel, Kat, Oda, OdaTipi
            
            # Otel kontrolü
            otel = Otel.query.get_or_404(otel_id)
            
            # Otele ait tüm oda tiplerini getir (OdaTipi tablosundan)
            oda_tipleri_query = db.session.query(OdaTipi).join(
                Oda, Oda.oda_tipi_id == OdaTipi.id
            ).join(
                Kat, Oda.kat_id == Kat.id
            ).filter(
                Kat.otel_id == otel_id,
                Oda.aktif == True
            ).distinct().order_by(OdaTipi.ad).all()
            
            # Oda tiplerini liste olarak döndür
            oda_tipleri_list = []
            for oda_tipi in oda_tipleri_query:
                oda_tipleri_list.append({
                    'id': oda_tipi.id,
                    'ad': oda_tipi.ad,
                    'dolap_sayisi': oda_tipi.dolap_sayisi,
                    'setup': oda_tipi.setup
                })
            
            return jsonify({
                'success': True,
                'oda_tipleri': oda_tipleri_list
            })
            
        except Exception as e:
            log_hata(e, modul='api_otel_oda_tipleri')
            return jsonify({
                'success': False,
                'error': str(e),
                'oda_tipleri': []
            }), 500

    # AJAX endpoint - Yeni oda ekle
    @app.route('/api/oda-ekle', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_oda_ekle():
        """AJAX ile yeni oda ekle"""
        try:
            from models import Oda, Kat, Otel
            from utils.audit import audit_create, serialize_model
            
            data = request.get_json()
            
            # Zorunlu alanları kontrol et
            if not data.get('otel_id'):
                return jsonify({
                    'success': False,
                    'error': 'Otel seçimi zorunludur!'
                }), 400
            
            if not data.get('kat_id'):
                return jsonify({
                    'success': False,
                    'error': 'Kat seçimi zorunludur!'
                }), 400
            
            if not data.get('oda_no'):
                return jsonify({
                    'success': False,
                    'error': 'Oda numarası zorunludur!'
                }), 400
            
            # Kat'ın seçilen otele ait olduğunu kontrol et
            kat = Kat.query.get(data['kat_id'])
            if not kat:
                return jsonify({
                    'success': False,
                    'error': 'Seçilen kat bulunamadı!'
                }), 404
            
            if kat.otel_id != int(data['otel_id']):
                return jsonify({
                    'success': False,
                    'error': 'Seçilen kat, seçilen otele ait değil!'
                }), 400
            
            # Aynı oda numarası var mı kontrol et
            mevcut_oda = Oda.query.filter_by(oda_no=data['oda_no']).first()
            if mevcut_oda:
                return jsonify({
                    'success': False,
                    'error': f'Bu oda numarası ({data["oda_no"]}) zaten kullanılıyor!'
                }), 400
            
            # Yeni oda oluştur
            oda = Oda(
                oda_no=data['oda_no'],
                kat_id=data['kat_id'],
                oda_tipi=data.get('oda_tipi', ''),
                kapasite=data.get('kapasite'),
                aktif=True
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
                'kat_id': oda.kat_id,
                'oda_tipi': oda.oda_tipi
            })
            
            return jsonify({
                'success': True,
                'message': f'Oda {oda.oda_no} başarıyla eklendi.',
                'oda': {
                    'id': oda.id,
                    'oda_no': oda.oda_no,
                    'kat_id': oda.kat_id,
                    'oda_tipi': oda.oda_tipi_adi,
                    'kapasite': oda.kapasite
                }
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_oda_ekle')
            return jsonify({
                'success': False,
                'error': f'Oda eklenirken hata oluştu: {str(e)}'
            }), 500

    # AJAX endpoint - Oda bilgilerini getir
    @app.route('/api/odalar/<int:oda_id>', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_oda_bilgi(oda_id):
        """Oda bilgilerini getir"""
        try:
            from models import Oda, Kat
            
            oda = Oda.query.get_or_404(oda_id)
            kat = Kat.query.get(oda.kat_id)
            
            return jsonify({
                'success': True,
                'oda': {
                    'id': oda.id,
                    'oda_no': oda.oda_no,
                    'kat_id': oda.kat_id,
                    'otel_id': kat.otel_id if kat else None,
                    'oda_tipi': oda.oda_tipi_adi,
                    'kapasite': oda.kapasite,
                    'aktif': oda.aktif
                }
            })
            
        except Exception as e:
            log_hata(e, modul='api_oda_bilgi')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # AJAX endpoint - Oda güncelle
    @app.route('/api/oda-guncelle/<int:oda_id>', methods=['PUT'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_oda_guncelle(oda_id):
        """AJAX ile oda güncelle"""
        try:
            from models import Oda, Kat
            from utils.audit import audit_create, serialize_model
            
            data = request.get_json()
            
            # Odayı bul
            oda = Oda.query.get_or_404(oda_id)
            
            # Eski değerleri kaydet (audit için)
            eski_deger = serialize_model(oda)
            
            # Zorunlu alanları kontrol et
            if not data.get('otel_id'):
                return jsonify({
                    'success': False,
                    'error': 'Otel seçimi zorunludur!'
                }), 400
            
            if not data.get('kat_id'):
                return jsonify({
                    'success': False,
                    'error': 'Kat seçimi zorunludur!'
                }), 400
            
            if not data.get('oda_no'):
                return jsonify({
                    'success': False,
                    'error': 'Oda numarası zorunludur!'
                }), 400
            
            # Kat'ın seçilen otele ait olduğunu kontrol et
            kat = Kat.query.get(data['kat_id'])
            if not kat:
                return jsonify({
                    'success': False,
                    'error': 'Seçilen kat bulunamadı!'
                }), 404
            
            if kat.otel_id != int(data['otel_id']):
                return jsonify({
                    'success': False,
                    'error': 'Seçilen kat, seçilen otele ait değil!'
                }), 400
            
            # Aynı oda numarası başka bir odada var mı kontrol et
            mevcut_oda = Oda.query.filter(
                Oda.oda_no == data['oda_no'],
                Oda.id != oda_id
            ).first()
            
            if mevcut_oda:
                return jsonify({
                    'success': False,
                    'error': f'Bu oda numarası ({data["oda_no"]}) başka bir oda tarafından kullanılıyor!'
                }), 400
            
            # Oda bilgilerini güncelle
            oda.oda_no = data['oda_no']
            oda.kat_id = data['kat_id']
            oda.oda_tipi = data.get('oda_tipi', '')
            oda.kapasite = data.get('kapasite')
            
            # Audit log
            audit_create(
                tablo_adi='odalar',
                kayit_id=oda.id,
                eski_deger=eski_deger,
                yeni_deger=serialize_model(oda),
                aciklama=f'Oda güncellendi - {oda.oda_no}'
            )
            
            db.session.commit()
            
            # Log kaydı
            log_islem('guncelleme', 'oda', {
                'oda_id': oda.id,
                'oda_no': oda.oda_no,
                'kat_id': oda.kat_id,
                'oda_tipi': oda.oda_tipi
            })
            
            return jsonify({
                'success': True,
                'message': f'Oda {oda.oda_no} başarıyla güncellendi.',
                'oda': {
                    'id': oda.id,
                    'oda_no': oda.oda_no,
                    'kat_id': oda.kat_id,
                    'oda_tipi': oda.oda_tipi_adi,
                    'kapasite': oda.kapasite
                }
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_oda_guncelle')
            return jsonify({
                'success': False,
                'error': f'Oda güncellenirken hata oluştu: {str(e)}'
            }), 500
