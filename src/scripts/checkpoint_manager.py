"""Enhanced checkpoint manager with file and database storage."""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from src.models.oauth_models import ExtractionState, ExtractionStatus

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Enhanced checkpoint manager supporting both file and database storage."""
    
    def __init__(self, checkpoint_file: str = 'checkpoints/extraction_state.json', db_session: Optional[Session] = None):
        """Initialize checkpoint manager.
        
        Args:
            checkpoint_file: Path to file-based checkpoint storage
            db_session: Optional database session for database-backed storage
        """
        self.checkpoint_file = checkpoint_file
        self.db = db_session
        os.makedirs(os.path.dirname(self.checkpoint_file), exist_ok=True)
        self.checkpoints = self._load_checkpoints()
    
    def _load_checkpoints(self) -> Dict[str, Any]:
        """Load checkpoints from file if it exists, otherwise return empty dict.
        
        Returns:
            Dictionary of checkpoint data
        """
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid checkpoint file {self.checkpoint_file}, starting fresh: {e}")
                # Backup corrupted file
                try:
                    backup_file = f"{self.checkpoint_file}.corrupted.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
                    os.rename(self.checkpoint_file, backup_file)
                    logger.info(f"Backed up corrupted checkpoint file to {backup_file}")
                except Exception as backup_error:
                    logger.warning(f"Could not backup corrupted checkpoint file: {backup_error}")
                return {}
            except (IOError, OSError) as e:
                logger.error(f"Error reading checkpoint file {self.checkpoint_file}: {e}")
                return {}
        return {}
    
    def _sync_to_database(self, entity_type: str, checkpoint_data: Dict[str, Any]) -> None:
        """Sync checkpoint data to database.
        
        Args:
            entity_type: Type of entity
            checkpoint_data: Checkpoint data dictionary
        """
        if not self.db:
            return
        
        try:
            extraction_state = self.db.query(ExtractionState).filter_by(entity_type=entity_type).first()
            
            if extraction_state:
                # Update existing state
                extraction_state.total_records_processed = checkpoint_data.get('total_records_processed', 0)
                extraction_state.api_offset = checkpoint_data.get('api_offset', 0)
                
                last_loaded_str = checkpoint_data.get('last_loaded')
                if last_loaded_str:
                    try:
                        extraction_state.last_loaded = datetime.fromisoformat(last_loaded_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        pass
                
                if checkpoint_data.get('completed', False):
                    extraction_state.last_successful_extraction = datetime.now(timezone.utc)
                    extraction_state.extraction_status = ExtractionStatus.COMPLETED
                else:
                    extraction_state.extraction_status = ExtractionStatus.IN_PROGRESS
                
                extraction_state.updated_at = datetime.now(timezone.utc)
            else:
                # Create new state
                last_loaded_str = checkpoint_data.get('last_loaded')
                last_loaded = None
                if last_loaded_str:
                    try:
                        last_loaded = datetime.fromisoformat(last_loaded_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        pass
                
                status = ExtractionStatus.COMPLETED if checkpoint_data.get('completed', False) else ExtractionStatus.IN_PROGRESS
                
                extraction_state = ExtractionState(
                    entity_type=entity_type,
                    total_records_processed=checkpoint_data.get('total_records_processed', 0),
                    api_offset=checkpoint_data.get('api_offset', 0),
                    last_loaded=last_loaded,
                    last_successful_extraction=datetime.now(timezone.utc) if checkpoint_data.get('completed', False) else None,
                    extraction_status=status
                )
                self.db.add(extraction_state)
            
            self.db.commit()
        except Exception as e:
            logger.error(f"Error syncing checkpoint to database for {entity_type}: {e}")
            if self.db:
                self.db.rollback()
    
    def _load_from_database(self, entity_type: str) -> Optional[Dict[str, Any]]:
        """Load checkpoint data from database.
        
        Args:
            entity_type: Type of entity
            
        Returns:
            Checkpoint data dictionary or None if not found
        """
        if not self.db:
            return None
        
        try:
            extraction_state = self.db.query(ExtractionState).filter_by(entity_type=entity_type).first()
            if extraction_state:
                return {
                    'total_records_processed': extraction_state.total_records_processed,
                    'api_offset': extraction_state.api_offset,
                    'last_loaded': extraction_state.last_loaded.isoformat() if extraction_state.last_loaded else None,
                    'completed': extraction_state.extraction_status == ExtractionStatus.COMPLETED,
                    'extraction_status': extraction_state.extraction_status.value,
                    'error_count': extraction_state.error_count,
                    'last_error_message': extraction_state.last_error_message
                }
        except Exception as e:
            logger.error(f"Error loading checkpoint from database for {entity_type}: {e}")
        
        return None
    
    def save_checkpoint(
        self,
        entity_type: str,
        total_records_processed: int,
        api_offset: Optional[int] = None,
        completed: bool = False,
        error_count: int = 0,
        last_error_message: Optional[str] = None
    ) -> None:
        """Save checkpoint with total records processed and API offset.
        
        Args:
            entity_type: The type of entity being processed
            total_records_processed: Total number of records processed so far
            api_offset: Current API pagination offset (optional, will be calculated if not provided)
            completed: Whether this entity type is fully loaded
            error_count: Number of errors encountered
            last_error_message: Last error message encountered
        """
        if entity_type not in self.checkpoints:
            self.checkpoints[entity_type] = {
                'total_records_processed': 0,
                'api_offset': 0,
                'last_loaded': None,
                'completed': False
            }

        self.checkpoints[entity_type]['total_records_processed'] = total_records_processed

        # If api_offset is provided, use it; otherwise calculate from total_records_processed
        if api_offset is not None:
            self.checkpoints[entity_type]['api_offset'] = api_offset
        else:
            # Calculate API offset based on total records processed (assuming batch size of 50)
            self.checkpoints[entity_type]['api_offset'] = (total_records_processed // 50) * 50

        if completed:
            self.checkpoints[entity_type]['last_loaded'] = datetime.now(timezone.utc).isoformat()
            self.checkpoints[entity_type]['completed'] = True
        else:
            self.checkpoints[entity_type]['completed'] = False

        self.checkpoints[entity_type]['error_count'] = error_count
        if last_error_message:
            self.checkpoints[entity_type]['last_error_message'] = last_error_message

        # Save to file with error handling
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.checkpoints, f, indent=2)
        except (IOError, OSError) as e:
            logger.error(f"Error saving checkpoint file {self.checkpoint_file}: {e}")
            # Continue even if file save fails - database sync will still work
        
        # Sync to database
        self._sync_to_database(entity_type, self.checkpoints[entity_type])
        
        logger.debug(
            f"Saved checkpoint for {entity_type}: {total_records_processed} records processed, "
            f"API offset: {self.checkpoints[entity_type]['api_offset']}"
        )

    def get_checkpoint(self, entity_type: str) -> int:
        """Get the total records processed for an entity type.
        
        Args:
            entity_type: Type of entity
            
        Returns:
            Total records processed
        """
        # Try to load from database first
        db_checkpoint = self._load_from_database(entity_type)
        if db_checkpoint:
            return db_checkpoint.get('total_records_processed', 0)
        
        # Fall back to file-based checkpoint
        return self.checkpoints.get(entity_type, {}).get('total_records_processed', 0)

    def get_api_offset(self, entity_type: str) -> int:
        """Get the API offset for an entity type.
        
        Args:
            entity_type: Type of entity
            
        Returns:
            API offset
        """
        # Try to load from database first
        db_checkpoint = self._load_from_database(entity_type)
        if db_checkpoint:
            return db_checkpoint.get('api_offset', 0)
        
        # Fall back to file-based checkpoint
        return self.checkpoints.get(entity_type, {}).get('api_offset', 0)

    def get_last_loaded_timestamp(self, entity_type: str) -> Optional[str]:
        """Get the last loaded timestamp for an entity type.
        
        Args:
            entity_type: Type of entity
            
        Returns:
            ISO format timestamp string or None
        """
        # Try to load from database first
        db_checkpoint = self._load_from_database(entity_type)
        if db_checkpoint:
            return db_checkpoint.get('last_loaded')
        
        # Fall back to file-based checkpoint
        return self.checkpoints.get(entity_type, {}).get('last_loaded')

    def get_query_params(self, entity_type: str, update: bool = False) -> Dict[str, Any]:
        """Get query parameters based on entity type and update flag.
        
        Args:
            entity_type: Type of entity
            update: Whether to perform incremental update
            
        Returns:
            Dictionary of query parameters
        """
        params = {}
        if update:
            last_loaded = self.get_last_loaded_timestamp(entity_type)
            if last_loaded:
                params['since'] = last_loaded
        return params

    def clear_checkpoints(self) -> None:
        """Clear all checkpoints from both file and database."""
        self.checkpoints = {}
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
        
        if self.db:
            try:
                self.db.query(ExtractionState).delete()
                self.db.commit()
            except Exception as e:
                logger.error(f"Error clearing database checkpoints: {e}")
                self.db.rollback()
        
        logger.debug("Cleared all checkpoints")

    def update_error_state(self, entity_type: str, error_message: str) -> None:
        """Update error state for an entity type.
        
        Args:
            entity_type: Type of entity
            error_message: Error message
            
        Raises:
            ValueError: If entity_type is invalid
        """
        if not entity_type or not isinstance(entity_type, str):
            raise ValueError("entity_type must be a non-empty string")
        if not isinstance(error_message, str):
            raise ValueError("error_message must be a string")
        
        if entity_type not in self.checkpoints:
            self.checkpoints[entity_type] = {
                'total_records_processed': 0,
                'api_offset': 0,
                'last_loaded': None,
                'completed': False,
                'error_count': 0
            }
        
        self.checkpoints[entity_type]['error_count'] = self.checkpoints[entity_type].get('error_count', 0) + 1
        self.checkpoints[entity_type]['last_error_message'] = error_message
        
        # Save to file with error handling
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.checkpoints, f, indent=2)
        except (IOError, OSError) as e:
            logger.error(f"Error saving checkpoint file {self.checkpoint_file}: {e}")
            # Continue even if file save fails - database update will still work
        
        # Update database
        if self.db:
            try:
                extraction_state = self.db.query(ExtractionState).filter_by(entity_type=entity_type).first()
                if extraction_state:
                    extraction_state.error_count += 1
                    extraction_state.last_error_message = error_message
                    extraction_state.extraction_status = ExtractionStatus.FAILED
                    extraction_state.updated_at = datetime.now(timezone.utc)
                else:
                    extraction_state = ExtractionState(
                        entity_type=entity_type,
                        error_count=1,
                        last_error_message=error_message,
                        extraction_status=ExtractionStatus.FAILED
                    )
                    self.db.add(extraction_state)
                self.db.commit()
            except Exception as e:
                logger.error(f"Error updating error state in database for {entity_type}: {e}", exc_info=True)
                if self.db:
                    self.db.rollback()

