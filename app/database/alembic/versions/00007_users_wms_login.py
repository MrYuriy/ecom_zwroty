"""users: log in with a WMS login instead of an e-mail

Revision ID: 00007
Revises: 00006
"""

import sqlalchemy as sa
from alembic import op

revision = "00007"
down_revision = "00006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing users keep their old e-mail as the login until an admin changes it.
    op.drop_index("ix_users_email", table_name="users")
    op.alter_column("users", "email", new_column_name="wms_login", type_=sa.String(64), existing_nullable=False)
    op.create_index("ix_users_wms_login", "users", ["wms_login"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_wms_login", table_name="users")
    op.alter_column("users", "wms_login", new_column_name="email", type_=sa.String(255), existing_nullable=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
