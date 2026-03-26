"""
Migration: QR Kod Sistemi Ekleme
Tarih: 2025-01-06
Açıklama: Oda tablosuna QR kod alanları ekleme ve yeni tablolar oluşturma
"""

import sys
import os

# Proje kök dizinini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

def upgrade():
    """Migration'ı uygula"""
    with app.app_context():
        try:
            print("🔄 Migration başlatılıyor...")
            
            # 1. Oda tablosuna yeni kolonlar ekle
            print("📝 Oda tablosuna QR kod alanları ekleniyor...")
            
            with db.engine.connect() as conn:
                # QR kod token
                conn.execute(text("""
                    ALTER TABLE odalar 
                    ADD COLUMN qr_kod_token VARCHAR(64) NULL UNIQUE
                """))
                conn.commit()
                print("  ✅ qr_kod_token eklendi")
                
                # QR kod görsel
                conn.execute(text("""
                    ALTER TABLE odalar 
                    ADD COLUMN qr_kod_gorsel TEXT NULL
                """))
                conn.commit()
                print("  ✅ qr_kod_gorsel eklendi")
                
                # QR kod oluşturma tarihi
                conn.execute(text("""
                    ALTER TABLE odalar 
                    ADD COLUMN qr_kod_olusturma_tarihi DATETIME NULL
                """))
                conn.commit()
                print("  ✅ qr_kod_olusturma_tarihi eklendi")
                
                # Misafir mesajı
                conn.execute(text("""
                    ALTER TABLE odalar 
                    ADD COLUMN misafir_mesaji VARCHAR(500) NULL
                """))
                conn.commit()
                print("  ✅ misafir_mesaji eklendi")
                
                # Index oluştur
                conn.execute(text("""
                    CREATE INDEX idx_qr_token ON odalar(qr_kod_token)
                """))
                conn.commit()
                print("  ✅ idx_qr_token index'i oluşturuldu")
            
            # 2. Yeni tabloları oluştur
            print("\n📝 Yeni tablolar oluşturuluyor...")
            db.create_all()
            print("  ✅ minibar_dolum_talepleri tablosu oluşturuldu")
            print("  ✅ qr_kod_okutma_loglari tablosu oluşturuldu")
            
            print("\n✅ Migration başarıyla tamamlandı!")
            return True
            
        except Exception as e:
            print(f"\n❌ Migration hatası: {str(e)}")
            print("⚠️  Rollback yapılıyor...")
            db.session.rollback()
            return False

def downgrade():
    """Migration'ı geri al"""
    with app.app_context():
        try:
            print("🔄 Rollback başlatılıyor...")
            
            with db.engine.connect() as conn:
                # Tabloları sil
                print("📝 Yeni tablolar siliniyor...")
                conn.execute(text("DROP TABLE IF EXISTS qr_kod_okutma_loglari"))
                conn.commit()
                print("  ✅ qr_kod_okutma_loglari silindi")
                
                conn.execute(text("DROP TABLE IF EXISTS minibar_dolum_talepleri"))
                conn.commit()
                print("  ✅ minibar_dolum_talepleri silindi")
                
                # Index'i sil
                print("\n📝 Index siliniyor...")
                conn.execute(text("DROP INDEX IF EXISTS idx_qr_token ON odalar"))
                conn.commit()
                print("  ✅ idx_qr_token silindi")
                
                # Kolonları sil
                print("\n📝 Oda tablosundan QR alanları siliniyor...")
                conn.execute(text("ALTER TABLE odalar DROP COLUMN misafir_mesaji"))
                conn.commit()
                print("  ✅ misafir_mesaji silindi")
                
                conn.execute(text("ALTER TABLE odalar DROP COLUMN qr_kod_olusturma_tarihi"))
                conn.commit()
                print("  ✅ qr_kod_olusturma_tarihi silindi")
                
                conn.execute(text("ALTER TABLE odalar DROP COLUMN qr_kod_gorsel"))
                conn.commit()
                print("  ✅ qr_kod_gorsel silindi")
                
                conn.execute(text("ALTER TABLE odalar DROP COLUMN qr_kod_token"))
                conn.commit()
                print("  ✅ qr_kod_token silindi")
            
            print("\n✅ Rollback başarıyla tamamlandı!")
            return True
            
        except Exception as e:
            print(f"\n❌ Rollback hatası: {str(e)}")
            return False

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()
