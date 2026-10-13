"""minibar dolum talebi detay tablosu

Revision ID: dolum_talebi_detay
Revises: 20251115_fiyat
Create Date: 2026-07-24

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = 'dolum_talebi_detay'
down_revision = '20251115_fiyat'
branch_labels = None
depends_on = None


def upgrade():
    """Misafir dolum talebi seçili ürünler detay tablosu"""
    op.create_table(
        'minibar_dolum_talebi_detay',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('talep_id', sa.Integer(), sa.ForeignKey('minibar_dolum_talepleri.id', ondelete='CASCADE'), nullable=False),
        sa.Column('urun_id', sa.Integer(), sa.ForeignKey('urunler.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), default=datetime.utcnow, nullable=False),
    )

    # İndeksler
    op.create_index('idx_dolum_talebi_detay_talep', 'minibar_dolum_talebi_detay', ['talep_id'])
    op.create_index('idx_dolum_talebi_detay_urun', 'minibar_dolum_talebi_detay', ['urun_id'])


def downgrade():
    """Tabloyu kaldır"""
    op.drop_index('idx_dolum_talebi_detay_urun', 'minibar_dolum_talebi_detay')
    op.drop_index('idx_dolum_talebi_detay_talep', 'minibar_dolum_talebi_detay')
    op.drop_table('minibar_dolum_talebi_detay')
