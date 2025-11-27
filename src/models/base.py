"""Base model for all database models."""
from sqlalchemy.ext.declarative import declarative_base

# Create base for all models
Base = declarative_base()

__all__ = ['Base']

