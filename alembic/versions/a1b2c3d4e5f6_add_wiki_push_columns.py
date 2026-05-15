"""add wiki push columns

Revision ID: a1b2c3d4e5f6
Revises: dcee284395e0
Create Date: 2026-05-15 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'dcee284395e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add wiki push columns to schedules and reports tables."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # ── schedules: wiki config columns ────────────────────
    sched_cols = [c['name'] for c in inspector.get_columns('schedules')]
    with op.batch_alter_table('schedules', schema=None) as batch_op:
        if 'wiki_enabled' not in sched_cols:
            batch_op.add_column(sa.Column('wiki_enabled', sa.Integer(), server_default='0', nullable=False))
        if 'wiki_space_key' not in sched_cols:
            batch_op.add_column(sa.Column('wiki_space_key', sa.String(), nullable=True))
        if 'wiki_ancestor_id' not in sched_cols:
            batch_op.add_column(sa.Column('wiki_ancestor_id', sa.String(), nullable=True))
        if 'wiki_title_prefix' not in sched_cols:
            batch_op.add_column(sa.Column('wiki_title_prefix', sa.String(), nullable=True))

    # ── reports: wiki publish tracking ────────────────────
    report_cols = [c['name'] for c in inspector.get_columns('reports')]
    with op.batch_alter_table('reports', schema=None) as batch_op:
        if 'wiki_url' not in report_cols:
            batch_op.add_column(sa.Column('wiki_url', sa.String(), nullable=True))
        if 'wiki_pushed_at' not in report_cols:
            batch_op.add_column(sa.Column('wiki_pushed_at', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove wiki push columns."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    report_cols = [c['name'] for c in inspector.get_columns('reports')]
    with op.batch_alter_table('reports', schema=None) as batch_op:
        if 'wiki_pushed_at' in report_cols:
            batch_op.drop_column('wiki_pushed_at')
        if 'wiki_url' in report_cols:
            batch_op.drop_column('wiki_url')

    sched_cols = [c['name'] for c in inspector.get_columns('schedules')]
    with op.batch_alter_table('schedules', schema=None) as batch_op:
        if 'wiki_title_prefix' in sched_cols:
            batch_op.drop_column('wiki_title_prefix')
        if 'wiki_ancestor_id' in sched_cols:
            batch_op.drop_column('wiki_ancestor_id')
        if 'wiki_space_key' in sched_cols:
            batch_op.drop_column('wiki_space_key')
        if 'wiki_enabled' in sched_cols:
            batch_op.drop_column('wiki_enabled')
