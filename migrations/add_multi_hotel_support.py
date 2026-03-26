"""
Çoklu Otel Desteği Migration Script
- KullaniciOtel ara tablosu oluşturur
- Kullanici tablosuna otel_id alanı ekler
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

# revision identifiers
revision = 'multi_hotel_support_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade database schema"""
    try:
        # 1. KullaniciOtel ara tablosu oluştur
        op.create_table(
            'kullanici_otel',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('kullanici_id', sa.Integer(), nullable=False),
            sa.Column('otel_id', sa.Integer(), nullable=False),
            sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), 
                     default=lambda: datetime.now(timezone.utc), nullable=True),
            sa.ForeignKeyConstraint(['kullanici_id'], ['kullanicilar.id'], 
                                   name='fk_kullanici_otel_kullanici', ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['otel_id'], ['oteller.id'], 
                                   name='fk_kullanici_otel_otel', ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('kullanici_id', 'otel_id', name='uq_kullanici_otel')
        )
        
        # Index oluştur
        op.create_index('idx_kullanici_otel', 'kullanici_otel', 
                       ['kullanici_id', 'otel_id'], unique=False)
        
        print("✅ kullanici_otel tablosu oluşturuldu")
        
        # 2. Kullanici tablosuna otel_id alanı ekle
        op.add_column('kullanicilar', 
                     sa.Column('otel_id', sa.Integer(), nullable=True))
        
        # Foreign key constraint ekle
        op.create_foreign_key(
            'fk_kullanici_otel',
            'kullanicilar', 'oteller',
            ['otel_id'], ['id'],
            ondelete='SET NULL'
        )
        
        print("✅ kullanicilar tablosuna otel_id alanı eklendi")
        
    except Exception as e:
        print(f"❌ Migration hatası: {str(e)}")
        raise


def downgrade():
    """Downgrade database schema"""
    try:
        # 1. Kullanici tablosundan otel_id alanını kaldır
        op.drop_constraint('fk_kullanici_otel', 'kullanicilar', type_='foreignkey')
        op.drop_column('kullanicilar', 'otel_id')
        
        print("✅ kullanicilar tablosundan otel_id alanı kaldırıldı")
        
        # 2. KullaniciOtel tablosunu sil
        op.drop_index('idx_kullanici_otel', table_name='kullanici_otel')
        op.drop_table('kullanici_otel')
        
        print("✅ kullanici_otel tablosu silindi")
        
    except Exception as e:
        print(f"❌ Rollback hatası: {str(e)}")
        raise
