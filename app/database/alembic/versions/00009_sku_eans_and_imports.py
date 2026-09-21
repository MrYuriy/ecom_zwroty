"""sku_eans (many codes per product) and sku_imports (bulk file imports)

Revision ID: 00009
Revises: 00008
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "00009"
down_revision = "00008"
branch_labels = None
depends_on = None

_status = sa.Enum("PENDING", "RUNNING", "DONE", "FAILED", name="sku_import_status_enum")


def upgrade() -> None:
    op.create_table(
        "sku_eans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ean", sa.String(32), nullable=False),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("sku_registry.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sku_eans_ean", "sku_eans", ["ean"], unique=True)
    op.create_index("ix_sku_eans_sku_id", "sku_eans", ["sku_id"])
    # Keep every code the register already had.
    op.execute("INSERT INTO sku_eans (ean, sku_id) SELECT ean, id FROM sku_registry WHERE ean IS NOT NULL")
    op.drop_index("ix_sku_registry_ean", table_name="sku_registry")
    op.drop_column("sku_registry", "ean")

    op.create_table(
        "sku_imports",
        sa.Column("uuid", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("status", _status, nullable=False, server_default="PENDING"),
        sa.Column("stage", sa.String(64), nullable=True),
        sa.Column("rows_read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skus_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skus_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("eans_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("eans_reassigned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("sku_imports")
    _status.drop(op.get_bind(), checkfirst=True)

    op.add_column("sku_registry", sa.Column("ean", sa.String(32), nullable=True))
    # One code per product again: keep the lowest one.
    op.execute("UPDATE sku_registry SET ean = (SELECT min(ean) FROM sku_eans WHERE sku_eans.sku_id = sku_registry.id)")
    op.create_index("ix_sku_registry_ean", "sku_registry", ["ean"], unique=True)
    op.drop_index("ix_sku_eans_sku_id", table_name="sku_eans")
    op.drop_index("ix_sku_eans_ean", table_name="sku_eans")
    op.drop_table("sku_eans")
