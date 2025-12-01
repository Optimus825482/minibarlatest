"""
Görevlendirme Sistemi - GorevService
Günlük minibar kontrol görevlerinin oluşturulması ve yönetimi
"""

from datetime import datetime, date, time, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload, subqueryload

from models import (
    db, GunlukGorev, GorevDetay, DNDKontrol, GorevDurumLog,
    MisafirKayit, Kullanici, Oda, Otel
)

# Görev durumları sabitleri
COMPLETED_STATUS = 'completed'
PENDING_STATUSES = ('pending', 'dnd_pending', 'in_progress')


class GorevService:
    """Günlük görev yönetim servisi"""
    
    @staticmethod
    def create_daily_tasks(otel_id: int, tarih: date) -> Dict:
        """
        Günlük görevleri oluşturur.
        In House, Arrivals ve Departures görevlerini ayrı ayrı oluşturur.
        
        Args:
            otel_id: Otel ID
            tarih: Görev tarihi
            
        Returns:
            Dict: Oluşturulan görev sayıları
        """
        try:
            result = {
                'inhouse_gorev_sayisi': 0,
                'arrival_gorev_sayisi': 0,
                'departure_gorev_sayisi': 0,
                'toplam_oda_sayisi': 0,
                'hatalar': []
            }
            
            # Otelin kat sorumlularını bul
            kat_sorumluları = Kullanici.query.filter(
                Kullanici.otel_id == otel_id,
                Kullanici.rol == 'kat_sorumlusu',
                Kullanici.aktif == True
            ).all()
            
            if not kat_sorumluları:
                result['hatalar'].append('Bu otel için aktif kat sorumlusu bulunamadı')
                return result
            
            # Her kat sorumlusu için görev oluştur
            for personel in kat_sorumluları:
                # In House görevleri
                inhouse_result = GorevService.create_inhouse_tasks(otel_id, personel.id, tarih)
                result['inhouse_gorev_sayisi'] += inhouse_result.get('oda_sayisi', 0)
                
                # Arrivals görevleri
                arrival_result = GorevService.create_arrival_tasks(otel_id, personel.id, tarih)
                result['arrival_gorev_sayisi'] += arrival_result.get('oda_sayisi', 0)
                
                # Departures görevleri
                departure_result = GorevService.create_departure_tasks(otel_id, personel.id, tarih)
                result['departure_gorev_sayisi'] += departure_result.get('oda_sayisi', 0)
            
            result['toplam_oda_sayisi'] = (
                result['inhouse_gorev_sayisi'] + 
                result['arrival_gorev_sayisi'] + 
                result['departure_gorev_sayisi']
            )
            
            db.session.commit()
            return result
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Günlük görev oluşturma hatası: {str(e)}")
    
    @staticmethod
    def create_inhouse_tasks(otel_id: int, personel_id: int, tarih: date) -> Dict:
        """
        In House kontrol görevlerini oluşturur.
        Kalmaya devam eden misafirler için görev oluşturur.
        
        Args:
            otel_id: Otel ID
            personel_id: Personel ID
            tarih: Görev tarihi
            
        Returns:
            Dict: Oluşturulan görev bilgileri
        """
        try:
            result = {'oda_sayisi': 0, 'gorev_id': None}
            
            # Mevcut In House görev var mı kontrol et
            mevcut_gorev = GunlukGorev.query.filter(
                GunlukGorev.otel_id == otel_id,
                GunlukGorev.personel_id == personel_id,
                GunlukGorev.gorev_tarihi == tarih,
                GunlukGorev.gorev_tipi == 'inhouse_kontrol'
            ).first()
            
            if mevcut_gorev:
                result['gorev_id'] = mevcut_gorev.id
                result['oda_sayisi'] = len(mevcut_gorev.detaylar)
                return result
            
            # In House misafir kayıtlarını bul (bugün içinde olan ve in_house tipinde)
            inhouse_kayitlar = MisafirKayit.query.join(Oda).join(Oda.kat).filter(
                MisafirKayit.kayit_tipi == 'in_house',
                MisafirKayit.giris_tarihi <= tarih,
                MisafirKayit.cikis_tarihi >= tarih,
                Oda.kat.has(otel_id=otel_id)
            ).all()
            
            if not inhouse_kayitlar:
                return result
            
            # Ana görev kaydı oluştur
            gorev = GunlukGorev(
                otel_id=otel_id,
                personel_id=personel_id,
                gorev_tarihi=tarih,
                gorev_tipi='inhouse_kontrol',
                durum='pending'
            )
            db.session.add(gorev)
            db.session.flush()  # ID almak için
            
            result['gorev_id'] = gorev.id
            
            # Her oda için detay oluştur
            for kayit in inhouse_kayitlar:
                detay = GorevDetay(
                    gorev_id=gorev.id,
                    oda_id=kayit.oda_id,
                    misafir_kayit_id=kayit.id,
                    durum='pending'
                )
                db.session.add(detay)
                result['oda_sayisi'] += 1
            
            return result
            
        except Exception as e:
            raise Exception(f"In House görev oluşturma hatası: {str(e)}")
    
    @staticmethod
    def create_arrival_tasks(otel_id: int, personel_id: int, tarih: date) -> Dict:
        """
        Arrivals kontrol görevlerini oluşturur.
        O gün giriş yapacak misafirler için görev oluşturur.
        
        Args:
            otel_id: Otel ID
            personel_id: Personel ID
            tarih: Görev tarihi
            
        Returns:
            Dict: Oluşturulan görev bilgileri
        """
        try:
            result = {'oda_sayisi': 0, 'gorev_id': None}
            
            # Mevcut Arrivals görev var mı kontrol et
            mevcut_gorev = GunlukGorev.query.filter(
                GunlukGorev.otel_id == otel_id,
                GunlukGorev.personel_id == personel_id,
                GunlukGorev.gorev_tarihi == tarih,
                GunlukGorev.gorev_tipi == 'arrival_kontrol'
            ).first()
            
            if mevcut_gorev:
                result['gorev_id'] = mevcut_gorev.id
                result['oda_sayisi'] = len(mevcut_gorev.detaylar)
                return result
            
            # Arrivals misafir kayıtlarını bul (bugün giriş yapacaklar)
            arrival_kayitlar = MisafirKayit.query.join(Oda).join(Oda.kat).filter(
                MisafirKayit.kayit_tipi == 'arrival',
                MisafirKayit.giris_tarihi == tarih,
                Oda.kat.has(otel_id=otel_id)
            ).all()
            
            if not arrival_kayitlar:
                return result
            
            # Ana görev kaydı oluştur
            gorev = GunlukGorev(
                otel_id=otel_id,
                personel_id=personel_id,
                gorev_tarihi=tarih,
                gorev_tipi='arrival_kontrol',
                durum='pending'
            )
            db.session.add(gorev)
            db.session.flush()
            
            result['gorev_id'] = gorev.id
            
            # Her oda için detay oluştur (varış saati ile birlikte)
            for kayit in arrival_kayitlar:
                detay = GorevDetay(
                    gorev_id=gorev.id,
                    oda_id=kayit.oda_id,
                    misafir_kayit_id=kayit.id,
                    durum='pending',
                    varis_saati=kayit.giris_saati  # Arrivals için varış saati
                )
                db.session.add(detay)
                result['oda_sayisi'] += 1
            
            return result
            
        except Exception as e:
            raise Exception(f"Arrivals görev oluşturma hatası: {str(e)}")
    
    @staticmethod
    def create_departure_tasks(otel_id: int, personel_id: int, tarih: date) -> Dict:
        """
        Departures kontrol görevlerini oluşturur.
        O gün çıkış yapacak misafirler için görev oluşturur.
        Öncelik sırası: Erken çıkış saati olan odalar önce kontrol edilir.
        
        Args:
            otel_id: Otel ID
            personel_id: Personel ID
            tarih: Görev tarihi
            
        Returns:
            Dict: Oluşturulan görev bilgileri
        """
        try:
            result = {'oda_sayisi': 0, 'gorev_id': None}
            
            # Mevcut Departures görev var mı kontrol et
            mevcut_gorev = GunlukGorev.query.filter(
                GunlukGorev.otel_id == otel_id,
                GunlukGorev.personel_id == personel_id,
                GunlukGorev.gorev_tarihi == tarih,
                GunlukGorev.gorev_tipi == 'departure_kontrol'
            ).first()
            
            if mevcut_gorev:
                result['gorev_id'] = mevcut_gorev.id
                result['oda_sayisi'] = len(mevcut_gorev.detaylar)
                return result
            
            # Departures misafir kayıtlarını bul (bugün çıkış yapacaklar)
            # Çıkış saatine göre sıralı
            departure_kayitlar = MisafirKayit.query.join(Oda).join(Oda.kat).filter(
                MisafirKayit.kayit_tipi == 'departure',
                MisafirKayit.cikis_tarihi == tarih,
                Oda.kat.has(otel_id=otel_id)
            ).order_by(MisafirKayit.cikis_saati.asc().nullslast()).all()
            
            if not departure_kayitlar:
                return result
            
            # Ana görev kaydı oluştur
            gorev = GunlukGorev(
                otel_id=otel_id,
                personel_id=personel_id,
                gorev_tarihi=tarih,
                gorev_tipi='departure_kontrol',
                durum='pending'
            )
            db.session.add(gorev)
            db.session.flush()
            
            result['gorev_id'] = gorev.id
            
            # Her oda için detay oluştur (çıkış saati ve öncelik sırası ile)
            for sira, kayit in enumerate(departure_kayitlar, start=1):
                detay = GorevDetay(
                    gorev_id=gorev.id,
                    oda_id=kayit.oda_id,
                    misafir_kayit_id=kayit.id,
                    durum='pending',
                    cikis_saati=kayit.cikis_saati,  # Departures için çıkış saati
                    oncelik_sirasi=sira  # Erken çıkış = düşük sıra = yüksek öncelik
                )
                db.session.add(detay)
                result['oda_sayisi'] += 1
            
            return result
            
        except Exception as e:
            raise Exception(f"Departures görev oluşturma hatası: {str(e)}")
    
    @staticmethod
    def complete_task(gorev_detay_id: int, personel_id: int, notlar: str = None) -> bool:
        """
        Görevi tamamlar.
        
        Args:
            gorev_detay_id: Görev detay ID
            personel_id: İşlemi yapan personel ID
            notlar: Opsiyonel notlar
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            detay = GorevDetay.query.get(gorev_detay_id)
            if not detay:
                raise ValueError("Görev detayı bulunamadı")
            
            if detay.durum == 'completed':
                raise ValueError("Görev zaten tamamlanmış")
            
            onceki_durum = detay.durum
            
            # Durumu güncelle
            detay.durum = 'completed'
            detay.kontrol_zamani = datetime.now(timezone.utc)
            if notlar:
                detay.notlar = notlar
            
            # Log kaydı oluştur
            log = GorevDurumLog(
                gorev_detay_id=gorev_detay_id,
                onceki_durum=onceki_durum,
                yeni_durum='completed',
                degistiren_id=personel_id,
                aciklama=notlar or 'Görev tamamlandı'
            )
            db.session.add(log)
            
            # Ana görevin durumunu kontrol et
            GorevService._update_main_task_status(detay.gorev_id)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Görev tamamlama hatası: {str(e)}")
    
    @staticmethod
    def mark_dnd(gorev_detay_id: int, personel_id: int, notlar: str = None) -> Dict:
        """
        Odayı DND olarak işaretler.
        DND odaları tamamlanmış sayılmaz, sadece kontrol kaydı tutulur.
        Minimum 3 kontrol gerekli ama sınırsız kontrol yapılabilir.
        
        Args:
            gorev_detay_id: Görev detay ID
            personel_id: İşlemi yapan personel ID
            notlar: Opsiyonel notlar
            
        Returns:
            Dict: DND durumu bilgileri
        """
        try:
            detay = GorevDetay.query.get(gorev_detay_id)
            if not detay:
                raise ValueError("Görev detayı bulunamadı")
            
            if detay.durum == 'completed':
                raise ValueError("Tamamlanmış görev DND olarak işaretlenemez")
            
            onceki_durum = detay.durum
            
            # DND sayısını artır
            detay.dnd_sayisi += 1
            detay.son_dnd_zamani = datetime.now(timezone.utc)
            
            # DND kontrol kaydı oluştur
            dnd_kontrol = DNDKontrol(
                gorev_detay_id=gorev_detay_id,
                kontrol_eden_id=personel_id,
                notlar=notlar
            )
            db.session.add(dnd_kontrol)
            
            # DND her zaman dnd_pending kalır - tamamlanmış sayılmaz
            detay.durum = 'dnd_pending'
            
            # Minimum kontrol durumu
            min_kontrol_tamamlandi = detay.dnd_sayisi >= 3
            
            result = {
                'dnd_sayisi': detay.dnd_sayisi,
                'min_kontrol_tamamlandi': min_kontrol_tamamlandi,
                'durum': 'dnd_pending'
            }
            
            aciklama = f'DND olarak işaretlendi ({detay.dnd_sayisi}. kontrol). Not: {notlar}' if notlar else f'DND olarak işaretlendi ({detay.dnd_sayisi}. kontrol)'
            
            # Log kaydı oluştur
            log = GorevDurumLog(
                gorev_detay_id=gorev_detay_id,
                onceki_durum=onceki_durum,
                yeni_durum=detay.durum,
                degistiren_id=personel_id,
                aciklama=aciklama
            )
            db.session.add(log)
            
            # Ana görevin durumunu kontrol et
            GorevService._update_main_task_status(detay.gorev_id)
            
            db.session.commit()
            return result
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"DND işaretleme hatası: {str(e)}")
    
    @staticmethod
    def calculate_countdown(varis_saati: time) -> Dict:
        """
        Varış saatine kalan süreyi hesaplar.
        
        Args:
            varis_saati: Misafir varış saati
            
        Returns:
            Dict: Geri sayım bilgileri (saat, dakika, saniye, uyari)
        """
        if not varis_saati:
            return {'saat': 0, 'dakika': 0, 'saniye': 0, 'uyari': False, 'gecmis': True}
        
        now = datetime.now(timezone.utc)
        today = now.date()
        
        # Varış zamanını bugünün tarihiyle birleştir
        varis_datetime = datetime.combine(today, varis_saati, tzinfo=timezone.utc)
        
        # Farkı hesapla
        fark = varis_datetime - now
        
        if fark.total_seconds() <= 0:
            return {'saat': 0, 'dakika': 0, 'saniye': 0, 'uyari': True, 'gecmis': True}
        
        toplam_saniye = int(fark.total_seconds())
        saat = toplam_saniye // 3600
        dakika = (toplam_saniye % 3600) // 60
        saniye = toplam_saniye % 60
        
        # 15 dakika altı uyarı
        uyari = toplam_saniye < 900  # 15 * 60 = 900 saniye
        
        return {
            'saat': saat,
            'dakika': dakika,
            'saniye': saniye,
            'uyari': uyari,
            'gecmis': False,
            'toplam_saniye': toplam_saniye
        }
    
    @staticmethod
    def get_pending_tasks(personel_id: int, tarih: date) -> List[Dict]:
        """
        Bekleyen görevleri getirir.
        
        Args:
            personel_id: Personel ID
            tarih: Görev tarihi
            
        Returns:
            List[Dict]: Bekleyen görev listesi
        """
        try:
            gorevler = GunlukGorev.query.filter(
                GunlukGorev.personel_id == personel_id,
                GunlukGorev.gorev_tarihi == tarih
            ).options(
                joinedload(GunlukGorev.detaylar).joinedload(GorevDetay.oda).subqueryload(Oda.kat)
            ).all()
            
            result = []
            for gorev in gorevler:
                bekleyen_detaylar = [d for d in gorev.detaylar if d.durum in ['pending', 'dnd_pending']]
                # Öncelik sırasına göre sırala
                bekleyen_detaylar.sort(key=lambda x: (x.oncelik_sirasi or 999))
                
                for detay in bekleyen_detaylar:
                    # Kontrol başlangıç zamanını al
                    kontrol_baslangic = GorevService._get_kontrol_baslangic(detay.oda_id, personel_id, tarih)
                    
                    # Kat bilgisini al
                    kat_no = None
                    kat_adi = None
                    if detay.oda and detay.oda.kat:
                        kat_no = detay.oda.kat.kat_no
                        kat_adi = detay.oda.kat.kat_adi or f"Kat {kat_no}"
                    
                    item = {
                        'gorev_id': gorev.id,
                        'detay_id': detay.id,
                        'gorev_tipi': gorev.gorev_tipi,
                        'kat_no': kat_no,
                        'kat_adi': kat_adi,
                        'oda_no': detay.oda.oda_no if detay.oda else None,
                        'oda_id': detay.oda_id,
                        'durum': detay.durum,
                        'dnd_sayisi': detay.dnd_sayisi,
                        'varis_saati': detay.varis_saati.isoformat() if detay.varis_saati else None,
                        'cikis_saati': detay.cikis_saati.isoformat() if detay.cikis_saati else None,
                        'oncelik_sirasi': detay.oncelik_sirasi,
                        'kontrol_baslangic': kontrol_baslangic,
                        'kaynak_silindi': detay.misafir_kayit_id is None  # Kaynak silindi göstergesi
                    }
                    
                    # Arrivals için geri sayım ekle
                    if gorev.gorev_tipi == 'arrival_kontrol' and detay.varis_saati:
                        item['countdown'] = GorevService.calculate_countdown(detay.varis_saati)
                    
                    # Departures için geri sayım ekle
                    if gorev.gorev_tipi == 'departure_kontrol' and detay.cikis_saati:
                        item['countdown'] = GorevService.calculate_countdown(detay.cikis_saati)
                    
                    result.append(item)
            
            return result
            
        except Exception as e:
            raise Exception(f"Bekleyen görev getirme hatası: {str(e)}")
    
    @staticmethod
    def get_completed_tasks(personel_id: int, tarih: date) -> List[Dict]:
        """
        Tamamlanan görevleri getirir.
        
        Args:
            personel_id: Personel ID
            tarih: Görev tarihi
            
        Returns:
            List[Dict]: Tamamlanan görev listesi
        """
        try:
            gorevler = GunlukGorev.query.filter(
                GunlukGorev.personel_id == personel_id,
                GunlukGorev.gorev_tarihi == tarih
            ).options(
                joinedload(GunlukGorev.detaylar).joinedload(GorevDetay.oda).subqueryload(Oda.kat)
            ).all()
            
            result = []
            for gorev in gorevler:
                tamamlanan_detaylar = [d for d in gorev.detaylar if d.durum == 'completed']
                for detay in tamamlanan_detaylar:
                    # Kontrol başlangıç, bitiş ve süre bilgilerini al
                    kontrol_baslangic, kontrol_bitis, kontrol_suresi = GorevService._get_kontrol_zamanlari_ve_sure(detay.oda_id, personel_id, tarih)
                    
                    # Kat bilgisini al
                    kat_no = None
                    kat_adi = None
                    if detay.oda and detay.oda.kat:
                        kat_no = detay.oda.kat.kat_no
                        kat_adi = detay.oda.kat.kat_adi or f"Kat {kat_no}"
                    
                    result.append({
                        'gorev_id': gorev.id,
                        'detay_id': detay.id,
                        'gorev_tipi': gorev.gorev_tipi,
                        'kat_no': kat_no,
                        'kat_adi': kat_adi,
                        'oda_no': detay.oda.oda_no if detay.oda else None,
                        'oda_id': detay.oda_id,
                        'durum': detay.durum,
                        'kontrol_baslangic': kontrol_baslangic,
                        'kontrol_zamani': kontrol_bitis or (detay.kontrol_zamani.strftime('%H:%M') if detay.kontrol_zamani else None),
                        'kontrol_suresi': kontrol_suresi,
                        'dnd_sayisi': detay.dnd_sayisi,
                        'kaynak_silindi': detay.misafir_kayit_id is None  # Kaynak silindi göstergesi
                    })
            
            return result
            
        except Exception as e:
            raise Exception(f"Tamamlanan görev getirme hatası: {str(e)}")
    
    @staticmethod
    def get_dnd_tasks(personel_id: int, tarih: date) -> List[Dict]:
        """
        DND durumundaki görevleri getirir.
        
        Args:
            personel_id: Personel ID
            tarih: Görev tarihi
            
        Returns:
            List[Dict]: DND görev listesi
        """
        try:
            gorevler = GunlukGorev.query.filter(
                GunlukGorev.personel_id == personel_id,
                GunlukGorev.gorev_tarihi == tarih
            ).options(
                joinedload(GunlukGorev.detaylar).joinedload(GorevDetay.oda).subqueryload(Oda.kat),
                joinedload(GunlukGorev.detaylar).joinedload(GorevDetay.dnd_kontroller)
            ).all()
            
            result = []
            for gorev in gorevler:
                dnd_detaylar = [d for d in gorev.detaylar if d.dnd_sayisi > 0]
                for detay in dnd_detaylar:
                    kontrol_gecmisi = [{
                        'kontrol_zamani': k.kontrol_zamani.isoformat() if k.kontrol_zamani else None,
                        'notlar': k.notlar
                    } for k in detay.dnd_kontroller]
                    
                    # Kat bilgisini al
                    kat_no = None
                    kat_adi = None
                    if detay.oda and detay.oda.kat:
                        kat_no = detay.oda.kat.kat_no
                        kat_adi = detay.oda.kat.kat_adi or f"Kat {kat_no}"
                    
                    result.append({
                        'gorev_id': gorev.id,
                        'detay_id': detay.id,
                        'gorev_tipi': gorev.gorev_tipi,
                        'kat_no': kat_no,
                        'kat_adi': kat_adi,
                        'oda_no': detay.oda.oda_no if detay.oda else None,
                        'oda_id': detay.oda_id,
                        'durum': detay.durum,
                        'dnd_sayisi': detay.dnd_sayisi,
                        'son_dnd_zamani': detay.son_dnd_zamani.isoformat() if detay.son_dnd_zamani else None,
                        'kontrol_gecmisi': kontrol_gecmisi,
                        'kaynak_silindi': detay.misafir_kayit_id is None  # Kaynak silindi göstergesi
                    })
            
            return result
            
        except Exception as e:
            raise Exception(f"DND görev getirme hatası: {str(e)}")
    
    @staticmethod
    def _update_main_task_status(gorev_id: int):
        """
        Ana görevin durumunu detaylara göre günceller.
        
        Args:
            gorev_id: Ana görev ID
        """
        try:
            gorev = GunlukGorev.query.get(gorev_id)
            if not gorev:
                return
            
            detaylar = gorev.detaylar
            if not detaylar:
                return
            
            tamamlanan = sum(1 for d in detaylar if d.durum == 'completed')
            toplam = len(detaylar)
            
            if tamamlanan == toplam:
                gorev.durum = 'completed'
                gorev.tamamlanma_tarihi = datetime.now(timezone.utc)
            elif tamamlanan > 0:
                gorev.durum = 'in_progress'
            else:
                # DND var mı kontrol et
                dnd_var = any(d.durum == 'dnd_pending' for d in detaylar)
                if dnd_var:
                    gorev.durum = 'in_progress'
                    
        except Exception as e:
            raise Exception(f"Ana görev durumu güncelleme hatası: {str(e)}")
    
    @staticmethod
    def get_task_summary(personel_id: int, tarih: date) -> Dict:
        """
        Personelin günlük görev özetini getirir.
        
        Args:
            personel_id: Personel ID
            tarih: Görev tarihi
            
        Returns:
            Dict: Görev özeti
        """
        try:
            gorevler = GunlukGorev.query.filter(
                GunlukGorev.personel_id == personel_id,
                GunlukGorev.gorev_tarihi == tarih
            ).options(joinedload(GunlukGorev.detaylar)).all()
            
            toplam = 0
            tamamlanan = 0
            bekleyen = 0
            dnd = 0
            
            for gorev in gorevler:
                for detay in gorev.detaylar:
                    toplam += 1
                    if detay.durum == 'completed':
                        tamamlanan += 1
                    elif detay.durum == 'dnd_pending':
                        dnd += 1
                    else:
                        bekleyen += 1
            
            return {
                'toplam': toplam,
                'tamamlanan': tamamlanan,
                'bekleyen': bekleyen,
                'dnd': dnd,
                'tamamlanma_orani': round((tamamlanan / toplam * 100), 1) if toplam > 0 else 0
            }
            
        except Exception as e:
            raise Exception(f"Görev özeti getirme hatası: {str(e)}")

    @staticmethod
    def _get_kontrol_baslangic(oda_id: int, personel_id: int, tarih: date) -> Optional[str]:
        """
        Oda kontrol başlangıç zamanını getirir.
        
        Args:
            oda_id: Oda ID
            personel_id: Personel ID
            tarih: Kontrol tarihi
            
        Returns:
            str: Başlangıç zamanı (HH:MM formatında) veya None
        """
        try:
            from models import OdaKontrolKaydi
            
            kayit = OdaKontrolKaydi.query.filter(
                OdaKontrolKaydi.oda_id == oda_id,
                OdaKontrolKaydi.personel_id == personel_id,
                OdaKontrolKaydi.kontrol_tarihi == tarih
            ).order_by(OdaKontrolKaydi.baslangic_zamani.desc()).first()
            
            if kayit and kayit.baslangic_zamani:
                return kayit.baslangic_zamani.strftime('%H:%M')
            return None
            
        except Exception:
            return None
    
    @staticmethod
    def _get_kontrol_zamanlari_ve_sure(oda_id: int, personel_id: int, tarih: date) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Oda kontrol başlangıç, bitiş zamanlarını ve süresini getirir.
        
        Args:
            oda_id: Oda ID
            personel_id: Personel ID
            tarih: Kontrol tarihi
            
        Returns:
            Tuple[str, str, str]: (Başlangıç zamanı, Bitiş zamanı, Süre) HH:MM formatında
        """
        try:
            from models import OdaKontrolKaydi
            
            kayit = OdaKontrolKaydi.query.filter(
                OdaKontrolKaydi.oda_id == oda_id,
                OdaKontrolKaydi.personel_id == personel_id,
                OdaKontrolKaydi.kontrol_tarihi == tarih,
                OdaKontrolKaydi.bitis_zamani.isnot(None)  # Sadece tamamlanmış kayıtlar
            ).order_by(OdaKontrolKaydi.bitis_zamani.desc()).first()
            
            if kayit:
                baslangic = kayit.baslangic_zamani.strftime('%H:%M') if kayit.baslangic_zamani else None
                bitis = kayit.bitis_zamani.strftime('%H:%M') if kayit.bitis_zamani else None
                
                # Süre hesapla
                sure = None
                if kayit.baslangic_zamani and kayit.bitis_zamani:
                    fark = kayit.bitis_zamani - kayit.baslangic_zamani
                    toplam_saniye = int(fark.total_seconds())
                    if toplam_saniye < 60:
                        sure = f"{toplam_saniye} sn"
                    elif toplam_saniye < 3600:
                        dakika = toplam_saniye // 60
                        saniye = toplam_saniye % 60
                        sure = f"{dakika} dk {saniye} sn"
                    else:
                        saat = toplam_saniye // 3600
                        dakika = (toplam_saniye % 3600) // 60
                        sure = f"{saat} sa {dakika} dk"
                
                return baslangic, bitis, sure
            return None, None, None
            
        except Exception:
            return None, None, None

    @staticmethod
    def handle_misafir_kayit_deletion(misafir_kayit_ids: List[int]) -> Dict:
        """
        MisafirKayit silinmeden önce ilişkili görevleri yönetir.
        
        Tamamlanmış görevlerde misafir_kayit_id = NULL yapar (korur).
        Bekleyen görevleri siler.
        Boş kalan GunlukGorev kayıtlarını siler.
        
        Args:
            misafir_kayit_ids: Silinecek MisafirKayit ID listesi
            
        Returns:
            Dict: {
                'nullified_completed': int,  # misafir_kayit_id NULL yapılan tamamlanmış görevler
                'deleted_pending': int,       # Silinen bekleyen görevler
                'deleted_empty_gorevler': int # Silinen boş ana görevler
            }
            
        Raises:
            Exception: Veritabanı hatası durumunda
        """
        try:
            result = {
                'nullified_completed': 0,
                'deleted_pending': 0,
                'deleted_empty_gorevler': 0
            }
            
            if not misafir_kayit_ids:
                return result
            
            # İlişkili GorevDetay kayıtlarını bul
            gorev_detaylar = GorevDetay.query.filter(
                GorevDetay.misafir_kayit_id.in_(misafir_kayit_ids)
            ).all()
            
            if not gorev_detaylar:
                return result
            
            # Etkilenen ana görev ID'lerini topla
            etkilenen_gorev_ids = set()
            
            for detay in gorev_detaylar:
                etkilenen_gorev_ids.add(detay.gorev_id)
                
                if detay.durum == COMPLETED_STATUS:
                    # Tamamlanmış görevlerde sadece misafir_kayit_id'yi NULL yap
                    # Görev ve ilişkili veriler (DNDKontrol, GorevDurumLog) korunur
                    detay.misafir_kayit_id = None
                    result['nullified_completed'] += 1
                elif detay.durum in PENDING_STATUSES:
                    # Bekleyen görevleri sil
                    # CASCADE ile DNDKontrol ve GorevDurumLog da silinir
                    db.session.delete(detay)
                    result['deleted_pending'] += 1
            
            # Flush yaparak silme işlemlerini uygula
            db.session.flush()
            
            # Boş kalan GunlukGorev kayıtlarını kontrol et ve sil
            for gorev_id in etkilenen_gorev_ids:
                gorev = GunlukGorev.query.get(gorev_id)
                if gorev:
                    # Kalan detay sayısını kontrol et
                    kalan_detay_sayisi = GorevDetay.query.filter(
                        GorevDetay.gorev_id == gorev_id
                    ).count()
                    
                    if kalan_detay_sayisi == 0:
                        # Hiç detay kalmadıysa ana görevi de sil
                        db.session.delete(gorev)
                        result['deleted_empty_gorevler'] += 1
            
            return result
            
        except Exception as e:
            raise Exception(f"MisafirKayit silme görev yönetimi hatası: {str(e)}")
