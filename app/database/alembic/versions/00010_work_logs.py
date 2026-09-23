"""work_logs

Revision ID: 00010
Revises: 00009
"""

import sqlalchemy as sa
from alembic import op

revision = "00010"
down_revision = "00009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_logs",
        sa.Column("work_date", sa.Date(), primary_key=True),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_work_logs_author_id", "work_logs", ["author_id"])


def downgrade() -> None:
    op.drop_index("ix_work_logs_author_id", table_name="work_logs")
    op.drop_table("work_logs")
