"""
Dolum Talebi Yönetimi Route'ları
"""

from flask import jsonify, request, session
from models import db, MinibarDolumTalebi, Oda, Kat, Kullanici
from utils.helpers import log_islem, log_hata
from utils.decorators import login_required, role_required
from datetime import datetime, timezone, timedelta


_SCHEMA_CHECKED = False


def _ensure_dolum_talebi_columns():
    """minibar_dolum_talepleri tablosunda goren_id, gorulme_tarihi, tamamlayan_id, kapatma_aciklamasi, iptal_aciklamasi, iptal_eden_id, iptal_tarihi kolonlarının varlığını garanti eder"""
    global _SCHEMA_CHECKED
    if _SCHEMA_CHECKED:
        return
    try:
        db.session.execute(db.text(
            "ALTER TABLE minibar_dolum_talepleri "
            "ADD COLUMN IF NOT EXISTS tamamlayan_id INTEGER REFERENCES kullanicilar(id) ON DELETE SET NULL, "
            "ADD COLUMN IF NOT EXISTS goren_id INTEGER REFERENCES kullanicilar(id) ON DELETE SET NULL, "
            "ADD COLUMN IF NOT EXISTS gorulme_tarihi TIMESTAMPTZ, "
            "ADD COLUMN IF NOT EXISTS kapatma_aciklamasi TEXT, "
            "ADD COLUMN IF NOT EXISTS iptal_aciklamasi TEXT, "
            "ADD COLUMN IF NOT EXISTS iptal_eden_id INTEGER REFERENCES kullanicilar(id) ON DELETE SET NULL, "
            "ADD COLUMN IF NOT EXISTS iptal_tarihi TIMESTAMPTZ"
        ))
        db.session.commit()
        _SCHEMA_CHECKED = True
    except Exception as e:
        db.session.rollback()
        log_hata(e, modul='dolum_talebi_schema_check')


def _talep_karsilanma_durumu(talep):
    """
    Mybar talebindeki ürünlerin odaya eklenip eklenmediğini kontrol eder.
    Talebin oluşturulma anından itibaren odaya eklenen veya ekstra eklenen ürünleri denetler.
    """
    from models import MinibarIslem, MinibarIslemDetay

    # İstenen ürünleri grupla ve say
    istenen_map = {}
    for d in talep.detaylar:
        if d.urun:
            if d.urun_id not in istenen_map:
                istenen_map[d.urun_id] = {
                    'urun_id': d.urun_id,
                    'urun_adi': d.urun.urun_adi,
                    'istenen_miktar': 0
                }
            istenen_map[d.urun_id]['istenen_miktar'] += 1

    if not istenen_map:
        return {
            'tam_karsilandi': True,
            'istenen_urunler': [],
            'eklenen_urunler': [],
            'eksik_urunler': []
        }

    tolerans_tarih = talep.talep_tarihi - timedelta(minutes=5) if talep.talep_tarihi else datetime.utcnow() - timedelta(days=1)

    islem_detaylari = (
        MinibarIslemDetay.query.join(MinibarIslem)
        .filter(
            MinibarIslem.oda_id == talep.oda_id,
            MinibarIslem.islem_tarihi >= tolerans_tarih,
            (
                (MinibarIslemDetay.eklenen_miktar.isnot(None) & (MinibarIslemDetay.eklenen_miktar > 0)) |
                (MinibarIslemDetay.ekstra_miktar.isnot(None) & (MinibarIslemDetay.ekstra_miktar > 0))
            )
        )
        .all()
    )

    eklenen_adetler = {}
    for detay in islem_detaylari:
        uid = detay.urun_id
        adet = (detay.ekstra_miktar or 0) if (detay.ekstra_miktar or 0) > 0 else (detay.eklenen_miktar or 0)
        eklenen_adetler[uid] = eklenen_adetler.get(uid, 0) + adet

    eklenen_urunler = []
    eksik_urunler = []

    for uid, item in istenen_map.items():
        eklenen_adet = eklenen_adetler.get(uid, 0)
        istenen_adet = item['istenen_miktar']
        if eklenen_adet >= istenen_adet:
            eklenen_urunler.append({
                'urun_id': uid,
                'urun_adi': item['urun_adi'],
                'eklenen_miktar': eklenen_adet,
                'istenen_miktar': istenen_adet
            })
        else:
            if eklenen_adet > 0:
                eklenen_urunler.append({
                    'urun_id': uid,
                    'urun_adi': item['urun_adi'],
                    'eklenen_miktar': eklenen_adet,
                    'istenen_miktar': istenen_adet
                })
            eksik_urunler.append({
                'urun_id': uid,
                'urun_adi': item['urun_adi'],
                'eklenen_miktar': eklenen_adet,
                'istenen_miktar': istenen_adet,
                'eksik_miktar': istenen_adet - eklenen_adet
            })

    tam_karsilandi = (len(eksik_urunler) == 0)

    return {
        'tam_karsilandi': tam_karsilandi,
        'istenen_urunler': [f"{item['urun_adi']} (x{item['istenen_miktar']})" for item in istenen_map.values()],
        'eklenen_urunler': eklenen_urunler,
        'eksik_urunler': eksik_urunler
    }


def _to_local_iso(dt):
    """Tarihi Kıbrıs/Türkiye saat dilimine (UTC+3) çevirip ISO string döndürür"""
    if not dt:
        return None
    local_tz = timezone(timedelta(hours=3))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(local_tz).isoformat()
    return dt.astimezone(local_tz).isoformat()


def _kullanici_ad_soyad(kullanici_obj, kullanici_id=None):
    """İlişkili kullanıcı nesnesi veya ID üzerinden ad soyad döndürür"""
    if kullanici_obj:
        return f"{kullanici_obj.ad} {kullanici_obj.soyad}".strip()
    if kullanici_id:
        k = db.session.get(Kullanici, kullanici_id)
        if k:
            return f"{k.ad} {k.soyad}".strip()
    return None


def register_dolum_talebi_routes(app):
    """Dolum talebi route'larını kaydet"""

    def _kullanici_otel_id_getir():
        """Kat sorumlusu ise atandığı otel_id'yi döndürür, diğer roller için None"""
        if session.get('rol') == 'kat_sorumlusu' and session.get('kullanici_id'):
            kullanici = db.session.get(Kullanici, session['kullanici_id'])
            if kullanici and kullanici.otel_id:
                return kullanici.otel_id
        return None

    def _depo_sorumlusu_otel_idleri_getir():
        """Depo sorumlusu ise yetkili olduğu otel ID listesini döndürür"""
        if session.get('rol') == 'depo_sorumlusu':
            try:
                from utils.authorization import get_kullanici_otelleri
                oteller = get_kullanici_otelleri()
                if oteller:
                    return [o.id for o in oteller]
            except Exception:
                pass
            if session.get('kullanici_id'):
                kullanici = db.session.get(Kullanici, session['kullanici_id'])
                if kullanici and kullanici.otel_id:
                    return [kullanici.otel_id]
        return None

    @app.route('/api/dolum-talepleri')
    @login_required
    @role_required('kat_sorumlusu', 'depo_sorumlusu', 'sistem_yoneticisi', 'admin', 'superadmin')
    def api_dolum_talepleri():
        """Bekleyen dolum taleplerini listele"""
        try:
            _ensure_dolum_talebi_columns()
            query = MinibarDolumTalebi.query.filter_by(durum='beklemede')
            otel_id = _kullanici_otel_id_getir()
            if otel_id:
                query = query.join(Oda, MinibarDolumTalebi.oda_id == Oda.id).join(Kat, Oda.kat_id == Kat.id).filter(Kat.otel_id == otel_id)

            talepler = query.order_by(
                MinibarDolumTalebi.talep_tarihi.desc()
            ).all()

            talep_listesi = []
            for talep in talepler:
                goren_ad = _kullanici_ad_soyad(getattr(talep, 'goren', None), getattr(talep, 'goren_id', None))
                
                # Ürün detaylarını grupla (adetli)
                urun_sayilari = {}
                for d in talep.detaylar:
                    if d.urun:
                        if d.urun_id not in urun_sayilari:
                            urun_sayilari[d.urun_id] = {
                                'urun_id': d.urun_id,
                                'urun_adi': d.urun.urun_adi,
                                'kategori': d.urun.kategori.kategori_adi if (d.urun and d.urun.kategori) else '',
                                'istenen_miktar': 0
                            }
                        urun_sayilari[d.urun_id]['istenen_miktar'] += 1

                talep_listesi.append({
                    'id': talep.id,
                    'oda_id': talep.oda_id,
                    'oda_no': talep.oda.oda_no,
                    'kat_adi': talep.oda.kat.kat_adi,
                    'talep_tarihi': _to_local_iso(talep.talep_tarihi),
                    'notlar': talep.notlar or '',
                    'secili_urunler': [d.urun.urun_adi for d in talep.detaylar if d.urun],
                    'secili_urun_detaylar': list(urun_sayilari.values()),
                    'goruldu': bool(talep.goren_id),
                    'goren_id': talep.goren_id,
                    'goren_ad': goren_ad,
                    'gorulme_tarihi': _to_local_iso(talep.gorulme_tarihi),
                })

            return jsonify({
                'success': True,
                'talepler': talep_listesi,
                'count': len(talep_listesi)
            })

        except Exception as e:
            log_hata(e, modul='dolum_talepleri_api')
            return jsonify({
                'success': False,
                'message': 'Talepler yüklenirken hata oluştu'
            }), 500

    @app.route('/api/dolum-talepleri-gorulmemis')
    @login_required
    @role_required('kat_sorumlusu')
    def api_dolum_talepleri_gorulmemis():
        """Kat sorumlusunun henüz onaylamadığı (görmediği) bekleyen Mybar taleplerini getirir"""
        try:
            _ensure_dolum_talebi_columns()
            query = MinibarDolumTalebi.query.filter(
                MinibarDolumTalebi.durum == 'beklemede',
                MinibarDolumTalebi.goren_id.is_(None)
            )
            otel_id = _kullanici_otel_id_getir()
            if otel_id:
                query = query.join(Oda, MinibarDolumTalebi.oda_id == Oda.id).join(Kat, Oda.kat_id == Kat.id).filter(Kat.otel_id == otel_id)

            talepler = query.order_by(MinibarDolumTalebi.talep_tarihi.asc()).all()
            liste = []
            for talep in talepler:
                urun_sayilari = {}
                for d in talep.detaylar:
                    if d.urun:
                        if d.urun_id not in urun_sayilari:
                            urun_sayilari[d.urun_id] = {
                                'urun_id': d.urun_id,
                                'urun_adi': d.urun.urun_adi,
                                'kategori': d.urun.kategori.kategori_adi if (d.urun and d.urun.kategori) else '',
                                'istenen_miktar': 0
                            }
                        urun_sayilari[d.urun_id]['istenen_miktar'] += 1

                liste.append({
                    'id': talep.id,
                    'oda_id': talep.oda_id,
                    'oda_no': talep.oda.oda_no if talep.oda else '',
                    'kat_adi': talep.oda.kat.kat_adi if (talep.oda and talep.oda.kat) else '',
                    'talep_tarihi': _to_local_iso(talep.talep_tarihi),
                    'notlar': talep.notlar or '',
                    'secili_urunler': [d.urun.urun_adi for d in talep.detaylar if d.urun],
                    'secili_urun_detaylar': list(urun_sayilari.values())
                })

            return jsonify({
                'success': True,
                'talepler': liste,
                'count': len(liste)
            })
        except Exception as e:
            log_hata(e, modul='dolum_talepleri_gorulmemis_api')
            return jsonify({
                'success': False,
                'talepler': [],
                'count': 0
            }), 500

    @app.route('/api/dolum-talebi-goruldu/<int:talep_id>', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu', 'depo_sorumlusu', 'sistem_yoneticisi', 'admin', 'superadmin')
    def api_dolum_talebi_goruldu(talep_id):
        """Kat sorumlusunun Mybar talebi dialogunu onayladığını (gördüğünü) kaydeder"""
        try:
            _ensure_dolum_talebi_columns()
            talep = db.session.get(MinibarDolumTalebi, talep_id)
            if not talep:
                return jsonify({
                    'success': False,
                    'message': 'Talep bulunamadı'
                }), 404

            kullanici_id = session.get('kullanici_id')
            simdi = datetime.utcnow()

            # İlk gören kat sorumlusunu kaydet (daha önce görülmediyse)
            if not talep.goren_id:
                talep.goren_id = kullanici_id
                talep.gorulme_tarihi = simdi

            # İlgili mybar_talebi bildirimlerini de okundu olarak işaretle
            try:
                db.session.execute(
                    db.text(
                        "UPDATE bildirimler SET okundu = TRUE, okunma_tarihi = :simdi "
                        "WHERE bildirim_tipi = 'mybar_talebi' AND okundu = FALSE "
                        "AND (gorev_id = :talep_id OR oda_id = :oda_id)"
                    ),
                    {'simdi': simdi, 'talep_id': talep.id, 'oda_id': talep.oda_id}
                )
            except Exception:
                pass

            db.session.commit()

            goren_ad = _kullanici_ad_soyad(getattr(talep, 'goren', None), talep.goren_id)

            log_islem('goruntuleme', 'dolum_talebi', {
                'talep_id': talep.id,
                'oda_id': talep.oda_id,
                'oda_no': talep.oda.oda_no if talep.oda else '',
                'goren_id': talep.goren_id,
                'goren_ad': goren_ad,
                'islem': 'mybar_talep_goruldu_onayi'
            })

            return jsonify({
                'success': True,
                'message': 'Talep görüldü olarak onaylandı',
                'talep_id': talep.id,
                'goren_id': talep.goren_id,
                'goren_ad': goren_ad,
                'gorulme_tarihi': _to_local_iso(talep.gorulme_tarihi)
            })
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='dolum_talebi_goruldu', extra_info={'talep_id': talep_id})
            return jsonify({
                'success': False,
                'message': 'Talep onaylanırken hata oluştu'
            }), 500

    @app.route('/api/kat-sorumlusu/mybar-karsila', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu', 'sistem_yoneticisi', 'admin', 'superadmin')
    def api_kat_sorumlusu_mybar_karsila():
        """
        Mybar talebindeki ürünleri odaya ekler.
        Tüketim = 0 (misafire tüketim yazılmaz), kat sorumlusu zimmet stoğundan düşer.
        """
        try:
            from utils.minibar_servisleri import (
                zimmet_stok_kontrol,
                zimmet_stok_dusu,
                tuketim_kaydet,
                minibar_stok_guncelle,
                ZimmetStokYetersizError,
            )
            from utils.logger import audit_create
            from models import Urun

            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Geçersiz veri gönderildi'}), 400

            talep_id = data.get('talep_id')
            oda_id = data.get('oda_id')
            urunler = data.get('urunler', [])

            if not talep_id or not oda_id or not urunler:
                return jsonify({'success': False, 'message': 'Eksik parametreler (talep_id, oda_id veya ürünler eksik)'}), 400

            talep = db.session.get(MinibarDolumTalebi, talep_id)
            if not talep:
                return jsonify({'success': False, 'message': 'Belirtilen talep bulunamadı'}), 404

            kullanici_id = session.get('kullanici_id')
            eklenen_sayisi = 0
            eklenen_kalemler = []

            # 1. Önce stok yeterlilik kontrolü
            for item in urunler:
                uid = int(item.get('urun_id', 0))
                miktar = int(item.get('miktar', 0))
                if miktar > 0:
                    zimmet_stok_kontrol(kullanici_id, uid, miktar)

            # 2. Stoğu düş ve tüketimsiz (miktar=0) olarak odaya ekle
            for item in urunler:
                uid = int(item.get('urun_id', 0))
                miktar = int(item.get('miktar', 0))
                if miktar <= 0:
                    continue

                # Kat sorumlusu zimmet stoğundan düş
                zimmet_stok_dusu(kullanici_id, uid, miktar)

                # Minibar oda stoğunu güncelle
                minibar_stok_guncelle(oda_id, uid, miktar, miktar)

                # Tüketimsiz olarak kaydet (tüketim=0, ekstra_miktar=miktar)
                tuketim_kaydet(
                    oda_id=oda_id,
                    urun_id=uid,
                    miktar=0,  # TÜKETİM YOK
                    personel_id=kullanici_id,
                    islem_tipi='ekstra_ekleme',
                    eklenen_miktar=miktar,
                    ekstra_miktar=miktar,
                    zimmet_detay_id=None
                )

                urun_obj = db.session.get(Urun, uid)
                urun_adi = urun_obj.urun_adi if urun_obj else f"Ürün #{uid}"
                eklenen_kalemler.append({
                    'urun_id': uid,
                    'urun_adi': urun_adi,
                    'miktar': miktar
                })
                eklenen_sayisi += miktar

            oda = db.session.get(Oda, oda_id)
            oda_no = oda.oda_no if oda else str(oda_id)

            # Audit log
            try:
                audit_create(
                    tablo_adi="minibar_dolum_talepleri",
                    kayit_id=talep_id,
                    yeni_deger={
                        "talep_id": talep_id,
                        "oda_no": oda_no,
                        "eklenen_kalemler": eklenen_kalemler,
                        "toplam_miktar": eklenen_sayisi
                    },
                    aciklama=f"Oda {oda_no} - Mybar talebi için {eklenen_sayisi} adet ürün odaya eklendi (Tüketimsiz, stoktan düşüldü)",
                )
            except Exception as audit_err:
                log_hata(audit_err, modul="mybar_karsila_audit")

            db.session.commit()

            return jsonify({
                'success': True,
                'message': f"{len(eklenen_kalemler)} kalem ({eklenen_sayisi} adet) ürün başarıyla odaya eklendi. (Stoğunuzdan düşüldü, tüketim yazılmadı)",
                'eklenen_sayisi': eklenen_sayisi,
                'eklenen_kalemler': eklenen_kalemler
            })

        except ZimmetStokYetersizError as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f"Yetersiz stok! Stoğunuzda {e.mevcut} adet var, gereken: {e.gereken}"
            }), 400
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul="mybar_karsila_api")
            return jsonify({
                'success': False,
                'message': f"İşlem sırasında hata oluştu: {str(e)}"
            }), 500

    @app.route('/api/dolum-talebi-durum-kontrol/<int:talep_id>', methods=['GET'])
    @login_required
    @role_required('kat_sorumlusu', 'depo_sorumlusu', 'sistem_yoneticisi', 'admin', 'superadmin')
    def api_dolum_talebi_durum_kontrol(talep_id):
        """Talebin ürünlerinin odaya eklenip eklenmediğini kontrol eder"""
        try:
            _ensure_dolum_talebi_columns()
            talep = db.session.get(MinibarDolumTalebi, talep_id)
            if not talep:
                return jsonify({'success': False, 'message': 'Talep bulunamadı'}), 404

            durum_ozet = _talep_karsilanma_durumu(talep)
            return jsonify({
                'success': True,
                'talep_id': talep.id,
                'oda_no': talep.oda.oda_no if talep.oda else '',
                'durum': talep.durum,
                **durum_ozet
            })
        except Exception as e:
            log_hata(e, modul='dolum_talebi_durum_kontrol')
            return jsonify({'success': False, 'message': 'Durum kontrolü sırasında hata oluştu'}), 500

    @app.route('/api/dolum-talebi-tamamla/<int:talep_id>', methods=['POST'])
    @login_required
    @role_required('kat_sorumlusu', 'sistem_yoneticisi', 'admin', 'superadmin')
    def api_dolum_talebi_tamamla(talep_id):
        """Dolum talebini tamamla / kapat"""
        try:
            _ensure_dolum_talebi_columns()
            talep = db.session.get(MinibarDolumTalebi, talep_id)

            if not talep:
                return jsonify({
                    'success': False,
                    'message': 'Talep bulunamadı'
                }), 404

            if talep.durum != 'beklemede':
                return jsonify({
                    'success': False,
                    'message': 'Bu talep zaten işlenmiş'
                }), 400

            data = request.get_json(silent=True) or {}
            onaylandi_eksik_kapat = data.get('onaylandi_eksik_kapat', False)
            aciklama = (data.get('aciklama') or data.get('notlar') or '').strip()

            durum_ozet = _talep_karsilanma_durumu(talep)
            tam_karsilandi = durum_ozet['tam_karsilandi']
            eksik_urunler = durum_ozet['eksik_urunler']

            if not tam_karsilandi:
                if not onaylandi_eksik_kapat:
                    return jsonify({
                        'success': False,
                        'eksik_var': True,
                        'eksik_urunler': eksik_urunler,
                        'message': 'Talep edilen ürünlerden bazıları henüz odaya eklenmemiş.'
                    }), 400

                # Eksik kapatma için açıklama zorunlu ve en az 3 kelime olmalı
                kelimeler = [w for w in aciklama.split() if len(w) > 1]
                if len(kelimeler) < 3 or len(aciklama) < 10:
                    return jsonify({
                        'success': False,
                        'eksik_var': True,
                        'eksik_urunler': eksik_urunler,
                        'message': 'Bu talebi kapatmak için eksik olan ürünler için açıklama yazmalısınız, aksi halde talep kapatılamaz. Bir ya da iki kelimelik açıklamalar kabul edilmez.'
                    }), 400

            simdi = datetime.utcnow()
            kullanici_id = session.get('kullanici_id')

            # Eğer görülme kaydı yoksa tamamlayan kişiyi aynı zamanda gören olarak da kaydet
            if not talep.goren_id:
                talep.goren_id = kullanici_id
                talep.gorulme_tarihi = simdi

            # Talebi tamamla
            talep.durum = 'tamamlandi'
            talep.tamamlanma_tarihi = simdi
            talep.tamamlayan_id = kullanici_id

            if not tam_karsilandi:
                talep.kapatma_aciklamasi = aciklama
                eksik_str = ', '.join(eksik_urunler)
                ek_not = f"Eksik Ürünle Kapatıldı ({eksik_str}) - Açıklama: {aciklama}"
                talep.notlar = f"{talep.notlar} | {ek_not}" if talep.notlar else ek_not
            else:
                talep.kapatma_aciklamasi = aciklama or "Tüm ürünler eksiksiz eklendi ve karşılandı."

            db.session.commit()

            # Log kaydı
            log_islem('guncelleme', 'dolum_talebi', {
                'talep_id': talep.id,
                'oda_id': talep.oda_id,
                'oda_no': talep.oda.oda_no if talep.oda else '',
                'durum': 'tamamlandi',
                'tamamlayan_id': kullanici_id,
                'tam_karsilandi': tam_karsilandi,
                'eksik_urunler': eksik_urunler,
                'kapatma_aciklamasi': talep.kapatma_aciklamasi
            })

            return jsonify({
                'success': True,
                'message': 'Mybar talebi başarıyla kapatıldı',
                'tam_karsilandi': tam_karsilandi
            })

        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='dolum_talebi_tamamla', extra_info={'talep_id': talep_id})
            return jsonify({
                'success': False,
                'message': 'Talep güncellenirken hata oluştu'
            }), 500

    @app.route('/api/dolum-talebi-iptal/<int:talep_id>', methods=['POST'])
    @login_required
    @role_required('depo_sorumlusu', 'sistem_yoneticisi', 'admin', 'superadmin')
    def api_dolum_talebi_iptal(talep_id):
        """Dolum talebini iptal et (SADECE Depo Sorumlusu ve Sistem Yöneticisi yetkisindedir)"""
        try:
            _ensure_dolum_talebi_columns()

            # Kat sorumlusu kesinlikle iptal edemez
            if session.get('rol') == 'kat_sorumlusu':
                return jsonify({
                    'success': False,
                    'message': 'Mybar talep iptali yalnızca Depo Sorumlusu ve Sistem Yöneticisi yetkisindedir.'
                }), 403

            talep = db.session.get(MinibarDolumTalebi, talep_id)

            if not talep:
                return jsonify({
                    'success': False,
                    'message': 'Talep bulunamadı'
                }), 404

            # İptal açıklaması zorunludur ve en az 3 kelime olmalıdır
            data = request.get_json(silent=True) or {}
            aciklama = (data.get('aciklama') or data.get('notlar') or '').strip()
            kelimeler = [w for w in aciklama.split() if len(w) > 1]
            if len(kelimeler) < 3 or len(aciklama) < 10:
                return jsonify({
                    'success': False,
                    'message': 'İptal edilen Mybar talepleri için en az 3 kelimelik geçerli bir açıklama girmek zorunludur. Bir ya da iki kelimelik açıklamalar kabul edilmez.'
                }), 400

            simdi = datetime.utcnow()
            kullanici_id = session.get('kullanici_id')
            if not talep.goren_id:
                talep.goren_id = kullanici_id
                talep.gorulme_tarihi = simdi

            # Talebi iptal et
            talep.durum = 'iptal'
            talep.iptal_eden_id = kullanici_id
            talep.iptal_tarihi = simdi
            talep.iptal_aciklamasi = aciklama
            talep.tamamlanma_tarihi = simdi
            talep.tamamlayan_id = kullanici_id
            talep.notlar = f"{talep.notlar} | İptal Nedeni: {aciklama}" if talep.notlar else f"İptal Nedeni: {aciklama}"
            db.session.commit()

            # Log kaydı
            log_islem('iptal', 'dolum_talebi', {
                'talep_id': talep.id,
                'oda_id': talep.oda_id,
                'durum': 'iptal',
                'iptal_eden_id': kullanici_id,
                'iptal_aciklamasi': aciklama
            })

            return jsonify({
                'success': True,
                'message': 'Mybar talebi iptal edildi'
            })

        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='dolum_talebi_iptal', extra_info={'talep_id': talep_id})
            return jsonify({
                'success': False,
                'message': 'Talep iptal edilirken hata oluştu'
            }), 500

    # Admin & Depo Sorumlusu Rapor/İzleme API'leri
    @app.route('/api/dolum-talepleri-admin')
    @login_required
    @role_required('sistem_yoneticisi', 'admin', 'depo_sorumlusu', 'superadmin')
    def api_dolum_talepleri_admin():
        """Sistem yöneticisi ve depo sorumlusu için tüm Mybar kişiselleştirme taleplerini ve görülme detaylarını listele"""
        try:
            _ensure_dolum_talebi_columns()
            durum = request.args.get('durum', 'tumu')
            gorulme = request.args.get('gorulme', 'tumu')  # tumu, goruldu, gorulmedi

            query = MinibarDolumTalebi.query

            depo_otel_idleri = _depo_sorumlusu_otel_idleri_getir()
            if depo_otel_idleri:
                query = query.join(Oda, MinibarDolumTalebi.oda_id == Oda.id).join(Kat, Oda.kat_id == Kat.id).filter(Kat.otel_id.in_(depo_otel_idleri))

            if durum != 'tumu':
                query = query.filter(MinibarDolumTalebi.durum == durum)

            if gorulme == 'goruldu':
                query = query.filter(MinibarDolumTalebi.goren_id.isnot(None))
            elif gorulme == 'gorulmedi':
                query = query.filter(MinibarDolumTalebi.goren_id.is_(None))

            talepler = query.order_by(
                MinibarDolumTalebi.talep_tarihi.desc()
            ).limit(200).all()

            talep_listesi = []
            for talep in talepler:
                goren_ad = _kullanici_ad_soyad(getattr(talep, 'goren', None), getattr(talep, 'goren_id', None))
                tamamlayan_ad = _kullanici_ad_soyad(getattr(talep, 'tamamlayan', None), getattr(talep, 'tamamlayan_id', None))
                iptal_eden_ad = _kullanici_ad_soyad(getattr(talep, 'iptal_eden', None), getattr(talep, 'iptal_eden_id', None))
                otel_adi = talep.oda.kat.otel.ad if (talep.oda and talep.oda.kat and talep.oda.kat.otel) else ''

                talep_dict = {
                    'id': talep.id,
                    'oda_id': talep.oda_id,
                    'oda_no': talep.oda.oda_no if talep.oda else '',
                    'kat_adi': talep.oda.kat.kat_adi if (talep.oda and talep.oda.kat) else '',
                    'otel_adi': otel_adi,
                    'talep_tarihi': _to_local_iso(talep.talep_tarihi),
                    'durum': talep.durum,
                    'notlar': talep.notlar or '',
                    'secili_urunler': [d.urun.urun_adi for d in talep.detaylar if d.urun],
                    'goruldu': bool(talep.goren_id),
                    'goren_id': talep.goren_id,
                    'goren_ad': goren_ad or '-',
                    'gorulme_tarihi': _to_local_iso(talep.gorulme_tarihi),
                    'tamamlanma_tarihi': _to_local_iso(talep.tamamlanma_tarihi),
                    'tamamlayan_ad': tamamlayan_ad or '-',
                    'kapatma_aciklamasi': getattr(talep, 'kapatma_aciklamasi', None) or '',
                    'iptal_aciklamasi': getattr(talep, 'iptal_aciklamasi', None) or '',
                    'iptal_eden_ad': iptal_eden_ad or '-',
                    'iptal_tarihi': _to_local_iso(getattr(talep, 'iptal_tarihi', None)),
                }

                talep_listesi.append(talep_dict)

            return jsonify({
                'success': True,
                'talepler': talep_listesi
            })

        except Exception as e:
            log_hata(e, modul='dolum_talepleri_admin_api')
            return jsonify({
                'success': False,
                'message': 'Talepler yüklenirken hata oluştu'
            }), 500

    @app.route('/api/dolum-talepleri-tamamlanan')
    @login_required
    @role_required('kat_sorumlusu', 'depo_sorumlusu', 'sistem_yoneticisi', 'admin', 'superadmin')
    def api_dolum_talepleri_tamamlanan():
        """Son 7 gün içinde tamamlanan dolum taleplerini listele"""
        try:
            _ensure_dolum_talebi_columns()
            from datetime import date

            # Son 7 günün başlangıcı
            yedi_gun_once = datetime.combine(date.today() - timedelta(days=7), datetime.min.time())

            # Tamamlanan talepleri getir
            query = MinibarDolumTalebi.query.filter(
                MinibarDolumTalebi.durum == 'tamamlandi',
                MinibarDolumTalebi.tamamlanma_tarihi >= yedi_gun_once
            )
            otel_id = _kullanici_otel_id_getir()
            if otel_id:
                query = query.join(Oda, MinibarDolumTalebi.oda_id == Oda.id).join(Kat, Oda.kat_id == Kat.id).filter(Kat.otel_id == otel_id)

            talepler = query.order_by(
                MinibarDolumTalebi.tamamlanma_tarihi.desc()
            ).all()

            talep_listesi = []
            for talep in talepler:
                goren_ad = _kullanici_ad_soyad(getattr(talep, 'goren', None), getattr(talep, 'goren_id', None))
                tamamlayan_ad = _kullanici_ad_soyad(getattr(talep, 'tamamlayan', None), getattr(talep, 'tamamlayan_id', None)) or "-"

                talep_listesi.append({
                    'id': talep.id,
                    'oda_id': talep.oda_id,
                    'oda_no': talep.oda.oda_no,
                    'kat_adi': talep.oda.kat.kat_adi,
                    'talep_tarihi': _to_local_iso(talep.talep_tarihi),
                    'tamamlanma_tarihi': _to_local_iso(talep.tamamlanma_tarihi),
                    'tamamlayan_ad': tamamlayan_ad,
                    'goren_ad': goren_ad or '-',
                    'gorulme_tarihi': _to_local_iso(talep.gorulme_tarihi),
                    'notlar': talep.notlar or '',
                    'secili_urunler': [d.urun.urun_adi for d in talep.detaylar if d.urun]
                })

            return jsonify({
                'success': True,
                'talepler': talep_listesi,
                'count': len(talep_listesi)
            })

        except Exception as e:
            log_hata(e, modul='dolum_talepleri_tamamlanan_api')
            return jsonify({
                'success': False,
                'message': 'Tamamlanan talepler yüklenirken hata oluştu'
            }), 500

    @app.route('/api/dolum-talepleri-istatistik')
    @login_required
    @role_required('sistem_yoneticisi', 'admin', 'depo_sorumlusu', 'superadmin')
    def api_dolum_talepleri_istatistik():
        """Dolum talepleri istatistikleri"""
        try:
            _ensure_dolum_talebi_columns()
            from datetime import date

            base_query = MinibarDolumTalebi.query
            depo_otel_idleri = _depo_sorumlusu_otel_idleri_getir()
            if depo_otel_idleri:
                base_query = base_query.join(Oda, MinibarDolumTalebi.oda_id == Oda.id).join(Kat, Oda.kat_id == Kat.id).filter(Kat.otel_id.in_(depo_otel_idleri))

            # Bekleyen talepler
            bekleyen = base_query.filter(MinibarDolumTalebi.durum == 'beklemede').count()

            # Henüz görülmeyen bekleyen talepler
            gorulmemis_bekleyen = base_query.filter(
                MinibarDolumTalebi.durum == 'beklemede',
                MinibarDolumTalebi.goren_id.is_(None)
            ).count()

            # Bugün tamamlanan
            bugun_baslangic = datetime.combine(date.today(), datetime.min.time())
            tamamlanan_bugun = base_query.filter(
                MinibarDolumTalebi.durum == 'tamamlandi',
                MinibarDolumTalebi.tamamlanma_tarihi >= bugun_baslangic
            ).count()

            # Bugün iptal edilen
            iptal_bugun = base_query.filter(
                MinibarDolumTalebi.durum == 'iptal',
                MinibarDolumTalebi.tamamlanma_tarihi >= bugun_baslangic
            ).count()

            return jsonify({
                'success': True,
                'bekleyen': bekleyen,
                'gorulmemis_bekleyen': gorulmemis_bekleyen,
                'tamamlanan_bugun': tamamlanan_bugun,
                'iptal_bugun': iptal_bugun
            })

        except Exception as e:
            log_hata(e, modul='dolum_talepleri_istatistik')
            return jsonify({
                'success': False,
                'message': 'İstatistikler yüklenirken hata oluştu'
            }), 500

    @app.route('/mybar-sunum')
    def mybar_sunum():
        """Mybar İş Akışı Görsel Sunumu ve PDF Çıktı Sayfası"""
        from flask import render_template
        return render_template('mybar_sunum.html')

