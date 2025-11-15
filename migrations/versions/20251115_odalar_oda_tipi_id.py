"""Odalar tablosuna oda_tipi_id kolonu ekle ve verileri güncelle

Revision ID: 20251115_odalar_oda_tipi_id
Revises: 
Create Date: 2025-11-15 10:50:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251115_odalar_oda_tipi_id'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    1. oda_tipi_id kolonu ekle
    2. Mevcut oda_tipi string değerlerini oda_tipi_id'ye map et
    3. oda_tipi kolonunu nullable yap (eski veri için)
    """
    
    # 1. oda_tipi_id kolonu ekle (nullable, foreign key)
    op.add_column('odalar', sa.Column('oda_tipi_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_odalar_oda_tipi', 'odalar', 'oda_tipleri', ['oda_tipi_id'], ['id'])
    
    # 2. Mapping tablosu
    mapping = {
        'JUNIOR  SUITE  ': 10,  # JUNIOR SUITE
        'JUNİOR  SUITE       ': 10,  # JUNIOR SUITE (Türkçe i)
        'JUNIOR SUITE': 10,
        'JUNIOR SUITE ': 10,
        'KING SUIT ': 12,  # KING SUITE
        'KING SUIT  ': 12,
        'KING SUITE': 12,
        'KING SUITE ': 12,
        'QUEEN SUITE': 11,
        'QUEEN SUITE ': 11,
        'QUEEN SUITE CONNECTION': 11,  # QUEEN SUITE
        'ROYAL KING': 12,  # KING SUITE
        'ROYAL QUEEN SUITE ': 11,  # QUEEN SUITE
        'ROYAL SUIT ': 10,  # JUNIOR SUITE
        'STANDARD': 9,
        'STANDARD ': 9,
        'STANDARD  ': 9,
        'STANDARD CONNECTION': 9,  # STANDARD
        'STANDARD CONNECTION ': 9,
        'CASINO': None  # Eşleşme yok, NULL kalacak
    }
    
    # 3. Her bir mapping için UPDATE
    conn = op.get_bind()
    for oda_tipi_str, oda_tipi_id in mapping.items():
        if oda_tipi_id is not None:
            conn.execute(
                sa.text(f"UPDATE odalar SET oda_tipi_id = {oda_tipi_id} WHERE oda_tipi = :oda_tipi"),
                {'oda_tipi': oda_tipi_str}
            )
    
    print("✅ Oda tipi ID'leri güncellendi")


def downgrade():
    """
    Geri alma: oda_tipi_id kolonunu kaldır
    """
    op.drop_constraint('fk_odalar_oda_tipi', 'odalar', type_='foreignkey')
    op.drop_column('odalar', 'oda_tipi_id')
