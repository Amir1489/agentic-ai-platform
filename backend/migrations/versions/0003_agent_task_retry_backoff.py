"""Persist retry scheduling and per-claim fencing tokens."""
from alembic import op
import sqlalchemy as sa

revision = "0003_agent_task_retry_backoff"
down_revision = "0002_agent_task_leases"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("agent_tasks")}
    if "lease_token" not in existing:
        op.add_column(
            "agent_tasks",
            sa.Column("lease_token", sa.String(length=36), nullable=False, server_default=""),
        )
    if "next_retry_at" not in existing:
        op.add_column(
            "agent_tasks",
            sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        )

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("agent_tasks")}
    if "ix_agent_tasks_lease_token" not in indexes:
        op.create_index("ix_agent_tasks_lease_token", "agent_tasks", ["lease_token"])
    if "ix_agent_tasks_next_retry_at" not in indexes:
        op.create_index("ix_agent_tasks_next_retry_at", "agent_tasks", ["next_retry_at"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("agent_tasks")}
    for name in ("ix_agent_tasks_next_retry_at", "ix_agent_tasks_lease_token"):
        if name in indexes:
            op.drop_index(name, table_name="agent_tasks")
    existing = {column["name"] for column in sa.inspect(bind).get_columns("agent_tasks")}
    if "next_retry_at" in existing:
        op.drop_column("agent_tasks", "next_retry_at")
    if "lease_token" in existing:
        op.drop_column("agent_tasks", "lease_token")
