"""
Akıllı Görev Önceliklendirme ve İş Akışı Planlama Servisi

Bu modül, kat sorumlusu görevlerini akıllı bir şekilde önceliklendirir:

ÖNCELİK KRİTERLERİ (Sırasıyla):
1. Departure-Arrival Çakışması (En kritik - zaman kısıtlı)
2. Arrival odaları (giriş saatine göre, 15dk önce hazır olmalı)
3. Departure odaları (çıkıştan max 1 saat sonra kontrol)
4. In-House odaları
5. DND odaları (2 saat sonra tekrar kontrol)

KAT OPTİMİZASYONU:
- 6 katlı otel yapısı dikkate alınır
- Aynı kattaki görevler gruplandırılır
- Verimli rota planlaması yapılır
"""

from datetime import datetime, date, time, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import IntEnum
from collections import defaultdict

from models import (
    db, GunlukGorev, GorevDetay, MisafirKayit, Oda, Kat, Otel
)


class OncelikTipi(IntEnum):
    """Görev öncelik tipleri - düşük değer = yüksek öncelik"""
    DEPARTURE_ARRIVAL_CAKISMA = 1  # En kritik
    ARRIVAL = 2
    DEPARTURE = 3
    INHOUSE = 4
    DND_TEKRAR = 5


@dataclass
class GorevOncelik:
    """Görev öncelik bilgisi"""
    gorev_detay_id: int
    oda_id: int
    oda_no: str
    kat_id: int
    kat_no: int
    kat_adi: str
    oncelik_tipi: OncelikTipi
    oncelik_sirasi: int
    hedef_zaman: Optional[datetime]  # Kontrol edilmesi gereken son zaman
    kalan_sure_dakika: Optional[int]
    aciklama: str
    gorev_tipi: str
    varis_saati: Optional[time]
    cikis_saati: Optional[time]
    dnd_sayisi: int = 0
    cakisma_bilgisi: Optional[Dict] = None  # Departure-Arrival çakışma detayı


class GorevOncelikService:
    """Akıllı görev önceliklendirme servisi"""
    
    # Sabit değerler
    ARRIVAL_HAZIRLIK_DAKIKA = 15  # Arrival'dan 15dk önce hazır olmalı
    DEPARTURE_KONTROL_DAKIKA = 60  # Departure'dan max 60dk sonra kontrol
    DND_TEKRAR_DAKIKA = 120  # DND'den 2 saat sonra tekrar kontrol
    
    @staticmethod
    def get_oncelikli_gorev_plani(personel_id: int, tarih: date, otel_id: int = None) -> Dict:
        """
        Personel için akıllı görev öncelik planı oluşturur.
        
        Args:
            personel_id: Kat sorumlusu ID
            tarih: Görev tarihi
            otel_id: Otel ID (opsiyonel)
            
        Returns:
            Dict: Önceliklendirilmiş görev planı
        """
        try:
            simdi = datetime.now(timezone.utc)
            bugun = simdi.date()
            
            # Tüm görevleri al
            gorevler = GunlukGorev.query.filter(
                GunlukGorev.personel_id == personel_id,
                GunlukGorev.gorev_tarihi == tarih
            ).all()
            
            if not gorevler:
                return {
                    'success': True,
                    'plan': [],
                    'kat_plani': {},
                    'ozet': {
                        'toplam': 0,
                        'kritik': 0,
                        'normal': 0
                    },
                    'baslangic_kat': None,
                    'briefing': 'Bugün için görev bulunmuyor.'
                }
            
            # Departure-Arrival çakışmalarını tespit et
            cakismalar = GorevOncelikService._tespit_cakismalar(tarih, otel_id)
            
            # Tüm görev detaylarını önceliklendir
            oncelikli_gorevler = []
            
            for gorev in gorevler:
                for detay in gorev.detaylar:
                    if detay.durum == 'completed':
                        continue  # Tamamlanmış görevleri atla
                    
                    oncelik = GorevOncelikService._hesapla_oncelik(
                        detay, gorev, cakismalar, simdi, tarih
                    )
                    if oncelik:
                        oncelikli_gorevler.append(oncelik)
            
            # Öncelik sırasına göre sırala
            oncelikli_gorevler.sort(key=lambda x: (
                x.oncelik_tipi.value,
                x.kalan_sure_dakika if x.kalan_sure_dakika is not None else 9999,
                x.kat_no,
                x.oda_no
            ))
            
            # Öncelik sırası numaralarını ata
            for idx, gorev in enumerate(oncelikli_gorevler, start=1):
                gorev.oncelik_sirasi = idx
            
            # Kat bazlı gruplama ve optimizasyon
            kat_plani = GorevOncelikService._kat_bazli_grupla(oncelikli_gorevler)
            
            # Başlangıç katını belirle
            baslangic_kat = GorevOncelikService._belirle_baslangic_kat(oncelikli_gorevler)
            
            # Briefing oluştur
            briefing = GorevOncelikService._olustur_briefing(
                oncelikli_gorevler, kat_plani, baslangic_kat
            )
            
            # Özet istatistikler
            kritik_sayisi = sum(1 for g in oncelikli_gorevler 
                              if g.oncelik_tipi in [OncelikTipi.DEPARTURE_ARRIVAL_CAKISMA, OncelikTipi.ARRIVAL])
            
            return {
                'success': True,
                'plan': [GorevOncelikService._gorev_to_dict(g) for g in oncelikli_gorevler],
                'kat_plani': kat_plani,
                'ozet': {
                    'toplam': len(oncelikli_gorevler),
                    'kritik': kritik_sayisi,
                    'normal': len(oncelikli_gorevler) - kritik_sayisi,
                    'cakisma_sayisi': len(cakismalar)
                },
                'baslangic_kat': baslangic_kat,
                'briefing': briefing,
                'guncelleme_zamani': simdi.isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Öncelik planı oluşturma hatası: {str(e)}'
            }
    
    @staticmethod
    def _tespit_cakismalar(tarih: date, otel_id: int = None) -> Dict[int, Dict]:
        """
        Departure-Arrival çakışmalarını tespit eder.
        Aynı odada bugün çıkış ve giriş varsa çakışma var demektir.
        
        Returns:
            Dict: {oda_id: {departure_saati, arrival_saati, aradaki_sure_dakika}}
        """
        cakismalar = {}
        
        # Bugün departure olan odaları bul
        departure_query = MisafirKayit.query.filter(
            MisafirKayit.kayit_tipi == 'departure',
            MisafirKayit.cikis_tarihi == tarih
        )
        
        if otel_id:
            departure_query = departure_query.join(Oda).join(Kat).filter(Kat.otel_id == otel_id)
        
        departures = {d.oda_id: d for d in departure_query.all()}
        
        # Bugün arrival olan odaları bul
        arrival_query = MisafirKayit.query.filter(
            MisafirKayit.kayit_tipi == 'arrival',
            MisafirKayit.giris_tarihi == tarih
        )
        
        if otel_id:
            arrival_query = arrival_query.join(Oda).join(Kat).filter(Kat.otel_id == otel_id)
        
        arrivals = {a.oda_id: a for a in arrival_query.all()}
        
        # Çakışmaları tespit et
        for oda_id in set(departures.keys()) & set(arrivals.keys()):
            dep = departures[oda_id]
            arr = arrivals[oda_id]
            
            dep_saat = dep.cikis_saati or time(12, 0)  # Varsayılan 12:00
            arr_saat = arr.giris_saati or time(14, 0)  # Varsayılan 14:00
            
            # Aradaki süreyi hesapla
            dep_dakika = dep_saat.hour * 60 + dep_saat.minute
            arr_dakika = arr_saat.hour * 60 + arr_saat.minute
            aradaki_sure = arr_dakika - dep_dakika
            
            cakismalar[oda_id] = {
                'departure_saati': dep_saat,
                'arrival_saati': arr_saat,
                'aradaki_sure_dakika': aradaki_sure,
                'kritik': aradaki_sure < 180  # 3 saatten az ise kritik
            }
        
        return cakismalar
    
    @staticmethod
    def _hesapla_oncelik(
        detay: GorevDetay, 
        gorev: GunlukGorev, 
        cakismalar: Dict,
        simdi: datetime,
        tarih: date
    ) -> Optional[GorevOncelik]:
        """Tek bir görev için öncelik hesaplar"""
        
        oda = detay.oda
        if not oda or not oda.kat:
            return None
        
        kat = oda.kat
        oda_id = detay.oda_id
        
        # Temel bilgiler
        base_info = {
            'gorev_detay_id': detay.id,
            'oda_id': oda_id,
            'oda_no': oda.oda_no,
            'kat_id': kat.id,
            'kat_no': kat.kat_no,
            'kat_adi': kat.kat_adi or f'Kat {kat.kat_no}',
            'gorev_tipi': gorev.gorev_tipi,
            'varis_saati': detay.varis_saati,
            'cikis_saati': detay.cikis_saati,
            'dnd_sayisi': detay.dnd_sayisi,
            'oncelik_sirasi': 0
        }
        
        # 1. Departure-Arrival Çakışması kontrolü
        if oda_id in cakismalar:
            cakisma = cakismalar[oda_id]
            
            # Departure saatinden hemen sonra kontrol edilmeli
            dep_saat = cakisma['departure_saati']
            hedef = datetime.combine(tarih, dep_saat, tzinfo=timezone.utc)
            kalan = int((hedef - simdi).total_seconds() / 60)
            
            return GorevOncelik(
                **base_info,
                oncelik_tipi=OncelikTipi.DEPARTURE_ARRIVAL_CAKISMA,
                hedef_zaman=hedef,
                kalan_sure_dakika=max(0, kalan),
                aciklama=f"⚠️ Çakışma! Çıkış: {dep_saat.strftime('%H:%M')}, Giriş: {cakisma['arrival_saati'].strftime('%H:%M')} ({cakisma['aradaki_sure_dakika']}dk)",
                cakisma_bilgisi=cakisma
            )
        
        # 2. DND Tekrar Kontrolü
        if detay.durum == 'dnd_pending' and detay.son_dnd_zamani:
            tekrar_zamani = detay.son_dnd_zamani + timedelta(minutes=GorevOncelikService.DND_TEKRAR_DAKIKA)
            kalan = int((tekrar_zamani - simdi).total_seconds() / 60)
            
            return GorevOncelik(
                **base_info,
                oncelik_tipi=OncelikTipi.DND_TEKRAR,
                hedef_zaman=tekrar_zamani,
                kalan_sure_dakika=max(0, kalan),
                aciklama=f"🚪 DND ({detay.dnd_sayisi}x) - Tekrar: {tekrar_zamani.strftime('%H:%M')}"
            )
        
        # 3. Arrival Kontrolü
        if gorev.gorev_tipi == 'arrival_kontrol' and detay.varis_saati:
            # Varış saatinden 15dk önce hazır olmalı
            hedef = datetime.combine(tarih, detay.varis_saati, tzinfo=timezone.utc)
            hedef = hedef - timedelta(minutes=GorevOncelikService.ARRIVAL_HAZIRLIK_DAKIKA)
            kalan = int((hedef - simdi).total_seconds() / 60)
            
            return GorevOncelik(
                **base_info,
                oncelik_tipi=OncelikTipi.ARRIVAL,
                hedef_zaman=hedef,
                kalan_sure_dakika=max(0, kalan),
                aciklama=f"✈️ Arrival - Varış: {detay.varis_saati.strftime('%H:%M')} (15dk önce hazır)"
            )
        
        # 4. Departure Kontrolü
        if gorev.gorev_tipi == 'departure_kontrol' and detay.cikis_saati:
            # Çıkıştan max 1 saat sonra kontrol
            hedef = datetime.combine(tarih, detay.cikis_saati, tzinfo=timezone.utc)
            hedef = hedef + timedelta(minutes=GorevOncelikService.DEPARTURE_KONTROL_DAKIKA)
            kalan = int((hedef - simdi).total_seconds() / 60)
            
            return GorevOncelik(
                **base_info,
                oncelik_tipi=OncelikTipi.DEPARTURE,
                hedef_zaman=hedef,
                kalan_sure_dakika=max(0, kalan),
                aciklama=f"🚶 Departure - Çıkış: {detay.cikis_saati.strftime('%H:%M')} (1 saat içinde kontrol)"
            )
        
        # 5. In-House Kontrolü
        if gorev.gorev_tipi == 'inhouse_kontrol':
            return GorevOncelik(
                **base_info,
                oncelik_tipi=OncelikTipi.INHOUSE,
                hedef_zaman=None,
                kalan_sure_dakika=None,
                aciklama="🏠 In-House - Günlük kontrol"
            )
        
        # Varsayılan
        return GorevOncelik(
            **base_info,
            oncelik_tipi=OncelikTipi.INHOUSE,
            hedef_zaman=None,
            kalan_sure_dakika=None,
            aciklama="📋 Kontrol görevi"
        )
    
    @staticmethod
    def _kat_bazli_grupla(gorevler: List[GorevOncelik]) -> Dict:
        """Görevleri kat bazında gruplar ve optimize eder"""
        
        kat_gruplari = defaultdict(list)
        
        for gorev in gorevler:
            kat_gruplari[gorev.kat_no].append(gorev)
        
        # Her kat için özet oluştur
        kat_plani = {}
        for kat_no, kat_gorevleri in sorted(kat_gruplari.items()):
            kritik = sum(1 for g in kat_gorevleri 
                        if g.oncelik_tipi in [OncelikTipi.DEPARTURE_ARRIVAL_CAKISMA, OncelikTipi.ARRIVAL])
            
            kat_plani[kat_no] = {
                'kat_no': kat_no,
                'kat_adi': kat_gorevleri[0].kat_adi if kat_gorevleri else f'Kat {kat_no}',
                'toplam_gorev': len(kat_gorevleri),
                'kritik_gorev': kritik,
                'gorevler': [GorevOncelikService._gorev_to_dict(g) for g in kat_gorevleri],
                'oncelik_sirasi': min(g.oncelik_sirasi for g in kat_gorevleri) if kat_gorevleri else 999
            }
        
        return kat_plani
    
    @staticmethod
    def _belirle_baslangic_kat(gorevler: List[GorevOncelik]) -> Optional[Dict]:
        """En öncelikli göreve göre başlangıç katını belirler"""
        
        if not gorevler:
            return None
        
        # En öncelikli görevin katı
        en_oncelikli = gorevler[0]
        
        return {
            'kat_no': en_oncelikli.kat_no,
            'kat_adi': en_oncelikli.kat_adi,
            'sebep': en_oncelikli.aciklama,
            'ilk_oda': en_oncelikli.oda_no
        }
    
    @staticmethod
    def _olustur_briefing(
        gorevler: List[GorevOncelik], 
        kat_plani: Dict,
        baslangic_kat: Optional[Dict]
    ) -> str:
        """Görev briefing metni oluşturur"""
        
        if not gorevler:
            return "Bugün için bekleyen görev bulunmuyor. ✅"
        
        lines = []
        
        # Özet
        kritik = sum(1 for g in gorevler 
                    if g.oncelik_tipi in [OncelikTipi.DEPARTURE_ARRIVAL_CAKISMA, OncelikTipi.ARRIVAL])
        cakisma = sum(1 for g in gorevler if g.oncelik_tipi == OncelikTipi.DEPARTURE_ARRIVAL_CAKISMA)
        
        lines.append(f"📋 Toplam {len(gorevler)} görev bekliyor.")
        
        if cakisma > 0:
            lines.append(f"⚠️ {cakisma} odada Departure-Arrival çakışması var!")
        
        if kritik > 0:
            lines.append(f"🔴 {kritik} kritik öncelikli görev mevcut.")
        
        # Başlangıç önerisi
        if baslangic_kat:
            lines.append(f"\n🚀 Önerilen başlangıç: {baslangic_kat['kat_adi']}")
            lines.append(f"   İlk oda: {baslangic_kat['ilk_oda']} - {baslangic_kat['sebep']}")
        
        # Kat sıralaması
        if len(kat_plani) > 1:
            sirali_katlar = sorted(kat_plani.values(), key=lambda x: x['oncelik_sirasi'])
            kat_sirasi = " → ".join([f"Kat {k['kat_no']}" for k in sirali_katlar])
            lines.append(f"\n📍 Önerilen kat sırası: {kat_sirasi}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _gorev_to_dict(gorev: GorevOncelik) -> Dict:
        """GorevOncelik nesnesini dict'e çevirir"""
        return {
            'gorev_detay_id': gorev.gorev_detay_id,
            'oda_id': gorev.oda_id,
            'oda_no': gorev.oda_no,
            'kat_id': gorev.kat_id,
            'kat_no': gorev.kat_no,
            'kat_adi': gorev.kat_adi,
            'oncelik_tipi': gorev.oncelik_tipi.name,
            'oncelik_tipi_deger': gorev.oncelik_tipi.value,
            'oncelik_sirasi': gorev.oncelik_sirasi,
            'hedef_zaman': gorev.hedef_zaman.isoformat() if gorev.hedef_zaman else None,
            'kalan_sure_dakika': gorev.kalan_sure_dakika,
            'aciklama': gorev.aciklama,
            'gorev_tipi': gorev.gorev_tipi,
            'varis_saati': gorev.varis_saati.isoformat() if gorev.varis_saati else None,
            'cikis_saati': gorev.cikis_saati.isoformat() if gorev.cikis_saati else None,
            'dnd_sayisi': gorev.dnd_sayisi,
            'cakisma_bilgisi': GorevOncelikService._serialize_cakisma(gorev.cakisma_bilgisi)
        }
    
    @staticmethod
    def _serialize_cakisma(cakisma: Optional[Dict]) -> Optional[Dict]:
        """Çakışma bilgisini JSON serializable hale getirir"""
        if not cakisma:
            return None
        return {
            'departure_saati': cakisma['departure_saati'].strftime('%H:%M') if cakisma.get('departure_saati') else None,
            'arrival_saati': cakisma['arrival_saati'].strftime('%H:%M') if cakisma.get('arrival_saati') else None,
            'aradaki_sure_dakika': cakisma.get('aradaki_sure_dakika'),
            'kritik': cakisma.get('kritik')
        }
    
    @staticmethod
    def get_kat_oncelik_plani(personel_id: int, kat_id: int, tarih: date) -> Dict:
        """
        Belirli bir kat için öncelik planı döndürür.
        Kat doluluk detay sayfasında kullanılır.
        """
        try:
            # Önce genel planı al
            from models import Kat
            kat = Kat.query.get(kat_id)
            if not kat:
                return {'success': False, 'error': 'Kat bulunamadı'}
            
            plan = GorevOncelikService.get_oncelikli_gorev_plani(
                personel_id, tarih, kat.otel_id
            )
            
            if not plan['success']:
                return plan
            
            # Sadece bu kata ait görevleri filtrele
            kat_gorevleri = [g for g in plan['plan'] if g['kat_id'] == kat_id]
            
            return {
                'success': True,
                'kat_id': kat_id,
                'kat_no': kat.kat_no,
                'kat_adi': kat.kat_adi,
                'gorevler': kat_gorevleri,
                'toplam': len(kat_gorevleri),
                'kritik': sum(1 for g in kat_gorevleri 
                            if g['oncelik_tipi'] in ['DEPARTURE_ARRIVAL_CAKISMA', 'ARRIVAL'])
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
