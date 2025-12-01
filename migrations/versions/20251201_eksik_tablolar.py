"""Eksik tabloları oluştur - 19 Kasım yedeğinden sonra eklenen tablolar

Revision ID: 20251201_eksik_tablolar
Revises: 
Create Date: 2024-12-01

Eksik Tablolar:
- gunluk_gorevler
- gorev_detaylari
- dnd_kontroller
- yukleme_gorevleri
- gorev_durum_loglari
- oda_kontrol_kayitlari
- email_ayarlari
- email_loglari
- doluluk_uyari_loglari
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251201_eksik_tablolar'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ENUM tipleri oluştur (eğer yoksa)
    gorev_tipi_enum = postgresql.ENUM(
        'inhouse_kontrol', 'arrival_kontrol', 'departure_kontrol',
        'inhouse_yukleme', 'arrivals_yukleme', 'departures_yukleme',
        name='gorev_tipi_enum',
        create_type=False
    )
    
    gorev_durum_enum = postgresql.ENUM(
        'pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete',
        name='gorev_durum_enum',
        create_type=False
    )
    
    # ENUM'ları oluştur
    conn = op.get_bind()
    
    # gorev_tipi_enum kontrolü ve oluşturma
    result = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'gorev_tipi_enum'"))
    if not result.fetchone():
        op.execute("CREATE TYPE gorev_tipi_enum AS ENUM ('inhouse_kontrol', 'arrival_kontrol', 'departure_kontrol', 'inhouse_yukleme', 'arrivals_yukleme', 'departures_yukleme')")
    
    # gorev_durum_enum kontrolü ve oluşturma
    result = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'gorev_durum_enum'"))
    if not result.fetchone():
        op.execute("CREATE TYPE gorev_durum_enum AS ENUM ('pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete')")
    
    # 1. gunluk_gorevler tablosu
    op.create_table('gunluk_gorevler',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('otel_id', sa.Integer(), nullable=False),
        sa.Column('personel_id', sa.Integer(), nullable=False),
        sa.Column('gorev_tarihi', sa.Date(), nullable=False),
        sa.Column('gorev_tipi', sa.Enum('inhouse_kontrol', 'arrival_kontrol', 'departure_kontrol', 'inhouse_yukleme', 'arrivals_yukleme', 'departures_yukleme', name='gorev_tipi_enum'), nullable=False),
        sa.Column('durum', sa.Enum('pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', name='gorev_durum_enum'), nullable=False, server_default='pending'),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
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

    # 2. gorev_detaylari tablosu
    op.create_table('gorev_detaylari',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('gorev_id', sa.Integer(), nullable=False),
        sa.Column('oda_id', sa.Integer(), nullable=False),
        sa.Column('misafir_kayit_id', sa.Integer(), nullable=True),
        sa.Column('durum', sa.Enum('pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', name='gorev_durum_enum'), nullable=False, server_default='pending'),
        sa.Column('varis_saati', sa.Time(), nullable=True),
        sa.Column('cikis_saati', sa.Time(), nullable=True),
        sa.Column('oncelik_sirasi', sa.Integer(), nullable=False, server_default='999'),
        sa.Column('kontrol_zamani', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dnd_sayisi', sa.Integer(), nullable=False, server_default='0'),
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
    op.create_index('idx_gorev_detay_oncelik', 'gorev_detaylari', ['oncelik_sirasi'])
    
    # 3. dnd_kontroller tablosu
    op.create_table('dnd_kontroller',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('gorev_detay_id', sa.Integer(), nullable=False),
        sa.Column('kontrol_zamani', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('kontrol_eden_id', sa.Integer(), nullable=True),
        sa.Column('notlar', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['gorev_detay_id'], ['gorev_detaylari.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['kontrol_eden_id'], ['kullanicilar.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_dnd_kontrol_gorev_detay', 'dnd_kontroller', ['gorev_detay_id'])
    op.create_index('idx_dnd_kontrol_zaman', 'dnd_kontroller', ['kontrol_zamani'])
    
    # 4. yukleme_gorevleri tablosu
    op.create_table('yukleme_gorevleri',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('otel_id', sa.Integer(), nullable=False),
        sa.Column('depo_sorumlusu_id', sa.Integer(), nullable=False),
        sa.Column('gorev_tarihi', sa.Date(), nullable=False),
        sa.Column('dosya_tipi', sa.String(20), nullable=False),
        sa.Column('durum', sa.Enum('pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', name='gorev_durum_enum'), nullable=False, server_default='pending'),
        sa.Column('yukleme_zamani', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dosya_yukleme_id', sa.Integer(), nullable=True),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['otel_id'], ['oteller.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['depo_sorumlusu_id'], ['kullanicilar.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dosya_yukleme_id'], ['dosya_yuklemeleri.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('otel_id', 'gorev_tarihi', 'dosya_tipi', name='uq_yukleme_gorev_otel_tarih_tip')
    )
    op.create_index('idx_yukleme_gorev_otel_tarih', 'yukleme_gorevleri', ['otel_id', 'gorev_tarihi'])
    op.create_index('idx_yukleme_gorev_depo_sorumlusu', 'yukleme_gorevleri', ['depo_sorumlusu_id'])
    op.create_index('idx_yukleme_gorev_durum', 'yukleme_gorevleri', ['durum'])
    
    # 5. gorev_durum_loglari tablosu
    op.create_table('gorev_durum_loglari',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('gorev_detay_id', sa.Integer(), nullable=False),
        sa.Column('onceki_durum', sa.Enum('pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', name='gorev_durum_enum'), nullable=True),
        sa.Column('yeni_durum', sa.Enum('pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', name='gorev_durum_enum'), nullable=False),
        sa.Column('degisiklik_zamani', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('degistiren_id', sa.Integer(), nullable=True),
        sa.Column('aciklama', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['gorev_detay_id'], ['gorev_detaylari.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['degistiren_id'], ['kullanicilar.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_gorev_durum_log_detay', 'gorev_durum_loglari', ['gorev_detay_id'])
    op.create_index('idx_gorev_durum_log_zaman', 'gorev_durum_loglari', ['degisiklik_zamani'])

    # 6. oda_kontrol_kayitlari tablosu
    op.create_table('oda_kontrol_kayitlari',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('oda_id', sa.Integer(), nullable=False),
        sa.Column('personel_id', sa.Integer(), nullable=False),
        sa.Column('kontrol_tarihi', sa.Date(), nullable=False),
        sa.Column('baslangic_zamani', sa.DateTime(timezone=True), nullable=False),
        sa.Column('bitis_zamani', sa.DateTime(timezone=True), nullable=True),
        sa.Column('kontrol_tipi', sa.String(20), nullable=False, server_default='sarfiyat_yok'),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['oda_id'], ['odalar.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['personel_id'], ['kullanicilar.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_oda_kontrol_oda_tarih', 'oda_kontrol_kayitlari', ['oda_id', 'kontrol_tarihi'])
    op.create_index('idx_oda_kontrol_personel_tarih', 'oda_kontrol_kayitlari', ['personel_id', 'kontrol_tarihi'])
    op.create_index('idx_oda_kontrol_bitis', 'oda_kontrol_kayitlari', ['bitis_zamani'])
    
    # 7. email_ayarlari tablosu
    op.create_table('email_ayarlari',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('smtp_server', sa.String(255), nullable=False),
        sa.Column('smtp_port', sa.Integer(), nullable=False, server_default='587'),
        sa.Column('smtp_username', sa.String(255), nullable=False),
        sa.Column('smtp_password', sa.String(500), nullable=False),
        sa.Column('smtp_use_tls', sa.Boolean(), server_default='true'),
        sa.Column('smtp_use_ssl', sa.Boolean(), server_default='false'),
        sa.Column('sender_email', sa.String(255), nullable=False),
        sa.Column('sender_name', sa.String(255), server_default="'Minibar Takip Sistemi'"),
        sa.Column('aktif', sa.Boolean(), server_default='true'),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('guncelleme_tarihi', sa.DateTime(timezone=True), nullable=True),
        sa.Column('guncelleyen_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['guncelleyen_id'], ['kullanicilar.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 8. email_loglari tablosu
    op.create_table('email_loglari',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alici_email', sa.String(255), nullable=False),
        sa.Column('alici_kullanici_id', sa.Integer(), nullable=True),
        sa.Column('konu', sa.String(500), nullable=False),
        sa.Column('icerik', sa.Text(), nullable=False),
        sa.Column('email_tipi', sa.String(50), nullable=False),
        sa.Column('durum', sa.String(20), server_default="'gonderildi'"),
        sa.Column('hata_mesaji', sa.Text(), nullable=True),
        sa.Column('gonderim_tarihi', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('okundu', sa.Boolean(), server_default='false'),
        sa.Column('okunma_tarihi', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tracking_id', sa.String(100), unique=True, nullable=True),
        sa.Column('ilgili_tablo', sa.String(100), nullable=True),
        sa.Column('ilgili_kayit_id', sa.Integer(), nullable=True),
        sa.Column('ek_bilgiler', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['alici_kullanici_id'], ['kullanicilar.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_email_log_alici', 'email_loglari', ['alici_email'])
    op.create_index('idx_email_log_tarih', 'email_loglari', ['gonderim_tarihi'])
    op.create_index('idx_email_log_tipi', 'email_loglari', ['email_tipi'])
    op.create_index('idx_email_log_durum', 'email_loglari', ['durum'])
    op.create_index('idx_email_log_tracking', 'email_loglari', ['tracking_id'])
    
    # 9. doluluk_uyari_loglari tablosu
    op.create_table('doluluk_uyari_loglari',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('otel_id', sa.Integer(), nullable=False),
        sa.Column('depo_sorumlusu_id', sa.Integer(), nullable=False),
        sa.Column('uyari_tarihi', sa.Date(), nullable=False),
        sa.Column('uyari_tipi', sa.String(50), nullable=False),
        sa.Column('email_gonderildi', sa.Boolean(), server_default='false'),
        sa.Column('email_log_id', sa.Integer(), nullable=True),
        sa.Column('sistem_yoneticisi_bilgilendirildi', sa.Boolean(), server_default='false'),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['otel_id'], ['oteller.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['depo_sorumlusu_id'], ['kullanicilar.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['email_log_id'], ['email_loglari.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_doluluk_uyari_tarih', 'doluluk_uyari_loglari', ['uyari_tarihi'])
    op.create_index('idx_doluluk_uyari_otel', 'doluluk_uyari_loglari', ['otel_id', 'uyari_tarihi'])


def downgrade():
    # Tabloları ters sırada sil (foreign key bağımlılıkları nedeniyle)
    op.drop_table('doluluk_uyari_loglari')
    op.drop_table('email_loglari')
    op.drop_table('email_ayarlari')
    op.drop_table('oda_kontrol_kayitlari')
    op.drop_table('gorev_durum_loglari')
    op.drop_table('yukleme_gorevleri')
    op.drop_table('dnd_kontroller')
    op.drop_table('gorev_detaylari')
    op.drop_table('gunluk_gorevler')
    
    # ENUM tiplerini sil
    op.execute("DROP TYPE IF EXISTS gorev_durum_enum")
    op.execute("DROP TYPE IF EXISTS gorev_tipi_enum")
