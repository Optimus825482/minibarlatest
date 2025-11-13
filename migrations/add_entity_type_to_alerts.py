"""
Add entity_type column to ml_alerts table
"""

from app import app
from models import db
from sqlalchemy import text

def upgrade():
    """entity_type kolonunu ekle"""
    
    with app.app_context():
        try:
            # entity_type kolonu ekle
            db.session.execute(text("""
                ALTER TABLE ml_alerts 
                ADD COLUMN IF NOT EXISTS entity_type VARCHAR(50);
            """))
            
            # Mevcut kayıtlar için default değer (stok alertleri için 'urun')
            db.session.execute(text("""
                UPDATE ml_alerts 
                SET entity_type = 'urun' 
                WHERE entity_type IS NULL 
                  AND alert_type IN ('stok_anomali', 'stok_bitis_uyari');
            """))
            
            db.session.commit()
            print("✅ entity_type kolonu başarıyla eklendi!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Hata: {str(e)}")
            raise

def downgrade():
    """Kolonu geri al"""
    with app.app_context():
        try:
            db.session.execute(text("ALTER TABLE ml_alerts DROP COLUMN IF EXISTS entity_type;"))
            db.session.commit()
            print("✅ entity_type kolonu silindi")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Hata: {str(e)}")
            raise

if __name__ == '__main__':
    print("entity_type kolonu ekleniyor...")
    upgrade()
