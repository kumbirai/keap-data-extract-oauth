"""
Data load manager for orchestrating entity loading operations.

This module provides a clean interface for loading data, eliminating the
complex main function and massive if/elif chains from the original script.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from src.api.keap_client import KeapClient
from src.database.config import SessionLocal
from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.loaders import LoadResult, LoaderFactory
from src.utils.global_logger import initialize_loggers

logger = logging.getLogger(__name__)


class DataLoadManager:
    """Main class to manage data loading operations.
    
    This class provides a clean interface for loading data, replacing the
    complex main function with a simple, extensible design.
    
    Can be used as a context manager for automatic resource cleanup:
    
    Example:
        with DataLoadManager() as manager:
            result = manager.load_entity('contacts')
    """

    def __init__(self):
        """Initialize the data load manager.
        
        Raises:
            Exception: If initialization fails (database connection, OAuth2 setup, etc.)
        """
        try:
            self.db = SessionLocal()
            
            # Create TokenManager and OAuth2Client for token refresh
            from src.auth.token_manager import TokenManager
            from src.auth.oauth2_client import OAuth2Client
            
            token_manager = TokenManager(self.db)
            oauth2_client = OAuth2Client(token_manager=token_manager)
            token_manager.set_oauth2_client(oauth2_client)
            
            # Create KeapClient with TokenManager
            self.client = KeapClient(token_manager=token_manager, db_session=self.db)
        except Exception as e:
            logger.error(f"Error initializing DataLoadManager: {e}", exc_info=True)
            if hasattr(self, 'db') and self.db:
                self.db.close()
            raise

        # Initialize logging
        initialize_loggers()

        # Initialize database tables
        from src.database.init_db import init_db
        init_db()

        # Initialize checkpoint manager with database session
        self.checkpoint_manager = CheckpointManager(db_session=self.db)

    def load_entity(
        self,
        entity_type: str,
        entity_id: Optional[int] = None,
        update: bool = False,
        stripe_object_id: Optional[str] = None,
    ) -> LoadResult:
        """Load a specific entity type or individual entity.
        
        Args:
            entity_type: The type of entity to load
            entity_id: Optional ID of specific entity to load
            update: Whether to perform an update operation
            
        Returns:
            LoadResult containing the operation statistics
        """
        if stripe_object_id or (entity_id and entity_type and entity_type.startswith("stripe_")):
            if not entity_type or not entity_type.startswith("stripe_"):
                logger.error("--stripe-object-id requires a stripe_* --entity-type")
                return LoadResult(1, 0, 1)
            if stripe_object_id:
                from src.stripe.orchestrator import run_stripe_object_by_id

                try:
                    return run_stripe_object_by_id(self.db, entity_type, stripe_object_id)
                except Exception as e:
                    logger.error("Stripe single-object load failed: %s", e, exc_info=True)
                    return LoadResult(1, 0, 1)
            logger.error("Stripe entities use string ids; pass --stripe-object-id (not --entity-id).")
            return LoadResult(1, 0, 1)
        if entity_id:
            return self._load_single_entity(entity_type, entity_id)
        else:
            return self._load_entity_type(entity_type, update)

    def _load_single_entity(self, entity_type: str, entity_id: int) -> LoadResult:
        """Load a single entity by ID.
        
        Args:
            entity_type: Type of entity to load
            entity_id: ID of the entity
            
        Returns:
            LoadResult with operation statistics
        """
        if not entity_type or not isinstance(entity_type, str):
            logger.error(f"Invalid entity_type: {entity_type}")
            return LoadResult(1, 0, 1)
        if not isinstance(entity_id, int) or entity_id <= 0:
            logger.error(f"Invalid entity_id: {entity_id}")
            return LoadResult(1, 0, 1)
        
        try:
            loader = LoaderFactory.create_loader(entity_type, self.client, self.db, self.checkpoint_manager)
            success = loader.load_entity_by_id(entity_id)
            return LoadResult(1, 1 if success else 0, 0 if success else 1)
        except ValueError as e:
            logger.error(f"Invalid input for {entity_type} {entity_id}: {e}")
            return LoadResult(1, 0, 1)
        except Exception as e:
            logger.error(f"Error loading {entity_type} {entity_id}: {e}", exc_info=True)
            return LoadResult(1, 0, 1)

    def _load_entity_type(self, entity_type: str, update: bool) -> LoadResult:
        """Load all entities of a specific type.
        
        Args:
            entity_type: Type of entity to load
            update: Whether to perform incremental update
            
        Returns:
            LoadResult with operation statistics
            
        Raises:
            ValueError: If entity_type is invalid
            Exception: If loading fails
        """
        if not entity_type or not isinstance(entity_type, str):
            raise ValueError(f"Invalid entity_type: {entity_type}")
        
        try:
            if entity_type.startswith("stripe_"):
                from src.stripe.orchestrator import run_stripe_entity

                try:
                    return run_stripe_entity(self.db, self.checkpoint_manager, entity_type, update)
                except RuntimeError as e:
                    logger.error("Stripe load cannot run: %s", e)
                    raise
            if entity_type.startswith("revolut_"):
                from src.revolut.orchestrator import run_revolut_entity

                return run_revolut_entity(self.db, self.checkpoint_manager, entity_type, update)
            if entity_type.startswith("keap_v2_"):
                from src.keap_v2.orchestrator import run_keap_v2_entity

                return run_keap_v2_entity(
                    self.db,
                    self.checkpoint_manager,
                    self.client.token_manager,
                    entity_type,
                    update,
                )
            loader = LoaderFactory.create_loader(entity_type, self.client, self.db, self.checkpoint_manager)
            return loader.load_all(update=update)
        except ValueError as e:
            logger.error(f"Invalid entity type {entity_type}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading {entity_type}: {e}", exc_info=True)
            raise

    def load_all_data(self, update: bool = False) -> LoadResult:
        """Load all data in the correct order to maintain referential integrity.
        
        This method replaces the massive if/elif chains and repetitive
        result aggregation from the original main function.
        """
        total_result = LoadResult(0, 0, 0)

        # Define load order for referential integrity
        # This could be moved to configuration for even more flexibility
        load_order = ['custom_fields',  # Referenced by contacts
                      'tags',  # Referenced by contacts
                      'products',  # Referenced by orders and subscriptions
                      'contacts',  # Referenced by orders, tasks, notes
                      'opportunities',  # Independent
                      'affiliates',  # Referenced by orders
                      'orders',  # Referenced by subscriptions
                      'tasks',  # Independent
                      'notes',  # Independent
                      'campaigns',  # Independent
                      'subscriptions',  # Referenced by products
                      ]

        for entity_type in load_order:
            try:
                logger.info(f"Loading {entity_type}...")
                result = self._load_entity_type(entity_type, update)
                total_result.total_records += result.total_records
                total_result.success_count += result.success_count
                total_result.failed_count += result.failed_count
                logger.info(f"Completed {entity_type}: {result.success_count}/{result.total_records} successful")
            except ValueError as e:
                logger.error(f"Invalid configuration for {entity_type}: {e}")
                total_result.failed_count += 1
                # Continue with other entities
            except Exception as e:
                logger.error(f"Error loading {entity_type}: {e}", exc_info=True)
                # Continue with other entities instead of failing completely
                total_result.failed_count += 1

        try:
            from src.keap_v2.orchestrator import run_keap_v2_extract

            v2_result = run_keap_v2_extract(
                self.db,
                self.checkpoint_manager,
                self.client.token_manager,
                update,
            )
            total_result.total_records += v2_result.total_records
            total_result.success_count += v2_result.success_count
            total_result.failed_count += v2_result.failed_count
        except Exception as e:
            logger.error("Keap v2 extract failed: %s", e, exc_info=True)
            total_result.failed_count += 1

        try:
            from src.stripe.orchestrator import run_stripe_extract

            stripe_result = run_stripe_extract(self.db, self.checkpoint_manager, update)
            total_result.total_records += stripe_result.total_records
            total_result.success_count += stripe_result.success_count
            total_result.failed_count += stripe_result.failed_count
        except Exception as e:
            logger.error("Stripe extract failed: %s", e, exc_info=True)
            total_result.failed_count += 1

        try:
            from src.revolut.orchestrator import run_revolut_extract

            revolut_result = run_revolut_extract(self.db, self.checkpoint_manager, update)
            total_result.total_records += revolut_result.total_records
            total_result.success_count += revolut_result.success_count
            total_result.failed_count += revolut_result.failed_count
        except Exception as e:
            logger.error("Revolut extract failed: %s", e, exc_info=True)
            total_result.failed_count += 1

        return total_result

    def get_supported_entity_types(self) -> list:
        """Get list of all supported entity types."""
        return LoaderFactory.get_supported_entity_types()

    def close(self):
        """Close database connection and cleanup resources."""
        try:
            if hasattr(self, 'db') and self.db:
                self.db.close()
            if hasattr(self, 'client') and self.client:
                # Close HTTP session if it exists
                if hasattr(self.client, 'session'):
                    self.client.session.close()
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        self.close()
        return False  # Don't suppress exceptions


def main(
    update: bool = False,
    entity_type: str = None,
    entity_id: int = None,
    stripe_object_id: str = None,
):
    """Main function to perform the data load.
    
    This simplified main function replaces the original 100+ line function
    with a clean, readable implementation.
    """
    start_time = datetime.now(timezone.utc)

    manager = DataLoadManager()

    try:
        if update:
            logger.info("Performing update operation...")
        else:
            logger.info("Starting full data load...")

        # Load data based on parameters
        if entity_type and stripe_object_id:
            result = manager.load_entity(entity_type, update=update, stripe_object_id=stripe_object_id)
        elif entity_type and entity_id:
            result = manager.load_entity(entity_type, entity_id, update)
        elif entity_type:
            result = manager.load_entity(entity_type, update=update)
        else:
            result = manager.load_all_data(update)

        # Log results
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time

        logger.info(f"Data load completed in {duration}")
        logger.info(f"Total records processed: {result.total_records}")
        logger.info(f"Successfully processed: {result.success_count}")
        logger.info(f"Failed to process: {result.failed_count}")

        # Run error reprocessing after main data load
        if not entity_id and not stripe_object_id:
            try:
                from src.scripts.reprocess_errors import ErrorReprocessor
                reprocessor = ErrorReprocessor()
                reprocessor.run()
                logger.info("Error reprocessing completed")
            except Exception as e:
                logger.error(f"Error during error reprocessing: {str(e)}")

    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise
    finally:
        manager.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Load data from Keap API into database')
    parser.add_argument('--update', action='store_true', help='Perform update operation using last_loaded timestamps')
    parser.add_argument('--entity-type', choices=LoaderFactory.get_supported_entity_types(), help='Type of entity to load')
    parser.add_argument('--entity-id', type=int, help='ID of specific entity to load')
    parser.add_argument(
        '--stripe-object-id',
        type=str,
        default=None,
        help='Stripe object id (e.g. ch_...) when using --entity-type stripe_*',
    )

    args = parser.parse_args()

    main(
        update=args.update,
        entity_type=args.entity_type,
        entity_id=args.entity_id,
        stripe_object_id=args.stripe_object_id,
    )

