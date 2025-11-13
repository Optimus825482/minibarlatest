"""
Veritabanı Yeniden Oluşturma Script'i
models.py'deki tüm modellere göre tabloları sıfırdan oluşturur
"""

from app import app, db
from models import *
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def recreate_database():
    """Tüm tabloları sil ve yeniden oluştur"""
    try:
        with app.app_context():
            logger.info("🗑️  Mevcut tablolar ve indeksler siliniyor...")
            
            # Önce tüm indeksleri manuel olarak sil
            from sqlalchemy import text
            try:
                # PostgreSQL için TÜM indeksleri bul ve sil (tüm schema'lardan)
                result = db.session.execute(text("""
                    SELECT schemaname, indexname 
                    FROM pg_indexes 
                    WHERE indexname NOT LIKE 'pg_%'
                    AND indexname NOT LIKE '%_pkey'
                    AND indexname NOT LIKE '%_fkey'
                """))
                
                indexes = [(row[0], row[1]) for row in result]
                logger.info(f"   Silinecek {len(indexes)} indeks bulundu")
                
                for schema, index_name in indexes:
                    try:
                        db.session.execute(text(f'DROP INDEX IF EXISTS {schema}."{index_name}" CASCADE'))
                        logger.info(f"   ✓ İndeks silindi: {schema}.{index_name}")
                    except Exception as e:
                        logger.warning(f"   ⚠ İndeks silinemedi: {schema}.{index_name} - {e}")
                
                db.session.commit()
            except Exception as e:
                logger.warning(f"   ⚠ İndeks temizleme hatası: {e}")
                db.session.rollback()
            
            # Şimdi tabloları sil
            db.drop_all()
            logger.info("✅ Tüm tablolar silindi")
            
            logger.info("🔨 Yeni tablolar oluşturuluyor...")
            db.create_all()
            logger.info("✅ Tüm tablolar oluşturuldu")
            
            # Tablo sayısını kontrol et
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            table_names = inspector.get_table_names()
            
            logger.info(f"📊 Toplam {len(table_names)} tablo oluşturuldu:")
            for table in sorted(table_names):
                logger.info(f"   ✓ {table}")
            
            logger.info("\n🎉 Veritabanı başarıyla yeniden oluşturuldu!")
            logger.info("📝 Şimdi gerekli verileri ekleyebilirsin.")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Hata oluştu: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("🏨 OTEL MİNİBAR TAKİP SİSTEMİ")
    print("   VERİTABANI YENİDEN OLUŞTURMA")
    print("=" * 60)
    print()
    print("⚠️  UYARI: Bu işlem TÜM VERİLERİ SİLECEK!")
    print()
    
    confirm = input("Devam etmek istiyor musun? (EVET yazarak onayla): ")
    
    if confirm.strip().upper() == "EVET":
        print()
        success = recreate_database()
        
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
