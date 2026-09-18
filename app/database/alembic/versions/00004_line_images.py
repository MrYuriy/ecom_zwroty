"""line_images

Revision ID: 00004
Revises: 00003
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "00004"
down_revision = "00003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "line_images",
        sa.Column("uuid", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "order_line_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("order_lines.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(64), nullable=False),
        sa.Column("content_type", sa.String(32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("file_name", name="uq_line_images_file_name"),
    )
    op.create_index("ix_line_images_order_line_uuid", "line_images", ["order_line_uuid"])


def downgrade() -> None:
    op.drop_index("ix_line_images_order_line_uuid", table_name="line_images")
    op.drop_table("line_images")
