"""
Oda Doluluk Hesaplama Servisi
Oda doluluk durumlarını hesaplar ve raporlar
"""

from datetime import date, datetime, timedelta
from models import db, MisafirKayit, Oda, Kat
from sqlalchemy import and_, or_, func


class OccupancyService:
    """Oda doluluk hesaplama servisi sınıfı"""
    
    @staticmethod
    def get_oda_doluluk_durumu(oda_id, tarih=None):
        """
        Belirli bir odanın belirli bir tarihteki doluluk durumunu döner
        
        Args:
            oda_id: Oda ID
            tarih: Kontrol edilecek tarih (None ise bugün)
            
        Returns:
            dict: {
                'dolu': bool,
                'mevcut_misafir': MisafirKayit veya None,
                'gelecek_rezervasyon': MisafirKayit veya None,
                'kalan_gun': int veya None
            }
        """
        if tarih is None:
            tarih = date.today()
        
        # Mevcut misafir (bugün odada olan)
        mevcut_misafir = MisafirKayit.query.filter(
            and_(
                MisafirKayit.oda_id == oda_id,
                MisafirKayit.giris_tarihi <= tarih,
                MisafirKayit.cikis_tarihi > tarih
            )
        ).order_by(MisafirKayit.giris_tarihi.desc()).first()
        
        # Gelecek rezervasyon (en yakın)
        gelecek_rezervasyon = MisafirKayit.query.filter(
            and_(
                MisafirKayit.oda_id == oda_id,
                MisafirKayit.giris_tarihi > tarih
            )
        ).order_by(MisafirKayit.giris_tarihi.asc()).first()
        
        # Kalan gün hesapla
        kalan_gun = None
        if mevcut_misafir:
            kalan_gun = (mevcut_misafir.cikis_tarihi - tarih).days
        
        return {
            'dolu': mevcut_misafir is not None,
            'mevcut_misafir': mevcut_misafir,
            'gelecek_rezervasyon': gelecek_rezervasyon,
            'kalan_gun': kalan_gun
        }
    
    @staticmethod
    def get_gunluk_doluluk_raporu(tarih, otel_id=None):
        """
        Belirli bir tarihteki genel doluluk raporunu döner
        
        Args:
            tarih: Rapor tarihi (date objesi)
            otel_id: Otel ID (opsiyonel, filtreleme için)
            
        Returns:
            dict: {
                'tarih': date,
                'toplam_oda': int,
                'dolu_oda': int,
                'giris_sayisi': int,
                'cikis_sayisi': int,
                'dolu_odalar': [oda_listesi],
                'kat_bazli': {kat_id: {dolu_oda_sayisi, odalar}}
            }
        """
        # Toplam oda sayısı
        oda_query = Oda.query.filter_by(aktif=True)
        
        if otel_id:
            oda_query = oda_query.join(Kat).filter(Kat.otel_id == otel_id)
        
        toplam_oda = oda_query.count()
        
        # Dolu odalar (o tarihte misafiri olan)
        dolu_oda_query = db.session.query(MisafirKayit.oda_id).filter(
            and_(
                MisafirKayit.giris_tarihi <= tarih,
                MisafirKayit.cikis_tarihi > tarih
            )
        ).distinct()
        
        if otel_id:
            dolu_oda_query = dolu_oda_query.join(Oda).join(Kat).filter(Kat.otel_id == otel_id)
        
        dolu_oda_ids = [row[0] for row in dolu_oda_query.all()]
        dolu_oda_sayisi = len(dolu_oda_ids)
        
        # Giriş yapacak misafirler (o gün giriş tarihi olan)
        giris_query = MisafirKayit.query.filter(MisafirKayit.giris_tarihi == tarih)
        
        if otel_id:
            giris_query = giris_query.join(Oda).join(Kat).filter(Kat.otel_id == otel_id)
        
        giris_sayisi = giris_query.count()
        
        # Çıkış yapacak misafirler (o gün çıkış tarihi olan)
        cikis_query = MisafirKayit.query.filter(MisafirKayit.cikis_tarihi == tarih)
        
        if otel_id:
            cikis_query = cikis_query.join(Oda).join(Kat).filter(Kat.otel_id == otel_id)
        
        cikis_sayisi = cikis_query.count()
        
        # Dolu odaların detayları
        dolu_odalar = []
        if dolu_oda_ids:
            dolu_oda_objeleri = Oda.query.filter(Oda.id.in_(dolu_oda_ids)).all()
            
            for oda in dolu_oda_objeleri:
                # O odanın o tarihteki misafir bilgisi
                misafir = MisafirKayit.query.filter(
                    and_(
                        MisafirKayit.oda_id == oda.id,
                        MisafirKayit.giris_tarihi <= tarih,
                        MisafirKayit.cikis_tarihi > tarih
                    )
                ).first()
                
                dolu_odalar.append({
                    'oda': oda,
                    'misafir': misafir,
                    'kalan_gun': (misafir.cikis_tarihi - tarih).days if misafir else 0
                })
        
        # Kat bazlı grupla
        kat_bazli = {}
        for oda_info in dolu_odalar:
            oda = oda_info['oda']
            kat_id = oda.kat_id
            
            if kat_id not in kat_bazli:
                kat_bazli[kat_id] = {
                    'kat': oda.kat,
                    'dolu_oda_sayisi': 0,
                    'toplam_oda_sayisi': 0,
                    'odalar': [],
                    'bos_odalar': []
                }
            
            kat_bazli[kat_id]['dolu_oda_sayisi'] += 1
            kat_bazli[kat_id]['odalar'].append(oda_info)
        
        # Boş odaları da ekle (her kat için)
        tum_odalar = oda_query.all()
        for oda in tum_odalar:
            kat_id = oda.kat_id
            
            if kat_id not in kat_bazli:
                kat_bazli[kat_id] = {
                    'kat': oda.kat,
                    'dolu_oda_sayisi': 0,
                    'toplam_oda_sayisi': 0,
                    'odalar': [],
                    'bos_odalar': []
                }
            
            kat_bazli[kat_id]['toplam_oda_sayisi'] += 1
            
            # Eğer oda dolu değilse boş odalara ekle
            if oda.id not in dolu_oda_ids:
                kat_bazli[kat_id]['bos_odalar'].append(oda)
        
        return {
            'tarih': tarih,
            'toplam_oda': toplam_oda,
            'dolu_oda': dolu_oda_sayisi,
            'bos_oda': toplam_oda - dolu_oda_sayisi,
            'giris_sayisi': giris_sayisi,
            'cikis_sayisi': cikis_sayisi,
            'dolu_odalar': dolu_odalar,
            'kat_bazli': kat_bazli
        }
    
    @staticmethod
    def get_oda_detay_bilgileri(oda_id):
        """
        Odanın detaylı misafir bilgilerini döner
        
        Args:
            oda_id: Oda ID
            
        Returns:
            dict: {
                'oda': Oda,
                'mevcut_misafir': MisafirKayit veya None,
                'gelecek_rezervasyonlar': [MisafirKayit listesi],
                'gecmis_kayitlar': [MisafirKayit listesi]
            }
        """
        oda = Oda.query.get(oda_id)
        
        if not oda:
            return None
        
        bugun = date.today()
        
        # Mevcut misafir
        mevcut_misafir = MisafirKayit.query.filter(
            and_(
                MisafirKayit.oda_id == oda_id,
                MisafirKayit.giris_tarihi <= bugun,
                MisafirKayit.cikis_tarihi > bugun
            )
        ).first()
        
        # Gelecek rezervasyonlar
        gelecek_rezervasyonlar = MisafirKayit.query.filter(
            and_(
                MisafirKayit.oda_id == oda_id,
                MisafirKayit.giris_tarihi > bugun
            )
        ).order_by(MisafirKayit.giris_tarihi.asc()).all()
        
        # Geçmiş kayıtlar (son 10)
        gecmis_kayitlar = MisafirKayit.query.filter(
            and_(
                MisafirKayit.oda_id == oda_id,
                MisafirKayit.cikis_tarihi <= bugun
            )
        ).order_by(MisafirKayit.cikis_tarihi.desc()).limit(10).all()
        
        return {
            'oda': oda,
            'mevcut_misafir': mevcut_misafir,
            'gelecek_rezervasyonlar': gelecek_rezervasyonlar,
            'gecmis_kayitlar': gecmis_kayitlar
        }
    
    @staticmethod
    def get_haftalik_doluluk_ozeti(baslangic_tarihi, otel_id=None):
        """
        Haftalık doluluk özetini döner (7 günlük)
        
        Args:
            baslangic_tarihi: Başlangıç tarihi
            otel_id: Otel ID (opsiyonel)
            
        Returns:
            list: Her gün için doluluk bilgisi
        """
        ozet = []
        
        for i in range(7):
            tarih = baslangic_tarihi + timedelta(days=i)
            gunluk_rapor = OccupancyService.get_gunluk_doluluk_raporu(tarih, otel_id)
            
            ozet.append({
                'tarih': tarih,
                'gun_adi': OccupancyService._get_gun_adi(tarih),
                'dolu_oda': gunluk_rapor['dolu_oda'],
                'toplam_oda': gunluk_rapor['toplam_oda'],
                'doluluk_orani': round((gunluk_rapor['dolu_oda'] / gunluk_rapor['toplam_oda'] * 100), 1) if gunluk_rapor['toplam_oda'] > 0 else 0,
                'giris_sayisi': gunluk_rapor['giris_sayisi'],
                'cikis_sayisi': gunluk_rapor['cikis_sayisi']
            })
        
        return ozet
    
    @staticmethod
    def _get_gun_adi(tarih):
        """Tarihten gün adını döner (Türkçe)"""
        gunler = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
        return gunler[tarih.weekday()]
    
    @staticmethod
    def get_kalan_gun_sayisi(cikis_tarihi, referans_tarihi=None):
        """
        Çıkış tarihine kalan gün sayısını hesaplar
        
        Args:
            cikis_tarihi: Çıkış tarihi
            referans_tarihi: Referans tarihi (None ise bugün)
            
        Returns:
            int: Kalan gün sayısı
        """
        if referans_tarihi is None:
            referans_tarihi = date.today()
        
        if isinstance(cikis_tarihi, datetime):
            cikis_tarihi = cikis_tarihi.date()
        
        if isinstance(referans_tarihi, datetime):
            referans_tarihi = referans_tarihi.date()
        
        return (cikis_tarihi - referans_tarihi).days
    
    @staticmethod
    def get_kalis_suresi(giris_tarihi, cikis_tarihi):
        """
        Kalış süresini hesaplar (gece sayısı)
        
        Args:
            giris_tarihi: Giriş tarihi
            cikis_tarihi: Çıkış tarihi
            
        Returns:
            int: Kalış süresi (gece)
        """
        if isinstance(giris_tarihi, datetime):
            giris_tarihi = giris_tarihi.date()
        
        if isinstance(cikis_tarihi, datetime):
            cikis_tarihi = cikis_tarihi.date()
        
        return (cikis_tarihi - giris_tarihi).days
