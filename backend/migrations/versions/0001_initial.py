"""Initial schema baseline.

This idempotent baseline adopts existing installations created by SQLAlchemy
create_all and creates missing tables for new installations. Future schema
changes must use explicit Alembic revisions.
"""
from alembic import op
from app.database import Base
from app import models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    # The baseline may adopt a live database. Never drop user data automatically.
    raise RuntimeError("The initial schema baseline is forward-only; restore from a backup for rollback.")
