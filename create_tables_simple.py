"""Kat Sorumlusu Sipariş Tabloları - Basit Oluşturma"""
import psycopg2
from psycopg2 import sql

# Veritabanı bağlantısı
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="minibar_takip",
    user="postgres",
    password="518518Erkan"
)

try:
    cur = conn.cursor()
    
    # Ana tablo
    cur.execute("""
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
    """)
    print("✅ kat_sorumlusu_siparis_talepleri tablosu oluşturuldu")
    
    # Detay tablosu
    cur.execute("""
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
    """)
    print("✅ kat_sorumlusu_siparis_talep_detaylari tablosu oluşturuldu")
    
    # İndeksler
    cur.execute("CREATE INDEX IF NOT EXISTS idx_talep_durum_tarih ON kat_sorumlusu_siparis_talepleri(durum, talep_tarihi);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_talep_kat_sorumlusu ON kat_sorumlusu_siparis_talepleri(kat_sorumlusu_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_talep_depo_sorumlusu ON kat_sorumlusu_siparis_talepleri(depo_sorumlusu_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_talep_no ON kat_sorumlusu_siparis_talepleri(talep_no);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_talep_detay_talep ON kat_sorumlusu_siparis_talep_detaylari(talep_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_talep_detay_urun ON kat_sorumlusu_siparis_talep_detaylari(urun_id);")
    print("✅ İndeksler oluşturuldu")
    
    conn.commit()
    
    # Kontrol
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('kat_sorumlusu_siparis_talepleri', 'kat_sorumlusu_siparis_talep_detaylari')
        ORDER BY table_name;
    """)
    
    tables = cur.fetchall()
    print(f"\n📋 Oluşturulan tablolar:")
    for table in tables:
        print(f"   - {table[0]}")
    
    print("\n✅ Tüm işlemler başarılı!")
    
except Exception as e:
    print(f"❌ Hata: {e}")
    conn.rollback()
finally:
    cur.close()
    conn.close()
