"""Add performance indexes to odalar table

Revision ID: 20260303_perf_idx
Revises: 
Create Date: 2026-03-03
"""
from alembic import op

# revision identifiers
revision = '20260303_perf_idx'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add indexes for odalar query performance"""
    # Composite index: aktif + oda_no (used by oda_tanimla page)
    op.create_index(
        'idx_odalar_aktif_oda_no', 'odalar', ['aktif', 'oda_no'],
        if_not_exists=True
    )
    # Foreign key index: kat_id (PostgreSQL doesn't auto-create FK indexes)
    op.create_index(
        'idx_odalar_kat_id', 'odalar', ['kat_id'],
        if_not_exists=True
    )


def downgrade():
    op.drop_index('idx_odalar_kat_id', table_name='odalar')
    op.drop_index('idx_odalar_aktif_oda_no', table_name='odalar')
