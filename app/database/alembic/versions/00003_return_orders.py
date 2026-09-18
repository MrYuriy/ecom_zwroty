"""return_orders + order_lines

Revision ID: 00003
Revises: 00002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "00003"
down_revision = "00002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "return_orders",
        sa.Column("uuid", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bo_wms_number", sa.String(64), nullable=True),
        sa.Column("tempo_number", sa.String(64), nullable=True),
        sa.Column("return_date", sa.Date(), nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("operator_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_return_orders_bo_wms_number", "return_orders", ["bo_wms_number"])
    op.create_index("ix_return_orders_tempo_number", "return_orders", ["tempo_number"])
    op.create_index("ix_return_orders_return_date", "return_orders", ["return_date"])
    op.create_index("ix_return_orders_operator_id", "return_orders", ["operator_id"])

    op.create_table(
        "order_lines",
        sa.Column("uuid", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "return_order_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("return_orders.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("sku_registry.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("carrier_type", sa.Enum("PARCEL", "PALLET", name="carrier_type_enum"), nullable=False),
        sa.Column("goods_condition", sa.Enum("DAMAGED", "FULL_VALUE", name="goods_condition_enum"), nullable=False),
        sa.Column("damage_description", sa.Text(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("quantity >= 1", name="ck_order_lines_quantity_positive"),
    )
    op.create_index("ix_order_lines_return_order_uuid", "order_lines", ["return_order_uuid"])
    op.create_index("ix_order_lines_sku_id", "order_lines", ["sku_id"])


def downgrade() -> None:
    op.drop_index("ix_order_lines_sku_id", table_name="order_lines")
    op.drop_index("ix_order_lines_return_order_uuid", table_name="order_lines")
    op.drop_table("order_lines")
    op.drop_index("ix_return_orders_operator_id", table_name="return_orders")
    op.drop_index("ix_return_orders_return_date", table_name="return_orders")
    op.drop_index("ix_return_orders_tempo_number", table_name="return_orders")
    op.drop_index("ix_return_orders_bo_wms_number", table_name="return_orders")
    op.drop_table("return_orders")
    bind = op.get_bind()
    sa.Enum(name="goods_condition_enum").drop(bind, checkfirst=True)
    sa.Enum(name="carrier_type_enum").drop(bind, checkfirst=True)
