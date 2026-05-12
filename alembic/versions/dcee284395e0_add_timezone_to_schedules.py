"""add timezone to schedules

Revision ID: dcee284395e0
Revises: 3a61b1c8c1b0
Create Date: 2026-05-12 18:04:29.001559

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dcee284395e0'
down_revision: Union[str, Sequence[str], None] = '3a61b1c8c1b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('schedules')]
    if 'timezone' not in columns:
        with op.batch_alter_table('schedules', schema=None) as batch_op:
            batch_op.add_column(sa.Column('timezone', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('schedules')]
    if 'timezone' in columns:
        with op.batch_alter_table('schedules', schema=None) as batch_op:
            batch_op.drop_column('timezone')
