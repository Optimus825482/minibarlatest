"""Email sistemi ve sistem ayarları tabloları

Revision ID: 20251201_email_sistemi
Revises: 20251130_oda_kontrol_kaydi
Create Date: 2024-12-01

Bu migration şunları ekler:
- EmailAyarlari tablosu (SMTP ayarları)
- EmailLog tablosu (Gönderilen email kayıtları)
- Kullanıcı email zorunluluğu
- DolulukUyariLog tablosu (Günlük doluluk uyarı kayıtları)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers
revision = '20251201_email_sistemi'
down_revision = 'oda_kontrol_kaydi'
branch_labels = None
depends_on = None


def upgrade():
    # Email Ayarları Tablosu
    op.create_table(
        'email_ayarlari',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('smtp_server', sa.String(255), nullable=False),
        sa.Column('smtp_port', sa.Integer(), nullable=False, default=587),
        sa.Column('smtp_username', sa.String(255), nullable=False),
        sa.Column('smtp_password', sa.String(500), nullable=False),  # Şifrelenmiş
        sa.Column('smtp_use_tls', sa.Boolean(), default=True),
        sa.Column('smtp_use_ssl', sa.Boolean(), default=False),
        sa.Column('sender_email', sa.String(255), nullable=False),
        sa.Column('sender_name', sa.String(255), default='Minibar Takip Sistemi'),
        sa.Column('aktif', sa.Boolean(), default=True),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('guncelleme_tarihi', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('guncelleyen_id', sa.Integer(), sa.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True),
    )
    
    # Email Log Tablosu
    op.create_table(
        'email_loglari',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('alici_email', sa.String(255), nullable=False),
        sa.Column('alici_kullanici_id', sa.Integer(), sa.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True),
        sa.Column('konu', sa.String(500), nullable=False),
        sa.Column('icerik', sa.Text(), nullable=False),
        sa.Column('email_tipi', sa.String(50), nullable=False),  # uyari, bilgi, sistem
        sa.Column('durum', sa.String(20), default='gonderildi'),  # gonderildi, hata, beklemede
        sa.Column('hata_mesaji', sa.Text(), nullable=True),
        sa.Column('gonderim_tarihi', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('okundu', sa.Boolean(), default=False),
        sa.Column('okunma_tarihi', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tracking_id', sa.String(100), unique=True, nullable=True),  # Okundu takibi için
        sa.Column('ilgili_tablo', sa.String(100), nullable=True),  # İlişkili tablo adı
        sa.Column('ilgili_kayit_id', sa.Integer(), nullable=True),  # İlişkili kayıt ID
        sa.Column('ek_bilgiler', JSONB, nullable=True),  # Ek metadata
    )
    
    # Doluluk Uyarı Log Tablosu
    op.create_table(
        'doluluk_uyari_loglari',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('otel_id', sa.Integer(), sa.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False),
        sa.Column('depo_sorumlusu_id', sa.Integer(), sa.ForeignKey('kullanicilar.id', ondelete='CASCADE'), nullable=False),
        sa.Column('uyari_tarihi', sa.Date(), nullable=False),
        sa.Column('uyari_tipi', sa.String(50), nullable=False),  # inhouse_eksik, arrivals_eksik, her_ikisi_eksik
        sa.Column('email_gonderildi', sa.Boolean(), default=False),
        sa.Column('email_log_id', sa.Integer(), sa.ForeignKey('email_loglari.id', ondelete='SET NULL'), nullable=True),
        sa.Column('sistem_yoneticisi_bilgilendirildi', sa.Boolean(), default=False),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # İndeksler
    op.create_index('idx_email_log_alici', 'email_loglari', ['alici_email'])
    op.create_index('idx_email_log_tarih', 'email_loglari', ['gonderim_tarihi'])
    op.create_index('idx_email_log_tipi', 'email_loglari', ['email_tipi'])
    op.create_index('idx_email_log_durum', 'email_loglari', ['durum'])
    op.create_index('idx_email_log_tracking', 'email_loglari', ['tracking_id'])
    op.create_index('idx_doluluk_uyari_tarih', 'doluluk_uyari_loglari', ['uyari_tarihi'])
    op.create_index('idx_doluluk_uyari_otel', 'doluluk_uyari_loglari', ['otel_id', 'uyari_tarihi'])


def downgrade():
    op.drop_index('idx_doluluk_uyari_otel')
    op.drop_index('idx_doluluk_uyari_tarih')
    op.drop_index('idx_email_log_tracking')
    op.drop_index('idx_email_log_durum')
    op.drop_index('idx_email_log_tipi')
    op.drop_index('idx_email_log_tarih')
    op.drop_index('idx_email_log_alici')
    op.drop_table('doluluk_uyari_loglari')
    op.drop_table('email_loglari')
    op.drop_table('email_ayarlari')
