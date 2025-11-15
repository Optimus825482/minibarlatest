"""
Data Migration: OdaTipiSatisFiyati - oda_tipi string'den oda_tipi_id integer'a geçiş
Tarih: 2025-11-15
"""

from models import db, OdaTipiSatisFiyati, OdaTipi
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def migrate_oda_tipi_satis_fiyatlari():
    """
    OdaTipiSatisFiyati tablosundaki eski oda_tipi string değerlerini
    yeni oda_tipi_id integer değerlerine dönüştür
    """
    try:
        print("=" * 80)
        print("ODA TİPİ SATIŞ FİYATLARI MİGRASYONU BAŞLIYOR")
        print("=" * 80)
        
        # Oda tipi mapping'i oluştur
        oda_tipleri = OdaTipi.query.all()
        oda_tipi_map = {ot.ad: ot.id for ot in oda_tipleri}
        
        print(f"\n✅ Oda Tipi Mapping:")
        for ad, id in oda_tipi_map.items():
            print(f"   {ad} → ID: {id}")
        
        # Eski string değerleri kontrol et (eğer eski kolon hala varsa)
        try:
            # Eski oda_tipi kolonunu kontrol et
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'oda_tipi_satis_fiyatlari' 
                AND column_name = 'oda_tipi'
            """))
            
            eski_kolon_var = result.fetchone() is not None
            
            if eski_kolon_var:
                print("\n⚠️  Eski 'oda_tipi' string kolonu bulundu, migration gerekli")
                
                # Eski değerleri oku
                result = db.session.execute(text("""
                    SELECT id, oda_tipi, urun_id 
                    FROM oda_tipi_satis_fiyatlari 
                    WHERE oda_tipi IS NOT NULL
                """))
                
                eski_kayitlar = result.fetchall()
                print(f"\n📊 Güncellenecek kayıt sayısı: {len(eski_kayitlar)}")
                
                guncellenen = 0
                hatali = 0
                
                for kayit in eski_kayitlar:
                    kayit_id, oda_tipi_str, urun_id = kayit
                    
                    # Oda tipi ID'sini bul
                    oda_tipi_id = oda_tipi_map.get(oda_tipi_str)
                    
                    if oda_tipi_id:
                        # Güncelle
                        db.session.execute(text("""
                            UPDATE oda_tipi_satis_fiyatlari 
                            SET oda_tipi_id = :oda_tipi_id 
                            WHERE id = :kayit_id
                        """), {
                            'oda_tipi_id': oda_tipi_id,
                            'kayit_id': kayit_id
                        })
                        guncellenen += 1
                        print(f"   ✅ ID {kayit_id}: '{oda_tipi_str}' → {oda_tipi_id}")
                    else:
                        hatali += 1
                        print(f"   ❌ ID {kayit_id}: '{oda_tipi_str}' için oda tipi bulunamadı!")
                
                db.session.commit()
                
                print(f"\n✅ Migration tamamlandı:")
                print(f"   - Güncellenen: {guncellenen}")
                print(f"   - Hatalı: {hatali}")
                
                # Eski kolonu kaldır (opsiyonel - dikkatli!)
                print("\n⚠️  Eski 'oda_tipi' kolonunu kaldırmak için:")
                print("   ALTER TABLE oda_tipi_satis_fiyatlari DROP COLUMN oda_tipi;")
                
            else:
                print("\n✅ Eski 'oda_tipi' kolonu bulunamadı, migration gerekli değil")
                print("   Tablo zaten oda_tipi_id kullanıyor")
        
        except Exception as e:
            print(f"\n❌ Migration hatası: {e}")
            db.session.rollback()
            raise
        
        print("\n" + "=" * 80)
        print("MİGRASYON TAMAMLANDI")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"Oda tipi satış fiyatları migration hatası: {e}")
        db.session.rollback()
        return False


if __name__ == '__main__':
    from app import app
    
    with app.app_context():
        migrate_oda_tipi_satis_fiyatlari()
