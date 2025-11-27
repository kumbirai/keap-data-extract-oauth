"""add extraction_state table

Revision ID: 002_extraction_state
Revises: 001_oauth_tokens
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_extraction_state'
down_revision = '001_oauth_tokens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for extraction status (only if it doesn't exist)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE extractionstatus AS ENUM ('pending', 'in_progress', 'completed', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.create_table(
        'extraction_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('total_records_processed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('api_offset', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_loaded', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_successful_extraction', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extraction_status', postgresql.ENUM('pending', 'in_progress', 'completed', 'failed', name='extractionstatus', create_type=False), nullable=True, server_default='pending'),
        sa.Column('error_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type')
    )
    op.create_index('idx_extraction_state_entity_type', 'extraction_state', ['entity_type'], unique=True)
    op.create_index('idx_extraction_state_status', 'extraction_state', ['extraction_status'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_extraction_state_status', table_name='extraction_state')
    op.drop_index('idx_extraction_state_entity_type', table_name='extraction_state')
    op.drop_table('extraction_state')
    op.execute('DROP TYPE extractionstatus')

