"""
Migration: Bildirimler Tablosu Ekleme
Tarih: 2025-02-17
Açıklama: Push bildirim sistemi için bildirimler tablosu oluşturma
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
            print("🔄 Bildirimler tablosu migration başlatılıyor...")

            with db.engine.connect() as conn:
                # Tablo zaten var mı kontrol et
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'bildirimler'
                    )
                """))
                exists = result.scalar()

                if exists:
                    print("ℹ️  bildirimler tablosu zaten mevcut.")
                    # Mevcut veri sayısını göster
                    row_count = conn.execute(text("SELECT COUNT(*) FROM bildirimler")).scalar()
                    print(f"   📊 Mevcut kayıt sayısı: {row_count}")
                    print("   ⚠️  Mevcut veriler korunuyor, sadece eksik index'ler kontrol ediliyor...")
                else:
                    # Tabloyu oluştur — sadece yoksa
                    conn.execute(text("""
                        CREATE TABLE bildirimler (
                            id SERIAL PRIMARY KEY,
                            hedef_rol VARCHAR(50) NOT NULL,
                            bildirim_tipi VARCHAR(50) NOT NULL,
                            baslik VARCHAR(255) NOT NULL,
                            mesaj TEXT,
                            hedef_otel_id INTEGER REFERENCES oteller(id) ON DELETE SET NULL,
                            hedef_kullanici_id INTEGER REFERENCES kullanicilar(id) ON DELETE SET NULL,
                            oda_id INTEGER REFERENCES odalar(id) ON DELETE SET NULL,
                            gorev_id INTEGER,
                            gonderen_id INTEGER REFERENCES kullanicilar(id) ON DELETE SET NULL,
                            okundu BOOLEAN DEFAULT FALSE,
                            olusturma_tarihi TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        )
                    """))
                    conn.commit()
                    print("  ✅ bildirimler tablosu oluşturuldu")

                # Index'ler — IF NOT EXISTS ile güvenli
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_bildirimler_hedef_rol ON bildirimler(hedef_rol)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_bildirimler_hedef_kullanici ON bildirimler(hedef_kullanici_id)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_bildirimler_okundu ON bildirimler(okundu)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_bildirimler_olusturma_tarihi ON bildirimler(olusturma_tarihi)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_bildirimler_tip_rol ON bildirimler(bildirim_tipi, hedef_rol)
                """))
                conn.commit()
                print("  ✅ Index'ler kontrol edildi / oluşturuldu")

            print("\n✅ Bildirimler tablosu migration başarıyla tamamlandı!")
            return True

        except Exception as e:
            print(f"\n❌ Migration hatası: {str(e)}")
            db.session.rollback()
            return False


def downgrade():
    """Migration'ı geri al — DİKKAT: Mevcut verileri siler!"""
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                # Önce mevcut veri sayısını kontrol et
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'bildirimler'
                    )
                """))
                if not result.scalar():
                    print("ℹ️  bildirimler tablosu zaten yok.")
                    return True

                row_count = conn.execute(text("SELECT COUNT(*) FROM bildirimler")).scalar()
                
                if row_count > 0:
                    print(f"⚠️  DİKKAT: bildirimler tablosunda {row_count} kayıt var!")
                    confirm = input("Tüm veriler silinecek. Devam etmek istiyor musunuz? (evet/hayir): ")
                    if confirm.lower() != 'evet':
                        print("❌ İşlem iptal edildi. Veriler korundu.")
                        return False

                conn.execute(text("DROP TABLE IF EXISTS bildirimler CASCADE"))
                conn.commit()
            print("✅ bildirimler tablosu silindi")
            return True
        except Exception as e:
            print(f"❌ Downgrade hatası: {str(e)}")
            return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--downgrade', action='store_true')
    args = parser.parse_args()

    if args.downgrade:
        downgrade()
    else:
        upgrade()
