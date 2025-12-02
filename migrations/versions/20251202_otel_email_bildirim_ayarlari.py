"""Otel bazında email bildirim ayarları

Revision ID: 20251202_email_bildirim
Revises: 
Create Date: 2024-12-02

Her otel için ayrı ayrı e-posta bildirim ayarları.
Varsayılan olarak tüm otellerde kapalı, sadece Merit Royal Diamond için açık.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251202_email_bildirim'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Otel tablosuna e-posta bildirim kolonları ekle
    op.add_column('oteller', sa.Column('email_bildirim_aktif', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('oteller', sa.Column('email_uyari_aktif', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('oteller', sa.Column('email_rapor_aktif', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('oteller', sa.Column('email_sistem_aktif', sa.Boolean(), server_default='false', nullable=True))
    
    # Merit Royal Diamond için bildirimleri aktif et
    op.execute("""
        UPDATE oteller 
        SET email_bildirim_aktif = true,
            email_uyari_aktif = true,
            email_rapor_aktif = true,
            email_sistem_aktif = true
        WHERE ad ILIKE '%Merit Royal Diamond%'
    """)


def downgrade():
    op.drop_column('oteller', 'email_sistem_aktif')
    op.drop_column('oteller', 'email_rapor_aktif')
    op.drop_column('oteller', 'email_uyari_aktif')
    op.drop_column('oteller', 'email_bildirim_aktif')
