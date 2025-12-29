"""
Raporlama Servisleri
Tarih: 2025-12-29
Açıklama: Otel bazlı zimmet, kat sorumlusu kullanım, oda bazlı tüketim,
          günlük görev ve karşılaştırmalı raporlar için servis fonksiyonları
"""

from models import (
    db, OtelZimmetStok, PersonelZimmetKullanim, Otel, Kullanici, Urun,
    MinibarIslem, MinibarIslemDetay, Oda, Kat, GunlukGorev, GorevDetay,
    PersonelZimmet, PersonelZimmetDetay
)
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, or_, desc, case
from decimal import Decimal
import pytz
import logging

logger = logging.getLogger(__name__)

KKTC_TZ = pytz.timezone('Europe/Nicosia')

def get_kktc_now():
    return datetime.now(KKTC_TZ)


class OtelZimmetRaporServisi:
    """Otel bazlı zimmet stok raporları"""
    
    @staticmethod
    def get_otel_zimmet_stok_raporu(otel_id: int = None) -> dict:
        """
        Otel bazlı zimmet stok raporu
        
        Args:
            otel_id: Otel ID (None ise tüm oteller)
            
        Returns:
            dict: Rapor verisi
        """
        try:
            query = db.session.query(
                Otel.id.label('otel_id'),
                Otel.ad.label('otel_ad'),
                Urun.id.label('urun_id'),
                Urun.urun_adi,
                Urun.birim,
                OtelZimmetStok.toplam_miktar,
                OtelZimmetStok.kullanilan_miktar,
                OtelZimmetStok.kalan_miktar,
                OtelZimmetStok.kritik_stok_seviyesi,
                OtelZimmetStok.son_guncelleme
            ).join(
                OtelZimmetStok, Otel.id == OtelZimmetStok.otel_id
            ).join(
                Urun, OtelZimmetStok.urun_id == Urun.id
            ).filter(Otel.aktif == True)
            
            if otel_id:
                query = query.filter(Otel.id == otel_id)
            
            query = query.order_by(Otel.ad, Urun.urun_adi)
            sonuclar = query.all()
            
            # Otel bazlı gruplama
            oteller = {}
            for row in sonuclar:
                if row.otel_id not in oteller:
                    oteller[row.otel_id] = {
                        'otel_id': row.otel_id,
                        'otel_ad': row.otel_ad,
                        'toplam_urun_cesidi': 0,
                        'toplam_stok': 0,
                        'toplam_kullanilan': 0,
                        'toplam_kalan': 0,
                        'kritik_urun_sayisi': 0,
                        'urunler': []
                    }
                
                # Stok durumu hesapla
                if row.kalan_miktar == 0:
                    stok_durumu = 'stokout'
                elif row.kalan_miktar <= row.kritik_stok_seviyesi:
                    stok_durumu = 'kritik'
                elif row.kalan_miktar <= row.kritik_stok_seviyesi * 1.5:
                    stok_durumu = 'dikkat'
                else:
                    stok_durumu = 'normal'
                
                oteller[row.otel_id]['urunler'].append({
                    'urun_id': row.urun_id,
                    'urun_adi': row.urun_adi,
                    'birim': row.birim,
                    'toplam_miktar': row.toplam_miktar,
                    'kullanilan_miktar': row.kullanilan_miktar,
                    'kalan_miktar': row.kalan_miktar,
                    'kritik_seviye': row.kritik_stok_seviyesi,
                    'stok_durumu': stok_durumu,
                    'kullanim_yuzdesi': round((row.kullanilan_miktar / row.toplam_miktar * 100), 1) if row.toplam_miktar > 0 else 0,
                    'son_guncelleme': row.son_guncelleme.strftime('%d.%m.%Y %H:%M') if row.son_guncelleme else None
                })
                
                oteller[row.otel_id]['toplam_urun_cesidi'] += 1
                oteller[row.otel_id]['toplam_stok'] += row.toplam_miktar
                oteller[row.otel_id]['toplam_kullanilan'] += row.kullanilan_miktar
                oteller[row.otel_id]['toplam_kalan'] += row.kalan_miktar
                if stok_durumu in ('kritik', 'stokout'):
                    oteller[row.otel_id]['kritik_urun_sayisi'] += 1
            
            return {
                'success': True,
                'rapor_tarihi': get_kktc_now().strftime('%d.%m.%Y %H:%M'),
                'toplam_otel': len(oteller),
                'oteller': list(oteller.values())
            }
            
        except Exception as e:
            logger.error(f"Otel zimmet stok raporu hatası: {e}")
            return {'success': False, 'message': str(e), 'oteller': []}


class KatSorumlusuKullanimRaporServisi:
    """Kat sorumlusu zimmet kullanım raporları"""
    
    @staticmethod
    def get_personel_kullanim_raporu(
        otel_id: int = None,
        personel_id: int = None,
        baslangic_tarihi: date = None,
        bitis_tarihi: date = None
    ) -> dict:
        """
        Kat sorumlusu zimmet kullanım raporu
        
        Args:
            otel_id: Otel ID (opsiyonel)
            personel_id: Personel ID (opsiyonel)
            baslangic_tarihi: Başlangıç tarihi
            bitis_tarihi: Bitiş tarihi
            
        Returns:
            dict: Rapor verisi
        """
        try:
            # Varsayılan tarih aralığı: Son 30 gün
            if not baslangic_tarihi:
                baslangic_tarihi = date.today() - timedelta(days=30)
            if not bitis_tarihi:
                bitis_tarihi = date.today()
            
            query = db.session.query(
                Kullanici.id.label('personel_id'),
                Kullanici.ad,
                Kullanici.soyad,
                Otel.id.label('otel_id'),
                Otel.ad.label('otel_ad'),
                Urun.id.label('urun_id'),
                Urun.urun_adi,
                Urun.birim,
                func.sum(
                    case(
                        (PersonelZimmetKullanim.islem_tipi != 'iade', PersonelZimmetKullanim.kullanilan_miktar),
                        else_=0
                    )
                ).label('toplam_kullanim'),
                func.sum(
                    case(
                        (PersonelZimmetKullanim.islem_tipi == 'iade', PersonelZimmetKullanim.kullanilan_miktar),
                        else_=0
                    )
                ).label('toplam_iade'),
                func.count(PersonelZimmetKullanim.id).label('islem_sayisi')
            ).join(
                OtelZimmetStok, PersonelZimmetKullanim.otel_zimmet_stok_id == OtelZimmetStok.id
            ).join(
                Otel, OtelZimmetStok.otel_id == Otel.id
            ).join(
                Kullanici, PersonelZimmetKullanim.personel_id == Kullanici.id
            ).join(
                Urun, PersonelZimmetKullanim.urun_id == Urun.id
            ).filter(
                PersonelZimmetKullanim.islem_tarihi >= baslangic_tarihi,
                PersonelZimmetKullanim.islem_tarihi <= bitis_tarihi + timedelta(days=1)
            )
            
            if otel_id:
                query = query.filter(OtelZimmetStok.otel_id == otel_id)
            if personel_id:
                query = query.filter(PersonelZimmetKullanim.personel_id == personel_id)
            
            query = query.group_by(
                Kullanici.id, Kullanici.ad, Kullanici.soyad,
                Otel.id, Otel.ad,
                Urun.id, Urun.urun_adi, Urun.birim
            ).order_by(Otel.ad, Kullanici.ad, Urun.urun_adi)
            
            sonuclar = query.all()
            
            # Personel bazlı gruplama
            personeller = {}
            for row in sonuclar:
                key = f"{row.otel_id}_{row.personel_id}"
                if key not in personeller:
                    personeller[key] = {
                        'personel_id': row.personel_id,
                        'ad_soyad': f"{row.ad} {row.soyad}",
                        'otel_id': row.otel_id,
                        'otel_ad': row.otel_ad,
                        'toplam_kullanim': 0,
                        'toplam_iade': 0,
                        'net_kullanim': 0,
                        'islem_sayisi': 0,
                        'urunler': []
                    }
                
                net = (row.toplam_kullanim or 0) - (row.toplam_iade or 0)
                personeller[key]['urunler'].append({
                    'urun_id': row.urun_id,
                    'urun_adi': row.urun_adi,
                    'birim': row.birim,
                    'kullanim': row.toplam_kullanim or 0,
                    'iade': row.toplam_iade or 0,
                    'net': net,
                    'islem_sayisi': row.islem_sayisi
                })
                
                personeller[key]['toplam_kullanim'] += row.toplam_kullanim or 0
                personeller[key]['toplam_iade'] += row.toplam_iade or 0
                personeller[key]['net_kullanim'] += net
                personeller[key]['islem_sayisi'] += row.islem_sayisi
            
            return {
                'success': True,
                'rapor_tarihi': get_kktc_now().strftime('%d.%m.%Y %H:%M'),
                'baslangic': baslangic_tarihi.strftime('%d.%m.%Y'),
                'bitis': bitis_tarihi.strftime('%d.%m.%Y'),
                'toplam_personel': len(personeller),
                'personeller': list(personeller.values())
            }
            
        except Exception as e:
            logger.error(f"Personel kullanım raporu hatası: {e}")
            return {'success': False, 'message': str(e), 'personeller': []}


class OdaBazliTuketimRaporServisi:
    """Oda bazlı minibar tüketim raporları"""
    
    @staticmethod
    def get_oda_bazli_tuketim_raporu(
        otel_id: int,
        baslangic_tarihi: date = None,
        bitis_tarihi: date = None,
        kat_id: int = None
    ) -> dict:
        """
        Oda bazlı minibar tüketim raporu
        
        Args:
            otel_id: Otel ID
            baslangic_tarihi: Başlangıç tarihi
            bitis_tarihi: Bitiş tarihi
            kat_id: Kat ID (opsiyonel)
            
        Returns:
            dict: Rapor verisi
        """
        try:
            if not baslangic_tarihi:
                baslangic_tarihi = date.today() - timedelta(days=7)
            if not bitis_tarihi:
                bitis_tarihi = date.today()
            
            otel = Otel.query.get(otel_id)
            if not otel:
                return {'success': False, 'message': 'Otel bulunamadı'}
            
            query = db.session.query(
                Oda.id.label('oda_id'),
                Oda.oda_no,
                Kat.kat_adi,
                Urun.id.label('urun_id'),
                Urun.urun_adi,
                Urun.birim,
                Urun.satis_fiyati,
                func.sum(MinibarIslemDetay.tuketim).label('toplam_tuketim'),
                func.count(MinibarIslem.id).label('islem_sayisi')
            ).join(
                MinibarIslem, Oda.id == MinibarIslem.oda_id
            ).join(
                MinibarIslemDetay, MinibarIslem.id == MinibarIslemDetay.islem_id
            ).join(
                Kat, Oda.kat_id == Kat.id
            ).join(
                Urun, MinibarIslemDetay.urun_id == Urun.id
            ).filter(
                Kat.otel_id == otel_id,
                MinibarIslem.islem_tarihi >= baslangic_tarihi,
                MinibarIslem.islem_tarihi <= bitis_tarihi + timedelta(days=1),
                MinibarIslemDetay.tuketim > 0
            )
            
            if kat_id:
                query = query.filter(Kat.id == kat_id)
            
            query = query.group_by(
                Oda.id, Oda.oda_no, Kat.kat_adi,
                Urun.id, Urun.urun_adi, Urun.birim, Urun.satis_fiyati
            ).order_by(Kat.kat_adi, Oda.oda_no, desc(func.sum(MinibarIslemDetay.tuketim)))
            
            sonuclar = query.all()
            
            # Oda bazlı gruplama
            odalar = {}
            genel_toplam_tuketim = 0
            genel_toplam_tutar = Decimal('0')
            
            for row in sonuclar:
                if row.oda_id not in odalar:
                    odalar[row.oda_id] = {
                        'oda_id': row.oda_id,
                        'oda_no': row.oda_no,
                        'kat': row.kat_adi,
                        'toplam_tuketim': 0,
                        'toplam_tutar': Decimal('0'),
                        'urun_cesidi': 0,
                        'urunler': []
                    }
                
                tutar = Decimal(str(row.toplam_tuketim)) * (row.satis_fiyati or Decimal('0'))
                
                odalar[row.oda_id]['urunler'].append({
                    'urun_id': row.urun_id,
                    'urun_adi': row.urun_adi,
                    'birim': row.birim,
                    'tuketim': row.toplam_tuketim,
                    'birim_fiyat': float(row.satis_fiyati) if row.satis_fiyati else 0,
                    'tutar': float(tutar),
                    'islem_sayisi': row.islem_sayisi
                })
                
                odalar[row.oda_id]['toplam_tuketim'] += row.toplam_tuketim
                odalar[row.oda_id]['toplam_tutar'] += tutar
                odalar[row.oda_id]['urun_cesidi'] += 1
                genel_toplam_tuketim += row.toplam_tuketim
                genel_toplam_tutar += tutar
            
            # Toplam tutarları float'a çevir
            for oda in odalar.values():
                oda['toplam_tutar'] = float(oda['toplam_tutar'])
            
            # En çok tüketen odaları sırala
            odalar_list = sorted(odalar.values(), key=lambda x: x['toplam_tuketim'], reverse=True)
            
            return {
                'success': True,
                'rapor_tarihi': get_kktc_now().strftime('%d.%m.%Y %H:%M'),
                'otel_id': otel_id,
                'otel_ad': otel.ad,
                'baslangic': baslangic_tarihi.strftime('%d.%m.%Y'),
                'bitis': bitis_tarihi.strftime('%d.%m.%Y'),
                'toplam_oda': len(odalar),
                'genel_toplam_tuketim': genel_toplam_tuketim,
                'genel_toplam_tutar': float(genel_toplam_tutar),
                'odalar': odalar_list
            }
            
        except Exception as e:
            logger.error(f"Oda bazlı tüketim raporu hatası: {e}")
            return {'success': False, 'message': str(e), 'odalar': []}


class GunlukGorevRaporServisi:
    """Günlük görev tamamlama raporları"""
    
    @staticmethod
    def get_gunluk_gorev_raporu(
        otel_id: int = None,
        baslangic_tarihi: date = None,
        bitis_tarihi: date = None,
        personel_id: int = None
    ) -> dict:
        """
        Günlük görev tamamlama raporu
        
        Args:
            otel_id: Otel ID (opsiyonel)
            baslangic_tarihi: Başlangıç tarihi
            bitis_tarihi: Bitiş tarihi
            personel_id: Personel ID (opsiyonel)
            
        Returns:
            dict: Rapor verisi
        """
        try:
            if not baslangic_tarihi:
                baslangic_tarihi = date.today() - timedelta(days=7)
            if not bitis_tarihi:
                bitis_tarihi = date.today()
            
            # Günlük görev özeti
            query = db.session.query(
                GunlukGorev.gorev_tarihi,
                Otel.id.label('otel_id'),
                Otel.ad.label('otel_ad'),
                Kullanici.id.label('personel_id'),
                Kullanici.ad.label('personel_ad'),
                Kullanici.soyad.label('personel_soyad'),
                func.count(GorevDetay.id).label('toplam_gorev'),
                func.sum(case((GorevDetay.durum == 'tamamlandi', 1), else_=0)).label('tamamlanan'),
                func.sum(case((GorevDetay.durum == 'beklemede', 1), else_=0)).label('bekleyen'),
                func.sum(case((GorevDetay.durum == 'dnd', 1), else_=0)).label('dnd'),
                func.sum(case((GorevDetay.durum == 'iptal', 1), else_=0)).label('iptal'),
                func.sum(case((GorevDetay.durum == 'incomplete', 1), else_=0)).label('tamamlanmadi')
            ).join(
                GorevDetay, GunlukGorev.id == GorevDetay.gunluk_gorev_id
            ).join(
                Kullanici, GunlukGorev.personel_id == Kullanici.id
            ).join(
                Otel, Kullanici.otel_id == Otel.id
            ).filter(
                GunlukGorev.gorev_tarihi >= baslangic_tarihi,
                GunlukGorev.gorev_tarihi <= bitis_tarihi
            )
            
            if otel_id:
                query = query.filter(Kullanici.otel_id == otel_id)
            if personel_id:
                query = query.filter(GunlukGorev.personel_id == personel_id)
            
            query = query.group_by(
                GunlukGorev.gorev_tarihi,
                Otel.id, Otel.ad,
                Kullanici.id, Kullanici.ad, Kullanici.soyad
            ).order_by(desc(GunlukGorev.gorev_tarihi), Otel.ad, Kullanici.ad)
            
            sonuclar = query.all()
            
            # Tarih bazlı gruplama
            gunler = {}
            for row in sonuclar:
                tarih_str = row.gorev_tarihi.strftime('%Y-%m-%d')
                if tarih_str not in gunler:
                    gunler[tarih_str] = {
                        'tarih': row.gorev_tarihi.strftime('%d.%m.%Y'),
                        'tarih_iso': tarih_str,
                        'toplam_gorev': 0,
                        'tamamlanan': 0,
                        'bekleyen': 0,
                        'dnd': 0,
                        'iptal': 0,
                        'tamamlanmadi': 0,
                        'tamamlanma_orani': 0,
                        'personeller': []
                    }
                
                tamamlanma_orani = round((row.tamamlanan / row.toplam_gorev * 100), 1) if row.toplam_gorev > 0 else 0
                
                gunler[tarih_str]['personeller'].append({
                    'personel_id': row.personel_id,
                    'ad_soyad': f"{row.personel_ad} {row.personel_soyad}",
                    'otel_id': row.otel_id,
                    'otel_ad': row.otel_ad,
                    'toplam': row.toplam_gorev,
                    'tamamlanan': row.tamamlanan,
                    'bekleyen': row.bekleyen,
                    'dnd': row.dnd,
                    'iptal': row.iptal,
                    'tamamlanmadi': row.tamamlanmadi,
                    'tamamlanma_orani': tamamlanma_orani
                })
                
                gunler[tarih_str]['toplam_gorev'] += row.toplam_gorev
                gunler[tarih_str]['tamamlanan'] += row.tamamlanan
                gunler[tarih_str]['bekleyen'] += row.bekleyen
                gunler[tarih_str]['dnd'] += row.dnd
                gunler[tarih_str]['iptal'] += row.iptal
                gunler[tarih_str]['tamamlanmadi'] += row.tamamlanmadi
            
            # Tamamlanma oranlarını hesapla
            for gun in gunler.values():
                gun['tamamlanma_orani'] = round((gun['tamamlanan'] / gun['toplam_gorev'] * 100), 1) if gun['toplam_gorev'] > 0 else 0
            
            # Tarihe göre sırala (en yeni önce)
            gunler_list = sorted(gunler.values(), key=lambda x: x['tarih_iso'], reverse=True)
            
            # Genel özet
            toplam_gorev = sum(g['toplam_gorev'] for g in gunler_list)
            toplam_tamamlanan = sum(g['tamamlanan'] for g in gunler_list)
            
            return {
                'success': True,
                'rapor_tarihi': get_kktc_now().strftime('%d.%m.%Y %H:%M'),
                'baslangic': baslangic_tarihi.strftime('%d.%m.%Y'),
                'bitis': bitis_tarihi.strftime('%d.%m.%Y'),
                'toplam_gun': len(gunler),
                'genel_toplam_gorev': toplam_gorev,
                'genel_tamamlanan': toplam_tamamlanan,
                'genel_tamamlanma_orani': round((toplam_tamamlanan / toplam_gorev * 100), 1) if toplam_gorev > 0 else 0,
                'gunler': gunler_list
            }
            
        except Exception as e:
            logger.error(f"Günlük görev raporu hatası: {e}")
            return {'success': False, 'message': str(e), 'gunler': []}


class OtelKarsilastirmaRaporServisi:
    """Otel karşılaştırma raporları"""
    
    @staticmethod
    def get_otel_karsilastirma_raporu(
        baslangic_tarihi: date = None,
        bitis_tarihi: date = None
    ) -> dict:
        """
        Oteller arası karşılaştırma raporu
        
        Args:
            baslangic_tarihi: Başlangıç tarihi
            bitis_tarihi: Bitiş tarihi
            
        Returns:
            dict: Rapor verisi
        """
        try:
            if not baslangic_tarihi:
                baslangic_tarihi = date.today() - timedelta(days=30)
            if not bitis_tarihi:
                bitis_tarihi = date.today()
            
            oteller = Otel.query.filter_by(aktif=True).all()
            karsilastirma = []
            
            for otel in oteller:
                # Zimmet stok durumu
                zimmet_query = db.session.query(
                    func.sum(OtelZimmetStok.toplam_miktar).label('toplam'),
                    func.sum(OtelZimmetStok.kullanilan_miktar).label('kullanilan'),
                    func.sum(OtelZimmetStok.kalan_miktar).label('kalan'),
                    func.count(OtelZimmetStok.id).label('urun_cesidi')
                ).filter(OtelZimmetStok.otel_id == otel.id).first()
                
                # Minibar tüketim
                tuketim_query = db.session.query(
                    func.sum(MinibarIslemDetay.tuketim).label('toplam_tuketim'),
                    func.count(func.distinct(MinibarIslem.id)).label('islem_sayisi'),
                    func.count(func.distinct(MinibarIslem.oda_id)).label('oda_sayisi')
                ).join(
                    MinibarIslem, MinibarIslemDetay.islem_id == MinibarIslem.id
                ).join(
                    Oda, MinibarIslem.oda_id == Oda.id
                ).join(
                    Kat, Oda.kat_id == Kat.id
                ).filter(
                    Kat.otel_id == otel.id,
                    MinibarIslem.islem_tarihi >= baslangic_tarihi,
                    MinibarIslem.islem_tarihi <= bitis_tarihi + timedelta(days=1)
                ).first()
                
                # Görev tamamlama
                gorev_query = db.session.query(
                    func.count(GorevDetay.id).label('toplam'),
                    func.sum(case((GorevDetay.durum == 'tamamlandi', 1), else_=0)).label('tamamlanan')
                ).join(
                    GunlukGorev, GorevDetay.gunluk_gorev_id == GunlukGorev.id
                ).join(
                    Kullanici, GunlukGorev.personel_id == Kullanici.id
                ).filter(
                    Kullanici.otel_id == otel.id,
                    GunlukGorev.gorev_tarihi >= baslangic_tarihi,
                    GunlukGorev.gorev_tarihi <= bitis_tarihi
                ).first()
                
                # Kat sorumlusu sayısı
                ks_sayisi = Kullanici.query.filter(
                    Kullanici.otel_id == otel.id,
                    Kullanici.rol == 'kat_sorumlusu',
                    Kullanici.aktif == True
                ).count()
                
                # Oda sayısı
                oda_sayisi = Oda.query.join(Kat).filter(
                    Kat.otel_id == otel.id,
                    Oda.aktif == True
                ).count()
                
                gorev_tamamlanma = 0
                if gorev_query and gorev_query.toplam and gorev_query.toplam > 0:
                    gorev_tamamlanma = round((gorev_query.tamamlanan or 0) / gorev_query.toplam * 100, 1)
                
                karsilastirma.append({
                    'otel_id': otel.id,
                    'otel_ad': otel.ad,
                    'oda_sayisi': oda_sayisi,
                    'kat_sorumlusu_sayisi': ks_sayisi,
                    'zimmet': {
                        'toplam_stok': zimmet_query.toplam or 0 if zimmet_query else 0,
                        'kullanilan': zimmet_query.kullanilan or 0 if zimmet_query else 0,
                        'kalan': zimmet_query.kalan or 0 if zimmet_query else 0,
                        'urun_cesidi': zimmet_query.urun_cesidi or 0 if zimmet_query else 0
                    },
                    'tuketim': {
                        'toplam': tuketim_query.toplam_tuketim or 0 if tuketim_query else 0,
                        'islem_sayisi': tuketim_query.islem_sayisi or 0 if tuketim_query else 0,
                        'aktif_oda': tuketim_query.oda_sayisi or 0 if tuketim_query else 0
                    },
                    'gorev': {
                        'toplam': gorev_query.toplam or 0 if gorev_query else 0,
                        'tamamlanan': gorev_query.tamamlanan or 0 if gorev_query else 0,
                        'tamamlanma_orani': gorev_tamamlanma
                    }
                })
            
            # Performansa göre sırala (görev tamamlanma oranı)
            karsilastirma.sort(key=lambda x: x['gorev']['tamamlanma_orani'], reverse=True)
            
            return {
                'success': True,
                'rapor_tarihi': get_kktc_now().strftime('%d.%m.%Y %H:%M'),
                'baslangic': baslangic_tarihi.strftime('%d.%m.%Y'),
                'bitis': bitis_tarihi.strftime('%d.%m.%Y'),
                'toplam_otel': len(karsilastirma),
                'oteller': karsilastirma
            }
            
        except Exception as e:
            logger.error(f"Otel karşılaştırma raporu hatası: {e}")
            return {'success': False, 'message': str(e), 'oteller': []}
