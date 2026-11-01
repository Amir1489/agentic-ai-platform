"""Add worker leases and bounded task attempts.

The initial baseline creates tables from current metadata, so this revision is
intentionally idempotent for both fresh and previously adopted databases.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_agent_task_leases"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("agent_tasks")}
    columns = [
        ("worker_id", sa.Column("worker_id", sa.String(length=100), nullable=False, server_default="")),
        ("claimed_at", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True)),
        ("heartbeat_at", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True)),
        ("lease_expires_at", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True)),
        ("attempt_count", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0")),
    ]
    for name, column in columns:
        if name not in existing:
            op.add_column("agent_tasks", column)

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("agent_tasks")}
    for name, column in [
        ("ix_agent_tasks_worker_id", "worker_id"),
        ("ix_agent_tasks_lease_expires_at", "lease_expires_at"),
    ]:
        if name not in indexes:
            op.create_index(name, "agent_tasks", [column])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("agent_tasks")}
    for name in ["ix_agent_tasks_lease_expires_at", "ix_agent_tasks_worker_id"]:
        if name in indexes:
            op.drop_index(name, table_name="agent_tasks")
    existing = {column["name"] for column in sa.inspect(bind).get_columns("agent_tasks")}
    for name in ["attempt_count", "lease_expires_at", "heartbeat_at", "claimed_at", "worker_id"]:
        if name in existing:
            op.drop_column("agent_tasks", name)
