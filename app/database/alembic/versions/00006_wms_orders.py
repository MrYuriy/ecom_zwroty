"""wms_orders

Revision ID: 00006
Revises: 00005
"""

import sqlalchemy as sa
from alembic import op

revision = "00006"
down_revision = "00005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wms_orders",
        sa.Column("bo_wms_number", sa.String(64), primary_key=True),
        sa.Column("tempo_number", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_wms_orders_created_at", "wms_orders", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_wms_orders_created_at", table_name="wms_orders")
    op.drop_table("wms_orders")
