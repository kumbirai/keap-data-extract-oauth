"""Database initialization."""
import logging
from sqlalchemy import inspect

from src.database.config import engine, Base
from src.models.models import OAuthToken, ExtractionState

logger = logging.getLogger(__name__)


def init_db():
    """Initialize database by creating all tables."""
    try:
        # Import all models to ensure they're registered with Base
        # This will be expanded when entity models are added
        from src.models.models import Base as ModelsBase
        
        # Create all tables
        ModelsBase.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Log existing tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.debug(f"Existing tables: {tables}")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

