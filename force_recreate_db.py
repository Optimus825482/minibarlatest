"""
Veritabanını ZORLA yeniden oluştur
Tüm objeleri (tablolar, indeksler, sequence'ler) temizle
"""

import psycopg2
from app import app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_recreate():
    """Veritabanını zorla temizle ve yeniden oluştur"""
    try:
        # .env'den DB bilgilerini al
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        db_url = os.getenv('DATABASE_URL')
        
        # PostgreSQL bağlantısı
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        logger.info("🗑️  Tüm veritabanı objeleri temizleniyor...")
        
        # 1. Tüm tabloları CASCADE ile sil
        cursor.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """)
        logger.info("   ✓ Tüm tablolar silindi")
        
        # 2. Tüm sequence'leri sil
        cursor.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP
                    EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(r.sequence_name) || ' CASCADE';
                END LOOP;
            END $$;
        """)
        logger.info("   ✓ Tüm sequence'ler silindi")
        
        # 3. Tüm view'ları sil
        cursor.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT table_name FROM information_schema.views WHERE table_schema = 'public') LOOP
                    EXECUTE 'DROP VIEW IF EXISTS ' || quote_ident(r.table_name) || ' CASCADE';
                END LOOP;
            END $$;
        """)
        logger.info("   ✓ Tüm view'lar silindi")
        
        # 4. Tüm function'ları sil
        cursor.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT routine_name FROM information_schema.routines WHERE routine_schema = 'public') LOOP
                    EXECUTE 'DROP FUNCTION IF EXISTS ' || quote_ident(r.routine_name) || ' CASCADE';
                END LOOP;
            END $$;
        """)
        logger.info("   ✓ Tüm function'lar silindi")
        
        # 5. Tüm type'ları sil
        cursor.execute("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT typname FROM pg_type WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public') AND typtype = 'e') LOOP
                    EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
                END LOOP;
            END $$;
        """)
        logger.info("   ✓ Tüm enum type'lar silindi")
        
        cursor.close()
        conn.close()
        
        logger.info("✅ Veritabanı tamamen temizlendi!")
        
        # Şimdi SQLAlchemy ile yeniden oluştur
        logger.info("🔨 Yeni tablolar oluşturuluyor...")
        
        from models import db
        with app.app_context():
            db.create_all()
            logger.info("✅ Tüm tablolar oluşturuldu!")
            
            # Tablo sayısını kontrol et
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            table_names = inspector.get_table_names()
            
            logger.info(f"📊 Toplam {len(table_names)} tablo oluşturuldu:")
            for table in sorted(table_names):
                logger.info(f"   ✓ {table}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Hata: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🏨 OTEL MİNİBAR TAKİP SİSTEMİ")
    print("   VERİTABANI ZORLA YENİDEN OLUŞTURMA")
    print("=" * 60)
    print()
    print("⚠️  UYARI: Bu işlem TÜM VERİLERİ SİLECEK!")
    print("   Tüm tablolar, indeksler, sequence'ler temizlenecek!")
    print()
    
    confirm = input("Devam etmek istiyor musun? (EVET yazarak onayla): ")
    
    if confirm.strip().upper() == "EVET":
        print()
        success = force_recreate()
        
        if success:
            print()
            print("=" * 60)
            print("✅ İşlem tamamlandı!")
            print("=" * 60)
        else:
            print()
            print("=" * 60)
            print("❌ İşlem başarısız!")
            print("=" * 60)
    else:
        print()
        print("❌ İşlem iptal edildi.")
