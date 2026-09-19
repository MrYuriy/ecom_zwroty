"""drop the SUPERVISOR role

Revision ID: 00005
Revises: 00004
"""

from alembic import op

revision = "00005"
down_revision = "00004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'OPERATOR' WHERE role = 'SUPERVISOR'")
    # Postgres can't remove a value from an enum, so the type is rebuilt without it.
    op.execute("ALTER TYPE role_enum RENAME TO role_enum_old")
    op.execute("CREATE TYPE role_enum AS ENUM ('OPERATOR', 'ADMIN')")
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE role_enum USING role::text::role_enum")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'OPERATOR'")
    op.execute("DROP TYPE role_enum_old")


def downgrade() -> None:
    op.execute("ALTER TYPE role_enum ADD VALUE IF NOT EXISTS 'SUPERVISOR' AFTER 'OPERATOR'")
