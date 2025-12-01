"""İlk stok yükleme özelliği için otel tablosuna alan ekleme

Revision ID: 20251201_ilk_stok
Revises: 20251201_email_sistemi
Create Date: 2025-12-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251201_ilk_stok'
down_revision = '20251201_email_sistemi'
branch_labels = None
depends_on = None


def upgrade():
    """Otel tablosuna ilk stok yükleme alanları ekle"""
    # İlk stok yüklendi flag'i
    op.add_column('oteller', sa.Column('ilk_stok_yuklendi', sa.Boolean(), nullable=True, server_default='false'))
    
    # İlk stok yükleme tarihi
    op.add_column('oteller', sa.Column('ilk_stok_yukleme_tarihi', sa.DateTime(timezone=True), nullable=True))
    
    # İlk stok yükleyen kullanıcı
    op.add_column('oteller', sa.Column('ilk_stok_yukleyen_id', sa.Integer(), nullable=True))
    
    # Foreign key constraint
    op.create_foreign_key(
        'fk_oteller_ilk_stok_yukleyen',
        'oteller', 'kullanicilar',
        ['ilk_stok_yukleyen_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    """Eklenen alanları kaldır"""
    op.drop_constraint('fk_oteller_ilk_stok_yukleyen', 'oteller', type_='foreignkey')
    op.drop_column('oteller', 'ilk_stok_yukleyen_id')
    op.drop_column('oteller', 'ilk_stok_yukleme_tarihi')
    op.drop_column('oteller', 'ilk_stok_yuklendi')
