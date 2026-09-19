"""return status (OPEN/CLOSED) and export statuses of lines and photos

Revision ID: 00008
Revises: 00007
"""

import sqlalchemy as sa
from alembic import op

revision = "00008"
down_revision = "00007"
branch_labels = None
depends_on = None

_status = sa.Enum("OPEN", "CLOSED", name="return_status_enum")


def upgrade() -> None:
    _status.create(op.get_bind(), checkfirst=True)
    op.add_column("return_orders", sa.Column("status", _status, nullable=False, server_default="OPEN"))
    op.add_column("return_orders", sa.Column("closed_at", sa.DateTime(), nullable=True))
    op.create_index("ix_return_orders_status", "return_orders", ["status"])

    op.add_column("order_lines", sa.Column("exported_at", sa.DateTime(), nullable=True))
    op.create_index("ix_order_lines_exported_at", "order_lines", ["exported_at"])

    op.add_column("line_images", sa.Column("downloaded_at", sa.DateTime(), nullable=True))
    op.create_index("ix_line_images_downloaded_at", "line_images", ["downloaded_at"])


def downgrade() -> None:
    op.drop_index("ix_line_images_downloaded_at", table_name="line_images")
    op.drop_column("line_images", "downloaded_at")
    op.drop_index("ix_order_lines_exported_at", table_name="order_lines")
    op.drop_column("order_lines", "exported_at")
    op.drop_index("ix_return_orders_status", table_name="return_orders")
    op.drop_column("return_orders", "closed_at")
    op.drop_column("return_orders", "status")
    _status.drop(op.get_bind(), checkfirst=True)
