"""
Misafir QR Kod Route'ları
"""

from flask import jsonify, request, render_template, session
from models import db, MinibarDolumTalebi, MinibarDolumTalebiDetay, Urun, Kat, OdaTipi, Setup, SetupIcerik, oda_tipi_setup
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from utils.qr_service import QRKodService
from utils.rate_limiter import QRRateLimiter, get_client_ip
from utils.helpers import log_islem, log_hata
from utils.bildirim_service import mybar_talebi_bildirimi
from utils.translate_service import format_guest_note_for_staff
import bleach


def register_misafir_qr_routes(app):
    """Misafir QR route'larını kaydet"""

    def _oda_urun_gruplari_olustur(oda):
        """Odadaki tüm setup içeriklerini UrunGrup bazında gruplar (N+1 stok sorgusu olmadan).

        Returns:
            list[dict]: [{grup_id, grup_adi, urunler:[{urun_id,urun_adi,birim,setup_adet}]}]
            Setup/oda tipi tanımsızsa boş liste.
        """
        try:
            if not oda or not getattr(oda, 'oda_tipi_id', None):
                return []

            oda_tipi = db.session.get(OdaTipi, oda.oda_tipi_id)
            if not oda_tipi:
                return []

            kat = oda.kat or (db.session.get(Kat, oda.kat_id) if getattr(oda, 'kat_id', None) else None)
            if not kat:
                return []

            otel_id = kat.otel_id
            setup_rows = db.session.execute(
                db.select(oda_tipi_setup.c.setup_id).where(
                    and_(
                        oda_tipi_setup.c.otel_id == otel_id,
                        oda_tipi_setup.c.oda_tipi_id == oda_tipi.id,
                    )
                )
            ).fetchall()
            setup_ids = [row[0] for row in setup_rows]

            if setup_ids:
                setuplar = Setup.query.filter(Setup.id.in_(setup_ids), Setup.aktif).all()
            else:
                setuplar = [s for s in oda_tipi.setuplar if s.aktif]

            aktif_setup_ids = [s.id for s in setuplar if s.aktif]
            if not aktif_setup_ids:
                return []

            icerikler = (
                SetupIcerik.query.options(joinedload(SetupIcerik.urun).joinedload(Urun.grup))
                .filter(SetupIcerik.setup_id.in_(aktif_setup_ids))
                .join(Urun)
                .filter(Urun.aktif)
                .all()
            )
        except Exception as e:
            log_hata(e, modul='misafir_qr_oda_setup')
            return []

        # Tüm setupların ürün listesini tekilleştir (aynı ürün birden fazla setup'ta varsa max adet)
        tekil = {}
        for icerik in icerikler:
            urun = icerik.urun
            if not urun:
                continue
            uid = urun.id
            adet = icerik.adet or 1
            grup = urun.grup
            mevcut = tekil.get(uid)
            if mevcut is None:
                tekil[uid] = {
                    'urun_id': uid,
                    'urun_adi': urun.urun_adi or '',
                    'birim': urun.birim or 'Adet',
                    'setup_adet': adet,
                    'grup_id': grup.id if grup else None,
                    'grup_adi': grup.grup_adi if grup else 'Diğer',
                }
            else:
                mevcut['setup_adet'] = max(mevcut['setup_adet'], adet)

        if not tekil:
            return []

        # UrunGrup'a göre grupla
        grup_harita = {}
        sira = []
        for u in tekil.values():
            key = u.get('grup_adi') or 'Diğer'
            if key not in grup_harita:
                grup_harita[key] = {'grup_id': u.get('grup_id'), 'grup_adi': key, 'urunler': []}
                sira.append(key)
            grup_harita[key]['urunler'].append({
                'urun_id': u['urun_id'],
                'urun_adi': u['urun_adi'],
                'birim': u['birim'],
                'setup_adet': u['setup_adet'],
            })
        return [grup_harita[k] for k in sira]

    
    @app.route('/qr/<token>')
    def qr_redirect(token):
        """QR kod yönlendirme - Akıllı routing"""
        try:
            # Rate limit kontrolü (Proxy uyumlu client IP)
            ip = get_client_ip() or request.remote_addr
            if not QRRateLimiter.check_qr_scan_limit(ip):  # type: ignore[arg-type]
                return render_template('errors/429.html'), 429
            
            # Token'ı doğrula
            oda = QRKodService.validate_token(token)
            
            if not oda:
                # Geçersiz token logu — log hatası 404 döndürmeyi engellemesin
                try:
                    QRKodService.log_qr_scan(
                        oda_id=None,
                        okutma_tipi='misafir_okutma',
                        kullanici_id=None,
                        basarili=False,
                        hata_mesaji='Geçersiz token'
                    )
                except Exception as log_err:
                    log_hata(log_err, modul='qr_redirect_invalid_token_log')
                return render_template('errors/404.html',
                                     message='Geçersiz QR kod'), 404
            
            # Kullanıcı kat sorumlusu mu kontrol et
            if 'kullanici_id' in session and session.get('rol') == 'kat_sorumlusu':
                # Kat sorumlusu - minibar işlemleri sayfasına yönlendir
                return render_template('kat_sorumlusu/qr_redirect.html',
                                     oda=oda,
                                     token=token)
            else:
                # Misafir - dolum talebi sayfasına yönlendir
                otel_logo = None
                otel_adi = None
                
                if oda.kat and oda.kat.otel:
                    otel_logo = oda.kat.otel.logo
                    otel_adi = oda.kat.otel.ad
                
                return render_template('misafir_dolum_talebi.html',
                                     oda=oda,
                                     token=token,
                                     otel_logo=otel_logo,
                                     otel_adi=otel_adi,
                                     urun_gruplari=_oda_urun_gruplari_olustur(oda))
                
        except Exception as e:
            log_hata(e, modul='qr_redirect', extra_info={'token': token[:10]})
            return render_template('errors/500.html'), 500
    
    
    @app.route('/misafir/dolum-talebi/<token>', methods=['GET', 'POST'])
    def misafir_dolum_talebi(token):
        """Misafir dolum talebi sayfası"""
        is_post = request.method == 'POST'
        try:
            # Rate limit kontrolü (Proxy uyumlu client IP)
            ip = get_client_ip() or request.remote_addr
            if not QRRateLimiter.check_qr_scan_limit(ip):  # type: ignore[arg-type]
                if is_post:
                    return jsonify({
                        'success': False,
                        'message': 'Çok fazla deneme. Lütfen 1 dakika bekleyin.'
                    }), 429
                return render_template('errors/429.html'), 429
            
            # Token'ı doğrula
            oda = QRKodService.validate_token(token)
            
            if not oda:
                if is_post:
                    return jsonify({
                        'success': False,
                        'message': 'Geçersiz QR kod'
                    }), 404
                return render_template('errors/404.html', message='Geçersiz QR kod'), 404
            
            # Otel logosunu al (Oda -> Kat -> Otel)
            otel_logo = None
            otel_adi = None
            
            if oda.kat and oda.kat.otel:
                otel_logo = oda.kat.otel.logo
                otel_adi = oda.kat.otel.ad
            
            if is_post:
                # Dolum talebi kaydet
                notlar = request.form.get('notlar', '').strip()
                secili_urun_idler = request.form.getlist('secili_urunler')

                # Input sanitization
                if notlar:
                    notlar = bleach.clean(notlar, tags=[], strip=True)
                    if len(notlar) > 500:
                        return jsonify({
                            'success': False,
                            'message': 'Not maksimum 500 karakter olabilir'
                        }), 400

                # Seçili ürünleri validate et — en az 1 ürün veya not olmalı
                gecerli_urun_idler = set()
                for g in _oda_urun_gruplari_olustur(oda):
                    for u in g.get('urunler', []):
                        gecerli_urun_idler.add(int(u['urun_id']))

                onaylanan_urun_idler = []
                for sid in secili_urun_idler:
                    try:
                        uid = int(sid)
                    except (TypeError, ValueError):
                        continue
                    if uid in gecerli_urun_idler and uid not in onaylanan_urun_idler:
                        onaylanan_urun_idler.append(uid)

                if not onaylanan_urun_idler and not notlar:
                    return jsonify({
                        'success': False,
                        'message': 'En az bir ürün seçmeli veya not eklemelisiniz.'
                    }), 400

                # Misafir notunu hangi dilde olursa olsun kat sorumlusu için Türkçe'ye çevir
                cevrilmis_not = format_guest_note_for_staff(notlar) if notlar else None

                # Talep oluştur
                talep = MinibarDolumTalebi(
                    oda_id=oda.id,
                    durum='beklemede',
                    notlar=cevrilmis_not if cevrilmis_not else None
                )
                db.session.add(talep)
                db.session.flush()  # talep.id al

                # Seçili ürünleri detay olarak ekle
                for uid in onaylanan_urun_idler:
                    db.session.add(MinibarDolumTalebiDetay(
                        talep_id=talep.id,
                        urun_id=uid
                    ))

                db.session.commit()

                # QR okutma logu — hata oluşursa kaydedilmiş talebi bozmasın
                try:
                    QRKodService.log_qr_scan(
                        oda_id=oda.id,
                        okutma_tipi='misafir_okutma',
                        kullanici_id=None,
                        basarili=True
                    )
                except Exception as qr_log_err:
                    log_hata(qr_log_err, modul='misafir_dolum_qr_log')

                # Log kaydı
                try:
                    log_islem('ekleme', 'dolum_talebi', {
                        'oda_id': oda.id,
                        'oda_no': oda.oda_no,
                        'talep_id': talep.id,
                        'urun_sayisi': len(onaylanan_urun_idler)
                    })
                except Exception as islem_log_err:
                    log_hata(islem_log_err, modul='misafir_dolum_islem_log')

                # Push bildirim gönder
                try:
                    otel_id = oda.kat.otel.id if oda.kat and oda.kat.otel else None
                    kat_adi = oda.kat.kat_adi if oda.kat else 'Bilinmeyen Kat'
                    secili_urun_adi = [d.urun.urun_adi for d in talep.detaylar if d.urun]
                    mybar_talebi_bildirimi(
                        otel_id=otel_id,  # type: ignore[arg-type]
                        oda_no=oda.oda_no,
                        kat_adi=kat_adi,
                        oda_id=oda.id,
                        notlar=cevrilmis_not,
                        secili_urunler=secili_urun_adi,
                        talep_id=talep.id,
                    )
                except Exception as bildirim_err:
                    log_hata(bildirim_err, modul='mybar_talebi_bildirim')

                return jsonify({
                    'success': True,
                    'message': 'Mybar kişiselleştirme talebiniz başarıyla gönderildi!'
                })

            else:  # GET
                urun_gruplari = _oda_urun_gruplari_olustur(oda)
                return render_template('misafir_dolum_talebi.html',
                                     oda=oda,
                                     token=token,
                                     otel_logo=otel_logo,
                                     otel_adi=otel_adi,
                                     urun_gruplari=urun_gruplari)
                
        except Exception as e:
            db.session.rollback()
            log_hata(e, modul='misafir_dolum_talebi', extra_info={'token': token[:10]})
            if is_post:
                return jsonify({
                    'success': False,
                    'message': 'Talep gönderilirken hata oluştu'
                }), 500
            return render_template('errors/500.html'), 500
