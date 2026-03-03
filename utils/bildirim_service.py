"""
Bildirim Service - Real-time bildirim yönetimi

Bu modül uygulama içi bildirimleri yönetir:
- Bildirim oluşturma
- Bildirim okuma
- Okundu işaretleme
- SSE stream desteği
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pytz

from models import db

KKTC_TZ = pytz.timezone('Europe/Nicosia')

def get_kktc_now():
    return datetime.now(KKTC_TZ)


class BildirimTipi:
    """Bildirim tipleri"""
    GOREV_OLUSTURULDU = 'gorev_olusturuldu'
    GOREV_TAMAMLANDI = 'gorev_tamamlandi'
    DND_KAYDI = 'dnd_kaydi'
    SARFIYAT_YOK = 'sarfiyat_yok'
    DOLULUK_YUKLENDI = 'doluluk_yuklendi'
    ROYALBAR_TALEBI = 'royalbar_talebi'


class BildirimService:
    """Bildirim işlemleri için service class"""
    
    @staticmethod
    def bildirim_olustur(
        hedef_rol: str,
        bildirim_tipi: str,
        baslik: str,
        mesaj: str = None,
        hedef_otel_id: int = None,
        hedef_kullanici_id: int = None,
        oda_id: int = None,
        gorev_id: int = None,
        gonderen_id: int = None
    ) -> int:
        """
        Yeni bildirim oluşturur
        
        Args:
            hedef_rol: 'depo_sorumlusu' veya 'kat_sorumlusu'
            bildirim_tipi: BildirimTipi enum değeri
            baslik: Bildirim başlığı
            mesaj: Detaylı mesaj (opsiyonel)
            hedef_otel_id: Hedef otel ID (opsiyonel)
            hedef_kullanici_id: Belirli kullanıcıya gönderim (opsiyonel)
            oda_id: İlişkili oda ID (opsiyonel)
            gorev_id: İlişkili görev ID (opsiyonel)
            gonderen_id: Gönderen kullanıcı ID (opsiyonel)
            
        Returns:
            int: Oluşturulan bildirim ID
        """
        try:
            sql = """
                INSERT INTO bildirimler 
                (hedef_rol, bildirim_tipi, baslik, mesaj, hedef_otel_id, 
                 hedef_kullanici_id, oda_id, gorev_id, gonderen_id, olusturma_tarihi)
                VALUES (:hedef_rol, :bildirim_tipi, :baslik, :mesaj, :hedef_otel_id,
                        :hedef_kullanici_id, :oda_id, :gorev_id, :gonderen_id, :olusturma_tarihi)
                RETURNING id
            """
            
            result = db.session.execute(
                db.text(sql),
                {
                    'hedef_rol': hedef_rol,
                    'bildirim_tipi': bildirim_tipi,
                    'baslik': baslik,
                    'mesaj': mesaj,
                    'hedef_otel_id': hedef_otel_id,
                    'hedef_kullanici_id': hedef_kullanici_id,
                    'oda_id': oda_id,
                    'gorev_id': gorev_id,
                    'gonderen_id': gonderen_id,
                    'olusturma_tarihi': get_kktc_now()
                }
            )
            db.session.commit()
            
            row = result.fetchone()
            return row[0] if row else None
            
        except Exception as e:
            db.session.rollback()
            print(f"Bildirim oluşturma hatası: {e}")
            return None
    
    @staticmethod
    def kullanici_bildirimlerini_getir(
        kullanici_id: int,
        kullanici_rol: str,
        otel_id: int = None,
        sadece_okunmamis: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Kullanıcının bildirimlerini getirir
        
        Args:
            kullanici_id: Kullanıcı ID
            kullanici_rol: Kullanıcı rolü
            otel_id: Otel ID (kat sorumlusu için)
            sadece_okunmamis: Sadece okunmamış bildirimleri getir
            limit: Maksimum bildirim sayısı
            
        Returns:
            List[Dict]: Bildirim listesi
        """
        try:
            sql = """
                SELECT id, hedef_rol, bildirim_tipi, baslik, mesaj, 
                       okundu, olusturma_tarihi, oda_id, gorev_id
                FROM bildirimler
                WHERE (hedef_rol = :hedef_rol OR hedef_kullanici_id = :kullanici_id)
            """
            
            params = {
                'hedef_rol': kullanici_rol,
                'kullanici_id': kullanici_id,
                'limit': limit
            }
            
            if otel_id:
                sql += " AND (hedef_otel_id = :otel_id OR hedef_otel_id IS NULL)"
                params['otel_id'] = otel_id
            
            if sadece_okunmamis:
                sql += " AND okundu = FALSE"
            
            # Son 24 saat
            sql += " AND olusturma_tarihi > NOW() - INTERVAL '24 hours'"
            sql += " ORDER BY olusturma_tarihi DESC LIMIT :limit"
            
            result = db.session.execute(db.text(sql), params)
            
            bildirimler = []
            for row in result:
                bildirimler.append({
                    'id': row[0],
                    'hedef_rol': row[1],
                    'bildirim_tipi': row[2],
                    'baslik': row[3],
                    'mesaj': row[4],
                    'okundu': row[5],
                    'olusturma_tarihi': row[6].isoformat() if row[6] else None,
                    'oda_id': row[7],
                    'gorev_id': row[8]
                })
            
            return bildirimler
            
        except Exception as e:
            print(f"Bildirim getirme hatası: {e}")
            return []
    
    @staticmethod
    def okunmamis_sayisi(kullanici_id: int, kullanici_rol: str, otel_id: int = None) -> int:
        """Okunmamış bildirim sayısını döndürür"""
        try:
            sql = """
                SELECT COUNT(*) FROM bildirimler
                WHERE (hedef_rol = :hedef_rol OR hedef_kullanici_id = :kullanici_id)
                AND okundu = FALSE
                AND olusturma_tarihi > NOW() - INTERVAL '24 hours'
            """
            
            params = {
                'hedef_rol': kullanici_rol,
                'kullanici_id': kullanici_id
            }
            
            if otel_id:
                sql = sql.replace(
                    "AND okundu = FALSE",
                    "AND (hedef_otel_id = :otel_id OR hedef_otel_id IS NULL) AND okundu = FALSE"
                )
                params['otel_id'] = otel_id
            
            result = db.session.execute(db.text(sql), params)
            row = result.fetchone()
            return row[0] if row else 0
            
        except Exception as e:
            db.session.rollback()
            print(f"Okunmamış sayısı hatası: {e}")
            return 0
    
    @staticmethod
    def okundu_isaretle(bildirim_id: int) -> bool:
        """Bildirimi okundu olarak işaretler"""
        try:
            sql = "UPDATE bildirimler SET okundu = TRUE WHERE id = :id"
            db.session.execute(db.text(sql), {'id': bildirim_id})
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Okundu işaretleme hatası: {e}")
            return False
    
    @staticmethod
    def tumunu_okundu_isaretle(kullanici_id: int, kullanici_rol: str, otel_id: int = None) -> bool:
        """Tüm bildirimleri okundu olarak işaretler"""
        try:
            sql = """
                UPDATE bildirimler SET okundu = TRUE
                WHERE (hedef_rol = :hedef_rol OR hedef_kullanici_id = :kullanici_id)
                AND okundu = FALSE
            """
            
            params = {
                'hedef_rol': kullanici_rol,
                'kullanici_id': kullanici_id
            }
            
            if otel_id:
                sql = sql.replace(
                    "AND okundu = FALSE",
                    "AND (hedef_otel_id = :otel_id OR hedef_otel_id IS NULL) AND okundu = FALSE"
                )
                params['otel_id'] = otel_id
            
            db.session.execute(db.text(sql), params)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Tümünü okundu işaretleme hatası: {e}")
            return False
    
    @staticmethod
    def yeni_bildirimler_var_mi(
        kullanici_id: int,
        kullanici_rol: str,
        otel_id: int = None,
        son_kontrol: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        Son kontrolden sonra gelen yeni bildirimleri getirir (SSE için)
        """
        try:
            sql = """
                SELECT id, hedef_rol, bildirim_tipi, baslik, mesaj, 
                       okundu, olusturma_tarihi, oda_id, gorev_id
                FROM bildirimler
                WHERE (hedef_rol = :hedef_rol OR hedef_kullanici_id = :kullanici_id)
                AND okundu = FALSE
            """
            
            params = {
                'hedef_rol': kullanici_rol,
                'kullanici_id': kullanici_id
            }
            
            if otel_id:
                sql += " AND (hedef_otel_id = :otel_id OR hedef_otel_id IS NULL)"
                params['otel_id'] = otel_id
            
            if son_kontrol:
                sql += " AND olusturma_tarihi > :son_kontrol"
                params['son_kontrol'] = son_kontrol
            
            sql += " ORDER BY olusturma_tarihi DESC LIMIT 10"
            
            result = db.session.execute(db.text(sql), params)
            
            bildirimler = []
            for row in result:
                bildirimler.append({
                    'id': row[0],
                    'hedef_rol': row[1],
                    'bildirim_tipi': row[2],
                    'baslik': row[3],
                    'mesaj': row[4],
                    'okundu': row[5],
                    'olusturma_tarihi': row[6].isoformat() if row[6] else None,
                    'oda_id': row[7],
                    'gorev_id': row[8]
                })
            
            return bildirimler
            
        except Exception as e:
            db.session.rollback()
            print(f"Yeni bildirim kontrolü hatası: {e}")
            return []


# Yardımcı fonksiyonlar - Kolay kullanım için
def gorev_olusturuldu_bildirimi(otel_id: int, otel_adi: str, gorev_sayisi: int, gonderen_id: int = None):
    """Görev oluşturulduğunda kat sorumlularına bildirim gönderir"""
    return BildirimService.bildirim_olustur(
        hedef_rol='kat_sorumlusu',
        bildirim_tipi=BildirimTipi.GOREV_OLUSTURULDU,
        baslik=f"📋 {otel_adi} için {gorev_sayisi} yeni görev",
        mesaj=f"Bugün için {gorev_sayisi} oda kontrol görevi oluşturuldu.",
        hedef_otel_id=otel_id,
        gonderen_id=gonderen_id
    )


def gorev_tamamlandi_bildirimi(
    otel_id: int,
    oda_no: str,
    personel_adi: str,
    gorev_id: int = None,
    oda_id: int = None,
    gonderen_id: int = None
):
    """Görev tamamlandığında depo sorumlusuna bildirim gönderir"""
    return BildirimService.bildirim_olustur(
        hedef_rol='depo_sorumlusu',
        bildirim_tipi=BildirimTipi.GOREV_TAMAMLANDI,
        baslik=f"✅ Oda {oda_no} kontrolü tamamlandı",
        mesaj=f"{personel_adi} tarafından kontrol edildi.",
        hedef_otel_id=otel_id,
        gorev_id=gorev_id,
        oda_id=oda_id,
        gonderen_id=gonderen_id
    )


def dnd_bildirimi(
    otel_id: int,
    oda_no: str,
    personel_adi: str,
    deneme_sayisi: int,
    oda_id: int = None,
    gonderen_id: int = None
):
    """DND kaydı oluşturulduğunda depo sorumlusuna bildirim gönderir"""
    return BildirimService.bildirim_olustur(
        hedef_rol='depo_sorumlusu',
        bildirim_tipi=BildirimTipi.DND_KAYDI,
        baslik=f"🚫 Oda {oda_no} DND ({deneme_sayisi}. deneme)",
        mesaj=f"{personel_adi} tarafından DND olarak işaretlendi.",
        hedef_otel_id=otel_id,
        oda_id=oda_id,
        gonderen_id=gonderen_id
    )


def sarfiyat_yok_bildirimi(
    otel_id: int,
    oda_no: str,
    personel_adi: str,
    oda_id: int = None,
    gonderen_id: int = None
):
    """Sarfiyat yok kaydı oluşturulduğunda depo sorumlusuna bildirim gönderir"""
    return BildirimService.bildirim_olustur(
        hedef_rol='depo_sorumlusu',
        bildirim_tipi=BildirimTipi.SARFIYAT_YOK,
        baslik=f"✔️ Oda {oda_no} sarfiyat yok",
        mesaj=f"{personel_adi} tarafından kontrol edildi, sarfiyat yok.",
        hedef_otel_id=otel_id,
        oda_id=oda_id,
        gonderen_id=gonderen_id
    )


def doluluk_yuklendi_bildirimi(otel_id: int, otel_adi: str, tarih: str, gonderen_id: int = None):
    """Doluluk bilgileri yüklendiğinde kat sorumlularına bildirim gönderir"""
    return BildirimService.bildirim_olustur(
        hedef_rol='kat_sorumlusu',
        bildirim_tipi=BildirimTipi.DOLULUK_YUKLENDI,
        baslik=f"📊 {otel_adi} doluluk bilgileri yüklendi",
        mesaj=f"{tarih} için doluluk bilgileri güncellendi.",
        hedef_otel_id=otel_id,
        gonderen_id=gonderen_id
    )


def royalbar_talebi_bildirimi(
    otel_id: int,
    oda_no: str,
    kat_adi: str,
    oda_id: int = None,
    notlar: str = None
):
    """Yeni Royalbar kişiselleştirme talebi geldiğinde kat sorumlusu ve yöneticilere bildirim gönderir"""
    mesaj = f"{kat_adi} - Oda {oda_no} misafiri Royalbar kişiselleştirme talebi gönderdi."
    if notlar:
        mesaj += f" Not: {notlar[:100]}"
    
    # Kat sorumlusuna bildirim
    BildirimService.bildirim_olustur(
        hedef_rol='kat_sorumlusu',
        bildirim_tipi=BildirimTipi.ROYALBAR_TALEBI,
        baslik=f"🛎️ Oda {oda_no} - Yeni Royalbar Kişiselleştirme Talebi",
        mesaj=mesaj,
        hedef_otel_id=otel_id,
        oda_id=oda_id
    )
    
    # Yöneticilere bildirim
    BildirimService.bildirim_olustur(
        hedef_rol='sistem_yoneticisi',
        bildirim_tipi=BildirimTipi.ROYALBAR_TALEBI,
        baslik=f"🛎️ Oda {oda_no} - Yeni Royalbar Kişiselleştirme Talebi",
        mesaj=mesaj,
        hedef_otel_id=otel_id,
        oda_id=oda_id
    )
    
    # Admin rolüne de bildirim
    BildirimService.bildirim_olustur(
        hedef_rol='admin',
        bildirim_tipi=BildirimTipi.ROYALBAR_TALEBI,
        baslik=f"🛎️ Oda {oda_no} - Yeni Royalbar Kişiselleştirme Talebi",
        mesaj=mesaj,
        hedef_otel_id=otel_id,
        oda_id=oda_id
    )

# Standalone wrapper - allows `from utils.bildirim_service import bildirim_olustur`
def bildirim_olustur(
    hedef_rol: str,
    bildirim_tipi: str,
    baslik: str,
    mesaj: str = None,
    hedef_otel_id: int = None,
    hedef_kullanici_id: int = None,
    oda_id: int = None,
    gorev_id: int = None,
    gonderen_id: int = None
) -> int:
    """Wrapper for BildirimService.bildirim_olustur - backward compatible import"""
    return BildirimService.bildirim_olustur(
        hedef_rol=hedef_rol,
        bildirim_tipi=bildirim_tipi,
        baslik=baslik,
        mesaj=mesaj,
        hedef_otel_id=hedef_otel_id,
        hedef_kullanici_id=hedef_kullanici_id,
        oda_id=oda_id,
        gorev_id=gorev_id,
        gonderen_id=gonderen_id
    )
