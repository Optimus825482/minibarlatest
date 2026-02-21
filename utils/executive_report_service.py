"""
Executive Report Service
Üst yönetici raporlama merkezi - Özelleştirilebilir raporlar
Ürün, Personel, Otel bazlı detaylı raporlama
"""

from datetime import datetime, timedelta, date
from sqlalchemy import func, desc, asc, cast, Date, extract, case, and_, or_, text
from models import (
    db, Kullanici, Otel, Oda, Urun, UrunGrup, Kat,
    MinibarIslem, MinibarIslemDetay, StokHareket,
    PersonelZimmet, PersonelZimmetDetay,
    AuditLog, SistemLog, GunlukGorev, GorevDetay,
    OdaKontrolKaydi, MinibarIslemTipi, KullaniciRol,
    GorevDurum, GorevTipi, HareketTipi,
    OdaDNDKayit, OdaDNDKontrol, DNDKontrol
)
import logging
import pytz
from utils.helpers import get_excluded_user_ids, EXCLUDED_USERNAMES

logger = logging.getLogger(__name__)
KKTC_TZ = pytz.timezone('Europe/Nicosia')


def get_kktc_now():
    return datetime.now(KKTC_TZ)


def parse_date(date_str):
    """Tarih string'ini date objesine çevir"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


class ExecutiveReportService:
    """Üst yönetici raporlama servisi"""

    # ==========================================
    # ÜRÜN TÜKETİM RAPORLARI
    # ==========================================

    @staticmethod
    def get_product_consumption_report(start_date=None, end_date=None, otel_id=None,
                                        kat_id=None, oda_id=None, urun_id=None,
                                        grup_id=None, group_by='urun'):
        """
        Ürün bazlı tüketim raporu - Çok katmanlı filtreleme
        group_by: 'urun', 'otel', 'kat', 'oda', 'gun', 'hafta', 'ay'
        """
        try:
            if not start_date:
                start_date = get_kktc_now().date() - timedelta(days=30)
            if not end_date:
                end_date = get_kktc_now().date()

            # Base query
            query = db.session.query(
                MinibarIslemDetay.urun_id,
                Urun.urun_adi,
                UrunGrup.grup_adi,
                func.sum(MinibarIslemDetay.tuketim).label('toplam_tuketim'),
                func.sum(MinibarIslemDetay.eklenen_miktar).label('toplam_eklenen'),
                func.sum(MinibarIslemDetay.ekstra_miktar).label('toplam_ekstra'),
                func.count(MinibarIslemDetay.id).label('islem_sayisi')
            ).join(
                MinibarIslem, MinibarIslemDetay.islem_id == MinibarIslem.id
            ).join(
                Urun, MinibarIslemDetay.urun_id == Urun.id
            ).join(
                UrunGrup, Urun.grup_id == UrunGrup.id
            ).join(
                Oda, MinibarIslem.oda_id == Oda.id
            ).join(
                Kat, Oda.kat_id == Kat.id
            ).filter(
                cast(MinibarIslem.islem_tarihi, Date).between(start_date, end_date),
                MinibarIslemDetay.tuketim > 0,
                ~MinibarIslem.personel_id.in_(get_excluded_user_ids())
            )

            # Filtreler
            if otel_id:
                query = query.filter(Kat.otel_id == otel_id)
            if kat_id:
                query = query.filter(Oda.kat_id == kat_id)
            if oda_id:
                query = query.filter(MinibarIslem.oda_id == oda_id)
            if urun_id:
                query = query.filter(MinibarIslemDetay.urun_id == urun_id)
            if grup_id:
                query = query.filter(Urun.grup_id == grup_id)

            # Gruplama
            if group_by == 'urun':
                query = query.group_by(
                    MinibarIslemDetay.urun_id, Urun.urun_adi, UrunGrup.grup_adi
                ).order_by(desc('toplam_tuketim'))
            elif group_by == 'otel':
                query = query.add_columns(
                    Kat.otel_id, Otel.ad.label('otel_adi')
                ).join(Otel, Kat.otel_id == Otel.id).group_by(
                    Kat.otel_id, Otel.ad,
                    MinibarIslemDetay.urun_id, Urun.urun_adi, UrunGrup.grup_adi
                ).order_by(Otel.ad, desc('toplam_tuketim'))
            elif group_by == 'kat':
                query = query.add_columns(
                    Kat.id.label('kat_id_col'), Kat.kat_adi, Kat.otel_id, Otel.ad.label('otel_adi')
                ).join(Otel, Kat.otel_id == Otel.id).group_by(
                    Kat.id, Kat.kat_adi, Kat.otel_id, Otel.ad,
                    MinibarIslemDetay.urun_id, Urun.urun_adi, UrunGrup.grup_adi
                ).order_by(Otel.ad, Kat.kat_adi, desc('toplam_tuketim'))
            elif group_by == 'oda':
                query = query.add_columns(
                    Oda.id.label('oda_id_col'), Oda.oda_no,
                    Kat.kat_adi, Otel.ad.label('otel_adi')
                ).join(Otel, Kat.otel_id == Otel.id).group_by(
                    Oda.id, Oda.oda_no, Kat.kat_adi, Otel.ad,
                    MinibarIslemDetay.urun_id, Urun.urun_adi, UrunGrup.grup_adi
                ).order_by(Otel.ad, Oda.oda_no, desc('toplam_tuketim'))
            elif group_by == 'gun':
                query = query.add_columns(
                    cast(MinibarIslem.islem_tarihi, Date).label('tarih')
                ).group_by(
                    cast(MinibarIslem.islem_tarihi, Date),
                    MinibarIslemDetay.urun_id, Urun.urun_adi, UrunGrup.grup_adi
                ).order_by(desc('tarih'))

            results = query.all()
            data = []
            for r in results:
                row = {
                    'urun_id': r.urun_id,
                    'urun_adi': r.urun_adi,
                    'grup_adi': r.grup_adi,
                    'toplam_tuketim': r.toplam_tuketim or 0,
                    'toplam_eklenen': r.toplam_eklenen or 0,
                    'toplam_ekstra': r.toplam_ekstra or 0,
                    'toplam_satis_tutari': 0,
                    'toplam_kar': 0,
                    'islem_sayisi': r.islem_sayisi or 0
                }
                if group_by == 'otel':
                    row['otel_id'] = r.otel_id
                    row['otel_adi'] = r.otel_adi
                elif group_by == 'kat':
                    row['kat_id'] = r.kat_id_col
                    row['kat_adi'] = r.kat_adi
                    row['otel_adi'] = r.otel_adi
                elif group_by == 'oda':
                    row['oda_id'] = r.oda_id_col
                    row['oda_no'] = r.oda_no
                    row['kat_adi'] = r.kat_adi
                    row['otel_adi'] = r.otel_adi
                elif group_by == 'gun':
                    row['tarih'] = r.tarih.isoformat() if r.tarih else None
                data.append(row)

            # Özet istatistikler
            summary = {
                'toplam_tuketim': sum(d['toplam_tuketim'] for d in data),
                'toplam_satis': 0,
                'toplam_kar': 0,
                'toplam_islem': sum(d['islem_sayisi'] for d in data),
                'urun_cesidi': len(set(d['urun_id'] for d in data)),
                'baslangic': start_date.isoformat(),
                'bitis': end_date.isoformat()
            }

            return {'success': True, 'data': data, 'summary': summary}

        except Exception as e:
            logger.error(f"Ürün tüketim raporu hatası: {e}")
            return {'success': False, 'error': str(e), 'data': [], 'summary': {}}

    # ==========================================
    # PERSONEL PERFORMANS RAPORLARI
    # ==========================================

    @staticmethod
    def get_personnel_report(start_date=None, end_date=None, otel_id=None,
                              personel_id=None, rol=None):
        """
        Personel performans raporu
        Kontrol edilen oda sayısı, eklenen ürün, tüketim tespiti
        """
        try:
            if not start_date:
                start_date = get_kktc_now().date() - timedelta(days=30)
            if not end_date:
                end_date = get_kktc_now().date()

            # Oda kontrol istatistikleri
            kontrol_query = db.session.query(
                Kullanici.id.label('personel_id'),
                Kullanici.ad,
                Kullanici.soyad,
                Kullanici.rol,
                Otel.ad.label('otel_adi'),
                func.count(func.distinct(OdaKontrolKaydi.oda_id)).label('kontrol_edilen_oda'),
                func.count(OdaKontrolKaydi.id).label('toplam_kontrol'),
                func.avg(
                    func.extract('epoch', OdaKontrolKaydi.bitis_zamani - OdaKontrolKaydi.baslangic_zamani)
                ).label('ort_kontrol_suresi_sn')
            ).join(
                OdaKontrolKaydi, Kullanici.id == OdaKontrolKaydi.personel_id
            ).join(
                Oda, OdaKontrolKaydi.oda_id == Oda.id
            ).join(
                Kat, Oda.kat_id == Kat.id
            ).join(
                Otel, Kat.otel_id == Otel.id
            ).filter(
                OdaKontrolKaydi.kontrol_tarihi.between(start_date, end_date),
                ~Kullanici.kullanici_adi.in_(EXCLUDED_USERNAMES)
            )

            if otel_id:
                kontrol_query = kontrol_query.filter(Kat.otel_id == otel_id)
            if personel_id:
                kontrol_query = kontrol_query.filter(Kullanici.id == personel_id)
            if rol:
                kontrol_query = kontrol_query.filter(Kullanici.rol == rol)

            kontrol_query = kontrol_query.group_by(
                Kullanici.id, Kullanici.ad, Kullanici.soyad, Kullanici.rol, Otel.ad
            ).order_by(desc('toplam_kontrol'))

            kontrol_results = kontrol_query.all()

            # Minibar işlem istatistikleri (eklenen ürün, tespit edilen tüketim)
            minibar_query = db.session.query(
                MinibarIslem.personel_id,
                func.sum(MinibarIslemDetay.eklenen_miktar).label('toplam_eklenen'),
                func.sum(MinibarIslemDetay.ekstra_miktar).label('toplam_ekstra'),
                func.sum(MinibarIslemDetay.tuketim).label('tespit_tuketim'),
                func.count(func.distinct(MinibarIslem.oda_id)).label('minibar_oda_sayisi')
            ).join(
                MinibarIslemDetay, MinibarIslem.id == MinibarIslemDetay.islem_id
            ).filter(
                cast(MinibarIslem.islem_tarihi, Date).between(start_date, end_date),
                ~MinibarIslem.personel_id.in_(get_excluded_user_ids())
            )

            if otel_id:
                minibar_query = minibar_query.join(
                    Oda, MinibarIslem.oda_id == Oda.id
                ).join(Kat, Oda.kat_id == Kat.id).filter(Kat.otel_id == otel_id)
            if personel_id:
                minibar_query = minibar_query.filter(MinibarIslem.personel_id == personel_id)

            minibar_query = minibar_query.group_by(MinibarIslem.personel_id)
            minibar_results = {r.personel_id: r for r in minibar_query.all()}

            data = []
            for r in kontrol_results:
                mb = minibar_results.get(r.personel_id)
                ort_sure = round(r.ort_kontrol_suresi_sn / 60, 1) if r.ort_kontrol_suresi_sn else 0
                data.append({
                    'personel_id': r.personel_id,
                    'ad_soyad': f"{r.ad} {r.soyad}",
                    'rol': r.rol,
                    'otel_adi': r.otel_adi,
                    'kontrol_edilen_oda': r.kontrol_edilen_oda or 0,
                    'toplam_kontrol': r.toplam_kontrol or 0,
                    'ort_kontrol_suresi_dk': ort_sure,
                    'toplam_eklenen': mb.toplam_eklenen if mb else 0,
                    'toplam_ekstra': mb.toplam_ekstra if mb else 0,
                    'tespit_tuketim': mb.tespit_tuketim if mb else 0,
                    'minibar_oda_sayisi': mb.minibar_oda_sayisi if mb else 0
                })

            summary = {
                'toplam_personel': len(data),
                'toplam_kontrol': sum(d['toplam_kontrol'] for d in data),
                'toplam_oda': sum(d['kontrol_edilen_oda'] for d in data),
                'ort_kontrol_suresi': round(
                    sum(d['ort_kontrol_suresi_dk'] for d in data) / max(len(data), 1), 1
                ),
                'baslangic': start_date.isoformat(),
                'bitis': end_date.isoformat()
            }

            return {'success': True, 'data': data, 'summary': summary}

        except Exception as e:
            logger.error(f"Personel raporu hatası: {e}")
            return {'success': False, 'error': str(e), 'data': [], 'summary': {}}

    # ==========================================
    # OTEL RAPORLARI
    # ==========================================

    @staticmethod
    def get_hotel_report(start_date=None, end_date=None, otel_id=None):
        """
        Otel bazlı kapsamlı rapor
        Tüketim, kontrol, görev tamamlanma, personel performansı
        """
        try:
            if not start_date:
                start_date = get_kktc_now().date() - timedelta(days=30)
            if not end_date:
                end_date = get_kktc_now().date()

            oteller_query = db.session.query(Otel).filter(Otel.aktif == True)
            if otel_id:
                oteller_query = oteller_query.filter(Otel.id == otel_id)
            oteller = oteller_query.all()

            data = []
            for otel in oteller:
                # Oda sayısı
                oda_sayisi = Oda.query.join(Kat).filter(
                    Kat.otel_id == otel.id, Oda.aktif == True
                ).count()

                # Tüketim
                tuketim = db.session.query(
                    func.sum(MinibarIslemDetay.tuketim).label('toplam'),
                    func.count(func.distinct(MinibarIslem.oda_id)).label('tuketim_oda')
                ).join(
                    MinibarIslem, MinibarIslemDetay.islem_id == MinibarIslem.id
                ).join(
                    Oda, MinibarIslem.oda_id == Oda.id
                ).join(Kat, Oda.kat_id == Kat.id).filter(
                    Kat.otel_id == otel.id,
                    cast(MinibarIslem.islem_tarihi, Date).between(start_date, end_date),
                    MinibarIslemDetay.tuketim > 0,
                    ~MinibarIslem.personel_id.in_(get_excluded_user_ids())
                ).first()

                # Kontrol
                kontrol = db.session.query(
                    func.count(OdaKontrolKaydi.id).label('toplam'),
                    func.count(func.distinct(OdaKontrolKaydi.oda_id)).label('oda_sayisi'),
                    func.count(func.distinct(OdaKontrolKaydi.personel_id)).label('personel_sayisi')
                ).join(
                    Oda, OdaKontrolKaydi.oda_id == Oda.id
                ).join(Kat, Oda.kat_id == Kat.id).filter(
                    Kat.otel_id == otel.id,
                    OdaKontrolKaydi.kontrol_tarihi.between(start_date, end_date),
                    ~OdaKontrolKaydi.personel_id.in_(get_excluded_user_ids())
                ).first()

                # Görev tamamlanma (sadece doluluk bilgisi yüklendikten sonra oluşturulan görevler)
                gorev = db.session.query(
                    func.count(GorevDetay.id).label('toplam'),
                    func.count(case((GorevDetay.durum == 'completed', 1))).label('tamamlanan')
                ).join(
                    GunlukGorev, GorevDetay.gorev_id == GunlukGorev.id
                ).filter(
                    GunlukGorev.otel_id == otel.id,
                    GunlukGorev.gorev_tarihi.between(start_date, end_date),
                    GorevDetay.misafir_kayit_id.isnot(None)
                ).first()

                gorev_oran = round(
                    (gorev.tamamlanan / gorev.toplam * 100) if gorev.toplam else 0, 1
                )

                # En çok tüketilen 5 ürün
                top_urunler = db.session.query(
                    Urun.urun_adi,
                    func.sum(MinibarIslemDetay.tuketim).label('miktar')
                ).join(
                    MinibarIslemDetay, Urun.id == MinibarIslemDetay.urun_id
                ).join(
                    MinibarIslem, MinibarIslemDetay.islem_id == MinibarIslem.id
                ).join(
                    Oda, MinibarIslem.oda_id == Oda.id
                ).join(Kat, Oda.kat_id == Kat.id).filter(
                    Kat.otel_id == otel.id,
                    cast(MinibarIslem.islem_tarihi, Date).between(start_date, end_date),
                    MinibarIslemDetay.tuketim > 0,
                    ~MinibarIslem.personel_id.in_(get_excluded_user_ids())
                ).group_by(Urun.urun_adi).order_by(desc('miktar')).limit(5).all()

                data.append({
                    'otel_id': otel.id,
                    'otel_adi': otel.ad,
                    'oda_sayisi': oda_sayisi,
                    'toplam_tuketim': tuketim.toplam or 0,
                    'satis_tutari': 0,
                    'tuketim_oda_sayisi': tuketim.tuketim_oda or 0,
                    'toplam_kontrol': kontrol.toplam or 0,
                    'kontrol_oda_sayisi': kontrol.oda_sayisi or 0,
                    'aktif_personel': kontrol.personel_sayisi or 0,
                    'toplam_gorev': gorev.toplam or 0,
                    'tamamlanan_gorev': gorev.tamamlanan or 0,
                    'gorev_oran': gorev_oran,
                    'top_urunler': [{'urun': u.urun_adi, 'miktar': u.miktar} for u in top_urunler]
                })

            summary = {
                'toplam_otel': len(data),
                'toplam_tuketim': sum(d['toplam_tuketim'] for d in data),
                'toplam_satis': 0,
                'toplam_kontrol': sum(d['toplam_kontrol'] for d in data),
                'baslangic': start_date.isoformat(),
                'bitis': end_date.isoformat()
            }

            return {'success': True, 'data': data, 'summary': summary}

        except Exception as e:
            logger.error(f"Otel raporu hatası: {e}")
            return {'success': False, 'error': str(e), 'data': [], 'summary': {}}

    # ==========================================
    # GÖREV PERFORMANS RAPORU
    # ==========================================

    @staticmethod
    def get_task_performance_report(start_date=None, end_date=None, otel_id=None, gorev_tipi=None):
        """
        Görev tipi bazlı performans raporu
        Tamamlanma oranları, DND oranları, ortalama süreler, personel bazlı kırılım
        """
        try:
            if not start_date:
                start_date = get_kktc_now().date() - timedelta(days=30)
            if not end_date:
                end_date = get_kktc_now().date()

            # --- Görev tipi bazlı özet (sadece doluluk bilgisi yüklendikten sonra oluşturulan görevler) ---
            tip_query = db.session.query(
                GunlukGorev.gorev_tipi,
                func.count(GorevDetay.id).label('toplam_oda'),
                func.count(case((GorevDetay.durum == 'completed', 1))).label('tamamlanan'),
                func.count(case((GorevDetay.durum == 'dnd_pending', 1))).label('dnd_bekleyen'),
                func.count(case((GorevDetay.durum == 'incomplete', 1))).label('tamamlanmayan'),
                func.sum(GorevDetay.dnd_sayisi).label('toplam_dnd'),
                func.count(func.distinct(GunlukGorev.id)).label('gorev_sayisi'),
                func.count(func.distinct(GunlukGorev.personel_id)).label('personel_sayisi')
            ).join(
                GorevDetay, GunlukGorev.id == GorevDetay.gorev_id
            ).filter(
                GunlukGorev.gorev_tarihi.between(start_date, end_date),
                GorevDetay.misafir_kayit_id.isnot(None)
            )

            if otel_id:
                tip_query = tip_query.filter(GunlukGorev.otel_id == otel_id)
            if gorev_tipi:
                tip_query = tip_query.filter(GunlukGorev.gorev_tipi == gorev_tipi)

            tip_query = tip_query.group_by(GunlukGorev.gorev_tipi)
            tip_results = tip_query.all()

            tip_data = []
            for r in tip_results:
                toplam = r.toplam_oda or 0
                tamamlanan = r.tamamlanan or 0
                oran = round((tamamlanan / toplam * 100) if toplam else 0, 1)
                dnd_oran = round(((r.dnd_bekleyen or 0) / toplam * 100) if toplam else 0, 1)
                tip_data.append({
                    'gorev_tipi': r.gorev_tipi,
                    'gorev_tipi_label': ExecutiveReportService._gorev_tipi_label(r.gorev_tipi),
                    'toplam_oda': toplam,
                    'tamamlanan': tamamlanan,
                    'tamamlanma_orani': oran,
                    'dnd_bekleyen': r.dnd_bekleyen or 0,
                    'dnd_orani': dnd_oran,
                    'tamamlanmayan': r.tamamlanmayan or 0,
                    'toplam_dnd': r.toplam_dnd or 0,
                    'gorev_sayisi': r.gorev_sayisi or 0,
                    'personel_sayisi': r.personel_sayisi or 0
                })

            # --- Ortalama tamamlanma süreleri (görev bazlı) ---
            sure_query = db.session.query(
                GunlukGorev.gorev_tipi,
                func.avg(
                    func.extract('epoch',
                        GunlukGorev.tamamlanma_tarihi - func.cast(
                            func.concat(func.cast(GunlukGorev.gorev_tarihi, db.Text), ' 00:00:00'),
                            db.DateTime
                        )
                    )
                ).label('ort_sure_sn')
            ).filter(
                GunlukGorev.gorev_tarihi.between(start_date, end_date),
                GunlukGorev.tamamlanma_tarihi.isnot(None)
            )
            if otel_id:
                sure_query = sure_query.filter(GunlukGorev.otel_id == otel_id)
            if gorev_tipi:
                sure_query = sure_query.filter(GunlukGorev.gorev_tipi == gorev_tipi)
            sure_query = sure_query.group_by(GunlukGorev.gorev_tipi)
            sure_map = {r.gorev_tipi: round((r.ort_sure_sn or 0) / 3600, 1) for r in sure_query.all()}

            for t in tip_data:
                t['ort_tamamlanma_saat'] = sure_map.get(t['gorev_tipi'], 0)

            # --- Personel bazlı kırılım ---
            # NOT: gunluk_gorevler.personel_id çoğunlukla NULL (görevler otele atanıyor).
            # Personel bilgisi minibar_islemleri.personel_id üzerinden oda+tarih eşleşmesiyle bulunuyor.
            personel_query = db.session.query(
                MinibarIslem.personel_id,
                Kullanici.ad,
                Kullanici.soyad,
                func.count(GorevDetay.id).label('toplam_oda'),
                func.count(case((GorevDetay.durum == 'completed', 1))).label('tamamlanan'),
                func.sum(GorevDetay.dnd_sayisi).label('toplam_dnd'),
                func.count(func.distinct(GunlukGorev.id)).label('gorev_sayisi')
            ).join(
                GorevDetay, GunlukGorev.id == GorevDetay.gorev_id
            ).join(
                MinibarIslem,
                and_(
                    MinibarIslem.oda_id == GorevDetay.oda_id,
                    cast(MinibarIslem.islem_tarihi, Date) == GunlukGorev.gorev_tarihi
                )
            ).join(
                Kullanici, MinibarIslem.personel_id == Kullanici.id
            ).filter(
                GunlukGorev.gorev_tarihi.between(start_date, end_date),
                GorevDetay.misafir_kayit_id.isnot(None),
                ~Kullanici.kullanici_adi.in_(EXCLUDED_USERNAMES)
            )
            if otel_id:
                personel_query = personel_query.filter(GunlukGorev.otel_id == otel_id)
            if gorev_tipi:
                personel_query = personel_query.filter(GunlukGorev.gorev_tipi == gorev_tipi)

            personel_query = personel_query.group_by(
                MinibarIslem.personel_id, Kullanici.ad, Kullanici.soyad
            ).order_by(desc('tamamlanan'))

            personel_data = []
            for r in personel_query.all():
                toplam = r.toplam_oda or 0
                tamamlanan = r.tamamlanan or 0
                oran = round((tamamlanan / toplam * 100) if toplam else 0, 1)
                personel_data.append({
                    'personel_id': r.personel_id,
                    'ad_soyad': f"{r.ad} {r.soyad}",
                    'toplam_oda': toplam,
                    'tamamlanan': tamamlanan,
                    'tamamlanma_orani': oran,
                    'toplam_dnd': r.toplam_dnd or 0,
                    'gorev_sayisi': r.gorev_sayisi or 0
                })

            # --- Günlük trend ---
            trend_query = db.session.query(
                GunlukGorev.gorev_tarihi,
                func.count(GorevDetay.id).label('toplam'),
                func.count(case((GorevDetay.durum == 'completed', 1))).label('tamamlanan'),
                func.sum(GorevDetay.dnd_sayisi).label('dnd')
            ).join(
                GorevDetay, GunlukGorev.id == GorevDetay.gorev_id
            ).filter(
                GunlukGorev.gorev_tarihi.between(start_date, end_date),
                GorevDetay.misafir_kayit_id.isnot(None)
            )
            if otel_id:
                trend_query = trend_query.filter(GunlukGorev.otel_id == otel_id)
            if gorev_tipi:
                trend_query = trend_query.filter(GunlukGorev.gorev_tipi == gorev_tipi)
            trend_query = trend_query.group_by(GunlukGorev.gorev_tarihi).order_by(asc(GunlukGorev.gorev_tarihi))

            trend_data = [{
                'tarih': r.gorev_tarihi.isoformat(),
                'tarih_label': r.gorev_tarihi.strftime('%d.%m'),
                'toplam': r.toplam or 0,
                'tamamlanan': r.tamamlanan or 0,
                'dnd': r.dnd or 0,
                'oran': round(((r.tamamlanan or 0) / (r.toplam or 1)) * 100, 1)
            } for r in trend_query.all()]

            summary = {
                'toplam_gorev_tipi': len(tip_data),
                'toplam_oda_gorev': sum(t['toplam_oda'] for t in tip_data),
                'toplam_tamamlanan': sum(t['tamamlanan'] for t in tip_data),
                'genel_oran': round(
                    sum(t['tamamlanan'] for t in tip_data) / max(sum(t['toplam_oda'] for t in tip_data), 1) * 100, 1
                ),
                'toplam_dnd': sum(t['toplam_dnd'] for t in tip_data),
                'aktif_personel': len(personel_data),
                'baslangic': start_date.isoformat(),
                'bitis': end_date.isoformat()
            }

            return {
                'success': True,
                'tip_data': tip_data,
                'personel_data': personel_data,
                'trend_data': trend_data,
                'summary': summary
            }

        except Exception as e:
            logger.error(f"Görev performans raporu hatası: {e}")
            return {'success': False, 'error': str(e), 'tip_data': [], 'personel_data': [], 'trend_data': [], 'summary': {}}

    # ==========================================
    # KARŞILAŞTIRMALI ANALİZ RAPORU
    # ==========================================

    @staticmethod
    def get_comparative_analysis(period1_start=None, period1_end=None,
                                  period2_start=None, period2_end=None, otel_id=None):
        """
        İki dönem karşılaştırması
        Tüketim, kontrol, görev tamamlanma, personel performansı
        """
        try:
            today = get_kktc_now().date()
            if not period1_start:
                period1_start = today.replace(day=1)
            if not period1_end:
                period1_end = today
            if not period2_start:
                # Geçen ay
                prev = period1_start - timedelta(days=1)
                period2_start = prev.replace(day=1)
            if not period2_end:
                period2_end = period1_start - timedelta(days=1)

            def get_period_metrics(p_start, p_end):
                """Bir dönem için tüm metrikleri topla"""
                filters = [cast(MinibarIslem.islem_tarihi, Date).between(p_start, p_end)]
                otel_filter = []
                if otel_id:
                    otel_filter = [Kat.otel_id == otel_id]

                # Tüketim
                tuk_q = db.session.query(
                    func.sum(MinibarIslemDetay.tuketim).label('tuketim'),
                    func.count(func.distinct(MinibarIslem.oda_id)).label('oda_sayisi'),
                    func.count(func.distinct(MinibarIslem.personel_id)).label('personel')
                ).join(
                    MinibarIslemDetay, MinibarIslem.id == MinibarIslemDetay.islem_id
                ).join(Oda, MinibarIslem.oda_id == Oda.id
                ).join(Kat, Oda.kat_id == Kat.id
                ).filter(*filters, MinibarIslemDetay.tuketim > 0, *otel_filter,
                         ~MinibarIslem.personel_id.in_(get_excluded_user_ids()))
                tuk = tuk_q.first()

                # Kontrol
                k_filters = [
                    OdaKontrolKaydi.kontrol_tarihi.between(p_start, p_end),
                    ~OdaKontrolKaydi.personel_id.in_(get_excluded_user_ids())
                ]
                if otel_id:
                    kontrol_q = db.session.query(
                        func.count(OdaKontrolKaydi.id).label('kontrol'),
                        func.count(func.distinct(OdaKontrolKaydi.oda_id)).label('oda'),
                        func.avg(
                            func.extract('epoch', OdaKontrolKaydi.bitis_zamani - OdaKontrolKaydi.baslangic_zamani)
                        ).label('ort_sure')
                    ).join(Oda, OdaKontrolKaydi.oda_id == Oda.id
                    ).join(Kat, Oda.kat_id == Kat.id
                    ).filter(*k_filters, Kat.otel_id == otel_id)
                else:
                    kontrol_q = db.session.query(
                        func.count(OdaKontrolKaydi.id).label('kontrol'),
                        func.count(func.distinct(OdaKontrolKaydi.oda_id)).label('oda'),
                        func.avg(
                            func.extract('epoch', OdaKontrolKaydi.bitis_zamani - OdaKontrolKaydi.baslangic_zamani)
                        ).label('ort_sure')
                    ).filter(*k_filters)
                kontrol = kontrol_q.first()

                # Görev (sadece doluluk bilgisi yüklendikten sonra oluşturulan görevler)
                g_filters = [
                    GunlukGorev.gorev_tarihi.between(p_start, p_end),
                    GorevDetay.misafir_kayit_id.isnot(None)
                ]
                if otel_id:
                    g_filters.append(GunlukGorev.otel_id == otel_id)
                gorev_q = db.session.query(
                    func.count(GorevDetay.id).label('toplam'),
                    func.count(case((GorevDetay.durum == 'completed', 1))).label('tamamlanan'),
                    func.sum(GorevDetay.dnd_sayisi).label('dnd')
                ).join(GunlukGorev, GorevDetay.gorev_id == GunlukGorev.id
                ).filter(*g_filters)
                gorev = gorev_q.first()

                gorev_toplam = gorev.toplam or 0
                gorev_tamamlanan = gorev.tamamlanan or 0

                return {
                    'tuketim': tuk.tuketim or 0,
                    'tuketim_oda': tuk.oda_sayisi or 0,
                    'tuketim_personel': tuk.personel or 0,
                    'kontrol': kontrol.kontrol or 0,
                    'kontrol_oda': kontrol.oda or 0,
                    'ort_kontrol_sure_dk': round((kontrol.ort_sure or 0) / 60, 1),
                    'gorev_toplam': gorev_toplam,
                    'gorev_tamamlanan': gorev_tamamlanan,
                    'gorev_oran': round((gorev_tamamlanan / gorev_toplam * 100) if gorev_toplam else 0, 1),
                    'toplam_dnd': gorev.dnd or 0
                }

            p1 = get_period_metrics(period1_start, period1_end)
            p2 = get_period_metrics(period2_start, period2_end)

            def calc_change(current, previous):
                if previous == 0:
                    return 100.0 if current > 0 else 0.0
                return round(((current - previous) / previous) * 100, 1)

            comparison = {}
            for key in p1:
                comparison[key] = {
                    'period1': p1[key],
                    'period2': p2[key],
                    'degisim': calc_change(p1[key], p2[key])
                }

            # Otel bazlı karşılaştırma
            otel_data = []
            if not otel_id:
                oteller = Otel.query.filter(Otel.aktif == True).all()
                for otel in oteller:
                    o_p1 = get_period_metrics(period1_start, period1_end)
                    # Otel bazlı hızlı sorgu
                    o_tuk1 = db.session.query(
                        func.sum(MinibarIslemDetay.tuketim)
                    ).join(MinibarIslem, MinibarIslemDetay.islem_id == MinibarIslem.id
                    ).join(Oda, MinibarIslem.oda_id == Oda.id
                    ).join(Kat, Oda.kat_id == Kat.id
                    ).filter(
                        Kat.otel_id == otel.id,
                        cast(MinibarIslem.islem_tarihi, Date).between(period1_start, period1_end),
                        MinibarIslemDetay.tuketim > 0,
                        ~MinibarIslem.personel_id.in_(get_excluded_user_ids())
                    ).scalar() or 0

                    o_tuk2 = db.session.query(
                        func.sum(MinibarIslemDetay.tuketim)
                    ).join(MinibarIslem, MinibarIslemDetay.islem_id == MinibarIslem.id
                    ).join(Oda, MinibarIslem.oda_id == Oda.id
                    ).join(Kat, Oda.kat_id == Kat.id
                    ).filter(
                        Kat.otel_id == otel.id,
                        cast(MinibarIslem.islem_tarihi, Date).between(period2_start, period2_end),
                        MinibarIslemDetay.tuketim > 0,
                        ~MinibarIslem.personel_id.in_(get_excluded_user_ids())
                    ).scalar() or 0

                    otel_data.append({
                        'otel_adi': otel.ad,
                        'period1_tuketim': o_tuk1,
                        'period2_tuketim': o_tuk2,
                        'degisim': calc_change(o_tuk1, o_tuk2)
                    })

            return {
                'success': True,
                'comparison': comparison,
                'otel_data': otel_data,
                'periods': {
                    'period1': {'start': period1_start.isoformat(), 'end': period1_end.isoformat()},
                    'period2': {'start': period2_start.isoformat(), 'end': period2_end.isoformat()}
                }
            }

        except Exception as e:
            logger.error(f"Karşılaştırmalı analiz hatası: {e}")
            return {'success': False, 'error': str(e), 'comparison': {}, 'otel_data': [], 'periods': {}}

    # ==========================================
    # DND RAPORLAMA SİSTEMİ
    # ==========================================

    @staticmethod
    def get_dnd_report(start_date=None, end_date=None, otel_id=None,
                       kat_id=None, oda_id=None, personel_id=None, group_by='oda'):
        """
        DND (Do Not Disturb) raporlama sistemi
        - Tüm DND kayıtları (OdaDNDKayit + GorevDetay dnd_pending)
        - DND sonrası tüketim kaydıyla kapatılan kayıtlar
        - Otel/kat/oda/personel bazlı gruplama
        group_by: 'oda', 'otel', 'kat', 'personel', 'gun'
        """
        try:
            if not start_date:
                start_date = get_kktc_now().date() - timedelta(days=30)
            if not end_date:
                end_date = get_kktc_now().date()

            # ---- 1. OdaDNDKayit tablosundan DND kayıtları ----
            dnd_query = db.session.query(
                OdaDNDKayit.id.label('dnd_id'),
                OdaDNDKayit.oda_id,
                Oda.oda_no,
                Kat.kat_adi,
                Kat.id.label('kat_id_col'),
                Otel.id.label('otel_id_col'),
                Otel.ad.label('otel_adi'),
                OdaDNDKayit.kayit_tarihi,
                OdaDNDKayit.dnd_sayisi,
                OdaDNDKayit.durum,
                OdaDNDKayit.ilk_dnd_zamani,
                OdaDNDKayit.son_dnd_zamani,
                OdaDNDKayit.gorev_detay_id
            ).join(
                Oda, OdaDNDKayit.oda_id == Oda.id
            ).join(
                Kat, Oda.kat_id == Kat.id
            ).join(
                Otel, OdaDNDKayit.otel_id == Otel.id
            ).filter(
                OdaDNDKayit.kayit_tarihi.between(start_date, end_date)
            )

            if otel_id:
                dnd_query = dnd_query.filter(OdaDNDKayit.otel_id == otel_id)
            if kat_id:
                dnd_query = dnd_query.filter(Kat.id == kat_id)
            if oda_id:
                dnd_query = dnd_query.filter(OdaDNDKayit.oda_id == oda_id)

            dnd_results = dnd_query.order_by(desc(OdaDNDKayit.kayit_tarihi)).all()

            # ---- 2. GorevDetay tablosundan DND kayıtları (görev sistemi) ----
            gorev_dnd_query = db.session.query(
                GorevDetay.id.label('detay_id'),
                GorevDetay.oda_id,
                Oda.oda_no,
                Kat.kat_adi,
                Kat.id.label('kat_id_col'),
                Otel.id.label('otel_id_col'),
                Otel.ad.label('otel_adi'),
                GunlukGorev.gorev_tarihi.label('kayit_tarihi'),
                GorevDetay.dnd_sayisi,
                GorevDetay.durum,
                GorevDetay.son_dnd_zamani,
                GunlukGorev.personel_id,
                Kullanici.ad.label('personel_ad'),
                Kullanici.soyad.label('personel_soyad')
            ).join(
                GunlukGorev, GorevDetay.gorev_id == GunlukGorev.id
            ).join(
                Oda, GorevDetay.oda_id == Oda.id
            ).join(
                Kat, Oda.kat_id == Kat.id
            ).join(
                Otel, GunlukGorev.otel_id == Otel.id
            ).join(
                Kullanici, GunlukGorev.personel_id == Kullanici.id
            ).filter(
                GunlukGorev.gorev_tarihi.between(start_date, end_date),
                GorevDetay.dnd_sayisi > 0,
                GorevDetay.misafir_kayit_id.isnot(None),
                ~Kullanici.kullanici_adi.in_(EXCLUDED_USERNAMES)
            )

            if otel_id:
                gorev_dnd_query = gorev_dnd_query.filter(GunlukGorev.otel_id == otel_id)
            if kat_id:
                gorev_dnd_query = gorev_dnd_query.filter(Kat.id == kat_id)
            if oda_id:
                gorev_dnd_query = gorev_dnd_query.filter(GorevDetay.oda_id == oda_id)
            if personel_id:
                gorev_dnd_query = gorev_dnd_query.filter(GunlukGorev.personel_id == personel_id)

            gorev_dnd_results = gorev_dnd_query.order_by(desc(GunlukGorev.gorev_tarihi)).all()

            # ---- 3. Birleşik DND kayıtları oluştur ----
            data = []
            seen_oda_tarih = set()

            # Önce görev sistemi kayıtları (daha detaylı — personel bilgisi var)
            for r in gorev_dnd_results:
                key = (r.oda_id, r.kayit_tarihi.isoformat() if r.kayit_tarihi else '')
                seen_oda_tarih.add(key)

                # DND sonrası tüketim kaydıyla kapatıldı mı?
                tuketim_kapandi = r.durum == 'completed'

                data.append({
                    'kaynak': 'gorev',
                    'oda_id': r.oda_id,
                    'oda_no': r.oda_no,
                    'kat_adi': r.kat_adi,
                    'kat_id': r.kat_id_col,
                    'otel_id': r.otel_id_col,
                    'otel_adi': r.otel_adi,
                    'tarih': r.kayit_tarihi.isoformat() if r.kayit_tarihi else '',
                    'tarih_label': r.kayit_tarihi.strftime('%d.%m.%Y') if r.kayit_tarihi else '',
                    'dnd_sayisi': r.dnd_sayisi or 0,
                    'durum': 'Tüketimle Kapatıldı' if tuketim_kapandi else (
                        'DND Bekliyor' if r.durum == 'dnd_pending' else r.durum
                    ),
                    'durum_kod': 'completed' if tuketim_kapandi else r.durum,
                    'personel': f"{r.personel_ad} {r.personel_soyad}" if r.personel_ad else '-',
                    'personel_id': r.personel_id,
                    'son_dnd_zamani': r.son_dnd_zamani.strftime('%H:%M') if r.son_dnd_zamani else '-',
                    'tuketim_kapandi': tuketim_kapandi
                })

            # Sonra bağımsız DND kayıtları (görev sistemiyle çakışmayanlar)
            for r in dnd_results:
                key = (r.oda_id, r.kayit_tarihi.isoformat() if r.kayit_tarihi else '')
                if key in seen_oda_tarih:
                    continue

                tuketim_kapandi = r.durum == 'tamamlandi'

                # Personel bilgisi: gorev_detay varsa oradan al
                personel_adi = '-'
                personel_id_val = None
                if r.gorev_detay_id:
                    gd = GorevDetay.query.get(r.gorev_detay_id)
                    if gd and gd.gorev:
                        p = Kullanici.query.get(gd.gorev.personel_id)
                        if p and p.kullanici_adi not in EXCLUDED_USERNAMES:
                            personel_adi = p.ad_soyad
                            personel_id_val = p.id

                data.append({
                    'kaynak': 'bagimsiz',
                    'oda_id': r.oda_id,
                    'oda_no': r.oda_no,
                    'kat_adi': r.kat_adi,
                    'kat_id': r.kat_id_col,
                    'otel_id': r.otel_id_col,
                    'otel_adi': r.otel_adi,
                    'tarih': r.kayit_tarihi.isoformat() if r.kayit_tarihi else '',
                    'tarih_label': r.kayit_tarihi.strftime('%d.%m.%Y') if r.kayit_tarihi else '',
                    'dnd_sayisi': r.dnd_sayisi or 0,
                    'durum': 'Tüketimle Kapatıldı' if tuketim_kapandi else (
                        'Aktif' if r.durum == 'aktif' else r.durum
                    ),
                    'durum_kod': 'completed' if tuketim_kapandi else r.durum,
                    'personel': personel_adi,
                    'personel_id': personel_id_val,
                    'son_dnd_zamani': r.son_dnd_zamani.strftime('%H:%M') if r.son_dnd_zamani else '-',
                    'tuketim_kapandi': tuketim_kapandi
                })

            # Personel filtresi (bağımsız kayıtlar için post-filter)
            if personel_id:
                data = [d for d in data if d.get('personel_id') == personel_id]

            # ---- 4. Özet istatistikler ----
            toplam_dnd = len(data)
            aktif_dnd = sum(1 for d in data if d['durum_kod'] in ('aktif', 'dnd_pending'))
            tuketimle_kapanan = sum(1 for d in data if d['tuketim_kapandi'])
            toplam_dnd_sayisi = sum(d['dnd_sayisi'] for d in data)

            # Otel bazlı dağılım
            otel_dagilim = {}
            for d in data:
                otel = d['otel_adi']
                if otel not in otel_dagilim:
                    otel_dagilim[otel] = {'toplam': 0, 'aktif': 0, 'kapanan': 0}
                otel_dagilim[otel]['toplam'] += 1
                if d['durum_kod'] in ('aktif', 'dnd_pending'):
                    otel_dagilim[otel]['aktif'] += 1
                if d['tuketim_kapandi']:
                    otel_dagilim[otel]['kapanan'] += 1

            # Günlük trend
            gun_trend = {}
            for d in data:
                tarih = d['tarih']
                if tarih not in gun_trend:
                    gun_trend[tarih] = {'toplam': 0, 'kapanan': 0, 'tarih_label': d['tarih_label']}
                gun_trend[tarih]['toplam'] += 1
                if d['tuketim_kapandi']:
                    gun_trend[tarih]['kapanan'] += 1

            trend_data = [v for _, v in sorted(gun_trend.items())]

            summary = {
                'toplam_dnd_kayit': toplam_dnd,
                'aktif_dnd': aktif_dnd,
                'tuketimle_kapanan': tuketimle_kapanan,
                'kapanma_orani': round((tuketimle_kapanan / toplam_dnd * 100) if toplam_dnd > 0 else 0, 1),
                'toplam_dnd_sayisi': toplam_dnd_sayisi,
                'baslangic': start_date.isoformat(),
                'bitis': end_date.isoformat()
            }

            return {
                'success': True,
                'data': data,
                'summary': summary,
                'otel_dagilim': [
                    {'otel': k, **v} for k, v in otel_dagilim.items()
                ],
                'trend_data': trend_data
            }

        except Exception as e:
            logger.error(f"DND raporu hatası: {e}", exc_info=True)
            return {
                'success': False, 'error': str(e),
                'data': [], 'summary': {},
                'otel_dagilim': [], 'trend_data': []
            }

    @staticmethod
    def _gorev_tipi_label(tip):
        labels = {
            'inhouse_kontrol': 'Inhouse Kontrol',
            'arrival_kontrol': 'Arrival Kontrol',
            'departure_kontrol': 'Departure Kontrol',
            'inhouse_yukleme': 'Inhouse Yükleme',
            'arrivals_yukleme': 'Arrivals Yükleme',
            'departures_yukleme': 'Departures Yükleme'
        }
        return labels.get(tip, tip)

    # ==========================================
    # GÜNLÜK TÜKETİM TREND RAPORU
    # ==========================================

    @staticmethod
    def get_daily_consumption_trend(start_date=None, end_date=None, otel_id=None, urun_id=None):
        """Günlük tüketim trendi - Grafik verisi"""
        try:
            if not start_date:
                start_date = get_kktc_now().date() - timedelta(days=30)
            if not end_date:
                end_date = get_kktc_now().date()

            query = db.session.query(
                cast(MinibarIslem.islem_tarihi, Date).label('tarih'),
                func.sum(MinibarIslemDetay.tuketim).label('toplam_tuketim'),
                func.count(func.distinct(MinibarIslem.oda_id)).label('oda_sayisi')
            ).join(
                MinibarIslemDetay, MinibarIslem.id == MinibarIslemDetay.islem_id
            ).join(
                Oda, MinibarIslem.oda_id == Oda.id
            ).join(Kat, Oda.kat_id == Kat.id).filter(
                cast(MinibarIslem.islem_tarihi, Date).between(start_date, end_date),
                MinibarIslemDetay.tuketim > 0,
                ~MinibarIslem.personel_id.in_(get_excluded_user_ids())
            )

            if otel_id:
                query = query.filter(Kat.otel_id == otel_id)
            if urun_id:
                query = query.filter(MinibarIslemDetay.urun_id == urun_id)

            query = query.group_by(
                cast(MinibarIslem.islem_tarihi, Date)
            ).order_by(asc('tarih'))

            results = query.all()
            data = [{
                'tarih': r.tarih.isoformat(),
                'tarih_label': r.tarih.strftime('%d.%m'),
                'toplam_tuketim': r.toplam_tuketim or 0,
                'oda_sayisi': r.oda_sayisi or 0
            } for r in results]

            return {'success': True, 'data': data}

        except Exception as e:
            logger.error(f"Günlük tüketim trend hatası: {e}")
            return {'success': False, 'error': str(e), 'data': []}

    # ==========================================
    # FİLTRE VERİLERİ (Dropdown'lar için)
    # ==========================================

    @staticmethod
    def get_filter_options():
        """Rapor filtreleri için dropdown verileri"""
        try:
            oteller = Otel.query.filter(Otel.aktif == True).order_by(Otel.ad).all()
            urun_gruplari = UrunGrup.query.filter(UrunGrup.aktif == True).order_by(UrunGrup.grup_adi).all()
            urunler = Urun.query.filter(Urun.aktif == True).order_by(Urun.urun_adi).all()

            return {
                'oteller': [{'id': o.id, 'ad': o.ad} for o in oteller],
                'urun_gruplari': [{'id': g.id, 'ad': g.grup_adi} for g in urun_gruplari],
                'urunler': [{'id': u.id, 'ad': u.urun_adi, 'grup_id': u.grup_id} for u in urunler]
            }
        except Exception as e:
            logger.error(f"Filtre verileri hatası: {e}")
            return {'oteller': [], 'urun_gruplari': [], 'urunler': []}

    @staticmethod
    def get_floors_by_hotel(otel_id):
        """Otel'e göre katları getir"""
        try:
            katlar = Kat.query.filter(
                Kat.otel_id == otel_id, Kat.aktif == True
            ).order_by(Kat.kat_no).all()
            return [{'id': k.id, 'ad': k.kat_adi, 'no': k.kat_no} for k in katlar]
        except Exception:
            return []

    @staticmethod
    def get_rooms_by_floor(kat_id):
        """Kat'a göre odaları getir"""
        try:
            odalar = Oda.query.filter(
                Oda.kat_id == kat_id, Oda.aktif == True
            ).order_by(Oda.oda_no).all()
            return [{'id': o.id, 'no': o.oda_no} for o in odalar]
        except Exception:
            return []

    @staticmethod
    def get_personnel_list(otel_id=None, rol=None):
        """Personel listesi"""
        try:
            query = Kullanici.query.filter(
                Kullanici.aktif == True,
                ~Kullanici.kullanici_adi.in_(EXCLUDED_USERNAMES)
            )
            if rol:
                query = query.filter(Kullanici.rol == rol)
            if otel_id:
                query = query.filter(
                    or_(
                        Kullanici.otel_id == otel_id,
                        Kullanici.id.in_(
                            db.session.query(
                                db.literal_column('kullanici_id')
                            ).select_from(
                                db.table('kullanici_otel')
                            ).filter(
                                db.literal_column('otel_id') == otel_id
                            )
                        )
                    )
                )
            query = query.order_by(Kullanici.ad, Kullanici.soyad)
            personeller = query.all()
            return [{'id': p.id, 'ad_soyad': p.ad_soyad, 'rol': p.rol} for p in personeller]
        except Exception:
            return []
