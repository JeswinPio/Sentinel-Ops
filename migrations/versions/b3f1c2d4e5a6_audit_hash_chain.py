"""audit hash chain

Revision ID: b3f1c2d4e5a6
Revises: a68c092700b5
Create Date: 2026-11-23 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3f1c2d4e5a6'
down_revision: Union[str, Sequence[str], None] = 'a68c092700b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('audit_logs', sa.Column('seq', sa.Integer(), nullable=True))
    op.add_column('audit_logs', sa.Column('prev_hash', sa.String(length=64), nullable=True))
    op.add_column('audit_logs', sa.Column('hash', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_audit_logs_seq'), 'audit_logs', ['seq'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_seq'), table_name='audit_logs')
    with op.batch_alter_table('audit_logs') as batch:
        batch.drop_column('hash')
        batch.drop_column('prev_hash')
        batch.drop_column('seq')
