"""add participant_code into registration_session

Revision ID: ec634439e98b
Revises: 1d768fcd86eb
Create Date: 2026-09-26 18:27:32.073268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec634439e98b'
down_revision: Union[str, Sequence[str], None] = '1d768fcd86eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'registration_sessions',
        sa.Column('participant_code', sa.String(), nullable=True)
    )

def downgrade() -> None:
    op.drop_column('registration_sessions', 'participant_code')
