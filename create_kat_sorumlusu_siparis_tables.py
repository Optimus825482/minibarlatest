"""
Kat Sorumlusu Sipariş Talepleri Tabloları Oluşturma
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

def create_tables():
    """Tabloları oluştur"""
    with app.app_context():
        try:
            # Ana tablo
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS kat_sorumlusu_siparis_talepleri (
                    id SERIAL PRIMARY KEY,
                    talep_no VARCHAR(50) UNIQUE NOT NULL,
                    kat_sorumlusu_id INTEGER NOT NULL REFERENCES kullanicilar(id) ON DELETE CASCADE,
                    depo_sorumlusu_id INTEGER REFERENCES kullanicilar(id) ON DELETE SET NULL,
                    talep_tarihi TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    onay_tarihi TIMESTAMP WITH TIME ZONE,
                    teslim_tarihi TIMESTAMP WITH TIME ZONE,
                    durum VARCHAR(20) DEFAULT 'beklemede' NOT NULL,
                    aciklama TEXT,
                    red_nedeni TEXT,
                    olusturma_tarihi TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    guncelleme_tarihi TIMESTAMP WITH TIME ZONE
                );
            """))
            
            # Detay tablosu
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS kat_sorumlusu_siparis_talep_detaylari (
                    id SERIAL PRIMARY KEY,
                    talep_id INTEGER NOT NULL REFERENCES kat_sorumlusu_siparis_talepleri(id) ON DELETE CASCADE,
                    urun_id INTEGER NOT NULL REFERENCES urunler(id) ON DELETE RESTRICT,
                    talep_miktari INTEGER NOT NULL CHECK (talep_miktari > 0),
                    onaylanan_miktar INTEGER DEFAULT 0 NOT NULL CHECK (onaylanan_miktar >= 0),
                    teslim_edilen_miktar INTEGER DEFAULT 0 NOT NULL CHECK (teslim_edilen_miktar >= 0),
                    aciliyet VARCHAR(10) DEFAULT 'normal' NOT NULL,
                    olusturma_tarihi TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    CONSTRAINT check_teslim_onay_limit CHECK (teslim_edilen_miktar <= onaylanan_miktar)
                );
            """))
            
            # İndeksler
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_talep_durum_tarih 
                ON kat_sorumlusu_siparis_talepleri(durum, talep_tarihi);
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_talep_kat_sorumlusu 
                ON kat_sorumlusu_siparis_talepleri(kat_sorumlusu_id);
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_talep_depo_sorumlusu 
                ON kat_sorumlusu_siparis_talepleri(depo_sorumlusu_id);
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_talep_no 
                ON kat_sorumlusu_siparis_talepleri(talep_no);
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_talep_detay_talep 
                ON kat_sorumlusu_siparis_talep_detaylari(talep_id);
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_talep_detay_urun 
                ON kat_sorumlusu_siparis_talep_detaylari(urun_id);
            """))
            
            db.session.commit()
            
            print("✅ Kat sorumlusu sipariş talepleri tabloları oluşturuldu")
            print("✅ İndeksler oluşturuldu")
            
            # Tablo kontrolü
            result = db.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('kat_sorumlusu_siparis_talepleri', 'kat_sorumlusu_siparis_talep_detaylari')
                ORDER BY table_name;
            """))
            
            tables = [row[0] for row in result]
            print(f"\n📋 Oluşturulan tablolar: {', '.join(tables)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Hata: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("Kat Sorumlusu Sipariş Talepleri Tabloları Oluşturma")
    print("=" * 60)
    create_tables()
