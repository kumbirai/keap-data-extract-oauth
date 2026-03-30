"""Configuration validation and management."""
import os
import logging
from typing import List, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


def get_env_var(name: str, required: bool = True, default: Optional[str] = None) -> str:
    """Get environment variable with validation.
    
    Args:
        name: Environment variable name
        required: Whether the variable is required
        default: Default value if not required and not set
        
    Returns:
        Environment variable value
        
    Raises:
        ConfigError: If required variable is missing
    """
    value = os.getenv(name, default)
    if required and not value:
        raise ConfigError(f"Required environment variable {name} is not set")
    return value


def validate_config() -> None:
    """Validate all required configuration.
    
    Raises:
        ConfigError: If any required configuration is missing or invalid
    """
    errors: List[str] = []
    
    # OAuth2 Configuration
    try:
        get_env_var('KEAP_CLIENT_ID')
    except ConfigError:
        errors.append("KEAP_CLIENT_ID is required")
    
    try:
        get_env_var('KEAP_CLIENT_SECRET')
    except ConfigError:
        errors.append("KEAP_CLIENT_SECRET is required")
    
    try:
        redirect_uri = get_env_var('KEAP_REDIRECT_URI')
        # Allow HTTP for localhost (common in development)
        if not (redirect_uri.startswith('https://') or redirect_uri.startswith('http://localhost')):
            errors.append("KEAP_REDIRECT_URI must be HTTPS or http://localhost")
    except ConfigError:
        errors.append("KEAP_REDIRECT_URI is required")
    
    # Database Configuration
    try:
        get_env_var('DB_HOST')
    except ConfigError:
        errors.append("DB_HOST is required")
    
    try:
        get_env_var('DB_PORT')
    except ConfigError:
        errors.append("DB_PORT is required")
    
    try:
        get_env_var('DB_NAME')
    except ConfigError:
        errors.append("DB_NAME is required")
    
    try:
        get_env_var('DB_USER')
    except ConfigError:
        errors.append("DB_USER is required")
    
    try:
        get_env_var('DB_PASSWORD')
    except ConfigError:
        errors.append("DB_PASSWORD is required")
    
    # Token Encryption
    try:
        encryption_key = get_env_var('TOKEN_ENCRYPTION_KEY')
        if len(encryption_key) < 32:
            errors.append("TOKEN_ENCRYPTION_KEY must be at least 32 bytes")
    except ConfigError:
        errors.append("TOKEN_ENCRYPTION_KEY is required")
    
    if errors:
        error_msg = "Configuration errors:\n" + "\n".join(f"  - {error}" for error in errors)
        raise ConfigError(error_msg)


def get_config() -> dict:
    """Get all configuration as a dictionary.
    
    Returns:
        Dictionary of configuration values
    """
    return {
        'keap_client_id': get_env_var('KEAP_CLIENT_ID'),
        'keap_client_secret': get_env_var('KEAP_CLIENT_SECRET'),
        'keap_redirect_uri': get_env_var('KEAP_REDIRECT_URI'),
        'db_host': get_env_var('DB_HOST', default='localhost'),
        'db_port': get_env_var('DB_PORT', default='5432'),
        'db_name': get_env_var('DB_NAME', default='keap_db'),
        'db_user': get_env_var('DB_USER', default='postgres'),
        'db_password': get_env_var('DB_PASSWORD'),
        'token_encryption_key': get_env_var('TOKEN_ENCRYPTION_KEY'),
        'token_refresh_threshold': int(get_env_var('TOKEN_REFRESH_THRESHOLD', required=False, default='300')),
        'log_level': get_env_var('LOG_LEVEL', required=False, default='INFO'),
        'batch_size': int(get_env_var('BATCH_SIZE', required=False, default='50')),
        'stripe_api_key': (get_env_var('STRIPE_API_KEY', required=False, default='') or '').strip() or None,
        'stripe_account_ids': (get_env_var('STRIPE_ACCOUNT_IDS', required=False, default='') or '').strip() or None,
        'stripe_api_version': (get_env_var('STRIPE_API_VERSION', required=False, default='') or '').strip() or None,
        'stripe_charge_lookback_days': int(get_env_var('STRIPE_CHARGE_LOOKBACK_DAYS', required=False, default='7')),
    }

