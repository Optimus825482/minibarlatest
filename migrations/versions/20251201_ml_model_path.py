"""ML Model tablosuna model_path kolonu ekleme

Revision ID: 20251201_ml_model_path
Revises: 
Create Date: 2025-12-01
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251201_ml_model_path'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """model_path kolonunu ekle"""
    # Kolon zaten varsa hata verme
    try:
        op.add_column('ml_models', sa.Column('model_path', sa.String(255), nullable=True))
        print("✅ ml_models.model_path kolonu eklendi")
    except Exception as e:
        print(f"⚠️ model_path kolonu zaten mevcut veya hata: {str(e)}")


def downgrade():
    """model_path kolonunu kaldır"""
    try:
        op.drop_column('ml_models', 'model_path')
    except Exception as e:
        print(f"⚠️ Downgrade hatası: {str(e)}")
