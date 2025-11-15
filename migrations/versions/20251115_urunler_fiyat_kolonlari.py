"""Urunler tablosuna fiyatlandirma kolonlari eklendi

Revision ID: 20251115_fiyat
Revises: 646cb7ed296e
Create Date: 2025-11-15 08:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251115_fiyat'
down_revision = '646cb7ed296e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Urunler tablosuna fiyatlandırma kolonları ekle
    op.add_column('urunler', sa.Column('satis_fiyati', sa.Numeric(precision=10, scale=2), nullable=True, comment='Satış fiyatı'))
    op.add_column('urunler', sa.Column('alis_fiyati', sa.Numeric(precision=10, scale=2), nullable=True, comment='Alış fiyatı'))
    op.add_column('urunler', sa.Column('kar_tutari', sa.Numeric(precision=10, scale=2), nullable=True, comment='Kar tutarı'))
    op.add_column('urunler', sa.Column('kar_orani', sa.Numeric(precision=5, scale=2), nullable=True, comment='Kar oranı (%)'))


def downgrade() -> None:
    # Kolonları geri al
    op.drop_column('urunler', 'kar_orani')
    op.drop_column('urunler', 'kar_tutari')
    op.drop_column('urunler', 'alis_fiyati')
    op.drop_column('urunler', 'satis_fiyati')
