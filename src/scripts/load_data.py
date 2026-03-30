"""
Main data loading script with audit logging.

This script provides the entry point for data loading operations with
comprehensive audit logging and checkpoint management.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from src.api.keap_client import KeapClient
from src.database.config import SessionLocal
from src.scripts.checkpoint_manager import CheckpointManager
from src.scripts.load_data_manager import DataLoadManager
from src.scripts.loaders import LoaderFactory
from src.utils.global_logger import initialize_loggers
from src.utils.logging_config import setup_logging

# Create logs and checkpoints directories if they don't exist
os.makedirs('logs', exist_ok=True)
os.makedirs('checkpoints', exist_ok=True)

# Setup logging - use LOG_LEVEL from .env if available
from src.utils.config import get_config
try:
    config = get_config()
    log_level_str = config.get('log_level', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
except Exception:
    log_level = logging.INFO

setup_logging(log_level=log_level, log_dir="logs", app_name="keap_data_extract")

# Get logger for this module
logger = logging.getLogger(__name__)


class AuditLogger:
    """Audit logger for tracking data load operations."""
    
    def __init__(self, audit_file: str = 'logs/audit_log.json'):
        self.audit_file = audit_file
        self.audits = self._load_audits()

    def _load_audits(self) -> dict:
        """Load existing audit logs from file."""
        if os.path.exists(self.audit_file):
            try:
                with open(self.audit_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Invalid audit file, starting fresh")
                return {}
        return {}

    def log_audit(self, entity_type: str, start_time: datetime, end_time: datetime, total_records: int, success: int, failed: int) -> None:
        """Log audit information for a data load operation."""
        duration = end_time - start_time
        duration_str = str(duration).split('.')[0]

        audit_entry = {
            'entity_type': entity_type,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'total_records': total_records,
            'success': success,
            'failed': failed,
            'duration': duration_str
        }

        if entity_type not in self.audits:
            self.audits[entity_type] = []

        self.audits[entity_type].append(audit_entry)

        with open(self.audit_file, 'w') as f:
            json.dump(self.audits, f, indent=2)

        logger.info(f"Audit log for {entity_type}: Total={total_records}, Success={success}, "
                    f"Failed={failed}, Duration={duration_str}")


def main(
    update: bool = False,
    entity_type: str = None,
    entity_id: int = None,
    stripe_object_id: str = None,
):
    """Main function to perform the data load with audit logging.
    
    Args:
        update: Whether to perform incremental update
        entity_type: Optional entity type to load
        entity_id: Optional entity ID to load
        
    Raises:
        Exception: If data loading fails
    """
    start_time = datetime.now(timezone.utc)
    audit_logger = AuditLogger()

    # Use context manager for automatic cleanup
    try:
        with DataLoadManager() as manager:
            if update:
                logger.info("Performing update operation...")
            else:
                logger.info("Starting full data load...")

            # Load data based on parameters
            if entity_type and stripe_object_id:
                result = manager.load_entity(
                    entity_type,
                    update=update,
                    stripe_object_id=stripe_object_id,
                )
                entity_key = f"{entity_type}_stripe_object"
            elif entity_type and entity_id:
                result = manager.load_entity(entity_type, entity_id, update)
                entity_key = f"{entity_type}_single"
            elif entity_type:
                result = manager.load_entity(entity_type, update=update)
                entity_key = entity_type
            else:
                result = manager.load_all_data(update)
                entity_key = "all_entities"

            # Log results
            end_time = datetime.now(timezone.utc)
            duration = end_time - start_time

            logger.info(f"Data load completed in {duration}")
            logger.info(f"Total records processed: {result.total_records}")
            logger.info(f"Successfully processed: {result.success_count}")
            logger.info(f"Failed to process: {result.failed_count}")

            # Log audit information
            audit_logger.log_audit(
                entity_type=entity_key,
                start_time=start_time,
                end_time=end_time,
                total_records=result.total_records,
                success=result.success_count,
                failed=result.failed_count
            )

            # Run error reprocessing after main data load
            if not entity_id and not stripe_object_id:
                try:
                    from src.scripts.reprocess_errors import ErrorReprocessor
                    reprocessor = ErrorReprocessor()
                    reprocessor.run()
                    logger.info("Error reprocessing completed")
                except Exception as e:
                    logger.error(f"Error during error reprocessing: {str(e)}", exc_info=True)
    except KeyboardInterrupt:
        logger.info("Data loading interrupted by user")
        raise
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        raise


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
        help='Stripe object id (e.g. ch_...) with --entity-type stripe_*',
    )

    args = parser.parse_args()

    main(
        update=args.update,
        entity_type=args.entity_type,
        entity_id=args.entity_id,
        stripe_object_id=args.stripe_object_id,
    )

