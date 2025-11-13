"""Merge migration heads

Revision ID: 0d9625cc0181
Revises: 761c02a6168a, ml_model_path_001
Create Date: 2025-11-12 18:32:51.814665

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0d9625cc0181'
down_revision = ('761c02a6168a', 'ml_model_path_001')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
