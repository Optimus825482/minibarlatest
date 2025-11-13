"""
Satın Alma İşlem Tabloları Migration
Direkt satın alma işlemleri için yeni tablolar ekler
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from models import db
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Yeni tabloları oluştur"""
    try:
        # Satın Alma İşlem Tablosu
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS satin_alma_islemler (
                id SERIAL PRIMARY KEY,
                islem_no VARCHAR(50) UNIQUE NOT NULL,
                tedarikci_id INTEGER NOT NULL REFERENCES tedarikciler(id) ON DELETE RESTRICT,
                otel_id INTEGER NOT NULL REFERENCES oteller(id) ON DELETE CASCADE,
                fatura_no VARCHAR(100),
                fatura_tarihi DATE,
                odeme_sekli VARCHAR(50),
                odeme_durumu VARCHAR(20) DEFAULT 'odenmedi' NOT NULL,
                toplam_tutar NUMERIC(12, 2) DEFAULT 0 NOT NULL,
                kdv_tutari NUMERIC(12, 2) DEFAULT 0 NOT NULL,
                genel_toplam NUMERIC(12, 2) DEFAULT 0 NOT NULL,
                aciklama TEXT,
                olusturan_id INTEGER REFERENCES kullanicilar(id) ON DELETE SET NULL,
                islem_tarihi TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                olusturma_tarihi TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                guncelleme_tarihi TIMESTAMP WITH TIME ZONE
            );
        """))
        
        # İndeksler
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_satin_alma_islem_tarih ON satin_alma_islemler(islem_tarihi);
            CREATE INDEX IF NOT EXISTS idx_satin_alma_tedarikci ON satin_alma_islemler(tedarikci_id);
            CREATE INDEX IF NOT EXISTS idx_satin_alma_otel ON satin_alma_islemler(otel_id);
            CREATE INDEX IF NOT EXISTS idx_satin_alma_islem_no ON satin_alma_islemler(islem_no);
        """))
        
        # Satın Alma İşlem Detay Tablosu
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS satin_alma_islem_detaylari (
                id SERIAL PRIMARY KEY,
                islem_id INTEGER NOT NULL REFERENCES satin_alma_islemler(id) ON DELETE CASCADE,
                urun_id INTEGER NOT NULL REFERENCES urunler(id) ON DELETE RESTRICT,
                miktar INTEGER NOT NULL CHECK (miktar > 0),
                birim_fiyat NUMERIC(10, 2) NOT NULL CHECK (birim_fiyat >= 0),
                kdv_orani NUMERIC(5, 2) DEFAULT 0 NOT NULL,
                kdv_tutari NUMERIC(10, 2) DEFAULT 0 NOT NULL,
                toplam_fiyat NUMERIC(12, 2) NOT NULL,
                stok_hareket_id INTEGER REFERENCES stok_hareketleri(id) ON DELETE SET NULL,
                olusturma_tarihi TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
            );
        """))
        
        # İndeksler
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_satin_alma_detay_islem ON satin_alma_islem_detaylari(islem_id);
            CREATE INDEX IF NOT EXISTS idx_satin_alma_detay_urun ON satin_alma_islem_detaylari(urun_id);
        """))
        
        db.session.commit()
        logger.info("✅ Satın alma işlem tabloları başarıyla oluşturuldu")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Migration hatası: {str(e)}")
        raise

def downgrade():
    """Tabloları kaldır"""
    try:
        db.session.execute(text("DROP TABLE IF EXISTS satin_alma_islem_detaylari CASCADE;"))
        db.session.execute(text("DROP TABLE IF EXISTS satin_alma_islemler CASCADE;"))
        db.session.commit()
        logger.info("✅ Satın alma işlem tabloları başarıyla kaldırıldı")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Downgrade hatası: {str(e)}")
        raise

if __name__ == '__main__':
    from app import app
    
    with app.app_context():
        print("🔄 Satın Alma İşlem Tabloları Migration Başlatılıyor...")
        print("-" * 60)
        
        try:
            upgrade()
            print("✅ Migration başarıyla tamamlandı!")
        except Exception as e:
            print(f"❌ Migration başarısız: {str(e)}")
