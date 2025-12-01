"""
Celery Asenkron İşlemler Konfigürasyonu
Fiyatlandırma ve Karlılık Sistemi için ağır hesaplamaları arka planda çalıştırır
"""

from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
import os

# Logging
logger = logging.getLogger(__name__)

# Celery instance oluştur
def make_celery(app=None):
    """Flask app ile entegre Celery instance oluştur"""
    
    # Config'den Celery ayarlarını al
    broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    
    celery = Celery(
        'minibar_takip',
        broker=broker_url,
        backend=result_backend
    )
    
    # Celery konfigürasyonu
    celery.conf.update(
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 saat max
        task_soft_time_limit=3000,  # 50 dakika soft limit
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
    )
    
    # Flask app context'i varsa ekle
    if app:
        celery.conf.update(app.config)
        
        class ContextTask(celery.Task):
            """Flask app context'i ile çalışan task"""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
    
    return celery

# Celery instance (Flask app olmadan da çalışabilir)
celery = make_celery()


# ============================================
# ASENKRON TASK'LAR
# ============================================

@celery.task(bind=True, name='fiyatlandirma.donemsel_kar_hesapla')
def donemsel_kar_hesapla_async(self, otel_id, baslangic_tarihi, bitis_tarihi, donem_tipi='gunluk'):
    """
    Dönemsel kar hesaplama - Asenkron
    
    Args:
        otel_id: Otel ID
        baslangic_tarihi: Başlangıç tarihi (ISO format string)
        bitis_tarihi: Bitiş tarihi (ISO format string)
        donem_tipi: Dönem tipi (gunluk, haftalik, aylik)
    
    Returns:
        dict: {
            'status': 'success' | 'error',
            'analiz_id': int,
            'message': str,
            'data': dict
        }
    """
    try:
        # Flask app context'i gerekli
        from app import app, db
        from models import DonemselKarAnalizi, MinibarIslemDetay, MinibarIslem
        from sqlalchemy import func
        from datetime import datetime
        
        with app.app_context():
            logger.info(f"Dönemsel kar hesaplama başladı - Otel: {otel_id}, Dönem: {donem_tipi}")
            
            # Tarih parse
            baslangic = datetime.fromisoformat(baslangic_tarihi)
            bitis = datetime.fromisoformat(bitis_tarihi)
            
            # Toplam gelir hesapla (satış fiyatı * miktar)
            toplam_gelir_query = db.session.query(
                func.sum(MinibarIslemDetay.satis_fiyati * MinibarIslemDetay.tuketim)
            ).join(
                MinibarIslem
            ).filter(
                MinibarIslem.otel_id == otel_id,
                MinibarIslem.islem_tarihi.between(baslangic, bitis),
                MinibarIslemDetay.satis_fiyati.isnot(None)
            )
            
            toplam_gelir = toplam_gelir_query.scalar() or Decimal('0')
            
            # Toplam maliyet hesapla (alış fiyatı * miktar)
            toplam_maliyet_query = db.session.query(
                func.sum(MinibarIslemDetay.alis_fiyati * MinibarIslemDetay.tuketim)
            ).join(
                MinibarIslem
            ).filter(
                MinibarIslem.otel_id == otel_id,
                MinibarIslem.islem_tarihi.between(baslangic, bitis),
                MinibarIslemDetay.alis_fiyati.isnot(None)
            )
            
            toplam_maliyet = toplam_maliyet_query.scalar() or Decimal('0')
            
            # Net kar ve kar marjı hesapla
            net_kar = toplam_gelir - toplam_maliyet
            kar_marji = (net_kar / toplam_gelir * 100) if toplam_gelir > 0 else Decimal('0')
            
            # Detaylı analiz verisi
            analiz_verisi = {
                'toplam_islem': db.session.query(func.count(MinibarIslem.id)).filter(
                    MinibarIslem.otel_id == otel_id,
                    MinibarIslem.islem_tarihi.between(baslangic, bitis)
                ).scalar(),
                'ortalama_islem_degeri': float(toplam_gelir / db.session.query(func.count(MinibarIslem.id)).filter(
                    MinibarIslem.otel_id == otel_id,
                    MinibarIslem.islem_tarihi.between(baslangic, bitis)
                ).scalar()) if db.session.query(func.count(MinibarIslem.id)).filter(
                    MinibarIslem.otel_id == otel_id,
                    MinibarIslem.islem_tarihi.between(baslangic, bitis)
                ).scalar() > 0 else 0,
                'hesaplama_tarihi': datetime.now(timezone.utc).isoformat()
            }
            
            # Veritabanına kaydet
            analiz = DonemselKarAnalizi(
                otel_id=otel_id,
                donem_tipi=donem_tipi,
                baslangic_tarihi=baslangic.date(),
                bitis_tarihi=bitis.date(),
                toplam_gelir=toplam_gelir,
                toplam_maliyet=toplam_maliyet,
                net_kar=net_kar,
                kar_marji=kar_marji,
                analiz_verisi=analiz_verisi
            )
            
            db.session.add(analiz)
            db.session.commit()
            
            logger.info(f"Dönemsel kar hesaplama tamamlandı - Analiz ID: {analiz.id}")
            
            return {
                'status': 'success',
                'analiz_id': analiz.id,
                'message': 'Dönemsel kar analizi başarıyla tamamlandı',
                'data': {
                    'toplam_gelir': float(toplam_gelir),
                    'toplam_maliyet': float(toplam_maliyet),
                    'net_kar': float(net_kar),
                    'kar_marji': float(kar_marji)
                }
            }
            
    except Exception as e:
        logger.error(f"Dönemsel kar hesaplama hatası: {str(e)}")
        return {
            'status': 'error',
            'message': f'Hata: {str(e)}',
            'data': None
        }


@celery.task(bind=True, name='fiyatlandirma.tuketim_trendi_guncelle')
def tuketim_trendi_guncelle_async(self, otel_id=None, donem='aylik'):
    """
    Tüketim trendi güncelleme - Asenkron
    Ürün bazlı tüketim trendlerini hesaplar ve günceller
    
    Args:
        otel_id: Otel ID (None ise tüm oteller)
        donem: Trend dönemi (haftalik, aylik, yillik)
    
    Returns:
        dict: {
            'status': 'success' | 'error',
            'message': str,
            'data': dict
        }
    """
    try:
        from app import app, db
        from models import Urun, MinibarIslemDetay, MinibarIslem
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        with app.app_context():
            logger.info(f"Tüketim trendi güncelleme başladı - Otel: {otel_id}, Dönem: {donem}")
            
            # Dönem aralığını belirle
            bugun = datetime.now(timezone.utc)
            if donem == 'haftalik':
                baslangic = bugun - timedelta(days=7)
                onceki_baslangic = baslangic - timedelta(days=7)
            elif donem == 'aylik':
                baslangic = bugun - timedelta(days=30)
                onceki_baslangic = baslangic - timedelta(days=30)
            else:  # yillik
                baslangic = bugun - timedelta(days=365)
                onceki_baslangic = baslangic - timedelta(days=365)
            
            # Ürünleri al
            urun_query = Urun.query.filter_by(aktif=True)
            urunler = urun_query.all()
            
            trend_verileri = []
            
            for urun in urunler:
                # Mevcut dönem tüketimi
                mevcut_tuketim_query = db.session.query(
                    func.sum(MinibarIslemDetay.tuketim)
                ).join(
                    MinibarIslem
                ).filter(
                    MinibarIslemDetay.urun_id == urun.id,
                    MinibarIslem.islem_tarihi.between(baslangic, bugun)
                )
                
                if otel_id:
                    mevcut_tuketim_query = mevcut_tuketim_query.filter(
                        MinibarIslem.otel_id == otel_id
                    )
                
                mevcut_tuketim = mevcut_tuketim_query.scalar() or 0
                
                # Önceki dönem tüketimi
                onceki_tuketim_query = db.session.query(
                    func.sum(MinibarIslemDetay.tuketim)
                ).join(
                    MinibarIslem
                ).filter(
                    MinibarIslemDetay.urun_id == urun.id,
                    MinibarIslem.islem_tarihi.between(onceki_baslangic, baslangic)
                )
                
                if otel_id:
                    onceki_tuketim_query = onceki_tuketim_query.filter(
                        MinibarIslem.otel_id == otel_id
                    )
                
                onceki_tuketim = onceki_tuketim_query.scalar() or 0
                
                # Trend hesapla
                if onceki_tuketim > 0:
                    degisim_orani = ((mevcut_tuketim - onceki_tuketim) / onceki_tuketim) * 100
                else:
                    degisim_orani = 100 if mevcut_tuketim > 0 else 0
                
                # Trend yönü
                if degisim_orani > 10:
                    trend_yonu = 'yukselen'
                elif degisim_orani < -10:
                    trend_yonu = 'dusen'
                else:
                    trend_yonu = 'sabit'
                
                trend_verileri.append({
                    'urun_id': urun.id,
                    'urun_adi': urun.urun_adi,
                    'mevcut_tuketim': mevcut_tuketim,
                    'onceki_tuketim': onceki_tuketim,
                    'degisim_orani': round(degisim_orani, 2),
                    'trend_yonu': trend_yonu
                })
            
            logger.info(f"Tüketim trendi güncelleme tamamlandı - {len(trend_verileri)} ürün işlendi")
            
            return {
                'status': 'success',
                'message': f'{len(trend_verileri)} ürün için tüketim trendi güncellendi',
                'data': {
                    'donem': donem,
                    'toplam_urun': len(trend_verileri),
                    'yukselen': len([t for t in trend_verileri if t['trend_yonu'] == 'yukselen']),
                    'dusen': len([t for t in trend_verileri if t['trend_yonu'] == 'dusen']),
                    'sabit': len([t for t in trend_verileri if t['trend_yonu'] == 'sabit']),
                    'trendler': trend_verileri[:10]  # İlk 10 ürün
                }
            }
            
    except Exception as e:
        logger.error(f"Tüketim trendi güncelleme hatası: {str(e)}")
        return {
            'status': 'error',
            'message': f'Hata: {str(e)}',
            'data': None
        }


@celery.task(bind=True, name='fiyatlandirma.stok_devir_guncelle')
def stok_devir_guncelle_async(self, otel_id=None):
    """
    Stok devir hızı güncelleme - Asenkron
    Ürün bazlı stok devir hızlarını hesaplar ve günceller
    
    Args:
        otel_id: Otel ID (None ise tüm oteller)
    
    Returns:
        dict: {
            'status': 'success' | 'error',
            'message': str,
            'data': dict
        }
    """
    try:
        from app import app, db
        from models import UrunStok, StokHareket
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        with app.app_context():
            logger.info(f"Stok devir hızı güncelleme başladı - Otel: {otel_id}")
            
            # Son 30 günlük dönem
            bugun = datetime.now(timezone.utc)
            baslangic = bugun - timedelta(days=30)
            
            # Stok kayıtlarını al
            stok_query = UrunStok.query
            if otel_id:
                stok_query = stok_query.filter_by(otel_id=otel_id)
            
            stoklar = stok_query.all()
            guncellenen_sayisi = 0
            
            for stok in stoklar:
                try:
                    # Son 30 günlük çıkışları hesapla
                    cikis_toplam = db.session.query(
                        func.sum(StokHareket.miktar)
                    ).filter(
                        StokHareket.urun_id == stok.urun_id,
                        StokHareket.hareket_tipi.in_(['cikis', 'fire']),
                        StokHareket.islem_tarihi.between(baslangic, bugun)
                    ).scalar() or 0
                    
                    # Stok devir hızını güncelle
                    stok.son_30gun_cikis = cikis_toplam
                    
                    # Devir hızı = Çıkış / Ortalama Stok
                    if stok.mevcut_stok > 0:
                        stok.stok_devir_hizi = Decimal(str(cikis_toplam)) / Decimal(str(stok.mevcut_stok))
                    else:
                        stok.stok_devir_hizi = Decimal('0')
                    
                    stok.son_guncelleme_tarihi = bugun
                    guncellenen_sayisi += 1
                    
                except Exception as e:
                    logger.warning(f"Stok devir güncelleme hatası (Ürün: {stok.urun_id}): {str(e)}")
                    continue
            
            db.session.commit()
            
            logger.info(f"Stok devir hızı güncelleme tamamlandı - {guncellenen_sayisi} stok güncellendi")
            
            return {
                'status': 'success',
                'message': f'{guncellenen_sayisi} stok kaydı güncellendi',
                'data': {
                    'toplam_stok': len(stoklar),
                    'guncellenen': guncellenen_sayisi,
                    'donem': '30_gun'
                }
            }
            
    except Exception as e:
        logger.error(f"Stok devir güncelleme hatası: {str(e)}")
        return {
            'status': 'error',
            'message': f'Hata: {str(e)}',
            'data': None
        }


# ============================================
# PERİYODİK TASK'LAR (Celery Beat için)
# ============================================

@celery.task(name='fiyatlandirma.gunluk_kar_analizi')
def gunluk_kar_analizi_task():
    """
    Günlük kar analizi - Otomatik çalışır (Celery Beat)
    Her gün gece yarısı tüm oteller için önceki günün kar analizini yapar
    """
    try:
        from app import app, db
        from models import Otel
        from datetime import datetime, timedelta
        
        with app.app_context():
            logger.info("Günlük kar analizi başladı")
            
            # Dün
            bugun = datetime.now(timezone.utc).date()
            dun = bugun - timedelta(days=1)
            
            # Tüm aktif oteller
            oteller = Otel.query.filter_by(aktif=True).all()
            
            for otel in oteller:
                # Asenkron task başlat
                donemsel_kar_hesapla_async.delay(
                    otel_id=otel.id,
                    baslangic_tarihi=dun.isoformat(),
                    bitis_tarihi=dun.isoformat(),
                    donem_tipi='gunluk'
                )
            
            logger.info(f"Günlük kar analizi task'ları başlatıldı - {len(oteller)} otel")
            
            return {
                'status': 'success',
                'message': f'{len(oteller)} otel için günlük kar analizi başlatıldı'
            }
            
    except Exception as e:
        logger.error(f"Günlük kar analizi task hatası: {str(e)}")
        return {
            'status': 'error',
            'message': f'Hata: {str(e)}'
        }


@celery.task(name='fiyatlandirma.haftalik_trend_analizi')
def haftalik_trend_analizi_task():
    """
    Haftalık trend analizi - Otomatik çalışır (Celery Beat)
    Her Pazartesi sabahı tüm oteller için haftalık trend analizi yapar
    """
    try:
        from app import app, db
        from models import Otel
        
        with app.app_context():
            logger.info("Haftalık trend analizi başladı")
            
            # Tüm aktif oteller
            oteller = Otel.query.filter_by(aktif=True).all()
            
            for otel in oteller:
                # Asenkron task başlat
                tuketim_trendi_guncelle_async.delay(
                    otel_id=otel.id,
                    donem='haftalik'
                )
            
            logger.info(f"Haftalık trend analizi task'ları başlatıldı - {len(oteller)} otel")
            
            return {
                'status': 'success',
                'message': f'{len(oteller)} otel için haftalık trend analizi başlatıldı'
            }
            
    except Exception as e:
        logger.error(f"Haftalık trend analizi task hatası: {str(e)}")
        return {
            'status': 'error',
            'message': f'Hata: {str(e)}'
        }


@celery.task(name='fiyatlandirma.aylik_stok_devir_analizi')
def aylik_stok_devir_analizi_task():
    """
    Aylık stok devir analizi - Otomatik çalışır (Celery Beat)
    Her ayın ilk günü tüm oteller için stok devir hızını günceller
    """
    try:
        from app import app, db
        from models import Otel
        
        with app.app_context():
            logger.info("Aylık stok devir analizi başladı")
            
            # Tüm aktif oteller
            oteller = Otel.query.filter_by(aktif=True).all()
            
            for otel in oteller:
                # Asenkron task başlat
                stok_devir_guncelle_async.delay(otel_id=otel.id)
            
            logger.info(f"Aylık stok devir analizi task'ları başlatıldı - {len(oteller)} otel")
            
            return {
                'status': 'success',
                'message': f'{len(oteller)} otel için stok devir analizi başlatıldı'
            }
            
    except Exception as e:
        logger.error(f"Aylık stok devir analizi task hatası: {str(e)}")
        return {
            'status': 'error',
            'message': f'Hata: {str(e)}'
        }


# ============================================
# GÖREVLENDİRME SİSTEMİ TASK'LARI
# ============================================

@celery.task(name='gorevlendirme.gunluk_yukleme_gorevleri_olustur')
def gunluk_yukleme_gorevleri_olustur_task():
    """
    Günlük yükleme görevleri oluşturma - Her gün 00:01'de çalışır
    Tüm depo sorumluları için In House ve Arrivals yükleme görevleri oluşturur
    """
    try:
        from app import app
        from utils.yukleme_gorev_service import YuklemeGorevService
        from datetime import date
        
        with app.app_context():
            logger.info("Günlük yükleme görevleri oluşturuluyor...")
            
            tarih = date.today()
            result = YuklemeGorevService.create_daily_upload_tasks(tarih)
            
            logger.info(f"✅ Günlük yükleme görevleri oluşturuldu: {len(result)} görev")
            
            return {
                'status': 'success',
                'message': f'{len(result)} yükleme görevi oluşturuldu',
                'gorevler': result
            }
            
    except Exception as e:
        logger.error(f"Günlük yükleme görevi oluşturma hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='gorevlendirme.eksik_yukleme_uyarisi')
def eksik_yukleme_uyarisi_task():
    """
    Eksik yükleme uyarısı - Her gün 18:00'da çalışır
    Yükleme yapılmamış otelleri tespit eder ve uyarı gönderir
    """
    try:
        from app import app
        from utils.yukleme_gorev_service import YuklemeGorevService
        from utils.bildirim_service import BildirimService
        from models import YuklemeGorev
        from datetime import date
        
        with app.app_context():
            logger.info("Eksik yükleme kontrolü yapılıyor...")
            
            tarih = date.today()
            
            # Bugün için bekleyen yükleme görevlerini bul
            bekleyen_gorevler = YuklemeGorev.query.filter(
                YuklemeGorev.gorev_tarihi == tarih,
                YuklemeGorev.durum == 'pending'
            ).all()
            
            uyari_sayisi = 0
            for gorev in bekleyen_gorevler:
                BildirimService.send_upload_warning(
                    depo_sorumlusu_id=gorev.depo_sorumlusu_id,
                    dosya_tipi=gorev.dosya_tipi,
                    otel_id=gorev.otel_id
                )
                uyari_sayisi += 1
            
            logger.info(f"✅ Eksik yükleme uyarıları gönderildi: {uyari_sayisi}")
            
            return {
                'status': 'success',
                'message': f'{uyari_sayisi} uyarı gönderildi'
            }
            
    except Exception as e:
        logger.error(f"Eksik yükleme uyarısı hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='gorevlendirme.doluluk_yukleme_uyari_kontrolu')
def doluluk_yukleme_uyari_kontrolu_task():
    """
    Doluluk yükleme uyarı kontrolü - Her gün KKTC saatiyle 10:00'da çalışır
    Günlük doluluk bilgilerini yüklememiş depo sorumlularına uyarı gönderir
    Sistem yöneticilerine bilgi maili gönderir
    """
    try:
        from app import app
        from utils.email_service import DolulukUyariService
        
        with app.app_context():
            logger.info("Doluluk yükleme uyarı kontrolü başladı...")
            
            result = DolulukUyariService.check_and_send_warnings(target_hour=10)
            
            logger.info(f"✅ Doluluk uyarı kontrolü tamamlandı: {result['warnings_sent']} uyarı gönderildi")
            
            return {
                'status': 'success',
                'message': f"{result['warnings_sent']} uyarı gönderildi",
                'details': result.get('details', [])
            }
            
    except Exception as e:
        logger.error(f"Doluluk uyarı kontrolü hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='gorevlendirme.dnd_tamamlanmayan_kontrol')
def dnd_tamamlanmayan_kontrol_task():
    """
    DND tamamlanmayan görev kontrolü - Her gün 23:59'da çalışır
    3 kez kontrol edilmemiş DND odalarını 'incomplete' olarak işaretler
    Ertesi gün depo sorumlusu ve sistem yöneticisine uyarı gönderir
    """
    try:
        from app import app, db
        from models import GorevDetay, GunlukGorev, GorevDurumLog
        from utils.bildirim_service import BildirimService
        from datetime import date
        
        with app.app_context():
            logger.info("DND tamamlanmayan görev kontrolü yapılıyor...")
            
            tarih = date.today()
            simdi = datetime.now(timezone.utc)
            
            # Bugün için 3 kez kontrol edilmemiş DND görevlerini bul
            tamamlanmayan_dnd = GorevDetay.query.join(GunlukGorev).filter(
                GunlukGorev.gorev_tarihi == tarih,
                GorevDetay.dnd_sayisi > 0,
                GorevDetay.dnd_sayisi < 3,
                GorevDetay.durum == 'dnd_pending'
            ).all()
            
            incomplete_sayisi = 0
            for detay in tamamlanmayan_dnd:
                # Görevi incomplete olarak işaretle
                onceki_durum = detay.durum
                detay.durum = 'incomplete'
                detay.notlar = f'DND kontrolü tamamlanmadı ({detay.dnd_sayisi}/3 kontrol yapıldı)'
                
                # Log kaydı oluştur
                log = GorevDurumLog(
                    gorev_detay_id=detay.id,
                    onceki_durum=onceki_durum,
                    yeni_durum='incomplete',
                    aciklama=f'Gün sonu - DND kontrolü tamamlanmadı ({detay.dnd_sayisi}/3)'
                )
                db.session.add(log)
                incomplete_sayisi += 1
            
            db.session.commit()
            
            if incomplete_sayisi > 0:
                # Depo sorumlusu ve sistem yöneticisine bildirim gönder
                detay_ids = [d.id for d in tamamlanmayan_dnd]
                BildirimService.send_dnd_incomplete_notification(detay_ids)
                logger.info(f"✅ {incomplete_sayisi} görev incomplete olarak işaretlendi")
            else:
                logger.info("✅ Tamamlanmayan DND görevi yok")
            
            return {
                'status': 'success',
                'message': f'{incomplete_sayisi} görev incomplete olarak işaretlendi'
            }
            
    except Exception as e:
        logger.error(f"DND tamamlanmayan kontrol hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


# ============================================
# GÜNLÜK RAPOR TASK'LARI
# ============================================

@celery.task(name='rapor.gunluk_gorev_raporu')
def gunluk_gorev_raporu_task():
    """
    Günlük görev tamamlanma raporu - Her sabah 08:00'de (KKTC saati) çalışır
    Bir gün önceki verileri içerir
    Kat sorumlularının görev tamamlanma raporlarını depo sorumlusu ve sistem yöneticisine gönderir
    """
    try:
        from app import app
        from models import Kullanici, Otel
        from utils.rapor_email_service import RaporEmailService
        from datetime import date, timedelta
        import pytz
        
        with app.app_context():
            # KKTC timezone kontrolü
            kktc_tz = pytz.timezone('Europe/Nicosia')
            now_kktc = datetime.now(kktc_tz)
            
            logger.info(f"📋 Günlük görev raporu task başladı - KKTC Saati: {now_kktc.strftime('%H:%M')}")
            
            # Bir gün önceki tarih
            rapor_tarihi = date.today() - timedelta(days=1)
            
            # Tüm aktif kat sorumlularını al
            kat_sorumlu_list = Kullanici.query.filter(
                Kullanici.rol == 'kat_sorumlusu',
                Kullanici.aktif == True
            ).all()
            
            gonderilen_rapor = 0
            hatali_rapor = 0
            
            for ks in kat_sorumlu_list:
                try:
                    result = RaporEmailService.send_gorev_raporu(ks.id, rapor_tarihi)
                    if result.get('success'):
                        gonderilen_rapor += 1
                        logger.info(f"✅ Görev raporu gönderildi: {ks.ad} {ks.soyad}")
                    else:
                        hatali_rapor += 1
                        logger.warning(f"⚠️ Görev raporu gönderilemedi: {ks.ad} {ks.soyad} - {result.get('message')}")
                except Exception as e:
                    hatali_rapor += 1
                    logger.error(f"❌ Görev raporu hatası ({ks.ad} {ks.soyad}): {str(e)}")
            
            logger.info(f"📋 Günlük görev raporu tamamlandı - Gönderilen: {gonderilen_rapor}, Hatalı: {hatali_rapor}")
            
            return {
                'status': 'success',
                'message': f'{gonderilen_rapor} rapor gönderildi, {hatali_rapor} hata',
                'gonderilen': gonderilen_rapor,
                'hatali': hatali_rapor
            }
            
    except Exception as e:
        logger.error(f"Günlük görev raporu task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='rapor.gunluk_minibar_sarfiyat_raporu')
def gunluk_minibar_sarfiyat_raporu_task():
    """
    Günlük minibar sarfiyat raporu - Her sabah 08:00'de (KKTC saati) çalışır
    Bir gün önceki verileri içerir
    Oda bazlı ürün sarfiyatı ve stok durumlarını depo sorumlusu ve sistem yöneticisine gönderir
    """
    try:
        from app import app
        from models import Otel
        from utils.rapor_email_service import RaporEmailService
        from datetime import date, timedelta
        import pytz
        
        with app.app_context():
            # KKTC timezone kontrolü
            kktc_tz = pytz.timezone('Europe/Nicosia')
            now_kktc = datetime.now(kktc_tz)
            
            logger.info(f"🍫 Günlük minibar sarfiyat raporu task başladı - KKTC Saati: {now_kktc.strftime('%H:%M')}")
            
            # Bir gün önceki tarih
            rapor_tarihi = date.today() - timedelta(days=1)
            
            # Tüm aktif otelleri al
            oteller = Otel.query.filter_by(aktif=True).all()
            
            gonderilen_rapor = 0
            hatali_rapor = 0
            
            for otel in oteller:
                try:
                    result = RaporEmailService.send_minibar_raporu(otel.id, rapor_tarihi)
                    if result.get('success'):
                        gonderilen_rapor += 1
                        logger.info(f"✅ Minibar raporu gönderildi: {otel.ad}")
                    else:
                        hatali_rapor += 1
                        logger.warning(f"⚠️ Minibar raporu gönderilemedi: {otel.ad} - {result.get('message')}")
                except Exception as e:
                    hatali_rapor += 1
                    logger.error(f"❌ Minibar raporu hatası ({otel.ad}): {str(e)}")
            
            logger.info(f"🍫 Günlük minibar sarfiyat raporu tamamlandı - Gönderilen: {gonderilen_rapor}, Hatalı: {hatali_rapor}")
            
            return {
                'status': 'success',
                'message': f'{gonderilen_rapor} rapor gönderildi, {hatali_rapor} hata',
                'gonderilen': gonderilen_rapor,
                'hatali': hatali_rapor
            }
            
    except Exception as e:
        logger.error(f"Günlük minibar sarfiyat raporu task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


# ============================================
# ML ANALİZ SİSTEMİ TASK'LARI
# ============================================

@celery.task(name='ml.veri_toplama')
def ml_veri_toplama_task():
    """
    ML veri toplama - Her 15 dakikada bir çalışır
    Stok, tüketim, dolum, zimmet, doluluk, talep ve QR metriklerini toplar
    """
    try:
        from app import app, db
        from utils.ml.data_collector import DataCollector
        
        with app.app_context():
            logger.info("🔄 ML veri toplama başladı...")
            
            collector = DataCollector(db)
            total_count = collector.collect_all_metrics()
            
            logger.info(f"✅ ML veri toplama tamamlandı: {total_count} metrik toplandı")
            
            return {
                'status': 'success',
                'message': f'{total_count} metrik toplandı',
                'total_metrics': total_count
            }
            
    except Exception as e:
        logger.error(f"ML veri toplama task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='ml.anomali_tespiti')
def ml_anomali_tespiti_task():
    """
    ML anomali tespiti - Her 5 dakikada bir çalışır
    Stok, tüketim, dolum, zimmet, doluluk ve talep anomalilerini tespit eder
    """
    try:
        from app import app, db
        from utils.ml.anomaly_detector import AnomalyDetector
        from utils.ml.alert_manager import AlertManager
        
        with app.app_context():
            logger.info("🔍 ML anomali tespiti başladı...")
            
            detector = AnomalyDetector(db)
            alert_manager = AlertManager(db)
            
            # Tüm anomali tespitlerini çalıştır
            stok_alerts = detector.detect_stok_anomalies()
            tuketim_alerts = detector.detect_tuketim_anomalies()
            dolum_alerts = detector.detect_dolum_anomalies()
            zimmet_alerts = detector.detect_zimmet_anomalies()
            occupancy_alerts = detector.detect_occupancy_anomalies()
            talep_alerts = detector.detect_talep_anomalies()
            
            total_alerts = stok_alerts + tuketim_alerts + dolum_alerts + zimmet_alerts + occupancy_alerts + talep_alerts
            
            logger.info(f"✅ ML anomali tespiti tamamlandı: {total_alerts} alert oluşturuldu")
            logger.info(f"   - Stok: {stok_alerts}, Tüketim: {tuketim_alerts}, Dolum: {dolum_alerts}")
            logger.info(f"   - Zimmet: {zimmet_alerts}, Doluluk: {occupancy_alerts}, Talep: {talep_alerts}")
            
            # Kritik alertler için email bildirimi gönder
            if total_alerts > 0:
                from models import MLAlert
                
                # Son 5 dakikadaki kritik alertleri al
                son_5_dk = datetime.now(timezone.utc) - timedelta(minutes=5)
                kritik_alertler = MLAlert.query.filter(
                    MLAlert.created_at >= son_5_dk,
                    MLAlert.severity.in_(['kritik', 'yuksek']),
                    MLAlert.is_false_positive == False
                ).all()
                
                for alert in kritik_alertler:
                    alert_manager.send_notification(alert)
            
            return {
                'status': 'success',
                'message': f'{total_alerts} alert oluşturuldu',
                'alerts': {
                    'stok': stok_alerts,
                    'tuketim': tuketim_alerts,
                    'dolum': dolum_alerts,
                    'zimmet': zimmet_alerts,
                    'doluluk': occupancy_alerts,
                    'talep': talep_alerts,
                    'total': total_alerts
                }
            }
            
    except Exception as e:
        logger.error(f"ML anomali tespiti task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='ml.model_egitimi')
def ml_model_egitimi_task():
    """
    ML model eğitimi - Her gece 00:00'da çalışır
    Yeterli veri varsa modelleri otomatik eğitir
    """
    try:
        from app import app, db
        from utils.ml.model_trainer import ModelTrainer
        from utils.ml.data_collector import DataCollector
        from models import MLMetric
        
        with app.app_context():
            logger.info("🎓 ML model eğitimi başladı...")
            
            trainer = ModelTrainer(db)
            min_data = trainer.min_data_points
            
            # Veri yeterliliğini kontrol et
            stok_count = MLMetric.query.filter_by(metric_type='stok_seviye').count()
            tuketim_count = MLMetric.query.filter_by(metric_type='tuketim_miktar').count()
            dolum_count = MLMetric.query.filter_by(metric_type='dolum_sure').count()
            
            logger.info(f"📊 Mevcut veri: Stok={stok_count}, Tüketim={tuketim_count}, Dolum={dolum_count} (Min: {min_data})")
            
            results = {
                'stok_model': None,
                'tuketim_model': None,
                'dolum_model': None,
                'trained_count': 0,
                'skipped_count': 0
            }
            
            # Stok modeli
            if stok_count >= min_data:
                model_id = trainer.train_stok_model()
                results['stok_model'] = model_id
                if model_id:
                    results['trained_count'] += 1
                    logger.info(f"✅ Stok modeli eğitildi: ID={model_id}")
            else:
                results['skipped_count'] += 1
                logger.info(f"⏭️ Stok modeli atlandı: Yetersiz veri ({stok_count}/{min_data})")
            
            # Tüketim modeli
            if tuketim_count >= min_data:
                model_id = trainer.train_tuketim_model()
                results['tuketim_model'] = model_id
                if model_id:
                    results['trained_count'] += 1
                    logger.info(f"✅ Tüketim modeli eğitildi: ID={model_id}")
            else:
                results['skipped_count'] += 1
                logger.info(f"⏭️ Tüketim modeli atlandı: Yetersiz veri ({tuketim_count}/{min_data})")
            
            # Dolum modeli
            if dolum_count >= min_data:
                model_id = trainer.train_dolum_model()
                results['dolum_model'] = model_id
                if model_id:
                    results['trained_count'] += 1
                    logger.info(f"✅ Dolum modeli eğitildi: ID={model_id}")
            else:
                results['skipped_count'] += 1
                logger.info(f"⏭️ Dolum modeli atlandı: Yetersiz veri ({dolum_count}/{min_data})")
            
            logger.info(f"🎓 ML model eğitimi tamamlandı: {results['trained_count']} model eğitildi, {results['skipped_count']} atlandı")
            
            return {
                'status': 'success',
                'message': f"{results['trained_count']} model eğitildi",
                'results': results
            }
            
    except Exception as e:
        logger.error(f"ML model eğitimi task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='ml.eski_verileri_temizle')
def ml_eski_verileri_temizle_task():
    """
    ML eski verileri temizle - Her gün 01:00'de çalışır
    90 günden eski metrikleri ve alertleri temizler
    """
    try:
        from app import app, db
        from utils.ml.data_collector import DataCollector
        from utils.ml.alert_manager import AlertManager
        
        with app.app_context():
            logger.info("🗑️ ML eski veri temizliği başladı...")
            
            collector = DataCollector(db)
            alert_manager = AlertManager(db)
            
            # Eski metrikleri temizle (90 gün)
            deleted_metrics = collector.cleanup_old_metrics(days=90)
            
            # Eski alertleri temizle (90 gün)
            deleted_alerts = alert_manager.cleanup_old_alerts(days=90)
            
            logger.info(f"✅ ML temizlik tamamlandı: {deleted_metrics} metrik, {deleted_alerts} alert silindi")
            
            return {
                'status': 'success',
                'message': f'{deleted_metrics} metrik, {deleted_alerts} alert silindi',
                'deleted_metrics': deleted_metrics,
                'deleted_alerts': deleted_alerts
            }
            
    except Exception as e:
        logger.error(f"ML eski veri temizliği task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='ml.gunluk_alert_ozeti')
def ml_gunluk_alert_ozeti_task():
    """
    ML günlük alert özeti - Her sabah 07:00'de çalışır
    Son 24 saatteki kritik alertlerin özetini sistem yöneticilerine gönderir
    """
    try:
        from app import app, db
        from utils.ml.alert_manager import AlertManager
        
        with app.app_context():
            logger.info("📧 ML günlük alert özeti gönderiliyor...")
            
            alert_manager = AlertManager(db)
            gonderilen = alert_manager.send_critical_alerts_summary()
            
            logger.info(f"✅ ML alert özeti gönderildi: {gonderilen} alıcı")
            
            return {
                'status': 'success',
                'message': f'{gonderilen} alıcıya gönderildi',
                'recipients': gonderilen
            }
            
    except Exception as e:
        logger.error(f"ML günlük alert özeti task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='ml.stok_bitis_kontrolu')
def ml_stok_bitis_kontrolu_task():
    """
    ML stok bitiş kontrolü - Her 6 saatte bir çalışır
    Stok bitiş tahminlerini hesaplar ve uyarı oluşturur
    """
    try:
        from app import app, db
        from utils.ml.metrics_calculator import MetricsCalculator
        from utils.ml.alert_manager import AlertManager
        from models import MLAlert
        
        with app.app_context():
            logger.info("📦 ML stok bitiş kontrolü başladı...")
            
            calculator = MetricsCalculator(db)
            alert_manager = AlertManager(db)
            
            alert_count = calculator.check_stock_depletion_alerts()
            
            # Kritik stok alertleri için email gönder
            if alert_count > 0:
                son_1_saat = datetime.now(timezone.utc) - timedelta(hours=1)
                kritik_alertler = MLAlert.query.filter(
                    MLAlert.alert_type == 'stok_bitis_uyari',
                    MLAlert.created_at >= son_1_saat,
                    MLAlert.severity.in_(['kritik', 'yuksek']),
                    MLAlert.is_false_positive == False
                ).all()
                
                for alert in kritik_alertler:
                    alert_manager.send_notification(alert)
            
            logger.info(f"✅ ML stok bitiş kontrolü tamamlandı: {alert_count} uyarı")
            
            return {
                'status': 'success',
                'message': f'{alert_count} stok bitiş uyarısı oluşturuldu',
                'alert_count': alert_count
            }
            
    except Exception as e:
        logger.error(f"ML stok bitiş kontrolü task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


# ============================================
# VERİTABANI YEDEKLEME TASK'LARI
# ============================================

@celery.task(name='backup.otomatik_yedekleme')
def otomatik_yedekleme_task():
    """
    Otomatik veritabanı yedekleme - Her gün 23:59'da çalışır
    Ayarlar sistem_ayarlari tablosundan okunur
    """
    try:
        from app import app
        from utils.backup_service import BackupService
        
        with app.app_context():
            # Ayarları kontrol et
            ayarlar = BackupService.get_backup_settings()
            
            if not ayarlar.get('otomatik_yedekleme', True):
                logger.info("Otomatik yedekleme devre dışı, atlanıyor...")
                return {'status': 'skipped', 'message': 'Otomatik yedekleme devre dışı'}
            
            logger.info("🔄 Otomatik yedekleme başlatılıyor...")
            
            # Yedek al
            result = BackupService.create_backup(
                kullanici_id=None,
                aciklama=f"Otomatik günlük yedek - {datetime.now().strftime('%d.%m.%Y')}"
            )
            
            if result['success']:
                logger.info(f"✅ Otomatik yedekleme tamamlandı: {result['filename']}")
                
                # Eski yedekleri temizle
                saklama_suresi = ayarlar.get('saklama_suresi', 15)
                cleanup_result = BackupService.cleanup_old_backups(days=saklama_suresi)
                
                if cleanup_result['deleted_count'] > 0:
                    logger.info(f"🗑️ {cleanup_result['deleted_count']} eski yedek silindi")
                
                return {
                    'status': 'success',
                    'message': f"Yedekleme tamamlandı: {result['filename']}",
                    'backup_id': result['backup_id'],
                    'cleaned_up': cleanup_result['deleted_count']
                }
            else:
                logger.error(f"❌ Otomatik yedekleme hatası: {result['message']}")
                return {
                    'status': 'error',
                    'message': result['message']
                }
                
    except Exception as e:
        logger.error(f"Otomatik yedekleme task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='backup.eski_yedekleri_temizle')
def eski_yedekleri_temizle_task():
    """
    Eski yedekleri temizle - Her gün 00:30'da çalışır
    """
    try:
        from app import app
        from utils.backup_service import BackupService
        
        with app.app_context():
            ayarlar = BackupService.get_backup_settings()
            saklama_suresi = ayarlar.get('saklama_suresi', 15)
            
            logger.info(f"🗑️ {saklama_suresi} günden eski yedekler temizleniyor...")
            
            result = BackupService.cleanup_old_backups(days=saklama_suresi)
            
            if result['deleted_count'] > 0:
                logger.info(f"✅ {result['deleted_count']} eski yedek silindi, {result['freed_space'] / 1024 / 1024:.2f} MB alan boşaltıldı")
            else:
                logger.info("✅ Silinecek eski yedek yok")
            
            return {
                'status': 'success',
                'deleted_count': result['deleted_count'],
                'freed_space_mb': round(result['freed_space'] / 1024 / 1024, 2)
            }
            
    except Exception as e:
        logger.error(f"Eski yedek temizleme task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


# ============================================
# CELERY BEAT SCHEDULE (Periyodik Task'lar)
# ============================================

celery.conf.beat_schedule = {
    # ============================================
    # ML ANALİZ SİSTEMİ SCHEDULE
    # ============================================
    
    # ML Veri Toplama - Her 15 dakikada bir
    'ml-veri-toplama': {
        'task': 'ml.veri_toplama',
        'schedule': 900.0,  # 15 dakika
    },
    # ML Anomali Tespiti - Her 5 dakikada bir
    'ml-anomali-tespiti': {
        'task': 'ml.anomali_tespiti',
        'schedule': 300.0,  # 5 dakika
    },
    # ML Model Eğitimi - Her gece 00:00'da (UTC 22:00 = KKTC 00:00)
    'ml-model-egitimi': {
        'task': 'ml.model_egitimi',
        'schedule': crontab(hour=22, minute=0),  # UTC 22:00 = KKTC 00:00
    },
    # ML Eski Verileri Temizle - Her gün 01:00'de
    'ml-eski-verileri-temizle': {
        'task': 'ml.eski_verileri_temizle',
        'schedule': crontab(hour=23, minute=0),  # UTC 23:00 = KKTC 01:00
    },
    # ML Günlük Alert Özeti - Her sabah 07:00'de (KKTC)
    'ml-gunluk-alert-ozeti': {
        'task': 'ml.gunluk_alert_ozeti',
        'schedule': crontab(hour=5, minute=0),  # UTC 05:00 = KKTC 07:00
    },
    # ML Stok Bitiş Kontrolü - Her 6 saatte bir
    'ml-stok-bitis-kontrolu': {
        'task': 'ml.stok_bitis_kontrolu',
        'schedule': 21600.0,  # 6 saat
    },
    
    # ============================================
    # FİYATLANDIRMA SİSTEMİ SCHEDULE
    # ============================================
    
    # Her gün gece 00:30'da günlük kar analizi
    'gunluk-kar-analizi': {
        'task': 'fiyatlandirma.gunluk_kar_analizi',
        'schedule': crontab(hour=22, minute=30),  # UTC 22:30 = KKTC 00:30
    },
    # Her Pazartesi sabah 06:00'da haftalık trend analizi
    'haftalik-trend-analizi': {
        'task': 'fiyatlandirma.haftalik_trend_analizi',
        'schedule': crontab(day_of_week=1, hour=4, minute=0),  # UTC 04:00 = KKTC 06:00
    },
    # Her ayın 1'i sabah 07:00'de stok devir analizi
    'aylik-stok-devir-analizi': {
        'task': 'fiyatlandirma.aylik_stok_devir_analizi',
        'schedule': crontab(day_of_month=1, hour=5, minute=0),  # UTC 05:00 = KKTC 07:00
    },
    
    # ============================================
    # GÖREVLENDİRME SİSTEMİ SCHEDULE
    # ============================================
    
    # Her gün 00:01'de yükleme görevleri oluştur
    'gunluk-yukleme-gorevleri': {
        'task': 'gorevlendirme.gunluk_yukleme_gorevleri_olustur',
        'schedule': crontab(hour=22, minute=1),  # UTC 22:01 = KKTC 00:01
    },
    # Her gün 18:00'da eksik yükleme uyarısı
    'eksik-yukleme-uyarisi': {
        'task': 'gorevlendirme.eksik_yukleme_uyarisi',
        'schedule': crontab(hour=16, minute=0),  # UTC 16:00 = KKTC 18:00
    },
    # Her gün 23:59'da DND tamamlanmayan kontrol
    'dnd-tamamlanmayan-kontrol': {
        'task': 'gorevlendirme.dnd_tamamlanmayan_kontrol',
        'schedule': crontab(hour=21, minute=59),  # UTC 21:59 = KKTC 23:59
    },
    # Her gün KKTC saatiyle 10:00'da doluluk yükleme uyarısı
    'doluluk-yukleme-uyari': {
        'task': 'gorevlendirme.doluluk_yukleme_uyari_kontrolu',
        'schedule': crontab(hour=8, minute=0),  # UTC 08:00 = KKTC 10:00
    },
    
    # ============================================
    # YEDEKLEME SİSTEMİ SCHEDULE
    # ============================================
    
    # Her gün 23:59'da otomatik yedekleme
    'otomatik-yedekleme': {
        'task': 'backup.otomatik_yedekleme',
        'schedule': crontab(hour=21, minute=59),  # UTC 21:59 = KKTC 23:59
    },
    # Her gün 00:30'da eski yedekleri temizle
    'eski-yedekleri-temizle': {
        'task': 'backup.eski_yedekleri_temizle',
        'schedule': crontab(hour=22, minute=30),  # UTC 22:30 = KKTC 00:30
    },
    
    # ============================================
    # RAPOR SİSTEMİ SCHEDULE
    # ============================================
    
    # Her sabah 08:00'de (KKTC) görev tamamlanma raporu
    'gunluk-gorev-raporu': {
        'task': 'rapor.gunluk_gorev_raporu',
        'schedule': crontab(hour=6, minute=0),  # UTC 06:00 = KKTC 08:00
    },
    # Her sabah 08:05'de (KKTC) minibar sarfiyat raporu
    'gunluk-minibar-sarfiyat-raporu': {
        'task': 'rapor.gunluk_minibar_sarfiyat_raporu',
        'schedule': crontab(hour=6, minute=5),  # UTC 06:05 = KKTC 08:05
    },
}


if __name__ == '__main__':
    # Celery worker'ı başlat
    # Komut: celery -A celery_app worker --loglevel=info
    # Beat için: celery -A celery_app beat --loglevel=info
    celery.start()
