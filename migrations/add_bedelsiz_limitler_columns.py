"""
Migration: bedelsiz_limitler tablosuna eksik kolonları ekle
Erkan için - Database Schema Fix
"""

from app import app, db
from sqlalchemy import text
from datetime import datetime, timezone

def upgrade():
    """Eksik kolonları ekle"""
    with app.app_context():
        try:
            print("\n🔧 bedelsiz_limitler tablosuna kolonlar ekleniyor...")
            
            # 1. aktif kolonu ekle
            db.session.execute(text("""
                ALTER TABLE bedelsiz_limitler 
                ADD COLUMN IF NOT EXISTS aktif BOOLEAN DEFAULT TRUE
            """))
            print("   ✓ aktif kolonu eklendi")
            
            # 2. olusturma_tarihi kolonu ekle
            db.session.execute(text("""
                ALTER TABLE bedelsiz_limitler 
                ADD COLUMN IF NOT EXISTS olusturma_tarihi TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            """))
            print("   ✓ olusturma_tarihi kolonu eklendi")
            
            # 3. Mevcut kayıtları güncelle
            db.session.execute(text("""
                UPDATE bedelsiz_limitler 
                SET aktif = TRUE 
                WHERE aktif IS NULL
            """))
            
            db.session.execute(text("""
                UPDATE bedelsiz_limitler 
                SET olusturma_tarihi = NOW() 
                WHERE olusturma_tarihi IS NULL
            """))
            print("   ✓ Mevcut kayıtlar güncellendi")
            
            db.session.commit()
            print("✅ Migration başarılı!\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration hatası: {e}\n")
            raise

def downgrade():
    """Kolonları kaldır"""
    with app.app_context():
        try:
            print("\n🔧 bedelsiz_limitler tablosundan kolonlar kaldırılıyor...")
            
            db.session.execute(text("""
                ALTER TABLE bedelsiz_limitler 
                DROP COLUMN IF EXISTS aktif
            """))
            
            db.session.execute(text("""
                ALTER TABLE bedelsiz_limitler 
                DROP COLUMN IF EXISTS olusturma_tarihi
            """))
            
            db.session.commit()
            print("✅ Rollback başarılı!\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Rollback hatası: {e}\n")
            raise

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()
