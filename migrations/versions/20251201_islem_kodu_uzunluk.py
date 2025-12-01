"""islem_kodu alanı uzunluğunu artır

Revision ID: 20251201_islem_kodu
Revises: 
Create Date: 2025-12-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251201_islem_kodu'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """islem_kodu alanlarını varchar(50) olarak güncelle"""
    # misafir_kayitlari tablosu
    op.alter_column('misafir_kayitlari', 'islem_kodu',
                    existing_type=sa.String(8),
                    type_=sa.String(50),
                    existing_nullable=False)
    
    # dosya_yuklemeleri tablosu
    op.alter_column('dosya_yuklemeleri', 'islem_kodu',
                    existing_type=sa.String(8),
                    type_=sa.String(50),
                    existing_nullable=False)


def downgrade():
    """Geri al - varchar(8)'e döndür"""
    op.alter_column('misafir_kayitlari', 'islem_kodu',
                    existing_type=sa.String(50),
                    type_=sa.String(8),
                    existing_nullable=False)
    
    op.alter_column('dosya_yuklemeleri', 'islem_kodu',
                    existing_type=sa.String(50),
                    type_=sa.String(8),
                    existing_nullable=False)
