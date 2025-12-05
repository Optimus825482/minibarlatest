"""Ana depo tedarik detaylarına created_at sütunu ekleme

Revision ID: add_created_at_tedarik
Revises: 
Create Date: 2025-12-05

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
import pytz

# revision identifiers, used by Alembic.
revision = 'add_created_at_tedarik'
down_revision = None
branch_labels = None
depends_on = None

# KKTC Timezone (GMT+2/+3)
KKTC_TZ = pytz.timezone('Europe/Nicosia')

def upgrade():
    # created_at sütununu ekle (nullable=True olarak başla)
    op.add_column('ana_depo_tedarik_detaylari', 
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Mevcut kayıtları şu anki KKTC saati ile güncelle
    kktc_now = datetime.now(KKTC_TZ)
    op.execute(f"""
        UPDATE ana_depo_tedarik_detaylari 
        SET created_at = '{kktc_now.strftime('%Y-%m-%d %H:%M:%S%z')}'
        WHERE created_at IS NULL
    """)

def downgrade():
    op.drop_column('ana_depo_tedarik_detaylari', 'created_at')
