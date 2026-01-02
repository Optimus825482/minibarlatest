"""Bağımsız DND Sistemi - Görev sisteminden ayrı DND kayıtları

Revision ID: bagimsiz_dnd_sistemi
Revises: 20251201_ilk_stok
Create Date: 2026-01-01

Bu migration, DND (Do Not Disturb) kayıtlarını görev sisteminden bağımsız hale getirir.
Artık bir oda için görev atanmamış olsa bile DND kaydı yapılabilir.

Yeni Tablolar:
- oda_dnd_kayitlari: Ana DND kayıtları (günlük bazda)
- oda_dnd_kontrolleri: Her DND kontrolü için detay kayıtları

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = 'bagimsiz_dnd_sistemi'
down_revision = '20251201_ilk_stok'
branch_labels = None
depends_on = None


def upgrade():
    """Bağımsız DND tablolarını oluştur"""
    
    # 1. Ana DND kayıtları tablosu (günlük bazda, oda başına tek kayıt)
    op.create_table(
        'oda_dnd_kayitlari',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('oda_id', sa.Integer(), sa.ForeignKey('odalar.id', ondelete='CASCADE'), nullable=False),
        sa.Column('otel_id', sa.Integer(), sa.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kayit_tarihi', sa.Date(), nullable=False),
        
        # DND durumu
        sa.Column('dnd_sayisi', sa.Integer(), default=0, nullable=False),
        sa.Column('ilk_dnd_zamani', sa.DateTime(timezone=True), nullable=True),
        sa.Column('son_dnd_zamani', sa.DateTime(timezone=True), nullable=True),
        
        # Durum: aktif, tamamlandi (3 kontrol yapıldı), iptal
        sa.Column('durum', sa.String(20), default='aktif', nullable=False),
        
        # Görev entegrasyonu (opsiyonel - varsa bağlanır)
        sa.Column('gorev_detay_id', sa.Integer(), sa.ForeignKey('gorev_detaylari.id', ondelete='SET NULL'), nullable=True),
        
        # Sistem bilgileri
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), default=datetime.utcnow, nullable=False),
        sa.Column('guncelleme_tarihi', sa.DateTime(timezone=True), nullable=True),
    )
    
    # İndeksler
    op.create_index('idx_oda_dnd_oda_tarih', 'oda_dnd_kayitlari', ['oda_id', 'kayit_tarihi'], unique=True)
    op.create_index('idx_oda_dnd_otel_tarih', 'oda_dnd_kayitlari', ['otel_id', 'kayit_tarihi'])
    op.create_index('idx_oda_dnd_durum', 'oda_dnd_kayitlari', ['durum'])
    op.create_index('idx_oda_dnd_gorev', 'oda_dnd_kayitlari', ['gorev_detay_id'])
    
    # 2. DND kontrol detayları tablosu (her kontrol için ayrı kayıt)
    op.create_table(
        'oda_dnd_kontrolleri',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('dnd_kayit_id', sa.Integer(), sa.ForeignKey('oda_dnd_kayitlari.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kontrol_no', sa.Integer(), nullable=False),  # 1, 2, 3...
        sa.Column('kontrol_eden_id', sa.Integer(), sa.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True),
        sa.Column('kontrol_zamani', sa.DateTime(timezone=True), default=datetime.utcnow, nullable=False),
        sa.Column('notlar', sa.Text(), nullable=True),
    )
    
    # İndeksler
    op.create_index('idx_dnd_kontrol_kayit', 'oda_dnd_kontrolleri', ['dnd_kayit_id'])
    op.create_index('idx_dnd_kontrol_zaman', 'oda_dnd_kontrolleri', ['kontrol_zamani'])
    op.create_index('idx_dnd_kontrol_personel', 'oda_dnd_kontrolleri', ['kontrol_eden_id'])


def downgrade():
    """Tabloları kaldır"""
    # Önce kontrol tablosunu kaldır (FK bağımlılığı)
    op.drop_index('idx_dnd_kontrol_personel', 'oda_dnd_kontrolleri')
    op.drop_index('idx_dnd_kontrol_zaman', 'oda_dnd_kontrolleri')
    op.drop_index('idx_dnd_kontrol_kayit', 'oda_dnd_kontrolleri')
    op.drop_table('oda_dnd_kontrolleri')
    
    # Sonra ana tabloyu kaldır
    op.drop_index('idx_oda_dnd_gorev', 'oda_dnd_kayitlari')
    op.drop_index('idx_oda_dnd_durum', 'oda_dnd_kayitlari')
    op.drop_index('idx_oda_dnd_otel_tarih', 'oda_dnd_kayitlari')
    op.drop_index('idx_oda_dnd_oda_tarih', 'oda_dnd_kayitlari')
    op.drop_table('oda_dnd_kayitlari')
