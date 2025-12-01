"""Görevlendirme sistemi modelleri

Revision ID: gorevlendirme_001
Revises: 0d9625cc0181
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'gorevlendirme_001'
down_revision = '0d9625cc0181'
branch_labels = None
depends_on = None


def upgrade():
    # Enum tipleri oluştur
    gorev_tipi_enum = postgresql.ENUM(
        'inhouse_kontrol', 'arrival_kontrol', 'inhouse_yukleme', 'arrivals_yukleme',
        name='gorev_tipi_enum',
        create_type=False
    )
    gorev_durum_enum = postgresql.ENUM(
        'pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete',
        name='gorev_durum_enum',
        create_type=False
    )
    
    # Enum'ları veritabanında oluştur
    op.execute("CREATE TYPE gorev_tipi_enum AS ENUM ('inhouse_kontrol', 'arrival_kontrol', 'inhouse_yukleme', 'arrivals_yukleme')")
    op.execute("CREATE TYPE gorev_durum_enum AS ENUM ('pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete')")
    
    # gunluk_gorevler tablosu
    op.create_table(
        'gunluk_gorevler',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('otel_id', sa.Integer(), nullable=False),
        sa.Column('personel_id', sa.Integer(), nullable=False),
        sa.Column('gorev_tarihi', sa.Date(), nullable=False),
        sa.Column('gorev_tipi', gorev_tipi_enum, nullable=False),
        sa.Column('durum', gorev_durum_enum, server_default='pending', nullable=False),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tamamlanma_tarihi', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notlar', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['otel_id'], ['oteller.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['personel_id'], ['kullanicilar.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_gunluk_gorev_otel_tarih', 'gunluk_gorevler', ['otel_id', 'gorev_tarihi'])
    op.create_index('idx_gunluk_gorev_personel_tarih', 'gunluk_gorevler', ['personel_id', 'gorev_tarihi'])
    op.create_index('idx_gunluk_gorev_durum', 'gunluk_gorevler', ['durum'])
    op.create_index('idx_gunluk_gorev_tipi', 'gunluk_gorevler', ['gorev_tipi'])
    
    # gorev_detaylari tablosu
    op.create_table(
        'gorev_detaylari',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('gorev_id', sa.Integer(), nullable=False),
        sa.Column('oda_id', sa.Integer(), nullable=False),
        sa.Column('misafir_kayit_id', sa.Integer(), nullable=True),
        sa.Column('durum', gorev_durum_enum, server_default='pending', nullable=False),
        sa.Column('varis_saati', sa.Time(), nullable=True),
        sa.Column('kontrol_zamani', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dnd_sayisi', sa.Integer(), server_default='0', nullable=False),
        sa.Column('son_dnd_zamani', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notlar', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['gorev_id'], ['gunluk_gorevler.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['oda_id'], ['odalar.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['misafir_kayit_id'], ['misafir_kayitlari.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_gorev_detay_gorev', 'gorev_detaylari', ['gorev_id'])
    op.create_index('idx_gorev_detay_oda', 'gorev_detaylari', ['oda_id'])
    op.create_index('idx_gorev_detay_durum', 'gorev_detaylari', ['durum'])
    op.create_index('idx_gorev_detay_dnd', 'gorev_detaylari', ['dnd_sayisi'])
    
    # dnd_kontroller tablosu
    op.create_table(
        'dnd_kontroller',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('gorev_detay_id', sa.Integer(), nullable=False),
        sa.Column('kontrol_zamani', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('kontrol_eden_id', sa.Integer(), nullable=True),
        sa.Column('notlar', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['gorev_detay_id'], ['gorev_detaylari.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['kontrol_eden_id'], ['kullanicilar.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_dnd_kontrol_gorev_detay', 'dnd_kontroller', ['gorev_detay_id'])
    op.create_index('idx_dnd_kontrol_zaman', 'dnd_kontroller', ['kontrol_zamani'])
    
    # yukleme_gorevleri tablosu
    op.create_table(
        'yukleme_gorevleri',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('otel_id', sa.Integer(), nullable=False),
        sa.Column('depo_sorumlusu_id', sa.Integer(), nullable=False),
        sa.Column('gorev_tarihi', sa.Date(), nullable=False),
        sa.Column('dosya_tipi', sa.String(20), nullable=False),
        sa.Column('durum', gorev_durum_enum, server_default='pending', nullable=False),
        sa.Column('yukleme_zamani', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dosya_yukleme_id', sa.Integer(), nullable=True),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['otel_id'], ['oteller.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['depo_sorumlusu_id'], ['kullanicilar.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dosya_yukleme_id'], ['dosya_yuklemeleri.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('otel_id', 'gorev_tarihi', 'dosya_tipi', name='uq_yukleme_gorev_otel_tarih_tip')
    )
    op.create_index('idx_yukleme_gorev_otel_tarih', 'yukleme_gorevleri', ['otel_id', 'gorev_tarihi'])
    op.create_index('idx_yukleme_gorev_depo_sorumlusu', 'yukleme_gorevleri', ['depo_sorumlusu_id'])
    op.create_index('idx_yukleme_gorev_durum', 'yukleme_gorevleri', ['durum'])
    
    # gorev_durum_loglari tablosu
    op.create_table(
        'gorev_durum_loglari',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('gorev_detay_id', sa.Integer(), nullable=False),
        sa.Column('onceki_durum', gorev_durum_enum, nullable=True),
        sa.Column('yeni_durum', gorev_durum_enum, nullable=False),
        sa.Column('degisiklik_zamani', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('degistiren_id', sa.Integer(), nullable=True),
        sa.Column('aciklama', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['gorev_detay_id'], ['gorev_detaylari.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['degistiren_id'], ['kullanicilar.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_gorev_durum_log_detay', 'gorev_durum_loglari', ['gorev_detay_id'])
    op.create_index('idx_gorev_durum_log_zaman', 'gorev_durum_loglari', ['degisiklik_zamani'])


def downgrade():
    # Tabloları sil
    op.drop_table('gorev_durum_loglari')
    op.drop_table('yukleme_gorevleri')
    op.drop_table('dnd_kontroller')
    op.drop_table('gorev_detaylari')
    op.drop_table('gunluk_gorevler')
    
    # Enum'ları sil
    op.execute("DROP TYPE IF EXISTS gorev_tipi_enum")
    op.execute("DROP TYPE IF EXISTS gorev_durum_enum")
