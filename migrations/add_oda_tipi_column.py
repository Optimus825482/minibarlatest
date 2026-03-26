# -*- coding: utf-8 -*-
"""
Oda Tipi Sütunu Ekleme Migration
Odalar tablosuna oda_tipi sütununu ekler ve mevcut değeri 50'den 100 karaktere çıkarır
"""

import os
import sys

# Proje kök dizinini Python path'ine ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from sqlalchemy import text

def upgrade():
    """Migration'ı uygula"""
    print("🔄 Oda tipi sütunu migration başlatılıyor...")
    
    with app.app_context():
        try:
            # Veritabanı tipini kontrol et
            db_type = os.getenv('DB_TYPE', 'mysql')
            
            if db_type == 'postgresql':
                # PostgreSQL için
                print("📊 PostgreSQL veritabanı tespit edildi")
                
                # Sütun var mı kontrol et
                check_query = text("""
                    SELECT column_name, character_maximum_length 
                    FROM information_schema.columns 
                    WHERE table_name = 'odalar' AND column_name = 'oda_tipi'
                """)
                
                result = db.session.execute(check_query).fetchone()
                
                if result:
                    current_length = result[1]
                    print(f"✅ oda_tipi sütunu mevcut (Mevcut uzunluk: {current_length})")
                    
                    if current_length < 100:
                        # Sütun uzunluğunu artır
                        alter_query = text("""
                            ALTER TABLE odalar 
                            ALTER COLUMN oda_tipi TYPE VARCHAR(100)
                        """)
                        db.session.execute(alter_query)
                        db.session.commit()
                        print(f"✅ oda_tipi sütunu {current_length} karakterden 100 karaktere güncellendi")
                    else:
                        print("✅ oda_tipi sütunu zaten 100 karakter veya daha uzun")
                else:
                    # Sütun yoksa ekle
                    alter_query = text("""
                        ALTER TABLE odalar 
                        ADD COLUMN oda_tipi VARCHAR(100)
                    """)
                    db.session.execute(alter_query)
                    db.session.commit()
                    print("✅ oda_tipi sütunu eklendi (100 karakter)")
            
            else:
                # MySQL için
                print("📊 MySQL veritabanı tespit edildi")
                
                # Sütun var mı kontrol et
                check_query = text("""
                    SELECT COLUMN_NAME, CHARACTER_MAXIMUM_LENGTH 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'odalar' 
                    AND COLUMN_NAME = 'oda_tipi'
                """)
                
                result = db.session.execute(check_query).fetchone()
                
                if result:
                    current_length = result[1]
                    print(f"✅ oda_tipi sütunu mevcut (Mevcut uzunluk: {current_length})")
                    
                    if current_length < 100:
                        # Sütun uzunluğunu artır
                        alter_query = text("""
                            ALTER TABLE odalar 
                            MODIFY COLUMN oda_tipi VARCHAR(100)
                        """)
                        db.session.execute(alter_query)
                        db.session.commit()
                        print(f"✅ oda_tipi sütunu {current_length} karakterden 100 karaktere güncellendi")
                    else:
                        print("✅ oda_tipi sütunu zaten 100 karakter veya daha uzun")
                else:
                    # Sütun yoksa ekle
                    alter_query = text("""
                        ALTER TABLE odalar 
                        ADD COLUMN oda_tipi VARCHAR(100)
                    """)
                    db.session.execute(alter_query)
                    db.session.commit()
                    print("✅ oda_tipi sütunu eklendi (100 karakter)")
            
            print("✅ Migration başarıyla tamamlandı!")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration hatası: {str(e)}")
            return False

def downgrade():
    """Migration'ı geri al"""
    print("🔄 Oda tipi sütunu migration geri alınıyor...")
    
    with app.app_context():
        try:
            db_type = os.getenv('DB_TYPE', 'mysql')
            
            if db_type == 'postgresql':
                # PostgreSQL için - sütunu 50 karaktere düşür
                alter_query = text("""
                    ALTER TABLE odalar 
                    ALTER COLUMN oda_tipi TYPE VARCHAR(50)
                """)
            else:
                # MySQL için - sütunu 50 karaktere düşür
                alter_query = text("""
                    ALTER TABLE odalar 
                    MODIFY COLUMN oda_tipi VARCHAR(50)
                """)
            
            db.session.execute(alter_query)
            db.session.commit()
            
            print("✅ Migration geri alındı - oda_tipi sütunu 50 karaktere düşürüldü")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration geri alma hatası: {str(e)}")
            return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Oda tipi sütunu migration')
    parser.add_argument('--downgrade', action='store_true', help='Migration\'ı geri al')
    args = parser.parse_args()
    
    if args.downgrade:
        downgrade()
    else:
        upgrade()
