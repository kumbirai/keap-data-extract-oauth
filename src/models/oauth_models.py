"""OAuth2 token and extraction state database models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import ENUM as PostgresEnum, JSONB
from sqlalchemy.sql import func
import enum

# Import Base from base module to avoid circular imports
from src.models.base import Base


class ExtractionStatus(enum.Enum):
    """Extraction status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class OAuthToken(Base):
    """OAuth2 token storage model."""
    __tablename__ = 'oauth_tokens'

    id = Column(Integer, primary_key=True)
    client_id = Column(String(255), nullable=False, unique=True, index=True)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=False)
    token_type = Column(String(50), default='Bearer')
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    scope = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<OAuthToken(client_id='{self.client_id}', expires_at='{self.expires_at}')>"


class ExtractionState(Base):
    """Extraction state tracking model."""
    __tablename__ = 'extraction_state'

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(100), nullable=False, unique=True, index=True)
    total_records_processed = Column(Integer, default=0)
    api_offset = Column(Integer, default=0)
    api_page_token = Column(Text, nullable=True)
    last_loaded = Column(DateTime(timezone=True))
    last_successful_extraction = Column(DateTime(timezone=True))
    extraction_status = Column(PostgresEnum(ExtractionStatus, name='extractionstatus', values_callable=lambda obj: [e.value for e in obj], create_type=False), default=ExtractionStatus.PENDING, index=True)
    error_count = Column(Integer, default=0)
    last_error_message = Column(Text)
    checkpoint_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ExtractionState(entity_type='{self.entity_type}', status='{self.extraction_status.value}')>"

