"""
Stok Yönetim Servisi

Stok durumu sorgulama, kritik stok takibi, sayım ve raporlama işlemleri.
Fiyatlandırma/karlılık fonksiyonları bu modülde yer almaz.
"""

from models import db, UrunStok, Urun, StokHareket
from models.base import get_kktc_now
from sqlalchemy import func
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class StokYonetimServisi:
    """Stok yönetimi servis katmanı"""

    @staticmethod
    def stok_durumu_getir(otel_id, urun_id=None):
        """
        Otel bazlı stok durumunu getir.
        
        Args:
            otel_id: Otel ID
            urun_id: Opsiyonel ürün ID (verilirse tek ürün döner)
        
        Returns:
            list[dict]: Stok bilgileri listesi
        """
        query = UrunStok.query.filter_by(otel_id=otel_id)

        if urun_id:
            query = query.filter_by(urun_id=urun_id)

        stoklar = query.all()

        sonuc = []
        for stok in stoklar:
            urun = stok.urun
            sonuc.append({
                'urun_id': stok.urun_id,
                'urun_adi': urun.urun_adi if urun else 'Bilinmeyen',
                'birim': urun.birim if urun else '',
                'grup_adi': urun.grup.grup_adi if urun and urun.grup else None,
                'mevcut_stok': stok.mevcut_stok,
                'minimum_stok': stok.minimum_stok,
                'maksimum_stok': stok.maksimum_stok,
                'kritik_stok_seviyesi': stok.kritik_stok_seviyesi,
                'durum': stok.stok_durumu(),
                'son_giris_tarihi': stok.son_giris_tarihi.strftime('%d.%m.%Y %H:%M') if stok.son_giris_tarihi else None,
                'son_cikis_tarihi': stok.son_cikis_tarihi.strftime('%d.%m.%Y %H:%M') if stok.son_cikis_tarihi else None,
                'son_guncelleme': stok.son_guncelleme_tarihi.strftime('%d.%m.%Y %H:%M') if stok.son_guncelleme_tarihi else None,
            })

        return sonuc

    @staticmethod
    def kritik_stoklar_getir(otel_id):
        """
        Kritik seviyedeki stokları getir.
        
        Args:
            otel_id: Otel ID
        
        Returns:
            list[dict]: Kritik stok bilgileri
        """
        stoklar = UrunStok.query.filter(
            UrunStok.otel_id == otel_id,
            UrunStok.mevcut_stok <= UrunStok.kritik_stok_seviyesi
        ).all()

        sonuc = []
        for stok in stoklar:
            urun = stok.urun
            sonuc.append({
                'urun_id': stok.urun_id,
                'urun_adi': urun.urun_adi if urun else 'Bilinmeyen',
                'birim': urun.birim if urun else '',
                'grup_adi': urun.grup.grup_adi if urun and urun.grup else None,
                'mevcut_stok': stok.mevcut_stok,
                'kritik_stok_seviyesi': stok.kritik_stok_seviyesi,
                'minimum_stok': stok.minimum_stok,
                'durum': stok.stok_durumu(),
                'eksik_miktar': max(0, stok.minimum_stok - stok.mevcut_stok),
            })

        return sonuc

    @staticmethod
    def stok_sayim_yap(otel_id, sayim_verileri, kullanici_id):
        """
        Stok sayımı yap ve farkları kaydet.
        
        Args:
            otel_id: Otel ID
            sayim_verileri: [{'urun_id': int, 'sayilan_miktar': int}, ...]
            kullanici_id: İşlemi yapan kullanıcı ID
        
        Returns:
            dict: Sayım sonuçları
        """
        farkli_urunler = []
        toplam_urun = len(sayim_verileri)

        for veri in sayim_verileri:
            urun_id = veri['urun_id']
            sayilan = veri['sayilan_miktar']

            stok = UrunStok.query.filter_by(otel_id=otel_id, urun_id=urun_id).first()

            if not stok:
                # Stok kaydı yoksa oluştur
                stok = UrunStok(
                    otel_id=otel_id,
                    urun_id=urun_id,
                    mevcut_stok=0
                )
                db.session.add(stok)
                db.session.flush()

            eski_miktar = stok.mevcut_stok
            fark = sayilan - eski_miktar

            stok.stok_guncelle(sayilan, 'sayim', kullanici_id)

            if fark != 0:
                # Fark varsa stok hareketi oluştur
                hareket_tipi = 'giris' if fark > 0 else 'cikis'
                hareket = StokHareket(
                    urun_id=urun_id,
                    hareket_tipi=hareket_tipi,
                    miktar=abs(fark),
                    aciklama=f'Stok sayımı düzeltmesi (Eski: {eski_miktar}, Yeni: {sayilan})',
                    islem_yapan_id=kullanici_id
                )
                db.session.add(hareket)

                urun = db.session.get(Urun, urun_id)
                farkli_urunler.append({
                    'urun_id': urun_id,
                    'urun_adi': urun.urun_adi if urun else 'Bilinmeyen',
                    'eski_miktar': eski_miktar,
                    'yeni_miktar': sayilan,
                    'fark': fark
                })

        db.session.commit()

        return {
            'toplam_urun': toplam_urun,
            'farkli_urun_sayisi': len(farkli_urunler),
            'farkli_urunler': farkli_urunler,
            'sayim_tarihi': get_kktc_now().strftime('%d.%m.%Y %H:%M')
        }

    @staticmethod
    def stok_devir_raporu(otel_id, baslangic, bitis):
        """
        Stok devir hızı raporu.
        
        Args:
            otel_id: Otel ID
            baslangic: Başlangıç tarihi (date)
            bitis: Bitiş tarihi (date)
        
        Returns:
            list[dict]: Ürün bazlı devir raporu
        """
        from datetime import datetime

        baslangic_dt = datetime.combine(baslangic, datetime.min.time())
        bitis_dt = datetime.combine(bitis, datetime.max.time())
        gun_sayisi = max((bitis - baslangic).days, 1)

        stoklar = UrunStok.query.filter_by(otel_id=otel_id).all()

        rapor = []
        for stok in stoklar:
            # Dönem içi çıkış miktarı
            cikis_toplam = db.session.query(
                func.coalesce(func.sum(StokHareket.miktar), 0)
            ).filter(
                StokHareket.urun_id == stok.urun_id,
                StokHareket.hareket_tipi == 'cikis',
                StokHareket.islem_tarihi >= baslangic_dt,
                StokHareket.islem_tarihi <= bitis_dt
            ).scalar()

            # Dönem içi giriş miktarı
            giris_toplam = db.session.query(
                func.coalesce(func.sum(StokHareket.miktar), 0)
            ).filter(
                StokHareket.urun_id == stok.urun_id,
                StokHareket.hareket_tipi == 'giris',
                StokHareket.islem_tarihi >= baslangic_dt,
                StokHareket.islem_tarihi <= bitis_dt
            ).scalar()

            # Devir hızı: çıkış / ortalama stok
            ortalama_stok = stok.mevcut_stok if stok.mevcut_stok > 0 else 1
            devir_hizi = round(float(cikis_toplam) / ortalama_stok, 2) if ortalama_stok else 0

            # Günlük ortalama tüketim
            gunluk_tuketim = round(float(cikis_toplam) / gun_sayisi, 2)

            # Tahmini kaç gün yeter
            kalan_gun = int(stok.mevcut_stok / gunluk_tuketim) if gunluk_tuketim > 0 else None

            urun = stok.urun
            rapor.append({
                'urun_id': stok.urun_id,
                'urun_adi': urun.urun_adi if urun else 'Bilinmeyen',
                'birim': urun.birim if urun else '',
                'mevcut_stok': stok.mevcut_stok,
                'donem_giris': int(giris_toplam),
                'donem_cikis': int(cikis_toplam),
                'devir_hizi': devir_hizi,
                'gunluk_tuketim': gunluk_tuketim,
                'tahmini_kalan_gun': kalan_gun,
            })

        return rapor

    @staticmethod
    def stok_deger_raporu(otel_id):
        """
        Stok değer raporu (miktar bazlı, fiyat bilgisi opsiyonel).
        
        Args:
            otel_id: Otel ID
        
        Returns:
            dict: Stok değer özeti
        """
        stoklar = UrunStok.query.filter_by(otel_id=otel_id).all()

        toplam_cesit = len(stoklar)
        toplam_miktar = 0
        kritik_sayisi = 0
        normal_sayisi = 0
        fazla_sayisi = 0
        urunler = []

        for stok in stoklar:
            toplam_miktar += stok.mevcut_stok
            durum = stok.stok_durumu()

            if durum in ('kritik', 'dusuk'):
                kritik_sayisi += 1
            elif durum == 'fazla':
                fazla_sayisi += 1
            else:
                normal_sayisi += 1

            urun = stok.urun
            urunler.append({
                'urun_id': stok.urun_id,
                'urun_adi': urun.urun_adi if urun else 'Bilinmeyen',
                'birim': urun.birim if urun else '',
                'mevcut_stok': stok.mevcut_stok,
                'durum': durum,
            })

        return {
            'otel_id': otel_id,
            'toplam_cesit': toplam_cesit,
            'toplam_miktar': toplam_miktar,
            'kritik_sayisi': kritik_sayisi,
            'normal_sayisi': normal_sayisi,
            'fazla_sayisi': fazla_sayisi,
            'urunler': urunler,
            'rapor_tarihi': get_kktc_now().strftime('%d.%m.%Y %H:%M')
        }

    @staticmethod
    def stok_guncelle(otel_id, urun_id, miktar, islem_tipi, kullanici_id, aciklama=None):
        """
        Manuel stok güncelleme.
        
        Args:
            otel_id: Otel ID
            urun_id: Ürün ID
            miktar: Miktar (pozitif)
            islem_tipi: 'giris', 'cikis', 'devir', 'fire'
            kullanici_id: İşlemi yapan kullanıcı ID
            aciklama: Opsiyonel açıklama
        
        Returns:
            dict: Güncelleme sonucu
        """
        if miktar <= 0:
            raise ValueError('Miktar sıfırdan büyük olmalıdır')

        stok = UrunStok.query.filter_by(otel_id=otel_id, urun_id=urun_id).first()

        if not stok:
            stok = UrunStok(
                otel_id=otel_id,
                urun_id=urun_id,
                mevcut_stok=0
            )
            db.session.add(stok)
            db.session.flush()

        eski_miktar = stok.mevcut_stok

        if islem_tipi in ('cikis', 'fire') and stok.mevcut_stok < miktar:
            raise ValueError(f'Yetersiz stok. Mevcut: {stok.mevcut_stok}, Talep: {miktar}')

        stok.stok_guncelle(miktar, islem_tipi, kullanici_id)

        hareket = StokHareket(
            urun_id=urun_id,
            hareket_tipi=islem_tipi,
            miktar=miktar,
            aciklama=aciklama or f'Manuel stok güncelleme ({islem_tipi})',
            islem_yapan_id=kullanici_id
        )
        db.session.add(hareket)
        db.session.commit()

        return {
            'success': True,
            'urun_id': urun_id,
            'otel_id': otel_id,
            'islem_tipi': islem_tipi,
            'eski_miktar': eski_miktar,
            'yeni_miktar': stok.mevcut_stok,
            'degisim': miktar
        }
