"""
Executive Dashboard Data Service
Üst yönetici paneli için veri toplama ve analiz servisi
"""

from datetime import datetime, timedelta, date
from sqlalchemy import func, desc, cast, Date, extract, case, and_, or_
from models import (
    db, Kullanici, Otel, Oda, Urun, UrunGrup, Kat,
    MinibarIslem, MinibarIslemDetay, StokHareket,
    PersonelZimmet, PersonelZimmetDetay,
    AuditLog, SistemLog, GunlukGorev, GorevDetay,
    OdaKontrolKaydi, MinibarIslemTipi, KullaniciRol,
    GorevDurum, GorevTipi, HareketTipi,
    OdaDNDKayit, OdaDNDKontrol
)
import logging
from utils.helpers import get_excluded_user_ids

logger = logging.getLogger(__name__)


def get_kktc_now():
    """KKTC saatini döndür"""
    from pytz import timezone
    kktc_tz = timezone('Europe/Nicosia')
    return datetime.now(kktc_tz).replace(tzinfo=None)


def get_date_range(period='today'):
    """Zaman periyoduna göre başlangıç-bitiş tarihi döndür"""
    now = get_kktc_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period == 'today':
        return today_start, now
    elif period == 'yesterday':
        yesterday = today_start - timedelta(days=1)
        return yesterday, today_start
    elif period == 'this_week':
        week_start = today_start - timedelta(days=now.weekday())
        return week_start, now
    elif period == 'last_week':
        this_week_start = today_start - timedelta(days=now.weekday())
        return this_week_start - timedelta(days=7), this_week_start
    elif period == 'this_month':
        month_start = today_start.replace(day=1)
        return month_start, now
    elif period == 'last_month':
        this_month_start = today_start.replace(day=1)
        last_month_end = this_month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return last_month_start, this_month_start
    else:  # all
        return datetime(2020, 1, 1), now


class ExecutiveDashboardService:
    """Executive Dashboard veri servisi"""

    @staticmethod
    def get_kpi_summary(period='today'):
        """Ana KPI kartları için özet veriler"""
        try:
            start_date, end_date = get_date_range(period)

            # Toplam oteller
            toplam_otel = Otel.query.filter_by(aktif=True).count()

            # Toplam odalar
            toplam_oda = Oda.query.filter_by(aktif=True).count()

            # Toplam ürünler
            toplam_urun = Urun.query.filter_by(aktif=True).count()

            # Toplam kullanıcılar
            toplam_kullanici = Kullanici.query.filter_by(aktif=True).count()

            # Kontrol edilen oda sayısı
            kontrol = OdaKontrolKaydi.query.filter(
                OdaKontrolKaydi.kontrol_tarihi >= start_date,
                OdaKontrolKaydi.kontrol_tarihi < end_date,
                ~OdaKontrolKaydi.personel_id.in_(get_excluded_user_ids())
            ).count()

            # Tüketilen ürün sayısı
            tuketim = db.session.query(
                func.coalesce(func.sum(MinibarIslemDetay.tuketim), 0)
            ).join(MinibarIslem).filter(
                MinibarIslem.islem_tarihi >= start_date,
                MinibarIslem.islem_tarihi < end_date,
                MinibarIslemDetay.tuketim > 0,
                ~MinibarIslem.personel_id.in_(get_excluded_user_ids())
            ).scalar() or 0

            # Görev tamamlanma oranı (sadece doluluk bilgisi yüklendikten sonra oluşturulan görevler)
            gorevler = GunlukGorev.query.filter(
                GunlukGorev.gorev_tarihi >= start_date.date(),
                GunlukGorev.gorev_tarihi <= end_date.date(),
                GunlukGorev.id.in_(
                    db.session.query(GorevDetay.gorev_id).filter(
                        GorevDetay.misafir_kayit_id.isnot(None)
                    ).distinct()
                )
            ).all()
            toplam_gorev = len(gorevler)
            tamamlanan_gorev = sum(1 for g in gorevler if g.durum == GorevDurum.COMPLETED)
            gorev_oran = round((tamamlanan_gorev / toplam_gorev * 100) if toplam_gorev > 0 else 0)

            # Aktif kullanıcı sayısı
            aktif_kullanici = db.session.query(
                func.count(func.distinct(AuditLog.kullanici_id))
            ).filter(
                AuditLog.islem_tarihi >= start_date,
                AuditLog.islem_tarihi < end_date,
                ~AuditLog.kullanici_id.in_(get_excluded_user_ids())
            ).scalar() or 0

            # Toplam işlem sayısı
            toplam_islem = AuditLog.query.filter(
                AuditLog.islem_tarihi >= start_date,
                AuditLog.islem_tarihi < end_date,
                ~AuditLog.kullanici_id.in_(get_excluded_user_ids())
            ).count()

            return {
                'toplam_otel': toplam_otel,
                'toplam_oda': toplam_oda,
                'toplam_urun': toplam_urun,
                'toplam_kullanici': toplam_kullanici,
                'bugun_kontrol': kontrol,
                'bugun_tuketim': int(tuketim),
                'gorev_oran': gorev_oran,
                'tamamlanan_gorev': tamamlanan_gorev,
                'toplam_gorev': toplam_gorev,
                'aktif_kullanici': aktif_kullanici,
                'bugun_islem': toplam_islem
            }
        except Exception as e:
            logger.error(f"KPI summary hatası: {e}")
            return {
                'toplam_otel': 0, 'toplam_oda': 0, 'toplam_urun': 0,
                'toplam_kullanici': 0, 'bugun_kontrol': 0, 'bugun_tuketim': 0,
                'gorev_oran': 0, 'tamamlanan_gorev': 0, 'toplam_gorev': 0,
                'aktif_kullanici': 0, 'bugun_islem': 0
            }

    @staticmethod
    def get_user_activity_stats():
        """Kullanıcı bazlı aktivite istatistikleri (executive dashboard - superadmin dahil)"""
        try:
            now = get_kktc_now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            users = Kullanici.query.filter(
                Kullanici.aktif == True
            ).all()
            user_stats = []

            for user in users:
                # Bugünkü işlem sayısı
                bugun_islem = AuditLog.query.filter(
                    AuditLog.kullanici_id == user.id,
                    AuditLog.islem_tarihi >= today_start
                ).count()

                # Son 7 günlük işlem sayısı
                haftalik_islem = AuditLog.query.filter(
                    AuditLog.kullanici_id == user.id,
                    AuditLog.islem_tarihi >= today_start - timedelta(days=7)
                ).count()

                # Son aktivite zamanı
                son_aktivite = db.session.query(
                    func.max(AuditLog.islem_tarihi)
                ).filter(
                    AuditLog.kullanici_id == user.id
                ).scalar()

                # Otel bilgisi
                otel_ad = user.otel.ad if user.otel else 'Genel'

                user_stats.append({
                    'id': user.id,
                    'ad_soyad': user.ad_soyad,
                    'rol': user.rol,
                    'otel': otel_ad,
                    'bugun_islem': bugun_islem,
                    'haftalik_islem': haftalik_islem,
                    'son_aktivite': son_aktivite.strftime('%d.%m.%Y %H:%M') if son_aktivite else '-',
                    'aktif_mi': bugun_islem > 0
                })

            # İşlem sayısına göre sırala
            user_stats.sort(key=lambda x: x['bugun_islem'], reverse=True)
            return user_stats
        except Exception as e:
            logger.error(f"User activity stats hatası: {e}")
            return []

    @staticmethod
    def get_hotel_comparison(period='today'):
        """Otel bazlı karşılaştırma verileri"""
        try:
            start_date, end_date = get_date_range(period)
            oteller = Otel.query.filter_by(aktif=True).order_by(Otel.id).all()
            hotel_data = []

            for otel in oteller:
                oda_sayisi = Oda.query.join(Kat).filter(
                    Kat.otel_id == otel.id, Oda.aktif == True
                ).count()

                kontrol = OdaKontrolKaydi.query.join(Oda).join(Kat).filter(
                    Kat.otel_id == otel.id,
                    OdaKontrolKaydi.kontrol_tarihi >= start_date,
                    OdaKontrolKaydi.kontrol_tarihi < end_date,
                    ~OdaKontrolKaydi.personel_id.in_(get_excluded_user_ids())
                ).count()

                tuketim = db.session.query(
                    func.coalesce(func.sum(MinibarIslemDetay.tuketim), 0)
                ).join(MinibarIslem).join(Oda, MinibarIslem.oda_id == Oda.id).join(Kat, Oda.kat_id == Kat.id).filter(
                    Kat.otel_id == otel.id,
                    MinibarIslem.islem_tarihi >= start_date,
                    MinibarIslem.islem_tarihi < end_date,
                    MinibarIslemDetay.tuketim > 0,
                    ~MinibarIslem.personel_id.in_(get_excluded_user_ids())
                ).scalar() or 0

                gorevler = GunlukGorev.query.filter(
                    GunlukGorev.otel_id == otel.id,
                    GunlukGorev.gorev_tarihi >= start_date.date(),
                    GunlukGorev.gorev_tarihi <= end_date.date(),
                    GunlukGorev.id.in_(
                        db.session.query(GorevDetay.gorev_id).filter(
                            GorevDetay.misafir_kayit_id.isnot(None)
                        ).distinct()
                    )
                ).all()
                toplam_g = len(gorevler)
                tamamlanan_g = sum(1 for g in gorevler if g.durum == GorevDurum.COMPLETED)

                hotel_data.append({
                    'id': otel.id,
                    'ad': otel.ad,
                    'oda_sayisi': oda_sayisi,
                    'bugun_kontrol': kontrol,
                    'bugun_tuketim': int(tuketim),
                    'gorev_toplam': toplam_g,
                    'gorev_tamamlanan': tamamlanan_g,
                    'gorev_oran': round((tamamlanan_g / toplam_g * 100) if toplam_g > 0 else 0)
                })

            return hotel_data
        except Exception as e:
            logger.error(f"Hotel comparison hatası: {e}")
            return []

    @staticmethod
    def get_consumption_trends(period='today', days=None):
        """Tüketim trend verileri (günlük)"""
        try:
            start_date, end_date = get_date_range(period)
            if days:
                now = get_kktc_now()
                start_date = now - timedelta(days=days)
                end_date = now

            delta = (end_date - start_date).days
            if delta < 1:
                delta = 1

            labels = []
            values = []

            for i in range(delta):
                day = start_date + timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)

                total = db.session.query(
                    func.coalesce(func.sum(MinibarIslemDetay.tuketim), 0)
                ).join(MinibarIslem).filter(
                    MinibarIslem.islem_tarihi >= day_start,
                    MinibarIslem.islem_tarihi < day_end,
                    MinibarIslemDetay.tuketim > 0,
                    ~MinibarIslem.personel_id.in_(get_excluded_user_ids())
                ).scalar() or 0

                labels.append(day_start.strftime('%d.%m'))
                values.append(int(total))

            return {'labels': labels, 'values': values}
        except Exception as e:
            logger.error(f"Consumption trends hatası: {e}")
            return {'labels': [], 'values': []}

    @staticmethod
    def get_top_consumed_products(limit=10, period='this_month'):
        """En çok tüketilen ürünler"""
        try:
            start_date, end_date = get_date_range(period)

            results = db.session.query(
                Urun.urun_adi,
                func.sum(MinibarIslemDetay.tuketim).label('toplam')
            ).join(MinibarIslemDetay, Urun.id == MinibarIslemDetay.urun_id
            ).join(MinibarIslem, MinibarIslemDetay.islem_id == MinibarIslem.id
            ).filter(
                MinibarIslem.islem_tarihi >= start_date,
                MinibarIslem.islem_tarihi < end_date,
                MinibarIslemDetay.tuketim > 0,
                ~MinibarIslem.personel_id.in_(get_excluded_user_ids())
            ).group_by(Urun.urun_adi
            ).order_by(desc('toplam')
            ).limit(limit).all()

            return {
                'labels': [r[0] for r in results],
                'values': [int(r[1]) for r in results]
            }
        except Exception as e:
            logger.error(f"Top consumed products hatası: {e}")
            return {'labels': [], 'values': []}

    @staticmethod
    def get_room_control_stats(period='today', days=None):
        """Oda kontrol istatistikleri (günlük)"""
        try:
            start_date, end_date = get_date_range(period)
            if days:
                now = get_kktc_now()
                start_date = now - timedelta(days=days)
                end_date = now

            delta = (end_date - start_date).days
            if delta < 1:
                delta = 1

            labels = []
            values = []

            for i in range(delta):
                day = start_date + timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)

                count = OdaKontrolKaydi.query.filter(
                    OdaKontrolKaydi.kontrol_tarihi >= day_start,
                    OdaKontrolKaydi.kontrol_tarihi < day_end,
                    ~OdaKontrolKaydi.personel_id.in_(get_excluded_user_ids())
                ).count()

                labels.append(day_start.strftime('%d.%m'))
                values.append(count)

            return {'labels': labels, 'values': values}
        except Exception as e:
            logger.error(f"Room control stats hatası: {e}")
            return {'labels': [], 'values': []}

    @staticmethod
    def get_recent_activity(limit=50):
        """Son aktiviteler (real-time feed - executive dashboard, superadmin dahil)"""
        try:
            activities = AuditLog.query.order_by(
                desc(AuditLog.islem_tarihi)
            ).limit(limit).all()

            result = []
            for a in activities:
                kullanici = Kullanici.query.get(a.kullanici_id) if a.kullanici_id else None
                result.append({
                    'id': a.id,
                    'zaman': a.islem_tarihi.strftime('%H:%M:%S') if a.islem_tarihi else '',
                    'tarih': a.islem_tarihi.strftime('%d.%m.%Y') if a.islem_tarihi else '',
                    'kullanici': kullanici.ad_soyad if kullanici else 'Sistem',
                    'rol': kullanici.rol if kullanici else '-',
                    'islem': a.islem_tipi.value if hasattr(a.islem_tipi, 'value') else str(a.islem_tipi),
                    'detay': a.aciklama or '',
                    'tablo': a.tablo_adi or ''
                })

            return result
        except Exception as e:
            logger.error(f"Recent activity hatası: {e}")
            return []

    @staticmethod
    def get_task_completion_by_hotel(period='today'):
        """Otel bazlı görev tamamlanma oranları (sadece doluluk bilgisi yüklendikten sonra oluşturulan görevler)"""
        try:
            start_date, end_date = get_date_range(period)
            oteller = Otel.query.filter_by(aktif=True).order_by(Otel.id).all()
            data = []

            for otel in oteller:
                # Sadece misafir kayıtlı (doluluk bilgisi yüklendikten sonra oluşturulan) görevleri al
                gorevler = GunlukGorev.query.filter(
                    GunlukGorev.otel_id == otel.id,
                    GunlukGorev.gorev_tarihi >= start_date.date(),
                    GunlukGorev.gorev_tarihi <= end_date.date(),
                    GunlukGorev.id.in_(
                        db.session.query(GorevDetay.gorev_id).filter(
                            GorevDetay.misafir_kayit_id.isnot(None)
                        ).distinct()
                    )
                ).all()
                toplam = len(gorevler)
                tamamlanan = sum(1 for g in gorevler if g.durum == GorevDurum.COMPLETED)
                oran = round((tamamlanan / toplam * 100) if toplam > 0 else 0)
                data.append({
                    'otel': otel.ad,
                    'toplam': toplam,
                    'tamamlanan': tamamlanan,
                    'oran': oran
                })

            return data
        except Exception as e:
            logger.error(f"Task completion by hotel hatası: {e}")
            return []

    @staticmethod
    def get_hourly_activity(period='today'):
        """Saatlik aktivite dağılımı"""
        try:
            start_date, end_date = get_date_range(period)

            results = db.session.query(
                extract('hour', AuditLog.islem_tarihi).label('saat'),
                func.count(AuditLog.id).label('sayi')
            ).filter(
                AuditLog.islem_tarihi >= start_date,
                AuditLog.islem_tarihi < end_date,
                ~AuditLog.kullanici_id.in_(get_excluded_user_ids())
            ).group_by('saat').order_by('saat').all()

            hours = {int(r.saat): r.sayi for r in results}
            labels = [f'{h:02d}:00' for h in range(24)]
            values = [hours.get(h, 0) for h in range(24)]

            return {'labels': labels, 'values': values}
        except Exception as e:
            logger.error(f"Hourly activity hatası: {e}")
            return {'labels': [], 'values': []}

    @staticmethod
    def get_weekly_summary():
        """Seçilen döneme göre dinamik özet kartları:
        - Görev Tamamlanma (tamamlanan/toplam)
        - Ort. Tüketim/İşlem (sadece tüketim kaydı olan işlemler)
        - Bugünkü DND Sayısı
        """
        try:
            now = get_kktc_now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            # --- Görev Tamamlanma (bugün, sadece misafir kayıtlı) ---
            gorevler = GunlukGorev.query.filter(
                GunlukGorev.gorev_tarihi == today_start.date(),
                GunlukGorev.id.in_(
                    db.session.query(GorevDetay.gorev_id).filter(
                        GorevDetay.misafir_kayit_id.isnot(None)
                    ).distinct()
                )
            ).all()
            toplam_gorev = len(gorevler)
            tamamlanan_gorev = sum(1 for g in gorevler if g.durum == GorevDurum.COMPLETED)

            # --- Ort. Tüketim/İşlem (sadece tüketim kaydı olan işlemler) ---
            # Tüketim kaydı olan işlem = MinibarIslem where en az 1 detayda tuketim > 0
            tuketim_islem_q = db.session.query(
                func.count(func.distinct(MinibarIslem.id)).label('islem_sayisi'),
                func.coalesce(func.sum(MinibarIslemDetay.tuketim), 0).label('toplam_tuketim')
            ).join(MinibarIslemDetay).filter(
                MinibarIslem.islem_tarihi >= today_start,
                MinibarIslem.islem_tarihi < today_end,
                MinibarIslemDetay.tuketim > 0,
                ~MinibarIslem.personel_id.in_(get_excluded_user_ids())
            ).first()

            tuketimli_islem_sayisi = tuketim_islem_q.islem_sayisi if tuketim_islem_q else 0
            toplam_tuketim = int(tuketim_islem_q.toplam_tuketim) if tuketim_islem_q else 0
            ort_tuketim_islem = round(toplam_tuketim / tuketimli_islem_sayisi, 2) if tuketimli_islem_sayisi > 0 else 0

            # --- Bugünkü DND Sayısı ---
            bugun_dnd = OdaDNDKayit.query.filter(
                OdaDNDKayit.kayit_tarihi == today_start.date(),
                OdaDNDKayit.durum == 'aktif'
            ).count()

            # Ayrıca GorevDetay'daki DND'ler (görev sistemi üzerinden)
            gorev_dnd = GorevDetay.query.join(GunlukGorev).filter(
                GunlukGorev.gorev_tarihi == today_start.date(),
                GorevDetay.durum == 'dnd_pending',
                GorevDetay.misafir_kayit_id.isnot(None)
            ).count()

            toplam_dnd = bugun_dnd + gorev_dnd

            return {
                'gorev_tamamlanan': tamamlanan_gorev,
                'gorev_toplam': toplam_gorev,
                'ort_tuketim_islem': ort_tuketim_islem,
                'tuketimli_islem': tuketimli_islem_sayisi,
                'toplam_tuketim': toplam_tuketim,
                'bugun_dnd': toplam_dnd
            }
        except Exception as e:
            logger.error(f"Weekly summary hatası: {e}")
            return {
                'gorev_tamamlanan': 0, 'gorev_toplam': 0,
                'ort_tuketim_islem': 0, 'tuketimli_islem': 0,
                'toplam_tuketim': 0, 'bugun_dnd': 0
            }
