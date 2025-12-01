"""Departures desteği ve görev önceliklendirme sistemi

Revision ID: 20251201_departures
Revises: 
Create Date: 2024-12-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251201_departures'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Departures dosya desteği ve görev önceliklendirme sistemi için gerekli değişiklikler:
    
    1. misafir_kayit_tipi enum'una 'departure' değeri eklendi
    2. misafir_kayitlari tablosuna cikis_saati kolonu eklendi
    3. gorev_tipi_enum'a 'departure_kontrol' değeri eklendi
    4. gorev_detaylari tablosuna cikis_saati ve oncelik_sirasi kolonları eklendi
    """
    
    # 1. MisafirKayitTipi enum'una departure değeri ekle
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'departure' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'misafir_kayit_tipi')
            ) THEN
                ALTER TYPE misafir_kayit_tipi ADD VALUE 'departure';
            END IF;
        END$$;
    """)
    
    # 2. MisafirKayit tablosuna cikis_saati kolonu ekle
    op.execute("""
        ALTER TABLE misafir_kayitlari 
        ADD COLUMN IF NOT EXISTS cikis_saati TIME;
    """)
    
    # 3. GorevTipi enum'una departure_kontrol değeri ekle
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'departure_kontrol' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'gorev_tipi_enum')
            ) THEN
                ALTER TYPE gorev_tipi_enum ADD VALUE 'departure_kontrol';
            END IF;
        END$$;
    """)
    
    # 4. GorevDetay tablosuna cikis_saati ve oncelik_sirasi kolonları ekle
    op.execute("""
        ALTER TABLE gorev_detaylari 
        ADD COLUMN IF NOT EXISTS cikis_saati TIME;
    """)
    
    op.execute("""
        ALTER TABLE gorev_detaylari 
        ADD COLUMN IF NOT EXISTS oncelik_sirasi INTEGER DEFAULT 0;
    """)
    
    # 5. Öncelik sırası için index ekle
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gorev_detay_oncelik 
        ON gorev_detaylari (oncelik_sirasi);
    """)


def downgrade():
    """Geri alma işlemleri"""
    # Index'i kaldır
    op.execute("DROP INDEX IF EXISTS idx_gorev_detay_oncelik;")
    
    # Kolonları kaldır
    op.execute("ALTER TABLE gorev_detaylari DROP COLUMN IF EXISTS oncelik_sirasi;")
    op.execute("ALTER TABLE gorev_detaylari DROP COLUMN IF EXISTS cikis_saati;")
    op.execute("ALTER TABLE misafir_kayitlari DROP COLUMN IF EXISTS cikis_saati;")
    
    # NOT: PostgreSQL'de enum değerleri DROP edilemez, sadece yeni değerler eklenebilir
