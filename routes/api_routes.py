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
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')

def get_kktc_now():
    """Kıbrıs saat diliminde şu anki zamanı döndürür."""
    return datetime.now(KKTC_TZ)

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
    
    # CSRF protection instance'ını al
    csrf = app.extensions.get('csrf')
    
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
            
            # Kritik seviye kontrolü (None ise varsayılan 10)
            kritik_seviye = urun.kritik_stok_seviyesi if urun.kritik_stok_seviyesi is not None else 10
            
            # Stok durumu
            if mevcut_stok > kritik_seviye:
                stok_durumu = 'Yeterli'
            elif mevcut_stok > 0:
                stok_durumu = 'Kritik'
            else:
                stok_durumu = 'Tükendi'
            
            return jsonify({
                'urun_adi': urun.urun_adi,
                'birim': urun.birim,
                'grup_adi': urun.grup.grup_adi,
                'kritik_stok_seviyesi': kritik_seviye,
                'mevcut_stok': mevcut_stok,
                'stok_durumu': stok_durumu
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
        """Tek bir ürünü minibar'a doldur - Otel bazlı zimmet sistemi ile"""
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
            
            # Otel bazlı zimmet kontrolü
            from utils.otel_zimmet_servisleri import OtelZimmetServisi, OtelZimmetStokYetersizError
            
            personel = Kullanici.query.get(kullanici_id)
            if not personel or not personel.otel_id:
                return jsonify({'success': False, 'error': 'Otel atamanız bulunamadı'})
            
            otel_id = personel.otel_id
            
            # Otel zimmet stoğunu kontrol et
            otel_stok = OtelZimmetServisi.get_otel_zimmet_stok(otel_id, urun_id)
            
            if not otel_stok:
                return jsonify({'success': False, 'error': f'Otel zimmet deposunda {urun.urun_adi} bulunmuyor'})
            
            if otel_stok.kalan_miktar < eklenen_miktar:
                return jsonify({'success': False, 'error': f'Yetersiz zimmet! Kalan: {otel_stok.kalan_miktar} {urun.birim}'})
            
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
            
            # Oda bilgisini al
            oda = Oda.query.get(oda_id)
            
            # Otel zimmet stoğundan düş ve kullanım kaydı oluştur
            otel_stok_updated, kullanim = OtelZimmetServisi.stok_dusu(
                otel_id=otel_id,
                urun_id=urun_id,
                miktar=int(eklenen_miktar),
                personel_id=kullanici_id,
                islem_tipi='minibar_kullanim',
                aciklama=f'Minibar doldurma - Oda: {oda.oda_no if oda else oda_id}'
            )
            
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
            
            # Eklenen ürün için minibar detayı kaydet
            detay = MinibarIslemDetay(
                islem_id=islem.id,
                urun_id=urun_id,
                baslangic_stok=gercek_mevcut_stok,
                bitis_stok=yeni_stok,
                tuketim=tuketim,
                eklenen_miktar=eklenen_miktar,
                zimmet_detay_id=None  # Artık otel bazlı sistem kullanılıyor
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
        """Seçilen odalara toplu olarak ürün doldur - Otel bazlı zimmet sistemi ile"""
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

            # Otel bazlı zimmet kontrolü
            from utils.otel_zimmet_servisleri import OtelZimmetServisi, OtelZimmetStokYetersizError
            
            personel = Kullanici.query.get(kullanici_id)
            if not personel or not personel.otel_id:
                return jsonify({'success': False, 'error': 'Otel atamanız bulunamadı'})
            
            otel_id = personel.otel_id
            
            # Otel zimmet stoğunu kontrol et
            otel_stok = OtelZimmetServisi.get_otel_zimmet_stok(otel_id, urun_id)
            
            if not otel_stok:
                return jsonify({'success': False, 'error': f'Otel zimmet deposunda {urun.urun_adi} bulunmuyor'})
            
            if otel_stok.kalan_miktar < toplam_gerekli:
                return jsonify({
                    'success': False,
                    'error': f'Otel zimmet deposunda yeterli ürün yok! Gereken: {toplam_gerekli} {urun.birim}, Mevcut: {otel_stok.kalan_miktar} {urun.birim}'
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
                    
                    # Otel zimmet stoğundan düş ve kullanım kaydı oluştur
                    otel_stok_updated, kullanim = OtelZimmetServisi.stok_dusu(
                        otel_id=otel_id,
                        urun_id=urun_id,
                        miktar=int(eklenen_miktar),
                        personel_id=kullanici_id,
                        islem_tipi='minibar_kullanim',
                        aciklama=f'Toplu doldurma - Oda: {oda.oda_no}'
                    )

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
                                    zimmet_detay_id=None  # Artık otel bazlı sistem
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
                        zimmet_detay_id=None  # Artık otel bazlı sistem
                    )
                    db.session.add(doldurma_detay)

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
                # Tarih aralığındaki tüm işlemleri al
                islemler_query = MinibarIslem.query.filter_by(oda_id=oda.id).filter(
                    MinibarIslem.islem_tipi.in_(['setup_kontrol', 'ekstra_tuketim'])
                )
                if query_filter:
                    islemler_query = islemler_query.filter(*query_filter)
                islemler = islemler_query.order_by(MinibarIslem.islem_tarihi.desc()).all()

                # Son işlem tarihi
                son_islem = islemler[0] if islemler else None

                oda_veri = {
                    'oda_no': oda.oda_no,
                    'oda_id': oda.id,
                    'son_islem_tarih': son_islem.islem_tarihi.strftime('%d.%m.%Y %H:%M') if son_islem else '-',
                    'urunler': [],
                    'toplam_tuketim_adedi': 0
                }

                # Ürün bazında toplam tüketim hesapla
                urun_tuketim_map = {}
                
                for islem in islemler:
                    for detay in islem.detaylar:
                        if detay.tuketim and detay.tuketim > 0:
                            urun = detay.urun
                            if urun.id not in urun_tuketim_map:
                                urun_tuketim_map[urun.id] = {
                                    'urun_adi': urun.urun_adi,
                                    'birim': urun.birim,
                                    'tuketim': 0,
                                    'son_stok': detay.bitis_stok or 0
                                }
                            urun_tuketim_map[urun.id]['tuketim'] += detay.tuketim
                            # En son stok bilgisini güncelle
                            if islem == son_islem:
                                urun_tuketim_map[urun.id]['son_stok'] = detay.bitis_stok or 0

                # Oda verilerine ekle
                for urun_id, urun_data in urun_tuketim_map.items():
                    oda_veri['urunler'].append({
                        'urun_adi': urun_data['urun_adi'],
                        'mevcut_stok': urun_data['son_stok'],
                        'tuketim': urun_data['tuketim'],
                        'birim': urun_data['birim']
                    })
                    oda_veri['toplam_tuketim_adedi'] += urun_data['tuketim']

                    # Kat geneli ürün toplam tüketim
                    if urun_id not in urun_toplam_tuketim:
                        urun_toplam_tuketim[urun_id] = {
                            'urun_adi': urun_data['urun_adi'],
                            'birim': urun_data['birim'],
                            'toplam': 0
                        }
                    urun_toplam_tuketim[urun_id]['toplam'] += urun_data['tuketim']

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
            
            return jsonify({
                'success': True,
                'odalar': [{
                    'id': oda.id,
                    'oda_no': oda.oda_no,
                    'oda_tipi': oda.oda_tipi_adi,
                    'kapasite': oda.kapasite
                } for oda in odalar]
            })
            
        except Exception as e:
            log_hata(e, modul='api_kat_odalar')
            return jsonify({'success': False, 'error': str(e)}), 500
    

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
        """Bir oteldeki oda tiplerini kat bazında getir"""
        try:
            from sqlalchemy import func
            from models import Otel, Kat, Oda, OdaTipi
            
            # Otel kontrolü
            otel = Otel.query.get_or_404(otel_id)
            
            # Kat bazlı oda tiplerini grupla
            kat_bazli = {}
            toplam_oda = 0
            
            # Otele ait katları al
            katlar = Kat.query.filter_by(otel_id=otel_id, aktif=True).order_by(Kat.kat_no).all()
            
            for kat in katlar:
                # Bu kattaki oda tiplerini grupla ve say
                oda_tipleri = db.session.query(
                    OdaTipi.ad,
                    func.count(Oda.id).label('sayi')
                ).join(
                    Oda, Oda.oda_tipi_id == OdaTipi.id
                ).filter(
                    Oda.kat_id == kat.id,
                    Oda.aktif == True
                ).group_by(
                    OdaTipi.ad
                ).order_by(
                    func.count(Oda.id).desc()
                ).all()
                
                if oda_tipleri:
                    kat_oda_sayisi = sum([sayi for _, sayi in oda_tipleri])
                    toplam_oda += kat_oda_sayisi
                    
                    kat_bazli[kat.kat_adi] = {
                        'kat_id': kat.id,
                        'kat_no': kat.kat_no,
                        'toplam_oda': kat_oda_sayisi,
                        'oda_tipleri': [
                            {
                                'oda_tipi': oda_tipi if oda_tipi else 'Belirtilmemiş',
                                'sayi': sayi
                            }
                            for oda_tipi, sayi in oda_tipleri
                        ]
                    }
            
            return jsonify({
                'success': True,
                'kat_bazli': kat_bazli,
                'toplam_oda': toplam_oda,
                'otel': {
                    'id': otel.id,
                    'ad': otel.ad
                }
            })
            
        except Exception as e:
            log_hata(e, modul='api_otel_oda_tipleri')
            return jsonify({
                'success': False,
                'error': str(e),
                'kat_bazli': {},
                'toplam_oda': 0
            }), 500
    
    @app.route('/api/oteller/<int:otel_id>/oda-tipleri-liste', methods=['GET'])
    @login_required
    def api_otel_oda_tipleri_liste(otel_id):
        """Bir oteldeki oda tiplerini basit liste olarak getir (oda formu için)"""
        try:
            from sqlalchemy import distinct
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
                    'dolap_sayisi': oda_tipi.dolap_sayisi
                })
            
            return jsonify({
                'success': True,
                'oda_tipleri': oda_tipleri_list
            })
            
        except Exception as e:
            log_hata(e, modul='api_otel_oda_tipleri_liste')
            return jsonify({
                'success': False,
                'error': str(e),
                'oda_tipleri': []
            }), 500

    # AJAX endpoint - Yeni oda ekle
    @app.route('/api/oda-ekle', methods=['POST'])
    @csrf.exempt
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
                oda_tipi_id=data.get('oda_tipi') if data.get('oda_tipi') else None,
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
                'oda_tipi_id': oda.oda_tipi_id
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
    
    # AJAX endpoint - Oda numarası kontrol et (duplikasyon)
    @app.route('/api/oda-no-kontrol', methods=['GET'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def api_oda_no_kontrol():
        """Oda numarasının kullanılıp kullanılmadığını kontrol et"""
        try:
            from models import Oda
            
            oda_no = request.args.get('oda_no', '').strip()
            
            if not oda_no:
                return jsonify({
                    'success': False,
                    'error': 'Oda numarası gerekli'
                }), 400
            
            # Aktif odalarda bu numara var mı?
            mevcut_oda = Oda.query.filter_by(oda_no=oda_no, aktif=True).first()
            
            return jsonify({
                'success': True,
                'mevcut': mevcut_oda is not None,
                'oda_no': oda_no
            })
            
        except Exception as e:
            log_hata(e, modul='api_oda_no_kontrol')
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # ============================================================================
    # ZİMMET ŞABLON API'LERİ
    # ============================================================================
    
    @app.route('/api/zimmet-sablonlar', methods=['GET'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_zimmet_sablonlar():
        """Zimmet şablonlarını listele"""
        try:
            from models import ZimmetSablon, ZimmetSablonDetay
            from utils.authorization import get_kullanici_otelleri
            
            oteller = get_kullanici_otelleri()
            otel_ids = [o.id for o in oteller]  # Otel objelerinden ID listesi çıkar
            
            # Kullanıcının erişebildiği otellerin şablonları + genel şablonlar
            sablonlar = ZimmetSablon.query.filter(
                ZimmetSablon.aktif == True,
                db.or_(
                    ZimmetSablon.otel_id.in_(otel_ids) if otel_ids else False,
                    ZimmetSablon.otel_id == None
                )
            ).order_by(ZimmetSablon.sablon_adi).all()
            
            result = []
            for sablon in sablonlar:
                detaylar = []
                for detay in sablon.detaylar:
                    detaylar.append({
                        'urun_id': detay.urun_id,
                        'urun_adi': detay.urun.urun_adi if detay.urun else '',
                        'grup_adi': detay.urun.grup.grup_adi if detay.urun and detay.urun.grup else '',
                        'varsayilan_miktar': detay.varsayilan_miktar,
                        'birim': detay.urun.birim if detay.urun else 'adet'
                    })
                
                result.append({
                    'id': sablon.id,
                    'sablon_adi': sablon.sablon_adi,
                    'aciklama': sablon.aciklama,
                    'urun_sayisi': len(sablon.detaylar),
                    'detaylar': detaylar
                })
            
            return jsonify(result)
            
        except Exception as e:
            log_hata(e, modul='api_zimmet_sablonlar')
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/zimmet-sablon-kaydet', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_zimmet_sablon_kaydet():
        """Yeni zimmet şablonu oluştur veya güncelle"""
        try:
            from models import ZimmetSablon, ZimmetSablonDetay
            
            data = request.get_json()
            sablon_id = data.get('sablon_id')
            sablon_adi = data.get('sablon_adi', '').strip()
            aciklama = data.get('aciklama', '').strip()
            otel_id = data.get('otel_id')
            urunler = data.get('urunler', [])  # [{urun_id, miktar}, ...]
            
            if not sablon_adi:
                return jsonify({'success': False, 'error': 'Şablon adı gerekli'}), 400
            
            if not urunler:
                return jsonify({'success': False, 'error': 'En az bir ürün ekleyin'}), 400
            
            if sablon_id:
                # Güncelleme
                sablon = db.session.get(ZimmetSablon, sablon_id)
                if not sablon:
                    return jsonify({'success': False, 'error': 'Şablon bulunamadı'}), 404
                
                sablon.sablon_adi = sablon_adi
                sablon.aciklama = aciklama
                sablon.otel_id = otel_id if otel_id else None
                
                # Mevcut detayları sil
                ZimmetSablonDetay.query.filter_by(sablon_id=sablon.id).delete()
            else:
                # Yeni oluştur
                sablon = ZimmetSablon(
                    sablon_adi=sablon_adi,
                    aciklama=aciklama,
                    otel_id=otel_id if otel_id else None,
                    olusturan_id=session.get('kullanici_id')
                )
                db.session.add(sablon)
                db.session.flush()
            
            # Detayları ekle
            for urun in urunler:
                detay = ZimmetSablonDetay(
                    sablon_id=sablon.id,
                    urun_id=urun['urun_id'],
                    varsayilan_miktar=urun.get('miktar', 1)
                )
                db.session.add(detay)
            
            db.session.commit()
            
            log_islem('sablon_kaydet', 'zimmet_sablon', {
                'sablon_id': sablon.id,
                'sablon_adi': sablon_adi,
                'urun_sayisi': len(urunler)
            })
            
            return jsonify({
                'success': True,
                'sablon_id': sablon.id,
                'message': 'Şablon başarıyla kaydedildi'
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_zimmet_sablon_kaydet')
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/zimmet-sablon-sil/<int:sablon_id>', methods=['DELETE'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_zimmet_sablon_sil(sablon_id):
        """Zimmet şablonunu sil (soft delete)"""
        try:
            from models import ZimmetSablon
            
            sablon = db.session.get(ZimmetSablon, sablon_id)
            if not sablon:
                return jsonify({'success': False, 'error': 'Şablon bulunamadı'}), 404
            
            sablon.aktif = False
            db.session.commit()
            
            log_islem('sablon_sil', 'zimmet_sablon', {'sablon_id': sablon_id})
            
            return jsonify({'success': True, 'message': 'Şablon silindi'})
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_zimmet_sablon_sil')
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/zimmet-tum-urunler', methods=['GET'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_zimmet_tum_urunler():
        """Tüm ürünleri stok bilgisiyle birlikte getir (Grid ve Hızlı Giriş için)"""
        try:
            from models import UrunStok
            from utils.authorization import get_kullanici_otelleri
            
            oteller = get_kullanici_otelleri()
            otel_ids = [o.id for o in oteller]
            secili_otel_id = request.args.get('otel_id', type=int)
            
            if secili_otel_id and secili_otel_id in otel_ids:
                otel_id = secili_otel_id
            elif otel_ids:
                otel_id = otel_ids[0]
            else:
                return jsonify([])
            
            # Tüm aktif ürünleri gruplarıyla birlikte getir
            urunler = Urun.query.filter_by(aktif=True).join(UrunGrup).order_by(
                UrunGrup.grup_adi, Urun.urun_adi
            ).all()
            
            # Bugün atanan miktarları al (tüm personeller için)
            from models import PersonelZimmet, PersonelZimmetDetay
            from datetime import date
            bugun = date.today()
            
            # Bugünkü zimmetlerdeki ürün miktarlarını topla
            bugun_atananlar = db.session.query(
                PersonelZimmetDetay.urun_id,
                db.func.sum(PersonelZimmetDetay.miktar).label('toplam')
            ).join(PersonelZimmet).filter(
                db.func.date(PersonelZimmet.zimmet_tarihi) == bugun,
                PersonelZimmet.durum == 'aktif'
            ).group_by(PersonelZimmetDetay.urun_id).all()
            
            bugun_map = {item.urun_id: item.toplam for item in bugun_atananlar}
            
            result = []
            for urun in urunler:
                # Stok bilgisini al
                stok = UrunStok.query.filter_by(urun_id=urun.id, otel_id=otel_id).first()
                mevcut_stok = stok.mevcut_stok if stok else 0
                
                result.append({
                    'id': urun.id,
                    'urun_adi': urun.urun_adi,
                    'grup_id': urun.grup_id,
                    'grup_adi': urun.grup.grup_adi if urun.grup else '',
                    'birim': urun.birim or 'adet',
                    'mevcut_stok': mevcut_stok,
                    'stok_durumu': 'Yeterli' if mevcut_stok > 10 else ('Kritik' if mevcut_stok > 0 else 'Yok'),
                    'bugun_atanan': bugun_map.get(urun.id, 0)
                })
            
            return jsonify(result)
            
        except Exception as e:
            log_hata(e, modul='api_zimmet_tum_urunler')
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/zimmet-hizli-ata', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def api_zimmet_hizli_ata():
        """Hızlı zimmet atama (Grid, Şablon, Hızlı Giriş için ortak endpoint)"""
        try:
            from models import UrunStok
            from utils.authorization import get_kullanici_otelleri
            from utils.audit import audit_create
            
            data = request.get_json()
            personel_id = data.get('personel_id')
            aciklama = data.get('aciklama', '')
            urunler = data.get('urunler', [])  # [{urun_id, miktar}, ...]
            
            if not personel_id:
                return jsonify({'success': False, 'error': 'Kat sorumlusu seçiniz'}), 400
            
            if not urunler:
                return jsonify({'success': False, 'error': 'En az bir ürün seçiniz'}), 400
            
            oteller = get_kullanici_otelleri()
            otel_ids = [o.id for o in oteller]
            secili_otel_id = data.get('otel_id')
            
            if secili_otel_id and secili_otel_id in otel_ids:
                otel_id = secili_otel_id
            elif otel_ids:
                otel_id = otel_ids[0]
            else:
                return jsonify({'success': False, 'error': 'Otel bulunamadı'}), 400
            
            # Stok kontrolü
            stok_hatasi = []
            for urun_data in urunler:
                urun_id = urun_data['urun_id']
                miktar = urun_data['miktar']
                
                stok = UrunStok.query.filter_by(urun_id=urun_id, otel_id=otel_id).first()
                mevcut = stok.mevcut_stok if stok else 0
                
                if miktar > mevcut:
                    urun = db.session.get(Urun, urun_id)
                    stok_hatasi.append(f"{urun.urun_adi}: İstenen {miktar}, Mevcut {mevcut}")
            
            if stok_hatasi:
                return jsonify({
                    'success': False,
                    'error': 'Stok yetersiz',
                    'detay': stok_hatasi
                }), 400
            
            # Bugün aynı personele zimmet var mı kontrol et
            from datetime import date
            bugun = date.today()
            
            mevcut_zimmet = PersonelZimmet.query.filter(
                PersonelZimmet.personel_id == personel_id,
                PersonelZimmet.durum == 'aktif',
                db.func.date(PersonelZimmet.zimmet_tarihi) == bugun
            ).first()
            
            if mevcut_zimmet:
                # Mevcut zimmete ekle
                zimmet = mevcut_zimmet
                if aciklama:
                    zimmet.aciklama = (zimmet.aciklama or '') + ' | ' + aciklama
            else:
                # Yeni zimmet oluştur
                zimmet = PersonelZimmet(
                    personel_id=personel_id,
                    teslim_eden_id=session['kullanici_id'],
                    aciklama=aciklama
                )
                db.session.add(zimmet)
                db.session.flush()
            
            # Detayları ekle ve stok düş
            for urun_data in urunler:
                urun_id = urun_data['urun_id']
                miktar = urun_data['miktar']
                
                # Aynı üründen zimmet detayı var mı kontrol et
                mevcut_detay = PersonelZimmetDetay.query.filter_by(
                    zimmet_id=zimmet.id,
                    urun_id=urun_id
                ).first()
                
                if mevcut_detay:
                    # Mevcut detaya miktar ekle
                    mevcut_detay.miktar += miktar
                    mevcut_detay.kalan_miktar += miktar
                else:
                    # Yeni zimmet detay oluştur
                    detay = PersonelZimmetDetay(
                        zimmet_id=zimmet.id,
                        urun_id=urun_id,
                        miktar=miktar,
                        kalan_miktar=miktar
                    )
                    db.session.add(detay)
                
                # Stok düş
                stok = UrunStok.query.filter_by(urun_id=urun_id, otel_id=otel_id).first()
                if stok:
                    stok.mevcut_stok -= miktar
                
                # Stok hareket kaydı
                hareket = StokHareket(
                    urun_id=urun_id,
                    hareket_tipi='cikis',
                    miktar=miktar,
                    aciklama=f'Zimmet atama - {aciklama}',
                    islem_yapan_id=session['kullanici_id']
                )
                db.session.add(hareket)
            
            db.session.commit()
            
            audit_create('personel_zimmet', zimmet.id, zimmet)
            
            log_islem('zimmet_ata', 'personel_zimmet', {
                'zimmet_id': zimmet.id,
                'personel_id': personel_id,
                'urun_sayisi': len(urunler)
            })
            
            return jsonify({
                'success': True,
                'zimmet_id': zimmet.id,
                'message': 'Zimmet başarıyla atandı'
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_zimmet_hizli_ata')
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/zimmet-tek-urun-ata', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu')
    def api_zimmet_tek_urun_ata():
        """Tek ürün zimmet atama - anında kaydet"""
        try:
            from models import UrunStok, PersonelZimmet, PersonelZimmetDetay
            from utils.authorization import get_kullanici_otelleri
            
            data = request.get_json()
            personel_id = data.get('personel_id')
            urun_id = data.get('urun_id')
            miktar = data.get('miktar', 1)
            zimmet_id = data.get('zimmet_id')  # Mevcut zimmet varsa
            otel_id = data.get('otel_id')
            
            if not personel_id or not urun_id:
                return jsonify({'success': False, 'error': 'Personel ve ürün gerekli'}), 400
            
            # Otel kontrolü
            oteller = get_kullanici_otelleri()
            otel_ids = [o.id for o in oteller]
            if otel_id and otel_id in otel_ids:
                secili_otel = otel_id
            elif otel_ids:
                secili_otel = otel_ids[0]
            else:
                return jsonify({'success': False, 'error': 'Otel bulunamadı'}), 400
            
            # Stok kontrolü
            stok = UrunStok.query.filter_by(urun_id=urun_id, otel_id=secili_otel).first()
            mevcut = stok.mevcut_stok if stok else 0
            if miktar > mevcut:
                return jsonify({'success': False, 'error': f'Yetersiz stok! Mevcut: {mevcut}'}), 400
            
            # Bugünkü tarihe göre mevcut zimmet var mı kontrol et
            from datetime import date
            bugun = date.today()
            
            # Önce bugünkü zimmet var mı bak
            zimmet = PersonelZimmet.query.filter(
                PersonelZimmet.personel_id == personel_id,
                db.func.date(PersonelZimmet.zimmet_tarihi) == bugun,
                PersonelZimmet.durum == 'aktif'
            ).first()
            
            if zimmet:
                zimmet_id = zimmet.id
            else:
                # Bugün için yeni zimmet oluştur
                zimmet = PersonelZimmet(
                    personel_id=personel_id,
                    teslim_eden_id=session['kullanici_id'],
                    aciklama='Hızlı zimmet atama'
                )
                db.session.add(zimmet)
                db.session.flush()
                zimmet_id = zimmet.id
            
            # Mevcut detay var mı kontrol et
            detay = PersonelZimmetDetay.query.filter_by(zimmet_id=zimmet_id, urun_id=urun_id).first()
            if detay:
                detay.miktar += miktar
                detay.kalan_miktar += miktar
            else:
                detay = PersonelZimmetDetay(
                    zimmet_id=zimmet_id,
                    urun_id=urun_id,
                    miktar=miktar,
                    kalan_miktar=miktar
                )
                db.session.add(detay)
            
            # Stok düş
            if stok:
                stok.mevcut_stok -= miktar
            
            # Stok hareket kaydı
            hareket = StokHareket(
                urun_id=urun_id,
                hareket_tipi='cikis',
                miktar=miktar,
                aciklama=f'Hızlı zimmet atama',
                islem_yapan_id=session['kullanici_id']
            )
            db.session.add(hareket)
            
            db.session.commit()
            
            # Ürün bilgisi
            urun = db.session.get(Urun, urun_id)
            yeni_stok = stok.mevcut_stok if stok else 0
            
            return jsonify({
                'success': True,
                'zimmet_id': zimmet_id,
                'detay_miktar': detay.miktar,
                'yeni_stok': yeni_stok,
                'urun_adi': urun.urun_adi if urun else ''
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_zimmet_tek_urun_ata')
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/zimmet-detay/<int:zimmet_id>', methods=['GET'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_zimmet_detay(zimmet_id):
        """Zimmet detaylarını getir"""
        try:
            from models import PersonelZimmet, PersonelZimmetDetay
            
            zimmet = db.session.get(PersonelZimmet, zimmet_id)
            if not zimmet:
                return jsonify({'success': False, 'error': 'Zimmet bulunamadı'}), 404
            
            detaylar = []
            for d in zimmet.detaylar:
                detaylar.append({
                    'detay_id': d.id,
                    'urun_id': d.urun_id,
                    'urun_adi': d.urun.urun_adi if d.urun else '',
                    'miktar': d.miktar,
                    'kalan': d.kalan_miktar
                })
            
            return jsonify({
                'success': True,
                'zimmet_id': zimmet.id,
                'personel': f"{zimmet.personel.ad} {zimmet.personel.soyad}" if zimmet.personel else '',
                'tarih': zimmet.zimmet_tarihi.strftime('%d.%m.%Y %H:%M') if zimmet.zimmet_tarihi else '',
                'durum': zimmet.durum,
                'detaylar': detaylar
            })
            
        except Exception as e:
            log_hata(e, modul='api_zimmet_detay')
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/zimmet-iptal/<int:zimmet_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_zimmet_iptal(zimmet_id):
        """Zimmet sil - kullanılmamışsa, FIFO kayıtlarını geri al ve kaydı sil"""
        try:
            from models import PersonelZimmet, PersonelZimmetDetay, UrunStok, StokFifoKayit, StokFifoKullanim, StokHareket
            
            zimmet = db.session.get(PersonelZimmet, zimmet_id)
            if not zimmet:
                return jsonify({'success': False, 'error': 'Zimmet bulunamadı'}), 404
            
            if zimmet.durum != 'aktif':
                return jsonify({'success': False, 'error': 'Bu zimmet zaten iptal edilmiş'}), 400
            
            otel_id = zimmet.personel.otel_id if zimmet.personel else None
            
            # Stokları geri ekle ve FIFO kayıtlarını geri al
            for d in zimmet.detaylar:
                # Geri alınacak miktar hesapla (kullanılmamış + iade edilmemiş)
                geri_alinacak = d.miktar - getattr(d, 'kullanilan_miktar', 0) - getattr(d, 'iade_edilen_miktar', 0)
                
                if geri_alinacak > 0:
                    # UrunStok güncelle
                    stok = UrunStok.query.filter_by(urun_id=d.urun_id, otel_id=otel_id).first()
                    if stok:
                        stok.mevcut_stok += geri_alinacak
                        stok.son_giris_tarihi = get_kktc_now()
                        stok.son_guncelleyen_id = session.get('kullanici_id')
                    
                    # Stok hareketi kaydet
                    stok_hareket = StokHareket(
                        urun_id=d.urun_id,
                        hareket_tipi='giris',
                        miktar=geri_alinacak,
                        aciklama=f'Zimmet Silme İadesi - Zimmet #{zimmet_id}',
                        islem_yapan_id=session.get('kullanici_id')
                    )
                    db.session.add(stok_hareket)
                
                # FIFO kullanım kayıtlarını geri al ve sil
                fifo_kullanimlar = StokFifoKullanim.query.filter_by(
                    referans_id=d.id,
                    islem_tipi='zimmet'
                ).all()
                
                for kullanim in fifo_kullanimlar:
                    fifo_kayit = db.session.get(StokFifoKayit, kullanim.fifo_kayit_id)
                    if fifo_kayit:
                        fifo_kayit.kalan_miktar += kullanim.miktar
                        fifo_kayit.kullanilan_miktar -= kullanim.miktar
                        fifo_kayit.tukendi = False
                    db.session.delete(kullanim)
                
                # Detay kaydını sil
                db.session.delete(d)
            
            # Zimmet kaydını sil
            db.session.delete(zimmet)
            db.session.commit()
            
            log_islem('silme', 'zimmet', {'zimmet_id': zimmet_id})
            
            return jsonify({'success': True, 'message': 'Zimmet silindi, stoklar geri eklendi'})
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_zimmet_iptal')
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/zimmet-detay-iptal/<int:detay_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_zimmet_detay_iptal(detay_id):
        """Tek ürün zimmet detayını iptal et - FIFO kayıtlarını geri al"""
        try:
            from models import PersonelZimmetDetay, UrunStok, StokFifoKayit, StokFifoKullanim, StokHareket
            
            detay = db.session.get(PersonelZimmetDetay, detay_id)
            if not detay:
                return jsonify({'success': False, 'error': 'Detay bulunamadı'}), 404
            
            zimmet = detay.zimmet
            otel_id = zimmet.personel.otel_id if zimmet and zimmet.personel else None
            
            # Geri alınacak miktar hesapla
            geri_alinacak = detay.miktar - getattr(detay, 'kullanilan_miktar', 0) - getattr(detay, 'iade_edilen_miktar', 0)
            
            if geri_alinacak <= 0:
                return jsonify({'success': False, 'error': 'Bu ürün tamamen kullanılmış, iptal edilemez!'}), 400
            
            # UrunStok güncelle
            stok = UrunStok.query.filter_by(urun_id=detay.urun_id, otel_id=otel_id).first()
            if stok:
                stok.mevcut_stok += geri_alinacak
                stok.son_giris_tarihi = get_kktc_now()
                stok.son_guncelleyen_id = session.get('kullanici_id')
            
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
            
            # Stok hareketi kaydet
            stok_hareket = StokHareket(
                urun_id=detay.urun_id,
                hareket_tipi='giris',
                miktar=geri_alinacak,
                aciklama=f'Zimmet Detay İptal İadesi - Detay #{detay_id}',
                islem_yapan_id=session.get('kullanici_id')
            )
            db.session.add(stok_hareket)
            
            # Detayı sil
            db.session.delete(detay)
            db.session.commit()
            
            log_islem('iptal', 'zimmet_detay', {'detay_id': detay_id})
            
            return jsonify({'success': True, 'message': 'Ürün zimmet listesinden çıkarıldı, stok geri eklendi'})
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_zimmet_detay_iptal')
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/zimmet-listesi', methods=['GET'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_zimmet_listesi():
        """Aktif zimmetleri listele"""
        try:
            from models import PersonelZimmet
            from utils.authorization import get_kullanici_otelleri
            
            oteller = get_kullanici_otelleri()
            otel_ids = [o.id for o in oteller]
            otel_id = request.args.get('otel_id', type=int)
            
            if otel_id and otel_id in otel_ids:
                secili_otel = otel_id
            elif otel_ids:
                secili_otel = otel_ids[0]
            else:
                return jsonify({'success': True, 'zimmetler': []})
            
            zimmetler = PersonelZimmet.query.filter(
                PersonelZimmet.durum == 'aktif',
                PersonelZimmet.personel.has(otel_id=secili_otel)
            ).order_by(PersonelZimmet.zimmet_tarihi.desc()).all()
            
            result = []
            for z in zimmetler:
                result.append({
                    'id': z.id,
                    'personel': f"{z.personel.ad} {z.personel.soyad}" if z.personel else '',
                    'tarih': z.zimmet_tarihi.strftime('%d.%m.%Y') if z.zimmet_tarihi else '',
                    'urun_sayisi': len(z.detaylar),
                    'durum': z.durum
                })
            
            return jsonify({'success': True, 'zimmetler': result})
            
        except Exception as e:
            log_hata(e, modul='api_zimmet_listesi')
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/zimmet-urun-ara', methods=['GET'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_zimmet_urun_ara():
        """Ürün arama (Hızlı Giriş autocomplete için)"""
        try:
            from models import UrunStok
            from utils.authorization import get_kullanici_otelleri
            
            q = request.args.get('q', '').strip().lower()
            otel_id = request.args.get('otel_id', type=int)
            
            if len(q) < 2:
                return jsonify([])
            
            oteller = get_kullanici_otelleri()
            otel_ids = [o.id for o in oteller]
            if otel_id and otel_id in otel_ids:
                secili_otel = otel_id
            elif otel_ids:
                secili_otel = otel_ids[0]
            else:
                return jsonify([])
            
            # Ürün adında arama yap
            urunler = Urun.query.filter(
                Urun.aktif == True,
                Urun.urun_adi.ilike(f'%{q}%')
            ).join(UrunGrup).order_by(Urun.urun_adi).limit(15).all()
            
            result = []
            for urun in urunler:
                stok = UrunStok.query.filter_by(urun_id=urun.id, otel_id=secili_otel).first()
                mevcut_stok = stok.mevcut_stok if stok else 0
                
                result.append({
                    'id': urun.id,
                    'urun_adi': urun.urun_adi,
                    'grup_adi': urun.grup.grup_adi if urun.grup else '',
                    'birim': urun.birim or 'adet',
                    'mevcut_stok': mevcut_stok
                })
            
            return jsonify(result)
            
        except Exception as e:
            log_hata(e, modul='api_zimmet_urun_ara')
            return jsonify({'error': str(e)}), 500

            return jsonify({'success': False, 'error': str(e)}), 500

    # ==================== SATIN ALMA API'LERİ ====================
    
    @app.route('/api/urunler-stok')
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_urunler_stok():
        """Tüm ürünleri stok bilgisiyle getir - Satın Alma Grid için"""
        try:
            from models import UrunStok
            from utils.authorization import get_kullanici_otelleri
            
            oteller = get_kullanici_otelleri()
            otel_ids = [o.id for o in oteller]
            otel_id = request.args.get('otel_id', type=int)
            
            if otel_id and otel_id in otel_ids:
                secili_otel = otel_id
            elif otel_ids:
                secili_otel = otel_ids[0]
            else:
                return jsonify({'success': True, 'urunler': []})
            
            urunler = Urun.query.filter_by(aktif=True).join(UrunGrup).order_by(UrunGrup.grup_adi, Urun.urun_adi).all()
            
            result = []
            for urun in urunler:
                stok = UrunStok.query.filter_by(urun_id=urun.id, otel_id=secili_otel).first()
                mevcut_stok = stok.mevcut_stok if stok else 0
                
                result.append({
                    'id': urun.id,
                    'urun_adi': urun.urun_adi,
                    'grup_id': urun.grup_id,
                    'grup_adi': urun.grup.grup_adi if urun.grup else 'Genel',
                    'birim': urun.birim or 'adet',
                    'stok': mevcut_stok
                })
            
            return jsonify({'success': True, 'urunler': result})
            
        except Exception as e:
            log_hata(e, modul='api_urunler_stok')
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/satin-alma/siparis-olustur', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_satin_alma_siparis_olustur():
        """Yeni satın alma siparişi oluştur - Akıllı Grid'den"""
        try:
            from models import SatinAlmaSiparisi, SatinAlmaSiparisDetay
            from utils.authorization import get_kullanici_otelleri
            from decimal import Decimal
            from datetime import date
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Geçersiz veri'}), 400
            
            urunler = data.get('urunler', [])
            aciklama = data.get('aciklama', '')
            
            if not urunler:
                return jsonify({'success': False, 'message': 'En az bir ürün seçmelisiniz'}), 400
            
            # Otel ID
            oteller = get_kullanici_otelleri()
            if not oteller:
                return jsonify({'success': False, 'message': 'Otel bulunamadı'}), 400
            otel_id = oteller[0].id
            
            # Sipariş numarası üret
            bugun = get_kktc_now()
            tarih_str = bugun.strftime('%Y%m%d')
            son_siparis = SatinAlmaSiparisi.query.filter(
                SatinAlmaSiparisi.siparis_no.like(f'SA-{tarih_str}-%')
            ).order_by(SatinAlmaSiparisi.siparis_no.desc()).first()
            
            if son_siparis:
                son_no = int(son_siparis.siparis_no.split('-')[-1])
                yeni_no = son_no + 1
            else:
                yeni_no = 1
            
            siparis_no = f'SA-{tarih_str}-{yeni_no:04d}'
            
            # Sipariş oluştur
            siparis = SatinAlmaSiparisi(
                siparis_no=siparis_no,
                tedarikci_id=None,
                otel_id=otel_id,
                tahmini_teslimat_tarihi=date.today(),
                durum='beklemede',
                toplam_tutar=Decimal('0'),
                aciklama=aciklama,
                olusturan_id=session['kullanici_id']
            )
            db.session.add(siparis)
            db.session.flush()
            
            # Detayları ekle
            for urun_data in urunler:
                urun_id = urun_data.get('urun_id')
                miktar = urun_data.get('miktar', 0)
                
                if miktar > 0:
                    detay = SatinAlmaSiparisDetay(
                        siparis_id=siparis.id,
                        urun_id=urun_id,
                        miktar=miktar,
                        birim_fiyat=Decimal('0'),
                        toplam_fiyat=Decimal('0'),
                        teslim_alinan_miktar=0
                    )
                    db.session.add(detay)
            
            db.session.commit()
            
            # Audit log
            audit_create('satin_alma_siparisleri', siparis.id, serialize_model(siparis))
            
            log_islem('ekleme', 'satin_alma_siparis', {
                'siparis_id': siparis.id,
                'siparis_no': siparis_no,
                'urun_sayisi': len(urunler)
            })
            
            return jsonify({
                'success': True,
                'siparis_id': siparis.id,
                'siparis_no': siparis_no,
                'message': 'Sipariş başarıyla oluşturuldu'
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_satin_alma_siparis_olustur')
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/siparis-detay/<int:siparis_id>')
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_siparis_detay(siparis_id):
        """Sipariş detaylarını getir"""
        try:
            from models import SatinAlmaSiparisi, SatinAlmaSiparisDetay
            
            siparis = SatinAlmaSiparisi.query.get_or_404(siparis_id)
            
            detaylar = []
            for d in siparis.detaylar:
                detaylar.append({
                    'id': d.id,
                    'urun_id': d.urun_id,
                    'urun_adi': d.urun.urun_adi if d.urun else 'Bilinmeyen',
                    'miktar': d.miktar,
                    'birim_fiyat': float(d.birim_fiyat) if d.birim_fiyat else 0,
                    'toplam_fiyat': float(d.toplam_fiyat) if d.toplam_fiyat else 0,
                    'teslim_alinan_miktar': d.teslim_alinan_miktar
                })
            
            return jsonify({
                'success': True,
                'siparis': {
                    'id': siparis.id,
                    'siparis_no': siparis.siparis_no,
                    'durum': siparis.durum,
                    'siparis_tarihi': siparis.siparis_tarihi.strftime('%d.%m.%Y %H:%M') if siparis.siparis_tarihi else '-',
                    'tedarikci': siparis.tedarikci.tedarikci_adi if siparis.tedarikci else None,
                    'tedarikci_id': siparis.tedarikci_id,
                    'aciklama': siparis.aciklama,
                    'toplam_tutar': float(siparis.toplam_tutar) if siparis.toplam_tutar else 0,
                    'detaylar': detaylar
                }
            })
        except Exception as e:
            log_hata(e, modul='api_siparis_detay')
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/satin-alma/tedarik-tamamla', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_tedarik_tamamla():
        """Onaylanan siparişin tedarik işlemini tamamla ve stok girişi yap"""
        try:
            from models import SatinAlmaSiparisi, SatinAlmaSiparisDetay, StokHareket, UrunStok
            from decimal import Decimal
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Geçersiz veri'}), 400
            
            siparis_id = data.get('siparis_id')
            tedarikci_id = data.get('tedarikci_id')
            tedarik_tarihi = data.get('tedarik_tarihi')
            fiyatlar = data.get('fiyatlar', {})
            stok_giris_yap = data.get('stok_giris_yap', True)
            
            siparis = SatinAlmaSiparisi.query.get_or_404(siparis_id)
            
            if siparis.durum != 'onaylandi':
                return jsonify({'success': False, 'message': 'Sadece onaylanmış siparişler için tedarik girişi yapılabilir'}), 400
            
            # Tedarikçi ve tarihi güncelle
            siparis.tedarikci_id = tedarikci_id
            siparis.gerceklesen_teslimat_tarihi = datetime.strptime(tedarik_tarihi, '%Y-%m-%d').date()
            siparis.durum = 'teslim_alindi'
            
            toplam_tutar = Decimal('0')
            
            # Detay fiyatlarını güncelle
            for detay in siparis.detaylar:
                detay_id_str = str(detay.id)
                if detay_id_str in fiyatlar:
                    birim_fiyat = Decimal(str(fiyatlar[detay_id_str]))
                    detay.birim_fiyat = birim_fiyat
                    detay.toplam_fiyat = birim_fiyat * detay.miktar
                    detay.teslim_alinan_miktar = detay.miktar
                    toplam_tutar += detay.toplam_fiyat
                    
                    # Stok girişi yap
                    if stok_giris_yap:
                        stok_hareket = StokHareket(
                            urun_id=detay.urun_id,
                            otel_id=siparis.otel_id,
                            hareket_tipi='giris',
                            miktar=detay.miktar,
                            aciklama=f'Satın alma girişi - {siparis.siparis_no}',
                            islem_yapan_id=session['kullanici_id']
                        )
                        db.session.add(stok_hareket)
                        
                        # UrunStok güncelle
                        urun_stok = UrunStok.query.filter_by(
                            urun_id=detay.urun_id,
                            otel_id=siparis.otel_id
                        ).first()
                        
                        if urun_stok:
                            urun_stok.miktar += detay.miktar
                        else:
                            urun_stok = UrunStok(
                                urun_id=detay.urun_id,
                                otel_id=siparis.otel_id,
                                miktar=detay.miktar
                            )
                            db.session.add(urun_stok)
            
            siparis.toplam_tutar = toplam_tutar
            db.session.commit()
            
            log_islem('guncelleme', 'satin_alma_siparis', {
                'siparis_id': siparis.id,
                'siparis_no': siparis.siparis_no,
                'islem': 'tedarik_tamamlandi',
                'stok_giris': stok_giris_yap
            })
            
            return jsonify({
                'success': True,
                'message': 'Tedarik işlemi tamamlandı',
                'stok_giris': stok_giris_yap
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_tedarik_tamamla')
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/otel-zimmet-stok-ekle', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_otel_zimmet_stok_ekle():
        """Otel zimmet stoğuna ürün ekle"""
        try:
            from models import OtelZimmetStok
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Geçersiz veri'}), 400
            
            stok_id = data.get('stok_id')
            miktar = data.get('miktar', 0)
            
            if not stok_id or miktar <= 0:
                return jsonify({'success': False, 'error': 'Stok ID ve miktar gerekli'}), 400
            
            stok = OtelZimmetStok.query.get(stok_id)
            if not stok:
                return jsonify({'success': False, 'error': 'Stok kaydı bulunamadı'}), 404
            
            # Stok ekle
            stok.toplam_miktar += miktar
            stok.kalan_miktar += miktar
            stok.son_guncelleme = get_kktc_now()
            
            db.session.commit()
            
            log_islem('ekleme', 'otel_zimmet_stok', {
                'stok_id': stok_id,
                'miktar': miktar,
                'yeni_toplam': stok.toplam_miktar,
                'yeni_kalan': stok.kalan_miktar
            })
            
            return jsonify({
                'success': True,
                'message': f'{miktar} adet stok eklendi',
                'yeni_toplam': stok.toplam_miktar,
                'yeni_kalan': stok.kalan_miktar
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_otel_zimmet_stok_ekle')
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/otel-zimmet-stoklari', methods=['GET'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_otel_zimmet_stoklari():
        """Belirli bir otelin zimmet stoklarını getir"""
        try:
            from models import OtelZimmetStok, Otel
            
            otel_id = request.args.get('otel_id', type=int)
            if not otel_id:
                return jsonify({'success': False, 'error': 'Otel ID gerekli'}), 400
            
            stoklar = OtelZimmetStok.query.filter_by(otel_id=otel_id).join(Urun).order_by(Urun.urun_adi).all()
            
            result = []
            for s in stoklar:
                if s.kalan_miktar == 0:
                    durum = 'stokout'
                elif s.kalan_miktar <= (s.kritik_stok_seviyesi or 10):
                    durum = 'kritik'
                elif s.kalan_miktar <= (s.kritik_stok_seviyesi or 10) * 1.5:
                    durum = 'dikkat'
                else:
                    durum = 'normal'
                
                result.append({
                    'id': s.id,
                    'urun_id': s.urun_id,
                    'urun_adi': s.urun.urun_adi if s.urun else 'Bilinmiyor',
                    'grup_adi': s.urun.grup.grup_adi if s.urun and s.urun.grup else 'Genel',
                    'birim': s.urun.birim if s.urun else 'Adet',
                    'toplam_miktar': s.toplam_miktar,
                    'kullanilan_miktar': s.kullanilan_miktar,
                    'kalan_miktar': s.kalan_miktar,
                    'durum': durum
                })
            
            return jsonify({'success': True, 'stoklar': result})
            
        except Exception as e:
            log_hata(e, modul='api_otel_zimmet_stoklari')
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/urunler-zimmet-icin', methods=['GET'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_urunler_zimmet_icin():
        """Zimmet için ürün listesi - Ana depo stok ve otel zimmet stoğu ile"""
        try:
            from models import OtelZimmetStok, UrunStok, UrunGrup
            
            otel_id = request.args.get('otel_id', type=int)
            if not otel_id:
                return jsonify({'success': False, 'error': 'Otel ID gerekli'}), 400
            
            # Tüm aktif ürünleri getir
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            # Ana depo stokları (UrunStok tablosundan)
            ana_depo_stoklar = {s.urun_id: s.mevcut_stok for s in UrunStok.query.filter_by(otel_id=otel_id).all()}
            
            # Otel zimmet stokları
            otel_zimmet_stoklar = {s.urun_id: s.kalan_miktar for s in OtelZimmetStok.query.filter_by(otel_id=otel_id).all()}
            
            result = []
            for u in urunler:
                grup = db.session.get(UrunGrup, u.grup_id) if u.grup_id else None
                result.append({
                    'id': u.id,
                    'urun_adi': u.urun_adi,
                    'birim': u.birim or 'Adet',
                    'grup_id': u.grup_id or 0,
                    'grup_adi': grup.grup_adi if grup else 'Genel',
                    'ana_depo_stok': ana_depo_stoklar.get(u.id, 0),
                    'otel_zimmet_stok': otel_zimmet_stoklar.get(u.id, 0)
                })
            
            return jsonify({'success': True, 'urunler': result})
            
        except Exception as e:
            log_hata(e, modul='api_urunler_zimmet_icin')
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/otel-zimmet-ekle', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_otel_zimmet_ekle():
        """Otel zimmet stoğuna yeni ürün ekle veya mevcut stoğu artır - Ana depodan düşer"""
        try:
            from models import OtelZimmetStok, UrunStok
            from utils.fifo_servisler import FifoStokServisi
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Geçersiz veri'}), 400
            
            otel_id = data.get('otel_id')
            urun_id = data.get('urun_id')
            miktar = data.get('miktar', 0)
            
            if not otel_id or not urun_id or miktar <= 0:
                return jsonify({'success': False, 'error': 'Otel, ürün ve miktar gerekli'}), 400
            
            # Ana depo stok kontrolü
            ana_depo_stok = UrunStok.query.filter_by(otel_id=otel_id, urun_id=urun_id).first()
            mevcut_ana_depo = ana_depo_stok.mevcut_stok if ana_depo_stok else 0
            
            if mevcut_ana_depo < miktar:
                urun = db.session.get(Urun, urun_id)
                urun_adi = urun.urun_adi if urun else 'Bilinmiyor'
                return jsonify({
                    'success': False, 
                    'error': f'Ana depoda yetersiz stok! {urun_adi}: Mevcut {mevcut_ana_depo}, İstenen {miktar}'
                }), 400
            
            # FIFO ile ana depodan stok çıkışı yap
            fifo_sonuc = FifoStokServisi.fifo_stok_cikis(
                otel_id=otel_id,
                urun_id=urun_id,
                miktar=miktar,
                islem_tipi='zimmet_transfer',
                referans_id=None,
                kullanici_id=session.get('kullanici_id')
            )
            
            if not fifo_sonuc['success']:
                return jsonify({
                    'success': False, 
                    'error': f'Stok çıkışı hatası: {fifo_sonuc["message"]}'
                }), 400
            
            # Otel zimmet stoğuna ekle
            stok = OtelZimmetStok.query.filter_by(otel_id=otel_id, urun_id=urun_id).first()
            
            if stok:
                # Mevcut stoğa ekle
                stok.toplam_miktar += miktar
                stok.kalan_miktar += miktar
                stok.son_guncelleme = get_kktc_now()
            else:
                # Yeni stok kaydı oluştur
                stok = OtelZimmetStok(
                    otel_id=otel_id,
                    urun_id=urun_id,
                    toplam_miktar=miktar,
                    kullanilan_miktar=0,
                    kalan_miktar=miktar,
                    kritik_stok_seviyesi=50
                )
                db.session.add(stok)
            
            db.session.commit()
            
            # Güncel ana depo stoğunu al
            ana_depo_stok = UrunStok.query.filter_by(otel_id=otel_id, urun_id=urun_id).first()
            yeni_ana_depo_stok = ana_depo_stok.mevcut_stok if ana_depo_stok else 0
            
            log_islem('ekleme', 'otel_zimmet_stok', {
                'otel_id': otel_id,
                'urun_id': urun_id,
                'miktar': miktar,
                'yeni_toplam': stok.toplam_miktar,
                'ana_depo_onceki': mevcut_ana_depo,
                'ana_depo_sonraki': yeni_ana_depo_stok
            })
            
            return jsonify({
                'success': True,
                'message': f'{miktar} adet ürün eklendi (Ana depodan düşüldü)',
                'yeni_toplam': stok.toplam_miktar,
                'yeni_kalan': stok.kalan_miktar,
                'ana_depo_stok': yeni_ana_depo_stok
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_otel_zimmet_ekle')
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/otel-zimmet-islemleri', methods=['GET'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_otel_zimmet_islemleri():
        """Otel zimmet işlemlerini listele - Her işlem için ayrı kart"""
        try:
            from models import OtelZimmetStok, Otel
            
            otel_id = request.args.get('otel_id', type=int)
            if not otel_id:
                return jsonify({'success': False, 'error': 'Otel ID gerekli'}), 400
            
            otel = Otel.query.get(otel_id)
            if not otel:
                return jsonify({'success': False, 'error': 'Otel bulunamadı'}), 404
            
            # O oteldeki kat sorumlularını al
            personeller = Kullanici.query.filter_by(
                otel_id=otel_id,
                rol='kat_sorumlusu',
                aktif=True
            ).all()
            personel_adlari = [f"{p.ad} {p.soyad}" for p in personeller]
            
            # Otel zimmet stoklarını getir
            stoklar = OtelZimmetStok.query.filter_by(otel_id=otel_id).join(Urun).order_by(Urun.urun_adi).all()
            
            if not stoklar:
                return jsonify({'success': True, 'islemler': []})
            
            # Tek bir "işlem" olarak göster (otel bazlı ortak havuz)
            urunler = []
            for s in stoklar:
                urunler.append({
                    'urun_id': s.urun_id,
                    'urun_adi': s.urun.urun_adi if s.urun else 'Bilinmiyor',
                    'eklenen': s.toplam_miktar,
                    'onceki': 0,
                    'toplam': s.kalan_miktar
                })
            
            islem = {
                'id': otel_id,
                'otel_adi': otel.ad,
                'personeller': personel_adlari,
                'urun_cesidi': len(urunler),
                'tarih': stoklar[0].son_guncelleme.strftime('%d.%m.%Y %H:%M') if stoklar and stoklar[0].son_guncelleme else '-',
                'urunler': urunler
            }
            
            return jsonify({'success': True, 'islemler': [islem]})
            
        except Exception as e:
            log_hata(e, modul='api_otel_zimmet_islemleri')
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/zimmet-listesi-filtreli', methods=['GET'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_zimmet_listesi_filtreli():
        """Otel Zimmet Stok bazlı liste - ÜRÜN BAZLI GÖSTERİM
        
        Her ürün için:
        - Otel adı
        - O oteldeki TÜM personellerin zimmet durumu
        - Toplam stok bilgisi
        """
        try:
            from models import OtelZimmetStok, Otel, Urun, UrunGrup, PersonelZimmetKullanim
            from utils.authorization import get_kullanici_otelleri
            from sqlalchemy import func
            
            oteller = get_kullanici_otelleri()
            otel_ids = [o.id for o in oteller]
            
            if not otel_ids:
                return jsonify({'success': True, 'zimmetler': []})
            
            # Otel zimmet stoklarını getir
            stoklar = OtelZimmetStok.query.filter(
                OtelZimmetStok.otel_id.in_(otel_ids)
            ).join(Otel).join(Urun).order_by(Urun.urun_adi).all()
            
            # Her otel için kat sorumlularını al
            otel_personeller = {}
            for otel_id in otel_ids:
                personeller = Kullanici.query.filter_by(
                    otel_id=otel_id,
                    rol='kat_sorumlusu',
                    aktif=True
                ).all()
                otel_personeller[otel_id] = [
                    {'id': p.id, 'ad': f"{p.ad} {p.soyad}"} for p in personeller
                ]
            
            result = []
            for stok in stoklar:
                # Stok durumu
                if stok.kalan_miktar == 0:
                    durum = 'stokout'
                elif stok.kalan_miktar <= (stok.kritik_stok_seviyesi or 10):
                    durum = 'kritik'
                elif stok.kalan_miktar <= (stok.kritik_stok_seviyesi or 10) * 1.5:
                    durum = 'dikkat'
                else:
                    durum = 'normal'
                
                result.append({
                    'id': stok.id,
                    'urun_id': stok.urun_id,
                    'urun_adi': stok.urun.urun_adi if stok.urun else 'Bilinmiyor',
                    'grup_adi': stok.urun.grup.grup_adi if stok.urun and stok.urun.grup else 'Genel',
                    'birim': stok.urun.birim if stok.urun else 'Adet',
                    'otel_id': stok.otel_id,
                    'otel_adi': stok.otel.ad if stok.otel else 'Bilinmiyor',
                    'toplam_miktar': stok.toplam_miktar,
                    'kullanilan_miktar': stok.kullanilan_miktar,
                    'kalan_miktar': stok.kalan_miktar,
                    'kritik_seviye': stok.kritik_stok_seviyesi or 10,
                    'durum': durum,
                    'personeller': otel_personeller.get(stok.otel_id, []),
                    'son_guncelleme': stok.son_guncelleme.strftime('%d.%m.%Y %H:%M') if stok.son_guncelleme else ''
                })
            
            return jsonify({'success': True, 'zimmetler': result})
            
        except Exception as e:
            log_hata(e, modul='api_zimmet_listesi_filtreli')
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/urunler-stoklu', methods=['GET'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_urunler_stoklu():
        """Otel Zimmet Stok bilgisiyle birlikte ürün listesi
        
        OtelZimmetStok tablosundan stok bilgisi çeker.
        Tüm kat sorumluları için ORTAK stok havuzu.
        """
        try:
            from models import OtelZimmetStok, UrunGrup
            from utils.authorization import get_kullanici_otelleri
            
            oteller = get_kullanici_otelleri()
            otel_id = oteller[0].id if oteller else None
            
            if not otel_id:
                return jsonify({'success': True, 'urunler': []})
            
            # Tüm ürünleri getir
            urunler = Urun.query.filter_by(aktif=True).order_by(Urun.urun_adi).all()
            
            # Otel zimmet stoklarını al (ORTAK HAVUZ)
            otel_stoklar = {
                s.urun_id: s.kalan_miktar 
                for s in OtelZimmetStok.query.filter_by(otel_id=otel_id).all()
            }
            
            result = []
            for u in urunler:
                grup = db.session.get(UrunGrup, u.grup_id) if u.grup_id else None
                otel_stok = otel_stoklar.get(u.id, 0)
                
                result.append({
                    'id': u.id,
                    'urun_adi': u.urun_adi,
                    'birim': u.birim or 'Adet',
                    'grup_id': u.grup_id or 0,
                    'grup_adi': grup.grup_adi if grup else 'Genel',
                    'stok': otel_stok,  # Otel ortak zimmet stoğu
                    'personel_zimmet': otel_stok  # Aynı değer - ortak havuz
                })
            
            return jsonify({'success': True, 'urunler': result})
            
        except Exception as e:
            log_hata(e, modul='api_urunler_stoklu')
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/zimmet-ata', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_zimmet_ata():
        """Zimmet atama - Aynı gün birleştirme mantığıyla"""
        try:
            from models import PersonelZimmet, PersonelZimmetDetay, UrunStok
            from utils.fifo_servisler import FifoStokServisi
            from utils.authorization import get_kullanici_otelleri
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Geçersiz veri'}), 400
            
            personel_id = data.get('personel_id')
            urunler = data.get('urunler', [])
            
            if not personel_id or not urunler:
                return jsonify({'success': False, 'error': 'Personel ve ürün bilgisi gerekli'}), 400
            
            personel = db.session.get(Kullanici, personel_id)
            if not personel or not personel.otel_id:
                return jsonify({'success': False, 'error': 'Personel bulunamadı'}), 404
            
            otel_id = personel.otel_id
            bugun = get_kktc_now().date()
            
            # Bugün aynı personele yapılmış aktif zimmet var mı?
            mevcut_zimmet = PersonelZimmet.query.filter(
                PersonelZimmet.personel_id == personel_id,
                PersonelZimmet.durum == 'aktif',
                db.func.date(PersonelZimmet.zimmet_tarihi) == bugun
            ).first()
            
            if mevcut_zimmet:
                zimmet = mevcut_zimmet
                yeni_kayit = False
            else:
                zimmet = PersonelZimmet(
                    personel_id=personel_id,
                    teslim_eden_id=session['kullanici_id']
                )
                db.session.add(zimmet)
                db.session.flush()
                yeni_kayit = True
            
            # Stok kontrolü - UrunStok tablosundan (ekrandaki ile aynı kaynak)
            urun_ids = [u['urun_id'] for u in urunler]
            stoklar = {s.urun_id: s.mevcut_stok for s in UrunStok.query.filter(
                UrunStok.otel_id == otel_id,
                UrunStok.urun_id.in_(urun_ids)
            ).all()}
            
            yetersiz = []
            for u in urunler:
                mevcut = stoklar.get(u['urun_id'], 0)
                if u['miktar'] > mevcut:
                    urun = db.session.get(Urun, u['urun_id'])
                    yetersiz.append(f"{urun.urun_adi if urun else 'Bilinmiyor'}: istenen {u['miktar']}, mevcut {mevcut}")
            
            if yetersiz:
                return jsonify({'success': False, 'error': f"Stok yetersiz: {', '.join(yetersiz)}"}), 400
            
            # Ürünleri ekle
            for u in urunler:
                # Mevcut zimmet varsa, aynı ürün var mı kontrol et
                mevcut_detay = None
                if not yeni_kayit:
                    mevcut_detay = PersonelZimmetDetay.query.filter_by(
                        zimmet_id=zimmet.id,
                        urun_id=u['urun_id']
                    ).first()
                
                if mevcut_detay:
                    # Mevcut detaya ekle
                    mevcut_detay.miktar += u['miktar']
                    mevcut_detay.kalan_miktar += u['miktar']
                    detay_id = mevcut_detay.id
                else:
                    # Yeni detay oluştur
                    detay = PersonelZimmetDetay(
                        zimmet_id=zimmet.id,
                        urun_id=u['urun_id'],
                        miktar=u['miktar'],
                        kalan_miktar=u['miktar']
                    )
                    db.session.add(detay)
                    db.session.flush()
                    detay_id = detay.id
                
                # FIFO stok çıkışı (FIFO kaydı yoksa otomatik oluşturur)
                fifo_sonuc = FifoStokServisi.fifo_stok_cikis(
                    otel_id=otel_id,
                    urun_id=u['urun_id'],
                    miktar=u['miktar'],
                    islem_tipi='zimmet',
                    referans_id=detay_id,
                    kullanici_id=session['kullanici_id']
                )
                
                if not fifo_sonuc['success']:
                    raise Exception(f"Stok hatası: {fifo_sonuc['message']}")
            
            db.session.commit()
            
            mesaj = 'Zimmet başarıyla atandı!' if yeni_kayit else 'Mevcut zimmete eklendi!'
            
            log_islem('ekleme', 'personel_zimmet', {
                'zimmet_id': zimmet.id,
                'personel_id': personel_id,
                'urun_sayisi': len(urunler),
                'yeni_kayit': yeni_kayit
            })
            
            return jsonify({'success': True, 'message': mesaj, 'zimmet_id': zimmet.id})
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_zimmet_ata')
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/otel-zimmet-iptal', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
    def api_otel_zimmet_iptal():
        """Otel zimmet stoğundan ürün iptal et - Ana depoya geri ekler
        
        Sadece kullanılmamış (kalan_miktar >= iptal_miktar) ürünler iptal edilebilir.
        İptal edilen miktar ana depoya FIFO ile geri eklenir.
        """
        try:
            from models import OtelZimmetStok, UrunStok
            from utils.fifo_servisler import FifoStokServisi
            
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Geçersiz veri'}), 400
            
            otel_id = data.get('otel_id')
            urun_id = data.get('urun_id')
            iptal_miktar = data.get('miktar', 0)
            
            if not otel_id or not urun_id or iptal_miktar <= 0:
                return jsonify({'success': False, 'error': 'Otel, ürün ve miktar gerekli'}), 400
            
            # Otel zimmet stoğunu kontrol et
            stok = OtelZimmetStok.query.filter_by(otel_id=otel_id, urun_id=urun_id).first()
            
            if not stok:
                return jsonify({'success': False, 'error': 'Bu ürün için zimmet kaydı bulunamadı'}), 404
            
            # Kalan miktar kontrolü - sadece kullanılmamış miktar iptal edilebilir
            if stok.kalan_miktar < iptal_miktar:
                urun = db.session.get(Urun, urun_id)
                urun_adi = urun.urun_adi if urun else 'Bilinmiyor'
                return jsonify({
                    'success': False, 
                    'error': f'İptal edilecek miktar kalan stoktan fazla! {urun_adi}: Kalan {stok.kalan_miktar}, İptal istenen {iptal_miktar}'
                }), 400
            
            # Otel zimmet stoğundan düş
            stok.toplam_miktar -= iptal_miktar
            stok.kalan_miktar -= iptal_miktar
            stok.son_guncelleme = get_kktc_now()
            
            # Ana depoya FIFO ile geri ekle
            fifo_sonuc = FifoStokServisi.fifo_stok_giris(
                otel_id=otel_id,
                urun_id=urun_id,
                miktar=iptal_miktar,
                islem_tipi='zimmet_iade',
                referans_id=stok.id,
                kullanici_id=session.get('kullanici_id'),
                birim_fiyat=0  # İade olduğu için fiyat 0
            )
            
            if not fifo_sonuc.get('success'):
                db.session.rollback()
                return jsonify({
                    'success': False, 
                    'error': f'Ana depoya iade hatası: {fifo_sonuc.get("message", "Bilinmeyen hata")}'
                }), 400
            
            # Eğer stok tamamen sıfırlandıysa kaydı sil
            if stok.toplam_miktar <= 0 and stok.kalan_miktar <= 0:
                db.session.delete(stok)
            
            db.session.commit()
            
            # Güncel ana depo stoğunu al
            ana_depo_stok = UrunStok.query.filter_by(otel_id=otel_id, urun_id=urun_id).first()
            yeni_ana_depo_stok = ana_depo_stok.mevcut_stok if ana_depo_stok else 0
            
            urun = db.session.get(Urun, urun_id)
            urun_adi = urun.urun_adi if urun else 'Bilinmiyor'
            
            log_islem('iptal', 'otel_zimmet_stok', {
                'otel_id': otel_id,
                'urun_id': urun_id,
                'urun_adi': urun_adi,
                'iptal_miktar': iptal_miktar,
                'yeni_zimmet_toplam': stok.toplam_miktar if stok else 0,
                'yeni_ana_depo': yeni_ana_depo_stok
            })
            
            return jsonify({
                'success': True,
                'message': f'{iptal_miktar} adet {urun_adi} zimmet iptali yapıldı ve ana depoya iade edildi',
                'yeni_zimmet_toplam': stok.toplam_miktar if stok else 0,
                'yeni_zimmet_kalan': stok.kalan_miktar if stok else 0,
                'ana_depo_stok': yeni_ana_depo_stok
            })
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='api_otel_zimmet_iptal')
            return jsonify({'success': False, 'error': str(e)}), 500
