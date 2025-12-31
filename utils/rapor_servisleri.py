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
                    # Otel logosunu al
                    otel_obj = Otel.query.get(row.otel_id)
                    otel_logo = otel_obj.logo if otel_obj and otel_obj.logo else None
                    
                    oteller[row.otel_id] = {
                        'otel_id': row.otel_id,
                        'otel_ad': row.otel_ad,
                        'otel_logo': otel_logo,
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


class KatSorumlusuGunSonuRaporServisi:
    """Kat Sorumlusu Gün Sonu Raporu - Profesyonel format"""
    
    @staticmethod
    def get_gun_sonu_raporu(
        otel_id: int,
        personel_ids: list = None,
        tarih: date = None,
        baslangic_tarihi: date = None,
        bitis_tarihi: date = None
    ) -> dict:
        """
        Kat sorumlusu gün sonu raporu - Tarih aralığı destekli
        
        Args:
            otel_id: Otel ID (zorunlu)
            personel_ids: Kat sorumlusu ID listesi (çoklu seçim)
            tarih: Tek tarih için (geriye uyumluluk)
            baslangic_tarihi: Tarih aralığı başlangıcı
            bitis_tarihi: Tarih aralığı bitişi
            
        Returns:
            dict: Gün sonu rapor verisi
        """
        try:
            # Tarih aralığı belirleme
            if baslangic_tarihi and bitis_tarihi:
                # Tarih aralığı modu
                tarih_baslangic = datetime.combine(baslangic_tarihi, datetime.min.time())
                tarih_bitis = datetime.combine(bitis_tarihi, datetime.max.time())
                rapor_tarihi_str = f"{baslangic_tarihi.strftime('%d.%m.%Y')} - {bitis_tarihi.strftime('%d.%m.%Y')}"
            else:
                # Tek tarih modu (geriye uyumluluk)
                if not tarih:
                    tarih = date.today()
                tarih_baslangic = datetime.combine(tarih, datetime.min.time())
                tarih_bitis = datetime.combine(tarih, datetime.max.time())
                rapor_tarihi_str = tarih.strftime('%d.%m.%Y')
            
            otel = Otel.query.get(otel_id)
            if not otel:
                return {'success': False, 'message': 'Otel bulunamadı'}
            
            # Kat sorumlularını getir
            kat_sorumlusu_query = Kullanici.query.filter(
                Kullanici.rol == 'kat_sorumlusu',
                Kullanici.aktif.is_(True),
                Kullanici.otel_id == otel_id
            )
            
            if personel_ids:
                kat_sorumlusu_query = kat_sorumlusu_query.filter(Kullanici.id.in_(personel_ids))
            
            kat_sorumlulari = kat_sorumlusu_query.order_by(Kullanici.ad, Kullanici.soyad).all()
            
            if not kat_sorumlulari:
                return {
                    'success': True,
                    'otel_adi': otel.ad,
                    'rapor_tarihi': rapor_tarihi_str,
                    'olusturma_zamani': get_kktc_now().strftime('%d.%m.%Y %H:%M'),
                    'personeller': [],
                    'genel_toplam': []
                }
            
            personel_raporlari = []
            # Genel toplam için tüm ürünleri takip et
            genel_urun_toplam = {}
            
            for personel in kat_sorumlulari:
                # Bu personelin o günkü minibar işlemlerini çek
                islemler = MinibarIslem.query.filter(
                    MinibarIslem.personel_id == personel.id,
                    MinibarIslem.islem_tarihi >= tarih_baslangic,
                    MinibarIslem.islem_tarihi <= tarih_bitis
                ).order_by(MinibarIslem.islem_tarihi).all()
                
                # Ürün bazlı özet - oda detayları ile
                urun_ozeti = {}
                
                for islem in islemler:
                    oda = Oda.query.get(islem.oda_id)
                    oda_no = oda.oda_no if oda else 'Bilinmiyor'
                    saat = islem.islem_tarihi.strftime('%H:%M')
                    
                    for detay in islem.detaylar:
                        # Sadece eklenen (minibara tamamlanan) ürünleri al
                        if detay.eklenen_miktar and detay.eklenen_miktar > 0:
                            urun = Urun.query.get(detay.urun_id)
                            urun_adi = urun.urun_adi if urun else 'Bilinmiyor'
                            urun_id = detay.urun_id
                            
                            if urun_id not in urun_ozeti:
                                urun_ozeti[urun_id] = {
                                    'urun_adi': urun_adi,
                                    'toplam_eklenen': 0,
                                    'odalar': []
                                }
                            
                            urun_ozeti[urun_id]['toplam_eklenen'] += detay.eklenen_miktar
                            urun_ozeti[urun_id]['odalar'].append({
                                'oda_no': oda_no,
                                'miktar': detay.eklenen_miktar,
                                'saat': saat
                            })
                            
                            # Genel toplama ekle
                            if urun_id not in genel_urun_toplam:
                                genel_urun_toplam[urun_id] = {
                                    'urun_adi': urun_adi,
                                    'toplam_eklenen': 0
                                }
                            genel_urun_toplam[urun_id]['toplam_eklenen'] += detay.eklenen_miktar
                
                # Ürün özetini listeye çevir ve sırala
                urun_listesi = list(urun_ozeti.values())
                urun_listesi.sort(key=lambda x: x['toplam_eklenen'], reverse=True)
                
                personel_toplam = sum(u['toplam_eklenen'] for u in urun_listesi)
                
                if urun_listesi:  # Sadece işlem yapan personelleri ekle
                    personel_raporlari.append({
                        'personel_id': personel.id,
                        'personel_adi': f"{personel.ad} {personel.soyad}",
                        'toplam_eklenen': personel_toplam,
                        'urun_sayisi': len(urun_listesi),
                        'urunler': urun_listesi
                    })
            
            # Genel toplamı listeye çevir ve sırala
            genel_toplam_listesi = list(genel_urun_toplam.values())
            genel_toplam_listesi.sort(key=lambda x: x['toplam_eklenen'], reverse=True)
            
            return {
                'success': True,
                'otel_id': otel_id,
                'otel_adi': otel.ad,
                'otel_logo': otel.logo if otel.logo else None,
                'rapor_tarihi': rapor_tarihi_str,
                'olusturma_zamani': get_kktc_now().strftime('%d.%m.%Y %H:%M'),
                'personeller': personel_raporlari,
                'genel_toplam': genel_toplam_listesi,
                'genel_toplam_adet': sum(u['toplam_eklenen'] for u in genel_toplam_listesi)
            }
            
        except Exception as e:
            logger.error(f"Gün sonu raporu hatası: {e}")
            return {'success': False, 'message': str(e)}


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
        Kat sorumlusu kullanım raporu - MinibarIslem tablosundan
        Gruplu tablo formatında - tarih+personel bazlı
        
        Args:
            otel_id: Otel ID (opsiyonel)
            personel_id: Personel ID (opsiyonel)
            baslangic_tarihi: Başlangıç tarihi
            bitis_tarihi: Bitiş tarihi
            
        Returns:
            dict: Rapor verisi - tarih+personel bazlı gruplu liste
        """
        try:
            # Varsayılan tarih aralığı: Son 30 gün
            if not baslangic_tarihi:
                baslangic_tarihi = date.today() - timedelta(days=30)
            if not bitis_tarihi:
                bitis_tarihi = date.today()
            
            # MinibarIslem tablosundan kat sorumlusu işlemlerini çek
            query = db.session.query(
                MinibarIslem.id.label('islem_id'),
                MinibarIslem.islem_tarihi,
                MinibarIslem.islem_tipi,
                Oda.oda_no,
                Kullanici.ad.label('personel_ad'),
                Kullanici.soyad.label('personel_soyad'),
                Otel.ad.label('otel_ad'),
                Urun.urun_adi,
                Urun.birim,
                MinibarIslemDetay.tuketim,
                MinibarIslemDetay.eklenen_miktar
            ).join(
                MinibarIslemDetay, MinibarIslem.id == MinibarIslemDetay.islem_id
            ).join(
                Oda, MinibarIslem.oda_id == Oda.id
            ).join(
                Kat, Oda.kat_id == Kat.id
            ).join(
                Otel, Kat.otel_id == Otel.id
            ).join(
                Kullanici, MinibarIslem.personel_id == Kullanici.id
            ).join(
                Urun, MinibarIslemDetay.urun_id == Urun.id
            ).filter(
                MinibarIslem.islem_tarihi >= baslangic_tarihi,
                MinibarIslem.islem_tarihi <= bitis_tarihi + timedelta(days=1),
                Kullanici.rol == 'kat_sorumlusu'
            )
            
            # Sadece tüketim veya ekleme olan kayıtları al
            query = query.filter(
                or_(
                    MinibarIslemDetay.tuketim > 0,
                    MinibarIslemDetay.eklenen_miktar > 0
                )
            )
            
            if otel_id:
                query = query.filter(Kat.otel_id == otel_id)
            if personel_id:
                query = query.filter(MinibarIslem.personel_id == personel_id)
            
            # Tarih azalan sırada
            query = query.order_by(desc(MinibarIslem.islem_tarihi), Oda.oda_no)
            
            sonuclar = query.all()
            
            # Tarih + Personel + Oda bazlı gruplama
            gruplar = {}
            toplam_tuketim = 0
            toplam_ekleme = 0
            benzersiz_personeller = set()
            
            for row in sonuclar:
                personel_adi = f"{row.personel_ad} {row.personel_soyad}"
                tarih_str = row.islem_tarihi.strftime('%d.%m.%Y %H:%M')
                benzersiz_personeller.add(personel_adi)
                
                # Grup anahtarı: tarih + personel + oda
                grup_key = f"{tarih_str}_{personel_adi}_{row.oda_no}"
                
                if grup_key not in gruplar:
                    gruplar[grup_key] = {
                        'tarih': tarih_str,
                        'personel': personel_adi,
                        'oda_no': row.oda_no,
                        'otel': row.otel_ad,
                        'urunler': []
                    }
                
                # Tüketim veya ekleme
                tuketim = row.tuketim or 0
                ekleme = row.eklenen_miktar or 0
                
                if tuketim > 0:
                    gruplar[grup_key]['urunler'].append({
                        'urun_adi': row.urun_adi,
                        'miktar': tuketim,
                        'birim': row.birim,
                        'islem_class': 'tuketim'
                    })
                    toplam_tuketim += tuketim
                
                if ekleme > 0:
                    gruplar[grup_key]['urunler'].append({
                        'urun_adi': row.urun_adi,
                        'miktar': ekleme,
                        'birim': row.birim,
                        'islem_class': 'ekleme'
                    })
                    toplam_ekleme += ekleme
            
            # Grupları listeye çevir ve tarih azalan sırala
            grup_listesi = list(gruplar.values())
            grup_listesi.sort(key=lambda x: x['tarih'], reverse=True)
            
            return {
                'success': True,
                'rapor_tarihi': get_kktc_now().strftime('%d.%m.%Y %H:%M'),
                'baslangic': baslangic_tarihi.strftime('%d.%m.%Y'),
                'bitis': bitis_tarihi.strftime('%d.%m.%Y'),
                'toplam_personel': len(benzersiz_personeller),
                'toplam_grup': len(grup_listesi),
                'toplam_tuketim': toplam_tuketim,
                'toplam_ekleme': toplam_ekleme,
                'gruplar': grup_listesi
            }
            
        except Exception as e:
            logger.error(f"Personel kullanım raporu hatası: {e}")
            return {'success': False, 'message': str(e), 'gruplar': []}


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
        Oda bazlı minibar tüketim raporu - Gruplu tablo formatında
        
        Args:
            otel_id: Otel ID
            baslangic_tarihi: Başlangıç tarihi
            bitis_tarihi: Bitiş tarihi
            kat_id: Kat ID (opsiyonel)
            
        Returns:
            dict: Rapor verisi - tarih+oda bazlı gruplu liste
        """
        try:
            if not baslangic_tarihi:
                baslangic_tarihi = date.today() - timedelta(days=7)
            if not bitis_tarihi:
                bitis_tarihi = date.today()
            
            otel = Otel.query.get(otel_id)
            if not otel:
                return {'success': False, 'message': 'Otel bulunamadı'}
            
            # Her işlem detayını çek
            query = db.session.query(
                MinibarIslem.id.label('islem_id'),
                MinibarIslem.islem_tarihi,
                Oda.oda_no,
                Urun.urun_adi,
                MinibarIslemDetay.tuketim,
                Kullanici.ad.label('personel_ad'),
                Kullanici.soyad.label('personel_soyad')
            ).join(
                MinibarIslemDetay, MinibarIslem.id == MinibarIslemDetay.islem_id
            ).join(
                Oda, MinibarIslem.oda_id == Oda.id
            ).join(
                Kat, Oda.kat_id == Kat.id
            ).join(
                Urun, MinibarIslemDetay.urun_id == Urun.id
            ).outerjoin(
                Kullanici, MinibarIslem.personel_id == Kullanici.id
            ).filter(
                Kat.otel_id == otel_id,
                MinibarIslem.islem_tarihi >= baslangic_tarihi,
                MinibarIslem.islem_tarihi <= bitis_tarihi + timedelta(days=1),
                MinibarIslemDetay.tuketim > 0
            )
            
            if kat_id:
                query = query.filter(Kat.id == kat_id)
            
            # Tarih azalan sırada
            query = query.order_by(desc(MinibarIslem.islem_tarihi), Oda.oda_no, Urun.urun_adi)
            
            sonuclar = query.all()
            
            # Tarih + Oda bazlı gruplama
            gruplar = {}
            genel_toplam_tuketim = 0
            benzersiz_odalar = set()
            
            for row in sonuclar:
                kontrol_eden = f"{row.personel_ad} {row.personel_soyad}" if row.personel_ad else '-'
                tarih_str = row.islem_tarihi.strftime('%d.%m.%Y %H:%M')
                
                # Grup anahtarı: tarih + oda + kontrol eden
                grup_key = f"{tarih_str}_{row.oda_no}_{kontrol_eden}"
                
                if grup_key not in gruplar:
                    gruplar[grup_key] = {
                        'tarih': tarih_str,
                        'oda_no': row.oda_no,
                        'kontrol_eden': kontrol_eden,
                        'urunler': []
                    }
                
                gruplar[grup_key]['urunler'].append({
                    'urun_adi': row.urun_adi,
                    'tuketim': row.tuketim
                })
                
                genel_toplam_tuketim += row.tuketim
                benzersiz_odalar.add(row.oda_no)
            
            # Grupları listeye çevir ve tarih azalan sırala
            grup_listesi = list(gruplar.values())
            grup_listesi.sort(key=lambda x: x['tarih'], reverse=True)
            
            return {
                'success': True,
                'rapor_tarihi': get_kktc_now().strftime('%d.%m.%Y %H:%M'),
                'otel_id': otel_id,
                'otel_ad': otel.ad,
                'baslangic': baslangic_tarihi.strftime('%d.%m.%Y'),
                'bitis': bitis_tarihi.strftime('%d.%m.%Y'),
                'toplam_oda': len(benzersiz_odalar),
                'toplam_grup': len(grup_listesi),
                'genel_toplam_tuketim': genel_toplam_tuketim,
                'gruplar': grup_listesi
            }
            
        except Exception as e:
            logger.error(f"Oda bazlı tüketim raporu hatası: {e}")
            return {'success': False, 'message': str(e), 'gruplar': []}


class GunlukGorevRaporServisi:
    """Günlük görev tamamlama raporları"""
    
    @staticmethod
    def get_gunluk_gorev_raporu(
        otel_id: int = None,
        baslangic_tarihi: date = None,
        bitis_tarihi: date = None,
        personel_id: int = None,
        personel_ids: list = None
    ) -> dict:
        """
        Günlük görev tamamlama raporu
        
        Args:
            otel_id: Otel ID (opsiyonel)
            baslangic_tarihi: Başlangıç tarihi
            bitis_tarihi: Bitiş tarihi
            personel_id: Personel ID (opsiyonel, tekil)
            personel_ids: Personel ID listesi (opsiyonel, çoklu)
            
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
            
            # Çoklu personel ID desteği
            if personel_ids:
                query = query.filter(GunlukGorev.personel_id.in_(personel_ids))
            elif personel_id:
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
