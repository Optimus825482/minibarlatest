"""Ana Depo Tedarik tabloları ekleme

Revision ID: 20251205_ana_depo_tedarik
Revises: 20251202_email_bildirim
Create Date: 2024-12-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251205_ana_depo_tedarik'
down_revision = '20251202_email_bildirim'
branch_labels = None
depends_on = None


def upgrade():
    # Ana Depo Tedarik tablosu
    op.create_table('ana_depo_tedarikleri',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tedarik_no', sa.String(length=50), nullable=False),
        sa.Column('otel_id', sa.Integer(), nullable=False),
        sa.Column('depo_sorumlusu_id', sa.Integer(), nullable=True),
        sa.Column('islem_tarihi', sa.DateTime(timezone=True), nullable=False),
        sa.Column('toplam_urun_sayisi', sa.Integer(), default=0),
        sa.Column('toplam_miktar', sa.Integer(), default=0),
        sa.Column('aciklama', sa.Text(), nullable=True),
        sa.Column('sistem_yoneticisi_goruldu', sa.Boolean(), default=False),
        sa.Column('gorulme_tarihi', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['otel_id'], ['oteller.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['depo_sorumlusu_id'], ['kullanicilar.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tedarik_no')
    )
    
    # İndeksler
    op.create_index('idx_ana_depo_tedarik_tarih', 'ana_depo_tedarikleri', ['islem_tarihi'])
    op.create_index('idx_ana_depo_tedarik_otel', 'ana_depo_tedarikleri', ['otel_id'])
    op.create_index('idx_ana_depo_tedarik_depo_sorumlusu', 'ana_depo_tedarikleri', ['depo_sorumlusu_id'])
    op.create_index('idx_ana_depo_tedarik_goruldu', 'ana_depo_tedarikleri', ['sistem_yoneticisi_goruldu'])
    
    # Ana Depo Tedarik Detay tablosu
    op.create_table('ana_depo_tedarik_detaylari',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tedarik_id', sa.Integer(), nullable=False),
        sa.Column('urun_id', sa.Integer(), nullable=False),
        sa.Column('miktar', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['tedarik_id'], ['ana_depo_tedarikleri.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['urun_id'], ['urunler.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # İndeksler
    op.create_index('idx_ana_depo_tedarik_detay_tedarik', 'ana_depo_tedarik_detaylari', ['tedarik_id'])
    op.create_index('idx_ana_depo_tedarik_detay_urun', 'ana_depo_tedarik_detaylari', ['urun_id'])


def downgrade():
    op.drop_table('ana_depo_tedarik_detaylari')
    op.drop_table('ana_depo_tedarikleri')
