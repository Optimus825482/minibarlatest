"""
Oda Tipi String Kolonlarını Temizleme Migration

Bu script:
1. oda_tipi_satis_fiyatlari tablosuna oda_tipi_id ekler
2. tuketim_kalibi tablosuna oda_tipi_id ekler
3. Verileri map eder
4. Eski oda_tipi string kolonlarını kaldırır
5. odalar.oda_tipi kolonunu kaldırır
"""

import sys
sys.path.insert(0, '.')

from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        print("=" * 60)
        print("ODA TİPİ STRING KOLONLARINI TEMİZLEME")
        print("=" * 60)
        
        # 1. oda_tipi_satis_fiyatlari tablosunu güncelle
        print("\n1. oda_tipi_satis_fiyatlari tablosu güncelleniyor...")
        try:
            # Kolon ekle
            db.session.execute(text('ALTER TABLE oda_tipi_satis_fiyatlari ADD COLUMN IF NOT EXISTS oda_tipi_id INTEGER'))
            db.session.commit()
            
            # Foreign key ekle
            try:
                db.session.execute(text('ALTER TABLE oda_tipi_satis_fiyatlari ADD CONSTRAINT fk_oda_tipi_satis_fiyatlari_oda_tipi FOREIGN KEY (oda_tipi_id) REFERENCES oda_tipleri(id)'))
                db.session.commit()
            except:
                db.session.rollback()
            
            # Mapping
            mapping = {
                'STANDARD': 9,
                'JUNIOR SUITE': 10,
                'QUEEN SUITE': 11,
                'KING SUITE': 12
            }
            
            for oda_tipi_str, oda_tipi_id in mapping.items():
                result = db.session.execute(
                    text('UPDATE oda_tipi_satis_fiyatlari SET oda_tipi_id = :oda_tipi_id WHERE oda_tipi = :oda_tipi'),
                    {'oda_tipi_id': oda_tipi_id, 'oda_tipi': oda_tipi_str}
                )
                if result.rowcount > 0:
                    print(f"  ✅ {result.rowcount} fiyat kaydı güncellendi: {oda_tipi_str} -> ID {oda_tipi_id}")
            
            db.session.commit()
            print("  ✅ oda_tipi_satis_fiyatlari güncellendi")
        except Exception as e:
            print(f"  ⚠️ Hata: {e}")
            db.session.rollback()
        
        # 2. tuketim_kalibi tablosunu güncelle
        print("\n2. tuketim_kalibi tablosu güncelleniyor...")
        try:
            # Kolon ekle
            db.session.execute(text('ALTER TABLE tuketim_kalibi ADD COLUMN IF NOT EXISTS oda_tipi_id INTEGER'))
            db.session.commit()
            
            # Foreign key ekle
            try:
                db.session.execute(text('ALTER TABLE tuketim_kalibi ADD CONSTRAINT fk_tuketim_kalibi_oda_tipi FOREIGN KEY (oda_tipi_id) REFERENCES oda_tipleri(id)'))
                db.session.commit()
            except:
                db.session.rollback()
            
            # Mapping
            for oda_tipi_str, oda_tipi_id in mapping.items():
                result = db.session.execute(
                    text('UPDATE tuketim_kalibi SET oda_tipi_id = :oda_tipi_id WHERE oda_tipi = :oda_tipi'),
                    {'oda_tipi_id': oda_tipi_id, 'oda_tipi': oda_tipi_str}
                )
                if result.rowcount > 0:
                    print(f"  ✅ {result.rowcount} kalıp kaydı güncellendi: {oda_tipi_str} -> ID {oda_tipi_id}")
            
            db.session.commit()
            print("  ✅ tuketim_kalibi güncellendi")
        except Exception as e:
            print(f"  ⚠️ Hata: {e}")
            db.session.rollback()
        
        # 3. Eski kolonları kaldır
        print("\n3. Eski oda_tipi string kolonları kaldırılıyor...")
        
        # 3a. oda_tipi_satis_fiyatlari.oda_tipi
        try:
            db.session.execute(text('ALTER TABLE oda_tipi_satis_fiyatlari DROP COLUMN IF EXISTS oda_tipi'))
            db.session.commit()
            print("  ✅ oda_tipi_satis_fiyatlari.oda_tipi kaldırıldı")
        except Exception as e:
            print(f"  ⚠️ Hata: {e}")
            db.session.rollback()
        
        # 3b. tuketim_kalibi.oda_tipi
        try:
            db.session.execute(text('ALTER TABLE tuketim_kalibi DROP COLUMN IF EXISTS oda_tipi'))
            db.session.commit()
            print("  ✅ tuketim_kalibi.oda_tipi kaldırıldı")
        except Exception as e:
            print(f"  ⚠️ Hata: {e}")
            db.session.rollback()
        
        # 3c. odalar.oda_tipi
        try:
            db.session.execute(text('ALTER TABLE odalar DROP COLUMN IF EXISTS oda_tipi'))
            db.session.commit()
            print("  ✅ odalar.oda_tipi kaldırıldı")
        except Exception as e:
            print(f"  ⚠️ Hata: {e}")
            db.session.rollback()
        
        # 4. Kontrol
        print("\n4. Kontrol ediliyor...")
        
        # Odalar
        result = db.session.execute(text('SELECT oda_tipi_id, COUNT(*) FROM odalar GROUP BY oda_tipi_id ORDER BY oda_tipi_id'))
        print("\n  Odalar:")
        for row in result:
            oda_tipi_id = row[0] if row[0] else 'NULL'
            print(f"    Oda Tipi ID {oda_tipi_id}: {row[1]} oda")
        
        # Satış Fiyatları
        result = db.session.execute(text('SELECT oda_tipi_id, COUNT(*) FROM oda_tipi_satis_fiyatlari GROUP BY oda_tipi_id ORDER BY oda_tipi_id'))
        print("\n  Satış Fiyatları:")
        for row in result:
            oda_tipi_id = row[0] if row[0] else 'NULL'
            print(f"    Oda Tipi ID {oda_tipi_id}: {row[1]} fiyat")
        
        # Tüketim Kalıpları
        result = db.session.execute(text('SELECT oda_tipi_id, COUNT(*) FROM tuketim_kalibi GROUP BY oda_tipi_id ORDER BY oda_tipi_id'))
        print("\n  Tüketim Kalıpları:")
        for row in result:
            oda_tipi_id = row[0] if row[0] else 'NULL'
            print(f"    Oda Tipi ID {oda_tipi_id}: {row[1]} kalıp")
        
        print("\n" + "=" * 60)
        print("✅ MİGRATION TAMAMLANDI!")
        print("=" * 60)

if __name__ == '__main__':
    migrate()
