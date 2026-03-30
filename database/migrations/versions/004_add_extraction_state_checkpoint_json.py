"""add extraction_state.checkpoint_json for stripe sync

Revision ID: 004_checkpoint_json
Revises: 003_stripe_bi
Create Date: 2026-03-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004_checkpoint_json"
down_revision = "003_stripe_bi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "extraction_state",
        sa.Column("checkpoint_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("extraction_state", "checkpoint_json")
