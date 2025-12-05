"""
FIFO Stok Takip Servisleri

Bu modül FIFO (First In First Out) prensibiyle stok takibi için
gerekli servis fonksiyonlarını içerir.

Fonksiyonlar:
- fifo_stok_giris: Yeni stok girişi (tedarik veya ilk yükleme)
- fifo_stok_cikis: FIFO kuralına göre stok çıkışı
- fifo_stok_durumu: Ürün bazlı FIFO stok durumu
- fifo_parti_detaylari: Parti bazlı stok detayları
- ilk_stok_yukle: İlk stok yükleme işlemi

Kullanım:
    from utils.fifo_servisler import FifoStokServisi
    
    # Stok girişi
    FifoStokServisi.fifo_stok_giris(otel_id, urun_id, miktar, kaynak_tipi, referans_id)
    
    # Stok çıkışı
    FifoStokServisi.fifo_stok_cikis(otel_id, urun_id, miktar, islem_tipi, referans_id)
"""

from datetime import datetime
from decimal import Decimal
from models import (
    db, Otel, Urun, UrunStok, StokFifoKayit, StokFifoKullanim,
    StokHareket, get_kktc_now
)
from utils.helpers import log_islem, log_hata
from utils.audit import audit_create


class FifoStokServisi:
    """FIFO stok yönetim servisi"""
    
    @staticmethod
    def fifo_stok_giris(otel_id, urun_id, miktar, kaynak_tipi='tedarik', 
                        referans_id=None, kullanici_id=None, aciklama=None):
        """
        FIFO kuralına göre stok girişi yapar.
        
        Args:
            otel_id: Otel ID
            urun_id: Ürün ID
            miktar: Giriş miktarı
            kaynak_tipi: 'tedarik', 'ilk_yukleme', 'iade', 'sayim_fazlasi'
            referans_id: İlgili kaynak kaydının ID'si
            kullanici_id: İşlemi yapan kullanıcı
            aciklama: Açıklama
            
        Returns:
            dict: {'success': bool, 'fifo_kayit_id': int, 'message': str}
        """
        try:
            # Validasyon
            if miktar <= 0:
                return {'success': False, 'message': 'Miktar sıfırdan büyük olmalıdır'}
            
            otel = db.session.get(Otel, otel_id)
            if not otel:
                return {'success': False, 'message': 'Otel bulunamadı'}
            
            urun = db.session.get(Urun, urun_id)
            if not urun:
                return {'success': False, 'message': 'Ürün bulunamadı'}
            
            # FIFO kaydı oluştur
            fifo_kayit = StokFifoKayit(
                otel_id=otel_id,
                urun_id=urun_id,
                tedarik_detay_id=referans_id if kaynak_tipi == 'tedarik' else None,
                giris_miktari=miktar,
                kalan_miktar=miktar,
                kullanilan_miktar=0,
                giris_tarihi=get_kktc_now(),
                tukendi=False
            )
            db.session.add(fifo_kayit)
            db.session.flush()  # ID almak için
            
            # UrunStok güncelle veya oluştur
            urun_stok = UrunStok.query.filter_by(
                otel_id=otel_id, 
                urun_id=urun_id
            ).first()
            
            if not urun_stok:
                urun_stok = UrunStok(
                    otel_id=otel_id,
                    urun_id=urun_id,
                    mevcut_stok=0,
                    minimum_stok=urun.kritik_stok_seviyesi or 10,
                    kritik_stok_seviyesi=urun.kritik_stok_seviyesi or 5
                )
                db.session.add(urun_stok)
            
            urun_stok.mevcut_stok += miktar
            urun_stok.son_giris_tarihi = get_kktc_now()
            if kullanici_id:
                urun_stok.son_guncelleyen_id = kullanici_id
            
            # Stok hareketi kaydet
            hareket_aciklama = aciklama or f'FIFO Stok Girişi - {kaynak_tipi}'
            stok_hareket = StokHareket(
                urun_id=urun_id,
                hareket_tipi='giris',
                miktar=miktar,
                aciklama=hareket_aciklama,
                islem_yapan_id=kullanici_id
            )
            db.session.add(stok_hareket)
            
            db.session.commit()
            
            # Log kaydı
            log_islem('ekleme', 'fifo_stok_giris', {
                'otel_id': otel_id,
                'urun_id': urun_id,
                'urun_adi': urun.urun_adi,
                'miktar': miktar,
                'kaynak_tipi': kaynak_tipi,
                'fifo_kayit_id': fifo_kayit.id
            })
            
            return {
                'success': True,
                'fifo_kayit_id': fifo_kayit.id,
                'message': f'{urun.urun_adi} için {miktar} adet stok girişi yapıldı'
            }
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'fifo_stok_giris')
            return {'success': False, 'message': f'Stok girişi hatası: {str(e)}'}
    
    @staticmethod
    def fifo_stok_cikis(otel_id, urun_id, miktar, islem_tipi='zimmet', 
                        referans_id=None, kullanici_id=None):
        """
        FIFO kuralına göre stok çıkışı yapar.
        En eski partiden başlayarak stok düşer.
        
        Args:
            otel_id: Otel ID
            urun_id: Ürün ID
            miktar: Çıkış miktarı
            islem_tipi: 'zimmet', 'minibar_dolum', 'fire', 'sayim_eksik'
            referans_id: İlgili işlem kaydının ID'si
            kullanici_id: İşlemi yapan kullanıcı
            
        Returns:
            dict: {'success': bool, 'kullanim_kayitlari': list, 'message': str}
        """
        try:
            if miktar <= 0:
                return {'success': False, 'message': 'Miktar sıfırdan büyük olmalıdır'}
            
            # Mevcut FIFO kayıtlarını al (en eski önce - FIFO)
            fifo_kayitlar = StokFifoKayit.query.filter(
                StokFifoKayit.otel_id == otel_id,
                StokFifoKayit.urun_id == urun_id,
                StokFifoKayit.tukendi == False,
                StokFifoKayit.kalan_miktar > 0
            ).order_by(StokFifoKayit.giris_tarihi.asc()).all()
            
            # Toplam mevcut FIFO stok
            toplam_fifo = sum(f.kalan_miktar for f in fifo_kayitlar)
            
            # UrunStok'tan mevcut stok kontrolü
            urun_stok = UrunStok.query.filter_by(otel_id=otel_id, urun_id=urun_id).first()
            toplam_urun_stok = urun_stok.mevcut_stok if urun_stok else 0
            
            # FIFO kaydı yoksa veya yetersizse ama UrunStok'ta varsa, otomatik FIFO kaydı oluştur
            if toplam_fifo < miktar and toplam_urun_stok >= miktar:
                eksik_miktar = toplam_urun_stok - toplam_fifo
                if eksik_miktar > 0:
                    # Mevcut stok için FIFO kaydı oluştur (geçmiş tarihli)
                    yeni_fifo = StokFifoKayit(
                        otel_id=otel_id,
                        urun_id=urun_id,
                        tedarik_detay_id=None,
                        giris_miktari=eksik_miktar,
                        kalan_miktar=eksik_miktar,
                        kullanilan_miktar=0,
                        giris_tarihi=get_kktc_now(),
                        tukendi=False
                    )
                    db.session.add(yeni_fifo)
                    db.session.flush()
                    fifo_kayitlar.append(yeni_fifo)
                    toplam_fifo = sum(f.kalan_miktar for f in fifo_kayitlar)
            
            # Stok kontrolü
            if toplam_fifo < miktar:
                return {
                    'success': False, 
                    'message': f'Yetersiz stok. Mevcut: {toplam_fifo}, İstenen: {miktar}'
                }
            
            # FIFO kuralına göre çıkış yap
            kalan_miktar = miktar
            kullanim_kayitlari = []
            
            for fifo in fifo_kayitlar:
                if kalan_miktar <= 0:
                    break
                
                # Bu partiden ne kadar alınacak?
                alinacak = min(fifo.kalan_miktar, kalan_miktar)
                
                # Kullanım kaydı oluştur
                kullanim = fifo.kullan(alinacak, islem_tipi, referans_id)
                kullanim_kayitlari.append({
                    'fifo_kayit_id': fifo.id,
                    'kullanim_id': kullanim.id,
                    'miktar': alinacak,
                    'parti_tarihi': fifo.giris_tarihi.isoformat()
                })
                
                kalan_miktar -= alinacak
            
            # UrunStok güncelle
            urun_stok = UrunStok.query.filter_by(
                otel_id=otel_id, 
                urun_id=urun_id
            ).first()
            
            if urun_stok:
                urun_stok.mevcut_stok -= miktar
                urun_stok.son_cikis_tarihi = get_kktc_now()
                urun_stok.son_30gun_cikis += miktar
                if kullanici_id:
                    urun_stok.son_guncelleyen_id = kullanici_id
            
            # Stok hareketi kaydet
            stok_hareket = StokHareket(
                urun_id=urun_id,
                hareket_tipi='cikis',
                miktar=miktar,
                aciklama=f'FIFO Stok Çıkışı - {islem_tipi}',
                islem_yapan_id=kullanici_id
            )
            db.session.add(stok_hareket)
            
            db.session.commit()
            
            # Log kaydı
            urun = db.session.get(Urun, urun_id)
            log_islem('guncelleme', 'fifo_stok_cikis', {
                'otel_id': otel_id,
                'urun_id': urun_id,
                'urun_adi': urun.urun_adi if urun else 'Bilinmiyor',
                'miktar': miktar,
                'islem_tipi': islem_tipi,
                'parti_sayisi': len(kullanim_kayitlari)
            })
            
            return {
                'success': True,
                'kullanim_kayitlari': kullanim_kayitlari,
                'message': f'{miktar} adet stok çıkışı yapıldı ({len(kullanim_kayitlari)} partiden)'
            }
            
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'fifo_stok_cikis')
            return {'success': False, 'message': f'Stok çıkışı hatası: {str(e)}'}
    
    @staticmethod
    def fifo_stok_durumu(otel_id, urun_id=None):
        """
        FIFO bazlı stok durumunu getirir.
        
        Args:
            otel_id: Otel ID
            urun_id: Ürün ID (opsiyonel, None ise tüm ürünler)
            
        Returns:
            list: Stok durumu listesi
        """
        try:
            query = StokFifoKayit.query.filter(
                StokFifoKayit.otel_id == otel_id,
                StokFifoKayit.tukendi == False
            )
            
            if urun_id:
                query = query.filter(StokFifoKayit.urun_id == urun_id)
            
            fifo_kayitlar = query.order_by(
                StokFifoKayit.urun_id,
                StokFifoKayit.giris_tarihi.asc()
            ).all()
            
            # Ürün bazlı grupla
            urun_stoklari = {}
            for fifo in fifo_kayitlar:
                uid = fifo.urun_id
                if uid not in urun_stoklari:
                    urun_stoklari[uid] = {
                        'urun_id': uid,
                        'urun_adi': fifo.urun.urun_adi if fifo.urun else 'Bilinmiyor',
                        'toplam_stok': 0,
                        'parti_sayisi': 0,
                        'en_eski_parti': None,
                        'partiler': []
                    }
                
                urun_stoklari[uid]['toplam_stok'] += fifo.kalan_miktar
                urun_stoklari[uid]['parti_sayisi'] += 1
                urun_stoklari[uid]['partiler'].append({
                    'fifo_id': fifo.id,
                    'giris_tarihi': fifo.giris_tarihi.isoformat(),
                    'giris_miktari': fifo.giris_miktari,
                    'kalan_miktar': fifo.kalan_miktar,
                    'kullanilan_miktar': fifo.kullanilan_miktar
                })
                
                if urun_stoklari[uid]['en_eski_parti'] is None:
                    urun_stoklari[uid]['en_eski_parti'] = fifo.giris_tarihi.isoformat()
            
            return list(urun_stoklari.values())
            
        except Exception as e:
            log_hata(e, 'fifo_stok_durumu')
            return []
    
    @staticmethod
    def ilk_stok_yukle(otel_id, stok_verileri, kullanici_id):
        """
        Otel için ilk stok yüklemesi yapar.
        Her otel için sadece 1 kez yapılabilir.
        
        Args:
            otel_id: Otel ID
            stok_verileri: [{'urun_id': int, 'miktar': int}, ...]
            kullanici_id: İşlemi yapan kullanıcı ID
            
        Returns:
            dict: {'success': bool, 'message': str, 'yuklenen_urun_sayisi': int}
        """
        try:
            otel = db.session.get(Otel, otel_id)
            if not otel:
                return {'success': False, 'message': 'Otel bulunamadı'}
            
            # İlk stok yükleme kontrolü
            if otel.ilk_stok_yuklendi:
                return {
                    'success': False, 
                    'message': f'Bu otel için ilk stok yüklemesi zaten yapılmış. Tarih: {otel.ilk_stok_yukleme_tarihi}'
                }
            
            if not stok_verileri:
                return {'success': False, 'message': 'Stok verisi boş olamaz'}
            
            yuklenen_sayisi = 0
            hatalar = []
            
            for veri in stok_verileri:
                urun_id = veri.get('urun_id')
                miktar = veri.get('miktar', 0)
                
                if not urun_id or miktar <= 0:
                    continue
                
                # FIFO stok girişi yap
                sonuc = FifoStokServisi.fifo_stok_giris(
                    otel_id=otel_id,
                    urun_id=urun_id,
                    miktar=miktar,
                    kaynak_tipi='ilk_yukleme',
                    referans_id=None,
                    kullanici_id=kullanici_id,
                    aciklama=f'İlk stok yüklemesi - {otel.ad}'
                )
                
                if sonuc['success']:
                    yuklenen_sayisi += 1
                else:
                    urun = db.session.get(Urun, urun_id)
                    hatalar.append(f"{urun.urun_adi if urun else urun_id}: {sonuc['message']}")
            
            if yuklenen_sayisi > 0:
                # Otel ilk stok yükleme durumunu güncelle
                otel.ilk_stok_yuklendi = True
                otel.ilk_stok_yukleme_tarihi = get_kktc_now()
                otel.ilk_stok_yukleyen_id = kullanici_id
                db.session.commit()
                
                # Log kaydı
                log_islem('ekleme', 'ilk_stok_yukleme', {
                    'otel_id': otel_id,
                    'otel_adi': otel.ad,
                    'yuklenen_urun_sayisi': yuklenen_sayisi,
                    'kullanici_id': kullanici_id
                })
                
                mesaj = f'{yuklenen_sayisi} ürün için ilk stok yüklemesi tamamlandı.'
                if hatalar:
                    mesaj += f' {len(hatalar)} ürün yüklenemedi.'
                
                return {
                    'success': True,
                    'message': mesaj,
                    'yuklenen_urun_sayisi': yuklenen_sayisi,
                    'hatalar': hatalar
                }
            else:
                return {
                    'success': False,
                    'message': 'Hiçbir ürün yüklenemedi',
                    'hatalar': hatalar
                }
                
        except Exception as e:
            db.session.rollback()
            log_hata(e, 'ilk_stok_yukle')
            return {'success': False, 'message': f'İlk stok yükleme hatası: {str(e)}'}
    
    @staticmethod
    def mevcut_stok_getir(otel_id, urun_id):
        """
        Belirli bir ürünün otel deposundaki mevcut stok miktarını getirir.
        
        Args:
            otel_id: Otel ID
            urun_id: Ürün ID
            
        Returns:
            int: Mevcut stok miktarı
        """
        try:
            toplam = db.session.query(
                db.func.coalesce(db.func.sum(StokFifoKayit.kalan_miktar), 0)
            ).filter(
                StokFifoKayit.otel_id == otel_id,
                StokFifoKayit.urun_id == urun_id,
                StokFifoKayit.tukendi == False
            ).scalar()
            
            return int(toplam) if toplam else 0
            
        except Exception as e:
            log_hata(e, 'mevcut_stok_getir')
            return 0
    
    @staticmethod
    def toplu_stok_getir(otel_id, urun_ids=None):
        """
        Birden fazla ürünün stok durumunu tek sorguda getirir.
        
        Args:
            otel_id: Otel ID
            urun_ids: Ürün ID listesi (None ise tüm ürünler)
            
        Returns:
            dict: {urun_id: mevcut_stok, ...}
        """
        try:
            query = db.session.query(
                StokFifoKayit.urun_id,
                db.func.sum(StokFifoKayit.kalan_miktar).label('toplam')
            ).filter(
                StokFifoKayit.otel_id == otel_id,
                StokFifoKayit.tukendi == False
            )
            
            if urun_ids:
                query = query.filter(StokFifoKayit.urun_id.in_(urun_ids))
            
            sonuclar = query.group_by(StokFifoKayit.urun_id).all()
            
            return {row.urun_id: int(row.toplam) for row in sonuclar}
            
        except Exception as e:
            log_hata(e, 'toplu_stok_getir')
            return {}
