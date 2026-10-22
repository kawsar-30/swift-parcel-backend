"""Added rider_type to riders

Revision ID: 5eed2ce91a59
Revises: 616ecd6ff2b2
Create Date: 2026-10-20 14:28:16.541244

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5eed2ce91a59'
down_revision: Union[str, None] = '616ecd6ff2b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Default value soho column add koro (jate purono rider der null na hoy)
    op.add_column(
        'riders', 
        sa.Column('rider_type', sa.String(length=20), nullable=False, server_default='both')
    )
    
    # 2. Ebar default value remove koro (notun rider der jonno server_default lagbe na)
    op.alter_column('riders', 'rider_type', server_default=None)


def downgrade() -> None:
    op.drop_column('riders', 'rider_type')