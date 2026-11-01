"""Add worker leases and bounded task attempts."""
from alembic import op
import sqlalchemy as sa

revision = "0002_agent_task_leases"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("agent_tasks", sa.Column("worker_id", sa.String(length=100), nullable=False, server_default=""))
    op.add_column("agent_tasks", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agent_tasks", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agent_tasks", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agent_tasks", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_agent_tasks_worker_id", "agent_tasks", ["worker_id"])
    op.create_index("ix_agent_tasks_lease_expires_at", "agent_tasks", ["lease_expires_at"])


def downgrade():
    op.drop_index("ix_agent_tasks_lease_expires_at", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_worker_id", table_name="agent_tasks")
    op.drop_column("agent_tasks", "attempt_count")
    op.drop_column("agent_tasks", "lease_expires_at")
    op.drop_column("agent_tasks", "heartbeat_at")
    op.drop_column("agent_tasks", "claimed_at")
    op.drop_column("agent_tasks", "worker_id")
