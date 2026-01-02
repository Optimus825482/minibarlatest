"""Oda kontrol kayıtları tablosu

Revision ID: oda_kontrol_kaydi
Revises: gorevlendirme_001
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = 'oda_kontrol_kaydi'
down_revision = 'gorevlendirme_001'
branch_labels = None
depends_on = None


def upgrade():
    """Oda kontrol kayıtları tablosunu oluştur"""
    op.create_table(
        'oda_kontrol_kayitlari',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('oda_id', sa.Integer(), sa.ForeignKey('odalar.id', ondelete='CASCADE'), nullable=False),
        sa.Column('personel_id', sa.Integer(), sa.ForeignKey('kullanicilar.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kontrol_tarihi', sa.Date(), nullable=False),
        sa.Column('baslangic_zamani', sa.DateTime(timezone=True), nullable=False),
        sa.Column('bitis_zamani', sa.DateTime(timezone=True), nullable=True),
        sa.Column('kontrol_tipi', sa.String(20), default='sarfiyat_yok', nullable=False),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), default=datetime.utcnow, nullable=False),
    )
    
    # İndeksler
    op.create_index('idx_oda_kontrol_oda_tarih', 'oda_kontrol_kayitlari', ['oda_id', 'kontrol_tarihi'])
    op.create_index('idx_oda_kontrol_personel_tarih', 'oda_kontrol_kayitlari', ['personel_id', 'kontrol_tarihi'])
    op.create_index('idx_oda_kontrol_bitis', 'oda_kontrol_kayitlari', ['bitis_zamani'])


def downgrade():
    """Tabloyu kaldır"""
    op.drop_index('idx_oda_kontrol_bitis', 'oda_kontrol_kayitlari')
    op.drop_index('idx_oda_kontrol_personel_tarih', 'oda_kontrol_kayitlari')
    op.drop_index('idx_oda_kontrol_oda_tarih', 'oda_kontrol_kayitlari')
    op.drop_table('oda_kontrol_kayitlari')
