# alembic/versions/xxxx_create_users_and_predictions_tables.py
"""create users and predictions tables

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-01-15 10:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = None        # None means this is the first migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id",              sa.Integer(),     nullable=False),
        sa.Column("name",            sa.String(100),   nullable=False),
        sa.Column("email",           sa.String(255),   nullable=False),
        sa.Column("hashed_password", sa.String(255),   nullable=False),
        sa.Column("age",             sa.Integer(),     nullable=False),
        sa.Column("role",            sa.Enum("admin", "user", name="userrole"), nullable=False),
        sa.Column("is_active",       sa.Boolean(),     nullable=False),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_id",    "users", ["id"])

    op.create_table(
        "predictions",
        sa.Column("id",            sa.Integer(),  nullable=False),
        sa.Column("user_id",       sa.Integer(),  nullable=False),
        sa.Column("input_hash",    sa.String(64), nullable=False),
        sa.Column("prediction",    sa.Float(),    nullable=False),
        sa.Column("confidence",    sa.Float(),    nullable=False),
        sa.Column("model_version", sa.String(20), nullable=False),
        sa.Column("latency_ms",    sa.Float(),    nullable=False),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_predictions_id",      "predictions", ["id"])
    op.create_index("ix_predictions_user_id", "predictions", ["user_id"])


def downgrade() -> None:
    op.drop_table("predictions")  # predictions first — it references users
    op.drop_table("users")