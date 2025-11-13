"""
Celery Asenkron İşlemler Konfigürasyonu
Fiyatlandırma ve Karlılık Sistemi için ağır hesaplamaları arka planda çalıştırır
"""

from celery import Celery
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
# CELERY BEAT SCHEDULE (Periyodik Task'lar)
# ============================================

celery.conf.beat_schedule = {
    # Her gün gece 00:30'da günlük kar analizi
    'gunluk-kar-analizi': {
        'task': 'fiyatlandirma.gunluk_kar_analizi',
        'schedule': 1800.0,  # 30 dakika (crontab(hour=0, minute=30) yerine)
    },
    # Her Pazartesi sabah 06:00'da haftalık trend analizi
    'haftalik-trend-analizi': {
        'task': 'fiyatlandirma.haftalik_trend_analizi',
        'schedule': 604800.0,  # 7 gün (crontab(day_of_week=1, hour=6, minute=0) yerine)
    },
    # Her ayın 1'i sabah 07:00'de stok devir analizi
    'aylik-stok-devir-analizi': {
        'task': 'fiyatlandirma.aylik_stok_devir_analizi',
        'schedule': 2592000.0,  # 30 gün (crontab(day_of_month=1, hour=7, minute=0) yerine)
    },
}


if __name__ == '__main__':
    # Celery worker'ı başlat
    # Komut: celery -A celery_app worker --loglevel=info
    # Beat için: celery -A celery_app beat --loglevel=info
    celery.start()
