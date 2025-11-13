"""add model_path column to ml_models

Revision ID: ml_model_path_001
Revises: 
Create Date: 2025-11-12 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ml_model_path_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Add model_path column to ml_models table
    Make model_data nullable for backward compatibility
    """
    # Add model_path column
    op.add_column('ml_models', 
        sa.Column('model_path', sa.String(500), nullable=True)
    )
    
    # Make model_data nullable (backward compatibility)
    op.alter_column('ml_models', 'model_data',
        existing_type=sa.LargeBinary(),
        nullable=True
    )
    
    # Add index for model_path
    op.create_index('idx_ml_models_path', 'ml_models', ['model_path'])
    
    print("✅ Migration applied: model_path column added to ml_models")


def downgrade():
    """
    Remove model_path column and revert model_data to NOT NULL
    """
    # Drop index
    op.drop_index('idx_ml_models_path', 'ml_models')
    
    # Make model_data NOT NULL again
    op.alter_column('ml_models', 'model_data',
        existing_type=sa.LargeBinary(),
        nullable=False
    )
    
    # Drop model_path column
    op.drop_column('ml_models', 'model_path')
    
    print("✅ Migration reverted: model_path column removed from ml_models")
