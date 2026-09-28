"""order_lines: total and intact pieces instead of one quantity with a condition

Revision ID: 00011
Revises: 00010
"""

import sqlalchemy as sa
from alembic import op

revision = "00011"
down_revision = "00010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("order_lines", sa.Column("quantity_total", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("order_lines", sa.Column("quantity_intact", sa.Integer(), nullable=False, server_default="0"))
    op.execute(
        "UPDATE order_lines SET quantity_total = quantity, "
        "quantity_intact = CASE WHEN goods_condition = 'FULL_VALUE' THEN quantity ELSE 0 END"
    )
    op.alter_column("order_lines", "quantity_total", server_default=None)
    op.alter_column("order_lines", "quantity_intact", server_default=None)

    op.drop_constraint("ck_order_lines_quantity_positive", "order_lines", type_="check")
    op.drop_column("order_lines", "quantity")
    op.drop_column("order_lines", "goods_condition")
    op.execute("DROP TYPE IF EXISTS goods_condition_enum")

    op.create_check_constraint("ck_order_lines_quantity_positive", "order_lines", "quantity_total >= 1")
    op.create_check_constraint(
        "ck_order_lines_quantity_intact", "order_lines", "quantity_intact >= 0 AND quantity_intact <= quantity_total"
    )


def downgrade() -> None:
    """Lossy: a line with both intact and damaged pieces comes back as one damaged line."""
    condition = sa.Enum("DAMAGED", "FULL_VALUE", name="goods_condition_enum")
    condition.create(op.get_bind(), checkfirst=True)
    op.add_column("order_lines", sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("order_lines", sa.Column("goods_condition", condition, nullable=False, server_default="DAMAGED"))
    op.execute(
        "UPDATE order_lines SET quantity = quantity_total, "
        "goods_condition = CASE WHEN quantity_intact = quantity_total THEN 'FULL_VALUE' ELSE 'DAMAGED' END"
    )
    op.alter_column("order_lines", "quantity", server_default=None)
    op.alter_column("order_lines", "goods_condition", server_default=None)

    op.drop_constraint("ck_order_lines_quantity_intact", "order_lines", type_="check")
    op.drop_constraint("ck_order_lines_quantity_positive", "order_lines", type_="check")
    op.drop_column("order_lines", "quantity_total")
    op.drop_column("order_lines", "quantity_intact")
    op.create_check_constraint("ck_order_lines_quantity_positive", "order_lines", "quantity >= 1")
