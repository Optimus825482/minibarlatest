"""Add multi-hotel support

Revision ID: 20251108_083857
Revises: 
Create Date: 2025-11-08 08:38:57

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251108_083857'
down_revision = None
depends_on = None


def upgrade():
    """
    Çoklu otel desteği için gerekli değişiklikleri uygula
    """
    # 1. KullaniciOtel ara tablosunu oluştur
    op.create_table(
        'kullanici_otel',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('kullanici_id', sa.Integer(), nullable=False),
        sa.Column('otel_id', sa.Integer(), nullable=False),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['kullanici_id'], ['kullanicilar.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['otel_id'], ['oteller.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('kullanici_id', 'otel_id', name='uq_kullanici_otel')
    )
    
    # Index ekle
    op.create_index('idx_kullanici_otel', 'kullanici_otel', ['kullanici_id', 'otel_id'])
    
    # 2. Kullanicilar tablosuna otel_id kolonu ekle
    op.add_column('kullanicilar', sa.Column('otel_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_kullanicilar_otel_id', 
        'kullanicilar', 
        'oteller',
        ['otel_id'], 
        ['id'],
        ondelete='SET NULL'
    )
    
    print("✅ Multi-hotel support migration completed successfully!")


def downgrade():
    """
    Migration'ı geri al
    """
    # Kullanicilar tablosundan otel_id kolonunu kaldır
    op.drop_constraint('fk_kullanicilar_otel_id', 'kullanicilar', type_='foreignkey')
    op.drop_column('kullanicilar', 'otel_id')
    
    # KullaniciOtel tablosunu sil
    op.drop_index('idx_kullanici_otel', table_name='kullanici_otel')
    op.drop_table('kullanici_otel')
    
    print("✅ Multi-hotel support migration rolled back successfully!")
