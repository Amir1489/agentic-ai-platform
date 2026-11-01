"""Add shared database-backed authentication rate-limit buckets.

Revision ID: 0002_auth_rate_limits
Revises: 0001_initial
"""
from alembic import op
from sqlalchemy import Column, Integer, String, inspect

revision = "0002_auth_rate_limits"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # The initial baseline uses current metadata.create_all() to adopt both
    # new and existing databases, so this revision must tolerate a table that
    # the baseline has already created on a fresh installation.
    bind = op.get_bind()
    if "auth_rate_limit_buckets" not in inspect(bind).get_table_names():
        op.create_table(
            "auth_rate_limit_buckets",
            Column("bucket_key", String(64), primary_key=True),
            Column("window_start", Integer(), nullable=False),
            Column("request_count", Integer(), nullable=False),
        )
    indexes = {item["name"] for item in inspect(bind).get_indexes("auth_rate_limit_buckets")}
    if "ix_auth_rate_limit_buckets_window_start" not in indexes:
        op.create_index("ix_auth_rate_limit_buckets_window_start", "auth_rate_limit_buckets", ["window_start"])


def downgrade():
    bind = op.get_bind()
    if "auth_rate_limit_buckets" in inspect(bind).get_table_names():
        indexes = {item["name"] for item in inspect(bind).get_indexes("auth_rate_limit_buckets")}
        if "ix_auth_rate_limit_buckets_window_start" in indexes:
            op.drop_index("ix_auth_rate_limit_buckets_window_start", table_name="auth_rate_limit_buckets")
        op.drop_table("auth_rate_limit_buckets")
