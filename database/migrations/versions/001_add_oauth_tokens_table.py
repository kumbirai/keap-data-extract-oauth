"""add oauth_tokens table

Revision ID: 001_oauth_tokens
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_oauth_tokens'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'oauth_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.String(length=255), nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=False),
        sa.Column('token_type', sa.String(length=50), nullable=True, server_default='Bearer'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scope', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('client_id')
    )
    op.create_index('idx_oauth_tokens_client_id', 'oauth_tokens', ['client_id'], unique=False)
    op.create_index('idx_oauth_tokens_expires_at', 'oauth_tokens', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_oauth_tokens_expires_at', table_name='oauth_tokens')
    op.drop_index('idx_oauth_tokens_client_id', table_name='oauth_tokens')
    op.drop_table('oauth_tokens')

