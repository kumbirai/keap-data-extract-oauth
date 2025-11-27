"""Token manager for OAuth2 token lifecycle management."""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from src.auth.token_storage import TokenStorage
from src.utils.config import get_config

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages OAuth2 token lifecycle including automatic refresh."""
    
    def __init__(self, db_session: Session, oauth2_client=None):
        """Initialize token manager.
        
        Args:
            db_session: SQLAlchemy database session
            oauth2_client: OAuth2Client instance for token refresh (optional, can be set later)
        """
        self.storage = TokenStorage(db_session)
        self.oauth2_client = oauth2_client
        self.config = get_config()
        self.refresh_threshold = timedelta(seconds=self.config.get('token_refresh_threshold', 300))
    
    def set_oauth2_client(self, oauth2_client):
        """Set OAuth2 client for token refresh.
        
        Args:
            oauth2_client: OAuth2Client instance
        """
        self.oauth2_client = oauth2_client
    
    def is_token_expired(self, expires_at: datetime) -> bool:
        """Check if token is expired or will expire soon.
        
        Args:
            expires_at: Token expiration datetime
            
        Returns:
            True if token is expired or will expire within threshold
        """
        if not expires_at:
            return True
        
        now = datetime.now(timezone.utc)
        # Consider token expired if it expires within threshold
        return expires_at <= (now + self.refresh_threshold)
    
    def get_valid_access_token(self, client_id: str) -> Optional[str]:
        """Get a valid access token, refreshing if necessary.
        
        Args:
            client_id: OAuth2 client ID
            
        Returns:
            Valid access token, or None if unavailable
            
        Raises:
            ValueError: If client_id is invalid
        """
        if not client_id or not isinstance(client_id, str):
            raise ValueError("client_id must be a non-empty string")
        
        tokens = self.storage.get_tokens(client_id)
        
        if not tokens:
            logger.warning(f"No tokens found for client_id: {client_id}")
            return None
        
        try:
            access_token = tokens.get('access_token')
            expires_at = tokens.get('expires_at')
            refresh_token = tokens.get('refresh_token')
            
            if not access_token or not expires_at or not refresh_token:
                logger.error(f"Invalid token data for client_id: {client_id}")
                return None
            
            # Check if token needs refresh
            if self.is_token_expired(expires_at):
                logger.info(f"Access token expired or expiring soon for client_id: {client_id}, refreshing...")
                
                if not self.oauth2_client:
                    logger.error("OAuth2 client not set, cannot refresh token")
                    return None
                
                # Attempt to refresh token
                try:
                    new_tokens = self.oauth2_client.refresh_token(refresh_token, client_id)
                    if new_tokens:
                        access_token = new_tokens.get('access_token')
                        if not access_token:
                            logger.error(f"Refresh token response missing access_token for client_id: {client_id}")
                            return None
                        logger.info(f"Successfully refreshed token for client_id: {client_id}")
                    else:
                        logger.error(f"Failed to refresh token for client_id: {client_id}")
                        return None
                except Exception as e:
                    logger.error(f"Error refreshing token for client_id {client_id}: {e}", exc_info=True)
                    return None
            
            return access_token
        except KeyError as e:
            logger.error(f"Missing required token field for client_id {client_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting access token for client_id {client_id}: {e}", exc_info=True)
            return None
    
    def refresh_access_token(self, client_id: str) -> bool:
        """Manually refresh access token.
        
        Args:
            client_id: OAuth2 client ID
            
        Returns:
            True if refresh successful, False otherwise
        """
        if not self.oauth2_client:
            logger.error("OAuth2 client not set, cannot refresh token")
            return False
        
        tokens = self.storage.get_tokens(client_id)
        if not tokens:
            logger.warning(f"No tokens found for client_id: {client_id}")
            return False
        
        refresh_token = tokens['refresh_token']
        
        try:
            new_tokens = self.oauth2_client.refresh_token(refresh_token, client_id)
            if new_tokens:
                logger.info(f"Successfully refreshed token for client_id: {client_id}")
                return True
            else:
                logger.error(f"Failed to refresh token for client_id: {client_id}")
                return False
        except Exception as e:
            logger.error(f"Error refreshing token for client_id {client_id}: {e}")
            return False
    
    def store_tokens(
        self,
        client_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        token_type: str = 'Bearer',
        scope: Optional[str] = None
    ) -> bool:
        """Store tokens after OAuth2 authorization or refresh.
        
        Args:
            client_id: OAuth2 client ID
            access_token: Access token
            refresh_token: Refresh token
            expires_in: Token expiration time in seconds
            token_type: Token type (default: Bearer)
            scope: OAuth2 scope
            
        Returns:
            True if stored successfully, False otherwise
            
        Raises:
            ValueError: If required parameters are invalid
        """
        # Input validation
        if not client_id or not isinstance(client_id, str):
            raise ValueError("client_id must be a non-empty string")
        if not access_token or not isinstance(access_token, str):
            raise ValueError("access_token must be a non-empty string")
        if not refresh_token or not isinstance(refresh_token, str):
            raise ValueError("refresh_token must be a non-empty string")
        if not isinstance(expires_in, int) or expires_in <= 0:
            raise ValueError("expires_in must be a positive integer")
        
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        try:
            self.storage.store_tokens(
                client_id=client_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                token_type=token_type,
                scope=scope
            )
            logger.info(f"Stored tokens for client_id: {client_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing tokens for client_id {client_id}: {e}", exc_info=True)
            return False
    
    def get_tokens(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get stored tokens.
        
        Args:
            client_id: OAuth2 client ID
            
        Returns:
            Dictionary with tokens and metadata, or None if not found
        """
        return self.storage.get_tokens(client_id)
    
    def has_valid_tokens(self, client_id: str) -> bool:
        """Check if valid tokens exist for client.
        
        Args:
            client_id: OAuth2 client ID
            
        Returns:
            True if valid tokens exist
        """
        tokens = self.storage.get_tokens(client_id)
        if not tokens:
            return False
        
        # Check if access token is still valid
        return not self.is_token_expired(tokens['expires_at'])

