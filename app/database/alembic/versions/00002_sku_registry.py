"""sku_registry

Revision ID: 00002
Revises: 00001
"""

import sqlalchemy as sa
from alembic import op

revision = "00002"
down_revision = "00001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sku_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trade_reference", sa.String(64), nullable=False),
        sa.Column("ean", sa.String(32), nullable=True),
        sa.Column("product_name", sa.String(500), nullable=False),
        sa.Column("is_parametrized", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_sku_registry_trade_reference", "sku_registry", ["trade_reference"], unique=True)
    op.create_index("ix_sku_registry_ean", "sku_registry", ["ean"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_sku_registry_ean", table_name="sku_registry")
    op.drop_index("ix_sku_registry_trade_reference", table_name="sku_registry")
    op.drop_table("sku_registry")
