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
import pytz

# KKTC Timezone (Kıbrıs - Europe/Nicosia)
KKTC_TZ = pytz.timezone('Europe/Nicosia')

def get_kktc_now():
    """Kıbrıs saat diliminde şu anki zamanı döndürür."""
    return datetime.now(KKTC_TZ)

# Logging
logger = logging.getLogger(__name__)

# Flask app ve db için lazy loading cache
_flask_app = None
_db = None

def get_flask_app():
    """Flask app'i lazy loading ile al - Celery worker'lar için"""
    global _flask_app, _db
    if _flask_app is None:
        try:
            # Önce app.py'den import etmeyi dene
            from app import app as flask_app, db as flask_db
            _flask_app = flask_app
            _db = flask_db
        except ImportError:
            # Import başarısız olursa, Flask app'i manuel oluştur
            import sys
            import os
            
            # Proje kök dizinini path'e ekle
            project_root = os.path.dirname(os.path.abspath(__file__))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from flask import Flask
            from models import db as models_db
            from config import Config
            
            flask_app = Flask(__name__)
            flask_app.config.from_object(Config)
            
            # Database bağlantısı
            database_url = os.getenv('DATABASE_URL')
            if database_url:
                flask_app.config['SQLALCHEMY_DATABASE_URI'] = database_url
            
            models_db.init_app(flask_app)
            _flask_app = flask_app
            _db = models_db
            
            logger.info("Flask app Celery worker için manuel oluşturuldu")
    
    return _flask_app, _db


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
    
    # Celery konfigürasyonu - Config'den değerler alınıyor (29.12.2025)
    # Magic numbers config.py'ye taşındı
    celery.conf.update(
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=int(os.getenv('CELERY_TASK_TIME_LIMIT', '3600')),  # 1 saat max (config'den)
        task_soft_time_limit=int(os.getenv('CELERY_TASK_SOFT_TIME_LIMIT', '3000')),  # 50 dakika soft limit
        worker_prefetch_multiplier=int(os.getenv('CELERY_WORKER_PREFETCH', '1')),
        worker_max_tasks_per_child=int(os.getenv('CELERY_MAX_TASKS_PER_CHILD', '1000')),
        broker_connection_retry_on_startup=True,  # Celery 6.0 uyarısını kaldır
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
        app, db = get_flask_app()
        from models import Urun, MinibarIslemDetay, MinibarIslem
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        with app.app_context():
            logger.info(f"Tüketim trendi güncelleme başladı - Otel: {otel_id}, Dönem: {donem}")
            
            # Dönem aralığını belirle
            bugun = get_kktc_now()
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
        app, db = get_flask_app()
        from models import UrunStok, StokHareket
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        with app.app_context():
            logger.info(f"Stok devir hızı güncelleme başladı - Otel: {otel_id}")
            
            # Son 30 günlük dönem
            bugun = get_kktc_now()
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




@celery.task(name='fiyatlandirma.haftalik_trend_analizi')
def haftalik_trend_analizi_task():
    """
    Haftalık trend analizi - Otomatik çalışır (Celery Beat)
    Her Pazartesi sabahı tüm oteller için haftalık trend analizi yapar
    """
    try:
        app, db = get_flask_app()
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
        app, db = get_flask_app()
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
        app, db = get_flask_app()
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
        app, db = get_flask_app()
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
        app, db = get_flask_app()
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
        app, db = get_flask_app()
        from models import GorevDetay, GunlukGorev, GorevDurumLog
        from utils.bildirim_service import BildirimService
        from datetime import date
        
        with app.app_context():
            logger.info("DND tamamlanmayan görev kontrolü yapılıyor...")
            
            tarih = date.today()
            simdi = get_kktc_now()
            
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
                detay.notlar = f'DND kontrolü tamamlanmadı ({detay.dnd_sayisi}/2 kontrol yapıldı)'
                
                # Log kaydı oluştur
                log = GorevDurumLog(
                    gorev_detay_id=detay.id,
                    onceki_durum=onceki_durum,
                    yeni_durum='incomplete',
                    aciklama=f'Gün sonu - DND kontrolü tamamlanmadı ({detay.dnd_sayisi}/2)'
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
    TÜM kat sorumlularının raporunu TEK mail olarak gönderir (okundu bilgisi ile)
    """
    try:
        app, db = get_flask_app()
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
            
            # TOPLU RAPOR GÖNDER (tek mail'de tüm personel)
            result = RaporEmailService.send_toplu_gorev_raporu(rapor_tarihi)
            
            if result.get('success'):
                logger.info(f"✅ Toplu görev raporu gönderildi: {result.get('message')}")
            else:
                logger.warning(f"⚠️ Toplu görev raporu gönderilemedi: {result.get('message')}")
            
            return {
                'status': 'success' if result.get('success') else 'error',
                'message': result.get('message'),
                'personel_sayisi': result.get('personel_sayisi', 0)
            }
            
    except Exception as e:
        logger.error(f"Günlük görev raporu task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='rapor.gunluk_minibar_sarfiyat_raporu')
def gunluk_minibar_sarfiyat_raporu_task():
    """
    Günlük minibar sarfiyat raporu - Her sabah 08:00'de (KKTC saati) çalışır
    Bir gün önceki verileri içerir
    TÜM otellerin raporunu TEK mail olarak gönderir (okundu bilgisi ile)
    """
    try:
        app, db = get_flask_app()
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
            
            # TOPLU RAPOR GÖNDER (tek mail'de tüm oteller)
            result = RaporEmailService.send_toplu_minibar_raporu(rapor_tarihi)
            
            if result.get('success'):
                logger.info(f"✅ Toplu minibar raporu gönderildi: {result.get('message')}")
            else:
                logger.warning(f"⚠️ Toplu minibar raporu gönderilemedi: {result.get('message')}")
            
            return {
                'status': 'success' if result.get('success') else 'error',
                'message': result.get('message'),
                'otel_sayisi': result.get('otel_sayisi', 0)
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
        app, db = get_flask_app()
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
        app, db = get_flask_app()
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
                son_5_dk = get_kktc_now() - timedelta(minutes=5)
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
        app, db = get_flask_app()
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
        app, db = get_flask_app()
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
        app, db = get_flask_app()
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
        app, db = get_flask_app()
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
                son_1_saat = get_kktc_now() - timedelta(hours=1)
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
        app, db = get_flask_app()
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
                aciklama=f"Otomatik günlük yedek - {get_kktc_now().strftime('%d.%m.%Y')}"
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
        app, db = get_flask_app()
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
# VERİTABANI TEMİZLİK TASK'LARI
# ============================================

@celery.task(name='maintenance.query_logs_temizle')
def query_logs_temizle_task():
    """
    query_logs tablosundan 7 günden eski kayıtları temizle
    Her hafta Pazar gecesi 02:00'de çalışır
    """
    try:
        app, db = get_flask_app()
        
        with app.app_context():
            from sqlalchemy import text
            
            logger.info("🗑️ query_logs tablosu temizleniyor (7 günden eski kayıtlar)...")
            
            # Silinecek kayıt sayısını öğren
            count_result = db.session.execute(text(
                "SELECT COUNT(*) FROM query_logs WHERE timestamp < NOW() - INTERVAL '7 days'"
            )).scalar()
            
            if count_result == 0:
                logger.info("✅ Silinecek eski query_logs kaydı yok")
                return {
                    'status': 'success',
                    'deleted_count': 0,
                    'message': 'Silinecek kayıt yok'
                }
            
            # Kayıtları sil
            db.session.execute(text(
                "DELETE FROM query_logs WHERE timestamp < NOW() - INTERVAL '7 days'"
            ))
            db.session.commit()
            
            logger.info(f"✅ {count_result} eski query_logs kaydı silindi")
            
            # Tablo boyutunu logla
            size_result = db.session.execute(text(
                "SELECT pg_size_pretty(pg_total_relation_size('query_logs'))"
            )).scalar()
            logger.info(f"📊 query_logs tablo boyutu: {size_result}")
            
            return {
                'status': 'success',
                'deleted_count': count_result,
                'table_size': size_result
            }
            
    except Exception as e:
        logger.error(f"query_logs temizleme task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='maintenance.query_logs_gunluk_temizle')
def query_logs_gunluk_temizle_task():
    """
    query_logs tablosundan 3 günden eski kayıtları temizle
    Her gün gece 03:00'de çalışır (KKTC saati)
    
    Bu tablo günde ~250K kayıt ürettiği için günlük temizlik gerekli.
    Performans için batch delete kullanılır.
    """
    try:
        app, db = get_flask_app()
        
        with app.app_context():
            from sqlalchemy import text
            
            logger.info("🗑️ [GÜNLÜK] query_logs tablosu temizleniyor (3 günden eski kayıtlar)...")
            
            # Önce tablo boyutunu al
            size_before = db.session.execute(text(
                "SELECT pg_size_pretty(pg_total_relation_size('query_logs'))"
            )).scalar()
            
            # Silinecek kayıt sayısını öğren
            count_result = db.session.execute(text(
                "SELECT COUNT(*) FROM query_logs WHERE timestamp < NOW() - INTERVAL '3 days'"
            )).scalar()
            
            if count_result == 0:
                logger.info("✅ Silinecek eski query_logs kaydı yok")
                return {
                    'status': 'success',
                    'deleted_count': 0,
                    'message': 'Silinecek kayıt yok',
                    'table_size': size_before
                }
            
            # Batch delete - Performans için 50K'lık parçalar halinde sil
            total_deleted = 0
            batch_size = 50000
            
            while True:
                result = db.session.execute(text(f"""
                    DELETE FROM query_logs 
                    WHERE id IN (
                        SELECT id FROM query_logs 
                        WHERE timestamp < NOW() - INTERVAL '3 days' 
                        LIMIT {batch_size}
                    )
                """))
                deleted = result.rowcount
                db.session.commit()
                
                if deleted == 0:
                    break
                    
                total_deleted += deleted
                logger.info(f"  🔄 {total_deleted} kayıt silindi...")
                
                # Her batch sonrası kısa bekleme (DB yükünü azaltmak için)
                import time
                time.sleep(0.5)
            
            # Sonra tablo boyutunu al
            size_after = db.session.execute(text(
                "SELECT pg_size_pretty(pg_total_relation_size('query_logs'))"
            )).scalar()
            
            logger.info(f"✅ [GÜNLÜK] {total_deleted} eski query_logs kaydı silindi")
            logger.info(f"📊 Tablo boyutu: {size_before} → {size_after}")
            
            return {
                'status': 'success',
                'deleted_count': total_deleted,
                'table_size_before': size_before,
                'table_size_after': size_after
            }
            
    except Exception as e:
        logger.error(f"query_logs günlük temizleme task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='maintenance.ml_metrics_temizle')
def ml_metrics_temizle_task():
    """
    ml_metrics tablosundan 60 günden eski kayıtları temizle
    Her hafta Pazartesi gece 03:30'da çalışır (KKTC saati)
    
    Bu tablo 130 MB civarında ve büyümeye devam ediyor.
    """
    try:
        app, db = get_flask_app()
        
        with app.app_context():
            from sqlalchemy import text
            
            logger.info("🗑️ ml_metrics tablosu temizleniyor (60 günden eski kayıtlar)...")
            
            # Önce tablo boyutunu al
            size_before = db.session.execute(text(
                "SELECT pg_size_pretty(pg_total_relation_size('ml_metrics'))"
            )).scalar()
            
            # Silinecek kayıt sayısını öğren
            count_result = db.session.execute(text(
                "SELECT COUNT(*) FROM ml_metrics WHERE created_at < NOW() - INTERVAL '60 days'"
            )).scalar()
            
            if count_result == 0:
                logger.info("✅ Silinecek eski ml_metrics kaydı yok")
                return {
                    'status': 'success',
                    'deleted_count': 0,
                    'message': 'Silinecek kayıt yok',
                    'table_size': size_before
                }
            
            # Kayıtları sil
            db.session.execute(text(
                "DELETE FROM ml_metrics WHERE created_at < NOW() - INTERVAL '60 days'"
            ))
            db.session.commit()
            
            # Sonra tablo boyutunu al
            size_after = db.session.execute(text(
                "SELECT pg_size_pretty(pg_total_relation_size('ml_metrics'))"
            )).scalar()
            
            logger.info(f"✅ {count_result} eski ml_metrics kaydı silindi")
            logger.info(f"📊 Tablo boyutu: {size_before} → {size_after}")
            
            return {
                'status': 'success',
                'deleted_count': count_result,
                'table_size_before': size_before,
                'table_size_after': size_after
            }
            
    except Exception as e:
        logger.error(f"ml_metrics temizleme task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@celery.task(name='maintenance.eski_loglari_temizle')
def eski_loglari_temizle_task():
    """
    Eski log tablolarını temizle (hata_loglari, audit_logs vb.)
    Her hafta Pazar gecesi 02:30'da çalışır
    """
    try:
        app, db = get_flask_app()
        
        with app.app_context():
            from sqlalchemy import text
            
            logger.info("🗑️ Eski log tabloları temizleniyor...")
            
            temizlik_sonuclari = {}
            
            # Temizlenecek tablolar ve saklama süreleri (gün)
            tablolar = {
                'hata_loglari': 30,
                'audit_logs': 90,
                'email_loglari': 30,
                'background_jobs': 7,
            }
            
            for tablo, gun in tablolar.items():
                try:
                    # Tarih sütununu belirle
                    tarih_sutunu = 'created_at' if tablo != 'hata_loglari' else 'tarih'
                    if tablo == 'email_loglari':
                        tarih_sutunu = 'gonderim_tarihi'
                    if tablo == 'background_jobs':
                        tarih_sutunu = 'created_at'
                    
                    # Silinecek kayıt sayısı
                    count_query = text(f"SELECT COUNT(*) FROM {tablo} WHERE {tarih_sutunu} < NOW() - INTERVAL '{gun} days'")
                    count = db.session.execute(count_query).scalar()
                    
                    if count and count > 0:
                        delete_query = text(f"DELETE FROM {tablo} WHERE {tarih_sutunu} < NOW() - INTERVAL '{gun} days'")
                        db.session.execute(delete_query)
                        temizlik_sonuclari[tablo] = count
                        logger.info(f"  ✅ {tablo}: {count} kayıt silindi ({gun} günden eski)")
                    else:
                        temizlik_sonuclari[tablo] = 0
                        
                except Exception as table_error:
                    logger.warning(f"  ⚠️ {tablo} temizlenemedi: {str(table_error)}")
                    temizlik_sonuclari[tablo] = f"Hata: {str(table_error)}"
            
            db.session.commit()
            
            toplam_silinen = sum(v for v in temizlik_sonuclari.values() if isinstance(v, int))
            logger.info(f"✅ Toplam {toplam_silinen} eski log kaydı silindi")
            
            return {
                'status': 'success',
                'details': temizlik_sonuclari,
                'total_deleted': toplam_silinen
            }
            
    except Exception as e:
        logger.error(f"Eski log temizleme task hatası: {str(e)}")
        return {'status': 'error', 'message': str(e)}


# ============================================
# CELERY BEAT SCHEDULE (Periyodik Task'lar)
# ============================================

celery.conf.beat_schedule = {
    # ============================================
    # ML ANALİZ SİSTEMİ SCHEDULE
    # ============================================
    
    # ML Veri Toplama - Sabah 08:00 - Akşam 20:00 arası her saat başı
    # UTC saat = KKTC saat - 2 (yaz saati) veya - 3 (kış saati)
    # KKTC 08:00-20:00 = UTC 06:00-18:00 (kış) veya 05:00-17:00 (yaz)
    'ml-veri-toplama': {
        'task': 'ml.veri_toplama',
        'schedule': crontab(hour='5-17', minute=0),  # UTC 05:00-17:00 = KKTC ~08:00-20:00
    },
    # ML Anomali Tespiti - Sabah 08:30 - Akşam 20:30 arası her saat (veri toplamadan 30dk sonra)
    'ml-anomali-tespiti': {
        'task': 'ml.anomali_tespiti',
        'schedule': crontab(hour='5-17', minute=30),  # UTC 05:30-17:30 = KKTC ~08:30-20:30
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
    
    # ============================================
    # VERİTABANI TEMİZLİK SCHEDULE
    # ============================================
    
    # Her gün gece 03:00'de (KKTC) query_logs günlük temizliği
    'query-logs-gunluk-temizle': {
        'task': 'maintenance.query_logs_gunluk_temizle',
        'schedule': crontab(hour=1, minute=0),  # UTC 01:00 = KKTC 03:00
    },
    # Her Pazar gecesi 02:00'de query_logs haftalık temizliği
    'query-logs-temizle': {
        'task': 'maintenance.query_logs_temizle',
        'schedule': crontab(day_of_week=0, hour=0, minute=0),  # UTC 00:00 Pazar = KKTC 02:00 Pazar
    },
    # Her Pazartesi gece 03:30'da (KKTC) ml_metrics temizliği
    'ml-metrics-temizle': {
        'task': 'maintenance.ml_metrics_temizle',
        'schedule': crontab(day_of_week=1, hour=1, minute=30),  # UTC 01:30 Pazartesi = KKTC 03:30 Pazartesi
    },
    # Her Pazar gecesi 02:30'da eski logları temizle
    'eski-loglari-temizle': {
        'task': 'maintenance.eski_loglari_temizle',
        'schedule': crontab(day_of_week=0, hour=0, minute=30),  # UTC 00:30 Pazar = KKTC 02:30 Pazar
    },
}


if __name__ == '__main__':
    # Celery worker'ı başlat
    # Komut: celery -A celery_app worker --loglevel=info
    # Beat için: celery -A celery_app beat --loglevel=info
    celery.start()
