"""
Main entry point for the Keap Data Extraction application.

This module provides the CLI interface for the application, handling
command-line arguments and coordinating the data extraction process.
"""

import argparse
import logging
import sys
from pathlib import Path

from src.api.exceptions import KeapAPIError, KeapAuthenticationError, KeapValidationError
from src.scripts.load_data import main as load_data_main
from src.scripts.loaders import LoaderFactory
from src.utils.logging_config import setup_logging


def ensure_directories_exist():
    """Ensure all required directories exist."""
    required_dirs = ["logs", "logs/errors", "checkpoints"]

    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logging.info(f"Ensured directory exists: {dir_path}")


def parse_args():
    """Parse all command line arguments."""
    parser = argparse.ArgumentParser(
        description='Keap Data Extraction Tool - OAuth2 Edition',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full data extraction
  python -m src

  # Incremental update (only changed data)
  python -m src --update

  # Extract specific entity type
  python -m src --entity-type contacts

  # All Stripe BI entities only (skips Keap when used alone)
  python -m src --entity-type stripe_all

  # Extract single entity by ID
  python -m src --entity-type contacts --entity-id 12345

  # Debug mode with verbose logging
  python -m src --debug
        """
    )
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--update', action='store_true', help='Perform update operation using last_loaded timestamps')
    parser.add_argument('--entity-type', choices=LoaderFactory.get_supported_entity_types(), help='Type of entity to load')
    parser.add_argument('--entity-id', type=int, help='ID of specific entity to load')
    parser.add_argument(
        '--stripe-object-id',
        type=str,
        default=None,
        help='Stripe object id (e.g. ch_...) when using --entity-type stripe_*',
    )
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    # Parse command line arguments
    args = parse_args()

    # Setup logging with the appropriate level
    # Priority: --debug flag > LOG_LEVEL from .env > default INFO
    if args.debug:
        log_level = logging.DEBUG
    else:
        # Get log level from .env file
        from src.utils.config import get_config
        try:
            config = get_config()
            log_level_str = config.get('log_level', 'INFO').upper()
            log_level = getattr(logging, log_level_str, logging.INFO)
        except Exception:
            log_level = logging.INFO
    
    setup_logging(log_level=log_level, log_dir="logs", app_name="keap_data_extract")

    logger = logging.getLogger(__name__)
    logger.info("Starting Keap Data Extraction application (OAuth2)")

    try:
        # Validate configuration before starting
        from src.utils.config import validate_config
        try:
            validate_config()
        except Exception as config_error:
            logger.error(f"Configuration validation failed: {config_error}")
            logger.error("Please check your .env file and ensure all required variables are set.")
            sys.exit(1)
        
        # Ensure all required directories exist
        ensure_directories_exist()

        # Execute the load_data script with arguments
        load_data_main(
            update=args.update,
            entity_type=args.entity_type,
            entity_id=args.entity_id,
            stripe_object_id=args.stripe_object_id,
        )
        logger.info("Data loading completed successfully")

    except KeapAuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        error_msg = str(e)
        if "Database tables not found" in error_msg:
            logger.error("\n" + "="*60)
            logger.error("SETUP REQUIRED:")
            logger.error("="*60)
            logger.error("1. Run database migrations:")
            logger.error("   alembic upgrade head")
            logger.error("2. Authorize the application:")
            logger.error("   python -m src.auth.authorize")
            logger.error("="*60)
        else:
            logger.error("Please run the authorization script to obtain OAuth2 tokens:")
            logger.error("  python -m src.auth.authorize")
        sys.exit(1)
    except KeapValidationError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except KeapAPIError as e:
        logger.error(f"API error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)

    logger.info("Application completed successfully")


if __name__ == "__main__":
    main()

